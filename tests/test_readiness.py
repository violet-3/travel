"""Offline readiness checks use an isolated local data directory."""

import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
from config import AmapConfig
from tools.readiness import check_local_readiness, format_readiness_report


class ReadinessTests(unittest.TestCase):
    def test_checks_local_imports_and_writable_temp_data_dir_without_network(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-readiness-") as temp, \
                patch.dict(os.environ, {}, clear=True), \
                patch.object(config.default_config, "amap", AmapConfig()), \
                patch.object(socket.socket, "connect", side_effect=AssertionError("network attempted")):
            result = check_local_readiness(Path(temp) / "isolated-data")

        self.assertTrue(result["dependencies_ok"], result["missing_modules"])
        self.assertTrue(result["data_directory_writable"])
        self.assertTrue(result["ready"])
        self.assertFalse(result["model_configured"])
        self.assertFalse(result["amap_configured"])
        self.assertFalse(result["network_connections_verified"])
        self.assertEqual(list(Path(result["data_directory"]).glob(".readiness-*")), [])

    def test_readiness_report_does_not_echo_environment_secrets(self):
        secret = "offline-readiness-secret"
        with tempfile.TemporaryDirectory(prefix="shanhe-readiness-") as temp, \
                patch.dict(os.environ, {"TRAVEL_LLM_KEY": secret}), \
                patch.object(config.default_config, "amap", AmapConfig(web_key="amap-secret")):
            result = check_local_readiness(temp)
            report = format_readiness_report(result)

        self.assertTrue(result["model_configured"])
        self.assertTrue(result["amap_configured"])
        self.assertNotIn(secret, report)
        self.assertNotIn("amap-secret", report)
        self.assertIn("不会连接模型或地图服务", report)

    def test_unwritable_data_path_blocks_local_readiness(self):
        with tempfile.TemporaryDirectory(prefix="shanhe-readiness-file-") as temp:
            blocked = Path(temp) / "not-a-directory"
            blocked.write_text("occupied", encoding="utf-8")
            result = check_local_readiness(blocked)
            report = format_readiness_report(result)

        self.assertFalse(result["data_directory_writable"])
        self.assertFalse(result["ready"])
        self.assertIn("SHANHE_TRAVEL_DATA_DIR", report)

    def test_missing_pydantic_returns_install_guidance_without_importing_app_config(self):
        import importlib
        import builtins

        real_import_module = importlib.import_module
        real_import = builtins.__import__

        def import_without_pydantic(module_name):
            if module_name == "pydantic":
                raise ModuleNotFoundError("pydantic unavailable in isolated venv")
            return real_import_module(module_name)

        def import_without_optional_config(name, *args, **kwargs):
            if name in {"config", "tools.model_profiles", "tools.amap_settings"}:
                raise AssertionError("configuration import attempted without required dependencies")
            return real_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory(prefix="shanhe-readiness-empty-venv-") as temp, \
                patch("tools.readiness.importlib.import_module", side_effect=import_without_pydantic), \
                patch("builtins.__import__", side_effect=import_without_optional_config):
            result = check_local_readiness(temp)
            report = format_readiness_report(result)

        self.assertFalse(result["ready"])
        self.assertTrue(result["configuration_checks_skipped"])
        self.assertIn("pydantic", result["missing_modules"])
        self.assertIn("pip install -r", report)
        self.assertIn(str(Path(sys.executable).resolve()), report)
        self.assertIn(str((Path(__file__).resolve().parents[1] / "requirements.txt").resolve()), report)
        self.assertIn("模型/高德配置：因依赖缺失未检查", report)


if __name__ == "__main__":
    unittest.main()
