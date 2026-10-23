"""Local model-profile metadata with OS keyring backed credentials.

Only non-secret profile fields are written to the JSON file. API keys stay in
the OS credential store or in process memory for explicitly session-only profiles.
"""

import json
import os
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from config import ModelConfig


class ProfileStoreError(RuntimeError):
    """Base error for profile storage operations."""


class ProfileNotFoundError(ProfileStoreError):
    pass


class CredentialStoreUnavailableError(ProfileStoreError):
    pass


class ProfileCredentialMissingError(ProfileStoreError):
    pass


class ProfileCredentialStore:
    """Small credential-store adapter around the user's OS keyring."""

    SERVICE_NAME = "shanhe-travel.model-profiles"

    def __init__(self):
        self._keyring = None
        self._available = False
        try:
            import keyring

            backend = keyring.get_keyring()
            self._keyring = keyring
            self._available = bool(backend.priority > 0)
        except Exception:
            # Unsupported desktop/session backends must not prevent the app starting.
            self._keyring = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def get(self, profile_id: str) -> str | None:
        if not self.available or self._keyring is None:
            raise CredentialStoreUnavailableError("系统凭据库不可用")
        try:
            return self._keyring.get_password(self.SERVICE_NAME, profile_id)
        except Exception:
            self._available = False
            raise CredentialStoreUnavailableError("读取系统凭据失败") from None

    def set(self, profile_id: str, secret: str) -> None:
        if not self.available or self._keyring is None:
            raise CredentialStoreUnavailableError("系统凭据库不可用")
        try:
            self._keyring.set_password(self.SERVICE_NAME, profile_id, secret)
        except Exception:
            self._available = False
            raise CredentialStoreUnavailableError("保存到系统凭据库失败") from None

    def delete(self, profile_id: str) -> None:
        if not self.available or self._keyring is None:
            raise CredentialStoreUnavailableError("系统凭据库不可用")
        try:
            if self._keyring.get_password(self.SERVICE_NAME, profile_id) is not None:
                self._keyring.delete_password(self.SERVICE_NAME, profile_id)
        except Exception:
            self._available = False
            raise CredentialStoreUnavailableError("从系统凭据库删除失败") from None


def _credential_target(base_url: str) -> tuple[str, str, int | None]:
    """Return the URL origin; path edits may keep a credential, origin edits may not."""
    parts = urlsplit(base_url)
    return parts.scheme.lower(), (parts.hostname or "").lower(), parts.port


class ProfilePayload(BaseModel):
    """Write-only profile fields accepted from the local settings form."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    base_url: str = "http://127.0.0.1:15721/v1"
    model: str = "deepseek-v4-flash"
    temperature: float | None = Field(default=0.5, ge=0.0, le=2.0)
    timeout: float = Field(default=60.0, gt=0.0, le=300.0)
    max_retries: int = Field(default=1, ge=0, le=5)
    max_tokens: int = Field(default=8192, ge=1, le=131072)
    provider: Literal["custom", "deepseek", "qwen", "glm", "moonshot", "doubao", "anthropic", "gemini"] = "custom"
    protocol: Literal["openai_compatible", "anthropic", "google_genai"] = "openai_compatible"
    structured_output_method: Literal["function_calling", "json_schema", "json_mode", "strict_json_text"] = "function_calling"
    api_key: SecretStr = Field(default=SecretStr(""), repr=False, exclude=True)
    session_only: bool = False
    make_default: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("配置名称不能为空")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return ModelConfig(base_url=value).base_url

    def to_model_config(self, profile_id: str, api_key: str | None = None) -> ModelConfig:
        secret = self.api_key.get_secret_value() if api_key is None else api_key
        return ModelConfig(
            profile_id=profile_id,
            provider=self.provider,
            protocol=self.protocol,
            base_url=self.base_url,
            api_key=secret or "sk-no-key-needed",
            model=self.model,
            temperature=self.temperature,
            timeout=self.timeout,
            max_retries=self.max_retries,
            max_tokens=self.max_tokens,
            structured_output_method=self.structured_output_method,
        )


class ProfileRecord(BaseModel):
    """Persisted, non-secret profile metadata."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str
    name: str
    base_url: str
    model: str
    temperature: float | None = 0.5
    timeout: float
    max_retries: int
    max_tokens: int
    provider: Literal["custom", "deepseek", "qwen", "glm", "moonshot", "doubao", "anthropic", "gemini"] = "custom"
    protocol: Literal["openai_compatible", "anthropic", "google_genai"] = "openai_compatible"
    structured_output_method: Literal["function_calling", "json_schema", "json_mode", "strict_json_text"] = "function_calling"
    has_saved_key: bool = False
    session_only: bool = False

    def to_model_config(self, api_key: str | None = None) -> ModelConfig:
        return ModelConfig(
            profile_id=self.profile_id,
            provider=self.provider,
            protocol=self.protocol,
            base_url=self.base_url,
            api_key=api_key or "sk-no-key-needed",
            model=self.model,
            temperature=self.temperature,
            timeout=self.timeout,
            max_retries=self.max_retries,
            max_tokens=self.max_tokens,
            structured_output_method=self.structured_output_method,
        )


