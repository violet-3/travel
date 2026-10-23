"""Offline contract, safety, and compatibility checks for web research."""

import asyncio
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from PIL import Image

from agents.guide_generator import GuideGenerator
from config import ModelConfig
from models.schemas import (
    RoutePlan,
    Spot,
    TravelGuide,
    WebEvidence,
    WebResearchStatus,
    WebSpotResearch,
)
from tools.deepseek_search import research_spots
from tools.deepseek_search_settings import (
    DeepSeekResearchConfig,
    DeepSeekSearchSettingsError,
    DeepSeekSearchSettingsPayload,
    DeepSeekSearchSettingsStore,
    OFFICIAL_BASE_URL,
)
from tools.guide_cache import GuideCache, build_cache_key
from tools.web_image_download import WebImageDownloader


def ready_config(key="offline-search-secret", base_url=OFFICIAL_BASE_URL):
    return DeepSeekResearchConfig(
        enabled=True, base_url=base_url, api_key=key, availability="ready",
        auth_mode="dedicated", identity=hashlib.sha256(key.encode()).hexdigest()[:32],
    )


def result(title, url="https://example.com/beijing-palace", snippet="北京故宫博物院 门票预约"):
    return {"title": title, "url": url, "snippet": snippet, "site_name": "景区资料页"}


class MemoryCredentials:
    available = True

    def __init__(self):
        self.value = None

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def delete(self):
        self.value = None


class FakeDownloader:
    def __init__(self, status="downloaded"):
        self.status = status
        self.urls = []

    async def download(self, url):
        self.urls.append(url)
        return {
            "status": self.status,
            "local_url": "/static/photos/web-research/" + "a" * 64 + ".jpg" if self.status == "downloaded" else None,
            "downloaded_at": "2026-10-23T01:02:03+00:00" if self.status == "downloaded" else None,
        }


