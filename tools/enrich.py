"""
生成时富化层 · POI 坐标 + 真实图片

对攻略里的每个景点/美食店补全两样东西:
  1. 真实坐标 —— 高德 v5 POI 搜索，前端"一键导航"的精确终点
  2. 图片 —— 有来源标注的多层降级，远端结果按 TTL 缓存并允许到期重试:
       本地缓存 static/photos/{城市}/{名称}.jpg
       > 高德 POI 实拍图 (v5 搜索 show_fields=photos)
       > Wikimedia Commons (可选, config.image.use_wikimedia, 大陆访问不稳定)
       > 高德静态地图 (需要有效坐标、服务配置与接口可用)
       > 留空 —— 前端降级为占位图

坐标与图片的命中结果记录在 static/photos/_index.json，
新鲜缓存可减少重复请求；文件损坏、记录过期或临时获取失败时会再次尝试。
"""

import asyncio
import hashlib
import io
import json
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import httpx
from PIL import Image

from config import AmapConfig, default_config
from tools.amap_utils import with_sig

PHOTO_DIR = Path(__file__).parent.parent / "static" / "photos"
INDEX_FILE = PHOTO_DIR / "_index.json"

_CONCURRENCY = 6          # 并发请求上限，避免触发高德 QPS 限制
_sem = asyncio.Semaphore(_CONCURRENCY)
_INDEX_LOCK = threading.RLock()
_CACHE_TTL = timedelta(days=30)
_CACHE_VERSION = "v4"
_MAX_IMAGE_BYTES = 12 * 1024 * 1024

_LOCAL_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


# ────────────────────────── 本地缓存 ──────────────────────────

def _safe_component(value: str) -> str:
    """Make a deterministic, collision-resistant single filesystem component."""
    raw = str(value or "")
    slug = re.sub(r"[^\w-]+", "-", raw, flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-._ ")[:42] or "item"
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"{slug}-{digest}"


def _legacy_safe_component(value: str) -> str:
    """Read-only compatibility path for old cache files; never used for writes."""
    text = re.sub(r'[\\/:*?"<>|#\s]', "", str(value or ""))
    text = text.strip(" .")[:60]
    return text if text not in {"", ".", ".."} else "_misc"


def _asset_path(city: str, name: str, ext: str = ".jpg", legacy: bool = False) -> Path:
    if ext.lower() not in _LOCAL_EXTS:
        raise ValueError("unsupported image extension")
    root = PHOTO_DIR.resolve()
    city_part = _legacy_safe_component(city) if legacy else _safe_component(city or "_misc")
    name_part = _legacy_safe_component(name) if legacy else _safe_component(name)
    candidate = (root / city_part / (name_part + ext.lower())).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise ValueError("photo cache path escapes its root") from None
    return candidate


def _photo_url(city: str, name: str, ext: str = ".jpg", legacy: bool = False) -> str:
    path = _asset_path(city, name, ext, legacy=legacy)
    relative = path.relative_to(PHOTO_DIR.resolve())
    return "/static/photos/" + "/".join(quote(part, safe="-_.") for part in relative.parts)


def _path_from_photo_url(value: str) -> Path | None:
    prefix = "/static/photos/"
    if not isinstance(value, str) or not value.startswith(prefix):
        return None
    parts = tuple(unquote(part) for part in value[len(prefix):].split("/"))
    if len(parts) != 2 or Path(parts[1]).suffix.lower() not in _LOCAL_EXTS:
        return None
    root = PHOTO_DIR.resolve()
    candidate = (root / parts[0] / parts[1]).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _valid_image_bytes(content: bytes) -> bool:
    if not isinstance(content, bytes) or len(content) < 24 or len(content) > _MAX_IMAGE_BYTES:
        return False
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                return False
            width, height = image.size
            if width < 1 or height < 1 or width > 16384 or height > 16384 or width * height > 40_000_000:
                return False
            image.verify()
        # `verify()` checks container structure; loading a second instance also
        # forces decoders to validate image data instead of accepting a header.
        with Image.open(io.BytesIO(content)) as image:
            image.load()
        return True
    except Exception:
        return False


def _valid_image_file(path: Path) -> bool:
    try:
        stat = path.stat()
        if stat.st_size > _MAX_IMAGE_BYTES:
            return False
        return _valid_image_bytes(path.read_bytes())
    except OSError:
        return False


def _local_photo(city: str, fname: str) -> str | None:
    """Return a valid cached file path; corrupt and tiny placeholders are misses."""
    for ext in _LOCAL_EXTS:
        for legacy in (False, True):
            try:
                candidate = _asset_path(city, fname, ext, legacy=legacy)
            except (OSError, ValueError):
                continue
            if candidate.is_file() and _valid_image_file(candidate):
                return _photo_url(city, fname, ext, legacy=legacy)
    return None


def _load_index() -> dict:
    with _INDEX_LOCK:
        try:
            value = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}


