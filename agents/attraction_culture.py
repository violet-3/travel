"""
景点推荐器 + 风土人情引擎 · 两个 Agent 合并在一个文件

- AttractionRecommenderAgent: RoutePlan → 为每个城市推荐景点（3层）
- CultureEngineAgent: RoutePlan → 为每个城市生成风土人情内容
"""

import json
import re
from typing import Any
from pydantic import BaseModel, ValidationError

from agents.base import BaseAgent
from models.schemas import RoutePlan, Spot, CultureData, TravelAgentContext, TravelIntent
class SpotList(BaseModel):
    items: list[Spot]


class CultureList(BaseModel):
    items: list[CultureData]


class AgentOutputError(ValueError):
    """Agent output is malformed, incomplete, or contains no usable records."""


def _route_and_intent(value: RoutePlan | TravelAgentContext) -> tuple[RoutePlan, TravelIntent | None]:
    if isinstance(value, TravelAgentContext):
        return value.route, value.intent
    return value, None


def _intent_guidance(intent: TravelIntent | None) -> str:
    if intent is None:
        return ""
    return f"""
## 本次旅行者条件（必须保留）
- 同行人数: {intent.travelers}人；同行关系: {intent.companion}
- 出行日期: {intent.travel_date_note or intent.travel_date or '未指定'}
- 旅行节奏: {intent.pace}
- 硬约束: {', '.join(intent.constraints) if intent.constraints else '无'}
- 饮食与兴趣偏好: {', '.join(intent.preferences) if intent.preferences else '无特殊偏好'}
按这些条件调整推荐。少走路时优先交通接驳方便、步行量较低的地点；不爬山时不要推荐登山路线；不辣时注明清淡或不辣的菜品选择。
"""


def _parse_json_text(text: str, label: str):
    text = text.strip()
    if not text:
        raise AgentOutputError(f"{label}输出为空")

    # Accept complete fenced JSON, but do not repair truncated output.
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AgentOutputError(
            f"{label}输出不是完整合法的 JSON（可能被截断），位置 {exc.lineno}:{exc.colno}"
        ) from exc


def _parse_item(item, item_model: type[BaseModel], identifier_field: str, label: str, index: int):
    if isinstance(item, item_model):
        model = item
    elif isinstance(item, BaseModel):
        raise AgentOutputError(f"{label}第 {index + 1} 条类型错误：期望 {item_model.__name__}")
    elif isinstance(item, dict):
        try:
            model = item_model.model_validate(item)
        except ValidationError as exc:
            raise AgentOutputError(f"{label}第 {index + 1} 条字段无效") from exc
    else:
        raise AgentOutputError(f"{label}第 {index + 1} 条必须是对象")

    identifier = getattr(model, identifier_field, None)
    if not isinstance(identifier, str) or not identifier.strip():
        raise AgentOutputError(f"{label}第 {index + 1} 条缺少有效的 {identifier_field}")
    return model


def _parse_collection(raw, wrapper_model: type[BaseModel], item_model: type[BaseModel],
                      identifier_field: str, label: str):
    if isinstance(raw, str):
        raw = _parse_json_text(raw, label)

    if isinstance(raw, wrapper_model):
        items = raw.items
    elif isinstance(raw, BaseModel):
        raise AgentOutputError(f"{label}包装类型错误：期望 {wrapper_model.__name__}")
    elif isinstance(raw, dict):
        items = raw["items"] if "items" in raw else [raw]
    elif isinstance(raw, list):
        items = raw
    else:
        raise AgentOutputError(f"{label}结果必须是对象列表或包含 items 的对象")

    if not isinstance(items, list):
        raise AgentOutputError(f"{label}的 items 必须是数组")
    if not items:
        raise AgentOutputError(f"{label}结果为空")
    return [_parse_item(item, item_model, identifier_field, label, index)
            for index, item in enumerate(items)]


