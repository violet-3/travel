"""
山河游记 · FastAPI 纯后端
启动: python app.py
API:
  POST /api/generate         → 攻略 JSON (一次性)
  POST /api/generate/stream  → NDJSON 流: 进度事件 + 最终攻略 (前端用)
  GET  /api/config           → 前端地图所需的高德 JS Key / 安全密钥
"""

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from datetime import date
from typing import Literal
from urllib.parse import urlsplit

import anyio
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, field_validator
from starlette.responses import JSONResponse

from config import (
    AmapConfig,
    ModelConfigError,
    ModelProfileNotFoundError,
    default_config,
    resolve_model_config,
)
from orchestrator_llm import TravelOrchestrator
from agents.guide_generator import GuideGenerator
from models.schemas import TravelGuide
from tools.model_profiles import (
    CredentialStoreUnavailableError,
    ModelProfileStore,
    ProfileNotFoundError,
    ProfilePayload,
    ProfileStoreError,
)
from tools.amap_settings import AmapSettingsError, AmapSettingsPayload, AmapSettingsStore
from tools.deepseek_search_settings import (
    OFFICIAL_BASE_URL,
    DeepSeekResearchConfig,
    DeepSeekSearchSettingsError,
    DeepSeekSearchSettingsPayload,
    DeepSeekSearchSettingsStore,
)
from tools.llm_client import (
    IntegrationDependencyError,
    classify_model_error,
    get_llm,
    safe_model_error_message,
)
from tools.travel_dates import TravelDateError, parse_travel_date, shanghai_today
from tools.travel_intent import TravelIntentError, validate_constraint_consistency
from tools.guide_history import GuideHistoryError, GuideHistoryStore
from tools.guide_cache import GuideCache, build_cache_key

app = FastAPI(title="山河游记")
_logger = logging.getLogger(__name__)
_STREAM_CLEANUP_TIMEOUT_SECONDS = 2.0
model_profiles = ModelProfileStore()
amap_settings = AmapSettingsStore()
deepseek_search_settings = DeepSeekSearchSettingsStore()
guide_history = GuideHistoryStore()
guide_cache = GuideCache()
frontend = Path(__file__).parent / "frontend"
photo_dir = Path(__file__).parent / "static" / "photos"
photo_dir.mkdir(parents=True, exist_ok=True)   # 富化层图片缓存目录

