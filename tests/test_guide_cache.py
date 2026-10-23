"""第15轮：短时结果缓存 —— 相同请求不重复付费，命中必须显式标注。"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from config import ModelConfig
from tools.guide_cache import (
    CACHE_VERSION,
    GuideCache,
    build_cache_key,
)


def _guide_payload(title: str = "安阳三日") -> dict:
    return {
        "title": title,
        "days": 3,
        "destinations": ["安阳"],
        "generated_at": "2026-10-20T10:00:00",
        "route": {"route_name": "安阳三日", "cities": ["安阳"], "daily_plan": []},
    }


class CacheKeyTests(unittest.TestCase):
    def setUp(self):
        self.config = ModelConfig(provider="deepseek", model="deepseek-chat",
                                  base_url="https://api.deepseek.com/v1")

    def test_same_request_produces_same_key(self):
        first = build_cache_key("安阳玩3天", {"days": 3}, self.config, None)
        second = build_cache_key("安阳玩3天", {"days": 3}, self.config, None)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 40)

    def test_whitespace_is_normalized(self):
        first = build_cache_key("安阳  玩3天", {}, self.config, None)
        second = build_cache_key(" 安阳 玩3天 ", {}, self.config, None)
        self.assertEqual(first, second)

    def test_different_conditions_change_key(self):
        base = build_cache_key("安阳玩3天", {"days": 3}, self.config, None)
        for changed in (
            build_cache_key("安阳玩4天", {"days": 3}, self.config, None),
            build_cache_key("安阳玩3天", {"days": 4}, self.config, None),
            build_cache_key("安阳玩3天", {"days": 3, "travelers": 2}, self.config, None),
        ):
            self.assertNotEqual(base, changed)

    def test_different_model_changes_key(self):
        base = build_cache_key("安阳", {}, self.config, None)
        other_model = ModelConfig(provider="deepseek", model="other-model",
                                  base_url="https://api.deepseek.com/v1")
        other_url = ModelConfig(provider="deepseek", model="deepseek-chat",
                                base_url="https://example.com/v1")
        self.assertNotEqual(base, build_cache_key("安阳", {}, other_model, None))
        self.assertNotEqual(base, build_cache_key("安阳", {}, other_url, None))

    def test_generation_affecting_model_settings_change_key(self):
        base = build_cache_key("安阳", {}, self.config, None)
        for changed in (
            self.config.model_copy(update={"temperature": 0.8}),
            self.config.model_copy(update={"max_tokens": 2048}),
            self.config.model_copy(update={"timeout": 30.0}),
            self.config.model_copy(update={"max_retries": 3}),
        ):
            self.assertNotEqual(base, build_cache_key("安阳", {}, changed, None))

    def test_shanghai_day_context_changes_key_for_relative_date_queries(self):
        first = build_cache_key("明天去苏州", {}, self.config, None, date_context="2026-10-23")
        next_day = build_cache_key("明天去苏州", {}, self.config, None, date_context="2026-10-24")
        self.assertNotEqual(first, next_day)

    def test_amap_configuration_changes_key_without_exposing_credentials(self):
        first_config = type("Amap", (), {"web_key": "secret-one", "web_secret": "sig-one"})()
        second_config = type("Amap", (), {"web_key": "secret-two", "web_secret": "sig-one"})()
        first = build_cache_key("苏州", {}, self.config, None, amap_config=first_config)
        second = build_cache_key("苏州", {}, self.config, None, amap_config=second_config)
        self.assertNotEqual(first, second)
        self.assertNotIn("secret-one", first)

    def test_profile_id_participates(self):
        base = build_cache_key("安阳", {}, self.config, None)
        with_profile = build_cache_key("安阳", {}, self.config, "abc123")
        self.assertNotEqual(base, with_profile)

    def test_api_key_is_not_part_of_the_key(self):
        """缓存 key 不应随密钥变化，也不应把密钥写进文件。"""
        base = build_cache_key("安阳", {}, self.config, None)
        with_key = self.config.model_copy(update={"api_key": "sk-secret-value"})
        self.assertEqual(base, build_cache_key("安阳", {}, with_key, None))

    def test_override_order_does_not_matter(self):
        first = build_cache_key("安阳", {"days": 3, "travelers": 2}, self.config, None)
        second = build_cache_key("安阳", {"travelers": 2, "days": 3}, self.config, None)
        self.assertEqual(first, second)


class CacheStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cache = GuideCache(directory=Path(self.temp.name), ttl_seconds=600)
        self.key = "a" * 40

    def tearDown(self):
        self.temp.cleanup()

    def test_roundtrip(self):
        self.assertTrue(self.cache.set(self.key, _guide_payload()))
        hit = self.cache.get(self.key)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["guide"]["title"], "安阳三日")
        self.assertGreaterEqual(hit["age_seconds"], 0)

    def test_missing_entry_returns_none(self):
        self.assertIsNone(self.cache.get("b" * 40))

    def test_expired_entry_is_not_returned_and_is_removed(self):
        self.assertTrue(self.cache.set(self.key, _guide_payload()))
        path = Path(self.temp.name) / f"{self.key}.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["saved_at"] = time.time() - 3600
        path.write_text(json.dumps(raw), encoding="utf-8")

        self.assertIsNone(self.cache.get(self.key))
        self.assertFalse(path.exists(), "过期条目应被清理")

    def test_corrupted_file_is_discarded(self):
        path = Path(self.temp.name) / f"{self.key}.json"
        path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(self.cache.get(self.key))
        self.assertFalse(path.exists())

    def test_wrong_version_is_rejected(self):
        path = Path(self.temp.name) / f"{self.key}.json"
        path.write_text(json.dumps({
            "version": CACHE_VERSION + 1, "saved_at": time.time(), "guide": _guide_payload(),
        }), encoding="utf-8")
        self.assertIsNone(self.cache.get(self.key))

    def test_guide_without_route_is_not_cached(self):
        self.assertFalse(self.cache.set(self.key, {"title": "空攻略"}))
        self.assertIsNone(self.cache.get(self.key))

    def test_invalid_nonempty_route_is_discarded_as_a_cache_miss(self):
        path = Path(self.temp.name) / f"{self.key}.json"
        path.write_text(json.dumps({
            "version": CACHE_VERSION,
            "saved_at": time.time(),
            "guide": {**_guide_payload(), "route": {"daily_plan": "not-a-list"}},
        }), encoding="utf-8")
        self.assertIsNone(self.cache.get(self.key))
        self.assertFalse(path.exists())

    def test_invalid_key_is_rejected(self):
        for bad in ("", "short", "z" * 40, None, 123):
            self.assertIsNone(self.cache.get(bad))
            self.assertFalse(self.cache.set(bad, _guide_payload()))

    def test_clear_removes_entries(self):
        self.cache.set(self.key, _guide_payload())
        self.cache.set("c" * 40, _guide_payload())
        self.assertEqual(self.cache.clear(), 2)
        self.assertEqual(self.cache.status()["entries"], 0)

    def test_status_counts_fresh_entries(self):
        self.cache.set(self.key, _guide_payload())
        status = self.cache.status()
        self.assertEqual(status["entries"], 1)
        self.assertEqual(status["fresh"], 1)
        self.assertEqual(status["ttl_seconds"], 600)

    def test_write_failure_is_reported_not_raised(self):
        cache = GuideCache(directory=Path(self.temp.name) / "file-as-dir")
        # 用同名文件占住目录路径，制造写入失败
        (Path(self.temp.name) / "file-as-dir").write_text("x", encoding="utf-8")
        self.assertFalse(cache.set(self.key, _guide_payload()))
        self.assertIsNone(cache.get(self.key))

    def test_prune_keeps_cache_bounded(self):
        for index in range(45):
            self.cache.set(f"{index:040x}", _guide_payload(f"攻略{index}"))
        entries = list(Path(self.temp.name).glob("*.json"))
        self.assertLessEqual(len(entries), 40)


if __name__ == "__main__":
    unittest.main()
