"""第13轮：行前准备 —— 天气驱动的备选方案与打包清单。

只用已经拿到的天气预报与用户条件做确定性推导：
- 有雨/高温/大风时给当天的替代安排
- 按温度、天数、同行关系、硬约束生成分组打包清单
- 明确哪些是通用建议、哪些依赖届时天气

不编造具体场馆名称，室内备选只给类别，避免幻觉。
"""

import re
from datetime import date, timedelta

from models.schemas import RoutePlan, TravelIntent

RAIN_WORDS = ("雨", "雪", "雷")
SEVERE_WORDS = ("暴雨", "大雨", "雷阵雨", "大雪", "暴雪", "冰雹")


def _norm(value: str) -> str:
    text = "".join(str(value or "").split())
    for suffix in ("特别行政区", "自治区", "自治州", "地区", "市", "县", "区"):
        if text.endswith(suffix):
            return text[:-len(suffix)]
    return text


def _as_int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _forecast_text(forecast: dict) -> str:
    """Combine day and night weather without repeating identical descriptions."""
    day = str(forecast.get("dayweather", forecast.get("day_weather", ""))).strip()
    night = str(forecast.get("nightweather", forecast.get("night_weather", ""))).strip()
    if not day:
        return night
    if not night or night == day:
        return day
    return f"{day}转{night}"


def _find_forecast(weather: list[dict], city: str, target: str) -> dict | None:
    target_key = _norm(city)
    for entry in weather or []:
        if not isinstance(entry, dict):
            continue
        if _norm(entry.get("city", "")) != target_key:
            continue
        for forecast in entry.get("forecast", []) or []:
            if str(forecast.get("date", "")) == target:
                return forecast
    return None


def _temperature_range(weather: list[dict]) -> tuple[int, int] | None:
    values: list[int] = []
    for entry in weather or []:
        if not isinstance(entry, dict):
            continue
        for forecast in entry.get("forecast", []) or []:
            for key in ("daytemp", "day_temp", "nighttemp", "night_temp"):
                parsed = _as_int(forecast.get(key))
                if parsed is not None:
                    values.append(parsed)
    if not values:
        return None
    return min(values), max(values)


def _clothing_items(low: int, high: int, days: int) -> list[str]:
    items: list[str] = []
    if low < 0:
        items.append("羽绒服、保暖内衣、厚手套与围巾")
    elif low < 8:
        items.append("厚外套或羽绒服，内搭抓绒/毛衣")
    elif low < 15:
        items.append("风衣或夹克，配长袖上衣")
    elif low < 22:
        items.append("薄外套或卫衣，方便早晚增减")
    else:
        items.append("短袖、速干上衣")

    if high - low >= 12:
        items.append("早晚温差大，额外备一件可叠穿的外套")
    if high >= 30:
        items.append("遮阳帽、墨镜与防晒霜（SPF50 更稳妥）")

    changes = max(1, min(days, 7))
    items.append(f"换洗衣物按 {changes} 套准备，长途可考虑途中洗衣")
    items.append("一双已经穿熟的舒适鞋，另备一双替换")
    return items


def _special_items(intent: TravelIntent | None) -> list[str]:
    if intent is None:
        return []
    text = " ".join(list(intent.constraints or []) + [intent.companion or ""] + list(intent.preferences or []))
    items: list[str] = []
    if re.search(r"少走路|少步行|腿脚不便|轮椅|无障碍", text):
        items.append("轻便折叠凳或助行手杖，出发前确认景区无障碍通道与电梯位置")
    if re.search(r"亲子|孩子|儿童|带娃", text):
        items.append("儿童常用药、湿巾、替换衣物与零食；推车需确认景区是否允许入园")
    if re.search(r"老人|长辈|父母", text):
        items.append("长辈日常用药按天数分装，随身携带医保卡与紧急联系人信息")
    if re.search(r"不爬山|不登山|不徒步", text):
        items.append("出发前核对每日点位是否包含登山或徒步；如有请按“不爬山”条件调整，石阶或湿滑路面可穿防滑鞋")
    if re.search(r"摄影|拍照|机位", text):
        items.append("备用电池与存储卡；清晨与黄昏机位注意提前占位")
    return items


