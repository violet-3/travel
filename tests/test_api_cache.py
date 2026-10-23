"""第15轮：Web 层的缓存接入 —— 命中要显式标注，强制刷新要真的重新生成。"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
from config import ModelConfig
from models.schemas import RoutePlan, TravelGuide
from tools.guide_cache import GuideCache
from tools.guide_history import GuideHistoryStore
from tools.amap_settings import AmapSettingsPayload


def _guide() -> TravelGuide:
    return TravelGuide(
        title="《安阳三日》",
        subtitle="安阳 · 3天2晚",
        destinations=["安阳"],
        days=3,
        route=RoutePlan(route_name="安阳三日", cities=["安阳"]),
    )


class CountingOrchestrator:
    def __init__(self, guide: TravelGuide):
        self.calls = 0
        self.llm_client = CountingCloseClient()
        self.model_config = ModelConfig(provider="deepseek", model="deepseek-chat",
                                        base_url="https://api.deepseek.com/v1")
        self._guide = guide

    async def generate(self, query, on_progress=None, request_overrides=None):
        self.calls += 1
        return self._guide.model_copy(deep=True)


class CountingCloseClient:
    def __init__(self):
        self.close_calls = 0

    async def aclose(self):
        self.close_calls += 1


class ApiCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cache = GuideCache(directory=Path(self.temp.name) / "cache", ttl_seconds=600)
        self.history = GuideHistoryStore(Path(self.temp.name) / "history.json")
        self.patchers = [
            patch.object(app, "guide_cache", self.cache),
            patch.object(app, "guide_history", self.history),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in self.patchers:
            patcher.stop()
        self.temp.cleanup()

    async def test_second_identical_request_is_served_from_cache(self):
        orchestrator = CountingOrchestrator(_guide())
        with patch.object(app, "_request_orchestrator", return_value=orchestrator):
            first = await app.api_generate(app.GenReq(query="安阳玩3天", days=3))
            second = await app.api_generate(app.GenReq(query="安阳玩3天", days=3))

        self.assertEqual(orchestrator.calls, 1, "第二次相同请求不应再调用模型")
        self.assertEqual(orchestrator.llm_client.close_calls, 1, "缓存命中要关闭未使用的客户端")
        self.assertFalse(first["cache_hit"])
        self.assertTrue(second["cache_hit"])
        self.assertIsNotNone(second["cache_age_seconds"])

    async def test_force_refresh_bypasses_cache(self):
        orchestrator = CountingOrchestrator(_guide())
        with patch.object(app, "_request_orchestrator", return_value=orchestrator):
            await app.api_generate(app.GenReq(query="安阳玩3天", days=3))
            refreshed = await app.api_generate(
                app.GenReq(query="安阳玩3天", days=3, force_refresh=True)
            )

        self.assertEqual(orchestrator.calls, 2)
        self.assertFalse(refreshed["cache_hit"])

    async def test_invalid_nonempty_cached_guide_falls_through_to_generation(self):
        import time
        from tools.guide_cache import CACHE_VERSION

        orchestrator = CountingOrchestrator(_guide())
        req = app.GenReq(query="安阳玩3天", days=3)
        key = app._cache_key_for(req, orchestrator)
        self.cache.directory.mkdir(parents=True, exist_ok=True)
        (self.cache.directory / f"{key}.json").write_text(json.dumps({
            "version": CACHE_VERSION,
            "saved_at": time.time(),
            "guide": {"title": "坏数据", "route": {"daily_plan": "not-a-list"}},
        }), encoding="utf-8")

        with patch.object(app, "_request_orchestrator", return_value=orchestrator):
            result = await app.api_generate(req)

        self.assertEqual(orchestrator.calls, 1)
        self.assertFalse(result["cache_hit"])
        self.assertEqual(result["title"], "《安阳三日》")

    async def test_cache_storage_exceptions_do_not_fail_successful_generation(self):
        class BrokenCache:
            def get(self, _key):
                raise OSError("read failed")

            def set(self, _key, _guide):
                raise OSError("write failed")

        orchestrator = CountingOrchestrator(_guide())
        with patch.object(app, "guide_cache", BrokenCache()), \
                patch.object(app, "_request_orchestrator", return_value=orchestrator):
            result = await app.api_generate(app.GenReq(query="安阳玩3天", days=3))

        self.assertEqual(orchestrator.calls, 1)
        self.assertFalse(result["cache_hit"])
        self.assertEqual(result["title"], "《安阳三日》")

    async def test_map_config_snapshot_changes_cache_namespace(self):
        req = app.GenReq(query="安阳玩3天", days=3)
        orchestrator = CountingOrchestrator(_guide())
        orchestrator.amap_config = type("Amap", (), {
            "web_key": "first-map-key", "web_secret": "signature",
        })()
        first_key = app._cache_key_for(req, orchestrator)
        orchestrator.amap_config = type("Amap", (), {
            "web_key": "second-map-key", "web_secret": "signature",
        })()
        second_key = app._cache_key_for(req, orchestrator)
        self.assertNotEqual(first_key, second_key)

    async def test_cache_key_uses_shanghai_day_only_when_query_has_no_explicit_date(self):
        from datetime import date

        orchestrator = CountingOrchestrator(_guide())
        relative_req = app.GenReq(query="明天去苏州", days=2)
        with patch.object(app, "shanghai_today", return_value=date(2026, 10, 23)):
            before_midnight = app._cache_key_for(relative_req, orchestrator)
        with patch.object(app, "shanghai_today", return_value=date(2026, 10, 24)):
            after_midnight = app._cache_key_for(relative_req, orchestrator)
        self.assertNotEqual(before_midnight, after_midnight)

        explicit_req = app.GenReq(
            query="苏州", travel_date=date(2026, 11, 1), days=2,
        )
        with patch.object(app, "shanghai_today", return_value=date(2026, 10, 23)):
            explicit_before = app._cache_key_for(explicit_req, orchestrator)
        with patch.object(app, "shanghai_today", return_value=date(2026, 10, 24)):
            explicit_after = app._cache_key_for(explicit_req, orchestrator)
        self.assertEqual(explicit_before, explicit_after)

    async def test_corrupt_cache_is_a_miss_for_stream_generation_too(self):
        import time
        from tools.guide_cache import CACHE_VERSION

        orchestrator = CountingOrchestrator(_guide())
        req = app.GenReq(query="安阳玩3天", days=3)
        key = app._cache_key_for(req, orchestrator)
        self.cache.directory.mkdir(parents=True, exist_ok=True)
        (self.cache.directory / f"{key}.json").write_text(json.dumps({
            "version": CACHE_VERSION,
            "saved_at": time.time(),
            "guide": {"title": "坏数据", "route": {"daily_plan": "not-a-list"}},
        }), encoding="utf-8")

        async def consume():
            response = await app.api_generate_stream(req, _RequestStub())
            return [json.loads(chunk) async for chunk in response.body_iterator]

        with patch.object(app, "_request_orchestrator", return_value=orchestrator):
            events = await consume()

        guide_events = [event for event in events if event.get("type") == "guide"]
        self.assertEqual(orchestrator.calls, 1)
        self.assertEqual(len(guide_events), 1)
        self.assertFalse(guide_events[0]["guide"]["cache_hit"])

    async def test_different_conditions_do_not_share_cache(self):
        orchestrator = CountingOrchestrator(_guide())
        with patch.object(app, "_request_orchestrator", return_value=orchestrator):
            await app.api_generate(app.GenReq(query="安阳玩3天", days=3))
            await app.api_generate(app.GenReq(query="安阳玩3天", days=3, travelers=2))

        self.assertEqual(orchestrator.calls, 2)

    async def test_cache_hit_still_creates_a_history_entry(self):
        orchestrator = CountingOrchestrator(_guide())
        with patch.object(app, "_request_orchestrator", return_value=orchestrator):
            first = await app.api_generate(app.GenReq(query="安阳玩3天", days=3))
            second = await app.api_generate(app.GenReq(query="安阳玩3天", days=3))

        self.assertTrue(first["history_saved"])
        self.assertTrue(second["history_saved"])
        self.assertNotEqual(first["history_id"], second["history_id"])
        self.assertEqual(len(self.history.list()), 2)

    async def test_stream_reports_cache_hit_as_progress_then_guide(self):
        orchestrator = CountingOrchestrator(_guide())

        async def consume():
            response = await app.api_generate_stream(
                app.GenReq(query="安阳玩3天", days=3), _RequestStub()
            )
            return [chunk async for chunk in response.body_iterator]

        with patch.object(app, "_request_orchestrator", return_value=orchestrator):
            await consume()
            chunks = await consume()

        events = [json.loads(chunk) for chunk in chunks]
        self.assertEqual(orchestrator.calls, 1)
        self.assertEqual(orchestrator.llm_client.close_calls, 1)
        self.assertTrue(any(event.get("stage") == "cache" for event in events))
        guide_events = [event for event in events if event.get("type") == "guide"]
        self.assertEqual(len(guide_events), 1)
        self.assertTrue(guide_events[0]["guide"]["cache_hit"])

    async def test_cache_status_and_clear_endpoints(self):
        orchestrator = CountingOrchestrator(_guide())
        with patch.object(app, "_request_orchestrator", return_value=orchestrator):
            await app.api_generate(app.GenReq(query="安阳玩3天", days=3))

        status = await app.cache_status()
        self.assertEqual(status["entries"], 1)
        self.assertEqual(status["fresh"], 1)

        cleared = await app.clear_cache()
        self.assertEqual(cleared["removed"], 1)
        self.assertEqual((await app.cache_status())["entries"], 0)

    async def test_successful_amap_save_and_clear_invalidate_cache(self):
        class SettingsStub:
            def __init__(self):
                self.save_calls = 0
                self.clear_calls = 0

            def save(self, _payload):
                self.save_calls += 1

            def clear(self):
                self.clear_calls += 1

            def public_status(self, _environment):
                return {"has_web_service_key": False}

        settings = SettingsStub()
        self.cache.set("f" * 40, app._guide_json(_guide()))
        with patch.object(app, "amap_settings", settings):
            await app.put_amap_settings(AmapSettingsPayload())
            self.assertEqual((await app.cache_status())["entries"], 0)
            self.cache.set("e" * 40, app._guide_json(_guide()))
            await app.delete_amap_settings()

        self.assertEqual(settings.save_calls, 1)
        self.assertEqual(settings.clear_calls, 1)
        self.assertEqual((await app.cache_status())["entries"], 0)


class _RequestStub:
    def __init__(self):
        self.disconnected = False

    async def is_disconnected(self):
        return self.disconnected


if __name__ == "__main__":
    unittest.main()
