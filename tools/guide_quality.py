"""第14轮：攻略质量自检。

用确定性规则给出可解释的评分，不调用模型，也不假装知道事实是否正确：
- 结构是否完整
- 需求是否被覆盖
- 内容是否充实
- 预算是否说清楚
- 位置与图片可信到什么程度
- 行程是否可执行（复用第12轮报告）

分数只说明"这份攻略自身有多完整、边界说清楚了没有"，不代表景点或票价经过官方核验。
"""

from models.schemas import TravelGuide

WEIGHTS = {
    "structure": 0.20,
    "request": 0.20,
    "content": 0.20,
    "budget": 0.15,
    "location": 0.15,
    "feasibility": 0.10,
}

LABELS = {
    "structure": "结构完整",
    "request": "需求覆盖",
    "content": "内容充实",
    "budget": "预算说明",
    "location": "位置与图片来源",
    "feasibility": "行程可执行",
}


def _norm(value: str) -> str:
    text = "".join(str(value or "").split())
    for suffix in ("特别行政区", "自治区", "自治州", "地区", "省", "市", "县", "区"):
        if text.endswith(suffix):
            return text[:-len(suffix)]
    return text


def _structure(guide: TravelGuide, issues: list[str]) -> int:
    score = 0
    if (guide.title or "").strip():
        score += 20
    else:
        issues.append("攻略缺少标题。")

    days = guide.route.daily_plan or []
    if days:
        score += 35
        slots = filled = 0
        for day in days:
            for activity in (day.morning, day.afternoon, day.evening):
                slots += 1
                if activity is not None and (activity.name or "").strip():
                    filled += 1
        ratio = (filled / slots) if slots else 0
        score += round(30 * ratio)
        if ratio < 0.7:
            issues.append(f"每日行程只填了 {filled}/{slots} 个时段，动线不够完整。")
    else:
        issues.append("没有每日行程安排。")

    if guide.spots:
        score += 10
    else:
        issues.append("没有推荐景点。")

    if guide.cultures:
        score += 5
    else:
        issues.append("没有风土人情内容。")
    return min(100, score)


def _request_coverage(guide: TravelGuide, issues: list[str]) -> int:
    request = guide.request
    if request is None:
        issues.append("本次没有保存需求摘要，无法核对条件是否被覆盖。")
        return 50

    score = 100
    route_keys = {_norm(city) for city in guide.route.cities}
    missing = [city for city in request.destinations if _norm(city) not in route_keys]
    if missing:
        score -= min(40, 15 * len(missing))
        issues.append("行程未覆盖目的地：" + "、".join(missing))

    actual_days = len(guide.route.daily_plan or [])
    if actual_days != request.days:
        score -= 20
        issues.append(f"实际行程 {actual_days} 天，与需求的 {request.days} 天不一致。")

    if request.budget is None:
        score -= 10
        issues.append("没有填写预算，费用部分只能给通用估算。")

    if not request.travel_date and not request.travel_date_note:
        score -= 10
        issues.append("没有明确出行日期，天气与预约建议的可用性会下降。")

    if request.constraints and not any("约束" in warning for warning in guide.route.warnings):
        score -= 5
        issues.append("已填写硬约束，但没有看到对应的核验说明。")

    return max(0, score)


def _content(guide: TravelGuide, issues: list[str]) -> int:
    days = max(1, len(guide.route.daily_plan or []))
    spots = guide.spots or []
    score = 0

    expected = max(2, days)
    if len(spots) >= expected:
        score += 35
    elif spots:
        score += round(35 * len(spots) / expected)
        issues.append(f"推荐景点 {len(spots)} 个，少于 {days} 天行程建议的 {expected} 个。")
    else:
        issues.append("没有推荐景点，内容偏薄。")

    if spots:
        with_tips = sum(1 for spot in spots if (spot.tips or "").strip())
        ratio = with_tips / len(spots)
        score += round(25 * ratio)
        if ratio < 0.5:
            issues.append(f"只有 {with_tips}/{len(spots)} 个景点带实用提示。")
        with_photo_spots = sum(1 for spot in spots if spot.photo_spots)
        if with_photo_spots:
            score += 10
        else:
            issues.append("没有摄影机位建议。")

    if guide.cultures:
        must_eat = [
            food for culture in guide.cultures
            for food in ((culture.cuisine or {}).get("must_eat") or [])
            if isinstance(food, dict)
        ]
        if must_eat:
            score += 20
        else:
            issues.append("风土人情里没有必吃清单。")
        if any(culture.folk_culture for culture in guide.cultures):
            score += 10
        else:
            issues.append("缺少民俗或建筑类内容。")
    else:
        issues.append("没有风土人情内容。")

    return min(100, score)


