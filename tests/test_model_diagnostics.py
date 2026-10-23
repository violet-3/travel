"""Local API diagnostics tests; all provider calls are mocked."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app
from tools.model_profiles import ModelProfileStore, ProfilePayload


class MemoryCredentials:
    available = True

    def __init__(self):
        self.values = {}

    def get(self, profile_id):
        return self.values.get(profile_id)

    def set(self, profile_id, secret):
        self.values[profile_id] = secret

    def delete(self, profile_id):
        self.values.pop(profile_id, None)


class ModelDiagnosticsApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shanhe-diagnostic-api-")
        self.store = ModelProfileStore(Path(self.temp.name) / "profiles.json", MemoryCredentials())
        self.client = TestClient(app.app)
        self.headers = {"Host": "127.0.0.1:8000", "Origin": "http://127.0.0.1:8000"}

    def tearDown(self):
        self.temp.cleanup()

    def test_profile_load_and_save_do_not_construct_models(self):
        with patch.object(app, "model_profiles", self.store), patch.object(app, "get_llm") as get_llm:
            created = self.client.post("/api/model-profiles", headers=self.headers, json={
                "name": "单配置", "provider": "moonshot", "protocol": "openai_compatible",
                "base_url": "https://api.moonshot.cn/v1", "model": "manual-model-id",
                "api_key": "offline-secret", "temperature": None,
            })
            self.assertEqual(created.status_code, 200, created.text)
            profile_id = created.json()["profile_id"]
            listed = self.client.get("/api/model-profiles", headers={"Host": "127.0.0.1:8000"})
            self.assertEqual(listed.status_code, 200, listed.text)
            self.assertEqual(listed.json()["profiles"][0]["model"], "manual-model-id")
            updated = self.client.put("/api/model-profiles/" + profile_id, headers=self.headers,
                                      json={"name": "单配置已编辑", "provider": "moonshot",
                                            "protocol": "openai_compatible",
                                            "base_url": "https://api.moonshot.cn/v1/custom-path",
                                            "model": "manual-model-id", "temperature": None,
                                            "api_key": ""})
            self.assertEqual(updated.status_code, 200, updated.text)
            get_llm.assert_not_called()

    def test_explicit_diagnostics_call_only_the_named_profile_and_classify_errors_safely(self):
        class FakeModelClient:
            async def chat(self, *_args, **_kwargs):
                return "OK"

            async def chat_structured(self, *_args, **_kwargs):
                return app.DiagnosticProbe(result="ok")

        with patch.object(app, "model_profiles", self.store):
            created = self.store.create(ProfilePayload(
                name="明确选择的配置", provider="deepseek", protocol="openai_compatible",
                base_url="https://api.deepseek.com", model="hand-entered-model",
                api_key="offline-secret", temperature=None,
            ))
            profile_id = created["profile_id"]
            with patch.object(app, "get_llm", return_value=FakeModelClient()) as get_llm:
                connection = self.client.post(
                    f"/api/model-profiles/{profile_id}/diagnostics/connection", headers=self.headers)
                self.assertEqual(connection.status_code, 200, connection.text)
                self.assertTrue(connection.json()["ok"])
                structured = self.client.post(
                    f"/api/model-profiles/{profile_id}/diagnostics/structured", headers=self.headers)
                self.assertEqual(structured.status_code, 200, structured.text)
                self.assertTrue(structured.json()["ok"])
                self.assertEqual(get_llm.call_count, 2)
                for call in get_llm.call_args_list:
                    self.assertEqual(call.args[0].profile_id, profile_id)
                    self.assertEqual(call.args[0].max_retries, 0)
                    self.assertIsNone(call.args[0].temperature)
                listed_after_test = self.client.get(
                    "/api/model-profiles", headers={"Host": "127.0.0.1:8000"})
                self.assertEqual(listed_after_test.status_code, 200)
                self.assertNotIn("diagnostic", listed_after_test.text.lower())

    def test_upstream_error_response_uses_fixed_safe_category_message(self):
        class Unauthorized(Exception):
            status_code = 401

        class FakeModelClient:
            async def chat(self, *_args, **_kwargs):
                raise Unauthorized("response leaked offline-secret")

        with patch.object(app, "model_profiles", self.store):
            created = self.store.create(ProfilePayload(
                name="错误分类", base_url="https://provider.example/v1",
                api_key="offline-secret",
            ))
            with patch.object(app, "get_llm", return_value=FakeModelClient()):
                result = self.client.post(
                    f"/api/model-profiles/{created['profile_id']}/diagnostics/connection",
                    headers=self.headers)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["category"], "authentication")
            self.assertNotIn("offline-secret", result.text)
            self.assertNotIn("response leaked", result.text)

    def test_empty_connection_reply_is_not_reported_as_success(self):
        class EmptyReplyClient:
            async def chat(self, *_args, **_kwargs):
                return "  \n"

        with patch.object(app, "model_profiles", self.store):
            created = self.store.create(ProfilePayload(
                name="空回复", base_url="https://provider.example/v1",
                api_key="offline-secret",
            ))
            with patch.object(app, "get_llm", return_value=EmptyReplyClient()):
                result = self.client.post(
                    f"/api/model-profiles/{created['profile_id']}/diagnostics/connection",
                    headers=self.headers)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertFalse(result.json()["ok"])
            self.assertEqual(result.json()["category"], "unknown")
            self.assertIn("未返回有效文本", result.json()["message"])


class ModelDiagnosticsCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_diagnostic_client_is_closed_after_success_and_failure(self):
        from config import ModelConfig

        success_client = type("Client", (), {})()
        success_client.chat = AsyncMock(return_value="OK")
        success_client.aclose = AsyncMock()
        with patch.object(app, "resolve_model_config", return_value=ModelConfig()), \
                patch.object(app, "get_llm", return_value=success_client):
            result = await app._diagnose_model_profile("profile-id", structured=False)
        self.assertTrue(result["ok"])
        success_client.aclose.assert_awaited_once()

        failed_client = type("Client", (), {})()
        failed_client.chat = AsyncMock(side_effect=RuntimeError("provider secret detail"))
        failed_client.aclose = AsyncMock()
        with patch.object(app, "resolve_model_config", return_value=ModelConfig()), \
                patch.object(app, "get_llm", return_value=failed_client):
            result = await app._diagnose_model_profile("profile-id", structured=False)
        self.assertFalse(result["ok"])
        failed_client.aclose.assert_awaited_once()

    async def test_diagnostic_client_is_closed_when_request_is_cancelled(self):
        from config import ModelConfig

        class BlockingClient:
            def __init__(self):
                self.started = asyncio.Event()
                self.closed = asyncio.Event()

            async def chat(self, *_args, **_kwargs):
                self.started.set()
                await asyncio.Event().wait()

            async def aclose(self):
                self.closed.set()

        client = BlockingClient()
        with patch.object(app, "resolve_model_config", return_value=ModelConfig()), \
                patch.object(app, "get_llm", return_value=client):
            task = asyncio.create_task(app._diagnose_model_profile("profile-id", structured=False))
            await client.started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertTrue(client.closed.is_set())


if __name__ == "__main__":
    unittest.main()