class ResearchFlowTests(unittest.IsolatedAsyncioTestCase):
    def client_for(self, search_payload, fetch_payload=None, *, search_status=200, fetch_status=200,
                   search_handler=None):
        calls = []

        async def handler(request):
            calls.append(request)
            self.assertEqual(request.headers.get("authorization"), "Bearer offline-search-secret")
            if request.url.path.endswith("/search"):
                if search_handler:
                    return await search_handler(request)
                return httpx.Response(search_status, json=search_payload)
            if request.url.path.endswith("/fetch"):
                return httpx.Response(fetch_status, json=fetch_payload or {})
            return httpx.Response(404)

        return httpx.MockTransport(handler), calls

    async def test_disabled_research_makes_no_requests_and_old_guide_defaults(self):
        def fail(_request):
            raise AssertionError("disabled research must not contact the network")

        spot = Spot(name="故宫博物院", city="北京市")
        status = await research_spots(
            [spot], DeepSeekResearchConfig(enabled=False, base_url=OFFICIAL_BASE_URL),
            transport=httpx.MockTransport(fail),
        )
        self.assertEqual(status.status, "disabled")
        self.assertEqual(status.search_count, 0)
        self.assertEqual(status.spots[0].status, "disabled")
        self.assertEqual(TravelGuide.model_validate({"title": "旧档案"}).web_research.status, "disabled")

    async def test_exact_page_quotes_image_candidate_and_budget_are_preserved(self):
        page = {
            "title": "北京故宫博物院门票与参观指南",
            "content": "# 北京故宫博物院\n成人票 ¥60，适用日期请查看预约页。\n学生票 ¥30，需出示学生证。\n"
                       "![logo](https://img.example/logo.png)\n"
                       "![故宫红墙](https://img.example/palace.jpg)",
        }
        transport, calls = self.client_for({"results": [result("北京故宫博物院门票")]}, page)
        downloader = FakeDownloader()
        spot = Spot(name="故宫博物院", city="北京市", ticket=188, ticket_status="reference")
        status = await research_spots([spot], ready_config(), downloader=downloader, transport=transport)

        self.assertEqual([request.url.path for request in calls], ["/v1/tools/search", "/v1/tools/fetch"])
        self.assertEqual(status.search_count, 1)
        self.assertEqual(status.fetch_count, 1)
        self.assertEqual(status.image_candidate_count, 1, "logo/icon 候选不应下载")
        self.assertEqual(downloader.urls, ["https://img.example/palace.jpg"])
        row = status.spots[0]
        self.assertEqual(row.status, "searched")
        evidence = row.evidence[0]
        self.assertEqual(evidence.source_id, hashlib.sha256(evidence.url.encode()).hexdigest()[:16])
        self.assertTrue(all(quote in page["content"] for quote in evidence.quotes))
        self.assertIn("成人票 ¥60，适用日期请查看预约页。", evidence.price_quotes)
        self.assertIn("学生票 ¥30，需出示学生证。", evidence.price_quotes)
        self.assertEqual(spot.ticket, 188, "网页票价不能覆盖生成器预算字段")
        self.assertEqual(spot.photo_source, "deepseek_web_image")

    async def test_same_city_different_attraction_is_rejected_before_fetch(self):
        transport, calls = self.client_for({
            "results": [result("北京八达岭长城成人票 ¥100", snippet="北京八达岭长城门票预约")]
        })
        spot = Spot(name="故宫博物院", city="北京市")
        status = await research_spots([spot], ready_config(), transport=transport)
        self.assertEqual(len(calls), 1)
        self.assertEqual(status.spots[0].status, "no_spot_match")
        self.assertEqual(status.spots[0].evidence, [])

    async def test_target_context_flows_into_generic_ticket_and_opening_subsections(self):
        body = "# 安阳殷墟\n\n## 门票\n\n成人票70元，预约后入园。\n\n## 开放时间\n\n09:00-17:00（16:30停止入场）"
        transport, _ = self.client_for(
            {"results": [result("安阳殷墟参观说明", "https://example.com/anyang-yinxu", "安阳殷墟门票预约")]},
            {"title": "殷墟参观说明", "content": body},
        )
        status = await research_spots([Spot(name="殷墟", city="安阳市")], ready_config(), transport=transport)
        evidence = status.spots[0].evidence[0]
        self.assertIn("成人票70元，预约后入园。", evidence.price_quotes)
        self.assertIn("09:00-17:00（16:30停止入场）", evidence.quotes)
        self.assertTrue(all(quote in body for quote in evidence.quotes))

    async def test_query_string_cannot_prove_city_or_spot_identity(self):
        bad = result("景区门票信息", "https://example.com/ticket?city=北京&spot=故宫博物院", "门票 ¥60")
        transport, calls = self.client_for({"results": [bad]})
        status = await research_spots([Spot(name="故宫博物院", city="北京市")], ready_config(), transport=transport)
        self.assertEqual(len(calls), 1)
        self.assertEqual(status.spots[0].status, "no_city_match")
        self.assertEqual(status.fetch_count, 0)

    async def test_fetch_body_for_another_attraction_keeps_only_search_lead(self):
        page = {"title": "北京故宫博物院门票", "content": "# 北京八达岭长城\n成人票 ¥100\n![长城](https://img.example/wall.jpg)"}
        transport, _ = self.client_for({"results": [result("北京故宫博物院门票")]}, page)
        status = await research_spots([Spot(name="故宫博物院", city="北京市")], ready_config(), transport=transport)
        row = status.spots[0]
        self.assertEqual(status.status, "partial")
        self.assertIn("未能匹配", status.message)
        self.assertEqual(row.status, "page_unmatched")
        self.assertEqual(row.evidence[0].fetch_status, "mismatch")
        self.assertEqual(row.evidence[0].price_quotes, [])
        self.assertEqual(row.evidence[0].image_candidates, [])

    async def test_http_errors_invalid_json_and_timeout_are_safe_and_not_retried(self):
        for code, expected in ((402, "余额不足"), (429, "频率受限")):
            transport, calls = self.client_for({"message": "offline-search-secret"}, search_status=code)
            result_status = await research_spots([Spot(name="故宫", city="北京")], ready_config(), transport=transport)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result_status.search_count, 1)
            self.assertIn(expected, result_status.message)
            self.assertNotIn("offline-search-secret", result_status.model_dump_json())

        async def invalid(_request):
            return httpx.Response(200, content=b"not-json")

        transport, calls = self.client_for({}, search_handler=invalid)
        result_status = await research_spots([Spot(name="故宫", city="北京")], ready_config(), transport=transport)
        self.assertEqual(len(calls), 1)
        self.assertIn("格式", result_status.message)

        async def timeout(_request):
            raise httpx.ReadTimeout("secret must not be echoed")

        transport, calls = self.client_for({}, search_handler=timeout)
        result_status = await research_spots([Spot(name="故宫", city="北京")], ready_config(), transport=transport)
        self.assertEqual(len(calls), 1)
        self.assertIn("超时", result_status.message)
        self.assertNotIn("secret must not be echoed", result_status.message)

    async def test_spot_limit_and_search_concurrency_are_bounded(self):
        active = 0
        maximum = 0
        calls = 0

        async def handler(request):
            nonlocal active, maximum, calls
            calls += 1
            active += 1
            maximum = max(maximum, active)
            try:
                await asyncio.sleep(0.01)
                return httpx.Response(200, json={"results": []})
            finally:
                active -= 1

        transport = httpx.MockTransport(handler)
        spots = [Spot(name=f"景点{i}", city="北京市") for i in range(5)]
        status = await research_spots(spots, ready_config(), transport=transport)
        self.assertEqual(calls, 3)
        self.assertLessEqual(maximum, 2)
        self.assertEqual(status.search_count, 3)
        self.assertTrue(all(item.status == "skipped_limit" for item in status.spots[3:]))

    async def test_total_timeout_keeps_partial_results_and_counts(self):
        entered = asyncio.Event()

        async def handler(request):
            payload = json.loads(await request.aread())
            if request.url.path.endswith("/search") and "慢景点" in payload["query"]:
                entered.set()
                await asyncio.sleep(0.25)
            if request.url.path.endswith("/search"):
                title = "北京快景点门票" if "快景点" in payload["query"] else "北京慢景点门票"
                return httpx.Response(200, json={"results": [result(title, snippet=title)]})
            return httpx.Response(200, json={"title": "北京快景点", "content": "# 北京快景点\n门票预约说明"})

        spots = [Spot(name="快景点", city="北京市"), Spot(name="慢景点", city="北京市")]
        with patch("tools.deepseek_search.TOTAL_TIMEOUT_SECONDS", 0.04):
            status = await research_spots(spots, ready_config(), transport=httpx.MockTransport(handler))
        self.assertTrue(entered.is_set())
        self.assertEqual(status.status, "partial")
        self.assertEqual(status.search_count, 2)
        self.assertEqual(status.fetch_count, 1)
        self.assertIn("fetched", {e.fetch_status for row in status.spots for e in row.evidence})

    async def test_external_cancellation_closes_client_and_drains_tasks(self):
        started = asyncio.Event()
        loop = asyncio.get_running_loop()
        errors = []
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _loop, context: errors.append(context))

        class BlockingTransport(httpx.AsyncBaseTransport):
            closed = False

            async def handle_async_request(self, request):
                started.set()
                await asyncio.Event().wait()

            async def aclose(self):
                self.closed = True

        transport = BlockingTransport()
        task = asyncio.create_task(research_spots(
            [Spot(name="故宫", city="北京")], ready_config(), transport=transport
        ))
        try:
            await asyncio.wait_for(started.wait(), timeout=1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0)
            self.assertTrue(transport.closed)
            self.assertEqual(errors, [])
        finally:
            loop.set_exception_handler(previous_handler)


