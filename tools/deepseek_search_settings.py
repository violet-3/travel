"""Local settings and credential resolution for optional DeepSeek Search/Fetch.

Only non-secret metadata is stored in the application data directory. A
separate Search key lives in the OS credential store or, when explicitly
requested, in memory for the current process. Model-profile credentials are
reused only after the user explicitly selects an eligible official DeepSeek
profile.
"""

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from tools.model_profiles import (
    ModelProfileStore,
    ProfileStoreError,
    app_data_dir,
)

OFFICIAL_BASE_URL = "https://api.deepseek.com"
SEARCH_SCHEMA_VERSION = "deepseek-search-fetch-v1"
_DEFAULT_TIMEOUT = 12.0


class DeepSeekSearchSettingsError(RuntimeError):
    """Safe error for Search/Fetch settings and credentials."""


def _origin(value: str) -> tuple[str, str, int | None]:
    parts = urlsplit(str(value or ""))
    try:
        port = parts.port
    except ValueError:
        return "", "", None
    return parts.scheme.lower(), (parts.hostname or "").lower(), port


def _is_official_profile(profile: dict) -> bool:
    if profile.get("provider") != "deepseek" or profile.get("protocol") != "openai_compatible":
        return False
    scheme, host, port = _origin(profile.get("base_url", ""))
    return scheme == "https" and host == "api.deepseek.com" and port in (None, 443)


def _normalize_base_url(value: str) -> str:
    value = str(value or OFFICIAL_BASE_URL).strip().rstrip("/")
    if not value or any(char.isspace() for char in value):
        raise ValueError("请输入有效的 DeepSeek Search 服务地址")
    try:
        parts = urlsplit(value)
        _ = parts.port
    except ValueError:
        raise ValueError("请输入有效的 DeepSeek Search 服务地址") from None
    if (parts.scheme not in {"https", "http"} or not parts.hostname
            or parts.username or parts.password or parts.query or parts.fragment):
        raise ValueError("服务地址需使用 HTTPS，且不能包含凭据、查询参数或片段")
    if parts.scheme == "http" and parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("联网 Search 服务地址必须使用 HTTPS")
    if len(value) > 512:
        raise ValueError("服务地址过长")
    return value


class DeepSeekSearchSettingsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    auth_mode: Literal["profile", "dedicated"] = "profile"
    profile_id: str | None = Field(default=None, max_length=64)
    base_url: str = OFFICIAL_BASE_URL
    api_key: SecretStr | None = Field(default=None, max_length=2048)
    session_only: bool = False

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if len(value) > 64:
            raise ValueError("配置 ID 无效")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value):
        return _normalize_base_url(value)


@dataclass(frozen=True)
class DeepSeekResearchConfig:
    enabled: bool
    base_url: str
    api_key: str | None = field(default=None, repr=False)
    auth_mode: str = "none"
    profile_id: str | None = None
    availability: str = "disabled"
    timeout: float = _DEFAULT_TIMEOUT
    identity: str = ""

    def with_enabled(self, enabled: bool) -> "DeepSeekResearchConfig":
        values = {
            "enabled": bool(enabled), "base_url": self.base_url,
            "api_key": self.api_key, "auth_mode": self.auth_mode,
            "profile_id": self.profile_id, "availability": self.availability,
            "timeout": self.timeout,
        }
        return _research_config(**values)


def _research_config(**values) -> DeepSeekResearchConfig:
    identity_payload = {
        "schema": SEARCH_SCHEMA_VERSION,
        "enabled": bool(values.get("enabled")),
        "base_url": str(values.get("base_url") or OFFICIAL_BASE_URL),
        "auth_mode": str(values.get("auth_mode") or "none"),
        "profile_id": str(values.get("profile_id") or ""),
        "availability": str(values.get("availability") or "disabled"),
        # One-way identity only; never serialize or log the credential itself.
        "key_digest": hashlib.sha256(str(values.get("api_key") or "").encode("utf-8")).hexdigest()[:24],
    }
    identity = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:32]
    return DeepSeekResearchConfig(identity=identity, **values)


