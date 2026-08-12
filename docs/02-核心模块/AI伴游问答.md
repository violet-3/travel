---
tags: [module, travel-agent, companion]
created: 2026-06-30
---

# AI 伴游问答 (AI Travel Companion)

## 职责

攻略生成后不是终点——用户在旅途中随时有疑问。AI 伴游提供**行程上下文感知**的实时问答。

## 与普通 AI 问答的区别

```
普通 AI 问答:
  用户: "附近有什么好吃的？"
  AI: ❓ (没有位置上下文，瞎猜)

AI 伴游:
  用户: "附近有什么好吃的？"
  AI: "你今天在 Day3 的大理古城，攻略里推荐了梅子井酒家（距你800m），
        另外附近还有杨记喜洲粑粑（距你350m），人均¥10。要导航过去吗？"
  ✅ 知道当前位置 + 知道当天行程 + 知道攻略推荐过什么
```

## 上下文注入

```python
class CompanionContext:
    """伴游问答的上下文"""
    
    def build_prompt(self, travel_data: UnifiedTravelData, 
                     current_day: int, user_location: tuple,
                     user_question: str) -> str:
        return f"""
你是一位正在陪同用户旅行的 AI 伴游。你现在掌握以下上下文：

## 用户当前状态
- 日期：{travel_data.daily_plan[current_day].date}
- 城市：{travel_data.daily_plan[current_day].city}
- 当前时间：{datetime.now().strftime('%H:%M')}
- 当前位置：{user_location}（纬度/经度）
- 今日行程：{travel_data.daily_plan[current_day].summary}

## 完整攻略上下文
{travel_data.markdown_summary}

## 附近信息
{self._get_nearby_spots(user_location, travel_data.spots)}
{self._get_nearby_food(user_location, travel_data.culture.cuisine)}

## 用户问题
{user_question}

请基于以上上下文回答。如果用户问攻略中已包含的内容，直接引用。
如果用户问攻略外的问题（如实时天气/临时改行程），如实告知你的知识边界。
"""
```

## 典型问答场景

| 用户问题 | AI 伴游回答 |
|---------|-----------|
| "下雨了怎么办" | 调用天气 API + 攻略中的室内备选景点推荐 |
| "走累了想休息" | 推荐附近评分 4.5+ 的茶馆/咖啡馆（攻略中标记的） |
| "这个景点和攻略说的不一样" | 解释可能原因（装修/季节/时间），推荐替代景点 |
| "想临时加一个地方" | 搜索附近 5km 内的未在攻略中但高评分的景点 |
| "带爸妈来合适吗" | 分析当前行程的体力消耗，给出调整建议 |
| "帮我导航到下一站" | 调用高德地图生成导航链接 |

## 实现架构

```
用户手机端（微信公众号/小程序/Web）
        │
        │ WebSocket（长连接）
        ▼
┌───────────────────────┐
│  AI 伴游服务            │
│                       │
│  请求 → 上下文组装 → LLM → 回答 │
│                │              │
│                ├── 攻略上下文   │
│                ├── 实时位置     │
│                ├── 天气 API    │
│                └── 高德附近搜索 │
└───────────────────────┘
```

## 离线降级

旅途中网络不稳定时：

```python
class OfflineFallback:
    """离线降级策略"""
    
    def __init__(self, travel_data: UnifiedTravelData):
        self.cached_qa = self._precompute_common_questions(travel_data)
        self.offline_index = self._build_search_index(travel_data)
    
    def answer_offline(self, question: str) -> str:
        # 1. 先在预计算 FAQ 中匹配
        for q, a in self.cached_qa.items():
            if self._similar(question, q) > 0.8:
                return a
        
        # 2. 全文搜索离线攻略
        results = self.offline_index.search(question, top_k=3)
        
        # 3. 返回最相关段落
        return f"（离线模式）攻略中提到：\n\n{results[0].text}"
```

## 前端交互

```
┌─────────────────────────────────┐
│  🗺️ Day 3 · 大理古城              │
│                                  │
│  [地图 + 行程主内容区域]            │
│                                  │
├─────────────────────────────────┤
│  💬 AI 伴游                    │  ← 底部可收起
│  ─────────────────────────────  │
│  🤖: 现在是下午3点，按攻略推荐     │
│      该去双廊看日落了（18:30日落）  │
│      距你12km，打车约25分钟 ¥20    │
│                                  │
│  [📍 导航到双廊]  [🔄 换个推荐]    │
│  ─────────────────────────────  │
│  [🗣️ 输入问题...]          [发送] │
└─────────────────────────────────┘
```

## 与 TripStar 对比

| | TripStar 伴游 | 本项目伴游 |
|------|------|------|
| 位置 | 左下角悬浮窗 | 底部可收起面板 |
| 上下文 | 行程数据 | 行程 + 景点详情 + 拍照机位 + 美食 |
| 离线 | 不支持 | ✅ 预计算 FAQ + 离线搜索 |
| 导航 | 无 | ✅ 一键跳转高德导航 |