@contextmanager
def _index_file_lock():
    """Serialize index read/merge/replace across threads and worker processes."""
    lock_path = INDEX_FILE.with_suffix(INDEX_FILE.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        if lock_file.seek(0, os.SEEK_END) == 0:
            lock_file.write(b"0")
            lock_file.flush()
        lock_file.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _save_index(index: dict) -> None:
    temp_path = None
    with _INDEX_LOCK:
        try:
            PHOTO_DIR.mkdir(parents=True, exist_ok=True)
            with _index_file_lock():
                try:
                    current = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
                    if not isinstance(current, dict):
                        current = {}
                except (OSError, json.JSONDecodeError):
                    current = {}
                # Merge with the latest on-disk index while holding both locks
                # so concurrent requests cannot erase one another's rows.
                for key, row in index.items():
                    if not isinstance(row, dict):
                        continue
                    existing = current.get(key)
                    if isinstance(existing, dict) and _timestamp_value(existing.get("checked_at")) > _timestamp_value(row.get("checked_at")):
                        continue
                    current[key] = row
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=PHOTO_DIR,
                    prefix=INDEX_FILE.name + ".", suffix=".tmp", delete=False,
                ) as temp_file:
                    temp_path = Path(temp_file.name)
                    json.dump(current, temp_file, ensure_ascii=False, indent=1)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                os.replace(temp_path, INDEX_FILE)
        except OSError:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _timestamp_value(value) -> float:
    try:
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _cache_key(city: str, prefix: str, name: str) -> str:
    payload = json.dumps([city, prefix, name], ensure_ascii=False, separators=(",", ":"))
    return f"{_CACHE_VERSION}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _cache_is_fresh(
    record: dict, now: datetime | None = None, expiry_field: str = "expires_at"
) -> bool:
    if not isinstance(record, dict):
        return False
    expires = _timestamp_value(record.get(expiry_field))
    return bool(expires and expires > (now or _now_utc()).timestamp())


def _store_image_bytes(dest: Path, content: bytes) -> bool:
    if not _valid_image_bytes(content):
        return False
    temp_path = None
    try:
        # Validate before creating a parent so a pre-existing symlink cannot
        # cause even directory creation to escape the cache root.
        root = PHOTO_DIR.resolve()
        resolved_dest = dest.resolve()
        resolved_dest.relative_to(root)
        resolved_dest.parent.mkdir(parents=True, exist_ok=True)
        # Validate again after creating the parent to catch a raced symlink.
        resolved_dest = dest.resolve()
        resolved_dest.relative_to(root)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=resolved_dest.parent,
            prefix=resolved_dest.name + ".", suffix=".tmp", delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, resolved_dest)
        return True
    except (OSError, ValueError):
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        return False


# ────────────────────────── 高德接口 ──────────────────────────

def _amap_key(config: AmapConfig | None = None) -> str:
    key = (config or default_config.amap).web_key
    return "" if (not key or key.startswith("YOUR_")) else key


