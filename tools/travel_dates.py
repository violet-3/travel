"""Deterministic travel-date parsing using the Asia/Shanghai calendar."""

from dataclasses import dataclass
from datetime import date
import re
from zoneinfo import ZoneInfo


class TravelDateError(ValueError):
    """A supplied Gregorian travel date is invalid or already in the past."""


@dataclass(frozen=True)
class TravelDateInfo:
    date_value: str | None = None
    month_value: str | None = None
    note: str = ""
    mentioned: bool = False


def shanghai_today() -> date:
    from datetime import datetime
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _month_number(value: str) -> int:
    if value.isdigit():
        return int(value)
    numerals = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    if value == "十一":
        return 11
    if value == "十二":
        return 12
    return numerals.get(value, 0)


def _month_label(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _future_month(year: int, month: int, today: date) -> tuple[int, int]:
    if (year, month) < (today.year, today.month):
        return year + 1, month
    return year, month


def parse_travel_date(text: str, today: date | None = None) -> TravelDateInfo:
    """Parse exact Gregorian dates and common relative months without inventing days."""
    today = today or shanghai_today()
    text = text or ""

    year_hint = None
    explicit_current_year = False
    if "明年" in text:
        year_hint = today.year + 1
    elif "今年" in text or "本年" in text:
        year_hint = today.year
        explicit_current_year = True

    # An explicitly written Gregorian date must be valid and in the future.
    full_patterns = (
        r"(?<!\d)(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})(?:日|号)?",
    )
    for pattern in full_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                parsed = date(*(int(part) for part in match.groups()))
            except ValueError as exc:
                raise TravelDateError("出行日期无效，请填写真实的公历日期。") from exc
            if parsed < today:
                raise TravelDateError("出行日期已过去，请填写未来的公历日期。")
            return TravelDateInfo(date_value=parsed.isoformat(), note=parsed.isoformat(), mentioned=True)

    # A month/day without a written year respects 明年/今年 before inferring a year.
    short_day = re.search(r"(?<!\d)(\d{1,2})月(\d{1,2})[日号]", text)
    if short_day:
        month, day = (int(part) for part in short_day.groups())
        year = year_hint or (today.year if (month, day) >= (today.month, today.day) else today.year + 1)
        try:
            parsed = date(year, month, day)
        except ValueError as exc:
            raise TravelDateError("出行日期无效，请填写真实的公历日期。") from exc
        if parsed < today and (explicit_current_year or year_hint is not None):
            raise TravelDateError("出行日期已过去，请填写未来的公历日期。")
        return TravelDateInfo(date_value=parsed.isoformat(), note=parsed.isoformat(), mentioned=True)

    year = year_hint or today.year
    has_relative_year = year_hint is not None

    # Lunar new-year timing changes annually; show uncertainty instead of guessing.
    if "春节" in text or "农历新年" in text:
        year_note = f"{year}年" if has_relative_year else ""
        return TravelDateInfo(note=f"{year_note}春节，具体日期待定，请填写公历日期", mentioned=True)

    # Named holiday periods do not imply a specific travel day.
    if "五一" in text or "劳动节" in text:
        year, month = _future_month(year, 5, today) if not has_relative_year else (year, 5)
        if (year, month) < (today.year, today.month):
            raise TravelDateError("出行月份已过去，请填写未来日期。")
        label = _month_label(year, month)
        return TravelDateInfo(month_value=label, note=f"{year}年5月（具体日期未定）", mentioned=True)
    if "国庆" in text or "十一假" in text:
        year, month = _future_month(year, 10, today) if not has_relative_year else (year, 10)
        if (year, month) < (today.year, today.month):
            raise TravelDateError("出行月份已过去，请填写未来日期。")
        label = _month_label(year, month)
        return TravelDateInfo(month_value=label, note=f"{year}年10月（具体日期未定）", mentioned=True)

    relative_month = re.search(r"下下个月|下下月|下个月|下月|本月|这个月", text)
    if relative_month:
        term = relative_month.group(0)
        offset = 2 if term.startswith("下下") else (1 if term.startswith("下") else 0)
        absolute = today.year * 12 + today.month - 1 + offset
        target_year, month = divmod(absolute, 12)
        label = _month_label(target_year, month + 1)
        return TravelDateInfo(month_value=label, note=f"{target_year}年{month + 1}月（具体日期未定）", mentioned=True)

    # Explicit Gregorian month, with an inferred year only when omitted.
    month_match = re.search(
        r"(?:(\d{4})年(\d{1,2})月|(\d{4})[-/](\d{1,2})|"
        r"(\d{1,2}|十一|十二|[一二三四五六七八九十])月)", text
    )
    if month_match:
        year_text = month_match.group(1) or month_match.group(3)
        month_text = month_match.group(2) or month_match.group(4) or month_match.group(5)
        month = _month_number(month_text)
        if not 1 <= month <= 12:
            raise TravelDateError("出行月份无效，请检查填写内容。")
        if year_text:
            year = int(year_text)
            if year < today.year or (year == today.year and month < today.month):
                raise TravelDateError("出行月份已过去，请填写未来日期。")
        elif year_hint is not None:
            year = year_hint
            if year == today.year and month < today.month:
                raise TravelDateError("出行月份已过去，请填写未来日期。")
        else:
            year, month = _future_month(year, month, today)
        label = _month_label(year, month)
        return TravelDateInfo(month_value=label, note=f"{year}年{month}月（具体日期未定）", mentioned=True)

    if "明年" in text:
        return TravelDateInfo(month_value=str(year), note=f"{year}年（具体日期未定）", mentioned=True)

    return TravelDateInfo()
