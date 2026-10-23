"""Merge user-entered travel fields with the LangChain intent parse."""

import re
from datetime import date
from decimal import Decimal

from models.schemas import TravelIntent
from tools.travel_dates import parse_travel_date


class TravelIntentError(ValueError):
    """A travel request is missing a destination or contains incompatible constraints."""


def _as_list(value) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, (list, tuple)) else [value]
    result = []
    for item in values:
        if not isinstance(item, str):
            continue
        result.extend(part.strip() for part in re.split(r"[,，、;；\n]+", item) if part.strip())
    return result


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


_CN_NUMBERS = {
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def _natural_text_values(query: str) -> dict:
    """Recover unambiguous numeric and departure details if an LLM omits them."""
    values = {}
    day_match = re.search(r"(?<!\d)(\d{1,2})\s*天", query)
    if not day_match:
        day_match = re.search(r"([一二两三四五六七八九十])\s*天", query)
    if day_match:
        raw = day_match.group(1)
        days = int(raw) if raw.isdigit() else _CN_NUMBERS.get(raw)
        if not days or days > 60:
            raise TravelIntentError("旅行天数需在1到60天之间。")
        values["days"] = days

    travelers_match = re.search(r"(?<!\d)(\d{1,2})\s*人", query)
    if travelers_match:
        travelers = int(travelers_match.group(1))
        if not 1 <= travelers <= 50:
            raise TravelIntentError("同行人数需在1到50人之间。")
        values["travelers"] = travelers

    budget_match = re.search(
        r"(?:人均(?:预算)?|总预算|预算|总额|花费|费用)\s*(?:约|为|是|[:：])?\s*"
        r"(?P<amount>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*"
        r"(?P<unit>万|千)?\s*(?:元|块)?",
        query,
    )
    if budget_match:
        amount = Decimal(budget_match.group("amount").replace(",", ""))
        amount *= {"万": Decimal(10_000), "千": Decimal(1_000), None: Decimal(1)}[
            budget_match.group("unit")
        ]
        if amount <= 0:
            raise TravelIntentError("预算金额需在1到100000000元之间。")
        if amount > 100_000_000:
            raise TravelIntentError("预算金额需在1到100000000元之间。")
        if amount != amount.to_integral_value():
            raise TravelIntentError("预算金额请填写整数元，或使用“千/万”单位。")
        values["budget"] = int(amount)
    if re.search(r"总预算|全程总额|全体总额|一共(?:花|预算)|所有人合计", query):
        values["budget_scope"] = "total"
    elif "人均" in query:
        values["budget_scope"] = "per_person"

    departure_match = re.search(r"(?:从|由)\s*([\u4e00-\u9fff]{2,6})\s*出发", query)
    if not departure_match:
        departure_match = re.search(r"(?:^|[\s，,、；;])([\u4e00-\u9fff]{2,6})出发", query)
    if departure_match:
        values["departure_city"] = departure_match.group(1)

    inferred_constraints = []
    for phrase, canonical in (
        ("不爬山", "不爬山"), ("不登山", "不爬山"), ("不徒步", "不爬山"),
        ("少走路", "少走路"), ("少步行", "少走路"), ("腿脚不便", "少走路"),
        ("轮椅", "无障碍"), ("无障碍", "无障碍"),
        ("不能吃辣", "不辣"), ("不可以吃辣", "不辣"), ("不吃辣", "不辣"),
        ("不吃辛辣", "不辣"), ("不想吃辣", "不辣"), ("不要吃辣", "不辣"),
        ("少放辣", "不辣"), ("不辣", "不辣"),
    ):
        if phrase in query:
            inferred_constraints.append(canonical)
    if inferred_constraints:
        values["constraints"] = _dedupe(inferred_constraints)
    return values


def _signals(text: str, negative: tuple[str, ...], positive: tuple[str, ...],
             direct_positive: bool = False) -> tuple[bool, bool]:
    lower = text.lower()
    no = any(term in lower for term in negative)
    clean = lower
    for phrase in sorted(negative, key=len, reverse=True):
        clean = clean.replace(phrase, " ")
    if direct_positive:
        yes = any(term in clean for term in positive)
    else:
        marker = r"(?:想|喜欢|喜歡|希望|要|计划|計劃|安排|体验|體驗|尝试|嘗試|打算|願意|愿意|可以)"
        action = r"(?:去|吃|走|进行|進行|安排|体验)?"
        yes = any(re.search(marker + r".{0,3}" + action + re.escape(term), clean)
                  for term in positive)
    return no, yes


def validate_constraint_consistency(query: str, constraints) -> None:
    """Reject clear hard-constraint contradictions before any model call."""
    form_text = " ".join(_as_list(constraints))
    pairs = (
        ("登山/徒步", ("不爬山", "不登山", "不徒步", "避免爬山", "不要爬山",
                         "不想爬山", "不喜欢爬山", "不想徒步", "不喜欢徒步"),
         ("爬山", "登山", "徒步")),
        ("步行强度", ("少走路", "不走路", "少步行", "轮椅", "腿脚不便",
                         "不想走长路", "不喜欢长距离步行"),
         ("长距离步行", "徒步", "暴走")),
        ("辣度", ("不辣", "不能吃辣", "不可以吃辣", "不吃辣", "不吃辛辣",
                    "不喜欢吃辣", "不想吃辣", "不要辣", "不要吃辣", "忌辣",
                    "无辣", "少辣", "少放辣"),
         ("吃辣", "辣味", "辣菜", "辣")),
    )
    for label, negatives, positives in pairs:
        query_no, query_yes = _signals(query, negatives, positives)
        form_no, form_yes = _signals(form_text, negatives, positives, direct_positive=True)
        if ((query_no and form_yes) or (query_yes and form_no)
                or (query_no and query_yes) or (form_no and form_yes)):
            raise TravelIntentError(
                f"自然语言与表单硬约束在“{label}”上冲突，请修改其中一处后再生成。"
            )


def merge_travel_intent(
    parsed: TravelIntent,
    query: str,
    overrides: dict | None = None,
    today: date | None = None,
) -> TravelIntent:
    """Apply explicit form values and deterministically normalize date expressions."""
    overrides = {key: value for key, value in (overrides or {}).items() if value is not None}
    validate_constraint_consistency(query, overrides.get("constraints"))
    values = parsed.model_dump()
    natural_values = _natural_text_values(query)
    for key, value in natural_values.items():
        if key == "constraints":
            values[key] = _dedupe(_as_list(values.get(key)) + value)
        else:
            values[key] = value

    destinations = _as_list(overrides.get("destinations"))
    if destinations:
        values["destinations"] = destinations

    for key in ("departure_city", "days", "travelers", "budget", "budget_scope", "pace"):
        if key in overrides:
            values[key] = overrides[key]

    if "preferences" in overrides:
        values["preferences"] = _dedupe(
            _as_list(values.get("preferences")) + _as_list(overrides["preferences"])
        )
    if "constraints" in overrides:
        values["constraints"] = _dedupe(
            _as_list(values.get("constraints")) + _as_list(overrides["constraints"])
        )

    # The schema default must not contradict an explicit multi-person form.
    # Keep any specific relationship supplied by the parser (family, friends, etc.).
    single_person_labels = {"独自", "一个人", "单人", "solo"}
    companion = str(values.get("companion") or "").strip()
    if int(values.get("travelers") or 1) > 1 and companion.casefold() in single_person_labels:
        values["companion"] = "同行（关系未注明）"

    # The explicit date input wins. Otherwise parse only recognizable user text;
    # never trust a model-invented date or a guessed lunar-holiday day.
    if "travel_date" in overrides:
        selected = overrides["travel_date"]
        if isinstance(selected, date):
            selected = selected.isoformat()
        values["travel_date"] = str(selected)
        values["travel_month"] = None
        values["travel_date_note"] = str(selected)
    else:
        date_info = parse_travel_date(query, today=today)
        values["travel_date"] = date_info.date_value
        values["travel_month"] = date_info.month_value
        values["travel_date_note"] = date_info.note

    if values.get("budget") is not None:
        amount = values["budget"]
        travelers = max(int(values.get("travelers") or 1), 1)
        per_person = amount / travelers if values.get("budget_scope") == "total" else amount
        if per_person < 1500:
            values["budget_level"] = "经济"
        elif per_person < 4000:
            values["budget_level"] = "中等"
        elif per_person < 8000:
            values["budget_level"] = "舒适"
        else:
            values["budget_level"] = "豪华"

    result = TravelIntent.model_validate(values)
    result.destinations = _dedupe(_as_list(result.destinations))
    if not result.destinations:
        raise TravelIntentError("请填写或在描述中说明至少一个旅行目的地。")
    return result
