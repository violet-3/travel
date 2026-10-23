"""Small deterministic checks for route consistency and obvious constraint conflicts."""

import re

from models.schemas import CultureData, RoutePlan, Spot, TravelIntent, Transport


_PROVINCES = {
    "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
    "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
    "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门",
}
_CITY_SUFFIXES = ("特别行政区", "自治区", "自治州", "地区", "省", "市", "县", "区")


def _norm_city(value: str) -> str:
    normalized = re.sub(r"\s+", "", value or "")
    for suffix in _CITY_SUFFIXES:
        if normalized.endswith(suffix):
            return normalized[:-len(suffix)]
    if normalized.endswith("省"):
        return normalized[:-1]
    return normalized


def _add_warning(route: RoutePlan, message: str) -> None:
    if message not in route.warnings:
        route.warnings.append(message)


def validate_route_plan(intent: TravelIntent, route: RoutePlan) -> list[str]:
    """Correct sequence numbering and warn about clear days/cities/transport mismatches."""
    before = set(route.warnings)

    actual_days = len(route.daily_plan)
    if actual_days != intent.days:
        _add_warning(
            route,
            f"行程当前有{actual_days}天，与需求中的{intent.days}天不一致；请核对后再使用。",
        )

    for index, day in enumerate(route.daily_plan, start=1):
        if day.day != index:
            day.day = index
            _add_warning(route, "每日行程编号与顺序不一致，已按列表顺序重新编号。")

    route_city_names = [city.strip() for city in route.cities if city and city.strip()]
    day_city_names = [day.city.strip() for day in route.daily_plan if day.city and day.city.strip()]
    route_city_keys = {_norm_city(city) for city in route_city_names}
    day_city_keys = {_norm_city(city) for city in day_city_names}

    if len(route_city_keys) != len(route_city_names):
        _add_warning(route, "路线城市列表存在重复项，请核对城市顺序。")
    missing_from_days = [city for city in route_city_names if _norm_city(city) not in day_city_keys]
    missing_from_route = [city for city in day_city_names if _norm_city(city) not in route_city_keys]
    if missing_from_days:
        _add_warning(route, "路线包含未安排到每日行程的城市：" + "、".join(dict.fromkeys(missing_from_days)) + "。")
    if missing_from_route:
        _add_warning(route, "每日行程出现路线列表之外的城市：" + "、".join(dict.fromkeys(missing_from_route)) + "。")

    day_order = list(dict.fromkeys(_norm_city(city) for city in day_city_names))
    route_order = list(dict.fromkeys(_norm_city(city) for city in route_city_names))
    if day_order and route_order and day_order != route_order:
        _add_warning(route, "路线城市顺序与每日行程顺序不一致，请核对城际安排。")

    for destination in intent.destinations:
        destination_key = _norm_city(destination)
        if not destination_key or destination_key in _PROVINCES:
            continue
        if not any(destination_key == key for key in route_city_keys | day_city_keys):
            _add_warning(route, f"行程未明确覆盖目的地“{destination}”，请核对城市安排。")

    expected_edges = []
    for current, following in zip(route.daily_plan, route.daily_plan[1:]):
        origin = current.city.strip()
        destination = following.city.strip()
        if origin and destination and _norm_city(origin) != _norm_city(destination):
            expected_edges.append((origin, destination))

    def edge_key(edge: tuple[str, str]) -> tuple[str, str]:
        return _norm_city(edge[0]), _norm_city(edge[1])

    existing_edges: dict[tuple[str, str], list[Transport]] = {}
    for transit in route.transport:
        edge = (transit.from_city.strip(), transit.to_city.strip())
        if edge[0] and edge[1]:
            existing_edges.setdefault(edge_key(edge), []).append(transit)

    seen_expected: dict[tuple[str, str], int] = {}
    expected_counts: dict[tuple[str, str], int] = {}
    for edge in expected_edges:
        key = edge_key(edge)
        expected_counts[key] = expected_counts.get(key, 0) + 1

    for origin, destination in expected_edges:
        key = edge_key((origin, destination))
        seen_expected[key] = seen_expected.get(key, 0) + 1
        candidates = existing_edges.get(key, [])
        if seen_expected[key] > len(candidates):
            reverse_exists = bool(existing_edges.get((key[1], key[0])))
            if candidates:
                reason = "重复路段未提供完整"
            else:
                reason = "方向与行程相反" if reverse_exists else "行程未提供"
            missing = Transport(
                from_city=origin, to_city=destination, mode="待确认", cost_est=None
            )
            route.transport.append(missing)
            existing_edges.setdefault(key, []).append(missing)
            _add_warning(
                route,
                f"{origin}→{destination}城际交通{reason}，费用待核价。",
            )
        elif candidates[seen_expected[key] - 1].cost_est is None:
            _add_warning(route, f"{origin}→{destination}城际交通费用未提供，预算待核价。")

    for key, candidates in existing_edges.items():
        if expected_counts.get(key, 0) and len(candidates) > expected_counts[key]:
            _add_warning(route, f"{candidates[0].from_city}→{candidates[0].to_city}城际交通段重复，请核对。")

    expected_keys = set(expected_counts)
    for transit in route.transport:
        origin = transit.from_city.strip()
        destination = transit.to_city.strip()
        if not origin or not destination:
            _add_warning(route, "交通段缺少出发城市或到达城市，请核对。")
            continue
        edge = (_norm_city(origin), _norm_city(destination))
        if edge not in expected_keys and (edge[1], edge[0]) in expected_keys:
            _add_warning(route, f"交通段{origin}→{destination}与每日行程方向不一致，请核对。")

    return [warning for warning in route.warnings if warning not in before]


