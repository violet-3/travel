"""Offline checks for route consistency, honest budget estimates, and hard constraints."""

import unittest

from agents.guide_generator import GuideGenerator
from models.schemas import (
    CultureData, DayPlan, RoutePlan, Spot, TravelIntent, Transport,
)
from tools.route_validation import validate_hard_constraints, validate_route_plan


class RouteConsistencyTests(unittest.TestCase):
    def test_missing_explicit_city_and_unscheduled_route_city_are_reported(self):
        intent = TravelIntent(destinations=["上海"], days=1)
        route = RoutePlan(
            cities=["安阳", "洛阳"],
            daily_plan=[DayPlan(day=1, city="安阳")],
        )
        warnings = validate_route_plan(intent, route)
        self.assertTrue(any("上海" in warning and "未明确覆盖" in warning for warning in warnings))
        self.assertTrue(any("洛阳" in warning and "未安排到每日行程" in warning for warning in warnings))

    def test_wrong_day_numbers_are_corrected_and_missing_city_link_is_added_unknown(self):
        intent = TravelIntent(destinations=["安阳", "洛阳"], days=2)
        route = RoutePlan(
            cities=["安阳", "洛阳"],
            daily_plan=[DayPlan(day=2, city="安阳"), DayPlan(day=5, city="洛阳")],
        )
        warnings = validate_route_plan(intent, route)
        self.assertEqual([day.day for day in route.daily_plan], [1, 2])
        self.assertTrue(any("重新编号" in warning for warning in warnings))
        self.assertEqual(len(route.transport), 1)
        self.assertEqual(route.transport[0].cost_est, None)
        self.assertTrue(any("安阳→洛阳" in warning and "待核价" in warning for warning in warnings))

    def test_repeated_city_transitions_are_counted_as_separate_segments(self):
        intent = TravelIntent(destinations=["安阳", "洛阳"], days=4)
        route = RoutePlan(
            cities=["安阳", "洛阳"],
            daily_plan=[
                DayPlan(day=1, city="安阳"), DayPlan(day=2, city="洛阳"),
                DayPlan(day=3, city="安阳"), DayPlan(day=4, city="洛阳"),
            ],
            transport=[
                Transport(**{"from": "安阳", "to": "洛阳", "cost_est": 100}),
                Transport(**{"from": "洛阳", "to": "安阳", "cost_est": 120}),
            ],
        )
        warnings = validate_route_plan(intent, route)
        self.assertEqual(len(route.transport), 3)
        self.assertIsNone(route.transport[-1].cost_est)
        self.assertTrue(any("安阳→洛阳" in warning and "未提供" in warning for warning in warnings))

    def test_city_suffix_variants_match_without_duplicate_transport(self):
        intent = TravelIntent(destinations=["安阳", "洛阳"], days=2)
        route = RoutePlan(
            cities=["安阳", "洛阳"],
            daily_plan=[DayPlan(day=1, city="安阳"), DayPlan(day=2, city="洛阳")],
            transport=[Transport(**{"from": "安阳市", "to": "洛阳市", "cost_est": 100})],
        )
        warnings = validate_route_plan(intent, route)
        self.assertEqual(len(route.transport), 1)
        self.assertFalse(any("未提供" in warning or "待核价" in warning for warning in warnings))


