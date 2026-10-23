"""Bounded DeepSeek Search/Fetch enrichment for generated travel spots."""

import asyncio
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

import httpx

from models.schemas import WebEvidence, WebImageCandidate, WebResearchStatus, WebSpotResearch
from tools.deepseek_search_settings import DeepSeekResearchConfig
from tools.web_image_download import WebImageDownloader, safe_http_url

SEARCH_TIMEOUT_SECONDS = 12.0
FETCH_TIMEOUT_SECONDS = 12.0
TOTAL_TIMEOUT_SECONDS = 42.0
MAX_SPOTS = 3
MAX_CONCURRENCY = 2
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_FETCH_TEXT = 500_000
MAX_EVIDENCE_PER_SPOT = 3
MAX_IMAGES_PER_SPOT = 5

_RELEVANT_LINE = re.compile(r"门票|票价|成人票|学生票|儿童票|价格|元/人|开放时间|营业时间|预约|入园|免票|免费")
_PRICE_LINE = re.compile(r"(?:¥|￥|人民币|\d\s*元|元/人|成人票|学生票|儿童票|门票.{0,12}\d)")
_FACT_HEADING = re.compile(
    r"^(?:门票(?:价格|信息|说明|须知|政策|日期|条件)?|票价(?:说明|信息|优惠)?|"
    r"成人票(?:价|价格)?|票种说明|票务信息|购票须知|预约(?:须知|方式|信息|规则)?|"
    r"开放时间(?:安排|说明)?|营业时间|参观时间|入园时间|服务时间|"
    r"门票与预约|门票及预约|预约与开放时间|开放时间与预约)$"
)
_TIME_VALUE = re.compile(r"\b\d{1,2}[:：]\d{2}\b|全天|暂停售票|停止入场|闭园|开放至")
_CITY_SUFFIXES = ("特别行政区", "维吾尔自治区", "壮族自治区", "回族自治区", "自治区", "自治州", "地区", "市", "县", "区")
_SPOT_SUFFIXES = ("风景名胜区", "旅游景区", "风景区", "博物院", "博物馆", "旅游区", "国家公园", "景区", "公园", "古城", "遗址", "峡谷", "寺庙", "寺", "庙", "宫", "山", "湖", "洞")
_NON_PHOTO = re.compile(r"logo|favicon|icon|qrcode|qr[-_ ]?code|avatar|sprite|二维码|公众号|图标", re.I)


class _ImageTagParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img":
            return
        attrs = dict(attrs)
        src = attrs.get("src") or attrs.get("data-src") or ""
        if src:
            self.items.append((src, attrs.get("alt", "")))


def _city_token(city: str) -> str:
    text = "".join(str(city or "").split())
    for suffix in _CITY_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[:-len(suffix)]
            break
    return text


def _mentions_city(city: str, result: dict) -> bool:
    token = _city_token(city)
    if len(token) < 2:
        return False
    values = []
    for key in ("title", "snippet", "summary"):
        value = result.get(key)
        if isinstance(value, str):
            values.append(unquote(value))
    url = result.get("url")
    if isinstance(url, str):
        try:
            parts = urlsplit(url)
            values.extend([unquote(parts.hostname or ""), unquote(parts.path)])
        except ValueError:
            pass
    haystack = "".join(values)
    return token.casefold() in haystack.casefold()


def _spot_tokens(name: str) -> list[str]:
    token = "".join(str(name or "").split())
    tokens = [token] if token else []
    for suffix in _SPOT_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 2:
            tokens.append(token[:-len(suffix)])
            break
    return tokens


def _mentions_spot(name: str, result: dict) -> bool:
    values = []
    for key in ("title", "snippet", "summary"):
        value = result.get(key)
        if isinstance(value, str):
            values.append(unquote(value))
    url = result.get("url")
    if isinstance(url, str):
        try:
            parts = urlsplit(url)
            values.extend([unquote(parts.hostname or ""), unquote(parts.path)])
        except ValueError:
            pass
    haystack = "".join("".join(value.split()) for value in values).casefold()
    return any(token.casefold() in haystack for token in _spot_tokens(name))


