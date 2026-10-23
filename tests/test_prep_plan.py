"""第13轮：行前清单与天气备选方案。"""

import unittest

from models.schemas import Activity, DayPlan, RoutePlan, TravelIntent
from tools.prep_plan import build_prep_plan


def _route(cities: list[str], start_day: int = 1) -> RoutePlan:
    return RoutePlan(
        route_name="测试行程",
        cities=cities,
        daily_plan=[
            DayPlan(day=index + start_day, city=city, morning=Activity(name=f"{city}博物馆"))
            for index, city in enumerate(cities)
        ],
    )


def _weather(city: str, date_value: str, day: str, night: str,
             high: str = "25", low: str = "15", wind: str = "1-3") -> dict:
    return {
        "status": "ok",
        "city": city,
        "forecast": [{
            "date": date_value,
            "dayweather": day,
            "nightweather": night,
            "daytemp": high,
            "nighttemp": low,
            "daypower": wind,
        }],
    }


class WeatherPlanTests(unittest.TestCase):
    def test_rainy_day_gets_indoor_fallback(self):
        route = _route(["北京"])
        intent = TravelIntent(destinations=["北京"], days=1, travel_date="2026-11-01")
        weather = [_weather("北京", "2026-11-01", "小雨", "阴")]
        plan = build_prep_plan(route, intent, weather)
        day = plan["weather_plans"][0]
        self.assertEqual(day["status"], "ok")
        self.assertIn("小雨", day["weather"])
        self.assertTrue(any("室内" in advice for advice in day["advice"]))

    def test_heavy_rain_adds_closure_warning(self):
        route = _route(["北京"])
        intent = TravelIntent(destinations=["北京"], days=1, travel_date="2026-11-01")
        weather = [_weather("北京", "2026-11-01", "暴雨", "大雨")]
        plan = build_prep_plan(route, intent, weather)
        advice = " ".join(plan["weather_plans"][0]["advice"])
        self.assertIn("较强降水", advice)

    def test_hot_day_moves_outdoor_activity_away_from_noon(self):
        route = _route(["重庆"])
        intent = TravelIntent(destinations=["重庆"], days=1, travel_date="2026-08-01")
        weather = [_weather("重庆", "2026-08-01", "晴", "晴", high="38", low="29")]
        plan = build_prep_plan(route, intent, weather)
        advice = " ".join(plan["weather_plans"][0]["advice"])
        self.assertIn("正午", advice)

    def test_strong_wind_warns_about_cable_cars(self):
        route = _route(["黄山"])
        intent = TravelIntent(destinations=["黄山"], days=1, travel_date="2026-11-01")
        weather = [_weather("黄山", "2026-11-01", "多云", "多云", wind="7")]
        plan = build_prep_plan(route, intent, weather)
        advice = " ".join(plan["weather_plans"][0]["advice"])
        self.assertIn("索道", advice)

    def test_clear_day_keeps_plan(self):
        route = _route(["北京"])
        intent = TravelIntent(destinations=["北京"], days=1, travel_date="2026-11-01")
        weather = [_weather("北京", "2026-11-01", "晴", "晴")]
        plan = build_prep_plan(route, intent, weather)
        advice = " ".join(plan["weather_plans"][0]["advice"])
        self.assertIn("按原计划", advice)

    def test_city_suffix_still_matches_forecast(self):
        route = _route(["北京市"])
        intent = TravelIntent(destinations=["北京市"], days=1, travel_date="2026-11-01")
        weather = [_weather("北京", "2026-11-01", "小雨", "阴")]
        plan = build_prep_plan(route, intent, weather)
        self.assertEqual(plan["weather_plans"][0]["status"], "ok")

    def test_identical_day_and_night_weather_is_not_repeated(self):
        """昼夜间同一天气时不要显示成“晴晴”。"""
        route = _route(["北京"])
        intent = TravelIntent(destinations=["北京"], days=1, travel_date="2026-11-01")
        weather = [_weather("北京", "2026-11-01", "晴", "晴")]
        plan = build_prep_plan(route, intent, weather)
        self.assertEqual(plan["weather_plans"][0]["weather"], "晴")

    def test_different_day_and_night_weather_reads_as_transition(self):
        route = _route(["北京"])
        intent = TravelIntent(destinations=["北京"], days=1, travel_date="2026-11-01")
        weather = [_weather("北京", "2026-11-01", "小雨", "阴")]
        plan = build_prep_plan(route, intent, weather)
        self.assertEqual(plan["weather_plans"][0]["weather"], "小雨转阴")

    def test_missing_forecast_is_marked_per_day(self):
        route = _route(["北京", "天津"])
        intent = TravelIntent(destinations=["北京", "天津"], days=2, travel_date="2026-11-01")
        weather = [_weather("北京", "2026-11-01", "晴", "晴")]
        plan = build_prep_plan(route, intent, weather)
        self.assertEqual(plan["weather_plans"][0]["status"], "ok")
        self.assertEqual(plan["weather_plans"][1]["status"], "no_forecast")


