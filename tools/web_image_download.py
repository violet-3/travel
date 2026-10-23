"""Bounded, SSRF-aware downloader for image links extracted from fetched pages."""

import asyncio
import hashlib
import ipaddress
import io
import os
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from PIL import Image

from tools.enrich import PHOTO_DIR

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 3
ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}


def safe_http_url(value: str, *, https_only: bool = False) -> bool:
    if not isinstance(value, str) or len(value) > 8192 or any(ord(char) < 0x21 for char in value):
        return False
    try:
        parts = urlsplit(value)
        port = parts.port
        host = parts.hostname
    except ValueError:
        return False
    if (parts.scheme.lower() not in ({"https"} if https_only else {"http", "https"})
            or not host or parts.username is not None or parts.password is not None
            or parts.fragment):
        return False
    if port is not None and not (1 <= port <= 65535):
        return False
    host = host.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal", ".test")):
        return False
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return True
    return address.is_global


async def _resolve_public_host(host: str, port: int):
    loop = asyncio.get_running_loop()
    results = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses = {item[4][0] for item in results}
    if not addresses:
        raise ValueError("dns_failed")
    normalized = []
    for value in addresses:
        try:
            address = ipaddress.ip_address(value.split("%", 1)[0])
        except ValueError:
            raise ValueError("unsafe_address") from None
        if not address.is_global:
            raise ValueError("unsafe_address")
        normalized.append(str(address))
    return normalized


def _validate_image(content: bytes):
    if not isinstance(content, bytes) or len(content) < 24 or len(content) > MAX_IMAGE_BYTES:
        return None
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in ALLOWED_FORMATS:
                return None
            width, height = image.size
            if width < 32 or height < 32 or width > 8192 or height > 8192 or width * height > 24_000_000:
                return None
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            return ALLOWED_FORMATS.get(image.format)
    except Exception:
        return None


def _store_image(content: bytes, source_url: str, cache_dir: Path) -> str | None:
    extension = _validate_image(content)
    if not extension:
        return None
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    root = Path(cache_dir).resolve()
    destination = (root / "web-research" / (digest + extension)).resolve()
    try:
        destination.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Re-check after mkdir in case the target directory was replaced by a symlink.
        destination.resolve().relative_to(root)
        temp_path = None
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=digest + ".", suffix=".tmp", delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, destination)
        return "/static/photos/web-research/" + destination.name
    except (OSError, ValueError):
        try:
            if "temp_path" in locals() and temp_path is not None:
                temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None


class WebImageDownloader:
    def __init__(
        self,
        cache_dir: str | Path | None = None,
        transport=None,
        resolver=None,
        timeout: float = 8.0,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir is not None else PHOTO_DIR
        self.transport = transport
        self.resolver = resolver or _resolve_public_host
        self.timeout = min(max(float(timeout), 0.1), 10.0)

    async def download(self, url: str) -> dict:
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if not safe_http_url(url, https_only=True):
            return {"status": "unsafe_url", "local_url": None, "downloaded_at": None}

        current = url
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout), follow_redirects=False,
            transport=self.transport, trust_env=False,
            headers={"User-Agent": "shanhe-travel/1.0"},
        ) as client:
            for redirect_count in range(MAX_REDIRECTS + 1):
                if not safe_http_url(current, https_only=True):
                    return {"status": "unsafe_redirect", "local_url": None, "downloaded_at": None}
                parts = urlsplit(current)
                try:
                    resolved = await asyncio.wait_for(
                        self.resolver(parts.hostname, parts.port or 443), timeout=self.timeout
                    )
                    addresses = resolved if isinstance(resolved, (list, tuple, set)) else []
                    if not addresses:
                        return {"status": "unsafe_or_unresolved_host", "local_url": None, "downloaded_at": None}
                    pinned_ip = str(addresses[0]).split("%", 1)[0]
                    try:
                        address = ipaddress.ip_address(pinned_ip)
                    except ValueError:
                        return {"status": "unsafe_or_unresolved_host", "local_url": None, "downloaded_at": None}
                    if not address.is_global:
                        return {"status": "unsafe_or_unresolved_host", "local_url": None, "downloaded_at": None}
                except Exception:
                    return {"status": "unsafe_or_unresolved_host", "local_url": None, "downloaded_at": None}
                try:
                    request = client.build_request("GET", current)
                    original_host = parts.hostname.encode("idna").decode("ascii")
                    host_header = original_host
                    port = parts.port or 443
                    if port != 443:
                        host_header += ":" + str(port)
                    request.headers["host"] = host_header
                    request.extensions["sni_hostname"] = original_host
                    request.url = request.url.copy_with(host=pinned_ip)
                    response = await client.send(request, stream=True)
                    try:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location or redirect_count >= MAX_REDIRECTS:
                                return {"status": "redirect_limit", "local_url": None, "downloaded_at": None}
                            current = urljoin(current, location)
                            continue
                        if response.status_code != 200:
                            return {"status": "http_error", "local_url": None, "downloaded_at": None}
                        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                        if not content_type.startswith("image/") or content_type in {"image/svg+xml", "image/x-icon"}:
                            return {"status": "not_image", "local_url": None, "downloaded_at": None}
                        length = response.headers.get("content-length")
                        if length:
                            try:
                                if int(length) > MAX_IMAGE_BYTES:
                                    return {"status": "too_large", "local_url": None, "downloaded_at": None}
                            except ValueError:
                                pass
                        chunks = []
                        size = 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > MAX_IMAGE_BYTES:
                                return {"status": "too_large", "local_url": None, "downloaded_at": None}
                            chunks.append(chunk)
                        content = b"".join(chunks)
                        if not _validate_image(content):
                            return {"status": "invalid_image", "local_url": None, "downloaded_at": None}
                        local_url = _store_image(content, url, self.cache_dir)
                        if not local_url:
                            return {"status": "cache_error", "local_url": None, "downloaded_at": None}
                        return {"status": "downloaded", "local_url": local_url, "downloaded_at": timestamp}
                    finally:
                        await response.aclose()
                except httpx.TimeoutException:
                    return {"status": "timeout", "local_url": None, "downloaded_at": None}
                except httpx.HTTPError:
                    return {"status": "network_error", "local_url": None, "downloaded_at": None}
        return {"status": "redirect_limit", "local_url": None, "downloaded_at": None}