class AttractionRecommenderAgent(BaseAgent[RoutePlan | TravelAgentContext, list[Spot]]):
    """景点推荐器: 路线 → 景点列表"""

    @property
    def output_schema(self):
        return SpotList

    @property
    def system_prompt(self) -> str:
        return """你是一位资深旅游编辑，曾为《孤独星球》《中国国家地理》撰稿。你对中国各地的景点了如指掌。

## 任务
为路线中的每个城市推荐景点，分三层:

- **Tier 1 (必去经典, 2~3个)**: 第一次来必打卡，知名度最高的
- **Tier 2 (深度体验, 3~5个)**: 有时间的值得去，比大众景点更有味道
- **Tier 3 (小众宝藏, 2~3个)**: 游客少但体验绝佳，本地人推荐的

## 输出格式
{"items": [
  {
    "name": "洱海",
    "city": "大理",
    "tier": 1,
    "type": "自然风光",
    "duration": "0.5天",
    "best_time": "日出6:30-7:00 / 日落18:30-19:30",
    "ticket": null,
    "ticket_status": "unknown",
    "tags": ["骑行", "拍照", "发呆"],
    "photo_spots": [
      {"name": "龙龛码头", "best_time": "日出 6:30-7:00", "shot": "逆光剪影"},
      {"name": "双廊观景台", "best_time": "日落 18:30-19:30", "shot": "耶稣光"}
    ],
    "tips": "顺时针环湖，租电动车80元/天，避开中午暴晒",
    "nearby_food": ["喜洲粑粑", "酸辣鱼", "乳扇"]
  }
]}

## 原则
- 每个城市推荐 6~10 个景点
- 每个景点必须带 city 字段（所属城市），用于后续地图定位
- 门票字段必须区分：ticket_status="reference" 时 ticket 填大于0的模型参考金额；明确免费时用 ticket_status="free" 且 ticket=0；无法确认时用 ticket_status="unknown" 且 ticket=null。旧数据的 ticket=0 代表未知，不代表免费。
- 门票金额、开放时间不能猜成已核实事实；ticket_status="reference" 也只是模型参考，攻略必须提示用户查景区官方信息。
- 每个景点给 1~3 个拍照机位
- 不要编造不存在的景点
- 必须遵守旅行者硬约束，不要把兴趣偏好当成覆盖硬约束的理由

请按 schema 返回包含 items 数组的结构化对象。"""

    def build_user_prompt(self, data: RoutePlan | TravelAgentContext) -> str:
        route, intent = _route_and_intent(data)
        cities = route.cities
        guidance = _intent_guidance(intent)
        return f"""请为以下城市的旅行路线推荐景点:

途经城市: {', '.join(cities)}
旅行天数: {len(route.daily_plan)}天
旅行节奏: 每天{len(route.daily_plan[0].__dict__) if route.daily_plan else '3'}个时段
{guidance}

为每个城市输出 tier1/tier2/tier3 三层景点推荐（每个景点带 city 字段）。
输出包含 items 数组的结构化对象:"""

    def parse_output(self, raw: Any) -> list[Spot]:
        return _parse_collection(raw, SpotList, Spot, "name", "景点推荐")


class CultureEngineAgent(BaseAgent[RoutePlan | TravelAgentContext, list[CultureData]]):
    """风土人情引擎: 路线 → 每个城市的文化内容"""

    @property
    def output_schema(self):
        return CultureList

    @property
    def system_prompt(self) -> str:
        return """你是一位中国民俗文化学者和美食评论家。你在中国各地生活过超过30年，对各地方言、饮食、节庆、禁忌有深入的实地研究。

## 任务
为每个城市从以下维度输出风土人情内容:

### 1. 美食地图
- must_eat: 必吃菜 Top5，每道菜含推荐理由、去哪吃（具体店名）、人均价格
- night_market: 夜市/小吃街推荐
- souvenir: 伴手礼推荐

### 2. 民俗文化
- ethnic_groups: 主要民族
- architecture: 建筑风格
- dialect: 方言短语 3~5句（带拼音和使用场景）
- clothing: 民族服饰特点

### 3. 节庆活动
当地节日时间表 + 看点

### 4. 历史典故
与城市/景点相关的真实故事（有人物/时间/事件）

### 5. 礼仪禁忌
具体规则 + 违反的后果

### 6. 生活方式
当地人一天的时间线 + 特色市场/赶集日

## 输出格式
{"items": [
  {
    "city": "大理",
    "cuisine": {
      "must_eat": [
        {"name": "大理酸辣鱼", "reason": "洱海鲫鱼+木瓜+辣椒", "where": "梅子井酒家", "price_per_person": 60, "tips": "古城里的贵，去下关吃正宗的"}
      ]
    },
    "folk_culture": {
      "ethnic_groups": ["白族"],
      "architecture": "白族照壁——三坊一照壁，四合五天井",
      "dialect": [
        {"phrase": "阿鹏", "pinyin": "a peng", "meaning": "对白族男子的称呼", "usage": "电影《五朵金花》后流行"}
      ]
    },
    "festivals": [
      {"name": "三月街", "date": "农历三月十五", "what_to_see": "千年赶一街，赛马对歌"}
    ],
    "history": [
      {"story": "大理古城是南诏国和大理国的都城，《天龙八部》段誉原型为大理国第16代国王段正严...", "period": "唐宋"}
    ],
    "taboos": [
      {"rule": "进白族家门不能踩门槛", "context": "白族民居", "consequence": "被视为不尊重主人"}
    ],
    "lifestyle": {
      "daily_rhythm": "早上吃饵丝→上午赶集→下午喝茶→晚上逛古城",
      "markets": ["大理古城菜市场（早上最热闹）", "三月街（每月农历初二、初九、十六、二十三）"]
    }
  }
]}

## 铁律
- 美食推荐必须具体到店名，不能只说"去当地人开的店"
- 方言必须有拼音和使用场景
- 禁忌必须具体，不能用"尊重当地习俗"这种废话
- 不要编造不存在的节日或习俗
- 必须遵守旅行者的饮食与行动硬约束；不辣需求应给清淡替代建议，不得只罗列辣菜

请按 schema 返回包含 items 数组的结构化对象。"""

    def build_user_prompt(self, data: RoutePlan | TravelAgentContext) -> str:
        route, intent = _route_and_intent(data)
        guidance = _intent_guidance(intent)
        travel_period = (
            intent.travel_date_note or intent.travel_date or "未指定"
            if intent else "未指定"
        )
        return f"""请为以下城市输出完整的风土人情指南:

途经城市: {', '.join(route.cities)}
出行时间: {travel_period}
{guidance}

请覆盖: 美食地图、民俗文化、节庆活动、历史典故、礼仪禁忌、生活方式。
输出包含 items 数组的结构化对象:"""

    def parse_output(self, raw: Any) -> list[CultureData]:
        return _parse_collection(raw, CultureList, CultureData, "city", "城市文化")