async def _poi_search(
    client: httpx.AsyncClient, keywords: str, city: str,
    config: AmapConfig | None = None,
) -> dict | None:
    """Return only a city-matched, name-matched AMap POI with valid coordinates."""
    cfg = config or default_config.amap
    key = _amap_key(cfg)
    if not key:
        return None
    params = {"keywords": keywords, "page_size": "10", "show_fields": "photos"}
    if city:
        # POI 2.0 uses `region` for city scoping; city_limit makes it strict.
        params["region"] = city
        params["city_limit"] = "true"

    async with _sem:
        try:
            resp = await client.get(
                "https://restapi.amap.com/v5/place/text",
                params=with_sig(params, key, cfg.web_secret))
            data = resp.json()
        except Exception:
            return None

    # 兼容未开通 v5 photos 字段的情况：去掉 show_fields 重试一次
    if str(data.get("status")) != "1":
        params.pop("show_fields", None)
        async with _sem:
            try:
                resp = await client.get(
                    "https://restapi.amap.com/v5/place/text",
                    params=with_sig(params, key, cfg.web_secret))
                data = resp.json()
            except Exception:
                return None

    for poi in data.get("pois") or []:
        if not _poi_name_matches(keywords, poi.get("name", "")):
            continue
        if city and not _poi_city_matches(city, poi):
            continue
        coordinate = _parse_coordinate(poi.get("location", ""))
        if coordinate is None:
            continue
        photos = [ph.get("url") for ph in (poi.get("photos") or []) if ph.get("url")]
        return {
            "coordinate": coordinate,
            "photos": photos,
            "name": poi.get("name", ""),
            "poi_id": str(poi.get("id") or ""),
        }
    return None


async def _static_map(
    client: httpx.AsyncClient, coordinate: list[float], config: AmapConfig | None = None
) -> bytes | None:
    """高德静态地图：真实位置地图卡，任何有坐标的 POI 都能生成"""
    cfg = config or default_config.amap
    key = _amap_key(cfg)
    if not key or not coordinate:
        return None
    loc = f"{coordinate[0]},{coordinate[1]}"
    params = with_sig(
        {"location": loc, "zoom": "15", "size": "480*300", "scale": "2",
         "markers": f"mid,0xFF6B9D,:{loc}"},
        key, cfg.web_secret)
    async with _sem:
        try:
            resp = await client.get("https://restapi.amap.com/v3/staticmap", params=params)
        except Exception:
            return None
    if resp.status_code == 200 and resp.content[:8] == b"\x89PNG\r\n\x1a\n":
        return resp.content
    return None


async def _wikimedia_photo(client: httpx.AsyncClient, query: str) -> str | None:
    """Wikimedia Commons 图片（默认关闭，知名景点覆盖好但大陆访问不稳定）"""
    if not default_config.image.use_wikimedia:
        return None
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": "1",
        "prop": "imageinfo", "iiprop": "url", "iiurlwidth": "640",
    }
    async with _sem:
        try:
            resp = await client.get(
                "https://commons.wikimedia.org/w/api.php",
                params=params, timeout=httpx.Timeout(8.0))
            pages = (resp.json().get("query") or {}).get("pages") or {}
        except Exception:
            return None
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("thumburl"):
            return info["thumburl"]
    return None


# ────────────────────────── 下载 ──────────────────────────

def _allowed_image_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or not host:
            return False
        return any(host == suffix or host.endswith("." + suffix)
                   for suffix in ("autonavi.com", "amap.com", "wikimedia.org"))
    except (TypeError, ValueError):
        return False


