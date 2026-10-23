"""Independent local settings for AMap browser and Web service credentials.

Only field names are stored in the JSON registry. Values are kept in the OS
credential store, and each generation receives one immutable configuration
snapshot from this store plus environment defaults.
"""

import json
import os
import tempfile
import threading
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from config import AmapConfig
from tools.model_profiles import app_data_dir


class AmapSettingsError(RuntimeError):
    """Safe error for local AMap settings and credential operations."""


class AmapCredentialStore:
    SERVICE_NAME = "shanhe-travel.amap-services"

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
    def available(self) -> bool:
        return self._available

    def get(self, name: str) -> str | None:
        if not self.available or self._keyring is None:
            raise AmapSettingsError("系统凭据库不可用")
        try:
            return self._keyring.get_password(self.SERVICE_NAME, name)
        except Exception:
            self._available = False
            raise AmapSettingsError("读取高德凭据失败") from None

    def set(self, name: str, value: str) -> None:
        if not self.available or self._keyring is None:
            raise AmapSettingsError("系统凭据库不可用")
        try:
            self._keyring.set_password(self.SERVICE_NAME, name, value)
        except Exception:
            self._available = False
            raise AmapSettingsError("保存高德凭据失败") from None

    def delete(self, name: str) -> None:
        if not self.available or self._keyring is None:
            raise AmapSettingsError("系统凭据库不可用")
        try:
            if self._keyring.get_password(self.SERVICE_NAME, name) is not None:
                self._keyring.delete_password(self.SERVICE_NAME, name)
        except Exception:
            self._available = False
            raise AmapSettingsError("删除高德凭据失败") from None


class AmapSettingsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    js_api_key: SecretStr | None = Field(default=None, max_length=512)
    js_security_code: SecretStr | None = Field(default=None, max_length=512)
    web_service_key: SecretStr | None = Field(default=None, max_length=512)
    web_service_secret: SecretStr | None = Field(default=None, max_length=512)


class AmapSettingsStore:
    FILE_NAME = "amap-settings.json"
    FIELDS = {
        "js_api_key": "js_key",
        "js_security_code": "js_security_code",
        "web_service_key": "web_key",
        "web_service_secret": "web_secret",
    }

    def __init__(self, path: str | Path | None = None, credentials=None):
        self.path = Path(path) if path is not None else app_data_dir() / self.FILE_NAME
        self.credentials = credentials if credentials is not None else AmapCredentialStore()
        self._lock = threading.RLock()
        self._saved_fields: set[str] = set()
        self._load_error = False
        self._load()

    @property
    def credential_store_available(self) -> bool:
        return bool(getattr(self.credentials, "available", False))

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if raw.get("version") != 1 or not isinstance(raw.get("saved_fields"), list):
                raise ValueError("unsupported config")
            saved = set(raw["saved_fields"])
            if not saved.issubset(self.FIELDS):
                raise ValueError("unknown fields")
            self._saved_fields = saved
        except Exception:
            self._load_error = True

    def _ensure_loaded(self) -> None:
        if self._load_error:
            raise AmapSettingsError("本地高德服务配置无法读取，请先备份后修复或移走该文件")

    def _persist(self, fields: set[str]) -> None:
        self._ensure_loaded()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=self.path.name + ".", suffix=".tmp", delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump({"version": 1, "saved_fields": sorted(fields)}, temp_file)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, self.path)
        except Exception:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise AmapSettingsError("本地高德服务配置保存失败") from None

    def resolve(self, environment: AmapConfig) -> AmapConfig:
        with self._lock:
            self._ensure_loaded()
            values = {
                "js_key": environment.js_key,
                "js_security_code": environment.js_security_code,
                "web_key": environment.web_key,
                "web_secret": environment.web_secret,
            }
            for field_name in self._saved_fields:
                secret = self.credentials.get(field_name)
                if not secret:
                    raise AmapSettingsError("已保存的高德凭据不可读取，请重新填写或清除本地配置")
                values[self.FIELDS[field_name]] = secret
            return AmapConfig(**values)

    def public_status(self, environment: AmapConfig) -> dict:
        with self._lock:
            self._ensure_loaded()
            config = self.resolve(environment)
            return {
                "credential_store_available": self.credential_store_available,
                "has_js_api_key": bool(config.js_key),
                "has_js_security_code": bool(config.js_security_code),
                "has_web_service_key": bool(config.web_key),
                "has_web_service_secret": bool(config.web_secret),
                "saved_fields": sorted(self._saved_fields),
            }

    def save(self, payload: AmapSettingsPayload) -> dict:
        with self._lock:
            self._ensure_loaded()
            submitted = {
                name: getattr(payload, name).get_secret_value()
                for name in self.FIELDS
                if getattr(payload, name) is not None
                and getattr(payload, name).get_secret_value()
            }
            if submitted and not self.credential_store_available:
                raise AmapSettingsError("系统凭据库不可用，请改用环境变量设置高德服务配置")

            old_submitted_values = {
                name: self.credentials.get(name) if name in self._saved_fields else None
                for name in submitted
            }
            new_fields = set(self._saved_fields)
            attempted = []
            try:
                for name, value in submitted.items():
                    # Include the current key in rollback even if the backend
                    # mutates it before raising an error.
                    attempted.append(name)
                    self.credentials.set(name, value)
                    new_fields.add(name)
                self._persist(new_fields)
            except Exception:
                for name in attempted:
                    try:
                        previous = old_submitted_values.get(name)
                        if previous is None:
                            self.credentials.delete(name)
                        else:
                            self.credentials.set(name, previous)
                    except Exception:
                        pass
                raise
            self._saved_fields = new_fields
            return {"saved": True, "saved_fields": sorted(self._saved_fields)}

    def clear(self) -> dict:
        with self._lock:
            self._ensure_loaded()
            if self._saved_fields and not self.credential_store_available:
                raise AmapSettingsError("系统凭据库不可用，暂时无法清除本地高德配置")
            old_values = {name: self.credentials.get(name) for name in self._saved_fields}
            deleted = []
            try:
                for name in self._saved_fields:
                    self.credentials.delete(name)
                    deleted.append(name)
                self._persist(set())
            except Exception:
                for name in deleted:
                    value = old_values.get(name)
                    if value:
                        try:
                            self.credentials.set(name, value)
                        except Exception:
                            pass
                raise
            self._saved_fields.clear()
            return {"cleared": True}
