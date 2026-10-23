"""Offline profile persistence, credential privacy, and local API boundary tests."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure importing the Web app never inspects a developer's real profile file.
_APP_DATA = tempfile.TemporaryDirectory(prefix="shanhe-app-test-")
os.environ["SHANHE_TRAVEL_DATA_DIR"] = _APP_DATA.name
os.environ["AMAP_WEATHER_KEY"] = ""
os.environ["AMAP_JS_API_KEY"] = ""
os.environ["AMAP_SECRET"] = ""
os.environ["TRAVEL_LLM_URL"] = "http://127.0.0.1:9/v1"
os.environ["TRAVEL_LLM_KEY"] = "offline-test-key"
os.environ["TRAVEL_LLM_MODEL"] = "offline-test-model"

from config import resolve_model_config  # noqa: E402
from tools.model_profiles import (  # noqa: E402
    CredentialStoreUnavailableError,
    ModelProfileStore,
    ProfilePayload,
    ProfileStoreError,
)


class MemoryCredentials:
    def __init__(self, available=True):
        self.available = available
        self.values = {}

    def get(self, profile_id):
        if not self.available:
            raise CredentialStoreUnavailableError("test credential store unavailable")
        return self.values.get(profile_id)

    def set(self, profile_id, secret):
        if not self.available:
            raise CredentialStoreUnavailableError("test credential store unavailable")
        self.values[profile_id] = secret

    def delete(self, profile_id):
        if not self.available:
            raise CredentialStoreUnavailableError("test credential store unavailable")
        self.values.pop(profile_id, None)


def payload(**overrides):
    values = {
        "name": "旅行主模型",
        "base_url": "https://provider.example/v1",
        "model": "travel-model",
        "api_key": "test-model-secret",
    }
    values.update(overrides)
    return ProfilePayload(**values)


class ModelProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shanhe-profile-test-")
        self.path = Path(self.temp.name) / "model-profiles.json"
        self.credentials = MemoryCredentials()
        self.store = ModelProfileStore(self.path, self.credentials)

    def tearDown(self):
        self.temp.cleanup()

    def test_saved_profile_recovers_after_restart_without_exposing_secret(self):
        public = self.store.create(payload(make_default=True))
        profile_id = public["profile_id"]

        self.assertIsInstance(public, dict)
        self.assertTrue(public["has_key"])
        self.assertNotIn("api_key", public)
        self.assertNotIn("test-model-secret", json.dumps(public))
        persisted = self.path.read_text(encoding="utf-8")
        self.assertNotIn("test-model-secret", persisted)
        self.assertNotIn("api_key", persisted)

        restarted = ModelProfileStore(self.path, self.credentials)
        config = restarted.resolve_model_config(profile_id)
        self.assertEqual(config.api_key.get_secret_value(), "test-model-secret")
        self.assertEqual(restarted.default_profile_id(), profile_id)

    def test_session_profile_can_be_edited_with_blank_key_and_stays_session_only(self):
        created = self.store.create(payload(session_only=True, make_default=True))
        profile_id = created["profile_id"]
        edited = self.store.update(profile_id, payload(
            name="临时主模型（已编辑）", api_key="", session_only=True, make_default=True,
        ))

        self.assertIsInstance(edited, dict)
        self.assertTrue(edited["has_key"])
        self.assertTrue(edited["session_only"])
        config = self.store.resolve_model_config(profile_id)
        self.assertEqual(config.api_key.get_secret_value(), "test-model-secret")
        self.assertEqual(config.model, "travel-model")

        restarted = ModelProfileStore(self.path, self.credentials)
        with self.assertRaises(ProfileStoreError):
            restarted.resolve_model_config(profile_id)

    def test_changing_provider_or_url_origin_requires_new_or_cleared_key(self):
        saved = self.store.create(payload())
        profile_id = saved["profile_id"]
        with self.assertRaisesRegex(ProfileStoreError, "重新填写 API Key"):
            self.store.update(profile_id, payload(base_url="https://other.example/v1", api_key=""))
        with self.assertRaisesRegex(ProfileStoreError, "重新填写 API Key"):
            self.store.update(profile_id, payload(provider="deepseek", api_key=""))

        # A path-only change on the same origin deliberately preserves the key.
        edited = self.store.update(profile_id, payload(
            base_url="https://provider.example/custom/v1", api_key="",
        ))
        self.assertTrue(edited["has_key"])
        self.assertEqual(self.store.resolve_model_config(profile_id).api_key.get_secret_value(), "test-model-secret")

        self.store.clear_credential(profile_id)
        updated = self.store.update(profile_id, payload(provider="deepseek", api_key=""))
        self.assertFalse(updated["has_key"])
        self.assertEqual(self.store.resolve_model_config(profile_id).provider, "deepseek")

    def test_default_profile_is_used_and_deletion_clears_default_and_credential(self):
        public = self.store.create(payload(make_default=True))
        profile_id = public["profile_id"]
        resolved = resolve_model_config(profile_store=self.store)
        self.assertEqual(resolved.profile_id, profile_id)
        self.assertEqual(resolved.model, "travel-model")

        self.store.delete(profile_id)
        self.assertIsNone(self.store.default_profile_id())
        self.assertNotIn(profile_id, self.credentials.values)
        self.assertEqual(resolve_model_config(profile_store=self.store).model, "offline-test-model")

    def test_resolved_generation_config_is_a_snapshot_when_profile_changes(self):
        import app

        public = self.store.create(payload(make_default=True))
        profile_id = public["profile_id"]
        with patch.object(app, "model_profiles", self.store):
            first_request = app._request_orchestrator(app.GenReq(profile_id=profile_id))
        self.store.update(profile_id, payload(
            name="旅行主模型", base_url="https://provider.example/v2",
            model="travel-model-v2", api_key="", make_default=True,
        ))

        self.assertEqual(first_request.model_config.model, "travel-model")
        self.assertEqual(first_request.model_config.base_url, "https://provider.example/v1")
        second_request = resolve_model_config(profile_id, self.store)
        self.assertEqual(second_request.model, "travel-model-v2")
        self.assertEqual(second_request.base_url, "https://provider.example/v2")

    def test_explicit_credential_clear_preserves_profile_and_removes_secret(self):
        public = self.store.create(payload())
        profile_id = public["profile_id"]
        cleared = self.store.clear_credential(profile_id)
        self.assertEqual(cleared["profile_id"], profile_id)
        self.assertFalse(cleared["has_key"])
        self.assertIn(profile_id, [row["profile_id"] for row in self.store.list_profiles()])
        self.assertNotIn(profile_id, self.credentials.values)

    def test_storage_failures_roll_back_credentials_metadata_and_default(self):
        original = self.store.create(payload(make_default=True))
        profile_id = original["profile_id"]
        original_default = self.store.default_profile_id()

        with patch.object(self.store, "_persist", side_effect=ProfileStoreError("disk full")):
            with self.assertRaises(ProfileStoreError):
                self.store.create(payload(name="新配置", make_default=True))
        self.assertEqual(len(self.store.list_profiles()), 1)
        self.assertEqual(self.store.default_profile_id(), original_default)
        self.assertEqual(set(self.credentials.values), {profile_id})

        with patch.object(self.store, "_persist", side_effect=ProfileStoreError("disk full")):
            with self.assertRaises(ProfileStoreError):
                self.store.update(profile_id, payload(
                    model="changed-model", api_key="replacement-secret", make_default=False,
                ))
        self.assertEqual(self.store.resolve_model_config(profile_id).model, "travel-model")
        self.assertEqual(self.credentials.values[profile_id], "test-model-secret")
        self.assertEqual(self.store.default_profile_id(), original_default)

        with patch.object(self.store, "_persist", side_effect=ProfileStoreError("disk full")):
            with self.assertRaises(ProfileStoreError):
                self.store.clear_credential(profile_id)
        self.assertTrue(self.store.list_profiles()[0]["has_key"])
        self.assertEqual(self.credentials.values[profile_id], "test-model-secret")
        self.assertEqual(self.store.default_profile_id(), original_default)

        with patch.object(self.store, "_persist", side_effect=ProfileStoreError("disk full")):
            with self.assertRaises(ProfileStoreError):
                self.store.delete(profile_id)
        self.assertEqual(len(self.store.list_profiles()), 1)
        self.assertEqual(self.store.default_profile_id(), original_default)
        self.assertEqual(self.credentials.values[profile_id], "test-model-secret")

    def test_keyring_unavailable_requires_explicit_session_only_for_secrets(self):
        self.credentials.available = False
        with self.assertRaises(CredentialStoreUnavailableError):
            self.store.create(payload())
        self.assertEqual(self.store.list_profiles(), [])

        temporary = self.store.create(payload(session_only=True))
        self.assertTrue(temporary["session_only"])
        self.assertTrue(temporary["has_key"])


class LocalProfileApiTests(unittest.TestCase):
    def test_profile_api_returns_only_safe_metadata_and_rejects_bad_origin(self):
        from fastapi.testclient import TestClient
        import app

        credentials = MemoryCredentials()
        with tempfile.TemporaryDirectory(prefix="shanhe-profile-api-") as temp_dir:
            store = ModelProfileStore(Path(temp_dir) / "model-profiles.json", credentials)
            client = TestClient(app.app)
            local_headers = {
                "Host": "127.0.0.1:8000",
                "Origin": "http://127.0.0.1:8000",
            }
            with patch.object(app, "model_profiles", store):
                denied = client.post(
                    "/api/model-profiles",
                    headers={"Host": "127.0.0.1:8000", "Origin": "https://attacker.example"},
                    json={"name": "阻断请求", "api_key": "must-not-store"},
                )
                self.assertEqual(denied.status_code, 403)

                remote_host = client.get("/api/model-profiles", headers={"Host": "attacker.example"})
                self.assertEqual(remote_host.status_code, 403)

                created = client.post(
                    "/api/model-profiles",
                    headers=local_headers,
                    json={"name": "浏览器配置", "model": "web-model", "api_key": "api-secret-never-return"},
                )
                self.assertEqual(created.status_code, 200, created.text)
                listed = client.get("/api/model-profiles", headers={"Host": "127.0.0.1:8000"})
                self.assertEqual(listed.status_code, 200, listed.text)
                response_text = created.text + listed.text
                self.assertNotIn("api-secret-never-return", response_text)
                self.assertNotIn('"api_key"', response_text)
                self.assertEqual(len(listed.json()["profiles"]), 1)

                secret_marker = "fake-secret-marker"
                invalid_key = client.post(
                    "/api/model-profiles",
                    headers=local_headers,
                    json={"name": "类型错误", "api_key": {"value": secret_marker}},
                )
                self.assertEqual(invalid_key.status_code, 422)
                self.assertNotIn(secret_marker, invalid_key.text)
                self.assertNotIn('"input"', invalid_key.text)

                invalid_url = client.post(
                    "/api/model-profiles",
                    headers=local_headers,
                    json={"name": "无效地址", "base_url": "ftp://invalid.example/v1"},
                )
                self.assertEqual(invalid_url.status_code, 422, invalid_url.text)

                class LeakyFailureOrchestrator:
                    async def generate(self, _query, on_progress=None):
                        raise RuntimeError("upstream echoed fake-secret-marker")

                with patch.object(app, "_request_orchestrator", return_value=LeakyFailureOrchestrator()):
                    failed = client.post("/api/generate", headers=local_headers,
                                         json={"query": "测试", "profile_id": None})
                    streamed = client.post("/api/generate/stream", headers=local_headers,
                                           json={"query": "测试", "profile_id": None})
                self.assertEqual(failed.status_code, 500)
                self.assertNotIn(secret_marker, failed.text)
                self.assertIn("生成失败", failed.text)
                self.assertEqual(streamed.status_code, 200)
                self.assertNotIn(secret_marker, streamed.text)
                self.assertIn('"type": "error"', streamed.text)


if __name__ == "__main__":
    unittest.main()
