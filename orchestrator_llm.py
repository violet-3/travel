"""
编排器 v1 (备份) · 直连 LLM 模式

用于 python main.py --direct 时使用
不依赖 Dify，直接调 DeepSeek API
"""

import asyncio
from typing import Callable, Optional

from models.schemas import TravelIntent, TravelGuide
from agents.intent_parser import IntentParserAgent
from agents.route_planner import RoutePlannerAgent
from agents.attraction_culture import AttractionRecommenderAgent, CultureEngineAgent
from agents.guide_generator import GuideGenerator

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

        self._notify(on_progress, 85, "compile", "正在生成攻略...")
        guide = self.compiler.compile(route, spots, cultures)
        self._notify(on_progress, 100, "done", "攻略生成完成！")

        return guide

    def _notify(self, callback, progress, stage, message):
        if callback:
            try:
                callback(progress, stage, message)
            except Exception:
                pass
