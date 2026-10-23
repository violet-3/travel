"""第12轮：行程可执行性 —— 只在有已核验坐标时判断地理合理性。"""

import unittest
from unittest.mock import AsyncMock, patch

from agents.guide_generator import GuideGenerator
from config import AmapConfig, ModelConfig
from models.schemas import (
    Activity, CultureData, DayPlan, RoutePlan, Spot, TravelAgentContext,
    TravelIntent, TravelIntentInput, TravelGuide,
)
from orchestrator_llm import TravelOrchestrator
from tools.itinerary_feasibility import (
    apply_feasibility,
    analyze_itinerary,
    haversine_km,
)

BEIJING = [116.4074, 39.9042]
SHANGHAI = [121.4737, 31.2304]
# 故宫 / 颐和园 附近，直线约 15 公里
GUGONG = [116.3970, 39.9163]
YIHEYUAN = [116.2730, 39.9999]
# 八达岭长城，距故宫约 60 公里
BADALING = [116.0169, 40.3564]


def _activity(name, coord=None, verified=None):
    if verified is None:
        verified = coord is not None
    return Activity(name=name, coordinate=coord, coordinate_verified=verified)


def _route(days):
    return RoutePlan(route_name="测试路线", cities=["北京"], daily_plan=days)


class HaversineTests(unittest.TestCase):
    def test_known_distance_beijing_to_shanghai(self):
        distance = haversine_km(BEIJING, SHANGHAI)
        self.assertIsNotNone(distance)
        self.assertAlmostEqual(distance, 1067, delta=25)

    def test_invalid_inputs_return_none(self):
        self.assertIsNone(haversine_km(None, SHANGHAI))
        self.assertIsNone(haversine_km([1.0], SHANGHAI))
        self.assertIsNone(haversine_km(["x", "y"], SHANGHAI))
        self.assertIsNone(haversine_km([200.0, 39.0], SHANGHAI))


class FeasibilityTests(unittest.TestCase):
    def test_far_apart_activities_on_same_day_are_flagged(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫", GUGONG),
                afternoon=_activity("八达岭长城", BADALING),
            )
        ])
        report = analyze_itinerary(route, TravelIntent(destinations=["北京"], days=1))
        self.assertTrue(report.checked)
        self.assertLess(report.score, 100)
        self.assertTrue(any("通勤约" in issue for issue in report.issues))
        self.assertGreaterEqual(report.days[0].max_leg_km, 50)

    def test_nearby_activities_stay_clean(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫", GUGONG),
                afternoon=_activity("颐和园", YIHEYUAN),
            )
        ])
        report = analyze_itinerary(route, TravelIntent(destinations=["北京"], days=1))
        self.assertEqual(report.score, 100)
        self.assertEqual(report.level, "A")
        self.assertEqual(report.issues, [])

    def test_cross_city_day_is_serious(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫", GUGONG),
                afternoon=_activity("外滩", SHANGHAI),
            )
        ])
        report = analyze_itinerary(route, TravelIntent(destinations=["北京"], days=1))
        self.assertLessEqual(report.score, 70)
        self.assertTrue(any("明显吃紧" in issue for issue in report.issues))

    def test_relaxed_pace_rejects_three_activities(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫"),
                afternoon=_activity("景山"),
                evening=_activity("南锣鼓巷"),
            )
        ])
        intent = TravelIntent(destinations=["北京"], days=1, pace="轻松")
        report = analyze_itinerary(route, intent)
        self.assertTrue(any("超过建议上限2个" in issue for issue in report.issues))

    def test_normal_pace_allows_three_activities(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫"),
                afternoon=_activity("景山"),
                evening=_activity("南锣鼓巷"),
            )
        ])
        intent = TravelIntent(destinations=["北京"], days=1, pace="不紧不慢")
        report = analyze_itinerary(route, intent)
        self.assertFalse(any("超过建议上限" in issue for issue in report.issues))

    def test_unverified_coordinates_are_ignored(self):
        """模型自报坐标但未核验时，不参与距离计算。"""
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫", GUGONG, verified=False),
                afternoon=_activity("外滩", SHANGHAI, verified=False),
            )
        ])
        report = analyze_itinerary(route, TravelIntent(destinations=["北京"], days=1))
        self.assertFalse(report.checked)
        self.assertEqual(report.location_coverage, 0.0)
        self.assertTrue(any("无法判断景点间通勤" in note for note in report.notes))
        self.assertEqual(report.issues, [])

    def test_partial_coverage_is_reported(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫", GUGONG),
                afternoon=_activity("颐和园", YIHEYUAN),
                evening=_activity("南锣鼓巷"),          # 无坐标
            )
        ])
        report = analyze_itinerary(route, TravelIntent(destinations=["北京"], days=1))
        self.assertTrue(report.checked)
        self.assertLess(report.location_coverage, 1.0)
        self.assertTrue(any("位置覆盖率" in note for note in report.notes))

    def test_one_verified_endpoint_does_not_claim_commute_was_checked(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫", GUGONG),
                afternoon=_activity("外滩", SHANGHAI, verified=False),
            )
        ])
        report = analyze_itinerary(route, TravelIntent(destinations=["北京"], days=1))
        self.assertFalse(report.checked)
        self.assertEqual(report.location_coverage, 0.5)

    def test_coverage_counts_each_activity_once_and_preserves_real_leg_number(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("活动A"),
                afternoon=_activity("活动B", GUGONG),
                evening=_activity("活动C", SHANGHAI),
            )
        ])
        report = analyze_itinerary(route, TravelIntent(destinations=["北京"], days=1))
        self.assertTrue(report.checked)
        self.assertAlmostEqual(report.location_coverage, 2 / 3, places=3)
        self.assertTrue(any("第1天第2段通勤" in issue for issue in report.issues))

    def test_empty_itinerary_reports_unchecked(self):
        report = analyze_itinerary(RoutePlan(), None)
        self.assertFalse(report.checked)
        self.assertEqual(report.days, [])
        self.assertEqual(report.score, 100)

    def test_report_serializes_for_the_api(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫", GUGONG),
                afternoon=_activity("八达岭长城", BADALING),
            )
        ])
        payload = analyze_itinerary(route, None).to_dict()
        self.assertEqual(payload["level"], "A" if payload["score"] >= 90 else payload["level"])
        self.assertIsInstance(payload["days"][0]["distance_km"], float)
        self.assertIn("issues", payload)


