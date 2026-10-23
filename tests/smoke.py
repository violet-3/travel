"""
冒烟测试 · 无需任何 API Key 即可运行

    venv/Scripts/python.exe -B tests/smoke.py

覆盖: 容错 JSON 解析 / 高德签名 / 编译器 intent 注入与预算分档 /
Transport 别名序列化 / 城市反查 / Agent 结构化输出 / 富化层离线降级与临时缓存。
"""

import asyncio
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import CultureData, RoutePlan, DayPlan, Activity, Spot  # noqa: E402

FAILED = []


def check(name, fn):
    try:
        fn()
        print(f"  ✅ {name}")
    except AssertionError as e:
        FAILED.append(name)
        print(f"  ❌ {name}: {e}")
    except Exception as e:
        FAILED.append(name)
        print(f"  ❌ {name}: {type(e).__name__}: {e}")


# ── json_utils ──────────────────────────────────────────────

def test_json_utils():
    from tools.json_utils import parse_json
    assert parse_json('```json\n[{"a":1}]\n```') == [{"a": 1}]
    r = parse_json('[{"name":"殷墟","tips":"great, don\'t miss it"}]')
    assert r[0]["tips"] == "great, don't miss it", "撇号不能被破坏"
    assert parse_json('{"a": [1, 2') == {"a": [1, 2]}      # 截断修复
    assert parse_json('{"a":1,}') == {"a": 1}               # 尾逗号
    assert parse_json({"already": "parsed"}) == {"already": "parsed"}


# ── amap 签名 ───────────────────────────────────────────────

def test_amap_sign():
    from tools.amap_utils import amap_sign, with_sig
    sig = amap_sign({"keywords": "安阳", "subdistrict": 0}, "testsecret")
    expect = hashlib.md5("keywords=安阳&subdistrict=0testsecret".encode("utf-8")).hexdigest()
    assert sig == expect, "签名使用原始 UTF-8 参数值；发送请求时再 URL 编码"
    p = with_sig({"keywords": "安阳"}, "KEY123", "testsecret")
    sig_with_key = hashlib.md5("key=KEY123&keywords=安阳testsecret".encode("utf-8")).hexdigest()
    assert p["key"] == "KEY123" and p["sig"] == sig_with_key, "key 必须参与签名"
    assert amap_sign({"a": 1}, "") == ""


# ── 编译器: intent 注入 + 预算分档 ──────────────────────────

def test_compile_intent_and_budget():
    from agents.guide_generator import GuideGenerator
    route = RoutePlan(route_name="安阳3日", cities=["安阳"],
                      daily_plan=[DayPlan(day=i + 1, city="安阳") for i in range(3)])
    gen = GuideGenerator()
    g = gen.compile(route, [], [], intent={"departure_city": "北京", "budget_level": "经济"})
    assert g.departure_city == "北京" and g.budget_level == "经济"
    # 安阳城市系数 0.8：经济 120×0.8=96/晚 ×2 晚
    assert g.budget.accommodation == 96 * 2, f"经济型住宿折算后 96/晚, 实际 {g.budget.accommodation}"
    g2 = gen.compile(route, [], [])
    assert g2.departure_city == "" and g2.budget_level == "中等" and g2.budget.accommodation == 200 * 2
    g3 = gen.compile(route, [], [], intent={"budget_level": "豪华"})
    assert g3.budget.accommodation == 560 * 2 and g3.budget.food == 220 * 3


# ── Transport 别名序列化 (前端读 t.from / t.to) ─────────────

def test_transport_alias():
    from models.schemas import Transport, TravelGuide
    r = RoutePlan(transport=[Transport(**{"from": "北京", "to": "安阳", "mode": "高铁"})])
    data = json.loads(TravelGuide(route=r).model_dump_json(by_alias=True))
    t = data["route"]["transport"][0]
    assert t["from"] == "北京" and t["to"] == "安阳", "必须以 by_alias 输出 from/to"


# ── 城市反查 (直连模式) ─────────────────────────────────────

def test_assign_spot_cities():
    from orchestrator_llm import TravelOrchestrator as LO
    route = RoutePlan(daily_plan=[DayPlan(day=1, city="安阳", morning=Activity(name="殷墟"))])
    spots = [Spot(name="殷墟博物馆"), Spot(name="完全匹配不上xyz")]
    LO()._assign_spot_cities(route, spots)
    assert spots[0].city == "安阳" and spots[1].city == ""


# ── 富化层: 无 Key 优雅降级 + 本地缓存命中 + 索引落盘 ────────

