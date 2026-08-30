"""
意图解析器 Agent · 用户自由文本 → 结构化 TravelIntent

这是整个系统的入口。用户说"想去云南玩7天"，Agent 提取出:
- 目的地: 云南
- 天数: 7
- 预算: 未指定→默认中等
- 偏好: 未指定→默认空
- 等等
"""

from datetime import datetime

from agents.base import BaseAgent
from models.schemas import TravelIntent
from tools.json_utils import parse_json


class IntentParserAgent(BaseAgent[str, TravelIntent]):
    """意图解析器: 自由文本 → 结构化意图"""

    @property
    def system_prompt(self) -> str:
        return """你是一个旅行意图解析专家。你的任务是从用户的自由文本中提取结构化的旅行信息。

## 提取字段

1. **destinations** (必填): 目的地城市/省份列表
   - 用户说"云南"→ ["云南"]
   - 用户说"成都和重庆"→ ["成都", "重庆"]
   - 用户说"江浙沪"→ ["南京", "杭州", "上海"]

2. **days** (必填): 旅行天数，未指定默认3
   - "玩7天"→ 7
   - "周末去"→ 2
   - "一周左右"→ 7

3. **budget** (选填): 预算金额(元)，不填则为null
   - "预算3000"→ 3000
   - "人均2000"→ 2000

4. **budget_level** (必填): 预算级别
   - 人均<1500 → "经济"
   - 人均1500-4000 → "中等"
   - 人均4000-8000 → "舒适"
   - 人均>8000 → "豪华"

5. **companion** (必填): 同行人
   - "一个人/独自"→ "独自"
   - "和女朋友/男朋友"→ "情侣"
   - "和朋友/同学"→ "朋友"
   - "带爸妈/带老人"→ "父母"
   - "带小孩/亲子"→ "带娃"

6. **pace** (必填): 旅行节奏
   - "特种兵/打卡/赶"→ "特种兵"
   - "轻松/慢/休闲/不累"→ "轻松"
   - 默认→ "不紧不慢"

7. **preferences** (选填): 兴趣偏好
   - 自然风光/人文历史/美食/摄影/徒步/购物/夜生活/亲子

8. **departure_city** (选填): 出发城市
   - "从北京出发"→ "北京"

9. **travel_date** (选填): 出行日期 YYYY-MM-DD
   - "五一去"→ 推断2026年五一假期日期
   - "国庆"→ 推断2026年国庆
   - "下个月"→ 当前月份+1
   - "春节"→ 推断春节日期

10. **constraints** (选填): 硬约束
    - "不爬山"→ ["不爬山"]
    - "不能吃辣"→ ["不辣"]
    - "带老人腿脚不便"→ ["不爬山", "少走路"]
    - "需要无障碍通道"→ ["无障碍"]

## 输出格式
只输出一个 JSON 对象。"""

    def build_user_prompt(self, user_input: str) -> str:
        now = datetime.now()
        return f"""请分析以下用户的旅行需求，提取结构化信息:

用户输入: {user_input}

当前日期: {now.year}年{now.month}月{now.day}日
请直接输出 JSON:"""

    def parse_output(self, raw: dict | str) -> TravelIntent:
        if isinstance(raw, str):
            raw = parse_json(raw)
        return TravelIntent(**raw)