class GenReq(BaseModel):
    query: str = ""
    profile_id: str | None = None
    destinations: list[str] | None = None
    departure_city: str | None = None
    travel_date: date | None = None
    days: int | None = Field(default=None, strict=True, ge=1, le=60)
    travelers: int | None = Field(default=None, strict=True, ge=1, le=50)
    budget: int | None = Field(default=None, strict=True, gt=0, le=100_000_000)
    budget_scope: Literal["per_person", "total"] | None = None
    pace: Literal["不紧不慢", "轻松", "特种兵"] | None = None
    preferences: list[str] | None = None
    constraints: list[str] | None = None
    # 第15轮：跳过短时缓存，强制重新调用模型
    force_refresh: bool = False

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value):
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError("invalid")
        return value.strip()

    @field_validator("destinations", "preferences", "constraints", mode="before")
    @classmethod
    def normalize_string_lists(cls, value):
        if value is None:
            return None
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError("invalid")
        return [item.strip() for item in value if item.strip()]

    @field_validator("departure_city", mode="before")
    @classmethod
    def normalize_optional_city(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("invalid")
        value = value.strip()
        return value or None

    @field_validator("travel_date")
    @classmethod
    def require_future_date(cls, value):
        if value is not None and value < shanghai_today():
            raise ValueError("invalid")
        return value

    def travel_overrides(self) -> dict:
        keys = (
            "destinations", "departure_city", "travel_date", "days", "travelers",
            "budget", "budget_scope", "pace", "preferences", "constraints",
        )
        return {key: getattr(self, key) for key in keys if getattr(self, key) is not None}


def _validate_generation_request(req: GenReq) -> None:
    overrides = req.travel_overrides()
    if not req.query and not req.destinations:
        raise HTTPException(status_code=422, detail="请填写旅行描述或至少一个目的地。")
    if "travel_date" not in overrides:
        try:
            parse_travel_date(req.query)
        except TravelDateError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        validate_constraint_consistency(req.query, overrides.get("constraints"))
    except TravelIntentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


class DiagnosticProbe(BaseModel):
    result: Literal["ok"]


def _parse_local_host(authority: str | None):
    if not authority:
        return None
    try:
        parsed = urlsplit("//" + authority)
        hostname = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError:
        return None
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        return None
    if hostname not in {"localhost", "127.0.0.1", "::1"}:
        return None
    return hostname, port


class LocalRequestBoundary:
    """Reject non-loopback hosts and cross-origin API writes."""

    def __init__(self, downstream):
        self.downstream = downstream

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.downstream(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        host = _parse_local_host(headers.get(b"host", b"").decode("latin1"))
        if host is None:
            response = JSONResponse({"detail": "仅允许通过本机地址访问"}, status_code=403)
            await response(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()
        origin_header = headers.get(b"origin")
        if path.startswith("/api/") and method in {"POST", "PUT", "PATCH", "DELETE"} and origin_header:
            try:
                origin = urlsplit(origin_header.decode("latin1"))
                origin_host = (origin.hostname or "").lower()
                origin_port = origin.port
                if origin_port is None:
                    origin_port = 443 if origin.scheme == "https" else 80
                host_name, host_port = host
                request_scheme = scope.get("scheme", "http").lower()
                request_port = host_port or (443 if request_scheme == "https" else 80)
                valid_origin = (
                    origin.scheme.lower() == request_scheme
                    and origin_host == host_name
                    and origin_port == request_port
                    and origin_host in {"localhost", "127.0.0.1", "::1"}
                    and not origin.username and not origin.password
                    and origin.path in {"", "/"} and not origin.query and not origin.fragment
                )
            except (UnicodeDecodeError, ValueError):
                valid_origin = False
            if not valid_origin:
                response = JSONResponse({"detail": "请求来源无效"}, status_code=403)
                await response(scope, receive, send)
                return

        await self.downstream(scope, receive, send)


app.add_middleware(LocalRequestBoundary)


def _profile_error(exc: ProfileStoreError) -> HTTPException:
    if isinstance(exc, ValidationError):
        return HTTPException(status_code=422, detail="模型配置字段无效，请检查填写内容")
    if isinstance(exc, ProfileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, CredentialStoreUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(RequestValidationError)
async def safe_validation_error(_request: Request, exc: RequestValidationError):
    """Never echo raw request values; invalid API-key inputs can contain secrets."""
    safe_errors = []
    for error in exc.errors():
        safe_errors.append({
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": "字段无效，请检查填写内容",
            "type": str(error.get("type", "value_error")),
        })
    return JSONResponse(status_code=422, content={"detail": safe_errors})


def _request_orchestrator(req: GenReq) -> TravelOrchestrator:
    try:
        # Resolve synchronously at request start. This immutable snapshot stays
        # attached to this run even if the default profile changes later.
        model_config = resolve_model_config(req.profile_id, model_profiles)
    except (ModelConfigError, ModelProfileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    amap_config_warning = ""
    try:
        amap_config = amap_settings.resolve(default_config.amap)
    except AmapSettingsError:
        # Keep the LangChain text-planning pipeline usable, but do not silently
        # fall back to another AMap credential when the selected one is unreadable.
        amap_config = AmapConfig(web_key="", web_secret="", js_key="", js_security_code="")
        amap_config_warning = "高德配置无法读取，本次未调用地图、POI 或天气服务；文本攻略仍可生成。"
    try:
        research_config = deepseek_search_settings.resolve(model_profiles)
    except DeepSeekSearchSettingsError:
        # An unreadable optional settings file must not block ordinary guide
        # generation. The requested opt-in is surfaced as unavailable.
        research_config = DeepSeekResearchConfig(
            enabled=True, base_url=OFFICIAL_BASE_URL, availability="profile_unavailable"
        )
    return TravelOrchestrator(
        model_config, amap_config=amap_config, amap_config_warning=amap_config_warning,
        research_config=research_config,
    )


def _guide_json(guide) -> dict:
    # by_alias: Transport 的 from/to 别名输出为 "from"/"to"，与前端字段对齐
    return json.loads(guide.model_dump_json(by_alias=True))


async def _record_guide_history(guide) -> bool:
    history_id = uuid.uuid4().hex
    try:
        guide.history_id = history_id
        guide.history_saved = True
        await asyncio.to_thread(guide_history.save, _guide_json(guide), history_id)
    except Exception:
        try:
            guide.history_id = None
            guide.history_saved = False
        except Exception:
            pass
        return False
    return True


def _cache_key_for(req: GenReq, orch) -> str:
    return build_cache_key(
        req.query, req.travel_overrides(),
        getattr(orch, "model_config", None), req.profile_id,
        date_context=(None if req.travel_date else shanghai_today().isoformat()),
        amap_config=getattr(orch, "amap_config", None),
        research_config=getattr(orch, "research_config", None),
    )


def _restore_cached_guide(hit: dict) -> TravelGuide:
    """Rebuild a guide from cache without inheriting stale history identifiers."""
    guide = TravelGuide.model_validate(hit["guide"])
    guide.cache_hit = True
    guide.cache_age_seconds = int(hit.get("age_seconds") or 0)
    guide.history_id = None
    guide.history_saved = False
    return guide


def _store_cache(cache_key: str, guide) -> None:
    # A cache hit must never be written back as a new entry.
    if guide is None or getattr(guide, "cache_hit", False):
        return
    try:
        guide_cache.set(cache_key, _guide_json(guide))
    except Exception as exc:
        _logger.warning("Generation cache write failed (%s)", type(exc).__name__)


def _read_cached_guide(cache_key: str):
    """Return a validated cache hit; every cache failure degrades to a miss."""
    try:
        hit = guide_cache.get(cache_key)
        if not hit:
            return None
        try:
            guide = _restore_cached_guide(hit)
        except Exception:
            try:
                guide_cache.discard(cache_key)
            except Exception:
                pass
            return None
        return {"guide": guide, "age_seconds": guide.cache_age_seconds or 0}
    except Exception as exc:
        _logger.warning("Generation cache read failed (%s)", type(exc).__name__)
        return None


def _invalidate_guide_cache_after_map_change() -> None:
    try:
        guide_cache.clear()
    except Exception as exc:
        _logger.warning("Generation cache invalidation failed (%s)", type(exc).__name__)


async def _close_unused_orchestrator(orch) -> None:
    """Release the eager client when a cache hit skips orchestrator.generate()."""
    client = getattr(orch, "llm_client", None)
    close = getattr(client, "aclose", None)
    if not callable(close):
        return
    with anyio.CancelScope(shield=True):
        try:
            await close()
        except Exception as exc:
            _logger.warning("Unused generation client close failed (%s)", type(exc).__name__)


def _runtime_metrics(orch, started: float) -> dict:
    client = getattr(orch, "llm_client", None)
    getter = getattr(client, "metrics_snapshot", None)
    llm_metrics = getter() if callable(getter) else {
        "requests": 0, "elapsed_ms": 0, "input_tokens": None,
        "output_tokens": None, "total_tokens": None,
        "usage_known_calls": 0, "usage_unknown_calls": 0,
    }
    return {"elapsed_ms": round((time.perf_counter() - started) * 1000), "llm": llm_metrics}


def _ndjson(obj) -> str:
    return json.dumps(obj, ensure_ascii=False) + "\n"


@app.post("/api/generate")
async def api_generate(req: GenReq):
    _validate_generation_request(req)
    orch = _request_orchestrator(req)
    overrides = req.travel_overrides()
    cache_key = _cache_key_for(req, orch)

    if not req.force_refresh:
        hit = await asyncio.to_thread(_read_cached_guide, cache_key)
        if hit:
            await _close_unused_orchestrator(orch)
            guide = hit["guide"]
            await _record_guide_history(guide)
            return _guide_json(guide)

    try:
        if overrides:
            guide = await orch.generate(req.query, request_overrides=overrides)
        else:
            guide = await orch.generate(req.query)
    except (TravelDateError, TravelIntentError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except Exception as exc:
        from orchestrator_llm import GenerationStageTimeout
        if isinstance(exc, GenerationStageTimeout):
            raise HTTPException(status_code=504, detail=str(exc)) from None
        raise HTTPException(status_code=500, detail="生成失败，请检查模型服务配置后重试") from None
    await asyncio.to_thread(_store_cache, cache_key, guide)
    await _record_guide_history(guide)
    return _guide_json(guide)


@app.post("/api/generate/stream")
async def api_generate_stream(req: GenReq, request: Request):
    """流式生成: 逐行输出 {"type":"progress",...} 进度事件，最后输出 {"type":"guide",...} 或 {"type":"error",...}"""
    _validate_generation_request(req)
    orch = _request_orchestrator(req)
    overrides = req.travel_overrides()
    cache_key = _cache_key_for(req, orch)
    queue: asyncio.Queue = asyncio.Queue()
    started = time.perf_counter()

    def on_progress(progress: int, stage: str, message: str):
        queue.put_nowait({"type": "progress", "progress": progress,
                          "stage": stage, "message": message})

    async def event_gen():
        if not req.force_refresh:
            hit = await asyncio.to_thread(_read_cached_guide, cache_key)
            if hit:
                await _close_unused_orchestrator(orch)
                guide = hit["guide"]
                age = hit["age_seconds"]
                yield _ndjson({
                    "type": "progress", "progress": 100, "stage": "cache",
                    "message": f"复用 {max(1, age // 60)} 分钟内的相同请求结果",
                })
                await _record_guide_history(guide)
                yield _ndjson({"type": "guide", "guide": _guide_json(guide)})
                return

        kwargs = {"on_progress": on_progress}
        if overrides:
            kwargs["request_overrides"] = overrides
        task = asyncio.create_task(orch.generate(req.query, **kwargs))
        getter = asyncio.create_task(queue.get())
        try:
            while True:
                done, _ = await asyncio.wait(
                    {getter, task}, timeout=0.25, return_when=asyncio.FIRST_COMPLETED
                )
                if not done:
                    if await request.is_disconnected():
                        return
                    continue
                if getter in done:
                    yield _ndjson(getter.result())
                    getter = asyncio.create_task(queue.get())
                if task in done:
                    getter.cancel()
                    while not queue.empty():          # 排空剩余进度
                        yield _ndjson(queue.get_nowait())
                    if task.cancelled():
                        yield _ndjson({"type": "error", "message": "本次生成已取消。",
                                       "metrics": _runtime_metrics(orch, started)})
                        return
                    exc = task.exception()
                    if exc:
                        if isinstance(exc, (TravelDateError, TravelIntentError)):
                            message = str(exc)
                        else:
                            from orchestrator_llm import GenerationStageTimeout
                            message = str(exc) if isinstance(exc, GenerationStageTimeout) else "生成失败，请检查模型服务配置后重试"
                        yield _ndjson({"type": "error", "message": message,
                                       "metrics": _runtime_metrics(orch, started)})
                    else:
                        guide = task.result()
                        await asyncio.to_thread(_store_cache, cache_key, guide)
                        await _record_guide_history(guide)
                        yield _ndjson({"type": "guide",
                                       "guide": _guide_json(guide)})
                    return
        finally:
            if not getter.done():
                getter.cancel()
            if not task.done():
                task.cancel()
            # Starlette cancels the response task inside its AnyIO task group on
            # ASGI disconnect. Shield this bounded join so a second cancellation
            # cannot interrupt the orchestrator's async SDK/resource cleanup.
            with anyio.move_on_after(
                _STREAM_CLEANUP_TIMEOUT_SECONDS, shield=True
            ) as cleanup_timeout:
                await asyncio.gather(getter, task, return_exceptions=True)
            if cleanup_timeout.cancel_called:
                _logger.warning(
                    "Timed out waiting for disconnected generation cleanup after %.1fs",
                    _STREAM_CLEANUP_TIMEOUT_SECONDS,
                )

    return StreamingResponse(event_gen(), media_type="application/x-ndjson")


@app.get("/api/history")
async def list_guide_history():
    try:
        return {"items": await asyncio.to_thread(guide_history.list)}
    except GuideHistoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@app.get("/api/history/{history_id}")
async def get_guide_history(history_id: str):
    try:
        guide = await asyncio.to_thread(guide_history.get, history_id)
    except GuideHistoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    if guide is None:
        raise HTTPException(status_code=404, detail="攻略历史不存在。")
    return guide


@app.delete("/api/history/{history_id}")
async def delete_guide_history(history_id: str):
    try:
        deleted = await asyncio.to_thread(guide_history.delete, history_id)
    except GuideHistoryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    if not deleted:
        raise HTTPException(status_code=404, detail="攻略历史不存在。")
    return {"deleted": True}


@app.get("/api/cache")
async def cache_status():
    """Report how many short-lived results are cached; never exposes guide content."""
    try:
        return await asyncio.to_thread(guide_cache.status)
    except Exception:
        raise HTTPException(status_code=503, detail="本地缓存状态无法读取。") from None


@app.delete("/api/cache")
async def clear_cache():
    try:
        removed = await asyncio.to_thread(guide_cache.clear)
    except Exception:
        raise HTTPException(status_code=503, detail="本地缓存清理失败。") from None
    return {"removed": removed}


@app.post("/api/export/markdown")
async def export_guide_markdown(guide: TravelGuide):
    markdown = GuideGenerator().to_markdown(guide)
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="shanhe-travel-guide.md"'},
    )


@app.get("/api/config")
async def api_config():
    """只返回浏览器 JS SDK 必需的 Key 与 JS 安全码，不包含 Web 服务凭据。"""
    try:
        amap = amap_settings.resolve(default_config.amap)
    except AmapSettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return {"amap_key": amap.js_key, "amap_security_code": amap.js_security_code}


@app.get("/api/amap-settings")
async def get_amap_settings():
    """Return configuration presence only; credential values are never echoed."""
    try:
        return amap_settings.public_status(default_config.amap)
    except AmapSettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@app.put("/api/amap-settings")
async def put_amap_settings(payload: AmapSettingsPayload):
    try:
        amap_settings.save(payload)
        _invalidate_guide_cache_after_map_change()
        return amap_settings.public_status(default_config.amap)
    except AmapSettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@app.delete("/api/amap-settings")
async def delete_amap_settings():
    try:
        amap_settings.clear()
        _invalidate_guide_cache_after_map_change()
        return amap_settings.public_status(default_config.amap)
    except AmapSettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@app.get("/api/deepseek-search-settings")
async def get_deepseek_search_settings():
    """Expose opt-in state and credential presence only; never return a key."""
    try:
        return deepseek_search_settings.public_status(model_profiles)
    except DeepSeekSearchSettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@app.put("/api/deepseek-search-settings")
async def put_deepseek_search_settings(payload: DeepSeekSearchSettingsPayload):
    try:
        deepseek_search_settings.save(payload)
        return deepseek_search_settings.public_status(model_profiles)
    except DeepSeekSearchSettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@app.delete("/api/deepseek-search-settings")
async def delete_deepseek_search_settings():
    try:
        deepseek_search_settings.clear()
        return deepseek_search_settings.public_status(model_profiles)
    except DeepSeekSearchSettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@app.get("/api/model-profiles")
async def list_model_profiles():
    try:
        return {
            "profiles": model_profiles.list_profiles(),
            "default_profile_id": model_profiles.default_profile_id(),
            "credential_store_available": model_profiles.credential_store_available,
        }
    except ProfileStoreError as exc:
        raise _profile_error(exc) from None


@app.post("/api/model-profiles")
async def create_model_profile(payload: ProfilePayload):
    try:
        return model_profiles.create(payload)
    except ValidationError as exc:
        raise _profile_error(exc) from None
    except ProfileStoreError as exc:
        raise _profile_error(exc) from None


@app.put("/api/model-profiles/{profile_id}")
async def update_model_profile(profile_id: str, payload: ProfilePayload):
    try:
        return model_profiles.update(profile_id, payload)
    except ValidationError as exc:
        raise _profile_error(exc) from None
    except ProfileStoreError as exc:
        raise _profile_error(exc) from None


@app.put("/api/model-profiles/{profile_id}/default")
async def set_default_model_profile(profile_id: str):
    try:
        model_profiles.set_default(profile_id)
        return {"default_profile_id": profile_id}
    except ProfileStoreError as exc:
        raise _profile_error(exc) from None


@app.delete("/api/model-profiles/{profile_id}/credential")
async def clear_model_profile_credential(profile_id: str):
    try:
        return model_profiles.clear_credential(profile_id)
    except ProfileStoreError as exc:
        raise _profile_error(exc) from None


@app.delete("/api/model-profiles/{profile_id}")
async def delete_model_profile(profile_id: str):
    try:
        model_profiles.delete(profile_id)
        return {"deleted": True}
    except ProfileStoreError as exc:
        raise _profile_error(exc) from None


async def _diagnose_model_profile(profile_id: str, structured: bool) -> dict:
    """Test exactly the requested saved profile; never select or fall back."""
    try:
        selected = resolve_model_config(profile_id, model_profiles)
    except ModelProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ProfileStoreError as exc:
        raise _profile_error(exc) from None

    # Keep explicit diagnostics short and inexpensive. Temperature is omitted so
    # models that reject sampling parameters can still be tested.
    config = selected.model_copy(update={
        "temperature": None,
        "timeout": min(selected.timeout, 20.0),
        "max_retries": 0,
        "max_tokens": min(selected.max_tokens, 128),
    })
    client = None
    try:
        client = get_llm(config)
        if structured:
            result = await client.chat_structured(
                "你正在执行一项结构化输出能力诊断。",
                '请返回 result 字段为 "ok" 的 JSON 对象。',
                schema=DiagnosticProbe,
            )
            if isinstance(result, dict):
                DiagnosticProbe.model_validate(result)
            elif not isinstance(result, DiagnosticProbe):
                DiagnosticProbe.model_validate(result)
        else:
            response = await client.chat("你正在执行连接诊断。", "请仅回复 OK。")
            if not isinstance(response, str) or not response.strip():
                return {
                    "ok": False,
                    "category": "unknown",
                    "message": "接口未返回有效文本，连接测试未通过。",
                }
    except Exception as exc:
        category = classify_model_error(exc, structured=structured)
        if isinstance(exc, IntegrationDependencyError):
            message = str(exc)  # This is a fixed local message, never provider data.
        else:
            message = safe_model_error_message(category)
        return {"ok": False, "category": category, "message": message}
    finally:
        close = getattr(client, "aclose", None)
        if callable(close):
            with anyio.CancelScope(shield=True):
                try:
                    await close()
                except Exception as exc:
                    _logger.warning("Diagnostic model client close failed (%s)", type(exc).__name__)

    return {
        "ok": True,
        "category": "success",
        "message": "本次结构化能力调用成功。" if structured else "本次连接调用成功。",
    }


@app.post("/api/model-profiles/{profile_id}/diagnostics/connection")
async def diagnose_model_profile_connection(profile_id: str):
    return await _diagnose_model_profile(profile_id, structured=False)


@app.post("/api/model-profiles/{profile_id}/diagnostics/structured")
async def diagnose_model_profile_structured(profile_id: str):
    return await _diagnose_model_profile(profile_id, structured=True)


@app.get("/")
async def index():
    return FileResponse(frontend / "index.html")


app.mount("/css", StaticFiles(directory=frontend / "css"), name="css")
app.mount("/js", StaticFiles(directory=frontend / "js"), name="js")
app.mount("/static/photos", StaticFiles(directory=photo_dir), name="photos")

if __name__ == "__main__":
    import uvicorn
    print("Shanhe Travel Guide")
    print("  http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
