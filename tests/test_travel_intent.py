"""Offline coverage for structured travel requests, date rules, and intent propagation."""

import asyncio
import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app
from agents.attraction_culture import AttractionRecommenderAgent, CultureEngineAgent
from agents.guide_generator import GuideGenerator
from agents.route_planner import RoutePlannerAgent
from config import AmapConfig, ModelConfig
from models.schemas import (
    Activity, RoutePlan, TravelAgentContext, TravelIntent, TravelIntentInput,
)
from orchestrator_llm import GenerationStageTimeout, TravelOrchestrator
from tools.travel_dates import TravelDateError, parse_travel_date
from tools.travel_intent import (
    TravelIntentError, merge_travel_intent, validate_constraint_consistency,
)


class TravelDateParsingTests(unittest.TestCase):
    def test_relative_months_roll_across_year_once(self):
        october = date(2026, 10, 20)
        december = date(2026, 12, 20)
        self.assertEqual(parse_travel_date("下个月去", october).month_value, "2026-11")
        self.assertEqual(parse_travel_date("本月出行", october).month_value, "2026-10")
        self.assertEqual(parse_travel_date("下个月", december).month_value, "2027-01")
        self.assertEqual(parse_travel_date("下下个月", december).month_value, "2027-02")

    def test_year_modifier_is_applied_before_month_day(self):
        today = date(2026, 10, 20)
        self.assertEqual(parse_travel_date("明年12月1日", today).date_value, "2027-12-01")
        with self.assertRaises(TravelDateError):
            parse_travel_date("今年5月1日", today)
        with self.assertRaises(TravelDateError):
            parse_travel_date("今年五一", today)

    def test_month_only_and_lunar_holidays_do_not_invent_a_day(self):
        today = date(2026, 10, 20)
        may = parse_travel_date("明年5月去", today)
        self.assertEqual(may.month_value, "2027-05")
        self.assertIsNone(may.date_value)
        self.assertIn("具体日期未定", may.note)
        spring = parse_travel_date("明年春节", today)
        self.assertIsNone(spring.date_value)
        self.assertIn("请填写公历日期", spring.note)

    def test_invalid_and_past_explicit_gregorian_dates_are_rejected(self):
        today = date(2026, 10, 20)
        for text in ("去西安2027年2月30日", "2020-01-01去旅行"):
            with self.subTest(text=text), self.assertRaises(TravelDateError):
                parse_travel_date(text, today)
        self.assertEqual(parse_travel_date("2027-01-02", today).date_value, "2027-01-02")


