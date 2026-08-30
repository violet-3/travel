"""
路线规划器 Agent · TravelIntent → RoutePlan

根据用户意图生成完整的多日行程骨架，包括:
- 每天去哪个城市、上午/下午/晚上做什么
- 城市间交通方式
- 注意事项（高反/预约/季节）

关键设计:
- 使用路线模板库作为先验知识，减少 LLM 幻觉
- LLM 在模板基础上根据用户偏好微调
"""

import json
from agents.base import BaseAgent
from models.schemas import TravelIntent, RoutePlan
from knowledge.route_templates import get_templates_for, ROUTE_TEMPLATES
from tools.json_utils import parse_json


class RoutePlannerAgent(BaseAgent[TravelIntent, RoutePlan]):
    """路线规划器: 意图 → 路线"""

    @property
    def system_prompt(self) -> str:
        return """你是一位拥有 15 年经验的中国旅游路线规划师。你对中国各省市的地理位置、交通网络、气候特征、景区特色了如指掌。

## 工作流程
1. 分析用户的意图（目的地、天数、偏好、节奏）
2. 从经典路线模板库中匹配，生成行程骨架
3. 根据用户偏好调整：喜欢自然风光的加户外景点，喜欢美食的加食街
4. 控制每日项目数量：特种兵4-6项，不紧不慢3-4项，轻松2-3项
5. 标注需要预约的项目和高原/安全提醒

## 地域知识要点
- 云南: 昆明(春城)→大理(洱海/古城)→丽江(古城/雪山)→香格里拉(藏族文化/高原)
- 四川: 成都(熊猫/火锅)→九寨沟(水景)→稻城亚丁(雪山)
- 西北: 西宁→青海湖→茶卡盐湖→敦煌(莫高窟/鸣沙山)
- 华东: 杭州(西湖)→苏州(园林)→上海(都市)→南京(古都)
- 华南: 桂林(山水)→阳朔(竹筏)→北海(银滩)
- 西南: 贵阳→黄果树→荔波→西江千户苗寨

## 交通规则
- 省内城市间优先高铁/动车（200-350km/h）
- 山区用大巴（如丽江→香格里拉）
- 超过800km考虑飞机
- 标注每段交通耗时和预估费用

## 输出格式
{
  "route_name": "昆大丽香7日经典线",
  "cities": ["昆明", "大理", "丽江", "香格里拉"],
  "daily_plan": [
    {
      "day": 1,
      "city": "昆明",
      "morning": {"name": "抵达昆明长水机场", "note": "机场大巴到市区25元"},
      "afternoon": {"name": "翠湖公园+讲武堂", "note": "免费，冬季可看红嘴鸥"},
      "evening": {"name": "南强街夜市", "note": "推荐烤乳扇、过桥米线"},
      "stay": "昆明市区五华区"
    }
  ],
  "transport": [
    {"from": "昆明", "to": "大理", "mode": "动车", "duration": "2h", "cost_est": 145}
  ],
  "warnings": ["香格里拉海拔3300m注意高反", "玉龙雪山索道需提前3天预约"],
  "total_budget_est": 4500
}

只输出 JSON，不要解释。"""

    def build_user_prompt(self, intent: TravelIntent) -> str:
        # 查找匹配的路线模板
        templates = get_templates_for(intent.destinations, intent.days)

        template_hint = ""
        if templates:
            template_hint = f"""
## 匹配的路线模板（参考，可根据用户偏好调整）
{json.dumps(templates, ensure_ascii=False, indent=2)}
"""

        return f"""请为以下用户规划旅行路线:

- 目的地: {', '.join(intent.destinations)}
- 天数: {intent.days}天
- 预算级别: {intent.budget_level} (预算: {intent.budget or '未指定'}元)
- 同行人: {intent.companion}
- 节奏: {intent.pace}
- 偏好: {', '.join(intent.preferences) if intent.preferences else '无特殊偏好'}
- 出发城市: {intent.departure_city or '未指定'}
- 出行日期: {intent.travel_date or '未指定'}
- 特殊约束: {', '.join(intent.constraints) if intent.constraints else '无'}

{template_hint}

请输出完整的路线规划 JSON:"""

    def parse_output(self, raw: dict | str) -> RoutePlan:
        if isinstance(raw, str):
            raw = parse_json(raw)
        return RoutePlan(**raw)
