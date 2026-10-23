"""第11轮：预算可信度 —— 门票按实际地点累加，住宿按城市等级折算。"""

import unittest

from agents.guide_generator import GuideGenerator
from models.schemas import Activity, DayPlan, RoutePlan, Spot, Transport, TravelIntent


def _day(number: int, city: str, morning="", afternoon="", evening="") -> DayPlan:
    return DayPlan(
        day=number,
        city=city,
        morning=Activity(name=morning),
        afternoon=Activity(name=afternoon),
        evening=Activity(name=evening),
    )


class TicketEstimateTests(unittest.TestCase):
    def setUp(self):
        self.gen = GuideGenerator()

    def test_tickets_follow_listed_spot_prices(self):
        """有标价的景点按各自门票累加，不再按天数拍 100。"""
        route = RoutePlan(
            route_name="安阳两日",
            cities=["安阳"],
            daily_plan=[
                _day(1, "安阳", morning="殷墟", afternoon="中国文字博物馆"),
                _day(2, "安阳", morning="太行大峡谷"),
            ],
        )
        spots = [
            Spot(name="殷墟", city="安阳", ticket=70),
            Spot(name="中国文字博物馆", city="安阳", ticket=0),
            Spot(name="太行大峡谷", city="安阳", ticket=120),
        ]
        guide = self.gen.compile(route, spots, [], intent=TravelIntent(destinations=["安阳"], days=2))

        # 正价可读作模型参考价；旧格式 ticket=0 仍是未知，不能误判免费。
        self.assertEqual(guide.budget.tickets_known, 190)
        self.assertEqual(guide.budget.tickets_estimated, 100)
        self.assertEqual(guide.budget.tickets, 290)
        self.assertIn("安阳 · 中国文字博物馆", guide.budget.tickets_pending_spots)
        self.assertNotIn("安阳 · 殷墟", guide.budget.tickets_pending_spots)

    def test_only_exact_generic_activities_are_exempt_from_unpriced_list(self):
        """只豁免完整的通用活动名，不吞掉带地名的潜在景点。"""
        route = RoutePlan(
            route_name="安阳两日", cities=["安阳"],
            daily_plan=[_day(1, "安阳", morning="早餐", afternoon="散步")],
        )
        guide = self.gen.compile(route, [], [], intent=TravelIntent(destinations=["安阳"], days=1))
        self.assertEqual(guide.budget.tickets_known, 0)
        self.assertEqual(guide.budget.tickets_estimated, 0)
        self.assertEqual(guide.budget.tickets_pending_spots, [])
        self.assertEqual(guide.budget.tickets_unpriced_activities, [])

    def test_named_attraction_containing_generic_activity_word_is_unpriced(self):
        route = RoutePlan(
            route_name="苏州一日", cities=["苏州"],
            daily_plan=[_day(1, "苏州", morning="拙政园散步")],
        )
        guide = self.gen.compile(
            route, [], [], intent=TravelIntent(destinations=["苏州"], days=1)
        )
        self.assertEqual(guide.budget.tickets, 0)
        self.assertEqual(guide.budget.tickets_unpriced_activities, ["苏州 · 拙政园散步"])

    def test_unmatched_potential_activity_is_not_charged_but_budget_is_marked_incomplete(self):
        route = RoutePlan(
            route_name="安阳一日", cities=["安阳"],
            daily_plan=[_day(1, "安阳", morning="古城遗址")],
        )
        guide = self.gen.compile(
            route, [], [], intent=TravelIntent(
                destinations=["安阳"], days=1, budget=3000, departure_city="安阳"
            )
        )
        self.assertEqual(guide.budget.tickets, 0)
        self.assertEqual(guide.budget.tickets_unpriced_activities, ["安阳 · 古城遗址"])
        self.assertEqual(guide.budget.budget_status, "needs_price_review")
        self.assertTrue(any("小计不能视为完整总额" in note for note in guide.budget.estimate_notes))

    def test_activity_prefix_is_removed_before_exact_city_name_match(self):
        route = RoutePlan(
            route_name="北京一日", cities=["北京"],
            daily_plan=[_day(1, "北京", morning="参观故宫")],
        )
        guide = self.gen.compile(
            route, [Spot(name="故宫", city="北京", ticket=60)], [],
            intent=TravelIntent(destinations=["北京"], days=1),
        )
        self.assertEqual(guide.budget.tickets_known, 60)
        self.assertEqual(guide.budget.tickets_unpriced_activities, [])

    def test_no_itinerary_detail_does_not_invent_ticket_costs(self):
        """缺少行程地点时不再按天数推定门票。"""
        route = RoutePlan(
            route_name="安阳三日", cities=["安阳"],
            daily_plan=[DayPlan(day=index + 1, city="安阳") for index in range(3)],
        )
        guide = self.gen.compile(route, [], [], intent=TravelIntent(destinations=["安阳"], days=3))
        self.assertEqual(guide.budget.tickets, 0)
        self.assertEqual(guide.budget.tickets_known, 0)
        self.assertEqual(guide.budget.tickets_pending_spots, [])

    def test_repeated_spot_is_only_charged_once(self):
        route = RoutePlan(
            route_name="安阳两日", cities=["安阳"],
            daily_plan=[
                _day(1, "安阳", morning="殷墟", evening="殷墟"),
                _day(2, "安阳", morning="殷墟"),
            ],
        )
        spots = [Spot(name="殷墟", city="安阳", ticket=70)]
        guide = self.gen.compile(route, spots, [], intent=TravelIntent(destinations=["安阳"], days=2))
        self.assertEqual(guide.budget.tickets_known, 70)

    def test_explicitly_free_spot_is_not_charged_or_estimated(self):
        route = RoutePlan(
            route_name="安阳一日", cities=["安阳"],
            daily_plan=[_day(1, "安阳", morning="免费公园")],
        )
        spots = [Spot(name="免费公园", city="安阳", ticket=0, ticket_status="free")]
        guide = self.gen.compile(route, spots, [], intent=TravelIntent(destinations=["安阳"], days=1))
        self.assertEqual(guide.budget.tickets, 0)
        self.assertEqual(guide.budget.tickets_estimated, 0)
        self.assertEqual(guide.budget.tickets_free_spots, ["安阳 · 免费公园"])

    def test_ticket_matching_requires_same_city_and_exact_normalized_name(self):
        route = RoutePlan(
            route_name="苏州一日", cities=["苏州"],
            daily_plan=[_day(1, "苏州市", morning="公园")],
        )
        spots = [
            Spot(name="公园", city="北京", ticket=90),
            Spot(name="公园", city="苏州", ticket=70),
            Spot(name="公园博物馆", city="苏州", ticket=300),
        ]
        guide = self.gen.compile(route, spots, [], intent=TravelIntent(destinations=["苏州"], days=1))
        self.assertEqual(guide.budget.tickets, 70)
        self.assertEqual(guide.budget.tickets_known, 70)
        self.assertEqual(guide.budget.tickets_pending_spots, [])

    def test_duplicate_unknown_spot_is_counted_once_in_estimate_and_pending_list(self):
        route = RoutePlan(
            route_name="安阳一日", cities=["安阳"],
            daily_plan=[_day(1, "安阳", morning="新博物馆", afternoon="新博物馆")],
        )
        spots = [Spot(name="新博物馆", city="安阳", ticket=None)]
        guide = self.gen.compile(route, spots, [], intent=TravelIntent(destinations=["安阳"], days=1))
        self.assertEqual(guide.budget.tickets_estimated, 100)
        self.assertEqual(guide.budget.tickets_pending_spots, ["安阳 · 新博物馆"])

    def test_legacy_ticket_values_remain_readable(self):
        self.assertEqual(Spot.model_validate({"name": "旧免费字段", "city": "安阳", "ticket": 0}).ticket_status,
                         "unknown")
        self.assertEqual(Spot.model_validate({"name": "旧价格字段", "city": "安阳", "ticket": 70}).ticket_status,
                         "reference")