class DeepSeekSearchCredentialStore:
    SERVICE_NAME = "shanhe-travel.deepseek-search"
    CREDENTIAL_NAME = "api_key"

    def __init__(self):
        self._keyring = None
        self._available = False
        try:
            import keyring

            backend = keyring.get_keyring()
            self._keyring = keyring
            self._available = bool(backend.priority > 0)
        except Exception:
            self._keyring = None
            self._available = False

    @property
    def available(self):
        return self._available

    def get(self) -> str | None:
        if not self.available or self._keyring is None:
            raise DeepSeekSearchSettingsError("系统凭据库不可用")
        try:
            return self._keyring.get_password(self.SERVICE_NAME, self.CREDENTIAL_NAME)
        except Exception:
            self._available = False
            raise DeepSeekSearchSettingsError("读取 Search 凭据失败") from None

    def set(self, value: str):
        if not self.available or self._keyring is None:
            raise DeepSeekSearchSettingsError("系统凭据库不可用，请明确选择仅本次运行")
        try:
            self._keyring.set_password(self.SERVICE_NAME, self.CREDENTIAL_NAME, value)
        except Exception:
            self._available = False
            raise DeepSeekSearchSettingsError("保存 Search 凭据失败") from None

    def delete(self):
        if not self.available or self._keyring is None:
            raise DeepSeekSearchSettingsError("系统凭据库不可用，无法清除 Search 凭据")
        try:
            if self._keyring.get_password(self.SERVICE_NAME, self.CREDENTIAL_NAME) is not None:
                self._keyring.delete_password(self.SERVICE_NAME, self.CREDENTIAL_NAME)
        except Exception:
            self._available = False
            raise DeepSeekSearchSettingsError("清除 Search 凭据失败") from None


