import asyncio
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

from config import AmapConfig
from models.schemas import DayPlan, RoutePlan, TravelIntent
from tools.amap_settings import AmapSettingsError, AmapSettingsPayload, AmapSettingsStore
from tools.amap_utils import amap_sign, with_sig
from tools.enrich import _poi_name_matches, _poi_search, _poi_city_matches, _parse_coordinate
from tools.weather import get_weather
from orchestrator_llm import _weather_targets


class MemoryCredentials:
    def __init__(self):
        self.available = True
        self.values = {}
        self.set_calls = 0
        self.fail_on_call = None

    def get(self, name):
        return self.values.get(name)

    def set(self, name, value):
        self.set_calls += 1
        self.values[name] = value
        if self.set_calls == self.fail_on_call:
            raise AmapSettingsError("模拟凭据保存失败")

    def delete(self, name):
        self.values.pop(name, None)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.calls.append((url, params or {}))
        return FakeResponse(self.responses.pop(0))


class AmapSignatureTests(unittest.TestCase):
    def test_signs_raw_utf8_values_before_http_url_encoding(self):
        params = {"keywords": "A+B 安阳", "z": 2, "key": "web-key"}
        expected = hashlib.md5("key=web-key&keywords=A+B 安阳&z=2private".encode("utf-8")).hexdigest()
        self.assertEqual(amap_sign(params, "private"), expected)
        self.assertEqual(with_sig({"keywords": "A+B 安阳"}, "web-key", "private")["sig"],
                         hashlib.md5("key=web-key&keywords=A+B 安阳private".encode("utf-8")).hexdigest())


class AmapSettingsTests(unittest.TestCase):
    def test_secrets_are_in_credential_store_and_not_json_or_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials = MemoryCredentials()
            store = AmapSettingsStore(Path(temp_dir) / "amap.json", credentials)
            store.save(AmapSettingsPayload(
                js_api_key="js-secret", js_security_code="js-code",
                web_service_key="rest-secret", web_service_secret="sign-secret",
            ))
            contents = store.path.read_text(encoding="utf-8")
            for secret in ("js-secret", "js-code", "rest-secret", "sign-secret"):
                self.assertNotIn(secret, contents)
            status = store.public_status(AmapConfig())
            self.assertTrue(status["has_js_api_key"])
            self.assertTrue(status["has_web_service_secret"])
            self.assertNotIn("js-secret", json.dumps(status))
            resolved = store.resolve(AmapConfig())
            self.assertEqual(resolved.web_key, "rest-secret")
            self.assertEqual(resolved.js_security_code, "js-code")

    def test_api_returns_only_the_browser_pair_and_never_echoes_values_in_status(self):
        import app as app_module
        from fastapi.testclient import TestClient

        with tempfile.TemporaryDirectory() as temp_dir:
            credentials = MemoryCredentials()
            store = AmapSettingsStore(Path(temp_dir) / "amap.json", credentials)
            store.save(AmapSettingsPayload(
                js_api_key="browser-js-key", js_security_code="browser-js-code",
                web_service_key="server-web-key", web_service_secret="server-signature",
            ))
            client = TestClient(app_module.app, base_url="http://127.0.0.1")
            with patch.object(app_module, "amap_settings", store):
                config_response = client.get("/api/config")
                status_response = client.get("/api/amap-settings")
            self.assertEqual(config_response.status_code, 200)
            self.assertEqual(config_response.json(), {
                "amap_key": "browser-js-key", "amap_security_code": "browser-js-code"
            })
            self.assertEqual(status_response.status_code, 200)
            status_text = status_response.text
            for secret in ("browser-js-key", "browser-js-code", "server-web-key", "server-signature"):
                self.assertNotIn(secret, status_text)

    def test_save_rolls_back_all_attempted_credentials_after_first_or_second_set_failure(self):
        for failure_offset in (1, 2):
            with self.subTest(failure_offset=failure_offset), tempfile.TemporaryDirectory() as temp_dir:
                credentials = MemoryCredentials()
                store = AmapSettingsStore(Path(temp_dir) / "amap.json", credentials)
                store.save(AmapSettingsPayload(
                    js_api_key="old-js", web_service_key="old-web",
                    web_service_secret="untouched-secret",
                ))
                credentials.fail_on_call = credentials.set_calls + failure_offset
                with self.assertRaises(AmapSettingsError):
                    store.save(AmapSettingsPayload(js_api_key="new-js", web_service_key="new-web"))
                self.assertEqual(credentials.values["js_api_key"], "old-js")
                self.assertEqual(credentials.values["web_service_key"], "old-web")
                self.assertEqual(credentials.values["web_service_secret"], "untouched-secret")


class PoiValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_exact_city_matched_poi_is_selected_after_an_attached_poi(self):
        client = FakeHttpClient([{
            "status": "1",
            "pois": [
                {"name": "天安门停车场", "cityname": "北京市", "adname": "东城区", "location": "116.4,39.9"},
                {"name": "天安门", "cityname": "北京市", "adname": "东城区", "location": "116.397,39.908"},
            ],
        }])
        config = AmapConfig(web_key="web-key", web_secret="sign-key")
        result = await _poi_search(client, "天安门", "北京", config)
        self.assertEqual(result["coordinate"], [116.397, 39.908])
        request_params = client.calls[0][1]
        self.assertEqual(request_params["region"], "北京")
        self.assertEqual(request_params["city_limit"], "true")
        self.assertNotIn("city", request_params)

    async def test_wrong_city_and_out_of_china_coordinates_are_rejected(self):
        wrong_city = FakeHttpClient([{
            "status": "1",
            "pois": [{"name": "西湖", "cityname": "杭州市", "adname": "西湖区", "location": "120.1,30.2"}],
        }])
        self.assertIsNone(await _poi_search(wrong_city, "西湖", "北京", AmapConfig(web_key="k")))
        bad_coordinate = FakeHttpClient([{
            "status": "1",
            "pois": [{"name": "西湖", "cityname": "杭州市", "adname": "西湖区", "location": "181,91"}],
        }])
        self.assertIsNone(await _poi_search(bad_coordinate, "西湖", "杭州", AmapConfig(web_key="k")))
        self.assertFalse(_poi_name_matches("故宫博物院", "故宫博物院公交站"))
        self.assertFalse(_poi_name_matches("天安门", "天安门停车场"))
        self.assertTrue(_poi_name_matches("天安门", "天安门"))
        self.assertFalse(_poi_city_matches("北京", {"cityname": "杭州市", "adname": "朝阳区"}))
        self.assertIsNone(_parse_coordinate("1,200"))


class WeatherDateTests(unittest.IsolatedAsyncioTestCase):
    async def test_weather_is_filtered_to_exact_requested_route_days(self):
        fake_client = FakeHttpClient([
            {"status": "1", "districts": [{"name": "安阳市", "adcode": "410500"}]},
            {"status": "1", "forecasts": [{
                "city": "安阳市", "province": "河南省", "reporttime": "2026-10-20 11:00:00",
                "casts": [
                    {"date": "2026-10-20", "week": "2", "dayweather": "晴", "daytemp": "20", "nighttemp": "11"},
                    {"date": "2026-10-21", "week": "3", "dayweather": "阴", "daytemp": "18", "nighttemp": "10"},
                    {"date": "2026-10-22", "week": "4", "dayweather": "小雨", "daytemp": "16", "nighttemp": "9"},
                ],
            }]},
        ])
        with patch("tools.weather.httpx.AsyncClient", return_value=fake_client):
            result = await get_weather(
                "安阳", config=AmapConfig(web_key="web-key"),
                travel_dates=[date(2026, 10, 21), date(2026, 10, 23)],
            )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["requested_dates"], ["2026-10-21", "2026-10-23"])
        self.assertEqual([day["date"] for day in result["forecast"]], ["2026-10-21"])
        self.assertEqual(result["forecast"][0]["dayweather"], "阴")
        self.assertEqual(result["reporttime"], "2026-10-20 11:00:00")

    async def test_missing_date_or_credentials_never_calls_weather_api(self):
        with patch("tools.weather.httpx.AsyncClient") as client_factory:
            result = await get_weather("安阳", config=AmapConfig(web_key="web-key"))
            self.assertEqual(result["status"], "date_required")
            result = await get_weather("安阳", date(2026, 10, 21), config=AmapConfig())
            self.assertEqual(result["status"], "no_key")
            client_factory.assert_not_called()


