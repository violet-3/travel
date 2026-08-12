"""
天气服务 · 高德天气 API (支持安全密钥签名)
文档: https://lbs.amap.com/api/webservice/guide/api/weatherinfo
"""

import hashlib
import httpx
from config import default_config


def _sign(params: dict) -> str:
    """高德安全密钥签名: MD5(排序后的参数拼串 + secret)"""
    secret = default_config.amap.secret
    if not secret:
        return ""
    # 按 key 字母排序，拼成 key=value&key=value...&secret
    sorted_items = sorted(params.items())
    raw = "&".join(f"{k}={v}" for k, v in sorted_items) + secret
    return hashlib.md5(raw.encode()).hexdigest()


async def get_weather(city: str) -> dict:
    """获取城市天气预报 (未来4天)"""
    key = default_config.amap.weather_key
    if not key:
        return {"status": "no_key", "city": city}

    # 地理编码
    params = {"key": key, "keywords": city, "subdistrict": 0}
    sig = _sign(params)
    if sig:
        params["sig"] = sig

    async with httpx.AsyncClient(timeout=10) as c:
        geo_resp = await c.get("https://restapi.amap.com/v3/config/district", params=params)
        geo_data = geo_resp.json()
        district = (geo_data.get("districts") or [{}])[0]
        adcode = district.get("adcode", "")

        if not adcode:
            return {"status": "not_found", "city": city}

        # 天气预报
        wp = {"key": key, "city": adcode, "extensions": "all"}
        wsig = _sign(wp)
        if wsig:
            wp["sig"] = wsig

        weather_resp = await c.get("https://restapi.amap.com/v3/weather/weatherInfo", params=wp)
        weather_data = weather_resp.json()

    if weather_data.get("status") != "1":
        return {"status": "error", "city": city}

    forecasts = weather_data.get("forecasts", [{}])[0]
    casts = forecasts.get("casts", [])

    # 当前天气
    live = weather_data.get("lives", [{}])[0] if weather_data.get("lives") else {}

    return {
        "status": "ok",
        "city": forecasts.get("city", city),
        "province": forecasts.get("province", ""),
        "current": {
            "weather": live.get("weather", ""),
            "temperature": live.get("temperature", ""),
            "wind": live.get("winddirection", "") + "风 " + live.get("windpower", "") + "级",
            "humidity": live.get("humidity", ""),
        } if live else None,
        "forecast": [
            {
                "date": c.get("date", ""),
                "week": _week_map.get(c.get("week", ""), c.get("week", "")),
                "day_weather": c.get("dayweather", ""),
                "night_weather": c.get("nightweather", ""),
                "day_temp": c.get("daytemp", ""),
                "night_temp": c.get("nighttemp", ""),
                "wind": c.get("daywind", "") + "风 " + c.get("daypower", "") + "级",
            }
            for c in casts[:4]
        ] if casts else [],
    }


_week_map = {"1": "周一", "2": "周二", "3": "周三", "4": "周四",
              "5": "周五", "6": "周六", "7": "周日"}


def clothing_advice(forecast: list[dict]) -> str:
    """根据天气预报给出穿衣建议"""
    if not forecast:
        return ""
    temps = []
    for f in forecast:
        for t in [f.get("day_temp", ""), f.get("night_temp", "")]:
            try:
                temps.append(int(t))
            except (ValueError, TypeError):
                pass
    if not temps:
        return ""
    high, low = max(temps), min(temps)
    has_rain = any("雨" in (f.get("day_weather", "") + f.get("night_weather", "")) for f in forecast)

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