class DeepSeekSearchSettingsStore:
    FILE_NAME = "deepseek-search-settings.json"

    def __init__(self, path: str | Path | None = None, credentials=None):
        self.path = Path(path) if path is not None else app_data_dir() / self.FILE_NAME
        self.credentials = credentials if credentials is not None else DeepSeekSearchCredentialStore()
        self._lock = threading.RLock()
        self._metadata = {
            "version": 1, "enabled": False, "auth_mode": "profile",
            "profile_id": None, "base_url": OFFICIAL_BASE_URL,
            "has_saved_key": False,
        }
        self._session_key: str | None = None
        self._load_error = False
        self._load()

    @property
    def credential_store_available(self) -> bool:
        return bool(getattr(self.credentials, "available", False))

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if raw.get("version") != 1 or raw.get("auth_mode") not in {"profile", "dedicated"}:
                raise ValueError("unsupported settings")
            self._metadata.update({
                "enabled": bool(raw.get("enabled", False)),
                "auth_mode": raw["auth_mode"],
                "profile_id": raw.get("profile_id") if isinstance(raw.get("profile_id"), str) else None,
                "base_url": _normalize_base_url(raw.get("base_url", OFFICIAL_BASE_URL)),
                "has_saved_key": bool(raw.get("has_saved_key", False)),
            })
        except Exception:
            self._load_error = True

    def _ensure_loaded(self):
        if self._load_error:
            raise DeepSeekSearchSettingsError("本地 Search 配置无法读取，请先备份后修复或移走该文件")

    def _persist(self, metadata: dict):
        self._ensure_loaded()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=self.path.name + ".", suffix=".tmp", delete=False,
            ) as file:
                temp_path = Path(file.name)
                json.dump(metadata, file, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, self.path)
        except Exception:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise DeepSeekSearchSettingsError("本地 Search 配置保存失败") from None

    def _effective_base_url(self) -> str:
        try:
            return _normalize_base_url(
                os.environ.get("DEEPSEEK_SEARCH_BASE_URL") or self._metadata["base_url"]
            )
        except ValueError as exc:
            raise DeepSeekSearchSettingsError(str(exc)) from None

    def _effective_auth_mode(self) -> str:
        mode = os.environ.get("DEEPSEEK_SEARCH_AUTH_MODE", "").strip().lower() or self._metadata["auth_mode"]
        if mode not in {"profile", "dedicated"}:
            raise DeepSeekSearchSettingsError("DEEPSEEK_SEARCH_AUTH_MODE 只能为 profile 或 dedicated")
        return mode

    def _effective_enabled(self, enabled_override: bool | None = None) -> tuple[bool, bool]:
        if enabled_override is not None:
            return bool(enabled_override), False
        value = os.environ.get("DEEPSEEK_SEARCH_ENABLED")
        if value is None or not value.strip():
            return bool(self._metadata["enabled"]), False
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True, True
        if normalized in {"0", "false", "no", "off"}:
            return False, True
        raise DeepSeekSearchSettingsError("DEEPSEEK_SEARCH_ENABLED 需使用 true 或 false")

    def _profiles(self, profile_store: ModelProfileStore) -> list[dict]:
        try:
            return [profile for profile in profile_store.list_profiles() if _is_official_profile(profile)]
        except ProfileStoreError:
            return []

    def public_status(self, profile_store: ModelProfileStore | None = None) -> dict:
        with self._lock:
            self._ensure_loaded()
            base_url = self._effective_base_url()
            env_key = os.environ.get("DEEPSEEK_SEARCH_API_KEY", "").strip()
            auth_mode = self._effective_auth_mode()
            enabled, enabled_env = self._effective_enabled()
            if auth_mode == "profile":
                has_key = False
                if profile_store is not None:
                    has_key = any(
                        p["profile_id"] == self._metadata.get("profile_id") and p.get("has_key")
                        for p in self._profiles(profile_store)
                    )
            else:
                same_origin = _origin(base_url) == _origin(self._metadata["base_url"])
                has_key = bool(env_key or (same_origin and (
                    self._session_key or self._metadata.get("has_saved_key")
                )))
            profiles = self._profiles(profile_store) if profile_store is not None else []
            return {
                "enabled": enabled,
                "enabled_overridden_by_environment": enabled_env,
                "auth_mode": auth_mode,
                "auth_mode_overridden_by_environment": bool(
                    os.environ.get("DEEPSEEK_SEARCH_AUTH_MODE", "").strip()
                ),
                "profile_id": self._metadata.get("profile_id"),
                "base_url": base_url,
                "base_url_overridden_by_environment": bool(os.environ.get("DEEPSEEK_SEARCH_BASE_URL", "").strip()),
                "has_key": has_key,
                "key_overridden_by_environment": bool(env_key),
                "credential_store_available": self.credential_store_available,
                "official_profiles": [
                    {"profile_id": p["profile_id"], "name": p["name"], "has_key": bool(p.get("has_key"))}
                    for p in profiles
                ],
            }

    def save(self, payload: DeepSeekSearchSettingsPayload) -> dict:
        with self._lock:
            self._ensure_loaded()
            key = payload.api_key.get_secret_value().strip() if payload.api_key else ""
            if key and len(key) > 2048:
                raise DeepSeekSearchSettingsError("API Key 长度无效")
            if payload.auth_mode == "profile" and key:
                raise DeepSeekSearchSettingsError("选择模型档案时无需填写独立 Search Key")
            if payload.auth_mode == "profile" and not payload.profile_id:
                if payload.enabled:
                    raise DeepSeekSearchSettingsError("请明确选择一个官方 DeepSeek 模型档案")
            if payload.auth_mode == "dedicated" and payload.enabled and not (
                key or self._session_key or self._metadata.get("has_saved_key")
                or os.environ.get("DEEPSEEK_SEARCH_API_KEY", "").strip()
            ):
                raise DeepSeekSearchSettingsError("请填写独立 Search API Key")
            if payload.auth_mode == "profile" and payload.base_url != OFFICIAL_BASE_URL:
                scheme, host, port = _origin(payload.base_url)
                if scheme != "https" or host != "api.deepseek.com" or port not in (None, 443):
                    raise DeepSeekSearchSettingsError("官方档案只能用于 api.deepseek.com；代理地址请改用独立 Search Key")

            old_url = self._metadata.get("base_url", OFFICIAL_BASE_URL)
            old_origin = _origin(old_url)
            new_origin = _origin(payload.base_url)
            has_existing_dedicated_key = bool(
                self._metadata.get("has_saved_key") or self._session_key
            )
            if (payload.auth_mode == "dedicated" and old_origin != new_origin
                    and has_existing_dedicated_key and not key):
                raise DeepSeekSearchSettingsError("Search 服务主机已变化，请重新填写该主机对应的 API Key")

            old_saved = bool(self._metadata.get("has_saved_key"))
            old_secret = None
            if old_saved:
                if not self.credential_store_available:
                    raise DeepSeekSearchSettingsError("系统凭据库不可用，无法安全切换或保存 Search 配置")
                old_secret = self.credentials.get()

            save_persistent_key = bool(payload.auth_mode == "dedicated" and key and not payload.session_only)
            keep_old_persistent_key = bool(
                payload.auth_mode == "dedicated" and old_saved and not key
                and old_origin == new_origin
            )
            next_meta = {
                "version": 1, "enabled": bool(payload.enabled),
                "auth_mode": payload.auth_mode, "profile_id": payload.profile_id,
                "base_url": payload.base_url,
                "has_saved_key": save_persistent_key or keep_old_persistent_key,
            }
            credential_changed = False
            try:
                if save_persistent_key:
                    if not self.credential_store_available:
                        raise DeepSeekSearchSettingsError("系统凭据库不可用；请明确勾选‘仅本次运行使用’")
                    self.credentials.set(key)
                    credential_changed = True
                elif old_saved and not keep_old_persistent_key:
                    self.credentials.delete()
                    credential_changed = True
                self._persist(next_meta)
            except Exception:
                if credential_changed:
                    try:
                        if old_secret:
                            self.credentials.set(old_secret)
                        else:
                            self.credentials.delete()
                    except Exception:
                        pass
                raise

            if payload.auth_mode == "dedicated":
                if key and payload.session_only:
                    self._session_key = key
                elif save_persistent_key:
                    self._session_key = None
                elif old_origin != new_origin:
                    self._session_key = None
                # Same-origin blank submissions retain the existing in-memory
                # key; secrets are never moved into metadata.
            else:
                self._session_key = None
            self._metadata = next_meta
            return {"saved": True}

    def clear(self) -> dict:
        with self._lock:
            self._ensure_loaded()
            next_meta = {
                "version": 1, "enabled": False, "auth_mode": "profile",
                "profile_id": None, "base_url": OFFICIAL_BASE_URL,
                "has_saved_key": False,
            }
            old_saved = bool(self._metadata.get("has_saved_key"))
            old_secret = None
            if old_saved:
                old_secret = self.credentials.get()
            try:
                if old_saved:
                    self.credentials.delete()
                self._persist(next_meta)
            except Exception:
                if old_saved and old_secret:
                    try:
                        self.credentials.set(old_secret)
                    except Exception:
                        pass
                raise
            self._session_key = None
            self._metadata = next_meta
            return {"cleared": True}

    def resolve(self, profile_store: ModelProfileStore | None = None, enabled_override: bool | None = None) -> DeepSeekResearchConfig:
        with self._lock:
            self._ensure_loaded()
            enabled, _enabled_env = self._effective_enabled(enabled_override)
            base_url = self._effective_base_url()
            mode = self._effective_auth_mode()
            profile_id = self._metadata.get("profile_id")
            if not enabled:
                return _research_config(enabled=False, base_url=base_url, auth_mode=mode,
                                        profile_id=profile_id, availability="disabled")

            secret = None
            availability = "missing_key"
            if mode == "profile":
                if not profile_id or profile_store is None:
                    availability = "profile_unavailable"
                elif _origin(base_url) != ("https", "api.deepseek.com", None) and _origin(base_url) != ("https", "api.deepseek.com", 443):
                    availability = "origin_changed"
                else:
                    profile = next((item for item in self._profiles(profile_store)
                                    if item["profile_id"] == profile_id), None)
                    if not profile or not profile.get("has_key"):
                        availability = "profile_unavailable"
                    else:
                        try:
                            config = profile_store.resolve_model_config(profile_id)
                            secret = config.api_key.get_secret_value()
                            if secret and secret != "sk-no-key-needed":
                                availability = "ready"
                        except (ProfileStoreError, Exception):
                            availability = "profile_unavailable"
            else:
                effective_origin = _origin(base_url)
                configured_origin = _origin(self._metadata["base_url"])
                env_key = os.environ.get("DEEPSEEK_SEARCH_API_KEY", "").strip()
                if effective_origin != configured_origin and not env_key:
                    availability = "origin_changed"
                else:
                    secret = env_key or self._session_key
                    if not secret and self._metadata.get("has_saved_key"):
                        try:
                            secret = self.credentials.get()
                        except DeepSeekSearchSettingsError:
                            secret = None
                    if secret:
                        availability = "ready"

            return _research_config(
                enabled=enabled, base_url=base_url, api_key=secret,
                auth_mode=mode, profile_id=profile_id, availability=availability,
            )
