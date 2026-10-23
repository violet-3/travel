"""
山河游记 · 配置文件

优先级: 环境变量 > 项目根目录 .env 文件 > 代码内默认值
把 .env.example 复制为 .env 并填入真实 Key 即可，不要把真实 Key 提交到仓库。
"""

import os
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator


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


@dataclass(frozen=True)
class AmapConfig:
    """独立的高德 Web 服务与浏览器 SDK 配置。"""

    web_key: str = field(
        default_factory=lambda: _env("AMAP_WEB_SERVICE_KEY", _env("AMAP_WEATHER_KEY", "")),
        repr=False,
    )
    web_secret: str = field(
        default_factory=lambda: _env("AMAP_WEB_SERVICE_SECRET", _env("AMAP_REST_SECRET", "")),
        repr=False,
    )
    js_key: str = field(default_factory=lambda: _env("AMAP_JS_API_KEY", ""), repr=False)
    js_security_code: str = field(default_factory=lambda: _env("AMAP_JS_SECURITY_CODE", ""), repr=False)

    # Keep old internal names available for older callers during migration.
    @property
    def weather_key(self) -> str:
        return self.web_key

    @property
    def route_key(self) -> str:
        return self.js_key

    @property
    def secret(self) -> str:
        return self.web_secret


class ModelConfigError(ValueError):
    """Safe, user-facing model configuration error without secret values."""


class ModelProfileNotFoundError(ValueError):
    """A named model profile was requested before profile storage is available."""


class ModelConfig(BaseModel):
    """Validated immutable snapshot for one model-generation request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str | None = None
    base_url: str = "http://127.0.0.1:15721/v1"
    api_key: SecretStr = Field(default=SecretStr("sk-no-key-needed"), repr=False, exclude=True)
    model: str = "deepseek-v4-flash"
    temperature: float | None = Field(default=0.5, ge=0.0, le=2.0)
    timeout: float = Field(default=60.0, gt=0.0, le=300.0)
    max_retries: int = Field(default=1, ge=0, le=5)
    max_tokens: int = Field(default=8192, ge=1, le=131072)
    provider: Literal["custom", "deepseek", "qwen", "glm", "moonshot", "doubao", "anthropic", "gemini"] = "custom"
    protocol: Literal["openai_compatible", "anthropic", "google_genai"] = "openai_compatible"
    structured_output_method: Literal["function_calling", "json_schema", "json_mode", "strict_json_text"] = "function_calling"

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ch.isspace() for ch in value):
            raise ValueError("must be a valid HTTP(S) base URL")
        try:
            parts = urlsplit(value)
            _ = parts.port  # Force validation of malformed ports.
        except ValueError as exc:
            raise ValueError("must be a valid HTTP(S) base URL") from exc
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment):
            raise ValueError("must use HTTP(S), a hostname, and no URL credentials/query/fragment")
        return value.rstrip("/")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 256:
            raise ValueError("must be a non-empty model name of at most 256 characters")
        return value

    @field_validator("timeout")
    @classmethod
    def validate_finite_timeout(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("must be finite")
        return value

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value or len(value) > 128:
            raise ValueError("must contain 1 to 128 non-space characters")
        return value

    @classmethod
    def from_env(cls) -> "ModelConfig":
        """Read the legacy TRAVEL_LLM_* variables into a fresh immutable snapshot."""
        try:
            raw = {
                "base_url": _env("TRAVEL_LLM_URL", "http://127.0.0.1:15721/v1"),
                "api_key": _env("TRAVEL_LLM_KEY", "sk-no-key-needed"),
                "model": _env("TRAVEL_LLM_MODEL", "deepseek-v4-flash"),
                "temperature": (float(_env("TRAVEL_LLM_TEMPERATURE", "0.5"))
                                if _env("TRAVEL_LLM_TEMPERATURE", "0.5").strip().lower() not in {"", "auto", "none"}
                                else None),
                "timeout": float(_env("TRAVEL_LLM_TIMEOUT", "60")),
                "max_retries": int(_env("TRAVEL_LLM_MAX_RETRIES", "1")),
                "max_tokens": int(_env("TRAVEL_LLM_MAX_TOKENS", "8192")),
                "provider": _env("TRAVEL_LLM_PROVIDER", "custom"),
                "protocol": _env("TRAVEL_LLM_PROTOCOL", "openai_compatible"),
                "structured_output_method": _env(
                    "TRAVEL_LLM_STRUCTURED_OUTPUT_METHOD", "function_calling"),
            }
            return cls.model_validate(raw)
        except (ValueError, ValidationError) as exc:
            if isinstance(exc, ValidationError):
                fields = ", ".join(sorted({str(err["loc"][0]) for err in exc.errors()}))
                raise ModelConfigError(f"模型配置无效，请检查字段：{fields}") from None
            raise ModelConfigError("模型配置中的数值字段格式无效") from None


# Keep the former public name available while callers migrate to ModelConfig.
LLMConfig = ModelConfig


def resolve_model_config(profile_id: str | None = None, profile_store=None) -> ModelConfig:
    """Resolve one request snapshot from a named/default profile or legacy env."""
    if profile_store is not None:
        selected_id = profile_id or profile_store.default_profile_id()
        if selected_id is not None:
            try:
                return profile_store.resolve_model_config(selected_id)
            except Exception as exc:
                # Keep the storage layer optional for CLI and legacy callers,
                # while preserving a safe message for the Web boundary.
                from tools.model_profiles import ProfileStoreError
                if isinstance(exc, ProfileStoreError):
                    raise ModelProfileNotFoundError(str(exc)) from None
                raise
    if profile_id is not None:
        raise ModelProfileNotFoundError("命名模型配置不可用")
    return ModelConfig.from_env()


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
if default_config.amap.web_key:
    print("[Amap] Web 服务 Key 已配置（天气/POI/静态地图）")
else:
    print("[Amap] WARNING: AMAP_WEB_SERVICE_KEY 未配置, 天气/坐标/图片富化不可用")
if default_config.amap.js_key:
    print("[Amap] JS API Key 已配置")
else:
    print("[Amap] WARNING: AMAP_JS_API_KEY 未配置, 前端地图不可用")
if default_config.amap.web_key and not default_config.amap.web_secret:
    print("[Amap] WARNING: AMAP_WEB_SERVICE_SECRET 未配置，Web 服务签名不会启用")
if default_config.amap.js_key and not default_config.amap.js_security_code:
    print("[Amap] WARNING: AMAP_JS_SECURITY_CODE 未配置，JS 安全码未设置")