def app_data_dir() -> Path:
    """Return the per-user application data directory without creating it."""
    if os.name == "nt":
        root = Path(os.environ.get("SHANHE_TRAVEL_DATA_DIR") or os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        if os.environ.get("SHANHE_TRAVEL_DATA_DIR"):
            return root
        return root / "ShanheTravel"
    if sys_platform() == "darwin":
        if os.environ.get("SHANHE_TRAVEL_DATA_DIR"):
            return Path(os.environ["SHANHE_TRAVEL_DATA_DIR"])
        return Path.home() / "Library" / "Application Support" / "ShanheTravel"
    if os.environ.get("SHANHE_TRAVEL_DATA_DIR"):
        return Path(os.environ["SHANHE_TRAVEL_DATA_DIR"])
    root = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return root / "shanhe-travel"


def sys_platform() -> str:
    # Kept tiny to make the platform path easy to replace in tests.
    import sys
    return sys.platform


class ModelProfileStore:
    """Atomic local profile registry backed by a credential-store adapter."""

    FILE_NAME = "model-profiles.json"

    def __init__(self, path: str | Path | None = None, credentials=None):
        self.path = Path(path) if path is not None else app_data_dir() / self.FILE_NAME
        self.credentials = credentials if credentials is not None else ProfileCredentialStore()
        self._lock = threading.RLock()
        self._profiles: dict[str, ProfileRecord] = {}
        self._default_profile_id: str | None = None
        self._session_profiles: dict[str, ProfileRecord] = {}
        self._session_secrets: dict[str, str] = {}
        self._session_default_profile_id: str | None = None
        self._load_error: str | None = None
        self._load()

    @property
    def credential_store_available(self) -> bool:
        return bool(getattr(self.credentials, "available", False))

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if raw.get("version") != 1 or not isinstance(raw.get("profiles"), list):
                raise ValueError("unsupported profile file")
            profiles = [ProfileRecord.model_validate(row) for row in raw["profiles"]]
            self._profiles = {item.profile_id: item for item in profiles}
            default_id = raw.get("default_profile_id")
            self._default_profile_id = default_id if default_id in self._profiles else None
        except Exception:
            # Keep settings accessible; operations report the corruption and never
            # overwrite the unreadable file implicitly.
            self._load_error = "本地模型配置文件无法读取，请先备份后修复或移走该文件"

    def _ensure_loaded(self) -> None:
        if self._load_error:
            raise ProfileStoreError(self._load_error)

    def _persist(self, profiles: dict[str, ProfileRecord], default_profile_id: str | None) -> None:
        self._ensure_loaded()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = {
            "version": 1,
            "default_profile_id": default_profile_id,
            "profiles": [profile.model_dump() for profile in profiles.values()],
        }
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=self.path.name + ".", suffix=".tmp", delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(content, temp_file, ensure_ascii=False, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, self.path)
        except Exception:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise ProfileStoreError("本地模型配置保存失败") from None

    def default_profile_id(self) -> str | None:
        with self._lock:
            self._ensure_loaded()
            if self._session_default_profile_id in self._session_profiles:
                return self._session_default_profile_id
            return self._default_profile_id

    def set_default(self, profile_id: str | None) -> str | None:
        with self._lock:
            self._ensure_loaded()
            if profile_id is None:
                self._persist(self._profiles, None)
                self._default_profile_id = None
                self._session_default_profile_id = None
                return None
            if profile_id in self._session_profiles:
                self._session_default_profile_id = profile_id
                return profile_id
            if profile_id not in self._profiles:
                raise ProfileNotFoundError("模型配置不存在")
            self._persist(self._profiles, profile_id)
            self._default_profile_id = profile_id
            self._session_default_profile_id = None
            return profile_id

    def _record_from_payload(self, profile_id: str, payload: ProfilePayload,
                             has_saved_key: bool, session_only: bool) -> ProfileRecord:
        config = payload.to_model_config(profile_id)
        return ProfileRecord(
            profile_id=profile_id,
            provider=payload.provider,
            protocol=payload.protocol,
            name=payload.name,
            base_url=config.base_url,
            model=config.model,
            temperature=config.temperature,
            timeout=config.timeout,
            max_retries=config.max_retries,
            max_tokens=config.max_tokens,
            structured_output_method=config.structured_output_method,
            has_saved_key=has_saved_key,
            session_only=session_only,
        )

    def create(self, payload: ProfilePayload) -> dict:
        with self._lock:
            self._ensure_loaded()
            profile_id = uuid.uuid4().hex
            secret = payload.api_key.get_secret_value()
            session_only = payload.session_only
            record = self._record_from_payload(
                profile_id, payload, has_saved_key=bool(secret) and not session_only,
                session_only=session_only,
            )

            if session_only:
                self._session_profiles[profile_id] = record
                if secret:
                    self._session_secrets[profile_id] = secret
                if payload.make_default:
                    self._session_default_profile_id = profile_id
                return self._public_record(record)

            if secret:
                if not self.credential_store_available:
                    raise CredentialStoreUnavailableError(
                        "系统凭据库不可用；请明确选择‘仅本次运行使用’"
                    )
                self.credentials.set(profile_id, secret)

            profiles = dict(self._profiles)
            profiles[profile_id] = record
            default_id = profile_id if payload.make_default else self._default_profile_id
            try:
                self._persist(profiles, default_id)
            except ProfileStoreError:
                if secret:
                    try:
                        self.credentials.delete(profile_id)
                    except ProfileStoreError:
                        raise ProfileStoreError("配置保存失败，凭据清理失败，请重新检查凭据状态") from None
                raise
            self._profiles = profiles
            if payload.make_default:
                self._default_profile_id = profile_id
                self._session_default_profile_id = None
            return self._public_record(record)

    def update(self, profile_id: str, payload: ProfilePayload) -> dict:
        with self._lock:
            self._ensure_loaded()
            old = self._session_profiles.get(profile_id) or self._profiles.get(profile_id)
            if old is None:
                raise ProfileNotFoundError("模型配置不存在")
            if old.session_only != payload.session_only:
                raise ProfileStoreError("配置的保存方式不能直接切换，请新建配置")

            submitted_secret = payload.api_key.get_secret_value()
            url_changed = _credential_target(old.base_url) != _credential_target(payload.base_url)
            provider_changed = old.provider != payload.provider or old.protocol != payload.protocol
            if old.session_only:
                old_secret = self._session_secrets.get(profile_id, "")
                if (old_secret and (provider_changed or url_changed) and not submitted_secret):
                    raise ProfileStoreError("服务商、协议或接口主机变更后，请重新填写 API Key；也可先单独清除旧密钥")
                secret = submitted_secret or self._session_secrets.get(profile_id, "")
                record = self._record_from_payload(profile_id, payload, False, True)
                self._session_profiles[profile_id] = record
                if submitted_secret:
                    self._session_secrets[profile_id] = submitted_secret
                if payload.make_default:
                    self._session_default_profile_id = profile_id
                return self._public_record(record)

            old_secret = None
            if old.has_saved_key and (provider_changed or url_changed) and not submitted_secret:
                raise ProfileStoreError("服务商、协议或接口主机变更后，请重新填写 API Key；也可先单独清除旧密钥")
            if submitted_secret and old.has_saved_key:
                if not self.credential_store_available:
                    raise CredentialStoreUnavailableError("系统凭据库不可用，暂时无法更新已保存凭证")
                old_secret = self.credentials.get(profile_id)

            has_saved_key = bool(submitted_secret) or old.has_saved_key
            record = self._record_from_payload(profile_id, payload, has_saved_key, False)
            profiles = dict(self._profiles)
            profiles[profile_id] = record
            default_id = profile_id if payload.make_default else self._default_profile_id

            if submitted_secret:
                if not self.credential_store_available:
                    raise CredentialStoreUnavailableError(
                        "系统凭据库不可用；请明确选择‘仅本次运行使用’"
                    )
                self.credentials.set(profile_id, submitted_secret)
            try:
                self._persist(profiles, default_id)
            except ProfileStoreError:
                if submitted_secret:
                    try:
                        if old_secret is None:
                            self.credentials.delete(profile_id)
                        else:
                            self.credentials.set(profile_id, old_secret)
                    except ProfileStoreError:
                        raise ProfileStoreError("配置保存失败，凭据回滚也失败，请重新检查凭据状态") from None
                raise

            self._profiles = profiles
            if payload.make_default:
                self._default_profile_id = profile_id
                self._session_default_profile_id = None
            return self._public_record(record)

    def clear_credential(self, profile_id: str) -> dict:
        with self._lock:
            self._ensure_loaded()
            session_record = self._session_profiles.get(profile_id)
            if session_record is not None:
                self._session_secrets.pop(profile_id, None)
                updated = session_record.model_copy(update={"has_saved_key": False})
                self._session_profiles[profile_id] = updated
                return self._public_record(updated)

            old = self._profiles.get(profile_id)
            if old is None:
                raise ProfileNotFoundError("模型配置不存在")
            if not old.has_saved_key:
                return self._public_record(old)
            if not self.credential_store_available:
                raise CredentialStoreUnavailableError("系统凭据库不可用，无法确认凭证删除状态")

            old_secret = self.credentials.get(profile_id)
            if old_secret:
                self.credentials.delete(profile_id)
            updated = old.model_copy(update={"has_saved_key": False})
            profiles = dict(self._profiles)
            profiles[profile_id] = updated
            try:
                self._persist(profiles, self._default_profile_id)
            except ProfileStoreError:
                if old_secret:
                    try:
                        self.credentials.set(profile_id, old_secret)
                    except ProfileStoreError:
                        raise ProfileStoreError("凭证删除已执行，但本地状态回写失败且凭据恢复失败") from None
                raise
            self._profiles = profiles
            return self._public_record(updated)

    def delete(self, profile_id: str) -> None:
        with self._lock:
            self._ensure_loaded()
            if profile_id in self._session_profiles:
                self._session_profiles.pop(profile_id, None)
                self._session_secrets.pop(profile_id, None)
                if self._session_default_profile_id == profile_id:
                    self._session_default_profile_id = None
                return

            old = self._profiles.get(profile_id)
            if old is None:
                raise ProfileNotFoundError("模型配置不存在")
            old_secret = None
            if old.has_saved_key:
                if not self.credential_store_available:
                    raise CredentialStoreUnavailableError("系统凭据库不可用，暂时无法一致地删除配置")
                old_secret = self.credentials.get(profile_id)
                if old_secret:
                    self.credentials.delete(profile_id)

            profiles = dict(self._profiles)
            del profiles[profile_id]
            default_id = None if self._default_profile_id == profile_id else self._default_profile_id
            try:
                self._persist(profiles, default_id)
            except ProfileStoreError:
                if old_secret:
                    try:
                        self.credentials.set(profile_id, old_secret)
                    except ProfileStoreError:
                        raise ProfileStoreError("配置删除未完成，且凭据恢复失败；请重新检查配置状态") from None
                raise
            self._profiles = profiles
            self._default_profile_id = default_id

    def resolve_model_config(self, profile_id: str) -> ModelConfig:
        with self._lock:
            self._ensure_loaded()
            record = self._session_profiles.get(profile_id) or self._profiles.get(profile_id)
            if record is None:
                raise ProfileNotFoundError("模型配置不存在或仅本次会话的配置已失效")

            if record.session_only:
                secret = self._session_secrets.get(profile_id)
            elif record.has_saved_key:
                if not self.credential_store_available:
                    raise CredentialStoreUnavailableError("系统凭据库不可用，无法读取该配置的密钥")
                secret = self.credentials.get(profile_id)
                if not secret:
                    raise ProfileCredentialMissingError("该配置的系统凭据不存在，请重新填写密钥")
            else:
                secret = None
            return record.to_model_config(secret)

    def list_profiles(self) -> list[dict]:
        with self._lock:
            self._ensure_loaded()
            default_id = self.default_profile_id()
            records = list(self._profiles.values()) + list(self._session_profiles.values())
            return [self._public_record(record, default_id=default_id) for record in records]

    def _public_record(self, record: ProfileRecord, default_id: str | None = None) -> dict:
        if default_id is None:
            default_id = self.default_profile_id()
        if record.session_only:
            has_key = bool(self._session_secrets.get(record.profile_id))
        elif record.has_saved_key and self.credential_store_available:
            try:
                has_key = bool(self.credentials.get(record.profile_id))
            except ProfileStoreError:
                has_key = False
        else:
            has_key = False
        return {
            "profile_id": record.profile_id,
            "name": record.name,
            "base_url": record.base_url,
            "model": record.model,
            "provider": record.provider,
            "protocol": record.protocol,
            "temperature": record.temperature,
            "timeout": record.timeout,
            "max_retries": record.max_retries,
            "max_tokens": record.max_tokens,
            "structured_output_method": record.structured_output_method,
            "has_key": has_key,
            "session_only": record.session_only,
            "is_default": record.profile_id == default_id,
        }
