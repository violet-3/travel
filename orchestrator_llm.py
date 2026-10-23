"""
LangChain 多 Agent 旅游攻略编排器

将意图解析、路线规划、景点推荐和文化解说等 LangChain Agent 组合，
并行生成可验证的结构化数据后编译为攻略。
"""

import asyncio
import time
from datetime import date, timedelta
from typing import Callable, Optional

from models.schemas import (
    TravelIntentInput, TravelAgentContext, RoutePlan, Spot, CultureData,
    TravelGuide, WebResearchStatus,
)
from agents.intent_parser import IntentParserAgent
from agents.route_planner import RoutePlannerAgent
from agents.attraction_culture import AttractionRecommenderAgent, CultureEngineAgent
from agents.guide_generator import GuideGenerator
from tools.enrich import clear_untrusted_enrichment, enrich_guide
from tools.weather import clothing_advice, get_weather
from tools.llm_client import LLMClient
from config import AmapConfig, ModelConfig, default_config
from tools.travel_dates import parse_travel_date
from tools.travel_intent import merge_travel_intent, validate_constraint_consistency
from tools.route_validation import validate_hard_constraints, validate_route_plan
from tools.itinerary_feasibility import analyze_itinerary, apply_feasibility
from tools.prep_plan import build_prep_plan
from tools.guide_quality import evaluate_guide
from tools.deepseek_search import TOTAL_TIMEOUT_SECONDS as WEB_RESEARCH_TIMEOUT_SECONDS, research_spots
from tools.deepseek_search_settings import DeepSeekResearchConfig, OFFICIAL_BASE_URL

ProgressCallback = Callable[[int, str, str], None]


class GenerationStageTimeout(TimeoutError):
    def __init__(self, stage: str, timeout: float):
        self.stage = stage
        self.timeout = timeout
        label = {"intent": "需求解析", "route": "路线规划", "content": "景点与文化生成",
                 "enrich": "地图、天气与地点补全", "web_research": "联网来源补全"}.get(stage, stage)
        super().__init__(f"{label}阶段超过 {int(timeout)} 秒，已停止本次请求。")


