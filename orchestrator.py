"""
编排器 v2 · Dify 工作流 + Python 胶水层

流程:
  用户输入 → Dify意图解析 → Python补默认值
         → Dify路线规划 → Dify内容生成
         → Python编译Markdown → 输出攻略

你建在 Dify 里的三个工作流是"大脑"，
Python 代码是"骨架"，负责串联、补缺、编译。
"""

import json
import os
import asyncio
from datetime import datetime
from typing import Callable, Optional

from models.schemas import TravelIntent, RoutePlan, Spot, CultureData, TravelGuide
from agents.guide_generator import GuideGenerator
from tools.dify_client import DifyClient
from tools.enrich import enrich_guide
from tools.weather import get_weather, clothing_advice
from config import default_config

ProgressCallback = Callable[[int, str, str], None]


class TravelOrchestrator:
    def __init__(self):
        self.dify = DifyClient(default_config)
        self.compiler = GuideGenerator()

    async def generate(self, user_input: str, on_progress=None) -> TravelGuide:
        """完整流程: Dify 意图解析 → 路线规划 → 内容生成"""

        # Step 1: 意图解析
        self._notify(on_progress, 10, "intent", "正在理解需求...")
        raw_intent = await self.dify.call_intent_parser(user_input)
        intent = self._fill_defaults(raw_intent)
        departure_city = intent.get("departure_city", "")
        budget_level = intent.get("budget_level", "中等")
        self._notify(on_progress, 20, "intent",
                     f"目的地: {', '.join(intent['destinations'])} | {intent['days']}天 | {intent['budget_level']}")

        # Step 2: 路线规划
        self._notify(on_progress, 25, "route", "正在规划路线...")
        route_dict = await self.dify.call_route_planner(intent)
        route = RoutePlan(**route_dict)
        self._notify(on_progress, 55, "route", f"路线: {route.route_name}")

        # Step 3: 内容生成 (按城市并行)
        self._notify(on_progress, 60, "content", "正在发掘景点和文化...")
        async def gen_city(city: str):
            try:
                result = await self.dify.call_content_generator(
                    route_json=json.dumps({**route_dict, "cities": [city],
                        "daily_plan": [d for d in route_dict.get("daily_plan", []) if d.get("city") == city]},
                        ensure_ascii=False),
                    preferences=json.dumps(intent.get("preferences", []), ensure_ascii=False),
                )
                return result if isinstance(result, list) else [result]
            except Exception:
                return None

        results = await asyncio.gather(*[gen_city(c) for c in route.cities])
        content_list = []
        for r in results:
            if r: content_list.extend(r)

        spots, cultures = self._split_content(content_list)
        self._notify(on_progress, 85, "content", f"{len(spots)} 景点, {len(cultures)} 城市文化")

        # Step 4: 存知识库
        self._notify(on_progress, 87, "save", "正在充实知识库...")
        self._save_to_obsidian(route.cities, spots, cultures)

        # Step 5: 天气
        self._notify(on_progress, 88, "weather", "正在查询天气...")
        weather_data, clothing_tip, amap_ready = await self._fetch_weather(route.cities)

        # Step 5.5: 富化 (POI 坐标 + 实景图片，失败不阻塞主流程)
        self._notify(on_progress, 89, "enrich", "正在匹配位置与实景图片...")
        try:
            await enrich_guide(spots, cultures)
        except Exception:
            pass

        # Step 6: 编译
        self._notify(on_progress, 90, "compile", "正在生成攻略...")
        guide = self.compiler.compile(route, spots, cultures, intent=intent)
        guide.weather = weather_data
        guide.clothing_tip = clothing_tip
        guide.amap_ready = amap_ready
        self._notify(on_progress, 100, "done", "攻略生成完成！")
        return guide

    def _fill_defaults(self, raw: dict) -> dict:
        """
        补全 LLM 可能漏掉的默认值

        设计思想: LLM 不可靠，默认值逻辑应该 100% 由代码控制。
        Dify 工作流只负责"精确提取"，代码负责"补全缺失"。
        """
        defaults = {
            "days": 3,
            "budget_level": "中等",
            "companion": "独自",
            "pace": "不紧不慢",
            "preferences": [],
            "constraints": [],
        }
        for key, default in defaults.items():
            if not raw.get(key):
                raw[key] = default
        return raw

    def _split_content(self, content_list: list) -> tuple[list[Spot], list[CultureData]]:
        """把内容生成器返回的 [{city, spots, culture}] 拆成两个列表"""
        spots = []
        cultures = []
        for item in content_list:
            if isinstance(item, dict):
                city = item.get("city", "")
                if "spots" in item:
                    for s in item["spots"]:
                        try:
                            spot = Spot(**s)
                            spot.city = city          # 景点归属城市，富化时按城市搜 POI
                            spots.append(spot)
                        except Exception:
                            pass
                if "culture" in item:
                    try:
                        cultures.append(CultureData(city=item.get("city", ""), **item["culture"]))
                    except Exception:
                        pass
        return spots, cultures

    def _notify(self, callback, progress, stage, message):
        if callback:
            try:
                callback(progress, stage, message)
            except Exception:
                pass

    async def _fetch_weather(self, cities: list[str]) -> tuple[list[dict], str, bool]:
        """查询所有城市的天气，返回 (天气列表, 穿衣建议, 高德是否就绪)"""
        weather_list = []
        all_forecasts = []
        amap_ready = bool(default_config.amap.weather_key)

        if not amap_ready:
            return [], "", False

        async def _one(city: str) -> dict:
            try:
                return await get_weather(city)
            except Exception:
                return {"status": "error", "city": city}

        weather_list = list(await asyncio.gather(*[_one(c) for c in cities]))
        for w in weather_list:
            if w.get("status") == "ok" and w.get("forecast"):
                all_forecasts.extend(w["forecast"])

        clothing = clothing_advice(all_forecasts) if all_forecasts else ""
        return weather_list, clothing, amap_ready

    def _save_to_obsidian(self, cities: list[str], spots: list, cultures: list):
        """把 Dify 内容生成器的输出存入 Obsidian 知识库（未配置目录则跳过）"""
        obsidian_base = default_config.obsidian_kb_dir
        if not obsidian_base:
            return
        os.makedirs(obsidian_base, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")

        # 按城市分别存
        for culture in cultures:
            city = culture.city
            city_dir = os.path.join(obsidian_base, city)
            os.makedirs(city_dir, exist_ok=True)

            # 只存该城市的景点
            city_spots = [s for s in spots if hasattr(s, 'name')]

            md = f"""---
tags: [旅游, 知识库, {city}]
created: {today}
source: Dify 内容生成器
---

# {city} · 旅游数据

> 自动采集 · {today}

## 景点 ({len(city_spots)} 处)

"""
            for s in city_spots[:10]:
                md += f"- **{s.name}** | {s.type} | ⏱{s.duration} | 🎫¥{s.ticket}\n"
                if s.tags:
                    md += f"  {' '.join('#' + t for t in s.tags)}\n"
                if s.tips:
                    md += f"  > {s.tips}\n"
                if s.nearby_food:
                    md += f"  🍜 {', '.join(s.nearby_food[:3])}\n"
                md += "\n"

            # 美食
            must_eat = culture.cuisine.get("must_eat", [])
            if must_eat:
                md += "## 美食\n\n"
                for f in must_eat[:8]:
                    md += f"- **{f.get('name','')}** — {f.get('reason','')}\n"
                    md += f"  📍 {f.get('where','')} | ¥{f.get('price_per_person',0)}/人\n"
                    if f.get('tips'):
                        md += f"  > {f.get('tips')}\n"
                    md += "\n"

            # 文化
            fc = culture.folk_culture
            if fc:
                md += "## 民俗文化\n\n"
                if fc.get("architecture"):
                    md += f"**建筑**: {fc['architecture']}\n\n"
                for d in fc.get("dialect", [])[:5]:
                    md += f"- **{d.get('phrase','')}** ({d.get('pinyin','')}) — {d.get('meaning','')}\n"
                md += "\n"

            if culture.festivals:
                md += "## 节庆\n\n"
                for f in culture.festivals[:3]:
                    md += f"- **{f.get('name','')}** ({f.get('date','')}) — {f.get('what_to_see','')}\n"
                md += "\n"

            if culture.taboos:
                md += "## 禁忌\n\n"
                for t in culture.taboos[:3]:
                    md += f"- {t.get('rule','')}\n"
                md += "\n"

            if culture.history:
                md += "## 历史典故\n\n"
                for h in culture.history[:3]:
                    md += f"- {h.get('story','')}\n"
                md += "\n"

            filepath = os.path.join(city_dir, f"{city}_{today}.md")
            with open(filepath, "w", encoding="utf-8") as fh:
                fh.write(md)

        # 全局索引文件
        index_md = f"""---
tags: [旅游, 知识库, 索引]
updated: {today}
---

# 旅游数据索引

> 自动采集，每次生成攻略后更新

## 已收录城市

"""
        for city_dir_name in sorted(os.listdir(obsidian_base)):
            full = os.path.join(obsidian_base, city_dir_name)
            if os.path.isdir(full):
                md_files = [fn for fn in os.listdir(full) if fn.endswith(".md")]
                for fn in md_files:
                    index_md += f"- [[旅游数据/{city_dir_name}/{fn.replace('.md','')}|{city_dir_name}]] ({len(md_files)} 次采集)\n"

        with open(os.path.join(obsidian_base, "_索引.md"), "w", encoding="utf-8") as fh:
            fh.write(index_md)
