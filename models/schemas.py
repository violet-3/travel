"""
数据模型 · Pydantic Schemas

所有从 Dify JSON 来的嵌套对象用 dict 而非 Pydantic Model
原因: dict 可以用 .get() 安全访问，Pydantic Model 不行
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TravelIntent(BaseModel):
    destinations: list[str] = Field(default_factory=list)
    days: int = Field(default=3, ge=1)
    budget: Optional[int] = None
    budget_level: str = "中等"
    companion: str = "独自"
    pace: str = "不紧不慢"
    preferences: list[str] = Field(default_factory=list)
    departure_city: Optional[str] = None
    travel_date: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)


class Activity(BaseModel):
    name: str = ""
    note: str = ""
    coordinate: Optional[list[float]] = None


class DayPlan(BaseModel):
    day: int
    city: str
    city_center: Optional[list[float]] = None
    morning: Activity = Field(default_factory=Activity)
    afternoon: Activity = Field(default_factory=Activity)
    evening: Activity = Field(default_factory=Activity)
    stay: str = ""
    stay_coordinate: Optional[list[float]] = None


class Transport(BaseModel):
    from_city: str = Field(default="", alias="from")
    to_city: str = Field(default="", alias="to")
    mode: str = ""
    duration: str = ""
    cost_est: int = 0
    from_coord: Optional[list[float]] = None
    to_coord: Optional[list[float]] = None

    class Config:
        populate_by_name = True


class RoutePlan(BaseModel):
    route_name: str = ""
    cities: list[str] = Field(default_factory=list)
    daily_plan: list[DayPlan] = Field(default_factory=list)
    transport: list[Transport] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    total_budget_est: int = 0


class PhotoSpot(BaseModel):
    name: str = ""
    best_time: str = ""
    shot: str = ""


class Spot(BaseModel):
    name: str = ""
    city: str = ""                                          # 所属城市（富化层按城市搜 POI）
    tier: int = 1
    type: str = ""
    duration: str = ""
    best_time: str = ""
    ticket: int = 0
    tags: list[str] = Field(default_factory=list)
    photo_spots: list[PhotoSpot] = Field(default_factory=list)
    tips: str = ""
    nearby_food: list[str] = Field(default_factory=list)
    coordinate: Optional[list[float]] = None
    photo: str = ""                                         # 实景图 URL（富化层回填，/static/photos/...）


class CultureData(BaseModel):
    """城市风土人情 · 嵌套数据用 dict 而非 Pydantic Model，方便 .get() 安全访问"""
    city: str = ""
    cuisine: dict = Field(default_factory=dict)
    folk_culture: dict = Field(default_factory=dict)
    festivals: list[dict] = Field(default_factory=list)     # ← dict, 不是 Festival Model
    history: list[dict] = Field(default_factory=list)
    taboos: list[dict] = Field(default_factory=list)        # ← dict, 不是 Taboo Model
    lifestyle: dict = Field(default_factory=dict)


class BudgetBreakdown(BaseModel):
    transport: int = 0
    accommodation: int = 0
    tickets: int = 0
    food: int = 0
    other: int = 0
    total: int = 0


class TravelGuide(BaseModel):
    title: str = ""
    subtitle: str = ""
    destinations: list[str] = Field(default_factory=list)
    departure_city: str = ""                                    # 出发地
    days: int = 0
    budget_level: str = ""
    route: RoutePlan = Field(default_factory=RoutePlan)
    spots: list[Spot] = Field(default_factory=list)
    cultures: list[CultureData] = Field(default_factory=list)
    budget: BudgetBreakdown = Field(default_factory=BudgetBreakdown)
    weather: list[dict] = Field(default_factory=list)
    clothing_tip: str = ""
    amap_ready: bool = False                                # 高德是否就绪
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