class TravelIntentMergeTests(unittest.TestCase):
    def setUp(self):
        self.parsed = TravelIntent(destinations=["安阳"], days=3)

    def test_text_days_are_preserved_unless_user_fills_days_form(self):
        natural = merge_travel_intent(self.parsed, "安阳玩7天")
        explicit = merge_travel_intent(self.parsed, "安阳玩7天", {"days": 5})
        self.assertEqual(natural.days, 7)
        self.assertEqual(explicit.days, 5)

    def test_explicit_fields_and_unambiguous_text_values_are_canonical(self):
        result = merge_travel_intent(
            self.parsed,
            "安阳玩3天，从上海出发，2人，总预算3000元",
            {"departure_city": "北京", "travelers": 2, "budget": 3000,
             "budget_scope": "total", "constraints": ["不爬山", "少走路", "不辣"]},
        )
        self.assertEqual(result.departure_city, "北京")
        self.assertEqual(result.travelers, 2)
        self.assertEqual(result.budget, 3000)
        self.assertEqual(result.budget_scope, "total")
        self.assertEqual(result.days, 3)
        self.assertEqual(result.constraints, ["不爬山", "少走路", "不辣"])

    def test_amount_units_and_decimals_are_not_truncated(self):
        parsed = self.parsed.model_copy(update={"budget": 15000})
        ten_thousand = merge_travel_intent(parsed, "安阳3天，预算1.5万元")
        thousands = merge_travel_intent(parsed, "安阳3天，预算3千元")
        self.assertEqual(ten_thousand.budget, 15000)
        self.assertEqual(thousands.budget, 3000)

    def test_departure_city_extraction_respects_from_boundary(self):
        for query, city in (
            ("想从上海出发去安阳3天", "上海"),
            ("我们从北京出发去安阳3天", "北京"),
        ):
            with self.subTest(query=query):
                parsed = self.parsed.model_copy(update={"departure_city": city})
                result = merge_travel_intent(parsed, query)
                self.assertEqual(result.departure_city, city)

    def test_constraints_merge_model_text_and_form_without_loss(self):
        parsed = self.parsed.model_copy(update={
            "constraints": ["无障碍", "少走路", "不爬山"],
        })
        natural_only = merge_travel_intent(parsed, "安阳3天，带轮椅，不爬山")
        with_form = merge_travel_intent(
            parsed, "安阳3天，带轮椅，不爬山", {"constraints": ["不辣"]}
        )
        self.assertEqual(natural_only.constraints, ["无障碍", "少走路", "不爬山"])
        self.assertEqual(with_form.constraints, ["无障碍", "少走路", "不爬山", "不辣"])

    def test_blank_optional_fields_do_not_override_parsed_values(self):
        parsed = self.parsed.model_copy(update={
            "departure_city": "上海", "travelers": 3, "budget": 2500,
            "budget_scope": "per_person", "pace": "轻松",
        })
        result = merge_travel_intent(parsed, "安阳玩7天", {
            "departure_city": None, "travelers": None, "budget": None,
            "budget_scope": None, "pace": None, "days": None,
        })
        self.assertEqual(result.departure_city, "上海")
        self.assertEqual(result.travelers, 3)
        self.assertEqual(result.budget, 2500)
        self.assertEqual(result.pace, "轻松")
        self.assertEqual(result.days, 7)

    def test_multi_person_form_does_not_leave_default_solo_companion(self):
        result = merge_travel_intent(self.parsed, "安阳", {"travelers": 2})
        self.assertEqual(result.travelers, 2)
        self.assertEqual(result.companion, "同行（关系未注明）")

    def test_explicit_companion_relationship_is_preserved(self):
        family = self.parsed.model_copy(update={"companion": "亲子"})
        family_result = merge_travel_intent(family, "成都", {"travelers": 3})
        single_with_explicit_relationship = merge_travel_intent(
            family, "成都", {"travelers": 1}
        )
        self.assertEqual(family_result.companion, "亲子")
        self.assertEqual(single_with_explicit_relationship.companion, "亲子")

    def test_missing_destination_is_rejected(self):
        with self.assertRaises(TravelIntentError):
            merge_travel_intent(TravelIntent(), "我想轻松地旅行")

    def test_destination_list_splits_chinese_enumeration_punctuation(self):
        result = merge_travel_intent(
            self.parsed, "", {"destinations": ["西安、洛阳"]}
        )
        self.assertEqual(result.destinations, ["西安", "洛阳"])

    def test_diet_negation_synonyms_are_not_misread_as_positive(self):
        for phrase in ("不能吃辣", "不吃辣", "不辣"):
            with self.subTest(phrase=phrase):
                validate_constraint_consistency("安阳，" + phrase, ["不辣"])

    def test_actual_hard_constraint_contradictions_are_rejected(self):
        cases = (
            ("安阳，想吃辣", ["不辣"]),
            ("安阳，不辣", ["吃辣"]),
            ("安阳，想去徒步", ["不爬山"]),
        )
        for query, constraints in cases:
            with self.subTest(query=query):
                with self.assertRaises(TravelIntentError):
                    validate_constraint_consistency(query, constraints)


