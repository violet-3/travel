"""第14轮：攻略质量自检 —— 评分必须可解释、不冒充事实核验。"""

import unittest

from agents.guide_generator import GuideGenerator
from models.schemas import (
    Activity, BudgetBreakdown, CultureData, DayPlan, PhotoSpot, RoutePlan, Spot,
    TravelIntent, Transport,
)
from tools.guide_quality import WEIGHTS, _content, _grade, evaluate_guide


def _route(days: int = 2, cities=None) -> RoutePlan:
    cities = cities or ["北京"]
    plan = []
    for index in range(days):
        city = cities[min(index, len(cities) - 1)]
        plan.append(DayPlan(
            day=index + 1, city=city,
            morning=Activity(name=f"{city}博物馆"),
            afternoon=Activity(name=f"{city}古城"),
            evening=Activity(name=f"{city}夜市"),
        ))
    return RoutePlan(route_name="北京两日", cities=cities, daily_plan=plan)


def _spots(count: int = 4, verified: bool = True, photo: bool = True,
           tips: bool = True, photo_spots: bool = True) -> list[Spot]:
    names = ["北京博物馆", "北京古城", "北京夜市", "北京公园"]
    return [
        Spot(
            name=names[index] if index < len(names) else f"景点{index}",
            city="北京", ticket=50,
            tips="建议早到" if tips else "",
            photo_spots=[PhotoSpot(name="机位")] if photo_spots else [],
            coordinate=[116.4, 39.9] if verified else None,
            coordinate_verified=verified,
            photo="/static/photos/x.jpg" if photo else "",
            photo_source="amap_poi_photo" if photo else "none",
        )
        for index in range(count)
    ]


def _culture() -> list[CultureData]:
    return [CultureData(
        city="北京",
        cuisine={"must_eat": [{"name": "烤鸭", "where": "老字号", "price_per_person": 120}]},
        folk_culture={"architecture": "四合院"},
    )]


def _guide(**overrides):
    intent = overrides.pop("intent", TravelIntent(
        destinations=["北京"], days=2, travelers=2, budget=3000,
        travel_date="2026-11-01", constraints=["不爬山"], departure_city="北京",
    ))
    guide = GuideGenerator().compile(
        overrides.pop("route", _route()),
        overrides.pop("spots", _spots()),
        overrides.pop("cultures", _culture()),
        intent=intent,
    )
    guide.feasibility = overrides.pop("feasibility", {
        "checked": True, "score": 100, "level": "A", "issues": [],
        "notes": [], "days": [], "location_coverage": 1.0,
    })
    guide.route.warnings.append("硬约束已传递给内容 Agent。")
    for key, value in overrides.items():
        setattr(guide, key, value)
    return guide


class StructureTests(unittest.TestCase):
    def test_empty_spots_and_cultures_receive_no_content_completeness_credit(self):
        guide = _guide(spots=[], cultures=[])
        issues = []
        self.assertEqual(_content(guide, issues), 0)
        self.assertTrue(any("没有推荐景点" in issue for issue in issues))
        self.assertTrue(any("没有风土人情内容" in issue for issue in issues))

    def test_partial_spot_data_does_not_receive_missing_culture_credit(self):
        guide = _guide(spots=_spots(1, tips=False, photo_spots=False), cultures=[])
        issues = []
        score = _content(guide, issues)
        self.assertLess(score, 35)
        self.assertTrue(any("没有风土人情内容" in issue for issue in issues))

    def test_complete_guide_scores_high(self):
        report = evaluate_guide(_guide())
        self.assertGreaterEqual(report["score"], 85)
        self.assertEqual(report["grade"], "A")
        self.assertEqual(report["issues"], [])

    def test_missing_spots_penalises_structure_and_content(self):
        report = evaluate_guide(_guide(spots=[]))
        self.assertLess(report["dimensions"]["structure"]["score"], 100)
        self.assertLess(report["dimensions"]["content"]["score"], 100)
        self.assertTrue(any("没有推荐景点" in issue for issue in report["issues"]))

    def test_empty_evening_slots_reduce_structure(self):
        route = _route()
        route.daily_plan[0].evening = Activity()
        route.daily_plan[1].evening = Activity()
        report = evaluate_guide(_guide(route=route))
        self.assertLess(report["dimensions"]["structure"]["score"], 100)
        self.assertTrue(any("动线不够完整" in issue for issue in report["issues"]))