class PackingTests(unittest.TestCase):
    def test_cold_weather_recommends_winter_gear(self):
        route = _route(["哈尔滨"])
        intent = TravelIntent(destinations=["哈尔滨"], days=2, travel_date="2027-01-05")
        weather = [
            _weather("哈尔滨", "2027-01-05", "晴", "晴", high="-8", low="-20"),
            _weather("哈尔滨", "2027-01-06", "晴", "晴", high="-6", low="-18"),
        ]
        plan = build_prep_plan(route, intent, weather)
        clothing = plan["packing"][0]
        self.assertEqual(clothing["group"], "衣物")
        self.assertTrue(any("羽绒服" in item for item in clothing["items"]))
        self.assertEqual(plan["temperature_range"], {"low": -20, "high": -6})

    def test_unknown_temperature_does_not_assume_spring_conditions(self):
        plan = build_prep_plan(_route(["北京"]), TravelIntent(destinations=["北京"], days=1), [])
        self.assertIsNone(plan["temperature_range"])
        basis = plan["packing"][0]["basis"]
        self.assertIn("没有可用温度预报", basis)
        self.assertTrue(any("未给出温度型穿衣结论" in note for note in plan["notes"]))
        self.assertFalse(any("15~25" in str(item) for item in plan["packing"]))

    def test_airline_battery_policy_is_left_for_current_rules(self):
        plan = build_prep_plan(_route(["北京"]), TravelIntent(destinations=["北京"], days=1), [])
        electronic = next(group for group in plan["packing"] if group["group"] == "随身与电子")
        text = " ".join(electronic["items"])
        self.assertIn("航司", text)
        self.assertIn("出发机场当日规定", text)
        self.assertNotIn("低于 100Wh", text)

    def test_no_climbing_preparation_is_a_reminder_not_a_claim_of_compliance(self):
        intent = TravelIntent(destinations=["杭州"], days=1, constraints=["不爬山"])
        plan = build_prep_plan(_route(["杭州"]), intent, [])
        items = next(group["items"] for group in plan["packing"] if group["group"] == "按你的条件补充")
        text = " ".join(items)
        self.assertIn("核对每日点位", text)
        self.assertNotIn("行程已避开", text)

    def test_child_trip_adds_child_items(self):
        intent = TravelIntent(
            destinations=["成都"], days=3, travelers=3, companion="亲子",
            preferences=["亲子"], constraints=["不爬山"],
        )
        plan = build_prep_plan(_route(["成都"] * 3), intent, [])
        group = next(item for item in plan["packing"] if item["group"] == "按你的条件补充")
        text = " ".join(group["items"])
        self.assertIn("儿童", text)
        self.assertIn("防滑鞋", text)

    def test_low_mobility_adds_accessibility_items(self):
        intent = TravelIntent(
            destinations=["杭州"], days=2, travelers=2, constraints=["少走路", "轮椅"],
        )
        plan = build_prep_plan(_route(["杭州"] * 2), intent, [])
        group = next(item for item in plan["packing"] if item["group"] == "按你的条件补充")
        text = " ".join(group["items"])
        self.assertIn("无障碍", text)

    def test_no_special_conditions_omits_extra_group(self):
        intent = TravelIntent(destinations=["北京"], days=1)
        plan = build_prep_plan(_route(["北京"]), intent, [])
        groups = [item["group"] for item in plan["packing"]]
        self.assertNotIn("按你的条件补充", groups)
        self.assertIn("证件与预订", groups)
        self.assertIn("健康与护理", groups)

    def test_notes_carry_verification_boundary(self):
        plan = build_prep_plan(_route(["北京"]), TravelIntent(destinations=["北京"], days=1), [])
        text = " ".join(plan["notes"])
        self.assertIn("出发前 1 天", text)
        self.assertIn("室内备选只给类别", text)


if __name__ == "__main__":
    unittest.main()