class TravelIntentPropagationTests(unittest.IsolatedAsyncioTestCase):
    async def test_canonical_request_reaches_all_agents_and_final_guide(self):
        observed = {}

        class FakeIntentParser:
            async def run(self, value):
                observed["intent_input"] = value
                return TravelIntent(destinations=["安阳"], days=3)

        class FakeRoutePlanner:
            async def run(self, intent):
                observed["route_intent"] = intent
                return RoutePlan(
                    route_name="安阳3日",
                    cities=["安阳"],
                    daily_plan=[
                        {"day": 1, "city": "安阳", "morning": Activity(name="殷墟")},
                        {"day": 2, "city": "安阳"},
                        {"day": 3, "city": "安阳"},
                    ],
                )

        class FakeSpots:
            async def run(self, context):
                observed["spots_context"] = context
                return []

        class FakeCulture:
            async def run(self, context):
                observed["culture_context"] = context
                return []

        orchestrator = TravelOrchestrator.__new__(TravelOrchestrator)
        orchestrator.model_config = ModelConfig()
        orchestrator.amap_config = AmapConfig(web_key="", web_secret="", js_key="", js_security_code="")
        orchestrator.amap_config_warning = ""
        orchestrator.intent_parser = FakeIntentParser()
        orchestrator.route_planner = FakeRoutePlanner()
        orchestrator.attraction_recommender = FakeSpots()
        orchestrator.culture_engine = FakeCulture()
        orchestrator.compiler = GuideGenerator()

        overrides = {
            "departure_city": "北京", "travelers": 2, "budget": 3000,
            "budget_scope": "total", "constraints": ["不爬山", "少走路", "不辣"],
        }
        with patch("orchestrator_llm.enrich_guide", new=AsyncMock()), \
             patch("orchestrator_llm.get_weather", new=AsyncMock(return_value={"status": "no_key", "forecast": []})):
            guide = await orchestrator.generate("安阳玩3天", request_overrides=overrides)

        self.assertIsInstance(observed["intent_input"], TravelIntentInput)
        self.assertEqual(observed["intent_input"].overrides, overrides)
        canonical = observed["route_intent"]
        self.assertEqual(canonical.departure_city, "北京")
        self.assertEqual(canonical.travelers, 2)
        self.assertEqual(canonical.budget, 3000)
        self.assertEqual(canonical.budget_scope, "total")
        for key in ("spots_context", "culture_context"):
            self.assertIsInstance(observed[key], TravelAgentContext)
            self.assertEqual(observed[key].intent, canonical)

        spots_prompt = AttractionRecommenderAgent(llm=object()).build_user_prompt(observed["spots_context"])
        culture_prompt = CultureEngineAgent(llm=object()).build_user_prompt(observed["culture_context"])
        route_prompt = RoutePlannerAgent(llm=object()).build_user_prompt(canonical)
        for prompt in (spots_prompt, culture_prompt, route_prompt):
            for constraint in ("不爬山", "少走路", "不辣"):
                self.assertIn(constraint, prompt)
        self.assertIn("2人", route_prompt)
        self.assertIn("全体总额", route_prompt)
        self.assertEqual(guide.request.departure_city, "北京")
        self.assertEqual(guide.request.travelers, 2)
        self.assertEqual(guide.request.budget_scope, "total")
        self.assertIn("本次需求摘要", GuideGenerator().to_markdown(guide))


class OrchestratorCancellationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.orchestrator = TravelOrchestrator.__new__(TravelOrchestrator)
        self.orchestrator._stage_durations = {}
        self.orchestrator._stage_timeout_overrides = {"content": 1.0}

    async def test_agent_failure_cancels_and_awaits_its_blocked_sibling(self):
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def fail_fast():
            raise RuntimeError("agent failure")

        async def wait_until_cancelled():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        work = self.orchestrator._run_stage(
            "content",
            self.orchestrator._run_parallel(fail_fast(), wait_until_cancelled()),
        )
        with self.assertRaisesRegex(RuntimeError, "agent failure"):
            await work
        self.assertTrue(started.is_set())
        self.assertTrue(cancelled.is_set())

    async def test_stage_timeout_cancels_and_awaits_all_parallel_agents(self):
        cancelled = asyncio.Event()
        self.orchestrator._stage_timeout_overrides["content"] = 0.02

        async def wait_until_cancelled():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        with self.assertRaises(GenerationStageTimeout):
            await self.orchestrator._run_stage(
                "content", self.orchestrator._run_parallel(wait_until_cancelled())
            )
        self.assertTrue(cancelled.is_set())


class TravelRequestApiValidationTests(unittest.TestCase):
    def test_invalid_and_past_dates_are_safe_422_before_model_construction(self):
        client = TestClient(app.app, base_url="http://127.0.0.1")
        with patch.object(app, "_request_orchestrator", side_effect=AssertionError("must not create model")):
            invalid_date = client.post(
                "/api/generate", json={"query": "想去西安，2027年2月30日旅行"}
            )
            past_date = client.post(
                "/api/generate/stream", json={"query": "想去西安，2020-01-01出发"}
            )
        self.assertEqual(invalid_date.status_code, 422)
        self.assertEqual(past_date.status_code, 422)
        self.assertIn("日期", invalid_date.text)
        self.assertIn("过去", past_date.text)

    def test_missing_destination_and_invalid_numbers_are_safe_422(self):
        client = TestClient(app.app, base_url="http://127.0.0.1")
        missing = client.post("/api/generate", json={"query": ""})
        bad_values = [
            {"query": "安阳", "days": 0},
            {"query": "安阳", "travelers": 0},
            {"query": "安阳", "budget": -1},
        ]
        self.assertEqual(missing.status_code, 422)
        for payload in bad_values:
            with self.subTest(payload=payload):
                response = client.post("/api/generate", json=payload)
                self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
