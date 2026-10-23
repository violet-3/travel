"""LangChain model adapters and strict structured-output handling."""

import json
import inspect
import threading
import time

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from config import ModelConfig

try:  # Keep the app importable so diagnostics can explain a missing extra.
    from langchain_anthropic import ChatAnthropic
except ImportError:  # pragma: no cover - covered with a missing-dependency mock
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover - covered with a missing-dependency mock
    ChatGoogleGenerativeAI = None


class IntegrationDependencyError(RuntimeError):
    """The selected LangChain provider integration is not installed."""


class StructuredOutputConfigurationError(ValueError):
    """The configured structured-output method does not fit its protocol."""


class _UsageCaptureHandler(BaseCallbackHandler):
    """Collect provider-reported token counts without retaining prompts or replies."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.has_input = False
        self.has_output = False
        self.has_total = False

    @staticmethod
    def _count(value):
        try:
            parsed = int(value)
            return parsed if parsed >= 0 else None
        except (TypeError, ValueError, OverflowError):
            return None

    def on_llm_end(self, response, **kwargs):
        candidates = []
        for row in getattr(response, "generations", []) or []:
            for generation in row or []:
                message = getattr(generation, "message", None)
                if message is not None:
                    candidates.extend([
                        getattr(message, "usage_metadata", None),
                        (getattr(message, "response_metadata", {}) or {}).get("token_usage"),
                        (getattr(message, "response_metadata", {}) or {}).get("usage"),
                    ])
        output = getattr(response, "llm_output", None) or {}
        candidates.extend([output.get("token_usage"), output.get("usage")])
        for usage in candidates:
            if not isinstance(usage, dict):
                continue
            input_value = usage.get("input_tokens", usage.get("prompt_tokens", usage.get("promptTokenCount")))
            output_value = usage.get("output_tokens", usage.get("completion_tokens", usage.get("candidatesTokenCount")))
            total_value = usage.get("total_tokens", usage.get("totalTokenCount"))
            input_count, output_count, total_count = map(self._count, (input_value, output_value, total_value))
            if input_count is None and output_count is None and total_count is None:
                continue
            if input_count is not None:
                self.input_tokens += input_count
                self.has_input = True
            if output_count is not None:
                self.output_tokens += output_count
                self.has_output = True
            if total_count is not None:
                self.total_tokens += total_count
                self.has_total = True
            elif input_count is not None and output_count is not None:
                self.total_tokens += input_count + output_count
                self.has_total = True
            return


def classify_model_error(exc: Exception, structured: bool = False) -> str:
    """Classify provider failures without exposing their messages to the caller."""
    status = (getattr(exc, "status_code", None) or getattr(exc, "status", None)
              or getattr(exc, "code", None))
    response = getattr(exc, "response", None)
    status = status or getattr(response, "status_code", None)
    try:
        status = int(status) if status is not None else None
    except (TypeError, ValueError):
        status = None

    class_names = " ".join(cls.__name__.lower() for cls in type(exc).__mro__)
    if status in {401, 403}:
        return "authentication"
    if status == 404:
        return "model_not_found"
    if status == 429:
        return "rate_limited"
    if status in {408, 504} or "timeout" in class_names or "timedout" in class_names:
        return "timeout"
    if structured and status in {400, 422}:
        # This text is used only to choose a safe category. It is never returned
        # or logged, because provider exceptions may contain submitted secrets.
        internal_text = str(exc).lower()
        indicators = ("unsupported", "not supported", "json_schema", "tool_choice",
                      "function calling", "structured output", "response_format")
        if any(indicator in internal_text for indicator in indicators):
            return "structured_output_unsupported"
    if structured and isinstance(exc, StructuredOutputConfigurationError):
        return "structured_output_unsupported"
    return "unknown"


def safe_model_error_message(category: str) -> str:
    """Return a fixed, non-sensitive explanation for a diagnostic failure."""
    return {
        "authentication": "鉴权失败：请核对 API Key、账号权限和接口区域。",
        "model_not_found": "模型不存在或当前账号无权调用，请核对模型 ID 与接口地址。",
        "timeout": "请求超时，请核对接口地址和网络后重试。",
        "rate_limited": "请求触发限流，请稍后重试或核对套餐额度。",
        "structured_output_unsupported": "本模型或接口不支持当前结构化输出方式；请明确更换方式后再测试。",
        "unknown": "诊断失败，请检查接口地址、模型名称和配置。",
    }.get(category, "诊断失败，请检查模型配置。")


def _model_kwargs(config: ModelConfig) -> dict:
    kwargs = {
        "model": config.model,
        "timeout": config.timeout,
        "max_retries": config.max_retries,
    }
    if config.temperature is not None:
        kwargs["temperature"] = config.temperature
    if config.protocol == "openai_compatible":
        kwargs.update(
            base_url=config.base_url,
            api_key=config.api_key.get_secret_value(),
            max_tokens=config.max_tokens,
        )
    elif config.protocol == "anthropic":
        if ChatAnthropic is None:
            raise IntegrationDependencyError("缺少 langchain-anthropic，请安装项目依赖后重试")
        kwargs.update(
            base_url=config.base_url,
            api_key=config.api_key.get_secret_value(),
            max_tokens=config.max_tokens,
        )
    elif config.protocol == "google_genai":
        if ChatGoogleGenerativeAI is None:
            raise IntegrationDependencyError("缺少 langchain-google-genai，请安装项目依赖后重试")
        kwargs.update(
            client_options=config.base_url,
            api_key=config.api_key.get_secret_value(),
            max_tokens=config.max_tokens,
            request_timeout=config.timeout,
            # Google GenAI's retries field is total attempts, and zero means
            # its own default retry count. Map project retries to attempts.
            retries=max(1, config.max_retries + 1),
        )
    else:  # ModelConfig validates this; keep the factory fail-closed.
        raise ValueError("不支持的模型协议")
    return kwargs


def make_chat_model(config: ModelConfig):
    """Create one LangChain chat model without issuing a network request."""
    if config.protocol == "openai_compatible":
        return ChatOpenAI(**_model_kwargs(config))
    if config.protocol == "anthropic":
        return ChatAnthropic(**_model_kwargs(config))
    if config.protocol == "google_genai":
        return ChatGoogleGenerativeAI(**_model_kwargs(config))
    raise ValueError("不支持的模型协议")


class LLMClient:
    """Use LangChain integrations for OpenAI-compatible, Anthropic, and Gemini APIs."""

    def __init__(self, config: ModelConfig | None = None):
        self.cfg = config or ModelConfig.from_env()
        self.llm = make_chat_model(self.cfg)
        self._metrics_lock = threading.Lock()
        self._metrics = {
            "requests": 0, "elapsed_ms": 0.0, "usage_known_calls": 0,
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "has_input": False, "has_output": False, "has_total": False,
        }

    def _record_invocation(self, capture: _UsageCaptureHandler, elapsed_ms: float):
        if not hasattr(self, "_metrics_lock"):
            self._metrics_lock = threading.Lock()
            self._metrics = {
                "requests": 0, "elapsed_ms": 0.0, "usage_known_calls": 0,
                "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
                "has_input": False, "has_output": False, "has_total": False,
            }
        with self._metrics_lock:
            metrics = self._metrics
            metrics["requests"] += 1
            metrics["elapsed_ms"] += elapsed_ms
            known = capture.has_input or capture.has_output or capture.has_total
            if known:
                metrics["usage_known_calls"] += 1
            for field in ("input_tokens", "output_tokens", "total_tokens"):
                has_field = getattr(capture, "has_" + field.removesuffix("_tokens"), False)
                if has_field:
                    metrics[field] += getattr(capture, field)
                    metrics["has_" + field.removesuffix("_tokens")] = True

    async def _ainvoke(self, runnable, values):
        capture = _UsageCaptureHandler()
        started = time.perf_counter()
        try:
            return await runnable.ainvoke(values, config={"callbacks": [capture]})
        finally:
            self._record_invocation(capture, (time.perf_counter() - started) * 1000)

    def metrics_snapshot(self) -> dict:
        if not hasattr(self, "_metrics_lock"):
            return {
                "requests": 0, "elapsed_ms": 0, "input_tokens": None,
                "output_tokens": None, "total_tokens": None,
                "usage_known_calls": 0, "usage_unknown_calls": 0,
            }
        with self._metrics_lock:
            metrics = dict(self._metrics)
        requests = metrics["requests"]
        return {
            "requests": requests,
            "elapsed_ms": round(metrics["elapsed_ms"]),
            "input_tokens": metrics["input_tokens"] if metrics["has_input"] else None,
            "output_tokens": metrics["output_tokens"] if metrics["has_output"] else None,
            "total_tokens": metrics["total_tokens"] if metrics["has_total"] else None,
            "usage_known_calls": metrics["usage_known_calls"],
            "usage_unknown_calls": max(0, requests - metrics["usage_known_calls"]),
        }

    async def aclose(self):
        """Close request-scoped async/sync SDK clients when an adapter exposes them."""
        seen = set()
        model_state = getattr(self.llm, "__dict__", {})
        clients = [model_state.get(name) for name in (
            "async_client", "root_async_client", "root_client", "_async_client",
            "_client", "client",
        )]
        provider_client = model_state.get("client")
        if provider_client is not None:
            try:
                clients.append(getattr(provider_client, "aio", None))
            except Exception:
                pass
        for client in clients:
            if client is None or id(client) in seen:
                continue
            seen.add(id(client))
            close = getattr(client, "aclose", None) or getattr(client, "close", None)
            if not callable(close):
                continue
            try:
                result = close()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                # A close error must not replace the generation result/error.
                continue

    def _prompt(self):
        return ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"), ("human", "{user_prompt}")
        ])

    def _with_model(self, model: str | None):
        return self.llm.bind(model=model) if model else self.llm

    async def chat(self, system_prompt: str, user_prompt: str,
                   model: str | None = None, temperature: float | None = None) -> str:
        llm = self._with_model(model)
        if temperature is not None:
            llm = llm.bind(temperature=temperature)
        response = await self._ainvoke(self._prompt() | llm, {
            "system_prompt": system_prompt, "user_prompt": user_prompt
        })
        content = response.content
        if isinstance(content, str):
            return content
        # Provider-native adapters may return standardized content blocks.
        text_parts = [part.get("text", "") for part in content
                      if isinstance(part, dict) and part.get("type") == "text"]
        return "".join(text_parts) if text_parts else str(content)

    async def chat_structured(self, system_prompt: str, user_prompt: str,
                              model: str | None = None, schema=None):
        """Invoke an explicitly configured structured-output strategy."""
        llm = self._with_model(model)
        method = self.cfg.structured_output_method

        if method == "strict_json_text":
            if schema is None or not callable(getattr(schema, "model_json_schema", None)) or not callable(getattr(schema, "model_validate", None)):
                raise StructuredOutputConfigurationError(
                    "严格 JSON 文本方式需要 Pydantic 模型作为 schema"
                )
            schema_text = json.dumps(schema.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
            strict_system = (
                system_prompt
                + "\n\n请按下面的 JSON Schema 返回一个完整 JSON 对象。"
                + "只输出 JSON，不要代码围栏、前后说明或额外字段。\n"
                + schema_text
            )
            raw = await self._ainvoke(self._prompt() | llm | StrOutputParser(), {
                "system_prompt": strict_system,
                "user_prompt": user_prompt,
            })
            try:
                decoded = json.loads(raw)
                return schema.model_validate(decoded)
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
                # Never repair, truncate, or otherwise turn incomplete JSON into success.
                raise ValueError("模型返回内容未通过严格 JSON 与 schema 校验") from None

        if method == "json_mode" and self.cfg.protocol != "openai_compatible":
            raise StructuredOutputConfigurationError(
                "当前原生协议不支持 JSON mode；请显式选择 JSON Schema、Function calling 或严格 JSON 文本"
            )

        if schema:
            parser_or_model = llm.with_structured_output(schema, method=method)
        else:
            parser_or_model = llm | JsonOutputParser()
        chain = self._prompt() | parser_or_model
        return await self._ainvoke(chain, {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt + "\n\n请只返回符合要求的结构化结果，不要附加解释。",
        })


def get_llm(config: ModelConfig | None = None) -> LLMClient:
    """Create a fresh client; never retain process-wide mutable model state."""
    return LLMClient(config)
