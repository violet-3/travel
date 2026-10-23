"""Offline tests for LangChain provider adapters and diagnostics."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from config import ModelConfig
from tools import llm_client
from tools.llm_client import (
    IntegrationDependencyError,
    LLMClient,
    _UsageCaptureHandler,
    classify_model_error,
    safe_model_error_message,
)
from tools.model_profiles import ModelProfileStore, ProfilePayload


class TinySchema(BaseModel):
    result: str


class ModelAdapterTests(unittest.TestCase):
    def test_real_chatopenai_root_clients_are_closed_without_network(self):
        client = LLMClient(ModelConfig(
            api_key="offline-fake", base_url="http://127.0.0.1:9/v1",
            timeout=1, max_retries=0,
        ))
        sync_root = client.llm.root_client
        async_root = client.llm.root_async_client
        self.assertFalse(sync_root.is_closed())
        self.assertFalse(async_root.is_closed())

        asyncio.run(client.aclose())

        self.assertTrue(sync_root.is_closed())
        self.assertTrue(async_root.is_closed())

    def test_provider_usage_is_reported_and_missing_usage_stays_unknown(self):
        client = LLMClient.__new__(LLMClient)
        capture = _UsageCaptureHandler()
        message = SimpleNamespace(usage_metadata={
            "input_tokens": 12, "output_tokens": 7, "total_tokens": 19,
        }, response_metadata={})
        response = SimpleNamespace(
            generations=[[SimpleNamespace(message=message)]], llm_output={},
        )
        capture.on_llm_end(response)
        client._record_invocation(capture, 25)
        client._record_invocation(_UsageCaptureHandler(), 10)

        metrics = client.metrics_snapshot()
        self.assertEqual(metrics["requests"], 2)
        self.assertEqual(metrics["elapsed_ms"], 35)
        self.assertEqual(metrics["input_tokens"], 12)
        self.assertEqual(metrics["output_tokens"], 7)
        self.assertEqual(metrics["total_tokens"], 19)
        self.assertEqual(metrics["usage_known_calls"], 1)
        self.assertEqual(metrics["usage_unknown_calls"], 1)

    def test_real_native_clients_construct_without_invoking_provider_apis(self):
        if llm_client.ChatAnthropic is None or llm_client.ChatGoogleGenerativeAI is None:
            self.skipTest("optional native LangChain packages are not installed")
        anthropic_client = LLMClient(ModelConfig(
            protocol="anthropic", base_url="https://api.anthropic.com",
            model="claude-sonnet-4-6", api_key="offline-fake",
            temperature=None, max_retries=0, timeout=11, max_tokens=128,
        ))
        gemini_client = LLMClient(ModelConfig(
            protocol="google_genai", base_url="https://generativelanguage.googleapis.com",
            model="gemini-3.8-flash", api_key="offline-fake",
            temperature=None, max_retries=0, timeout=12, max_tokens=256,
        ))
        self.assertEqual(anthropic_client.llm.model, "claude-sonnet-4-6")
        self.assertEqual(gemini_client.llm.base_url, "https://generativelanguage.googleapis.com")
        self.assertEqual(gemini_client.llm.max_output_tokens, 256)
        self.assertEqual(gemini_client.llm.timeout, 12)
        self.assertEqual(gemini_client.llm.max_retries, 1)

    def test_factory_uses_each_langchain_adapter_and_omits_auto_temperature(self):
        cases = [
            ("openai_compatible", "ChatOpenAI", {"base_url", "api_key", "max_tokens"}),
            ("anthropic", "ChatAnthropic", {"base_url", "api_key", "max_tokens"}),
            ("google_genai", "ChatGoogleGenerativeAI", {"client_options", "api_key", "max_tokens", "request_timeout", "retries"}),
        ]
        for protocol, adapter_name, required in cases:
            with self.subTest(protocol=protocol):
                config = ModelConfig(protocol=protocol, temperature=None, api_key="adapter-key")
                with patch.object(llm_client, adapter_name) as adapter:
                    client = LLMClient(config)
                kwargs = adapter.call_args.kwargs
                self.assertTrue(required.issubset(kwargs))
                self.assertNotIn("temperature", kwargs)
                self.assertEqual(kwargs["api_key"], "adapter-key")
                self.assertIs(client.cfg, config)

    def test_missing_provider_package_is_reported_without_network(self):
        config = ModelConfig(protocol="anthropic")
        with patch.object(llm_client, "ChatAnthropic", None):
            with self.assertRaises(IntegrationDependencyError) as caught:
                LLMClient(config)
        self.assertIn("langchain-anthropic", str(caught.exception))

    def test_native_protocols_pass_selected_schema_method_to_langchain(self):
        class FakeStructuredRunnable(RunnableLambda):
            def __init__(self):
                super().__init__(lambda _value: None)
                self.method = None

            def with_structured_output(self, schema, method):
                self.method = method
                return RunnableLambda(lambda _value: schema(result="ok"))

        for protocol, method in (("openai_compatible", "json_schema"),
                                 ("anthropic", "function_calling"),
                                 ("google_genai", "json_schema")):
            with self.subTest(protocol=protocol):
                model = FakeStructuredRunnable()
                client = LLMClient.__new__(LLMClient)
                client.cfg = ModelConfig(protocol=protocol, structured_output_method=method)
                client.llm = model
                result = asyncio.run(client.chat_structured("system", "user", schema=TinySchema))
                self.assertEqual(result, TinySchema(result="ok"))
                self.assertEqual(model.method, method)

    def test_strict_json_text_passes_schema_and_rejects_non_json_or_invalid_shape(self):
        seen = []

        async def run(raw):
            client = LLMClient.__new__(LLMClient)
            client.cfg = ModelConfig(structured_output_method="strict_json_text")
            def capture(value):
                seen.extend(message.content for message in value.to_messages())
                return raw
            client.llm = RunnableLambda(capture)
            return await client.chat_structured("system", "user", schema=TinySchema)

        result = asyncio.run(run('{"result":"ok"}'))
        self.assertEqual(result, TinySchema(result="ok"))
        self.assertTrue(any('"result"' in str(content) for content in seen))
        for invalid in ('```json\n{"result":"ok"}\n```', '{"other":"no"', '{"other":"no"}'):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "严格 JSON"):
                    asyncio.run(run(invalid))

    def test_classifies_common_provider_errors_without_returning_raw_text(self):
        class ProviderError(Exception):
            def __init__(self, status, message="private-upstream-key"):
                super().__init__(message)
                self.status_code = status

        class GoogleProviderError(Exception):
            def __init__(self, code):
                self.code = code

        cases = [
            (ProviderError(401), False, "authentication"),
            (ProviderError(404), False, "model_not_found"),
            (ProviderError(429), False, "rate_limited"),
            (GoogleProviderError(429), False, "rate_limited"),
            (GoogleProviderError(504), False, "timeout"),
            (TimeoutError("private-upstream-key"), False, "timeout"),
            (ProviderError(400, "json_schema unsupported private-upstream-key"), True,
             "structured_output_unsupported"),
            (ProviderError(500), False, "unknown"),
        ]
        for error, structured, expected in cases:
            with self.subTest(category=expected):
                category = classify_model_error(error, structured)
                self.assertEqual(category, expected)
                self.assertNotIn("private-upstream-key", safe_model_error_message(category))

    def test_old_profile_metadata_loads_with_safe_protocol_defaults(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-profile-migration-") as folder:
            path = Path(folder) / "model-profiles.json"
            path.write_text(json.dumps({
                "version": 1,
                "default_profile_id": "old-profile",
                "profiles": [{
                    "profile_id": "old-profile", "name": "旧配置",
                    "base_url": "https://legacy.example/v1", "model": "legacy-model",
                    "temperature": 0.5, "timeout": 30.0, "max_retries": 1,
                    "max_tokens": 1024, "structured_output_method": "function_calling",
                    "has_saved_key": False, "session_only": False,
                }],
            }), encoding="utf-8")
            store = ModelProfileStore(path, credentials=None)
            public = store.list_profiles()[0]
            self.assertEqual(public["provider"], "custom")
            self.assertEqual(public["protocol"], "openai_compatible")
            self.assertEqual(store.resolve_model_config("old-profile").protocol, "openai_compatible")


if __name__ == "__main__":
    unittest.main()