def _page_matches(city: str, name: str, page: dict) -> bool:
    # Only the fetched body establishes page identity. A matching Search/title
    # can still lead to a captcha, redirect landing page, or another POI page.
    text = str(page.get("content") or "")
    compact = "".join(text.split()).casefold()
    city_token = _city_token(city)
    city_ok = len(city_token) >= 2 and city_token.casefold() in compact
    spot_ok = any(token.casefold() in compact for token in _spot_tokens(name))
    return city_ok and spot_ok


def _relevant_quotes(content: str, spot_name: str) -> tuple[list[str], list[str]]:
    quotes = []
    price_quotes = []
    seen = set()
    spot_tokens = [token.casefold() for token in _spot_tokens(spot_name)]
    spot_heading = False
    fact_heading = False
    for raw_line in str(content or "").splitlines():
        line = raw_line.strip()
        if re.match(r"^#{1,6}\s", line):
            heading = "".join(line.split()).casefold()
            heading_text = re.sub(r"^#{1,6}", "", heading).strip(" :：|·-_")
            if any(token in heading for token in spot_tokens):
                spot_heading = True
                fact_heading = False
            elif spot_heading and _FACT_HEADING.fullmatch(heading_text):
                # Generic ticket/opening-hours subsections keep the immediately
                # preceding target-attraction heading in scope.
                fact_heading = True
            else:
                # A new named attraction or an unrelated section resets scope.
                spot_heading = False
                fact_heading = False
            if (line and _RELEVANT_LINE.search(line) and spot_heading):
                excerpt = line[:500]
                if excerpt not in seen:
                    seen.add(excerpt)
                    quotes.append(excerpt)
            continue
        if not line:
            continue
        compact_line = "".join(line.split()).casefold()
        if not spot_heading and not any(token in compact_line for token in spot_tokens):
            continue
        is_fact_line = bool(_RELEVANT_LINE.search(line) or _PRICE_LINE.search(line))
        is_opening_value = fact_heading and bool(_TIME_VALUE.search(line))
        if not is_fact_line and not is_opening_value:
            continue
        # Keep a contiguous excerpt from the fetched body, so a quote is always
        # verifiable as an exact substring even when the original line is long.
        excerpt = line[:500]
        if excerpt not in seen:
            seen.add(excerpt)
            quotes.append(excerpt)
        if _PRICE_LINE.search(line) and excerpt not in price_quotes:
            price_quotes.append(excerpt)
        if len(quotes) >= 8:
            break
    return quotes[:8], price_quotes[:8]


def _markdown_images(markdown: str, page_url: str, spot_name: str) -> list[WebImageCandidate]:
    text = str(markdown or "")
    found: list[tuple[str, str]] = []
    # Markdown image links, including optional angle brackets around the URL.
    pattern = re.compile(r"!\[([^\]]{0,300})\]\(\s*(?:<([^>]+)>|([^\s)]+))", re.I)
    for match in pattern.finditer(text):
        found.append((match.group(2) or match.group(3) or "", match.group(1) or ""))
    parser = _ImageTagParser()
    try:
        parser.feed(text)
        found.extend(parser.items)
    except Exception:
        pass

    images = []
    seen = set()
    for raw_url, alt in found:
        url = html.unescape(str(raw_url or "").strip())
        if url.startswith(("//", "/")):
            # Relative page assets can be common, but they must resolve to the
            # actual source page's host and still pass the public URL check.
            from urllib.parse import urljoin
            url = urljoin(page_url, url)
        try:
            path_and_alt = (urlsplit(url).path + " " + str(alt or ""))
        except ValueError:
            continue
        if not safe_http_url(url) or url in seen or _NON_PHOTO.search(path_and_alt):
            continue
        seen.add(url)
        alt_text = str(alt or "")[:300]
        name_match = any(token.casefold() in "".join(alt_text.split()).casefold()
                         for token in _spot_tokens(spot_name))
        images.append(WebImageCandidate(
            url=url, alt=alt_text,
            association="alt_mentions_spot" if name_match else "unverified",
        ))
        if len(images) >= MAX_IMAGES_PER_SPOT:
            break
    return images