class WarningTests(unittest.TestCase):
    def test_warnings_are_capped_and_summarized(self):
        day = DayPlan(
            day=1, city="北京",
            morning=_activity("故宫", GUGONG),
            afternoon=_activity("外滩", SHANGHAI),
            evening=_activity("兵马俑", [109.2785, 34.3841]),
        )
        route = _route([day])
        report = analyze_itinerary(route, TravelIntent(destinations=["北京"], days=1))
        apply_feasibility(route, report, limit=2)
        detail = [warning for warning in route.warnings if "通勤约" in warning]
        self.assertLessEqual(len(detail), 2)
        self.assertTrue(any("另有" in warning for warning in route.warnings))

    def test_duplicate_warnings_are_not_added_twice(self):
        route = _route([
            DayPlan(
                day=1, city="北京",
                morning=_activity("故宫", GUGONG),
                afternoon=_activity("外滩", SHANGHAI),
            )
        ])
        report = analyze_itinerary(route, TravelIntent(destinations=["北京"], days=1))
        apply_feasibility(route, report)
        before = len(route.warnings)
        apply_feasibility(route, report)
        self.assertEqual(len(route.warnings), before)


class _FakeIntentParser:
    async def run(self, payload: TravelIntentInput):
        return TravelIntent(destinations=["北京"], days=1, departure_city="北京")


class _FakeRoutePlanner:
    async def run(self, intent: TravelIntent):
        return RoutePlan(
            route_name="北京一日",
            cities=["北京"],
            daily_plan=[
                DayPlan(
                    day=1, city="北京",
                    morning=Activity(name="故宫"),
                    afternoon=Activity(name="八达岭长城"),
                )
            ],
        )


class _FakeAttractionAgent:
    async def run(self, context: TravelAgentContext):
        return [Spot(name="故宫", city="北京", ticket=60)]


class _FakeCultureAgent:
    async def run(self, context: TravelAgentContext):
        return [CultureData(city="北京")]


class OrchestratorIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_feasibility_lands_on_the_guide_after_enrichment(self):
        orchestrator = TravelOrchestrator.__new__(TravelOrchestrator)
        orchestrator.model_config = ModelConfig(timeout=1, max_retries=0)
        orchestrator.amap_config = AmapConfig(web_key="", web_secret="", js_key="", js_security_code="")
        orchestrator.amap_config_warning = ""
        orchestrator.intent_parser = _FakeIntentParser()
        orchestrator.route_planner = _FakeRoutePlanner()
        orchestrator.attraction_recommender = _FakeAttractionAgent()
        orchestrator.culture_engine = _FakeCultureAgent()
        orchestrator.compiler = GuideGenerator()

        async def fake_enrich(spots, cultures, route=None, config=None):
            # 模拟高德核验：只有富化层写回的坐标才算 verified。
            route.daily_plan[0].morning.coordinate = GUGONG
            route.daily_plan[0].morning.coordinate_verified = True
            route.daily_plan[0].afternoon.coordinate = BADALING
            route.daily_plan[0].afternoon.coordinate_verified = True

        async def no_weather(city, config, travel_dates):
            return {"status": "no_key", "city": city, "forecast": []}

        with patch("orchestrator_llm.enrich_guide", new=AsyncMock(side_effect=fake_enrich)), \
                patch("orchestrator_llm.get_weather", new=no_weather):
            guide = await orchestrator.generate("北京一日游", request_overrides={})

        self.assertIsInstance(guide, TravelGuide)
        self.assertTrue(guide.feasibility.get("checked"))
        self.assertLess(guide.feasibility["score"], 100)
        self.assertTrue(any("通勤" in issue for issue in guide.feasibility["issues"]))
        self.assertTrue(any("行程紧凑度" in w or "通勤" in w for w in guide.route.warnings))


if __name__ == "__main__":
    unittest.main()