def _image_extension(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith((b"RIFF")) and content[8:12] == b"WEBP":
        return ".webp"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    return ".jpg"


async def _download_to(client: httpx.AsyncClient, url: str, dest: Path) -> Path | None:
    """Download an allow-listed image atomically; never persist the source URL."""
    if not _allowed_image_url(url):
        return None
    async with _sem:
        try:
            resp = await client.get(url)
        except Exception:
            return None
    content = resp.content if resp.status_code == 200 else b""
    if not _valid_image_bytes(content):
        return None
    final_url = str(getattr(resp, "url", url))
    if not _allowed_image_url(final_url):
        return None
    actual_dest = dest.with_suffix(_image_extension(content))
    return actual_dest if _store_image_bytes(actual_dest, content) else None


# ────────────────────────── 富化主流程 ──────────────────────────

async def _resolve(
    client: httpx.AsyncClient, city: str, name: str, prefix: str,
    index: dict, config: AmapConfig | None = None,
) -> tuple[str | None, list | None, dict]:
    """Resolve a POI and return local photo, verified coordinate, and provenance."""
    cfg = config or default_config.amap
    if not str(city or "").strip() or not str(name or "").strip():
        return None, None, {}

    cache_key = _cache_key(city, prefix, name)
    cached = index.get(cache_key)
    cached = cached if isinstance(cached, dict) else {}
    now = _now_utc()
    coordinate_fresh = _cache_is_fresh(cached, now, "coordinate_expires_at")
    photo_fresh = _cache_is_fresh(cached, now, "photo_expires_at")
    coordinate = (
        _parse_coordinate(cached.get("coordinate"))
        if coordinate_fresh and cached.get("coordinate_verified") is True
        and cached.get("coordinate_source") == "amap_poi" else None
    )
    photo = None
    if cached.get("photo_source") == "local_unknown":
        photo_fresh = True  # local assets have no reliable query date or remote TTL
    if photo_fresh and cached.get("photo_source") in {
        "amap_poi_photo", "wikimedia_commons", "static_map", "local_unknown"
    }:
        cached_path = _path_from_photo_url(cached.get("photo", ""))
        expected_paths = {
            _asset_path(city, prefix + name, ext)
            for ext in _LOCAL_EXTS
        }
        if cached_path in expected_paths and cached_path and _valid_image_file(cached_path):
            photo = cached.get("photo")
    if coordinate and photo:
        return photo, coordinate, cached

    # A pre-index/legacy image has no trustworthy provenance. Keep the legacy
    # local-first behavior, but expose it as unknown and never call it a photo.
    if not cached and not photo:
        legacy_photo = _local_photo(city, prefix + name)
        legacy_path = _path_from_photo_url(legacy_photo or "")
        hashed_paths = {_asset_path(city, prefix + name, ext) for ext in _LOCAL_EXTS}
        if legacy_photo and legacy_path not in hashed_paths:
            photo = legacy_photo

    key = _amap_key(cfg)
    if not key:
        record = dict(cached)
        if photo and not record:
            record = {"photo": photo, "photo_source": "local_unknown"}
        if not coordinate and record:
            record["coordinate"] = None
            record["coordinate_verified"] = False
            record["coordinate_source"] = ""
            record["coordinate_checked_at"] = None
            record["coordinate_expires_at"] = None
        if not photo and record:
            record["photo"] = ""
            record["photo_source"] = "none"
            record["photo_checked_at"] = None
            record["photo_expires_at"] = None
        return photo, coordinate, record

    poi = None
    coordinate_refreshed = False
    if not coordinate or not photo or cached.get("photo_source") == "local_unknown":
        poi = await _poi_search(client, name, city, cfg)
    if poi and poi.get("coordinate"):
        coordinate = poi["coordinate"]
        coordinate_refreshed = True

    photo_source = cached.get("photo_source") if photo else "none"
    if photo and not photo_source:
        photo_source = "local_unknown"
    photo_host = cached.get("photo_source_host") if photo else ""
    photo_checked_at = cached.get("photo_checked_at") if photo else None
    if not photo:
        # 1) AMap POI photograph.
        for source_url in (poi or {}).get("photos", []):
            if not _allowed_image_url(source_url):
                continue
            base_path = _asset_path(city, prefix + name, ".jpg")
            downloaded_path = await _download_to(client, source_url, base_path)
            if downloaded_path:
                photo = _photo_url(city, prefix + name, downloaded_path.suffix.lower())
                photo_source = "amap_poi_photo"
                photo_host = (urlsplit(source_url).hostname or "").lower()
                photo_checked_at = _now_utc().isoformat()
                break

    # 2) Optional Wikimedia Commons photograph.
    if not photo:
        wiki_url = await _wikimedia_photo(client, f"{city} {name}".strip())
        if wiki_url and _allowed_image_url(wiki_url):
            downloaded_path = await _download_to(
                client, wiki_url, _asset_path(city, prefix + name, ".jpg")
            )
            if downloaded_path:
                photo = _photo_url(city, prefix + name, downloaded_path.suffix.lower())
                photo_source = "wikimedia_commons"
                photo_host = (urlsplit(wiki_url).hostname or "").lower()
                photo_checked_at = _now_utc().isoformat()

    # 3) A static map is a location illustration, never a real POI photograph.
    if not photo and coordinate:
        png = await _static_map(client, coordinate, cfg)
        if png and _store_image_bytes(_asset_path(city, prefix + name, ".png"), png):
            photo = _photo_url(city, prefix + name, ".png")
            photo_source = "static_map"
            photo_host = "restapi.amap.com"
            photo_checked_at = _now_utc().isoformat()

    current = _now_utc()
    if coordinate_refreshed:
        coordinate_checked_at = current.isoformat()
        coordinate_expires_at = (current + _CACHE_TTL).isoformat()
    elif coordinate and coordinate_fresh:
        # A photo retry must never renew the verification age of a cached POI.
        coordinate_checked_at = cached.get("coordinate_checked_at")
        coordinate_expires_at = cached.get("coordinate_expires_at")
    else:
        coordinate_checked_at = None
        coordinate_expires_at = None

    if photo and photo_source in {"amap_poi_photo", "wikimedia_commons", "static_map"}:
        if photo_checked_at and photo_checked_at != cached.get("photo_checked_at"):
            photo_expires_at = (_timestamp_value(photo_checked_at) + _CACHE_TTL.total_seconds())
            photo_expires_at = datetime.fromtimestamp(photo_expires_at, timezone.utc).isoformat()
        else:
            photo_expires_at = cached.get("photo_expires_at")
    else:
        photo_expires_at = None

    active_expiries = [
        _timestamp_value(value) for value in (coordinate_expires_at, photo_expires_at)
        if value
    ]
    record = {
        "photo": photo or "",
        "photo_source": photo_source if photo else "none",
        "photo_source_host": photo_host if photo else "",
        "photo_checked_at": photo_checked_at if photo else None,
        "photo_expires_at": photo_expires_at,
        "coordinate": coordinate,
        "coordinate_verified": bool(coordinate),
        "coordinate_source": "amap_poi" if coordinate else "",
        "coordinate_checked_at": coordinate_checked_at,
        "coordinate_expires_at": coordinate_expires_at,
        "poi_id": ((poi or {}).get("poi_id") or cached.get("poi_id", "")) if coordinate else "",
        "poi_name": ((poi or {}).get("name") or cached.get("poi_name", "")) if coordinate else "",
        "verification_boundary": (
            "已核对高德 POI 名称、城市与坐标；未核验门票、营业时间、预约及无障碍信息。"
            if coordinate else "图片来源已标记；未核验票务、营业时间、预约及无障碍信息。"
        ),
        "checked_at": current.isoformat(),
        "expires_at": datetime.fromtimestamp(max(active_expiries), timezone.utc).isoformat()
        if active_expiries else None,
    }
    # Never persist a miss: a future call can retry after keys/network recover.
    if photo or coordinate:
        index[cache_key] = record
    return photo, coordinate, record


async def _enrich_spot(client: httpx.AsyncClient, spot, index: dict, config: AmapConfig) -> None:
    try:
        city = getattr(spot, "city", "") or ""
        photo, coordinate, record = await _resolve(client, city, spot.name, "", index, config)
        spot.photo = photo or ""
        spot.photo_source = record.get("photo_source", "none")
        spot.photo_checked_at = record.get("photo_checked_at")
        spot.coordinate = coordinate
        spot.coordinate_verified = bool(coordinate)
        spot.coordinate_source = record.get("coordinate_source", "")
        spot.coordinate_checked_at = record.get("coordinate_checked_at")
        spot.poi_id = record.get("poi_id", "")
    except Exception:
        pass  # 单个景点失败不影响整体


async def _enrich_culture(client: httpx.AsyncClient, culture, index: dict, config: AmapConfig) -> None:
    city = culture.city or ""
    must_eat = (culture.cuisine or {}).get("must_eat") or []
    for food in must_eat:
        if not isinstance(food, dict):
            continue
        try:
            store = food.get("where") or food.get("name") or ""
            if not store:
                continue
            photo, coordinate, record = await _resolve(client, city, store, "food_", index, config)
            food["coordinate"] = coordinate
            food["coordinate_verified"] = bool(coordinate)
            food["coordinate_source"] = record.get("coordinate_source", "")
            food["coordinate_checked_at"] = record.get("coordinate_checked_at")
            food["poi_id"] = record.get("poi_id", "")
            food["photo"] = photo or ""
            food["photo_source"] = record.get("photo_source", "none")
            food["photo_checked_at"] = record.get("photo_checked_at")
        except Exception:
            continue


async def _enrich_activity(client: httpx.AsyncClient, city: str, activity, config: AmapConfig) -> None:
    if not activity:
        return
    activity.coordinate = None
    activity.coordinate_verified = False
    activity.coordinate_source = ""
    activity.coordinate_checked_at = None
    activity.poi_id = ""
    if not getattr(activity, "name", "").strip():
        return
    if not _amap_key(config):
        return
    poi = await _poi_search(client, activity.name, city, config)
    if poi and poi.get("coordinate"):
        activity.coordinate = poi["coordinate"]
        activity.coordinate_verified = True
        activity.coordinate_source = "amap_poi"
        activity.coordinate_checked_at = _now_utc().isoformat()
        activity.poi_id = poi.get("poi_id", "")


def clear_untrusted_enrichment(spots: list, cultures: list, route=None) -> None:
    """Clear every model-asserted photo/location provenance before enrichment."""
    for spot in spots or []:
        spot.coordinate = None
        spot.coordinate_verified = False
        spot.coordinate_source = ""
        spot.coordinate_checked_at = None
        spot.poi_id = ""
        spot.photo = ""
        spot.photo_source = "none"
        spot.photo_checked_at = None
    for culture in cultures or []:
        cuisine = getattr(culture, "cuisine", {}) or {}
        for food in cuisine.get("must_eat", []) if isinstance(cuisine, dict) else []:
            if not isinstance(food, dict):
                continue
            for key in (
                "coordinate", "coordinate_verified", "coordinate_source",
                "coordinate_checked_at", "poi_id", "photo", "photo_source",
                "photo_checked_at",
            ):
                food.pop(key, None)
            food["coordinate"] = None
            food["coordinate_verified"] = False
            food["photo"] = ""
            food["photo_source"] = "none"
    if route is not None:
        for day in getattr(route, "daily_plan", []) or []:
            day.city_center = None
            day.stay_coordinate = None
            day.stay_coordinate_verified = False
            for activity in (day.morning, day.afternoon, day.evening):
                if activity is None:
                    continue
                activity.coordinate = None
                activity.coordinate_verified = False
                activity.coordinate_source = ""
                activity.coordinate_checked_at = None
                activity.poi_id = ""
        for segment in getattr(route, "transport", []) or []:
            segment.from_coord = None
            segment.to_coord = None


async def enrich_guide(spots: list, cultures: list, route=None, config: AmapConfig | None = None) -> None:
    """Enrich content POIs and daily activities with verified AMap locations.

    纯本地缓存可用时（未配高德 Key）也能命中历史图片。
    """
    clear_untrusted_enrichment(spots, cultures, route)
    cfg = config or default_config.amap
    daily_plan = getattr(route, "daily_plan", []) if route is not None else []
    if not spots and not cultures and not daily_plan:
        return

    index = _load_index()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0),
        follow_redirects=True,
        headers={"User-Agent": "shanhe-travel/1.0"},
    ) as client:
        tasks = [_enrich_spot(client, s, index, cfg) for s in spots]
        tasks += [_enrich_culture(client, c, index, cfg) for c in cultures]
        for day in daily_plan:
            for activity in (day.morning, day.afternoon, day.evening):
                tasks.append(_enrich_activity(client, day.city, activity, cfg))
        await asyncio.gather(*tasks)
    _save_index(index)