def _source_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


class DeepSeekSearchClient:
    """Small HTTP client; only safe status categories leave the module."""

    def __init__(self, config: DeepSeekResearchConfig, transport=None):
        self.config = config
        self.timeout = min(max(float(config.timeout), 0.1), SEARCH_TIMEOUT_SECONDS)
        self.transport = transport
        self._client = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout), follow_redirects=False,
            transport=self.transport, trust_env=False,
            headers={"Authorization": "Bearer " + str(self.config.api_key or ""),
                     "Content-Type": "application/json",
                     "Accept": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _post(self, path: str, payload: dict) -> dict:
        if not self.config.api_key:
            raise _ResearchError("missing_key")
        base = self.config.base_url.rstrip("/")
        if base.lower().endswith("/v1"):
            base = base[:-3]
        url = base + path
        try:
            if self._client is None:
                raise _ResearchError("client_closed")
            async with self._client.stream("POST", url, json=payload) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    raise _ResearchError(f"http_{response.status_code}")
                length = response.headers.get("content-length")
                if length:
                    try:
                        if int(length) > MAX_RESPONSE_BYTES:
                            raise _ResearchError("response_too_large")
                    except ValueError:
                        pass
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise _ResearchError("response_too_large")
                    body.extend(chunk)
            try:
                value = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                raise _ResearchError("invalid_response") from None
            if not isinstance(value, dict):
                raise _ResearchError("invalid_response")
            return value
        except _ResearchError:
            raise
        except httpx.TimeoutException:
            raise _ResearchError("timeout") from None
        except httpx.HTTPError:
            raise _ResearchError("network_error") from None
        except asyncio.CancelledError:
            raise
        except Exception:
            raise _ResearchError("network_error") from None

    async def search(self, query: str) -> list[dict]:
        if not isinstance(query, str) or not query.strip():
            raise _ResearchError("invalid_query")
        if len(query) > 128:
            query = query[:128]
        value = await self._post("/v1/tools/search", {
            "query": query, "count": 5, "need_content": False,
        })
        results = value.get("results")
        if results is None and isinstance(value.get("data"), dict):
            results = value["data"].get("results")
        if not isinstance(results, list):
            raise _ResearchError("invalid_response")
        return [item for item in results[:50] if isinstance(item, dict)]

    async def fetch(self, url: str) -> dict:
        if not safe_http_url(url):
            raise _ResearchError("unsafe_source_url")
        value = await self._post("/v1/tools/fetch", {"url": url})
        title, content = value.get("title"), value.get("content")
        if not isinstance(content, str):
            raise _ResearchError("invalid_response")
        if len(content) > MAX_FETCH_TEXT:
            content = content[:MAX_FETCH_TEXT]
        return {"title": title if isinstance(title, str) else "", "content": content}


class _ResearchError(RuntimeError):
    def __init__(self, code: str):
        self.code = code if re.fullmatch(r"(?:http_\d{3}|[a-z_]+)", code) else "request_failed"
        super().__init__(self.code)


def _status_message(code: str) -> str:
    labels = {
        "http_402": "DeepSeek Search 余额不足，请检查账户额度。",
        "http_401": "DeepSeek Search 凭据未通过验证，请检查配置。",
        "http_403": "DeepSeek Search 服务拒绝了请求，请检查账户权限。",
        "http_429": "DeepSeek Search 请求频率受限，本次未重试。",
        "timeout": "DeepSeek Search 请求超时。",
        "invalid_response": "DeepSeek Search 返回格式无法识别。",
        "response_too_large": "DeepSeek Search 返回内容超出安全上限。",
        "unsafe_source_url": "搜索结果链接不符合安全要求。",
        "network_error": "DeepSeek Search 网络连接失败。",
        "missing_key": "尚未配置可用的 DeepSeek Search 凭据。",
    }
    return labels.get(code, f"DeepSeek Search 请求失败（{code}），本次未重试。")


async def research_spots(
    spots: list,
    config: DeepSeekResearchConfig,
    downloader: WebImageDownloader | None = None,
    transport=None,
    on_progress=None,
) -> WebResearchStatus:
    """Search at most three spots; each receives <=1 Search and <=1 Fetch."""
    spot_list = list(spots or [])
    spot_records = [
        WebSpotResearch(spot_index=index, spot_name=str(getattr(spot, "name", "") or ""),
                        city=str(getattr(spot, "city", "") or ""))
        for index, spot in enumerate(spot_list)
    ]
    if not config.enabled:
        return WebResearchStatus(status="disabled", message="联网检索已关闭。", spots=spot_records)
    if config.availability != "ready" or not config.api_key:
        for row in spot_records:
            row.status = "unavailable"
        return WebResearchStatus(status="unavailable", message=_status_message(config.availability), spots=spot_records)

    targets = list(enumerate(spot_list))[:MAX_SPOTS]
    for row in spot_records[MAX_SPOTS:]:
        row.status = "skipped_limit"
    if not targets:
        return WebResearchStatus(status="complete", message="没有可联网检索的景点。", spots=spot_records)

    api = DeepSeekSearchClient(config, transport=transport)
    image_downloader = downloader or WebImageDownloader()
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    results: list[tuple[str, int, int, int, int]] = []
    error_codes: list[str] = []
    stats = {"searched_spots": 0, "search_count": 0, "fetch_count": 0,
             "image_candidate_count": 0, "images_downloaded": 0, "successful": 0}

    async def process(indexed_spot):
        index, spot = indexed_spot
        row = spot_records[index]
        search_count = fetch_count = candidate_count = downloaded_count = 0
        async with semaphore:
            city = str(getattr(spot, "city", "") or "").strip()
            name = str(getattr(spot, "name", "") or "").strip()
            query = f"{city} {name} 景区 门票 开放时间 预约".strip()
            try:
                stats["searched_spots"] += 1
                search_count += 1
                stats["search_count"] += 1
                search_results = await api.search(query)
            except _ResearchError as exc:
                error_codes.append(exc.code)
                row.status = "error"
                return (exc.code, search_count, fetch_count, candidate_count, downloaded_count)

            accepted = []
            saw_city_match = False
            for item in search_results:
                url = item.get("url")
                title = item.get("title") if isinstance(item.get("title"), str) else ""
                if not isinstance(url, str) or not safe_http_url(url):
                    continue
                if not _mentions_city(city, item):
                    continue
                saw_city_match = True
                if not _mentions_spot(name, item):
                    continue
                if any(existing.get("url") == url for existing in accepted):
                    continue
                accepted.append(item)
                if len(accepted) >= MAX_EVIDENCE_PER_SPOT:
                    break

            if not accepted:
                result_status = "no_spot_match" if saw_city_match else ("no_city_match" if search_results else "no_results")
                row.status = result_status
                stats["successful"] += 1
                return (result_status, search_count, fetch_count, candidate_count, downloaded_count)

            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            evidence = []
            for item in accepted:
                evidence.append(WebEvidence(
                    source_id=_source_id(item["url"]),
                    title=str(item.get("title") or item.get("site_name") or "网页来源")[:300],
                    url=item["url"], site_name=str(item.get("site_name") or "")[:160],
                    status="search_only", city_match="matched",
                    snippet=str(item.get("snippet") or item.get("summary") or "")[:800],
                ))
            row.evidence = evidence
            row.status = "searched"

            # At most one page is fetched for each attraction, even if Search
            # returned several plausible links.
            primary = accepted[0]
            try:
                fetch_count += 1
                stats["fetch_count"] += 1
                page = await api.fetch(primary["url"])
            except _ResearchError as exc:
                error_codes.append(exc.code)
                row.status = "searched"
                evidence[0].fetch_status = "error"
                return (exc.code, search_count, fetch_count, candidate_count, downloaded_count)

            if not _page_matches(city, name, page):
                evidence[0].fetch_status = "mismatch"
                evidence[0].city_match = "unverified"
                row.status = "page_unmatched"
                return ("page_unmatched", search_count, fetch_count, candidate_count, downloaded_count)

            evidence[0].title = str(page.get("title") or evidence[0].title)[:300]
            evidence[0].status = "fetched"
            evidence[0].fetch_status = "fetched"
            evidence[0].fetched_at = now
            quotes, price_quotes = _relevant_quotes(page["content"], name)
            evidence[0].quotes = quotes
            evidence[0].price_quotes = price_quotes
            images = _markdown_images(page["content"], primary["url"], name)
            candidate_count += len(images)
            stats["image_candidate_count"] += len(images)
            if images:
                evidence[0].image_candidates = images
                # Only the first page-linked candidate is downloaded; all
                # others remain links, never remote <img> elements.
                preferred = sorted(
                    images,
                    key=lambda item: (
                        item.association != "alt_mentions_spot",
                        int(bool(_NON_PHOTO.search((urlsplit(item.url).path + " " + item.alt)))),
                    ),
                )
                preferred = preferred[0]
                try:
                    downloaded = await image_downloader.download(preferred.url)
                except Exception:
                    downloaded = {"status": "network_error", "local_url": None, "downloaded_at": None}
                preferred.status = downloaded["status"]
                preferred.local_url = downloaded.get("local_url") or ""
                preferred.downloaded_at = downloaded.get("downloaded_at")
                downloaded_count += int(downloaded["status"] == "downloaded")
                stats["images_downloaded"] += int(downloaded["status"] == "downloaded")
                if downloaded["status"] == "downloaded" and getattr(spot, "photo_source", "none") in {"none", "static_map"}:
                    spot.photo = downloaded["local_url"]
                    spot.photo_source = "deepseek_web_image"
                    spot.photo_checked_at = downloaded.get("downloaded_at")
            stats["successful"] += 1
            return ("fetched", search_count, fetch_count, candidate_count, downloaded_count)

    async with api:
        tasks = [asyncio.create_task(process(item)) for item in targets]
        group = asyncio.gather(*tasks, return_exceptions=False)
        try:
            completed = await asyncio.wait_for(group, timeout=TOTAL_TIMEOUT_SECONDS)
            results.extend(completed)
        except asyncio.TimeoutError:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(group, return_exceptions=True)
            await asyncio.gather(*tasks, return_exceptions=True)
            for index, _spot in targets:
                row = spot_records[index]
                if row.evidence:
                    row.status = "searched"
                elif row.status in {"disabled", "unavailable", "searched"}:
                    row.status = "error"
            error_codes.append("total_timeout")
        except BaseException:
            for task in tasks:
                if not task.done():
                    task.cancel()
            if not group.done():
                group.cancel()
            await asyncio.gather(group, return_exceptions=True)
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    if callable(on_progress):
        try:
            on_progress()
        except Exception:
            pass
    search_count = stats["search_count"]
    fetch_count = stats["fetch_count"]
    candidate_count = stats["image_candidate_count"]
    downloaded_count = stats["images_downloaded"]
    successes = stats["successful"]
    has_unmatched_page = any(row.status == "page_unmatched" for row in spot_records)
    status = "partial" if has_unmatched_page else (
        "complete" if not error_codes else ("partial" if successes else "failed")
    )
    message = "联网资料已整理；来源均未作官方核验，票价仍为网页线索。"
    if has_unmatched_page:
        message = "部分抓取正文未能匹配目标城市和景点；已排除该页的票价与图片。"
    elif error_codes:
        message = _status_message(error_codes[0]) + " 已保留本次成功获取的来源。"
    return WebResearchStatus(
        status=status, message=message, searched_spots=stats["searched_spots"],
        search_count=search_count, fetch_count=fetch_count,
        image_candidate_count=candidate_count, images_downloaded=downloaded_count,
        completed_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        spots=spot_records,
    )
