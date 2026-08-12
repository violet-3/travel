"""
路线模板库 · 先验知识

LLM 对中国旅游的知识不完整（训练数据偏旧、容易幻觉）。
这里存储了经典路线的结构化模板，作为 RoutePlanner 的参考。

使用方式:
    get_templates_for(["云南"], 7) → 返回匹配度最高的模板
"""

# 路线模板: key = 目的地关键词, value = 经典路线列表
ROUTE_TEMPLATES: dict[str, list[dict]] = {
    "云南": [
        {
            "name": "昆大丽香 7 日经典线",
            "days": 7,
            "cities": ["昆明", "大理", "丽江", "香格里拉"],
            "pace": "不紧不慢",
            "suitable_for": ["自然风光", "人文历史", "摄影"],
            "best_season": "4-5月 / 9-11月",
            "transport": [
                {"from": "昆明", "to": "大理", "mode": "动车", "duration": "2h"},
                {"from": "大理", "to": "丽江", "mode": "动车", "duration": "1.5h"},
                {"from": "丽江", "to": "香格里拉", "mode": "大巴", "duration": "3h"},
            ],
            "highlights": ["洱海骑行", "玉龙雪山", "独克宗古城"],
            "warnings": ["香格里拉海拔3300m注意高反", "玉龙雪山大索道需提前3天20:00抢票"],
        },
        {
            "name": "昆明大理丽江 5 日精华线",
            "days": 5,
            "cities": ["昆明", "大理", "丽江"],
            "pace": "不紧不慢",
            "suitable_for": ["自然风光", "美食", "休闲"],
            "transport": [
                {"from": "昆明", "to": "大理", "mode": "动车", "duration": "2h"},
                {"from": "大理", "to": "丽江", "mode": "动车", "duration": "1.5h"},
            ],
        },
        {
            "name": "西双版纳 4 日热带风情线",
            "days": 4,
            "cities": ["西双版纳"],
            "pace": "轻松",
            "suitable_for": ["自然风光", "少数民族文化", "亲子"],
            "best_season": "11-2月（避开雨季）",
        },
    ],
    "四川": [
        {
            "name": "成都及周边 5 日休闲线",
            "days": 5,
            "cities": ["成都", "都江堰", "乐山"],
            "pace": "不紧不慢",
            "suitable_for": ["美食", "人文历史", "休闲"],
            "highlights": ["大熊猫基地", "都江堰", "乐山大佛", "宽窄巷子"],
            "transport": [
                {"from": "成都", "to": "都江堰", "mode": "城际列车", "duration": "30min"},
                {"from": "成都", "to": "乐山", "mode": "高铁", "duration": "1h"},
            ],
        },
        {
            "name": "川西大环线 8 日深度线",
            "days": 8,
            "cities": ["成都", "康定", "新都桥", "稻城", "色达"],
            "pace": "特种兵",
            "suitable_for": ["自然风光", "摄影", "徒步"],
            "best_season": "5-10月",
            "warnings": ["稻城亚丁海拔4700m", "色达佛学院需提前预约"],
        },
    ],
    "西北": [
        {
            "name": "青甘大环线 7 日经典线",
            "days": 7,
            "cities": ["西宁", "青海湖", "茶卡", "敦煌", "张掖"],
            "pace": "不紧不慢",
            "suitable_for": ["自然风光", "摄影", "人文历史"],
            "best_season": "6-8月",
        },
    ],
    "华东": [
        {
            "name": "江南水乡 5 日柔情线",
            "days": 5,
            "cities": ["杭州", "苏州", "乌镇", "上海"],
            "pace": "轻松",
            "suitable_for": ["人文历史", "美食", "休闲"],
            "transport": [
                {"from": "杭州", "to": "苏州", "mode": "高铁", "duration": "1.5h"},
                {"from": "苏州", "to": "上海", "mode": "高铁", "duration": "30min"},
            ],
        },
    ],
    "华南": [
        {
            "name": "桂林阳朔 4 日山水线",
            "days": 4,
            "cities": ["桂林", "阳朔"],
            "pace": "轻松",
            "suitable_for": ["自然风光", "摄影", "亲子"],
            "highlights": ["漓江竹筏", "阳朔西街", "龙脊梯田"],
        },
    ],
}


def get_templates_for(destinations: list[str], days: int) -> list[dict]:
    """根据目的地和天数查找匹配的路线模板"""
    results = []

    for dest in destinations:
        for key, templates in ROUTE_TEMPLATES.items():
            if key in dest or dest in key:
                for t in templates:
                    # 天数匹配: ±2天内都算匹配
                    if abs(t["days"] - days) <= 2:
                        results.append(t)

    # 按天数匹配度排序
    results.sort(key=lambda t: abs(t["days"] - days))
    return results[:2]  # 最多返回2个最匹配的