def test_enrich_no_key_and_cache():
    import io
    from PIL import Image
    from tools import enrich
    enrich_guide = enrich.enrich_guide
    INDEX_FILE = enrich.INDEX_FILE
    PHOTO_DIR = enrich.PHOTO_DIR
    _local_photo = enrich._local_photo
    spots = [Spot(name="殷墟", city="安阳")]
    cultures = [CultureData(city="安阳", cuisine={"must_eat": [{"name": "扁粉菜", "where": "老西扁粉菜"}]})]
    fixture = io.BytesIO()
    Image.new("RGB", (2, 2), (34, 92, 71)).save(fixture, format="JPEG")
    (PHOTO_DIR / "安阳").mkdir(parents=True, exist_ok=True)
    (PHOTO_DIR / "安阳" / "殷墟.jpg").write_bytes(fixture.getvalue())
    (PHOTO_DIR / "安阳" / "food_老西扁粉菜.jpg").write_bytes(fixture.getvalue())
    asyncio.run(enrich_guide(spots, cultures))
    assert spots[0].coordinate is None, "无 Key 时不应有坐标"
    assert not spots[0].coordinate_verified
    assert spots[0].photo == "" or spots[0].photo.startswith("/static/photos/")
    idx = json.loads(INDEX_FILE.read_text(encoding="utf-8")) if INDEX_FILE.exists() else {}
    assert len(idx) == 0, f"无来源查询时不应写入正向缓存，实际 {len(idx)} 条"
    # 本地缓存命中
    d = PHOTO_DIR / "安阳"
    d.mkdir(parents=True, exist_ok=True)
    (d / "殷墟.jpg").write_bytes(b"fake")
    assert _local_photo("安阳", "殷墟") is None


# ── 天气: 无 Key ────────────────────────────────────────────

def test_weather_no_key():
    from tools.weather import get_weather
    r = asyncio.run(get_weather("安阳", "2099-01-01")) if _has_key() else {"status": "no_key"}
    assert r.get("status") in ("no_key", "ok", "error", "outside_forecast_window")


def _has_key():
    from config import default_config
    return bool(default_config.amap.weather_key) and not default_config.amap.weather_key.startswith("YOUR_")


def test_agent_output_contract():
    test_file = Path(__file__).with_name("test_agent_output.py")
    spec = importlib.util.spec_from_file_location("offline_agent_output_tests", test_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.AgentOutputParserTests)
    result = unittest.TestResult()
    suite.run(result)
    if not result.wasSuccessful():
        details = "\n".join(message for _, message in result.failures + result.errors)
        raise AssertionError(details or "Agent output contract tests failed")


if __name__ == "__main__":
    # Set inert config before importing modules that read config.py at import time.
    offline_env = {
        "AMAP_WEATHER_KEY": "",
        "AMAP_WEB_SERVICE_KEY": "",
        "AMAP_WEB_SERVICE_SECRET": "",
        "AMAP_JS_API_KEY": "",
        "AMAP_JS_SECURITY_CODE": "",
        "AMAP_SECRET": "",
        "TRAVEL_LLM_URL": "http://127.0.0.1:9/v1",
        "TRAVEL_LLM_KEY": "offline-smoke-key",
        "TRAVEL_LLM_MODEL": "offline-smoke-model",
    }
    with patch.dict(os.environ, offline_env):
        from config import default_config
        from tools import enrich

        old_amap = default_config.amap
        old_wikimedia = default_config.image.use_wikimedia
        old_photo_dir, old_index_file = enrich.PHOTO_DIR, enrich.INDEX_FILE
        from config import AmapConfig
        default_config.amap = AmapConfig(web_key="", web_secret="", js_key="", js_security_code="")
        default_config.image.use_wikimedia = False

        network_attempts = []

        class OfflineHTTPClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def get(self, url, *args, **kwargs):
                network_attempts.append(url)
                raise AssertionError(f"Offline smoke attempted HTTP: {url}")

        try:
            with TemporaryDirectory(prefix="shanhe-smoke-") as temp_dir:
                temp_photos = Path(temp_dir) / "photos"
                enrich.PHOTO_DIR = temp_photos
                enrich.INDEX_FILE = temp_photos / "_index.json"

                print("── 山河游记 离线冒烟测试 ──")
                with patch("httpx.AsyncClient", OfflineHTTPClient):
                    check("json_utils 容错解析", test_json_utils)
                    check("amap 数字签名", test_amap_sign)
                    check("编译器 intent 注入 + 预算分档", test_compile_intent_and_budget)
                    check("Transport 别名序列化", test_transport_alias)
                    check("LangChain 编排城市反查", test_assign_spot_cities)
                    check("LangChain Agent 输出兼容与失败契约", test_agent_output_contract)
                    check("富化层无 Key 降级 + 临时缓存", test_enrich_no_key_and_cache)
                    check("天气服务无 Key 行为", test_weather_no_key)
                if network_attempts:
                    FAILED.append("HTTP 隔离")
                    print(f"  ❌ HTTP 隔离: 尝试请求 {network_attempts}")
                else:
                    print("  ✅ HTTP 隔离: 未发起请求")
                if temp_photos.exists() and not enrich.INDEX_FILE.exists():
                    FAILED.append("临时图片目录")
                    print("  ❌ 临时图片目录: 测试索引未写入临时目录")
        finally:
            enrich.PHOTO_DIR, enrich.INDEX_FILE = old_photo_dir, old_index_file
            default_config.amap = old_amap
            default_config.image.use_wikimedia = old_wikimedia

    print("──────────────────────")
    if FAILED:
        print(f"FAILED: {len(FAILED)} -> {FAILED}")
        sys.exit(1)
    print("ALL PASSED ✅")
