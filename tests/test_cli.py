"""Local CLI safety tests; no model or network calls are made."""

import asyncio
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main as cli
from main import _safe_output_path


class CliSavePathTests(unittest.TestCase):
    def test_windows_invalid_characters_are_removed_and_path_stays_under_output(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-cli-") as temp:
            root = Path(temp) / "output"
            target = _safe_output_path(root, "..\\CON:<苏州>?* ", "2026-10-23T09:00:00")
            self.assertEqual(target.parent, root.resolve())
            self.assertIn("苏州", target.name)
            for invalid in '<>:"/\\|?*':
                self.assertNotIn(invalid, target.name)
            self.assertTrue(target.name.endswith("_2026-10-23.md"))

    def test_blank_or_traversal_only_title_has_a_clear_error(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-cli-") as temp:
            for title in ("", "../../", "\\\\"):
                with self.subTest(title=title), self.assertRaisesRegex(ValueError, "标题清理后为空"):
                    _safe_output_path(temp, title, "2026-10-23")

    def test_reserved_windows_device_name_is_prefixed(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-cli-") as temp:
            target = _safe_output_path(temp, "CON", "2026-10-23")
            self.assertTrue(target.name.startswith("_CON_"))

    def test_blank_model_title_returns_nonzero_and_readable_error(self):
        class FakeOrchestrator:
            compiler = SimpleNamespace(to_markdown=lambda _guide: "# travel")

            async def generate(self, _query, on_progress=None):
                return SimpleNamespace(title="../\\", generated_at="2026-10-23")

        with tempfile.TemporaryDirectory(prefix="shanhe-cli-") as temp, \
                patch("config.resolve_model_config"), \
                patch("config.default_config.output_dir", temp), \
                patch("orchestrator_llm.TravelOrchestrator", return_value=FakeOrchestrator()):
            output = io.StringIO()
            with redirect_stdout(output):
                result = asyncio.run(cli.main(["安阳三日", "--save"]))

        self.assertEqual(result, 1)
        self.assertIn("标题清理后为空", output.getvalue())
        self.assertFalse(Path(temp).exists())

    def test_missing_cli_model_configuration_explains_session_only_boundary(self):
        from config import ModelConfig

        with patch.dict(os.environ, {}, clear=True), \
                patch("tools.model_profiles.ModelProfileStore"), \
                patch("config.resolve_model_config", return_value=ModelConfig()):
            output = io.StringIO()
            with redirect_stdout(output):
                result = asyncio.run(cli.main(["安阳三日"]))

        self.assertEqual(result, 1)
        self.assertIn("仅本次运行", output.getvalue())
        self.assertIn("独立 CLI 无法读取", output.getvalue())

    def test_vendor_exception_is_sanitized_and_returns_nonzero(self):
        from config import ModelConfig

        class FailingOrchestrator:
            compiler = SimpleNamespace(to_markdown=lambda _guide: "")

            async def generate(self, _query, on_progress=None):
                raise RuntimeError("provider leaked offline-secret")

        with patch("config.resolve_model_config", return_value=ModelConfig(profile_id="saved")), \
                patch("orchestrator_llm.TravelOrchestrator", return_value=FailingOrchestrator()):
            output = io.StringIO()
            with redirect_stdout(output):
                result = asyncio.run(cli.main(["安阳三日"]))

        self.assertEqual(result, 1)
        self.assertIn("攻略生成失败", output.getvalue())
        self.assertNotIn("offline-secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