class LodgingTierTests(unittest.TestCase):
    def setUp(self):
        self.gen = GuideGenerator()

    def test_tier_factor_applies_to_overnight_city_only(self):
        """北京过夜按 1.5 系数，安阳按 0.8，不吃大锅饭。"""
        route = RoutePlan(
            route_name="北京安阳", cities=["北京", "安阳"],
            daily_plan=[_day(1, "北京"), _day(2, "安阳"), _day(3, "安阳")],
        )
        guide = self.gen.compile(route, [], [], intent=TravelIntent(destinations=["北京", "安阳"], days=3))
        # 中等档 250/晚：第1晚北京 375，第2晚安阳 200
        self.assertEqual(guide.budget.accommodation, 575)
        self.assertEqual(guide.budget.lodging_cities, ["北京", "安阳"])
        self.assertEqual(guide.budget.lodging_night_rate, 250)

    def test_unknown_city_keeps_base_rate(self):
        route = RoutePlan(
            route_name="某县城两日", cities=["某某县"],
            daily_plan=[_day(1, "某某县"), _day(2, "某某县")],
        )
        guide = self.gen.compile(route, [], [], intent=TravelIntent(destinations=["某某县"], days=2))
        self.assertEqual(guide.budget.accommodation, 250)
        self.assertTrue(any("平均每人每晚约¥250" in note for note in guide.budget.estimate_notes))

    def test_notes_state_the_actual_converted_nightly_rate(self):
        """北京 1.5 系数下要写清折算后的每晚价格，而不是只给基准价。"""
        route = RoutePlan(
            route_name="北京两日", cities=["北京"],
            daily_plan=[_day(1, "北京"), _day(2, "北京")],
        )
        guide = self.gen.compile(route, [], [], intent=TravelIntent(destinations=["北京"], days=2))
        # 两日游 1 晚：中等档 250 × 北京 1.5 = 375
        self.assertEqual(guide.budget.accommodation, 375)
        self.assertTrue(any("平均每人每晚约¥375" in note for note in guide.budget.estimate_notes))

    def test_city_suffix_is_normalized(self):
        """写成“北京市”也要命中北京系数。"""
        route = RoutePlan(
            route_name="北京两日", cities=["北京市"],
            daily_plan=[_day(1, "北京市"), _day(2, "北京市")],
        )
        guide = self.gen.compile(route, [], [], intent=TravelIntent(destinations=["北京市"], days=2))
        self.assertEqual(guide.budget.accommodation, 375)


