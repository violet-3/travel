"""第12轮：行程可执行性校验。

只用已核验的坐标做确定性判断，不猜位置：
- 同日相邻活动通勤距离是否离谱
- 单日移动总里程是否超出合理范围
- 活动数量与节奏是否匹配
- 粗估在途 + 停留时长是否超过当天可用时间

没有任何可核验坐标时，报告明确标注"无法判断"，不给假分数。
"""

from dataclasses import dataclass, field
from math import asin, cos, radians, sin, sqrt

from models.schemas import RoutePlan, TravelIntent

EARTH_RADIUS_KM = 6371.0088

# 按节奏设定单日活动数上限
PACE_ACTIVITY_LIMIT = {"轻松": 2, "不紧不慢": 3, "特种兵": 4}

# 同日相邻活动通勤距离阈值（km）
LEG_WARN_KM = 40.0
LEG_SERIOUS_KM = 100.0

# 单日移动总里程阈值（km）
DAY_DISTANCE_WARN_KM = 80.0
DAY_DISTANCE_SERIOUS_KM = 160.0

# 粗估用参数
DEFAULT_ACTIVITY_HOURS = 2.5
AVERAGE_SPEED_KMH = 40.0

# 当天可用小时上限（按节奏）
PACE_DAY_HOURS = {"轻松": 9.0, "不紧不慢": 11.0, "特种兵": 13.0}


def haversine_km(start: list[float] | None, end: list[float] | None) -> float | None:
    """Great-circle distance in km; returns None when either point is unusable."""
    if not start or not end or len(start) != 2 or len(end) != 2:
        return None
    try:
        lon1, lat1 = float(start[0]), float(start[1])
        lon2, lat2 = float(end[0]), float(end[1])
    except (TypeError, ValueError):
        return None
    if not (-180 <= lon1 <= 180 and -90 <= lat1 <= 90):
        return None
    if not (-180 <= lon2 <= 180 and -90 <= lat2 <= 90):
        return None
    lon1, lat1, lon2, lat2 = map(radians, (lon1, lat1, lon2, lat2))
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(h)))


@dataclass
class DayFeasibility:
    day: int
    city: str
    activities: int
    distance_km: float | None = None
    max_leg_km: float | None = None
    estimated_hours: float | None = None
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "city": self.city,
            "activities": self.activities,
            "distance_km": None if self.distance_km is None else round(self.distance_km, 1),
            "max_leg_km": None if self.max_leg_km is None else round(self.max_leg_km, 1),
            "estimated_hours": (
                None if self.estimated_hours is None else round(self.estimated_hours, 1)
            ),
            "issues": list(self.issues),
        }


@dataclass
class FeasibilityReport:
    score: int = 100
    level: str = "A"
    days: list[DayFeasibility] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    location_coverage: float = 0.0
    checked: bool = False

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level,
            "checked": self.checked,
            "location_coverage": round(self.location_coverage, 3),
            "days": [day.to_dict() for day in self.days],
            "issues": list(self.issues),
            "notes": list(self.notes),
        }


def _activity_sequence(day) -> list:
    return [
        activity for activity in (day.morning, day.afternoon, day.evening)
        if activity is not None and (getattr(activity, "name", "") or "").strip()
    ]


def _verified_coord(activity) -> list[float] | None:
    if not getattr(activity, "coordinate_verified", False):
        return None
    return getattr(activity, "coordinate", None)


