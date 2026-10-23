"""
数据模型 · Pydantic Schemas

所有从 Dify JSON 来的嵌套对象用 dict 而非 Pydantic Model
原因: dict 可以用 .get() 安全访问，Pydantic Model 不行
"""

import hashlib

from pydantic import BaseModel, Field, model_validator
from typing import Literal
from typing import Optional
from datetime import datetime
from urllib.parse import urlsplit


def _validate_public_http_url(value: str) -> str:
    if not isinstance(value, str) or len(value) > 8192 or any(ord(char) < 0x21 for char in value):
        raise ValueError("网页来源地址无效")
    try:
        parts = urlsplit(value)
        _ = parts.port
    except ValueError:
        raise ValueError("网页来源地址无效") from None
    if (parts.scheme.lower() not in {"http", "https"} or not parts.hostname
            or parts.username is not None or parts.password is not None):
        raise ValueError("网页来源地址无效")
    return value


class TravelIntent(BaseModel):
    destinations: list[str] = Field(default_factory=list)
    days: int = Field(default=3, ge=1, le=60)
    budget: Optional[int] = Field(default=None, gt=0, le=100_000_000)
    budget_scope: Literal["per_person", "total"] = "per_person"
    travelers: int = Field(default=1, ge=1, le=50)
    budget_level: str = "中等"
    companion: str = "独自"
    pace: str = "不紧不慢"
    preferences: list[str] = Field(default_factory=list)
    departure_city: Optional[str] = None
    travel_date: Optional[str] = None
    travel_month: Optional[str] = None
    travel_date_note: str = ""
    constraints: list[str] = Field(default_factory=list)


class TravelIntentInput(BaseModel):
    """Natural language plus only the form values the user explicitly supplied."""

    query: str = ""
    overrides: dict = Field(default_factory=dict)


class Activity(BaseModel):
    name: str = ""
    note: str = ""
    coordinate: Optional[list[float]] = None
    coordinate_verified: bool = False
    coordinate_source: str = ""
    coordinate_checked_at: Optional[str] = None
    poi_id: str = ""


class DayPlan(BaseModel):
    day: int
    city: str
    city_center: Optional[list[float]] = None
    morning: Activity = Field(default_factory=Activity)
    afternoon: Activity = Field(default_factory=Activity)
    evening: Activity = Field(default_factory=Activity)
    stay: str = ""
    stay_coordinate: Optional[list[float]] = None
    stay_coordinate_verified: bool = False


class Transport(BaseModel):
    from_city: str = Field(default="", alias="from")
    to_city: str = Field(default="", alias="to")
    mode: str = ""
    duration: str = ""
    cost_est: Optional[int] = Field(default=None, ge=0, le=100_000_000)
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


class TravelAgentContext(BaseModel):
    """Canonical user request paired with the generated route for downstream agents."""

    route: RoutePlan
    intent: TravelIntent


class PhotoSpot(BaseModel):
    name: str = ""
    best_time: str = ""
    shot: str = ""


class WebImageCandidate(BaseModel):
    url: str = ""
    alt: str = ""
    association: Literal["alt_mentions_spot", "unverified"] = "unverified"
    status: Literal[
        "candidate", "downloaded", "unsafe_url", "unsafe_redirect",
        "unsafe_or_unresolved_host", "redirect_limit", "http_error",
        "not_image", "too_large", "invalid_image", "cache_error",
        "timeout", "network_error",
    ] = "candidate"
    local_url: str = ""
    downloaded_at: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def validate_candidate_url(cls, value):
        if isinstance(value, dict) and value.get("url"):
            value = dict(value)
            value["url"] = _validate_public_http_url(value["url"])
        return value


class WebEvidence(BaseModel):
    source_id: str = ""
    title: str = ""
    url: str = ""
    site_name: str = ""
    status: Literal["search_only", "fetched"] = "search_only"
    fetch_status: Literal["not_attempted", "fetched", "mismatch", "error"] = "not_attempted"
    city_match: Literal["matched", "unverified"] = "unverified"
    fetched_at: Optional[str] = None
    snippet: str = ""
    quotes: list[str] = Field(default_factory=list)
    price_quotes: list[str] = Field(default_factory=list)
    image_candidates: list[WebImageCandidate] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def validate_source_url(cls, value):
        if isinstance(value, dict) and value.get("url"):
            value = dict(value)
            value["url"] = _validate_public_http_url(value["url"])
        return value

    @model_validator(mode="after")
    def source_id_matches_url(self):
        if self.url:
            expected = hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:16]
            if self.source_id != expected:
                raise ValueError("网页来源 ID 与来源地址不匹配")
        return self


class WebSpotResearch(BaseModel):
    spot_index: int = Field(ge=0)
    spot_name: str = ""
    city: str = ""
    status: Literal[
        "disabled", "unavailable", "searched", "no_results", "no_city_match",
        "no_spot_match", "page_unmatched", "error", "skipped_limit",
    ] = "disabled"
    evidence: list[WebEvidence] = Field(default_factory=list)


