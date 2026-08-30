"""
生成时富化层 · POI 坐标 + 真实图片

对攻略里的每个景点/美食店补全两样东西:
  1. 真实坐标 —— 高德 v5 POI 搜索，前端"一键导航"的精确终点
  2. 真实图片 —— 四层降级，全部落盘本地缓存，一次抓取永久复用:
       本地缓存 static/photos/{城市}/{名称}.jpg
       > 高德 POI 实拍图 (v5 搜索 show_fields=photos)
       > Wikimedia Commons (可选, config.image.use_wikimedia, 大陆访问不稳定)
       > 高德静态地图 (有坐标即可生成, 100% 可用)
       > 留空 —— 前端降级为占位图

坐标与图片的命中结果记录在 static/photos/_index.json，
重复生成同一目的地时直接命中缓存，不再请求外部 API。
"""

import asyncio
import json
import re
from pathlib import Path

import httpx

from config import default_config
from tools.amap_utils import with_sig

PHOTO_DIR = Path(__file__).parent.parent / "static" / "photos"
INDEX_FILE = PHOTO_DIR / "_index.json"

_CONCURRENCY = 6          # 并发请求上限，避免触发高德 QPS 限制
_sem = asyncio.Semaphore(_CONCURRENCY)

_LOCAL_EXTS = (".jpg", ".jpeg", ".png", ".webp")


# ────────────────────────── 本地缓存 ──────────────────────────

def _safe_filename(name: str) -> str:
    """去掉文件系统不允许的字符"""
    return re.sub(r'[\\/:*?"<>|#\s]', "", name).strip()[:60]


def _photo_url(city: str, fname: str, ext: str = ".jpg") -> str:
    prefix = f"{city}/" if city else ""
    return f"/static/photos/{prefix}{fname}{ext}"


def _local_photo(city: str, fname: str) -> str | None:
    """本地缓存命中则返回可访问的 URL 路径"""
    folder = PHOTO_DIR / city if city else PHOTO_DIR
    for ext in _LOCAL_EXTS:
        if (folder / (fname + ext)).is_file():
            return _photo_url(city, fname, ext)
    return None


def _load_index() -> dict:
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_index(index: dict) -> None:
    try:
        PHOTO_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(
            json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


# ────────────────────────── 高德接口 ──────────────────────────

def _amap_key() -> str:
    key = default_config.amap.weather_key
    return "" if (not key or key.startswith("YOUR_")) else key


async def _poi_search(client: httpx.AsyncClient, keywords: str, city: str) -> dict | None:
    """高德 v5 POI 搜索，返回 {coordinate, photos} 或 None"""
    key = _amap_key()
    if not key:
        return None
    params = {"keywords": keywords, "page_size": "1", "show_fields": "photos"}
    if city:
        params["city"] = city

    async with _sem:
        try:
            resp = await client.get(
                "https://restapi.amap.com/v5/place/text",
                params=with_sig(params, key, default_config.amap.secret))
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
                    params=with_sig(params, key, default_config.amap.secret))
                data = resp.json()
            except Exception:
                return None

    pois = data.get("pois") or []
    if not pois:
        return None
    poi = pois[0]

    coordinate = None
    loc = poi.get("location", "")
    if "," in loc:
        try:
            coordinate = [float(x) for x in loc.split(",")]
        except ValueError:
            coordinate = None

    photos = [ph.get("url") for ph in (poi.get("photos") or []) if ph.get("url")]
    return {"coordinate": coordinate, "photos": photos}


async def _static_map(client: httpx.AsyncClient, coordinate: list[float]) -> bytes | None:
    """高德静态地图：真实位置地图卡，任何有坐标的 POI 都能生成"""
    key = _amap_key()
    if not key or not coordinate:
        return None
    loc = f"{coordinate[0]},{coordinate[1]}"
    params = with_sig(
        {"location": loc, "zoom": "15", "size": "480*300", "scale": "2",
         "markers": f"mid,0xFF6B9D,:{loc}"},
        key, default_config.amap.secret)
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