class HonestBudgetTests(unittest.TestCase):
    def test_same_day_trip_has_zero_lodging_and_no_fixed_transport_addition(self):
        route = RoutePlan(
            route_name="西安一日游", cities=["西安"], daily_plan=[DayPlan(day=1, city="西安")]
        )
        request = TravelIntent(
            destinations=["西安"], days=1, travelers=2, departure_city="西安"
        )
        guide = GuideGenerator().compile(route, [], [], intent=request)
        self.assertEqual(guide.budget.nights, 0)
        self.assertEqual(guide.budget.accommodation, 0)
        self.assertEqual(guide.budget.transport, 0)
        self.assertEqual(guide.budget.group_total, guide.budget.total * 2)
        self.assertEqual(guide.budget.transport_unknown_segments, [])

    def test_group_total_budget_is_compared_with_known_group_costs(self):
        route = RoutePlan(
            route_name="西安两日游", cities=["西安"],
            daily_plan=[DayPlan(day=1, city="西安"), DayPlan(day=2, city="西安")],
        )
        request = TravelIntent(
            destinations=["西安"], days=2, travelers=2, departure_city="北京",
            budget=1000, budget_scope="total",
        )
        guide = GuideGenerator().compile(route, [], [], intent=request)
        self.assertEqual(guide.budget.nights, 1)
        # 中等档基准 250/晚，西安按 1.15 城市系数折算为 288。
        self.assertEqual(guide.budget.accommodation, 288)
        self.assertEqual(guide.budget.transport, 0)
        # 该场景没有安排可匹配景点，因此不再虚构“每天至少¥100”门票。
        self.assertEqual(guide.budget.total, 548)
        self.assertEqual(guide.budget.group_total, 1096)
        self.assertEqual(guide.budget.budget_status, "over_known_budget")
        self.assertTrue(any("已超过需求预算" in warning for warning in guide.route.warnings))

    def test_missing_intercity_cost_stays_out_of_subtotal_and_markdown_says_pending(self):
        route = RoutePlan(
            route_name="安阳洛阳两日游", cities=["安阳", "洛阳"],
            daily_plan=[DayPlan(day=1, city="安阳"), DayPlan(day=2, city="洛阳")],
        )
        request = TravelIntent(destinations=["安阳", "洛阳"], days=2, travelers=2)
        validate_route_plan(request, route)
        guide = GuideGenerator().compile(route, [], [], intent=request)
        self.assertEqual(guide.budget.transport, 0)
        self.assertTrue(any("安阳→洛阳" in value for value in guide.budget.transport_unknown_segments))
        self.assertEqual(guide.budget.budget_status, "needs_transport_quote")
        markdown = GuideGenerator().to_markdown(guide)
        self.assertIn("待核价", markdown)
        self.assertIn("2人团体已知小计", markdown)
        self.assertIn("不含任何待核价交通段", markdown)

    def test_quoted_outbound_and_return_legs_are_not_duplicated_as_unknown(self):
        route = RoutePlan(
            route_name="上海安阳往返", cities=["安阳"],
            daily_plan=[DayPlan(day=1, city="安阳"), DayPlan(day=2, city="安阳")],
            transport=[
                Transport(**{"from": "上海", "to": "安阳市", "cost_est": 500}),
                Transport(**{"from": "安阳", "to": "上海", "cost_est": 520}),
            ],
        )
        request = TravelIntent(
            destinations=["安阳"], days=2, travelers=1, departure_city="上海"
        )
        guide = GuideGenerator().compile(route, [], [], intent=request)
        self.assertEqual(guide.budget.transport, 1020)
        self.assertEqual(guide.budget.transport_unknown_segments, [])

        partial_route = route.model_copy(deep=True)
        partial_route.transport = partial_route.transport[:1]
        partial = GuideGenerator().compile(partial_route, [], [], intent=request)
        self.assertEqual(partial.budget.transport, 500)
        self.assertEqual(len(partial.budget.transport_unknown_segments), 1)
        self.assertIn("安阳→上海", partial.budget.transport_unknown_segments[0])


class HardConstraintReviewTests(unittest.TestCase):
    def test_clear_climb_and_spicy_conflicts_are_warned_and_not_claimed_satisfied(self):
        request = TravelIntent(
            destinations=["西安"], days=1, constraints=["不爬山", "少走路", "不辣"]
        )
        route = RoutePlan(
            cities=["西安"], daily_plan=[
                DayPlan(day=1, city="西安", morning={"name": "华山登顶徒步"})
            ]
        )
        foods = [CultureData(city="西安", cuisine={
            "must_eat": [{"name": "麻辣牛肉", "tips": "本次推荐特色辣味菜"}]
        })]
        warnings = validate_hard_constraints(request, route, [Spot(name="兵马俑")], foods)
        self.assertTrue(any("违反“不爬山/不徒步”" in warning for warning in warnings))
        self.assertTrue(any("可能违反“不辣”" in warning for warning in warnings))
        self.assertTrue(any("本地只检查了明显关键词冲突" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