class CostShareTests(unittest.TestCase):
    def setUp(self):
        self.gen = GuideGenerator()

    def test_share_sums_to_one(self):
        route = RoutePlan(
            route_name="安阳两日", cities=["安阳"],
            daily_plan=[_day(1, "安阳"), _day(2, "安阳")],
            transport=[Transport(**{"from": "北京", "to": "安阳", "cost_est": 200})],
        )
        guide = self.gen.compile(route, [], [], intent=TravelIntent(
            destinations=["安阳"], days=2, departure_city="北京",
        ))
        share = guide.budget.cost_share
        self.assertEqual(set(share), {"transport", "accommodation", "tickets", "food", "other"})
        self.assertAlmostEqual(sum(share.values()), 1.0, places=2)

    def test_high_transport_share_warns(self):
        route = RoutePlan(
            route_name="北京两日", cities=["北京"],
            daily_plan=[_day(1, "北京"), _day(2, "北京")],
            transport=[Transport(**{"from": "上海", "to": "北京", "cost_est": 5000})],
        )
        guide = self.gen.compile(route, [], [], intent=TravelIntent(
            destinations=["北京"], days=2, departure_city="上海",
        ))
        self.assertTrue(any("城际交通占人均已知费用" in warning for warning in guide.route.warnings))

    def test_markdown_shows_ticket_split_and_pending_names(self):
        route = RoutePlan(
            route_name="安阳两日", cities=["安阳"],
            daily_plan=[_day(1, "安阳", morning="殷墟", afternoon="小众展馆")],
        )
        spots = [
            Spot(name="殷墟", city="安阳", ticket=70),
            Spot(name="小众展馆", city="安阳", ticket=None),
        ]
        guide = self.gen.compile(route, spots, [], intent=TravelIntent(destinations=["安阳"], days=1))
        markdown = GuideGenerator().to_markdown(guide)
        self.assertIn("模型参考价 ¥70", markdown)
        self.assertIn("门票待核实：安阳 · 小众展馆", markdown)
        self.assertIn("门票金额来自模型参考或估算，未做官方核验", markdown)
        self.assertIn("费用结构", markdown)


if __name__ == "__main__":
    unittest.main()
