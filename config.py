"""
山河游记 · 配置文件

优先级: 环境变量 > 项目根目录 .env 文件 > 代码内默认值
把 .env.example 复制为 .env 并填入真实 Key 即可，不要把真实 Key 提交到仓库。
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    """轻量 .env 加载器: 只认识 KEY=VALUE 和 # 注释，已存在的环境变量不覆盖"""
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _is_placeholder(v: str) -> bool:
    return (not v) or v.startswith("YOUR_") or v.startswith("app-YOUR_")


@dataclass
class DifyConfig:
    base_url: str = field(default_factory=lambda: _env("DIFY_BASE_URL", "http://192.168.0.11/v1"))
    intent_key: str = field(default_factory=lambda: _env("DIFY_INTENT_KEY", ""))
    route_key: str = field(default_factory=lambda: _env("DIFY_ROUTE_KEY", ""))
    content_key: str = field(default_factory=lambda: _env("DIFY_CONTENT_KEY", ""))
    temperature: float = 0.5

    def get_key(self, workflow: str) -> str:
        return {"intent": self.intent_key, "route": self.route_key, "content": self.content_key}[workflow]


@dataclass
class AmapConfig:
    """高德地图 API 配置"""
    weather_key: str = field(default_factory=lambda: _env("AMAP_WEATHER_KEY", ""))  # Web服务 Key (天气/POI搜索/静态地图)
    route_key: str = field(default_factory=lambda: _env("AMAP_JS_API_KEY", ""))     # Web端 JS API Key (前端地图)
    secret: str = field(default_factory=lambda: _env("AMAP_SECRET", ""))            # 安全密钥


@dataclass
class LLMConfig:
    """LLM 直连模式配置 (用于 --direct 模式)"""
    base_url: str = field(default_factory=lambda: _env("TRAVEL_LLM_URL", "http://127.0.0.1:15721/v1"))
    api_key: str = field(default_factory=lambda: _env("TRAVEL_LLM_KEY", "sk-no-key-needed"))
    model: str = field(default_factory=lambda: _env("TRAVEL_LLM_MODEL", "deepseek-v4-flash"))
    temperature: float = 0.5
    max_tokens: int = 8192


@dataclass
class ImageConfig:
    """图片富化策略 (tools/enrich.py)"""
    # Wikimedia Commons 兜底图源: 知名景点覆盖好但大陆访问不稳定，默认关闭
    use_wikimedia: bool = False


@dataclass
class Config:
    use_dify: bool = True
    dify: DifyConfig = field(default_factory=DifyConfig)
    amap: AmapConfig = field(default_factory=AmapConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    output_dir: str = ""
    # Obsidian 知识库目录，留空则跳过保存
    obsidian_kb_dir: str = field(default_factory=lambda: _env("OBSIDIAN_KB_DIR", ""))

    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "output")

    @classmethod
    def from_env(cls) -> "Config":
        return cls()


default_config = Config()

# ─── 启动时校验 ───
if default_config.amap.weather_key:
    print(f"[Amap] Web服务 Key loaded: ***{default_config.amap.weather_key[-4:]} (天气/POI/静态地图)")
else:
    print("[Amap] WARNING: AMAP_WEATHER_KEY 未配置, 天气/坐标/图片富化不可用")
if default_config.amap.route_key:
    print(f"[Amap] JS API Key loaded: ***{default_config.amap.route_key[-4:]}")
else:
    print("[Amap] WARNING: AMAP_JS_API_KEY 未配置, 前端地图不可用")
if not default_config.amap.secret:
    print("[Amap] WARNING: AMAP_SECRET 未配置, 已配置 Key 的情况下地图可能无法加载")
if default_config.dify.intent_key:
    print("[Dify] workflow keys configured")
else:
    print("[Dify] WARNING: DIFY_*_KEY 未配置, 请复制 .env.example 为 .env 填写")