class WebResearchStatus(BaseModel):
    status: Literal["disabled", "unavailable", "complete", "partial", "failed"] = "disabled"
    message: str = ""
    searched_spots: int = 0
    search_count: int = 0
    fetch_count: int = 0
    image_candidate_count: int = 0
    images_downloaded: int = 0
    completed_at: Optional[str] = None
    spots: list[WebSpotResearch] = Field(default_factory=list)


class Spot(BaseModel):
    name: str = ""
    city: str = ""                                          # 所属城市（富化层按城市搜 POI）
    tier: int = 1
    type: str = ""
    duration: str = ""
    best_time: str = ""
    # None / unknown means price unavailable. ticket=0 is free only with status=free.
    ticket: Optional[int] = Field(default=None, ge=0)
    ticket_status: Literal["unknown", "reference", "free"] = "unknown"
    tags: list[str] = Field(default_factory=list)
    photo_spots: list[PhotoSpot] = Field(default_factory=list)
    tips: str = ""
    nearby_food: list[str] = Field(default_factory=list)
    coordinate: Optional[list[float]] = None
    coordinate_verified: bool = False
    coordinate_source: str = ""
    coordinate_checked_at: Optional[str] = None
    poi_id: str = ""
    photo: str = ""                                         # 本地图片 URL（实景图/位置示意图/未知来源）
    photo_source: str = "none"                              # 富化层填写，模型值会被清理
    photo_checked_at: Optional[str] = None

    @model_validator(mode="after")
    def normalize_legacy_ticket_price(self):
        # Prior archives used ticket=0 for an unknown price. Positive legacy
        # values remain readable as model reference prices; zero stays unknown.
        if self.ticket_status == "free":
            if self.ticket not in (None, 0):
                raise ValueError("免费景点的 ticket 必须为 0 或 null")
            self.ticket = 0
        elif self.ticket_status == "reference":
            if self.ticket is None or self.ticket <= 0:
                raise ValueError("参考门票价必须大于 0")
        elif self.ticket is not None and self.ticket > 0:
            self.ticket_status = "reference"
        return self


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
    # `total` is the per-person known-cost subtotal; unknown transport is excluded.
    total: int = 0
    group_total: int = 0
    travelers: int = 1
    nights: int = 0
    transport_unknown_segments: list[str] = Field(default_factory=list)
    estimate_notes: list[str] = Field(default_factory=list)
    budget_status: Literal[
        "no_budget", "over_known_budget", "needs_transport_quote",
        "needs_price_review", "within_estimate"
    ] = "no_budget"
    # 门票拆分为“景点标价累加”和“未知单价兜底估算”，便于用户判断可信度
    tickets_known: int = 0
    tickets_estimated: int = 0
    tickets_pending_spots: list[str] = Field(default_factory=list)
    tickets_free_spots: list[str] = Field(default_factory=list)
    tickets_unpriced_activities: list[str] = Field(default_factory=list)
    # 住宿按行程所在城市的等级系数折算，保留实际采用的单价便于复核
    lodging_night_rate: int = 0
    lodging_cities: list[str] = Field(default_factory=list)
    # 各项占人均已知小计的比例，用于发现结构异常（例如交通占比过高）
    cost_share: dict = Field(default_factory=dict)


class TravelGuide(BaseModel):
    title: str = ""
    subtitle: str = ""
    destinations: list[str] = Field(default_factory=list)
    departure_city: str = ""                                    # 出发地
    days: int = 0
    budget_level: str = ""
    request: Optional[TravelIntent] = None
    route: RoutePlan = Field(default_factory=RoutePlan)
    spots: list[Spot] = Field(default_factory=list)
    cultures: list[CultureData] = Field(default_factory=list)
    budget: BudgetBreakdown = Field(default_factory=BudgetBreakdown)
    weather: list[dict] = Field(default_factory=list)
    clothing_tip: str = ""
    # 第12轮：基于已核验坐标的行程可执行性判断（含逐日通勤与问题清单）
    feasibility: dict = Field(default_factory=dict)
    # 第13轮：天气驱动的行前清单与逐日备选方案
    prep: dict = Field(default_factory=dict)
    # 第14轮：确定性的攻略质量自检（分数、维度、问题清单）
    quality: dict = Field(default_factory=dict)
    amap_ready: bool = False                                # 高德是否就绪
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    generation_metrics: dict = Field(default_factory=dict)
    history_id: Optional[str] = None
    history_saved: bool = False
    # 第15轮：本次结果是否复用了短时缓存（不影响内容本身的可信度）
    cache_hit: bool = False
    cache_age_seconds: Optional[int] = None
    web_research: WebResearchStatus = Field(default_factory=WebResearchStatus)
