"""
编排器 v1 · 直连 LLM 模式

用于 python main.py --direct 时使用
不依赖 Dify，直接调 DeepSeek API

流程与 Dify 模式对齐: Agent 生成内容后同样经过
坐标/图片富化 (tools/enrich) 与 intent 注入编译。
"""

import asyncio
from typing import Callable, Optional

from models.schemas import TravelIntent, RoutePlan, Spot, CultureData, TravelGuide
from agents.intent_parser import IntentParserAgent
from agents.route_planner import RoutePlannerAgent
from agents.attraction_culture import AttractionRecommenderAgent, CultureEngineAgent
from agents.guide_generator import GuideGenerator
from tools.enrich import enrich_guide

ProgressCallback = Callable[[int, str, str], None]


class TravelOrchestrator:
    """编排器 v1: 直连 LLM 模式"""

    def __init__(self):
        self.intent_parser = IntentParserAgent()
        self.route_planner = RoutePlannerAgent()
        self.attraction_recommender = AttractionRecommenderAgent()
        self.culture_engine = CultureEngineAgent()
        self.compiler = GuideGenerator()

    async def generate(
        self,
        user_input: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> TravelGuide:
        self._notify(on_progress, 5, "intent", "正在理解需求...")
        intent = await self.intent_parser.run(user_input)
        self._notify(on_progress, 15, "intent",
                     f"目的地: {', '.join(intent.destinations)} | {intent.days}天")

        self._notify(on_progress, 20, "route", "正在规划路线...")
        route = await self.route_planner.run(intent)
        self._notify(on_progress, 45, "route", f"路线: {route.route_name}")

        self._notify(on_progress, 50, "content", "正在发掘景点和文化...")
        spots, cultures = await asyncio.gather(
            self.attraction_recommender.run(route),
            self.culture_engine.run(route),
        )
        self._notify(on_progress, 80, "content",
                     f"找到 {len(spots)} 个景点, {len(cultures)} 个城市文化")

        # 景点缺 city 时从每日行程反查（富化层按城市搜 POI 需要它）
        self._assign_spot_cities(route, spots)

        # 富化: POI 坐标 + 实景图片（失败不阻塞主流程）
        self._notify(on_progress, 82, "enrich", "正在匹配位置与实景图片...")
        try:
            await enrich_guide(spots, cultures)
        except Exception:
            pass

        self._notify(on_progress, 85, "compile", "正在生成攻略...")
        guide = self.compiler.compile(route, spots, cultures, intent=intent)
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
