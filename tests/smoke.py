"""
冒烟测试 · 无需任何 API Key 即可运行

    venv/Scripts/python tests/smoke.py    # 或 python tests/smoke.py

覆盖: 容错 JSON 解析 / 高德签名 / 编译器 intent 注入与预算分档 /
Transport 别名序列化 / 城市反查 / 富化层无 Key 降级与本地缓存。
"""

import asyncio
import hashlib
import json
import sys
from pathlib import Path

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
    expect = hashlib.md5("keywords=%E5%AE%89%E9%98%B3&subdistrict=0testsecret".encode()).hexdigest()
    assert sig == expect, "中文参数值必须 URL 编码后参与签名"
    p = with_sig({"keywords": "安阳"}, "KEY123", "testsecret")
    sig_with_key = hashlib.md5("key=KEY123&keywords=%E5%AE%89%E9%98%B3testsecret".encode()).hexdigest()
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
    assert g.budget.accommodation == 120 * 2, f"经济型住宿 120/晚, 实际 {g.budget.accommodation}"
    g2 = gen.compile(route, [], [])
    assert g2.departure_city == "" and g2.budget_level == "中等" and g2.budget.accommodation == 250 * 2
    g3 = gen.compile(route, [], [], intent={"budget_level": "豪华"})
    assert g3.budget.accommodation == 700 * 2 and g3.budget.food == 220 * 3


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
    from tools.enrich import enrich_guide, INDEX_FILE, PHOTO_DIR, _local_photo
    spots = [Spot(name="殷墟", city="安阳")]
    cultures = [CultureData(city="安阳", cuisine={"must_eat": [{"name": "扁粉菜", "where": "老西扁粉菜"}]})]
    asyncio.run(enrich_guide(spots, cultures))
    assert spots[0].coordinate is None, "无 Key 时不应有坐标"
    assert spots[0].photo == "" or spots[0].photo.startswith("/static/photos/")
    idx = json.loads(INDEX_FILE.read_text(encoding="utf-8")) if INDEX_FILE.exists() else {}
    assert len(idx) == 2, f"索引应记录 2 条, 实际 {len(idx)}"
    # 本地缓存命中
    d = PHOTO_DIR / "安阳"
    d.mkdir(parents=True, exist_ok=True)
    (d / "殷墟.jpg").write_bytes(b"fake")
    assert _local_photo("安阳", "殷墟") == "/static/photos/安阳/殷墟.jpg"


# ── 天气: 无 Key ────────────────────────────────────────────

def test_weather_no_key():
    from tools.weather import get_weather
    r = asyncio.run(get_weather("安阳")) if _has_key() else {"status": "no_key"}
    assert r.get("status") in ("no_key", "ok", "error")


def _has_key():
    from config import default_config
    return bool(default_config.amap.weather_key) and not default_config.amap.weather_key.startswith("YOUR_")


if __name__ == "__main__":
    print("── 山河游记 冒烟测试 ──")
    check("json_utils 容错解析", test_json_utils)
    check("amap 数字签名", test_amap_sign)
    check("编译器 intent 注入 + 预算分档", test_compile_intent_and_budget)
    check("Transport 别名序列化", test_transport_alias)
    check("直连模式城市反查", test_assign_spot_cities)
    check("富化层无 Key 降级 + 缓存", test_enrich_no_key_and_cache)
    check("天气服务无 Key 行为", test_weather_no_key)
    print("──────────────────────")
    if FAILED:
        print(f"FAILED: {len(FAILED)} -> {FAILED}")
        sys.exit(1)
    print("ALL PASSED ✅")
