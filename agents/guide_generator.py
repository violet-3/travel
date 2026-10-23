"""攻略生成器 · 所有数据 → TravelGuide 与 Markdown

将 RoutePlan + Spots + CultureData 编译为:
1. 结构化 TravelGuide（含确定性预算估算）
2. 可直接保存或粘贴到笔记软件的 Markdown 攻略
"""

from datetime import datetime, timedelta, timezone
import ipaddress
import re
from urllib.parse import quote, urlsplit

from models.schemas import RoutePlan, Spot, CultureData, BudgetBreakdown, TravelGuide, TravelIntent


class GuideGenerator:
    """
    攻略生成器

    这不是一个 LLM Agent，而是纯模板编译引擎。
    因为到这个阶段，所有创意性内容已经由前面的 Agent 生成了，
    这里只需要把数据填入模板。
    """

    def compile(
        self,
        route: RoutePlan,
        spots: list[Spot],
        cultures: list[CultureData],
        intent: "TravelIntent | dict | None" = None,
    ) -> TravelGuide:
        """编译所有数据为最终攻略

        intent 可传 TravelIntent 实例或兼容字典，用于保留本次实际采用的用户条件。
        """

        def _from_intent(key: str, default: str = "") -> str:
            if intent is None:
                return default
            if isinstance(intent, dict):
                return intent.get(key) or default
            return getattr(intent, key, default) or default

        if isinstance(intent, TravelIntent):
            request = intent
        elif isinstance(intent, dict):
            request = TravelIntent.model_validate(intent)
        else:
            request = None

        budget = self._calculate_budget(
            route, _from_intent("budget_level", "中等"), request=request, spots=spots
        )
        days = len(route.daily_plan)

        return TravelGuide(
            title=f"《{route.route_name}》",
            subtitle=f"{' → '.join(route.cities)} · {days}天{max(days - 1, 0)}晚",
            destinations=route.cities,
            days=days,
            departure_city=_from_intent("departure_city"),
            budget_level=_from_intent("budget_level", "中等"),
            request=request,
            route=route,
            spots=spots,
            cultures=cultures,
            budget=budget,
        )

    def to_markdown(self, guide: TravelGuide) -> str:
        """把 TravelGuide 编译为 Markdown 字符串"""
        md = []

        def verification_date(value) -> str:
            if not value:
                return ""

        def verification_timestamp(value) -> str:
            if not value:
                return ""
            try:
                parsed = datetime.fromisoformat(str(value))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M %Z")
            except (TypeError, ValueError, OverflowError):
                return ""
            try:
                parsed = datetime.fromisoformat(str(value))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
            except (TypeError, ValueError, OverflowError):
                return ""

        def markdown_text(value) -> str:
            text = str(value or "").replace("\r", " ").replace("\n", " ")
            return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text)

        def markdown_url(value) -> str:
            value = str(value or "")
            try:
                parts = urlsplit(value)
                _ = parts.port
            except ValueError:
                return ""
            if (parts.scheme.lower() not in {"http", "https"} or not parts.hostname
                    or parts.username is not None or parts.password is not None
                    or any(ord(char) < 0x21 for char in value)):
                return ""
            host = parts.hostname.lower().rstrip(".")
            if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
                return ""
            try:
                if not ipaddress.ip_address(host).is_global:
                    return ""
            except ValueError:
                pass
            return quote(value, safe=":/?&=#%+-._~")

        def markdown_link(label, value):
            url = markdown_url(value)
            if not url:
                return markdown_text(label) + "（来源链接无效）"
            return f"[{markdown_text(label)}]({url})"

        # ─── 标题 ───
        md.append(f"# {guide.title}")
        md.append(f"> {guide.subtitle}")
        md.append("")

        # ─── 速览表 ───
        md.append("## 📋 速览")
        md.append("")
        md.append("| 项目 | 详情 |")
        md.append("|------|------|")
        md.append(f"| 行程天数 | {guide.days}天{guide.days-1}晚 |")
        md.append(f"| 途经城市 | {' → '.join(guide.destinations)} |")
        md.append(f"| 人均已知费用小计 | ¥{guide.budget.total} |")
        md.append(f"| 旅行节奏 | {guide.request.pace if guide.request else '不紧不慢'} |")
        md.append("")
        md.append("> 信息边界：门票、人均餐费与游览时长为参考估算；营业时间、预约要求和无障碍设施未经官方核验，出行前请向景区或商家确认。图片可能是实景图、位置示意图或来源未明的本地图片，具体以来源标记为准。")
        md.append("")

        research = guide.web_research
        md.append("## 🌐 联网来源状态")
        md.append("")
        if research.status == "disabled":
            md.append("本次联网 Search/Fetch 已关闭，未发起网页请求。")
        else:
            md.append(
                f"状态：{research.status}；Search {research.search_count} 次，"
                f"Fetch {research.fetch_count} 次。{markdown_text(research.message)}"
            )
            md.append("网页内容属于线索，景点归属、机构属性、票种、适用日期及图片授权均未由本系统核验；网页票价不计入预算。")
        md.append("")

        if guide.request:
            md.append("## 本次需求摘要")
            md.append("")
            request = guide.request
            md.append(f"- 目的地：{'、'.join(request.destinations) or '未注明'}")
            md.append(f"- 出发地：{request.departure_city or '未注明'}")
            md.append(f"- 出行时间：{request.travel_date_note or request.travel_date or '未指定'}")
            md.append(f"- 同行人数：{request.travelers}人")
            budget = f"¥{request.budget}" if request.budget is not None else "未指定"
            scope = "全体总额" if request.budget_scope == "total" else "人均"
            md.append(f"- 预算：{budget}（{scope}）")
            md.append(f"- 硬约束：{'、'.join(request.constraints) or '无'}")
            md.append("")

        # ─── 路线总览 ───
        md.append("## 🗺️ 路线总览")
        md.append("")
        md.append("```")
        for t in guide.route.transport:
            md.append(f"{t.from_city} ──{t.mode}({t.duration})──▶ {t.to_city}")
        md.append("```")
        md.append("")

        # ─── 每日详情 ───
        md.append("## 📅 每日详情")
        md.append("")
        for day in guide.route.daily_plan:
            md.append(f"### Day {day.day}：{day.city}")
            md.append("")
            if day.morning.name:
                md.append(f"**☀️ 上午**: {day.morning.name}")
                if day.morning.note:
                    md.append(f"  > {day.morning.note}")
                md.append("")
            if day.afternoon.name:
                md.append(f"**🌤️ 下午**: {day.afternoon.name}")
                if day.afternoon.note:
                    md.append(f"  > {day.afternoon.note}")
                md.append("")
            if day.evening.name:
                md.append(f"**🌙 晚上**: {day.evening.name}")
                if day.evening.note:
                    md.append(f"  > {day.evening.note}")
                md.append("")
            if day.stay:
                md.append(f"**🏨 住宿**: {day.stay}")
                md.append("")

        # ─── 景点推荐 ───
        if guide.spots:
            research_rows = {
                row.spot_index: row for row in getattr(guide.web_research, "spots", [])
            }
            md.append("## 📸 推荐景点")
            md.append("")
            for tier_name, tier_num in [("🏅 必去经典", 1), ("🔍 深度体验", 2), ("💎 小众宝藏", 3)]:
                tier_spots = [(i, s) for i, s in enumerate(guide.spots) if s.tier == tier_num]
                if tier_spots:
                    md.append(f"### {tier_name}")
                    md.append("")
                    for spot_index, spot in tier_spots[:10]:
                        web_spot = research_rows.get(spot_index)
                        web_status = web_spot.status if web_spot else guide.web_research.status
                        web_evidence = web_spot.evidence if web_spot else []
                        if spot.ticket_status == "free":
                            ticket = "模型标记免费，待核实"
                        elif spot.ticket and spot.ticket > 0:
                            ticket = f"模型参考价 ¥{spot.ticket}，待核实"
                        else:
                            ticket = "待核实"
                        md.append(f"**{spot.name}** | {spot.type} | ⏱️ {spot.duration or '时长待确认'}（参考） | 🎫 门票{ticket}")
                        photo_labels = {
                            "amap_poi_photo": "高德 POI 图片",
                            "wikimedia_commons": "Wikimedia Commons 图片",
                            "static_map": "高德位置示意图（非实景照片）",
                            "deepseek_web_image": "网页图片（内容匹配与授权未核验）",
                            "local_unknown": "本地图片（来源未核实）",
                            "none": "暂无图片",
                        }
                        location_label = "高德 POI 已核对" if spot.coordinate_verified else "位置待核对"
                        photo_date = verification_date(spot.photo_checked_at)
                        coordinate_date = verification_date(spot.coordinate_checked_at)
                        photo_label = photo_labels.get(spot.photo_source, "来源待核实")
                        if photo_date and spot.photo_source not in {"local_unknown", "none"}:
                            photo_label += f"（获取于 {photo_date}）"
                        if coordinate_date and spot.coordinate_verified:
                            location_label += f"（{coordinate_date}）"
                        md.append(f"  图片：{photo_label}；位置：{location_label}（仅核对位置）。门票、开放时间、预约与无障碍信息未做官方核验。")
                        if spot.tags:
                            md.append(f"  {' · '.join(['#' + t for t in spot.tags])}")
                        if spot.tips:
                            md.append(f"  > 💡 {spot.tips}")
                        if spot.photo_spots:
                            for ps in spot.photo_spots[:2]:
                                md.append(f"  - 📷 {ps.name} — {ps.best_time} ({ps.shot})")
                        if web_status == "disabled":
                            md.append("  网页资料：本次未检索（联网检索已关闭）。")
                        elif web_status == "unavailable":
                            md.append("  网页资料：联网检索已启用，但没有可用凭据；本景点未检索。")
                        elif web_status == "skipped_limit":
                            md.append("  网页资料：超过本次 3 个景点上限，未检索。")
                        elif web_status == "no_city_match":
                            md.append("  网页资料：未找到可在标题、摘要或页面路径中匹配此城市的结果。")
                        elif web_status == "no_spot_match":
                            md.append("  网页资料：同城结果未匹配景点名称，未采纳票价或图片。")
                        elif web_status == "page_unmatched":
                            md.append("  网页资料：抓取页未匹配目标城市与景点名称，未采纳该页票价或图片。")
                        elif web_status == "no_results":
                            md.append("  网页资料：本次未检索到结果。")
                        for evidence in web_evidence:
                            md.append(
                                f"  网页来源：{markdown_link(evidence.title or '网页来源', evidence.url)}"
                                f"（{verification_timestamp(evidence.fetched_at) or '仅搜索结果，未抓取正文'}；"
                                "机构属性与官方性未核验）"
                            )
                            if evidence.snippet:
                                md.append(f"    搜索摘要（非网页原文）：{markdown_text(evidence.snippet)}")
                            if evidence.price_quotes:
                                md.append("    网页票价线索（票种、日期与适用条件待核实，不计入预算）：")
                                for line in evidence.price_quotes[:5]:
                                    md.append(f"    - {markdown_text(line)}")
                            if evidence.quotes:
                                md.append("    页面摘录（逐字截取；未核验适用性）：")
                                for line in evidence.quotes[:8]:
                                    md.append(f"    > {markdown_text(line)}")
                            if evidence.fetch_status == "mismatch":
                                md.append("    抓取正文与目标景点不匹配，正文中的票价和图片未采纳。")
                            if evidence.image_candidates:
                                md.append("    图片候选（从来源页提取；内容关联和授权未核验）：")
                                for candidate in evidence.image_candidates[:5]:
                                    label = candidate.alt or "页面图片候选"
                                    md.append(f"    - {markdown_link(label, candidate.url)}")
                                    if re.fullmatch(r"/static/photos/web-research/[0-9a-f]{64}\.(?:jpg|png|webp|gif)", candidate.local_url or ""):
                                        md.append(f"      本机缓存图：[{markdown_text('查看缓存图片')}]({candidate.local_url})（离开本机后链接可能不可用）")
                            elif evidence.status == "fetched":
                                md.append("    来源页未提取到可用图片链接；未使用网站图标作为景点照片。")
                        md.append("")

        # ─── 风土人情 ───
        if guide.cultures:
            md.append("## 🎭 风土人情")
            md.append("")
            for culture in guide.cultures:
                md.append(f"### {culture.city}")
                md.append("")

                # 美食
                must_eat = culture.cuisine.get("must_eat", [])
                if must_eat:
                    md.append("#### 🍜 必吃清单")
                    md.append("")
                    md.append("| 美食 | 去哪吃 | 人均估算 | 图片与位置来源 | 推荐理由 |")
                    md.append("|------|--------|----------|----------------|---------|")
                    for food in must_eat[:6]:
                        price = food.get('price_per_person')
                        price_label = f"约¥{price}" if price else "待确认"
                        source = {
                            "amap_poi_photo": "高德 POI 图片",
                            "wikimedia_commons": "Wikimedia 图片",
                            "static_map": "位置示意图（非实景）",
                            "local_unknown": "本地图片（来源未核实）",
                            "none": "暂无图片",
                        }.get(food.get("photo_source"), "图片来源待核实")
                        photo_date = verification_date(food.get("photo_checked_at"))
                        coordinate_date = verification_date(food.get("coordinate_checked_at"))
                        if photo_date and food.get("photo_source") not in {"local_unknown", "none"}:
                            source += f"，获取于 {photo_date}"
                        source += "；位置" + (f"由高德 POI 核对（{coordinate_date}）" if food.get("coordinate_verified") and coordinate_date else "由高德 POI 核对" if food.get("coordinate_verified") else "待核对")
                        md.append(f"| {food.get('name', '')} | {food.get('where', '')} | {price_label} | {source} | {food.get('reason', '')} |")
                    md.append("")

                # 民俗
                folk = culture.folk_culture
                if folk.get("architecture"):
                    md.append(f"**🏛️ 建筑**: {folk['architecture']}")
                    md.append("")
                if folk.get("dialect"):
                    md.append("**🗣️ 方言**:")
                    for d in folk["dialect"][:3]:
                        md.append(f"- **{d.get('phrase', '')}** ({d.get('pinyin', '')}) — {d.get('meaning', '')}（{d.get('usage', '')}）")
                    md.append("")

                # 节庆
                if culture.festivals:
                    md.append("**🎪 节庆**:")
                    for f in culture.festivals[:3]:
                        md.append(f"- {f.get('name','')}（{f.get('date','')}）— {f.get('what_to_see','')}")
                    md.append("")

                # 禁忌
                if culture.taboos:
                    md.append("**⚠️ 礼仪禁忌**:")
                    for t in culture.taboos[:3]:
                        md.append(f"- {t.get('rule','')}（{t.get('context','')}）")
                    md.append("")

        # ─── 预算 ───
        md.append("## 💰 预算明细")
        md.append("")
        md.append("| 项目 | 费用 |")
        md.append("|------|------|")
        md.append(f"| 已知城际交通 | ¥{guide.budget.transport} / 人 |")
        md.append(f"| 住宿（{guide.budget.nights}晚） | ¥{guide.budget.accommodation} / 人 |")
        if (guide.budget.tickets_known or guide.budget.tickets_estimated
                or guide.budget.tickets_free_spots):
            ticket_detail = (
                f"（模型参考价 ¥{guide.budget.tickets_known} + 未知估算 ¥{guide.budget.tickets_estimated}"
                f" + 明确标记免费 {len(guide.budget.tickets_free_spots)} 处）"
            )
        else:
            ticket_detail = ""
        md.append(f"| 门票估算{ticket_detail} | ¥{guide.budget.tickets} / 人 |")
        md.append(f"| 餐饮估算 | ¥{guide.budget.food} / 人 |")
        md.append(f"| 其他估算 | ¥{guide.budget.other} / 人 |")
        md.append(f"| **人均已知费用小计** | **¥{guide.budget.total}** |")
        md.append(f"| **{guide.budget.travelers}人团体已知小计** | **¥{guide.budget.group_total}** |")
        if guide.budget.cost_share:
            parts = []
            for key, label in (
                ("transport", "交通"), ("accommodation", "住宿"), ("tickets", "门票"),
                ("food", "餐饮"), ("other", "其他"),
            ):
                value = guide.budget.cost_share.get(key)
                if value:
                    parts.append(f"{label} {value * 100:.0f}%")
            if parts:
                md.append("")
                md.append("费用结构：" + " · ".join(parts) + "（占人均已知小计）")
        if guide.budget.tickets_pending_spots:
            md.append("")
            md.append("以下匹配到的推荐景点未提供门票价格，暂按每处"
                      f"¥{GuideGenerator._TICKET_FALLBACK_PER_SPOT}估算，需行前核实：")
            for name in guide.budget.tickets_pending_spots[:10]:
                md.append(f"- 门票待核实：{name}")
        if guide.budget.tickets_free_spots:
            md.append("")
            md.append("模型标记为免费的推荐景点（尚未做官方核验）：")
            for name in guide.budget.tickets_free_spots[:10]:
                md.append(f"- 免费参考：{name}")
        if guide.budget.tickets_unpriced_activities:
            md.append("")
            md.append("以下行程活动未匹配到同城推荐景点，门票未计入；请确认是否收费：")
            for name in guide.budget.tickets_unpriced_activities[:10]:
                md.append(f"- 门票未覆盖：{name}")
        if guide.budget.transport_unknown_segments:
            md.append("")
            md.append("以下交通费用未计入小计，需补充实际出发地、班次与报价：")
            for segment in guide.budget.transport_unknown_segments:
                md.append(f"- 待核价：{segment}")
        if guide.budget.estimate_notes:
            md.append("")
            md.append("估算口径：")
            for note in guide.budget.estimate_notes:
                md.append(f"- {note}")
        if guide.budget.budget_status == "over_known_budget":
            md.append("")
            md.append("**提示：已知费用估算已超过需求预算。**")
        elif guide.budget.budget_status == "needs_transport_quote" and guide.request and guide.request.budget:
            md.append("")
            md.append("**提示：交通仍有待核价项目，当前不能确认符合需求预算。**")
        elif guide.budget.budget_status == "needs_price_review":
            md.append("")
            md.append("**提示：部分行程活动的门票未覆盖，当前小计不完整，不能确认符合预算。**")
        elif guide.budget.budget_status == "within_estimate":
            md.append("")
            md.append("**提示：已知费用估算在需求预算范围内；这不是最终报价，未核价交通费用另计。**")
        md.append("")

        # ─── 行程可执行性 ───
        feasibility = guide.feasibility or {}
        if feasibility.get("checked"):
            md.append("## 🚶 行程可执行性")
            md.append("")
            md.append(
                f"可执行性评分：**{feasibility.get('score', 100)} / 100**"
                f"（等级 {feasibility.get('level', 'A')}）"
            )
            md.append("")
            rows = [day for day in feasibility.get("days", []) if day.get("distance_km") is not None]
            if rows:
                md.append("| 天 | 城市 | 活动数 | 当天在途 | 最长一段 | 粗估耗时 |")
                md.append("|---|---|---|---|---|---|")
                for day in rows:
                    md.append(
                        f"| Day {day.get('day')} | {day.get('city', '')} | "
                        f"{day.get('activities', 0)} | {day.get('distance_km')} km | "
                        f"{day.get('max_leg_km')} km | {day.get('estimated_hours')} h |"
                    )
                md.append("")
            for note in feasibility.get("notes", []):
                md.append(f"- {note}")
            md.append("")
            if feasibility.get("issues"):
                md.append("需要留意：")
                for issue in feasibility["issues"]:
                    md.append(f"- {issue}")
                md.append("")
        elif feasibility.get("notes"):
            md.append("## 🚶 行程可执行性")
            md.append("")
            for note in feasibility["notes"]:
                md.append(f"- {note}")
            md.append("")

        # ─── 行前准备 ───
        prep = guide.prep or {}
        if prep.get("packing") or prep.get("weather_plans"):
            md.append("## 🎒 行前准备")
            md.append("")
            temp_range = prep.get("temperature_range")
            if temp_range:
                md.append(
                    f"预报温度区间：**{temp_range.get('low')}~{temp_range.get('high')}℃**"
                    "（出发前 1 天请再确认）"
                )
                md.append("")
            plans = [plan for plan in prep.get("weather_plans", []) if plan.get("status") == "ok"]
            if plans:
                md.append("### 逐日应变")
                md.append("")
                for plan in plans:
                    label = f"**Day {plan.get('day')} · {plan.get('city', '')}"
                    if plan.get("weather"):
                        label += f"（{plan['weather']}）"
                    md.append(label + "**")
                    for advice in plan.get("advice", []):
                        md.append(f"- {advice}")
                    md.append("")
            for group in prep.get("packing", []):
                md.append(f"### {group.get('group', '')}")
                md.append("")
                if group.get("basis"):
                    md.append(f"> {group['basis']}")
                    md.append("")
                for item in group.get("items", []):
                    md.append(f"- {item}")
                md.append("")
            if prep.get("notes"):
                md.append("说明：")
                for note in prep["notes"]:
                    md.append(f"- {note}")
                md.append("")

        # ─── 注意事项 ───
        if guide.route.warnings:
            md.append("## ⚠️ 注意事项")
            md.append("")
            for w in guide.route.warnings:
                md.append(f"- {w}")
            md.append("")

        # ─── 质量自检 ───
        quality = guide.quality or {}
        if quality.get("score") is not None:
            md.append("## 🔎 攻略自检")
            md.append("")
            md.append(
                f"综合 **{quality.get('score')} / 100**（等级 {quality.get('grade', '-')}）"
            )
            md.append("")
            md.append("| 维度 | 得分 | 权重 |")
            md.append("|---|---|---|")
            for dimension in (quality.get("dimensions") or {}).values():
                weight = dimension.get("weight")
                weight_label = f"{round(float(weight) * 100)}%" if weight is not None else "-"
                md.append(
                    f"| {dimension.get('label', '')} | {dimension.get('score', '-')} | {weight_label} |"
                )
            md.append("")
            if quality.get("issues"):
                md.append("可改进项：")
                for issue in quality["issues"]:
                    md.append(f"- {issue}")
                md.append("")
            for note in quality.get("notes", []):
                md.append(f"> {note}")
            md.append("")

        # ─── 页脚 ───
        md.append("---")
        md.append(f"*攻略由 TravelAgent AI 生成 · {guide.generated_at[:10]}*")

        return "\n".join(md)

    # 住宿/餐饮日标准 (元/晚, 元/天)，按预算级别分档
    _LEVEL_RATES = {
        "经济": (120, 50),
        "中等": (250, 80),
        "舒适": (400, 130),
        "豪华": (700, 220),
    }

    # 住宿基准价是全国均值，按城市等级折算。只列明确城市，未列出的按 1.0，
    # 不对未知城市臆测物价。
    _CITY_LODGING_FACTOR = {
        "北京": 1.50, "上海": 1.50, "深圳": 1.45, "广州": 1.35, "三亚": 1.45,
        "杭州": 1.30, "南京": 1.25, "厦门": 1.25, "苏州": 1.20, "成都": 1.20,
        "青岛": 1.20, "重庆": 1.15, "西安": 1.15, "宁波": 1.15, "丽江": 1.10,
        "武汉": 1.10, "长沙": 1.10, "大连": 1.10, "天津": 1.05, "昆明": 1.05,
        "福州": 1.05, "济南": 1.00, "郑州": 1.00, "桂林": 1.00, "合肥": 0.95,
        "哈尔滨": 0.95, "沈阳": 0.95, "南昌": 0.95, "贵阳": 0.95, "南宁": 0.95,
        "长春": 0.90, "太原": 0.90, "兰州": 0.90, "洛阳": 0.85,
        "开封": 0.85, "安阳": 0.80,
    }

    # 行程活动中没有明确标价的门票，按此单价兜底估算
    _TICKET_FALLBACK_PER_SPOT = 100

    @classmethod
    def _lodging_factor(cls, city: str) -> float:
        normalized = cls._normalize_city_key(city)
        return cls._CITY_LODGING_FACTOR.get(normalized, 1.0)

    @staticmethod
    def _normalize_city_key(value: str) -> str:
        text = "".join(str(value or "").split())
        for suffix in ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区",
                       "自治区", "自治州", "地区", "省", "市"):
            if text.endswith(suffix):
                return text[:-len(suffix)]
        return text

    @staticmethod
    def _normalize_spot_name(value: str) -> str:
        text = re.sub(r"[\s·,，。;；:：()（）\[\]【】]", "", str(value or ""))
        for prefix in ("前往", "参观", "遊覽", "游览", "游玩", "打卡"):
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        return text

    @staticmethod
    def _is_non_ticket_activity(value: str) -> bool:
        # Only exempt complete generic activity labels. Substring checks hide
        # named attractions such as “拙政园散步” from the uncovered-price list.
        normalized = GuideGenerator._normalize_spot_name(value)
        return normalized in {
            "早餐", "午餐", "晚餐", "用餐", "用餐时间", "用餐時間",
            "散步", "步行", "自由活动", "自由活動", "自由安排", "自由时间", "自由時間",
            "休息", "乘车", "乘車", "公共交通", "交通", "返程", "办理入住", "辦理入住",
            "酒店入住", "前往酒店",
        }

    @classmethod
    def _match_spot(cls, activity_name: str, city: str, spots: list[Spot]) -> Spot | None:
        """Conservatively match a day's activity to a spot in the same city."""
        target = cls._normalize_spot_name(activity_name)
        city_key = cls._normalize_city_key(city)
        if not target or not city_key:
            return None
        for spot in spots:
            candidate = cls._normalize_spot_name(spot.name)
            spot_city = cls._normalize_city_key(spot.city)
            if spot_city == city_key and candidate and candidate == target:
                return spot
        return None

    def _ticket_estimate(
        self, route: RoutePlan, spots: list[Spot]
    ) -> tuple[int, int, int, list[str], list[str], list[str]]:
        """Estimate tickets only for uniquely matched recommended attractions."""
        fallback = self._TICKET_FALLBACK_PER_SPOT
        seen: set[tuple[str, str]] = set()
        priced: dict[tuple[str, str], int] = {}
        pending: list[str] = []
        free: list[str] = []
        unpriced: list[str] = []
        unpriced_seen: set[tuple[str, str]] = set()
        for day in route.daily_plan:
            for activity in (day.morning, day.afternoon, day.evening):
                name = (getattr(activity, "name", "") or "").strip()
                if not name:
                    continue
                spot = self._match_spot(name, day.city, spots)
                if spot is None:
                    # Do not infer a charge, but keep potentially ticketed
                    # activities visible so the subtotal is not mistaken as complete.
                    unpriced_key = (
                        self._normalize_city_key(day.city), self._normalize_spot_name(name)
                    )
                    if (not self._is_non_ticket_activity(name)
                            and unpriced_key not in unpriced_seen):
                        unpriced_seen.add(unpriced_key)
                        unpriced.append(f"{day.city} · {name}" if day.city else name)
                    continue
                identity = (
                    self._normalize_city_key(spot.city),
                    self._normalize_spot_name(spot.name),
                )
                if identity in seen:
                    continue
                seen.add(identity)
                label = f"{day.city} · {spot.name}"
                if spot.ticket_status == "free":
                    free.append(label)
                elif spot.ticket and spot.ticket > 0:
                    priced[identity] = int(spot.ticket)
                else:
                    pending.append(label)

        known = sum(priced.values())
        estimated = fallback * len(pending)
        total = known + estimated
        return total, known, estimated, pending, free, unpriced

    def _calculate_budget(
        self, route: RoutePlan, level: str = "中等", request: TravelIntent | None = None,
        spots: list[Spot] | None = None,
    ) -> BudgetBreakdown:
        """Return a per-person known-cost estimate and keep unknown transport separate."""
        days = len(route.daily_plan)
        nights = max(days - 1, 0)
        travelers = request.travelers if request else 1
        night_rate, food_rate = self._LEVEL_RATES.get(level, self._LEVEL_RATES["中等"])

        transport = sum(t.cost_est or 0 for t in route.transport if t.cost_est is not None)
        unknown_segments = []
        for transit in route.transport:
            if transit.cost_est is None:
                label = f"{transit.from_city}→{transit.to_city}城际交通".strip("→ ")
                if label and label not in unknown_segments:
                    unknown_segments.append(label)

        day_cities = [day.city.strip() for day in route.daily_plan if day.city.strip()]
        departure_city = request.departure_city.strip() if request and request.departure_city else ""
        first_city = day_cities[0] if day_cities else "首站"
        last_city = day_cities[-1] if day_cities else "末站"
        same_start = departure_city and self._same_city(departure_city, first_city)
        same_end = departure_city and self._same_city(departure_city, last_city)
        if not same_start and departure_city and not self._has_transport(
            route, departure_city, first_city
        ):
            segment = f"{departure_city}→{first_city}首站交通"
            if segment not in unknown_segments:
                unknown_segments.append(segment)
        elif not departure_city:
            segment = f"出发地→{first_city}首站交通"
            if segment not in unknown_segments:
                unknown_segments.append(segment)
        if not same_end and departure_city and not self._has_transport(
            route, last_city, departure_city
        ):
            segment = f"{last_city}→{departure_city}返程交通"
            if segment not in unknown_segments:
                unknown_segments.append(segment)
        elif not departure_city:
            segment = f"{last_city}→出发地返程交通"
            if segment not in unknown_segments:
                unknown_segments.append(segment)

        # Lodging is per person per night; a same-day trip has zero lodging nights.
        # Each night is priced with the tier factor of the city actually stayed in.
        lodging_cities: list[str] = []
        accommodation = 0
        for index in range(nights):
            city = day_cities[min(index, len(day_cities) - 1)] if day_cities else ""
            factor = self._lodging_factor(city)
            accommodation += round(night_rate * factor)
            if city:
                lodging_cities.append(city)

        (tickets, tickets_known, tickets_estimated, tickets_pending,
         tickets_free, tickets_unpriced) = self._ticket_estimate(
            route, spots or []
        )

        food = food_rate * days

        # 其他
        other = 50 * days

        total = transport + accommodation + tickets + food + other
        group_total = total * travelers
        budget_status = "no_budget"

        def add_warning_once(message: str) -> None:
            if message not in route.warnings:
                route.warnings.append(message)

        if tickets_unpriced:
            add_warning_once("有行程活动未覆盖门票价格，当前费用小计不完整，请核实是否收费。")

        if request and request.budget is not None:
            if request.budget_scope == "total":
                over_budget = group_total > request.budget
            else:
                over_budget = total > request.budget
            if over_budget:
                budget_status = "over_known_budget"
                scope = "团体" if request.budget_scope == "total" else "人均"
                add_warning_once(
                    f"已知费用估算{scope}¥{group_total if request.budget_scope == 'total' else total}"
                    f"，已超过需求预算¥{request.budget}；待核价交通另计。"
                )
            elif unknown_segments:
                budget_status = "needs_transport_quote"
                add_warning_once("仍有交通费用待核价，当前不能确认是否符合需求预算。")
            elif tickets_unpriced:
                budget_status = "needs_price_review"
                add_warning_once("有行程活动未覆盖门票价格，当前不能确认总费用是否符合预算。")
            else:
                budget_status = "within_estimate"
        elif unknown_segments:
            budget_status = "needs_transport_quote"
        elif tickets_unpriced:
            budget_status = "needs_price_review"
            add_warning_once("有行程活动未覆盖门票价格，当前费用小计不完整。")

        notes = [
            f"住宿按每人每晚基准¥{night_rate}估算，再按过夜城市等级折算，共{nights}晚；一日游住宿按0晚。",
            f"餐饮按每人每天¥{food_rate}估算，其他按每人每天¥50估算。",
            "各项为粗略规划估算，不是实时价格或商家报价。",
            "已知费用小计不含任何待核价交通段。",
        ]
        notes.append(
            "门票金额来自模型参考或估算，未做官方核验；仅统计按城市与名称精确匹配的推荐景点，"
            "其他活动不自动认定收费。"
        )
        if tickets_known or tickets_estimated:
            notes.append(
                f"门票按已安排且匹配的推荐景点累计：模型参考价¥{tickets_known}"
                f"，未知价格按每处¥{self._TICKET_FALLBACK_PER_SPOT}估算¥{tickets_estimated}。"
            )
        if tickets_free:
            notes.append(f"模型标记免费 {len(tickets_free)} 处，未做官方核验且未计入门票费用。")
        if tickets_unpriced:
            notes.append(
                f"有{len(tickets_unpriced)}项行程活动未能匹配到同城推荐景点，门票未计入；"
                "需核实活动是否收费，当前费用小计不能视为完整总额。"
            )
        if lodging_cities:
            mixed = "、".join(dict.fromkeys(lodging_cities))
            notes.append(f"过夜城市：{mixed}；不同城市按各自等级系数折算，未列入的城市按基准价。")
            if nights:
                notes.append(f"折算后平均每人每晚约¥{round(accommodation / nights)}。")
        notes.append(f"团体已知小计按人均已知小计×{travelers}人计算。")

        cost_share = {}
        if total > 0:
            cost_share = {
                key: round(value / total, 3)
                for key, value in (
                    ("transport", transport), ("accommodation", accommodation),
                    ("tickets", tickets), ("food", food), ("other", other),
                )
            }
            if cost_share.get("transport", 0) > 0.45:
                add_warning_once(
                    f"已列明的城际交通占人均已知费用约{cost_share['transport'] * 100:.0f}%，"
                    "如与实际票价差异较大，请以铁路或航司报价为准。"
                )

        return BudgetBreakdown(
            transport=transport,
            accommodation=accommodation,
            tickets=tickets,
            food=food,
            other=other,
            total=total,
            group_total=group_total,
            travelers=travelers,
            nights=nights,
            transport_unknown_segments=unknown_segments,
            estimate_notes=notes,
            budget_status=budget_status,
            tickets_known=tickets_known,
            tickets_estimated=tickets_estimated,
            tickets_pending_spots=tickets_pending,
            tickets_free_spots=tickets_free,
            tickets_unpriced_activities=tickets_unpriced,
            lodging_night_rate=night_rate,
            lodging_cities=list(dict.fromkeys(lodging_cities)),
            cost_share=cost_share,
        )

    @staticmethod
    def _same_city(left: str, right: str) -> bool:
        def normalize(value: str) -> str:
            value = value.strip().replace(" ", "")
            for suffix in ("特别行政区", "自治州", "地区", "市", "县", "区"):
                if value.endswith(suffix):
                    return value[:-len(suffix)]
            return value
        return normalize(left) == normalize(right)

    @classmethod
    def _has_transport(cls, route: RoutePlan, origin: str, destination: str) -> bool:
        return any(
            cls._same_city(transit.from_city, origin)
            and cls._same_city(transit.to_city, destination)
            for transit in route.transport
        )
