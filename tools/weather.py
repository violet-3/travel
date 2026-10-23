"""日期对齐的高德天气服务。未来预报不跨越供应商实际返回的日期范围。"""

from datetime import date, timedelta

import httpx

from config import AmapConfig, default_config
from tools.amap_utils import with_sig


async def get_weather(
    city: str,
    travel_date: date | str | None = None,
    days: int = 1,
    config: AmapConfig | None = None,
    *,
    travel_dates: list[date | str] | None = None,
) -> dict:
    """Fetch and filter the provider forecast to the requested travel dates."""
    cfg = config or default_config.amap
    requested_dates = sorted({parsed for item in (travel_dates or []) if (parsed := _as_date(item)) is not None})
    if not requested_dates:
        start = _as_date(travel_date)
        if start is not None:
            days = max(1, min(int(days or 1), 60))
            requested_dates = [start + timedelta(days=offset) for offset in range(days)]
    if not requested_dates:
        return {"status": "date_required", "city": city, "forecast": []}
    start, end = requested_dates[0], requested_dates[-1]
    requested_set = set(requested_dates)
    if not cfg.web_key:
        return {
            "status": "no_key", "city": city, "forecast": [],
            "requested_start": start.isoformat(), "requested_end": end.isoformat(),
            "requested_dates": [day.isoformat() for day in requested_dates],
        }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            geo_resp = await client.get(
                "https://restapi.amap.com/v3/config/district",
                params=with_sig(
                    {"keywords": city, "subdistrict": 0, "extensions": "base"},
                    cfg.web_key, cfg.web_secret,
                ),
            )
            geo_data = geo_resp.json()
            districts = geo_data.get("districts") or []
            district = next(
                (item for item in districts if _same_place(city, item.get("name", ""))),
                None,
            )
            adcode = (district or {}).get("adcode", "")
            if not adcode:
                return {"status": "not_found", "city": city, "forecast": [], "requested_start": start.isoformat(), "requested_end": end.isoformat(), "requested_dates": [day.isoformat() for day in requested_dates]}

            weather_resp = await client.get(
                "https://restapi.amap.com/v3/weather/weatherInfo",
                params=with_sig(
                    {"city": adcode, "extensions": "all"}, cfg.web_key, cfg.web_secret
                ),
            )
            weather_data = weather_resp.json()
    except Exception:
        return {"status": "error", "city": city, "forecast": [], "requested_start": start.isoformat(), "requested_end": end.isoformat(), "requested_dates": [day.isoformat() for day in requested_dates]}

    if weather_data.get("status") != "1":
        return {"status": "error", "city": city, "forecast": [], "requested_start": start.isoformat(), "requested_end": end.isoformat(), "requested_dates": [day.isoformat() for day in requested_dates]}

    region = (weather_data.get("forecasts") or [{}])[0]
    provider_casts = region.get("casts") or []
    selected = []
    for cast in provider_casts:
        forecast_date = _as_date(cast.get("date"))
        if forecast_date is None or forecast_date not in requested_set:
            continue
        selected.append({
            "date": forecast_date.isoformat(),
            "week": _week_map.get(str(cast.get("week", "")), cast.get("week", "")),
            "dayweather": cast.get("dayweather", ""),
            "nightweather": cast.get("nightweather", ""),
            "daytemp": cast.get("daytemp", ""),
            "nighttemp": cast.get("nighttemp", ""),
            "daywind": cast.get("daywind", ""),
            "daypower": cast.get("daypower", ""),
            # Retain snake-case aliases for existing offline callers.
            "day_weather": cast.get("dayweather", ""),
            "night_weather": cast.get("nightweather", ""),
            "day_temp": cast.get("daytemp", ""),
            "night_temp": cast.get("nighttemp", ""),
        })
    status = "ok" if len(selected) == len(requested_dates) else ("partial" if selected else "outside_forecast_window")
    return {
        "status": status,
        "city": region.get("city", city),
        "province": region.get("province", ""),
        "reporttime": region.get("reporttime", ""),
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "requested_dates": [day.isoformat() for day in requested_dates],
        "forecast": selected,
    }


_week_map = {"1": "周一", "2": "周二", "3": "周三", "4": "周四",
             "5": "周五", "6": "周六", "7": "周日"}


def clothing_advice(forecast: list[dict]) -> str:
    """根据天气预报给出穿衣建议"""
    if not forecast:
        return ""
    temps = []
    for f in forecast:
        for t in [f.get("daytemp", f.get("day_temp", "")), f.get("nighttemp", f.get("night_temp", ""))]:
            try:
                temps.append(int(t))
            except (ValueError, TypeError):
                pass
    if not temps:
        return ""
    high, low = max(temps), min(temps)
    has_rain = any(
        "雨" in (f.get("dayweather", f.get("day_weather", "")) + f.get("nightweather", f.get("night_weather", "")))
        for f in forecast
    )

    advice = []
    if low < 5:
        advice.append("羽绒服/厚大衣")
    elif low < 12:
        advice.append("薄外套/风衣")
    elif low < 18:
        advice.append("长袖衬衫/薄卫衣")
    else:
        advice.append("短袖/T恤")

    if high - low > 12:
        advice.append("早晚温差大，备一件外套")

    if has_rain:
        advice.append("带雨伞/雨衣")

    if high > 30:
        advice.append("防晒霜+墨镜+帽子")

    return " · ".join(advice)


def _as_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _normalize_place(value: str) -> str:
    text = "".join(str(value or "").split())
    for suffix in ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区", "自治区", "自治州", "地区", "市", "县", "区"):
        if text.endswith(suffix):
            return text[:-len(suffix)]
    return text


def _same_place(left: str, right: str) -> bool:
    return bool(_normalize_place(left)) and _normalize_place(left) == _normalize_place(right)
