"""
山河游记 · 配置文件
"""

import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class DifyConfig:
    base_url: str = "http://192.168.0.11/v1"
    # TODO: 请填写你自己的 Dify App API Key
    intent_key: str = "app-YOUR_DIFY_INTENT_KEY"
    route_key: str = "app-YOUR_DIFY_ROUTE_KEY"
    content_key: str = "app-YOUR_DIFY_CONTENT_KEY"
    temperature: float = 0.5

    def get_key(self, workflow: str) -> str:
        return {"intent": self.intent_key, "route": self.route_key, "content": self.content_key}[workflow]
#

@dataclass
class AmapConfig:
    """高德地图 API 配置"""
    # TODO: 请填写你自己的高德地图 API Key
    weather_key: str = "YOUR_AMAP_WEATHER_KEY"    # Web服务 Key (天气)
    route_key: str = "YOUR_AMAP_JS_API_KEY"       # Web端 JS API Key (地图)
    secret: str = "YOUR_AMAP_SECRET"              # 安全密钥


@dataclass
class UnsplashConfig:
    """Unsplash 图片 API (免费 50次/小时) — 中国内容覆盖面差"""
    access_key: str = ""

# ← FIX: 新增 LLMConfig 类，承载 --direct 模式所需的连接配置
@dataclass
class LLMConfig:
    """LLM 直连模式配置 (用于 --direct 模式)"""
    base_url: str = "http://127.0.0.1:15721/v1"
    api_key: str = "sk-no-key-needed"
    model: str = "deepseek-v4-flash"
    temperature: float = 0.5
    max_tokens: int = 8192
@dataclass
class ImageConfig:
    """图片策略"""
    # 本地图片目录（优先级最高）
    # 结构: {local_photo_dir}/{城市名}/{景点名}.jpg
    local_photo_dir: str = ""

    # 在线图片源 (优先级: 本地 > 百度 > Picsum)
    use_baidu_search: bool = False  # 百度图片搜索 (需付费 API)

    @property
    def is_ready(self) -> bool:
        return bool(self.local_photo_dir)


@dataclass
class Config:
    use_dify: bool = True
    dify: DifyConfig = field(default_factory=DifyConfig)
    amap: AmapConfig = field(default_factory=AmapConfig)
    unsplash: UnsplashConfig = field(default_factory=UnsplashConfig)
    # llm: LLMConfig = field(default_factory=LLMConfig)  # ← FIX: 新增字段
    image: ImageConfig = field(default_factory=ImageConfig)  # ← FIX: 新增字段
    output_dir: str = ""  # ← FIX: 新增字段
    obsidian_kb_dir: str = r"G:\AI_agent_space\AI-Agent-Space\_知识库\旅游数据"

    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "output")

    @classmethod
    def from_env(cls) -> "Config":
        return Config()


default_config = Config()

# ─── 启动时校验 ───
if default_config.amap.secret:
    print(f"[Amap] Security key loaded: ***{default_config.amap.secret[-4:]}")
else:
    print("[Amap] WARNING: security key not set, map will not work")
if default_config.amap.route_key:
    print(f"[Amap] JS API Key loaded: {default_config.amap.route_key[:6]}...{default_config.amap.route_key[-4:]}")
if default_config.amap.weather_key:
    print(f"[Amap] Weather Key loaded: {default_config.amap.weather_key[:6]}...{default_config.amap.weather_key[-4:]}")
