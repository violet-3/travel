"""
攻略生成器 Agent · 所有数据 → Markdown 攻略

将 RoutePlan + Spots + CultureData 编译为:
1. 完整的 Markdown 文本攻略
2. 可直接写入 Obsidian
"""

from models.schemas import RoutePlan, Spot, CultureData, BudgetBreakdown, TravelGuide


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
    ) -> TravelGuide:
        """编译所有数据为最终攻略"""
        budget = self._calculate_budget(route)

        return TravelGuide(
            title=f"《{route.route_name}》",
            subtitle=f"{' → '.join(route.cities)} · {len(route.daily_plan)}天{len(route.daily_plan)-1}晚",
            destinations=route.cities,
            days=len(route.daily_plan),
            budget_level="中等",
            route=route,
            spots=spots,
            cultures=cultures,
            budget=budget,
        )

    def to_markdown(self, guide: TravelGuide) -> str:
        """把 TravelGuide 编译为 Markdown 字符串"""
        md = []

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
        md.append(f"| 人均预算 | ¥{guide.budget.total} |")
        md.append(f"| 旅行节奏 | 不紧不慢 |")
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
            md.append("## 📸 推荐景点")
            md.append("")
            for tier_name, tier_num in [("🏅 必去经典", 1), ("🔍 深度体验", 2), ("💎 小众宝藏", 3)]:
                tier_spots = [s for s in guide.spots if s.tier == tier_num]
                if tier_spots:
                    md.append(f"### {tier_name}")
                    md.append("")
                    for spot in tier_spots[:10]:
                        md.append(f"**{spot.name}** | {spot.type} | ⏱️ {spot.duration} | 🎫 ¥{spot.ticket}")
                        if spot.tags:
                            md.append(f"  {' · '.join(['#' + t for t in spot.tags])}")
                        if spot.tips:
                            md.append(f"  > 💡 {spot.tips}")
                        if spot.photo_spots:
                            for ps in spot.photo_spots[:2]:
                                md.append(f"  - 📷 {ps.name} — {ps.best_time} ({ps.shot})")
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
                    md.append("| 美食 | 去哪吃 | 人均 | 推荐理由 |")
                    md.append("|------|--------|------|---------|")
                    for food in must_eat[:6]:
                        md.append(f"| {food.get('name', '')} | {food.get('where', '')} | ¥{food.get('price_per_person', 0)} | {food.get('reason', '')} |")
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
        md.append(f"| 交通 | ¥{guide.budget.transport} |")
        md.append(f"| 住宿 | ¥{guide.budget.accommodation} |")
        md.append(f"| 门票 | ¥{guide.budget.tickets} |")
        md.append(f"| 餐饮 | ¥{guide.budget.food} |")
        md.append(f"| 其他 | ¥{guide.budget.other} |")
        md.append(f"| **合计** | **¥{guide.budget.total}** |")
        md.append("")

        # ─── 注意事项 ───
        if guide.route.warnings:
            md.append("## ⚠️ 注意事项")
            md.append("")
            for w in guide.route.warnings:
                md.append(f"- {w}")
            md.append("")

        # ─── 页脚 ───
        md.append("---")
        md.append(f"*攻略由 TravelAgent AI 生成 · {guide.generated_at[:10]}*")

        return "\n".join(md)

    def _calculate_budget(self, route: RoutePlan) -> BudgetBreakdown:
        """根据路线估算预算"""
        days = len(route.daily_plan)

        # 交通
        transport = sum(t.cost_est for t in route.transport)
        # 往返大交通估计
        transport += 800

        # 住宿: 经济150/中250/高400 x晚数
        accommodation = 250 * (days - 1)

        # 门票: 日均100
        tickets = 100 * days

        # 餐饮: 日均80
        food = 80 * days

        # 其他
        other = 50 * days

        return BudgetBreakdown(
            transport=transport,
            accommodation=accommodation,
            tickets=tickets,
            food=food,
            other=other,
            total=transport + accommodation + tickets + food + other,
        )