def _normalize_place(value: str) -> str:
    text = "".join(str(value or "").split())
    for suffix in ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区", "自治区", "自治州", "地区", "市", "县", "区"):
        if text.endswith(suffix):
            return text[:-len(suffix)]
    return text


def _poi_city_matches(city: str, poi: dict) -> bool:
    target = _normalize_place(city)
    candidates = (poi.get("cityname"), poi.get("adname"))
    return bool(target) and any(_normalize_place(candidate or "") == target for candidate in candidates)


def _poi_name_matches(query: str, result_name: str) -> bool:
    def normalize(value: str) -> str:
        return re.sub(r"[\s·,，。;；:：()（）\[\]【】]", "", str(value or ""))
    query_norm = normalize(query)
    name_norm = normalize(result_name)
    return bool(query_norm and name_norm and query_norm == name_norm)


def _parse_coordinate(value) -> list[float] | None:
    try:
        if isinstance(value, str):
            longitude, latitude = value.split(",", 1)
            coordinate = [float(longitude), float(latitude)]
        elif isinstance(value, (list, tuple)) and len(value) == 2:
            coordinate = [float(value[0]), float(value[1])]
        else:
            return None
    except (TypeError, ValueError):
        return None
    longitude, latitude = coordinate
    if not (73 <= longitude <= 135 and 3 <= latitude <= 54):
        return None
    return coordinate