class SettingsAndCacheTests(unittest.TestCase):
    def make_store(self, folder):
        return DeepSeekSearchSettingsStore(Path(folder) / "deepseek-search-settings.json", MemoryCredentials())

    def test_session_only_save_failure_keeps_old_key_and_origin_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(folder)
            store.save(DeepSeekSearchSettingsPayload(
                enabled=True, auth_mode="dedicated", base_url=OFFICIAL_BASE_URL,
                api_key="session-old", session_only=True,
            ))
            old = store.resolve()
            with patch.object(store, "_persist", side_effect=DeepSeekSearchSettingsError("disk failure")):
                with self.assertRaises(DeepSeekSearchSettingsError):
                    store.save(DeepSeekSearchSettingsPayload(
                        enabled=True, auth_mode="dedicated", base_url="https://proxy.example",
                        api_key="session-new", session_only=True,
                    ))
            current = store.resolve()
            self.assertEqual(current.identity, old.identity)
            self.assertEqual(current.api_key, "session-old")
            self.assertEqual(current.base_url, OFFICIAL_BASE_URL)

    def test_switch_to_session_key_then_clear_removes_saved_credential(self):
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(folder)
            credentials = store.credentials
            store.save(DeepSeekSearchSettingsPayload(
                enabled=True, auth_mode="dedicated", api_key="saved-old",
            ))
            store.save(DeepSeekSearchSettingsPayload(
                enabled=True, auth_mode="dedicated", api_key="session-new", session_only=True,
            ))
            self.assertIsNone(credentials.get(), "old persisted credential is removed on source switch")
            store.clear()
            self.assertIsNone(credentials.get())
            self.assertFalse(store.public_status()["has_key"])

    def test_origin_change_requires_reentry_and_env_override_does_not_reuse_key(self):
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(folder)
            store.save(DeepSeekSearchSettingsPayload(
                enabled=True, auth_mode="dedicated", api_key="proxy-key",
            ))
            with self.assertRaises(DeepSeekSearchSettingsError):
                store.save(DeepSeekSearchSettingsPayload(
                    enabled=True, auth_mode="dedicated", base_url="https://other.example",
                ))
            with patch.dict(os.environ, {"DEEPSEEK_SEARCH_BASE_URL": "https://other.example"}):
                resolved = store.resolve()
                self.assertEqual(resolved.availability, "origin_changed")
                self.assertIsNone(resolved.api_key)

    def test_environment_key_requires_explicit_enable_and_dedicated_source(self):
        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(folder)
            env = {
                "DEEPSEEK_SEARCH_ENABLED": "true",
                "DEEPSEEK_SEARCH_AUTH_MODE": "dedicated",
                "DEEPSEEK_SEARCH_API_KEY": "env-search-key",
                "DEEPSEEK_SEARCH_BASE_URL": "https://search-proxy.example",
            }
            with patch.dict(os.environ, env, clear=False):
                resolved = store.resolve()
                status = store.public_status()
            self.assertTrue(resolved.enabled)
            self.assertEqual(resolved.availability, "ready")
            self.assertEqual(resolved.api_key, "env-search-key")
            self.assertTrue(status["enabled_overridden_by_environment"])
            self.assertTrue(status["auth_mode_overridden_by_environment"])
            self.assertTrue(status["key_overridden_by_environment"])
            self.assertTrue(status["base_url_overridden_by_environment"])

            # A standalone key never opts in or silently switches auth source.
            with patch.dict(os.environ, {
                "DEEPSEEK_SEARCH_API_KEY": "env-search-key",
                "DEEPSEEK_SEARCH_ENABLED": "",
                "DEEPSEEK_SEARCH_AUTH_MODE": "",
                "DEEPSEEK_SEARCH_BASE_URL": "",
            }, clear=False):
                default = store.resolve()
            self.assertFalse(default.enabled)
            self.assertEqual(default.availability, "disabled")

    def test_profile_reuse_requires_explicit_eligible_official_profile(self):
        class Profiles:
            def __init__(self, provider, base_url):
                self.provider = provider
                self.base_url = base_url

            def list_profiles(self):
                return [{"profile_id": "explicit", "name": "explicit", "provider": self.provider,
                         "protocol": "openai_compatible", "base_url": self.base_url, "has_key": True}]

            def resolve_model_config(self, profile_id):
                self.asserted_id = profile_id
                return ModelConfig(profile_id=profile_id, provider="deepseek", base_url=self.base_url,
                                   api_key="profile-secret")

        with tempfile.TemporaryDirectory() as folder:
            store = self.make_store(folder)
            profiles = Profiles("deepseek", OFFICIAL_BASE_URL)
            store.save(DeepSeekSearchSettingsPayload(
                enabled=True, auth_mode="profile", profile_id="explicit",
            ))
            self.assertEqual(store.resolve(profiles).api_key, "profile-secret")
            self.assertEqual(profiles.asserted_id, "explicit")
            profiles.provider = "custom"
            self.assertEqual(store.resolve(profiles).availability, "profile_unavailable")

    def test_cache_identity_changes_with_enablement_and_search_credential(self):
        with tempfile.TemporaryDirectory() as folder:
            first = self.make_store(folder)
            first.save(DeepSeekSearchSettingsPayload(
                enabled=True, auth_mode="dedicated", api_key="first-key",
            ))
            config_a = first.resolve()
            disabled = first.resolve(enabled_override=False)
            second = self.make_store(Path(folder) / "second")
            second.save(DeepSeekSearchSettingsPayload(
                enabled=True, auth_mode="dedicated", api_key="second-key",
            ))
            config_b = second.resolve()
            self.assertNotEqual(config_a.identity, disabled.identity)
            self.assertNotEqual(config_a.identity, config_b.identity)
            model = ModelConfig(provider="deepseek", base_url=OFFICIAL_BASE_URL)
            key_a = build_cache_key("安阳三日", {}, model, None, research_config=config_a)
            key_off = build_cache_key("安阳三日", {}, model, None, research_config=disabled)
            key_b = build_cache_key("安阳三日", {}, model, None, research_config=config_b)
            self.assertEqual(len({key_a, key_off, key_b}), 3)
            self.assertNotIn("first-key", json.dumps({"a": config_a.identity, "b": key_a}))

    def test_sources_round_trip_through_cache_history_and_markdown(self):
        url = "https://example.com/beijing-palace"
        source_id = hashlib.sha256(url.encode()).hexdigest()[:16]
        quote = "成人票 ¥60，适用日期请查看预约页。"
        evidence = WebEvidence(
            source_id=source_id, title="北京故宫博物院门票", url=url,
            status="fetched", fetch_status="fetched", city_match="matched",
            fetched_at="2026-10-23T01:02:03+00:00", quotes=[quote], price_quotes=[quote],
        )
        guide = TravelGuide(
            title="安阳漫游", days=1, destinations=["北京"],
            route=RoutePlan(route_name="北京一日", cities=["北京"]),
            spots=[Spot(name="故宫博物院", city="北京市", ticket=188, ticket_status="reference")],
            web_research=WebResearchStatus(
                status="complete", message="来源已获取", search_count=1, fetch_count=1,
                spots=[WebSpotResearch(spot_index=0, spot_name="故宫博物院", city="北京市",
                                       status="searched", evidence=[evidence])],
            ),
        )
        markdown = GuideGenerator().to_markdown(guide)
        self.assertIn("网页票价线索", markdown)
        self.assertIn("(https://example.com/beijing-palace)", markdown)
        self.assertIn("不计入预算", markdown)

        with tempfile.TemporaryDirectory() as folder:
            cache = GuideCache(Path(folder) / "cache")
            cache_key = "b" * 40
            cache.set(cache_key, json.loads(guide.model_dump_json(by_alias=True)))
            self.assertIsNotNone(cache.get(cache_key))
        with self.assertRaises(ValueError):
            WebEvidence(source_id="not-a-hash", title="x", url=url)


class WebImageDownloadTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def png_bytes():
        image = Image.new("RGB", (80, 60), (45, 100, 70))
        import io
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    async def test_download_pins_ip_preserves_host_sni_and_never_sends_authorization(self):
        seen = []
        image_bytes = self.png_bytes()

        async def handler(request):
            seen.append(request)
            return httpx.Response(200, headers={"Content-Type": "image/png"}, content=image_bytes)

        async def resolver(_host, _port):
            return ["8.8.8.8"]

        with tempfile.TemporaryDirectory() as folder:
            downloader = WebImageDownloader(
                cache_dir=folder, transport=httpx.MockTransport(handler), resolver=resolver,
            )
            result = await downloader.download("https://images.example/palace.png")
            self.assertEqual(result["status"], "downloaded")
            self.assertEqual(seen[0].url.host, "8.8.8.8")
            self.assertEqual(seen[0].headers["host"], "images.example")
            self.assertEqual(seen[0].extensions["sni_hostname"], "images.example")
            self.assertNotIn("authorization", seen[0].headers)
            self.assertTrue((Path(folder) / "web-research").is_dir())
            self.assertTrue(result["local_url"].startswith("/static/photos/web-research/"))

    async def test_private_target_and_private_redirect_are_not_requested(self):
        calls = []

        async def handler(request):
            calls.append(request)
            return httpx.Response(302, headers={"Location": "https://127.0.0.1/admin"})

        async def resolver(_host, _port):
            return ["8.8.8.8"]

        downloader = WebImageDownloader(
            transport=httpx.MockTransport(handler), resolver=resolver,
        )
        direct = await downloader.download("https://127.0.0.1/private.png")
        redirected = await downloader.download("https://images.example/logo.png")
        self.assertEqual(direct["status"], "unsafe_url")
        self.assertEqual(redirected["status"], "unsafe_redirect")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