def _score_to_level(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def analyze_itinerary(
    route: RoutePlan, intent: TravelIntent | None = None
) -> FeasibilityReport:
    """Deterministic feasibility report. Absence of issues does not prove a day works."""
    report = FeasibilityReport()
    pace = (intent.pace if intent else "") or "不紧不慢"
    activity_limit = PACE_ACTIVITY_LIMIT.get(pace, 3)
    day_hours_limit = PACE_DAY_HOURS.get(pace, 11.0)

    activity_locations = 0
    verified_locations = 0
    possible_segments = 0
    valid_segments = 0
    deduction = 0

    for day in route.daily_plan or []:
        activities = _activity_sequence(day)
        item = DayFeasibility(day=day.day, city=day.city or "", activities=len(activities))
        activity_locations += len(activities)
        verified_locations += sum(1 for activity in activities if _verified_coord(activity))

        if len(activities) > activity_limit:
            item.issues.append(
                f"按“{pace}”节奏，第{day.day}天安排了{len(activities)}个活动，"
                f"超过建议上限{activity_limit}个。"
            )
            deduction += 8

        legs: list[tuple[int, float]] = []
        for leg_number, (current, following) in enumerate(
            zip(activities, activities[1:]), start=1
        ):
            possible_segments += 1
            start = _verified_coord(current)
            end = _verified_coord(following)
            distance = haversine_km(start, end)
            if distance is not None:
                valid_segments += 1
                legs.append((leg_number, distance))

        if legs:
            distances = [distance for _, distance in legs]
            item.distance_km = sum(distances)
            item.max_leg_km = max(distances)
            for index, distance in legs:
                if distance >= LEG_SERIOUS_KM:
                    item.issues.append(
                        f"第{day.day}天第{index}段通勤约{distance:.0f}公里，当天往返明显吃紧。"
                    )
                    deduction += 18
                elif distance >= LEG_WARN_KM:
                    item.issues.append(
                        f"第{day.day}天第{index}段通勤约{distance:.0f}公里，建议核对是否同城。"
                    )
                    deduction += 10

            if item.distance_km >= DAY_DISTANCE_SERIOUS_KM:
                item.issues.append(
                    f"第{day.day}天单日移动约{item.distance_km:.0f}公里，实际会大量耗在路上。"
                )
                deduction += 15
            elif item.distance_km >= DAY_DISTANCE_WARN_KM:
                item.issues.append(
                    f"第{day.day}天单日移动约{item.distance_km:.0f}公里，需要预留交通时间。"
                )
                deduction += 8

            commute_hours = item.distance_km / AVERAGE_SPEED_KMH
            item.estimated_hours = commute_hours + len(activities) * DEFAULT_ACTIVITY_HOURS
            if item.estimated_hours > day_hours_limit:
                item.issues.append(
                    f"第{day.day}天粗估需{item.estimated_hours:.1f}小时"
                    f"（含在途与停留），超出“{pace}”节奏的{day_hours_limit:.0f}小时预算。"
                )
                deduction += 10

        report.days.append(item)

    report.checked = valid_segments > 0
    report.location_coverage = (
        verified_locations / activity_locations if activity_locations else 0.0
    )

    for item in report.days:
        report.issues.extend(item.issues)

    if report.checked:
        report.notes.append(
            f"按{valid_segments}/{possible_segments}段两端均已核验的坐标计算直线距离"
            f"（非实际道路里程），活动位置覆盖率约"
            f"{report.location_coverage * 100:.0f}%。"
        )
        if report.location_coverage < 0.6:
            report.notes.append("多数活动位置未核验，距离结论仅覆盖已核验的部分。")
    else:
        report.notes.append(
            "本次没有可计算的通勤段（每段两端都需有已核验坐标），无法判断景点间通勤；"
            "请以地图实际路线为准。"
        )
        # 没有坐标时不因“无法判断”扣分，仅保留活动数等本地可判断的问题。
        report.notes.append("可行性分数只反映活动数量与节奏，不含地理距离。")

    report.score = max(0, min(100, 100 - deduction))
    report.level = _score_to_level(report.score)
    return report


def apply_feasibility(
    route: RoutePlan, report: FeasibilityReport, limit: int = 3
) -> None:
    """Surface the most important issues as route warnings (deduplicated).

    The full per-day detail stays in the feasibility report so the warning list
    does not drown out budget, constraint and map messages.
    """
    for issue in report.issues[:limit]:
        if issue not in route.warnings:
            route.warnings.append(issue)
    hidden = len(report.issues) - limit
    if hidden > 0:
        summary = f"另有{hidden}项行程紧凑度问题，见每日可行性明细。"
        if summary not in route.warnings:
            route.warnings.append(summary)