async def _download_to(client: httpx.AsyncClient, url: str, dest: Path) -> bool:
    """下载图片到本地；校验 content-type / 魔数 / 大小，避免把错误页存成图片"""
    async with _sem:
        try:
            resp = await client.get(url)
        except Exception:
            return False
    content = resp.content if resp.status_code == 200 else b""
    is_image = (
        len(content) > 5000
        and (content[:3] == b"\xff\xd8\xff"                # JPEG
             or content[:8] == b"\x89PNG\r\n\x1a\n"        # PNG
             or "image" in resp.headers.get("content-type", ""))
    )
    if not is_image:
        return False
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
    except OSError:
        return False
    return True


# ────────────────────────── 富化主流程 ──────────────────────────

async def _resolve(client: httpx.AsyncClient, city: str, name: str, prefix: str, index: dict) -> tuple[str | None, list | None]:
    """解析单个 POI 的 (图片URL, 坐标)，四层降级 + 缓存

    index 为本次富化全程共享的缓存索引，由 enrich_guide 统一加载与落盘。
    """
    fname = prefix + _safe_filename(name)
    if not fname:
        return None, None

    cache_key = f"{city}|{prefix}|{name}"
    cached = index.get(cache_key)
    if cached:
        return cached.get("photo"), cached.get("coordinate")

    photo = _local_photo(city, fname)
    coordinate = None

    # 1) POI 搜索：拿坐标（导航终点），顺带拿实拍图
    poi = await _poi_search(client, name, city)
    if poi:
        coordinate = poi["coordinate"]
        if not photo and poi["photos"]:
            dest = PHOTO_DIR / (city or "_misc") / (fname + ".jpg")
            if await _download_to(client, poi["photos"][0], dest):
                photo = _photo_url(city, fname)

    # 2) Wikimedia（可选）
    if not photo:
        wiki = await _wikimedia_photo(client, f"{city} {name}".strip())
        if wiki:
            dest = PHOTO_DIR / (city or "_misc") / (fname + ".jpg")
            if await _download_to(client, wiki, dest):
                photo = _photo_url(city, fname)

    # 3) 静态地图兜底（需要坐标）
    if not photo and coordinate:
        png = await _static_map(client, coordinate)
        if png:
            dest = PHOTO_DIR / (city or "_misc") / (fname + ".jpg")
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(png)
                photo = _photo_url(city, fname)
            except OSError:
                pass

    index[cache_key] = {"photo": photo, "coordinate": coordinate}
    return photo, coordinate


async def _enrich_spot(client: httpx.AsyncClient, spot, index: dict) -> None:
    try:
        city = getattr(spot, "city", "") or ""
        photo, coordinate = await _resolve(client, city, spot.name, "", index)
        if coordinate and not spot.coordinate:
            spot.coordinate = coordinate
        if photo:
            spot.photo = photo
    except Exception:
        pass  # 单个景点失败不影响整体


async def _enrich_culture(client: httpx.AsyncClient, culture, index: dict) -> None:
    city = culture.city or ""
    must_eat = (culture.cuisine or {}).get("must_eat") or []
    for food in must_eat:
        if not isinstance(food, dict):
            continue
        try:
            store = food.get("where") or food.get("name") or ""
            if not store:
                continue
            photo, coordinate = await _resolve(client, city, store, "food_", index)
            if coordinate:
                food["coordinate"] = coordinate
            if photo:
                food["photo"] = photo
        except Exception:
            continue


async def enrich_guide(spots: list, cultures: list) -> None:
    """原地补充 spots / cultures 美食的 coordinate 与 photo 字段

    纯本地缓存可用时（未配高德 Key）也能命中历史图片。
    """
    if not spots and not cultures:
        return

    index = _load_index()
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(15.0),
        follow_redirects=True,
        headers={"User-Agent": "shanhe-travel/1.0"},
    ) as client:
        tasks = [_enrich_spot(client, s, index) for s in spots]
        tasks += [_enrich_culture(client, c, index) for c in cultures]
        await asyncio.gather(*tasks)
    _save_index(index)