class RequestTests(unittest.TestCase):
    def test_uncovered_destination_is_reported(self):
        intent = TravelIntent(destinations=["北京", "天津"], days=2, budget=2000)
        route = _route(days=2, cities=["北京"])
        report = evaluate_guide(_guide(intent=intent, route=route))
        self.assertLess(report["dimensions"]["request"]["score"], 100)
        self.assertTrue(any("未覆盖目的地：天津" in issue for issue in report["issues"]))

    def test_day_mismatch_is_reported(self):
        intent = TravelIntent(destinations=["北京"], days=5, budget=2000)
        report = evaluate_guide(_guide(intent=intent, route=_route(days=2)))
        self.assertTrue(any("与需求的 5 天不一致" in issue for issue in report["issues"]))

    def test_missing_date_and_budget_are_flagged(self):
        intent = TravelIntent(destinations=["北京"], days=2)
        report = evaluate_guide(_guide(intent=intent))
        text = " ".join(report["issues"])
        self.assertIn("没有填写预算", text)
        self.assertIn("没有明确出行日期", text)

    def test_guide_without_request_gets_middle_score(self):
        guide = _guide()
        guide.request = None
        report = evaluate_guide(guide)
        self.assertEqual(report["dimensions"]["request"]["score"], 50)
        self.assertTrue(any("没有保存需求摘要" in issue for issue in report["issues"]))


class BudgetTests(unittest.TestCase):
    def test_unknown_transport_legs_lower_budget_score(self):
        route = _route()
        route.transport = [
            Transport(from_city="北京", to_city="天津", mode="高铁", cost_est=None),
            Transport(from_city="天津", to_city="北京", mode="高铁", cost_est=None),
        ]
        report = evaluate_guide(_guide(route=route))
        self.assertLess(report["dimensions"]["budget"]["score"], 100)
        self.assertTrue(any("未核价" in issue for issue in report["issues"]))

    def test_pending_ticket_prices_are_reported(self):
        spots = _spots()
        for spot in spots:
            spot.ticket = 0
            spot.ticket_status = "unknown"
        report = evaluate_guide(_guide(spots=spots))
        self.assertTrue(any("没有门票标价" in issue for issue in report["issues"]))

    def test_zero_budget_total_is_flagged(self):
        guide = _guide()
        guide.budget = BudgetBreakdown()
        report = evaluate_guide(guide)
        self.assertEqual(report["dimensions"]["budget"]["score"], 0)
        self.assertTrue(any("预算小计为 0" in issue for issue in report["issues"]))


class LocationTests(unittest.TestCase):
    def test_unverified_locations_lower_score(self):
        report = evaluate_guide(_guide(spots=_spots(verified=False, photo=False)))
        self.assertEqual(report["dimensions"]["location"]["score"], 0)
        self.assertTrue(any("位置未核验" in issue for issue in report["issues"]))
        self.assertTrue(any("有可用图片" in issue for issue in report["issues"]))

    def test_fully_verified_locations_score_full(self):
        report = evaluate_guide(_guide(spots=_spots(verified=True, photo=True)))
        self.assertEqual(report["dimensions"]["location"]["score"], 100)


class FeasibilityTests(unittest.TestCase):
    def test_unchecked_feasibility_is_not_a_failure_but_drags_score(self):
        report = evaluate_guide(_guide(feasibility={
            "checked": False, "score": 100, "level": "A", "issues": [], "notes": [],
        }))
        self.assertEqual(report["dimensions"]["feasibility"]["score"], 65)
        self.assertTrue(any("无法判断" in issue for issue in report["issues"]))

    def test_missing_report_is_flagged(self):
        guide = _guide()
        guide.feasibility = {}
        report = evaluate_guide(guide)
        self.assertEqual(report["dimensions"]["feasibility"]["score"], 60)

    def test_feasibility_issues_are_propagated(self):
        report = evaluate_guide(_guide(feasibility={
            "checked": True, "score": 60, "level": "C",
            "issues": ["第1天第1段通勤约1069公里，当天往返明显吃紧。"],
            "notes": [],
        }))
        self.assertEqual(report["dimensions"]["feasibility"]["score"], 60)
        self.assertTrue(any("1069" in issue for issue in report["issues"]))


class ScoreShapeTests(unittest.TestCase):
    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0)

    def test_score_stays_in_range_and_has_all_dimensions(self):
        for guide in (_guide(), _guide(spots=[]), _guide(spots=_spots(verified=False))):
            report = evaluate_guide(guide)
            self.assertGreaterEqual(report["score"], 0)
            self.assertLessEqual(report["score"], 100)
            self.assertEqual(set(report["dimensions"]), set(WEIGHTS))
            self.assertIn(report["grade"], {"A", "B", "C", "D"})
            self.assertTrue(report["notes"])

    def test_grade_thresholds(self):
        self.assertEqual(_grade(90), "A")
        self.assertEqual(_grade(75), "B")
        self.assertEqual(_grade(60), "C")
        self.assertEqual(_grade(40), "D")

    def test_issues_are_deduplicated(self):
        report = evaluate_guide(_guide(spots=[], feasibility={}))
        self.assertEqual(len(report["issues"]), len(set(report["issues"])))


if __name__ == "__main__":
    unittest.main()