def _budget(guide: TravelGuide, issues: list[str]) -> int:
    budget = guide.budget
    score = 100

    if not budget.total:
        issues.append("预算小计为 0，可能没有可用的行程数据。")
        return 0

    unknown = budget.transport_unknown_segments or []
    if unknown:
        score -= min(30, 6 * len(unknown))
        issues.append(f"有 {len(unknown)} 段城际交通未核价，费用小计不含这部分。")

    pending = budget.tickets_pending_spots or []
    if pending:
        score -= min(20, 4 * len(pending))
        issues.append(f"有 {len(pending)} 处地点没有门票标价，门票按估算计入。")

    unpriced = budget.tickets_unpriced_activities or []
    if unpriced:
        score -= min(25, 8 * len(unpriced))
        issues.append(
            f"有 {len(unpriced)} 项行程活动未匹配门票信息，费用小计可能不完整。"
        )

    if guide.request is not None and guide.request.budget is None:
        score -= 15
        issues.append("没有填写预算，无法判断当前估算是否在你的接受范围内。")

    if budget.budget_status == "over_known_budget":
        issues.append("已知费用估算已超过填写的预算。")

    if not budget.estimate_notes:
        score -= 10
        issues.append("没有给出估算口径说明。")

    return max(0, score)


def _location(guide: TravelGuide, issues: list[str]) -> int:
    spots = guide.spots or []
    if not spots:
        issues.append("没有景点，无法评估位置可信度。")
        return 50

    verified = sum(1 for spot in spots if spot.coordinate_verified)
    coord_ratio = verified / len(spots)
    score = round(60 * coord_ratio)
    if coord_ratio < 1:
        issues.append(f"{len(spots) - verified} 个景点的位置未核验，导航可能退化为名称搜索。")

    with_photo = sum(1 for spot in spots if spot.photo and spot.photo_source != "none")
    photo_ratio = with_photo / len(spots)
    score += round(40 * photo_ratio)
    if photo_ratio < 0.5:
        issues.append(f"只有 {with_photo}/{len(spots)} 个景点有可用图片。")

    return min(100, score)


def _feasibility(guide: TravelGuide, issues: list[str]) -> int:
    report = guide.feasibility or {}
    if not report:
        issues.append("本次没有生成行程可执行性报告。")
        return 60
    if not report.get("checked"):
        issues.append("缺少已核验坐标，景点间通勤无法判断。")
        return 65
    for issue in report.get("issues", [])[:3]:
        issues.append(issue)
    return int(report.get("score", 60))


def _grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def evaluate_guide(guide: TravelGuide) -> dict:
    """Deterministic quality report. A high score is not a factual verification."""
    issues: list[str] = []
    dimensions = {
        "structure": _structure(guide, issues),
        "request": _request_coverage(guide, issues),
        "content": _content(guide, issues),
        "budget": _budget(guide, issues),
        "location": _location(guide, issues),
        "feasibility": _feasibility(guide, issues),
    }

    total = round(sum(dimensions[key] * WEIGHTS[key] for key in WEIGHTS))

    return {
        "score": max(0, min(100, total)),
        "grade": _grade(total),
        "dimensions": {
            key: {"label": LABELS[key], "score": value, "weight": WEIGHTS[key]}
            for key, value in dimensions.items()
        },
        "issues": list(dict.fromkeys(issues)),
        "notes": [
            "评分只衡量这份攻略自身是否完整、边界是否说清楚。",
            "分数高不代表景点、票价、开放时间或无障碍设施经过官方核验。",
        ],
    }
