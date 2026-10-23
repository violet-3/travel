"""第15轮：相同请求的短时结果缓存。

同一个问题在短时间内重复点生成时，没必要再花一次模型费用：
- key 由规范化后的查询、表单条件、上海日期、模型生成参数及高德配置指纹共同决定
- 只缓存成功生成的完整攻略，不缓存失败、取消或空结果
- 过期文件在被读取或写入时顺手清理
- 命中时由调用方显式标注，绝不静默替换成旧结果

缓存属于本机加速，不是内容核验；命中结果仍保留原始的生成时间。
"""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from models.schemas import TravelGuide
from tools.model_profiles import app_data_dir

CACHE_VERSION = 2
DEFAULT_TTL_SECONDS = 1800
MAX_ENTRIES = 40


def _stable(value):
    """Normalize arbitrary override values into a deterministic structure."""
    if isinstance(value, dict):
        return {str(key): _stable(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_stable(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def build_cache_key(
    query: str, overrides: dict | None, model_config, profile_id: str | None,
    date_context: str | None = None, amap_config=None, research_config=None,
) -> str:
    # AMap credentials can change enrichment results. Store only a one-way
    # fingerprint in the cache key, never the credential values themselves.
    amap_values = [
        str(getattr(amap_config, field, "") or "")
        for field in ("web_key", "web_secret", "js_key", "js_security_code")
    ]
    amap_fingerprint = hashlib.sha256(
        json.dumps(amap_values, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:24]
    payload = {
        "version": CACHE_VERSION,
        "query": " ".join(str(query or "").split()),
        "overrides": _stable(overrides or {}),
        "profile": str(profile_id or ""),
        "date_context": str(date_context or ""),
        "amap_fingerprint": amap_fingerprint,
        # ResearchConfig.identity already contains only a one-way credential
        # digest; enabled state and schema version isolate opt-in results.
        "research_identity": str(getattr(research_config, "identity", "") or ""),
        "model": [
            str(getattr(model_config, "provider", "") or ""),
            str(getattr(model_config, "protocol", "") or ""),
            str(getattr(model_config, "model", "") or ""),
            str(getattr(model_config, "base_url", "") or ""),
            str(getattr(model_config, "structured_output_method", "") or ""),
            getattr(model_config, "temperature", None),
            getattr(model_config, "max_tokens", None),
            getattr(model_config, "timeout", None),
            getattr(model_config, "max_retries", None),
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:40]


class GuideCache:
    """Small atomic on-disk cache for repeated generation requests."""

    def __init__(self, directory: str | Path | None = None, ttl_seconds: int | None = None):
        self.directory = (
            Path(directory) if directory is not None else app_data_dir() / "guide-cache"
        )
        self.ttl_seconds = int(ttl_seconds if ttl_seconds is not None else DEFAULT_TTL_SECONDS)

    def _path(self, key: str) -> Path | None:
        if not isinstance(key, str) or len(key) != 40:
            return None
        if not all(char in "0123456789abcdef" for char in key):
            return None
        return self.directory / f"{key}.json"

    def _is_fresh(self, saved_at: float, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        return 0 <= current - saved_at <= self.ttl_seconds

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        if path is None:
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError):
            self._discard(path)
            return None

        if not isinstance(raw, dict) or raw.get("version") != CACHE_VERSION:
            self._discard(path)
            return None
        try:
            saved_at = float(raw.get("saved_at", 0))
        except (TypeError, ValueError):
            self._discard(path)
            return None
        if not self._is_fresh(saved_at):
            self._discard(path)
            return None
        guide = raw.get("guide")
        if not isinstance(guide, dict) or not guide.get("route"):
            self._discard(path)
            return None
        try:
            TravelGuide.model_validate(guide)
        except Exception:
            # Cache files are disposable input. Invalid/stale serialized guides
            # become misses instead of reaching the API's response boundary.
            self._discard(path)
            return None
        return {
            "guide": guide,
            "cached_at": saved_at,
            "age_seconds": round(time.time() - saved_at),
        }

    def set(self, key: str, guide: dict) -> bool:
        """Write one entry atomically. Returns False instead of raising on I/O errors."""
        path = self._path(key)
        if path is None or not isinstance(guide, dict) or not guide.get("route"):
            return False
        try:
            TravelGuide.model_validate(guide)
        except Exception:
            return False
        temp_path = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.directory,
                prefix=path.name + ".", suffix=".tmp", delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(
                    {"version": CACHE_VERSION, "saved_at": time.time(), "guide": guide},
                    temp_file, ensure_ascii=False,
                )
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, path)
        except (OSError, TypeError, ValueError):
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            return False

        self._prune()
        return True

    def _discard(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def discard(self, key: str) -> None:
        """Remove one known cache entry without raising on storage errors."""
        path = self._path(key)
        if path is not None:
            self._discard(path)

    def _prune(self) -> None:
        """Drop expired entries and keep the cache bounded."""
        try:
            entries = [
                entry for entry in self.directory.iterdir()
                if entry.is_file() and entry.suffix == ".json"
            ]
        except OSError:
            return
        now = time.time()
        alive: list[tuple[float, Path]] = []
        for entry in entries:
            try:
                saved_at = entry.stat().st_mtime
            except OSError:
                continue
            if self._is_fresh(saved_at, now):
                alive.append((saved_at, entry))
            else:
                self._discard(entry)

        alive.sort(reverse=True)
        for _, entry in alive[MAX_ENTRIES:]:
            self._discard(entry)

    def clear(self) -> int:
        try:
            entries = [
                entry for entry in self.directory.iterdir()
                if entry.is_file() and entry.suffix == ".json"
            ]
        except OSError:
            return 0
        removed = 0
        for entry in entries:
            try:
                entry.unlink()
                removed += 1
            except OSError:
                continue
        return removed

    def status(self) -> dict:
        try:
            entries = [
                entry for entry in self.directory.iterdir()
                if entry.is_file() and entry.suffix == ".json"
            ]
        except OSError:
            entries = []
        now = time.time()
        fresh = 0
        for entry in entries:
            try:
                if self._is_fresh(entry.stat().st_mtime, now):
                    fresh += 1
            except OSError:
                continue
        return {"entries": len(entries), "fresh": fresh, "ttl_seconds": self.ttl_seconds}
