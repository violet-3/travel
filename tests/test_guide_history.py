"""Offline checks for atomic local guide history and API failure handling."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app
from models.schemas import TravelGuide
from tools.guide_history import GuideHistoryError, GuideHistoryStore


class GuideHistoryStoreTests(unittest.TestCase):
    def test_saved_guide_survives_store_recreation_without_credentials(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-guide-history-") as folder:
            path = Path(folder) / "guide-history.json"
            guide = {
                "title": "安阳漫游",
                "destinations": ["安阳"],
                "days": 3,
                "request": {"travelers": 2},
            }
            history_id = GuideHistoryStore(path).save(guide)

            reopened = GuideHistoryStore(path)
            self.assertEqual(reopened.get(history_id), guide)
            self.assertEqual(reopened.list()[0]["title"], "安阳漫游")
            persisted = path.read_text(encoding="utf-8")
            self.assertNotIn("api_key", persisted)
            self.assertNotIn("web_service_secret", persisted)

    def test_malformed_day_rows_are_skipped_instead_of_breaking_history_list(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-guide-history-bad-row-") as folder:
            path = Path(folder) / "guide-history.json"
            path.write_text(json.dumps({
                "version": 1,
                "items": [{
                    "id": "a" * 32,
                    "saved_at": "2026-10-20T00:00:00+00:00",
                    "guide": {"title": "坏行", "days": "三天", "destinations": ["安阳"]},
                }],
            }), encoding="utf-8")

            self.assertEqual(GuideHistoryStore(path).list(), [])

    def test_lock_directory_errors_become_guide_history_error(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-guide-history-parent-") as folder:
            parent_file = Path(folder) / "not-a-directory"
            parent_file.write_text("file", encoding="utf-8")
            store = GuideHistoryStore(parent_file / "guide-history.json")

            with self.assertRaises(GuideHistoryError):
                store.save({"title": "安阳漫游", "days": 3})

    def test_failed_atomic_replace_keeps_previous_history_usable(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-guide-history-replace-") as folder:
            path = Path(folder) / "guide-history.json"
            store = GuideHistoryStore(path)
            history_id = store.save({"title": "原攻略", "days": 3})

            with patch("tools.guide_history.os.replace", side_effect=PermissionError("denied")):
                with self.assertRaises(GuideHistoryError):
                    store.save({"title": "新攻略", "days": 4})

            self.assertEqual(store.get(history_id)["title"], "原攻略")

    def test_history_write_failure_does_not_fail_generated_guide(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-guide-history-fallback-") as folder:
            parent_file = Path(folder) / "not-a-directory"
            parent_file.write_text("file", encoding="utf-8")
            bad_store = GuideHistoryStore(parent_file / "guide-history.json")
            guide = TravelGuide(title="安阳漫游", days=3)

            with patch.object(app, "guide_history", bad_store):
                saved = asyncio.run(app._record_guide_history(guide))

            self.assertFalse(saved)
            self.assertFalse(guide.history_saved)
            self.assertIsNone(guide.history_id)

    def test_history_detail_api_returns_service_unavailable_for_storage_failure(self):
        client = TestClient(app.app, base_url="http://127.0.0.1")
        with patch.object(app.guide_history, "get", side_effect=GuideHistoryError("本地历史不可读")):
            response = client.get("/api/history/" + "a" * 32)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "本地历史不可读")


if __name__ == "__main__":
    unittest.main()
