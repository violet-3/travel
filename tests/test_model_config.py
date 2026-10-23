"""Offline validation and request-isolation tests for model configuration."""

import asyncio
import os
import unittest
from unittest.mock import patch
from fastapi import HTTPException

# Keep import-time configuration diagnostics and client construction harmless.
os.environ["AMAP_WEATHER_KEY"] = ""
os.environ["AMAP_JS_API_KEY"] = ""
os.environ["AMAP_SECRET"] = ""
os.environ["TRAVEL_LLM_URL"] = "http://127.0.0.1:9/v1"
os.environ["TRAVEL_LLM_KEY"] = "offline-test-key"
os.environ["TRAVEL_LLM_MODEL"] = "offline-test-model"

from config import (  # noqa: E402
    ModelConfig,
    ModelConfigError,
    ModelProfileNotFoundError,
    resolve_model_config,
)
from models.schemas import TravelIntent  # noqa: E402
from orchestrator_llm import TravelOrchestrator  # noqa: E402
from tools.llm_client import LLMClient  # noqa: E402


class ModelConfigTests(unittest.TestCase):
    def test_legacy_environment_variables_create_validated_snapshot(self):
        env = {
            "TRAVEL_LLM_URL": "https://model.example/v1/",
            "TRAVEL_LLM_KEY": "legacy-env-key",
            "TRAVEL_LLM_MODEL": "legacy-model",
            "TRAVEL_LLM_TEMPERATURE": "0.25",
            "TRAVEL_LLM_TIMEOUT": "25",
            "TRAVEL_LLM_MAX_RETRIES": "2",
            "TRAVEL_LLM_MAX_TOKENS": "4096",
            "TRAVEL_LLM_STRUCTURED_OUTPUT_METHOD": "json_schema",
        }
        with patch.dict(os.environ, env, clear=False):
            config = ModelConfig.from_env()

        self.assertEqual(config.base_url, "https://model.example/v1")
        self.assertEqual(config.api_key.get_secret_value(), "legacy-env-key")
        self.assertEqual(config.model, "legacy-model")
        self.assertEqual(config.temperature, 0.25)
        self.assertEqual(config.timeout, 25)
        self.assertEqual(config.max_retries, 2)
        self.assertEqual(config.max_tokens, 4096)
        self.assertEqual(config.structured_output_method, "json_schema")

    def test_environment_selects_native_provider_protocol_and_auto_temperature(self):
        env = {
            "TRAVEL_LLM_PROVIDER": "anthropic",
            "TRAVEL_LLM_PROTOCOL": "anthropic",
            "TRAVEL_LLM_TEMPERATURE": "auto",
            "TRAVEL_LLM_STRUCTURED_OUTPUT_METHOD": "strict_json_text",
        }
        with patch.dict(os.environ, env, clear=False):
            config = ModelConfig.from_env()
        self.assertEqual(config.provider, "anthropic")
        self.assertEqual(config.protocol, "anthropic")
        self.assertIsNone(config.temperature)
        self.assertEqual(config.structured_output_method, "strict_json_text")

    def test_config_is_immutable_and_secret_is_never_serialized(self):
        config = ModelConfig(api_key="do-not-disclose-this-key")
        with self.assertRaises(Exception):
            config.model = "changed"

        self.assertNotIn("do-not-disclose-this-key", repr(config))
        self.assertNotIn("do-not-disclose-this-key", str(config))
        self.assertNotIn("api_key", config.model_dump())
        self.assertNotIn("do-not-disclose-this-key", config.model_dump_json())

    def test_invalid_model_configuration_is_rejected(self):
        invalid = [
            {"base_url": "ftp://model.example/v1"},
            {"base_url": "https://user:pass@model.example/v1"},
            {"base_url": "https://model.example/v1?token=secret"},
            {"base_url": "not-a-url"},
            {"model": "  "},
            {"timeout": 0},
            {"timeout": float("inf")},
            {"max_retries": -1},
            {"max_retries": 6},
            {"max_tokens": 0},
            {"max_tokens": 131073},
            {"structured_output_method": "unsupported"},
            {"profile_id": "  "},
        ]
        for override in invalid:
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    ModelConfig(**override)

    def test_invalid_environment_configuration_has_safe_error(self):
        env = {
            "TRAVEL_LLM_URL": "https://model.example/v1",
            "TRAVEL_LLM_KEY": "sensitive-env-key",
            "TRAVEL_LLM_MODEL": "model-a",
            "TRAVEL_LLM_TIMEOUT": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(ModelConfigError) as ctx:
                ModelConfig.from_env()
        self.assertNotIn("sensitive-env-key", str(ctx.exception))
        self.assertIn("timeout", str(ctx.exception))

    def test_named_profile_boundary_is_explicit_until_profile_store_exists(self):
        self.assertIsNone(resolve_model_config().profile_id)
        with self.assertRaises(ModelProfileNotFoundError):
            resolve_model_config("saved-profile-1")

    def test_client_factory_receives_only_the_selected_snapshot(self):
        config = ModelConfig(
            base_url="https://provider.example/v1",
            api_key="factory-test-key",
            model="factory-model",
            timeout=17,
            max_retries=3,
            max_tokens=2048,
            structured_output_method="function_calling",
        )
        with patch("tools.llm_client.ChatOpenAI") as chat_openai:
            client = LLMClient(config)

        self.assertIs(client.cfg, config)
        kwargs = chat_openai.call_args.kwargs
        self.assertEqual(kwargs["base_url"], config.base_url)
        self.assertEqual(kwargs["api_key"], "factory-test-key")
        self.assertEqual(kwargs["model"], "factory-model")
        self.assertEqual(kwargs["timeout"], 17)
        self.assertEqual(kwargs["max_retries"], 3)
        self.assertEqual(kwargs["max_tokens"], 2048)
        self.assertEqual(kwargs["temperature"], 0.5)

    def test_real_client_repr_does_not_disclose_secret(self):
        config = ModelConfig(api_key="client-repr-secret")
        client = LLMClient(config)
        self.assertNotIn("client-repr-secret", repr(client))
        self.assertNotIn("client-repr-secret", repr(client.llm))


class ConcurrentRequestIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_requests_keep_distinct_url_model_and_key(self):
        config_a = ModelConfig(
            profile_id="future-a", base_url="https://a.example/v1",
            api_key="key-a", model="model-a")
        config_b = ModelConfig(
            profile_id="future-b", base_url="https://b.example/v1",
            api_key="key-b", model="model-b")
        request_a = TravelOrchestrator(config_a)
        request_b = TravelOrchestrator(config_b)

        self.assertIs(request_a.intent_parser.llm, request_a.culture_engine.llm)
        self.assertIsNot(request_a.intent_parser.llm, request_b.intent_parser.llm)

        arrived = 0
        both_arrived = asyncio.Event()
        observed = []

        def mock_request(client, destination):
            async def chat_structured(system_prompt, user_prompt, model=None, schema=None):
                nonlocal arrived
                arrived += 1
                if arrived == 2:
                    both_arrived.set()
                await asyncio.wait_for(both_arrived.wait(), timeout=2)
                await asyncio.sleep(0)
                selected = client.cfg
                observed.append((
                    selected.base_url,
                    selected.model,
                    selected.api_key.get_secret_value(),
                ))
                return TravelIntent(destinations=[destination], days=2)
            return chat_structured

        request_a.llm_client.chat_structured = mock_request(request_a.llm_client, "城市甲")
        request_b.llm_client.chat_structured = mock_request(request_b.llm_client, "城市乙")

        task_a = asyncio.create_task(request_a.intent_parser.run("需求 A"))
        task_b = asyncio.create_task(request_b.intent_parser.run("需求 B"))
        await both_arrived.wait()
        # Later environment changes cannot mutate already-resolved request configs.
        with patch.dict(os.environ, {
            "TRAVEL_LLM_URL": "https://changed.example/v1",
            "TRAVEL_LLM_KEY": "changed-key",
            "TRAVEL_LLM_MODEL": "changed-model",
        }, clear=False):
            intents = await asyncio.gather(task_a, task_b)

        self.assertEqual({intent.destinations[0] for intent in intents}, {"城市甲", "城市乙"})
        self.assertCountEqual(observed, [
            ("https://a.example/v1", "model-a", "key-a"),
            ("https://b.example/v1", "model-b", "key-b"),
        ])

    async def test_web_requests_capture_config_at_handler_entry(self):
        import app

        arrived = 0
        both_arrived = asyncio.Event()
        observed = []

        class MockOrchestrator:
            def __init__(self, model_config, amap_config=None, amap_config_warning="", research_config=None):
                self.model_config = model_config

            async def generate(self, query, on_progress=None):
                nonlocal arrived
                arrived += 1
                if arrived == 2:
                    both_arrived.set()
                await asyncio.wait_for(both_arrived.wait(), timeout=2)
                selected = self.model_config
                observed.append((selected.base_url, selected.model,
                                 selected.api_key.get_secret_value()))
                return object()

        env_a = {
            "TRAVEL_LLM_URL": "https://web-a.example/v1",
            "TRAVEL_LLM_KEY": "web-key-a",
            "TRAVEL_LLM_MODEL": "web-model-a",
        }
        env_b = {
            "TRAVEL_LLM_URL": "https://web-b.example/v1",
            "TRAVEL_LLM_KEY": "web-key-b",
            "TRAVEL_LLM_MODEL": "web-model-b",
        }
        with patch("app.TravelOrchestrator", MockOrchestrator), \
                patch.object(app, "amap_settings", type("AmapSettings", (), {"resolve": lambda self, env: env})()), \
                patch("app._guide_json", return_value={"ok": True}):
            with patch.dict(os.environ, env_a, clear=False):
                task_a = asyncio.create_task(app.api_generate(app.GenReq(query="需求 A")))
                await asyncio.sleep(0)
                with patch.dict(os.environ, env_b, clear=False):
                    task_b = asyncio.create_task(app.api_generate(app.GenReq(query="需求 B")))
                    responses = await asyncio.gather(task_a, task_b)

        self.assertEqual(responses, [{"ok": True}, {"ok": True}])
        self.assertCountEqual(observed, [
            ("https://web-a.example/v1", "web-model-a", "web-key-a"),
            ("https://web-b.example/v1", "web-model-b", "web-key-b"),
        ])

    async def test_web_rejects_profile_id_until_profile_store_exists(self):
        import app
        with self.assertRaises(HTTPException) as ctx:
            await app.api_generate(app.GenReq(profile_id="future-profile"))
        self.assertEqual(ctx.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
