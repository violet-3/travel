"""Offline, end-to-end orchestration scenarios with deterministic fake Agents."""

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from agents.guide_generator import GuideGenerator
from config import AmapConfig, ModelConfig
from models.schemas import (
    Activity, CultureData, DayPlan, RoutePlan, Spot, TravelAgentContext,
    TravelIntent, TravelIntentInput, Transport,
)
from orchestrator_llm import TravelOrchestrator


SCENARIOS = (
    {
        "name": "single-city-three-days",
        "query": "想去安阳玩3天",
        "overrides": {"destinations": ["安阳"], "days": 3},
        "days": 3,
        "destinations": ["安阳"],
    },
    {
        "name": "multi-city-seven-days",
        "query": "杭州苏州和朋友出游7天",
        "overrides": {
            "destinations": ["杭州", "苏州"], "days": 7, "travelers": 3,
            "budget": 24000, "budget_scope": "total",
        },
        "days": 7,
        "destinations": ["杭州", "苏州"],
        "travelers": 3,
        "companion": "朋友同行",
    },
    {
        "name": "one-day-trip",
        "query": "西安一日游",
        "overrides": {"destinations": ["西安"], "days": 1, "departure_city": "西安"},
        "days": 1,
        "destinations": ["西安"],
    },
    {
        "name": "family-trip",
        "query": "成都亲子旅行",
        "overrides": {
            "destinations": ["成都"], "days": 4, "travelers": 3,
            "pace": "轻松", "preferences": ["亲子"], "constraints": ["不爬山"],
        },
        "days": 4,
        "destinations": ["成都"],
        "constraints": ["不爬山"],
        "companion": "亲子",
    },
    {
        "name": "older-traveler-low-walking",
        "query": "杭州带老人少走路",
        "overrides": {
            "destinations": ["杭州"], "days": 3, "travelers": 2,
            "pace": "轻松", "constraints": ["少走路"],
        },
        "days": 3,
        "destinations": ["杭州"],
        "constraints": ["少走路"],
        "companion": "老人同行",
    },
    {
        "name": "low-budget-trip",
        "query": "西安3天预算500元",
        "overrides": {
            "destinations": ["西安"], "days": 3, "travelers": 1,
            "budget": 500, "budget_scope": "per_person", "departure_city": "西安",
        },
        "days": 3,
        "destinations": ["西安"],
        "budget_status": "over_known_budget",
    },
    {
        "name": "cross-year-weather-dates",
        "query": "2026年12月31日去安阳",
        "overrides": {
            "destinations": ["安阳"], "days": 3, "travel_date": "2026-12-31",
        },
        "days": 3,
        "destinations": ["安阳"],
        "weather_dates": [date(2026, 12, 31), date(2027, 1, 1), date(2027, 1, 2)],
    },
    {
        "name": "no-map-key-text-degrades",
        "query": "成都3天",
        "overrides": {"destinations": ["成都"], "days": 3},
        "days": 3,
        "destinations": ["成都"],
        "amap_ready": False,
    },
)


class FakeIntentParser:
    async def run(self, request: TravelIntentInput):
        values = request.overrides
        query = request.query
        companion = "独自"
        if "亲子" in query or "带孩子" in query:
            companion = "亲子"
        elif "老人" in query or "爸妈" in query:
            companion = "老人同行"
        elif "朋友" in query:
            companion = "朋友同行"
        return TravelIntent(
            destinations=values.get("destinations", []),
            days=values.get("days", 3),
            travelers=values.get("travelers", 1),
            budget=values.get("budget"),
            budget_scope=values.get("budget_scope", "per_person"),
            departure_city=values.get("departure_city"),
            pace=values.get("pace", "不紧不慢"),
            preferences=values.get("preferences", []),
            constraints=values.get("constraints", []),
            companion=companion,
        )