class TravelOrchestrator:
    """LangChain Agent 流程编排器。"""

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        amap_config: AmapConfig | None = None,
        amap_config_warning: str = "",
        research_config: DeepSeekResearchConfig | None = None,
    ):
        # Capture one immutable configuration for this orchestration request and
        # share its client across the four agents in this request only.
        self.model_config = model_config if model_config is not None else ModelConfig.from_env()
        self.amap_config = amap_config if amap_config is not None else default_config.amap
        self.amap_config_warning = amap_config_warning
        self.research_config = research_config or DeepSeekResearchConfig(
            enabled=False, base_url=OFFICIAL_BASE_URL, availability="disabled"
        )
        self.llm_client = LLMClient(self.model_config)
        self.intent_parser = IntentParserAgent(llm=self.llm_client)
        self.route_planner = RoutePlannerAgent(llm=self.llm_client)
        self.attraction_recommender = AttractionRecommenderAgent(llm=self.llm_client)
        self.culture_engine = CultureEngineAgent(llm=self.llm_client)
        self.compiler = GuideGenerator()

    async def generate(
        self,
        user_input: str,
        on_progress: Optional[ProgressCallback] = None,
        request_overrides: dict | None = None,
    ) -> TravelGuide:
        self._generation_started = time.perf_counter()
        self._stage_durations = {}
        try:
            return await self._generate_impl(user_input, on_progress, request_overrides)
        finally:
            client = getattr(self, "llm_client", None)
            close = getattr(client, "aclose", None)
            if callable(close):
                try:
                    await close()
                except Exception:
                    pass

    def _stage_timeout(self, stage: str) -> float:
        overrides = getattr(self, "_stage_timeout_overrides", {})
        if stage in overrides:
            return float(overrides[stage])
        if stage == "enrich":
            return 120.0
        if stage == "web_research":
            return WEB_RESEARCH_TIMEOUT_SECONDS + 3.0
        config = getattr(self, "model_config", None)
        call_timeout = float(getattr(config, "timeout", 60.0))
        retries = int(getattr(config, "max_retries", 1))
        return min(300.0, max(30.0, call_timeout * (retries + 1) + 15.0))

    async def _run_stage(self, stage: str, awaitable):
        timeout = self._stage_timeout(stage)
        started = time.perf_counter()
        try:
            return await asyncio.wait_for(awaitable, timeout=timeout)
        except asyncio.TimeoutError:
            raise GenerationStageTimeout(stage, timeout) from None
        finally:
            self._stage_durations[stage] = round((time.perf_counter() - started) * 1000)

    async def _run_parallel(self, *awaitables, return_exceptions: bool = False):
        """Run sibling agents together and always stop siblings after interruption."""
        tasks = [asyncio.create_task(awaitable) for awaitable in awaitables]
        try:
            return await asyncio.gather(*tasks, return_exceptions=return_exceptions)
        except BaseException:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    async def _generate_impl(
        self,
        user_input: str,
        on_progress: Optional[ProgressCallback] = None,
        request_overrides: dict | None = None,
    ) -> TravelGuide:
        request_overrides = request_overrides or {}
        validate_constraint_consistency(user_input, request_overrides.get("constraints"))
        if "travel_date" not in request_overrides:
            parse_travel_date(user_input)

        self._notify(on_progress, 5, "intent", "正在理解需求...")
        intent = await self._run_stage(
            "intent",
            self.intent_parser.run(TravelIntentInput(query=user_input, overrides=request_overrides)),
        )
        intent = merge_travel_intent(intent, user_input, request_overrides)
        self._notify(on_progress, 15, "intent",
                     f"目的地: {', '.join(intent.destinations)} | {intent.days}天 | {intent.travelers}人")

        self._notify(on_progress, 20, "route", "正在规划路线...")
        route = await self._run_stage("route", self.route_planner.run(intent))
        validate_route_plan(intent, route)
        if self.amap_config_warning and self.amap_config_warning not in route.warnings:
            route.warnings.append(self.amap_config_warning)
        self._notify(on_progress, 45, "route", f"路线: {route.route_name}")

        self._notify(on_progress, 50, "content", "正在发掘景点和文化...")
        agent_context = TravelAgentContext(route=route, intent=intent)
        spots, cultures = await self._run_stage("content", self._run_parallel(
            self.attraction_recommender.run(agent_context),
            self.culture_engine.run(agent_context),
        ))
        validate_hard_constraints(intent, route, spots, cultures)
        self._notify(on_progress, 80, "content",
                     f"找到 {len(spots)} 个景点, {len(cultures)} 个城市文化")

        # 景点缺 city 时从每日行程反查（富化层按城市搜 POI 需要它）
        self._assign_spot_cities(route, spots)
        # Never allow model-authored coordinates/photos/provenance to survive if
        # enrichment later fails; only the server-side enrichment layer may set them.
        clear_untrusted_enrichment(spots, cultures, route)

        # 富化: POI 坐标 + 实景图片（失败不阻塞主流程）
        self._notify(on_progress, 82, "enrich", "正在匹配位置与实景图片...")
        try:
            weather_targets = _weather_targets(route, intent)
            weather_jobs = [
                get_weather(city, config=self.amap_config, travel_dates=dates)
                for city, dates in weather_targets
            ]
            enrich_job = enrich_guide(spots, cultures, route=route, config=self.amap_config)
            enrich_and_weather = await self._run_stage("enrich", self._run_parallel(
                enrich_job, *weather_jobs, return_exceptions=True
            ))
            enrich_error = enrich_and_weather[0] if enrich_and_weather else None
            if isinstance(enrich_error, Exception):
                route.warnings.append("地图与 POI 补全暂不可用，地点导航会降级为名称搜索。")
            weather = [
                result if isinstance(result, dict) else {
                    "status": "error", "city": city, "forecast": []
                }
                for (city, _), result in zip(weather_targets, enrich_and_weather[1:])
            ]
        except GenerationStageTimeout:
            route.warnings.append("地图、天气与 POI 补全超时；文本攻略仍可使用，相关地点或天气信息待确认。")
            weather = [{"status": "error", "city": city, "forecast": []}
                       for city, _ in _weather_targets(route, intent)]
        except Exception:
            route.warnings.append("地图、天气或 POI 补全失败；文本攻略仍可使用，相关地点或天气信息待确认。")
            weather = [{"status": "error", "city": city, "forecast": []}
                       for city, _ in _weather_targets(route, intent)]

        # Web facts are fetched after model-authored content and existing AMap
        # enrichment, then attached directly to the output without another LLM
        # call. Page text is treated as untrusted evidence, never as instructions.
        self._notify(on_progress, 84, "web_research", "正在补充景点网页来源…")
        try:
            web_research = await self._run_stage(
                "web_research", research_spots(spots, self.research_config)
            )
        except GenerationStageTimeout:
            web_research = {
                "status": "failed", "message": "联网来源补全超时；文本攻略仍可使用。",
                "search_count": 0, "fetch_count": 0,
            }
        except Exception:
            web_research = {
                "status": "failed", "message": "联网来源补全失败；文本攻略仍可使用。",
                "search_count": 0, "fetch_count": 0,
            }

        self._notify(on_progress, 85, "compile", "正在生成攻略...")
        # 富化完成后再判断可执行性：只有核验过的坐标才参与距离计算。
        feasibility = analyze_itinerary(route, intent)
        apply_feasibility(route, feasibility)
        guide = self.compiler.compile(route, spots, cultures, intent=intent)
        guide.feasibility = feasibility.to_dict()
        guide.weather = weather
        guide.prep = build_prep_plan(route, intent, weather)
        guide.web_research = WebResearchStatus.model_validate(web_research)
        guide.clothing_tip = clothing_advice(
            [forecast for city_weather in weather for forecast in city_weather.get("forecast", [])]
        )
        guide.amap_ready = bool(self.amap_config.js_key)
        metrics_getter = getattr(getattr(self, "llm_client", None), "metrics_snapshot", None)
        llm_metrics = metrics_getter() if callable(metrics_getter) else {
            "requests": 0, "elapsed_ms": 0, "input_tokens": None,
            "output_tokens": None, "total_tokens": None,
            "usage_known_calls": 0, "usage_unknown_calls": 0,
        }
        guide.generation_metrics = {
            "elapsed_ms": round((time.perf_counter() - self._generation_started) * 1000),
            "stages_ms": dict(self._stage_durations),
            "llm": llm_metrics,
        }
        # 所有字段就位后再自检，评分才能覆盖预算、可行性与图片来源的实际状态。
        guide.quality = evaluate_guide(guide)
        self._notify(on_progress, 100, "done", "攻略生成完成！")

        return guide

    def _assign_spot_cities(self, route: RoutePlan, spots: list[Spot]) -> None:
        """景点缺 city 时，从每日行程的活动中模糊反查所属城市"""
        name_to_city: list[tuple[str, str]] = []
        for day in route.daily_plan:
            for act in (day.morning, day.afternoon, day.evening):
                if act and act.name:
                    name_to_city.append((act.name, day.city))
        for s in spots:
            if getattr(s, "city", ""):
                continue
            for act_name, city in name_to_city:
                if s.name and (s.name in act_name or act_name in s.name):
                    s.city = city
                    break

    def _notify(self, callback, progress, stage, message):
        if callback:
            try:
                callback(progress, stage, message)
            except Exception:
                pass


def _weather_targets(route: RoutePlan, intent) -> list[tuple[str, list]]:
    """Use the actual city assigned to each itinerary day, with exact dates."""
    days_by_city: dict[str, list[int]] = {}
    for day in route.daily_plan:
        city = (day.city or "").strip()
        if city:
            days_by_city.setdefault(city, []).append(day.day)
    cities = list(days_by_city) if days_by_city else list(dict.fromkeys(route.cities or intent.destinations))
    try:
        start = date.fromisoformat(intent.travel_date) if intent.travel_date else None
    except (TypeError, ValueError):
        start = None
    if start is None:
        return [(city, []) for city in cities]
    targets = []
    for city in cities:
        day_numbers = days_by_city.get(city) or list(range(1, intent.days + 1))
        dates = [start + timedelta(days=max(0, int(day_number) - 1)) for day_number in day_numbers]
        targets.append((city, dates))
    return targets