def _weather_plans(
    route: RoutePlan, weather: list[dict], intent: TravelIntent | None
) -> list[dict]:
    """One entry per itinerary day that has a usable forecast."""
    plans: list[dict] = []
    start: date | None = None
    if intent is not None and intent.travel_date:
        try:
            start = date.fromisoformat(str(intent.travel_date)[:10])
        except ValueError:
            start = None

    for day in route.daily_plan or []:
        target = ""
        if start is not None:
            target = (start + timedelta(days=max(0, int(day.day) - 1))).isoformat()
        forecast = _find_forecast(weather, day.city, target) if target else None
        entry = {
            "day": day.day,
            "city": day.city or "",
            "date": target,
            "weather": "",
            "advice": [],
        }
        if not forecast:
            entry["status"] = "no_forecast"
            plans.append(entry)
            continue

        text = _forecast_text(forecast)
        entry["weather"] = text
        entry["status"] = "ok"
        high = _as_int(forecast.get("daytemp", forecast.get("day_temp")))
        low = _as_int(forecast.get("nighttemp", forecast.get("night_temp")))
        wind_power = _as_int(forecast.get("daypower"))

        if any(word in text for word in RAIN_WORDS):
            severe = any(word in text for word in SEVERE_WORDS)
            entry["advice"].append(
                "当天有降水，把户外点位换成室内类别：博物馆、美术馆、图书馆或大型商场；"
                "若安排了峡谷、登山、游船类项目，建议整体顺延到晴天。"
            )
            if severe:
                entry["advice"].append("预报为较强降水，山区与临水路段风险更高，请当天早上再确认景区是否开放。")
        if high is not None and high >= 35:
            entry["advice"].append("最高温偏高，把户外活动放到上午 10 点前和傍晚，正午安排室内或休息。")
        if low is not None and low <= -5:
            entry["advice"].append("夜间低温，注意保暖与路面结冰，山区路段尤其小心。")
        if wind_power is not None and wind_power >= 6:
            entry["advice"].append("风力较大，索道、游船与高空项目可能临时停运，出发前电话确认。")
        if not entry["advice"]:
            entry["advice"].append("天气暂无明显风险，按原计划执行；出发前一天再复核一次预报。")
        plans.append(entry)
    return plans


def build_prep_plan(
    route: RoutePlan, intent: TravelIntent | None, weather: list[dict] | None = None
) -> dict:
    """Assemble a deterministic pre-trip checklist and per-day weather fallback."""
    weather = weather or []
    days = max(1, len(route.daily_plan or []))
    temp_range = _temperature_range(weather)

    packing: list[dict] = []
    if temp_range:
        low, high = temp_range
        packing.append({
            "group": "衣物",
            "items": _clothing_items(low, high, days),
            "basis": f"按预报温度 {low}~{high}℃ 与 {days} 天行程推算",
        })
    else:
        packing.append({
            "group": "衣物",
            "items": [
                "按目的地季节准备便于增减的衣物，出发前一天查看当地天气再调整",
                f"换洗衣物按 {max(1, min(days, 7))} 套准备，长途可考虑途中洗衣",
                "一双已经穿熟的舒适鞋，另备一双替换",
            ],
            "basis": "没有可用温度预报；未生成基于温度的穿衣建议",
        })

    packing.append({
        "group": "证件与预订",
        "items": [
            "身份证（住宿与景区实名预约都要用）",
            "可享优惠的证件：学生证、老年证、军官证等，按实际携带",
            "交通票据与酒店确认单截图，离线也能查看",
            "热门景区提前实名预约，别到现场才发现约满",
        ],
        "basis": "通用行前事项，与具体景区政策无关",
    })
    packing.append({
        "group": "随身与电子",
        "items": [
            "携带充电宝前查看所乘航司与出发机场当日规定，核对容量、标识和携带方式",
            "常用支付方式，另备少量现金应对小店与信号盲区",
            "雨具：折叠伞或轻便雨衣",
        ],
        "basis": "通用行前事项",
    })
    packing.append({
        "group": "健康与护理",
        "items": [
            "常备药：肠胃药、感冒药、创可贴、晕车药",
            "个人处方药按天数带足，随身而非托运",
            "纸巾与免洗洗手液",
        ],
        "basis": "通用行前事项，不构成医疗建议",
    })

    special = _special_items(intent)
    if special:
        packing.append({
            "group": "按你的条件补充",
            "items": special,
            "basis": "依据本次填写的同行关系与硬约束",
        })

    plans = _weather_plans(route, weather, intent)
    notes = [
        "天气预报来自高德接口，时效有限，出发前 1 天请再查一次。",
        "室内备选只给类别，具体场馆请按当天营业时间与预约情况自行选择。",
        "打包清单是通用建议，不含专业户外或医疗装备。",
    ]
    if not temp_range:
        notes.append("本次没有可用温度预报，未给出温度型穿衣结论；请按目的地季节并在出发前查看预报。")
    if route.daily_plan and not any(plan["status"] == "ok" for plan in plans):
        notes.append("所有行程日均无可用预报，逐日备选方案未能生成。")

    return {
        "packing": packing,
        "weather_plans": plans,
        "notes": notes,
        "temperature_range": (
            {"low": temp_range[0], "high": temp_range[1]} if temp_range else None
        ),
    }