class FakeRoutePlanner:
    async def run(self, intent: TravelIntent):
        destinations = intent.destinations
        days = intent.days
        day_cities = [
            destinations[min((day_index * len(destinations)) // days, len(destinations) - 1)]
            for day_index in range(days)
        ]
        daily_plan = [
            DayPlan(day=index, city=city, morning=Activity(name=f"{city}城市博物馆"))
            for index, city in enumerate(day_cities, start=1)
        ]
        transitions = []
        for origin, destination in zip(day_cities, day_cities[1:]):
            if origin != destination and (origin, destination) not in transitions:
                transitions.append((origin, destination))
        return RoutePlan(
            route_name=f"{'-'.join(destinations)}{days}日游",
            cities=destinations,
            daily_plan=daily_plan,
            transport=[
                Transport(from_city=origin, to_city=destination,
                          mode="测试交通", duration="1小时", cost_est=100)
                for origin, destination in transitions
            ],
        )


class FakeAttractionAgent:
    def __init__(self, observed_contexts):
        self.observed_contexts = observed_contexts

    async def run(self, context: TravelAgentContext):
        self.observed_contexts.append(context)
        return [Spot(name=f"{city}城市博物馆", city=city, duration="2小时")
                for city in context.route.cities]


class FakeCultureAgent:
    def __init__(self, observed_contexts):
        self.observed_contexts = observed_contexts

    async def run(self, context: TravelAgentContext):
        self.observed_contexts.append(context)
        return [CultureData(city=city) for city in context.route.cities]


def fake_orchestrator():
    observed_contexts = []
    orchestrator = TravelOrchestrator.__new__(TravelOrchestrator)
    orchestrator.model_config = ModelConfig(timeout=1, max_retries=0)
    orchestrator.amap_config = AmapConfig(
        web_key="", web_secret="", js_key="", js_security_code=""
    )
    orchestrator.amap_config_warning = ""
    orchestrator.intent_parser = FakeIntentParser()
    orchestrator.route_planner = FakeRoutePlanner()
    orchestrator.attraction_recommender = FakeAttractionAgent(observed_contexts)
    orchestrator.culture_engine = FakeCultureAgent(observed_contexts)
    orchestrator.compiler = GuideGenerator()
    return orchestrator, observed_contexts


class FixedTravelScenarioTests(unittest.IsolatedAsyncioTestCase):
    async def test_offline_generation_scenarios_keep_request_and_guide_consistent(self):
        observed_weather_dates = []

        async def no_key_weather(city, config, travel_dates):
            observed_weather_dates.extend(travel_dates)
            return {"status": "no_key", "city": city, "forecast": []}

        with patch("orchestrator_llm.enrich_guide", new=AsyncMock(return_value=None)) as enrich, \
                patch("orchestrator_llm.get_weather", new=no_key_weather):
            for scenario in SCENARIOS:
                with self.subTest(scenario=scenario["name"]):
                    orchestrator, contexts = fake_orchestrator()
                    guide = await orchestrator.generate(
                        scenario["query"], request_overrides=scenario["overrides"]
                    )

                    self.assertEqual(guide.days, scenario["days"])
                    self.assertEqual(guide.request.destinations, scenario["destinations"])
                    self.assertEqual(guide.route.cities, scenario["destinations"])
                    self.assertEqual(len(guide.route.daily_plan), scenario["days"])
                    self.assertTrue(all(context.intent == guide.request for context in contexts))
                    self.assertFalse(guide.amap_ready)
                    self.assertTrue(all(
                        "no_key" == weather["status"] for weather in guide.weather
                    ))
                    self.assertEqual(enrich.await_args.kwargs["config"].web_key, "")

                    if "travelers" in scenario:
                        self.assertEqual(guide.request.travelers, scenario["travelers"])
                    if "constraints" in scenario:
                        self.assertEqual(guide.request.constraints, scenario["constraints"])
                        self.assertTrue(all(
                            scenario["constraints"][0] in context.intent.constraints
                            for context in contexts
                        ))
                    if "companion" in scenario:
                        self.assertEqual(guide.request.companion, scenario["companion"])
                    if scenario["name"] == "multi-city-seven-days":
                        self.assertEqual(guide.request.budget_scope, "total")
                        self.assertTrue(all(context.intent.travelers == 3 for context in contexts))
                    if scenario["name"] == "one-day-trip":
                        self.assertEqual(guide.budget.nights, 0)
                    if "budget_status" in scenario:
                        self.assertEqual(guide.budget.budget_status, scenario["budget_status"])
                    if "amap_ready" in scenario:
                        self.assertEqual(guide.amap_ready, scenario["amap_ready"])

        self.assertEqual(
            observed_weather_dates,
            [date(2026, 12, 31), date(2027, 1, 1), date(2027, 1, 2)],
        )


if __name__ == "__main__":
    unittest.main()