def _constraint_value(constraints: list[str], terms: tuple[str, ...]) -> bool:
    return any(term in constraint for constraint in constraints for term in terms)


def _collect_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [part for item in value.values() for part in _collect_strings(item)]
    if isinstance(value, (list, tuple)):
        return [part for item in value for part in _collect_strings(item)]
    return []


def validate_hard_constraints(
    intent: TravelIntent,
    route: RoutePlan,
    spots: list[Spot],
    cultures: list[CultureData],
) -> list[str]:
    """Flag only clear keyword conflicts; absence of a flag does not prove fulfillment."""
    constraints = intent.constraints
    if not constraints:
        return []
    before = set(route.warnings)
    activities = []
    for day in route.daily_plan:
        activities.extend((day.morning, day.afternoon, day.evening))
    activity_text = [f"{activity.name} {activity.note}" for activity in activities if activity]

    if _constraint_value(constraints, ("不爬山", "不登山", "不徒步", "避免爬山")):
        for text in activity_text:
            if re.search(r"爬山|登山|登顶|攀岩|徒步", text) and not re.search(r"不|避免|取消|改为", text):
                _add_warning(route, "行程内容疑似违反“不爬山/不徒步”约束，请调整对应活动。")
                break

    if _constraint_value(constraints, ("少走路", "少步行", "腿脚不便", "轮椅")):
        for text in activity_text:
            if re.search(r"徒步|暴走|步行\s*\d+(?:\.\d+)?\s*公里|走\s*\d+(?:\.\d+)?\s*公里", text):
                _add_warning(route, "行程包含明显步行或徒步安排，可能违反“少走路”约束，请核对。")
                break

    if _constraint_value(constraints, ("不辣", "不能吃辣", "不吃辣", "忌辣")):
        food_text = [part for culture in cultures for part in _collect_strings(culture.cuisine)]
        for text in food_text:
            if (re.search(r"麻辣|香辣|酸辣|辣椒|辛辣|辣菜", text)
                    and not re.search(r"不辣|无辣|少辣|可选清淡", text)):
                _add_warning(route, "餐饮内容包含辣味菜品，可能违反“不辣”约束，请补充清淡替代。")
                break

    if not any("约束已传递" in warning for warning in route.warnings):
        _add_warning(
            route,
            "硬约束已传递给内容 Agent；本地只检查了明显关键词冲突，景区开放、无障碍与实际步行量仍需行前核实。",
        )
    return [warning for warning in route.warnings if warning not in before]