class RouteWeatherTargetTests(unittest.TestCase):
    def test_province_destination_uses_actual_daily_cities_and_dates(self):
        intent = TravelIntent(destinations=["云南"], days=3, travel_date="2026-10-21")
        route = RoutePlan(
            cities=["云南"],
            daily_plan=[
                DayPlan(day=1, city="昆明"),
                DayPlan(day=2, city="大理"),
                DayPlan(day=3, city="丽江"),
            ],
        )
        self.assertEqual(_weather_targets(route, intent), [
            ("昆明", [date(2026, 10, 21)]),
            ("大理", [date(2026, 10, 22)]),
            ("丽江", [date(2026, 10, 23)]),
        ])


class AmapFailureFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_map_credential_read_failure_keeps_langchain_text_generation_available(self):
        from orchestrator_llm import TravelOrchestrator

        intent = TravelIntent(
            destinations=["安阳"], days=1, travel_date="2026-10-21"
        )
        route = RoutePlan(cities=["安阳"], daily_plan=[DayPlan(day=1, city="安阳")])
        empty_map_config = AmapConfig(web_key="", web_secret="", js_key="", js_security_code="")
        warning = "高德配置无法读取，本次未调用地图、POI 或天气服务；文本攻略仍可生成。"

        with patch("orchestrator_llm.LLMClient", return_value=object()), \
             patch("tools.weather.httpx.AsyncClient") as weather_client, \
             tempfile.TemporaryDirectory() as temp_dir:
            orchestrator = TravelOrchestrator(
                amap_config=empty_map_config, amap_config_warning=warning
            )
            orchestrator.intent_parser.run = AsyncMock(return_value=intent)
            orchestrator.route_planner.run = AsyncMock(return_value=route)
            orchestrator.attraction_recommender.run = AsyncMock(return_value=[])
            orchestrator.culture_engine.run = AsyncMock(return_value=[])
            with patch("tools.enrich.PHOTO_DIR", Path(temp_dir)), \
                 patch("tools.enrich.INDEX_FILE", Path(temp_dir) / "index.json"):
                guide = await orchestrator.generate(
                    "安阳", request_overrides={
                        "destinations": ["安阳"], "days": 1,
                        "travel_date": "2026-10-21",
                    }
                )
        self.assertEqual(guide.weather[0]["status"], "no_key")
        self.assertIn(warning, guide.route.warnings)
        self.assertFalse(guide.amap_ready)
        weather_client.return_value.get.assert_not_called()

    def test_request_orchestrator_uses_empty_map_snapshot_when_saved_credentials_cannot_be_read(self):
        import app as app_module
        from config import ModelConfig

        class BrokenAmapSettings:
            def resolve(self, environment):
                raise AmapSettingsError("credential read failure")

        with patch.object(app_module, "resolve_model_config", return_value=ModelConfig()), \
             patch.object(app_module, "amap_settings", BrokenAmapSettings()), \
             patch.object(app_module, "TravelOrchestrator") as factory:
            app_module._request_orchestrator(app_module.GenReq(query="安阳"))
        kwargs = factory.call_args.kwargs
        self.assertEqual(kwargs["amap_config"].web_key, "")
        self.assertEqual(kwargs["amap_config"].js_key, "")
        self.assertTrue(kwargs["amap_config_warning"])


if __name__ == "__main__":
    unittest.main()
