"""Offline checks for local startup readiness; never probes provider services."""

from __future__ import annotations

import contextlib
import importlib
import io
import os
import shlex
import sys
import tempfile
from pathlib import Path

REQUIRED_MODULES = (
    "fastapi",
    "uvicorn",
    "httpx",
    "pydantic",
    "anyio",
    "keyring",
    "PIL",
    "langchain",
    "langchain_openai",
    "langchain_anthropic",
    "langchain_google_genai",
    "google.genai",
    "tzdata",
)


def check_local_readiness(data_dir: str | Path | None = None) -> dict:
    """Check imports, local data-directory writes, and configuration presence.

    This function performs no HTTP requests and never returns credential values.
    Missing model or AMap configuration is advisory: the Web app can still start
    so the user can configure a model in its settings page.
    """
    missing_modules: list[str] = []
    # Some imported packages print optional configuration notices on import.
    # Keep readiness output free of any incidental credential fragments.
    with contextlib.redirect_stdout(io.StringIO()):
        for module_name in REQUIRED_MODULES:
            try:
                importlib.import_module(module_name)
            except Exception:
                missing_modules.append(module_name)

        if missing_modules:
            root = Path(data_dir) if data_dir is not None else _fallback_app_data_dir()
            writable = _check_directory_writable(root)
            return {
                "ready": False,
                "dependencies_ok": False,
                "missing_modules": missing_modules,
                "data_directory": str(root),
                "data_directory_writable": writable,
                "model_configured": None,
                "amap_configured": None,
                "configuration_checks_skipped": True,
                "network_connections_verified": False,
            }

        from config import default_config
        from tools.amap_settings import AmapSettingsStore
        from tools.model_profiles import ModelProfileStore, app_data_dir

    root = Path(data_dir) if data_dir is not None else app_data_dir()
    data_directory_writable = _check_directory_writable(root)
    model_configured = False
    amap_configured = False
    try:
        profile_store = ModelProfileStore(root / ModelProfileStore.FILE_NAME)
        model_configured = profile_store.default_profile_id() is not None
    except Exception:
        # A broken profile file is not a startup blocker; the UI can surface it.
        pass

    model_env_names = (
        "TRAVEL_LLM_URL", "TRAVEL_LLM_KEY", "TRAVEL_LLM_MODEL",
        "TRAVEL_LLM_PROVIDER", "TRAVEL_LLM_PROTOCOL",
    )
    if any(os.environ.get(name, "").strip() for name in model_env_names):
        key = os.environ.get("TRAVEL_LLM_KEY", "").strip()
        model_configured = model_configured or bool(
            any(os.environ.get(name, "").strip() for name in model_env_names if name != "TRAVEL_LLM_KEY")
            or (key and not key.startswith("YOUR_") and key != "sk-no-key-needed")
        )

    try:
        amap_store = AmapSettingsStore(root / AmapSettingsStore.FILE_NAME)
        saved_amap_fields = bool(getattr(amap_store, "_saved_fields", set()))
    except Exception:
        saved_amap_fields = False
    amap_configured = saved_amap_fields or any((
        default_config.amap.js_key,
        default_config.amap.js_security_code,
        default_config.amap.web_key,
        default_config.amap.web_secret,
    ))

    dependencies_ok = not missing_modules
    locally_ready = dependencies_ok and data_directory_writable
    return {
        "ready": locally_ready,
        "dependencies_ok": dependencies_ok,
        "missing_modules": missing_modules,
        "data_directory": str(root),
        "data_directory_writable": data_directory_writable,
        "model_configured": bool(model_configured),
        "amap_configured": bool(amap_configured),
        "network_connections_verified": False,
    }


def _fallback_app_data_dir() -> Path:
    """Resolve the normal per-user path with stdlib only, for empty venvs."""
    override = os.environ.get("SHANHE_TRAVEL_DATA_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "ShanheTravel"
    if os.sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ShanheTravel"
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "shanhe-travel"


def _check_directory_writable(root: Path) -> bool:
    probe_path = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=root,
            prefix=".readiness-", suffix=".tmp", delete=False,
        ) as probe:
            probe_path = Path(probe.name)
            probe.write("ok")
        probe_path.unlink(missing_ok=True)
        return True
    except OSError:
        if probe_path is not None:
            try:
                probe_path.unlink(missing_ok=True)
            except OSError:
                pass
        return False


def format_readiness_report(result: dict) -> str:
    """Render a compact report without any configuration values."""
    dependency_status = "通过" if result["dependencies_ok"] else "缺少依赖"
    directory_status = "可写" if result["data_directory_writable"] else "不可写"
    startup_status = "本机可启动" if result["ready"] else "本机暂不可启动"
    missing = result.get("missing_modules") or []
    lines = [
        f"启动检查：{startup_status}",
        f"依赖导入：{dependency_status}" + (f"（{', '.join(missing)}）" if missing else ""),
        f"应用数据目录：{directory_status}（{result['data_directory']}）",
    ]
    if not result["data_directory_writable"]:
        lines.append("请检查该目录的写入权限，或将 SHANHE_TRAVEL_DATA_DIR 设置为可写目录。")
    if result.get("configuration_checks_skipped"):
        lines.append("模型/高德配置：因依赖缺失未检查。")
        lines.append("依赖修复命令：" + _dependency_install_command())
    else:
        lines.append("模型配置：已发现配置" if result["model_configured"] else "模型配置：未配置，可启动网页后在“模型设置”中补充")
        lines.append("高德配置：已发现配置" if result["amap_configured"] else "高德配置：未配置（可选）")
    lines.append("连接检查：未执行；此检查不会连接模型或地图服务。")
    return "\n".join(lines)


def _dependency_install_command() -> str:
    """Use the exact interpreter running --check and this repo's requirements."""
    python_path = str(Path(sys.executable).resolve())
    requirements_path = str((Path(__file__).resolve().parents[1] / "requirements.txt").resolve())
    if os.name == "nt":
        def quote_powershell(value: str) -> str:
            return '"' + value.replace('"', '`"') + '"'

        return (
            f"PowerShell：& {quote_powershell(python_path)} -X utf8 -m pip install -r "
            f"{quote_powershell(requirements_path)}"
        )
    return (
        f"{shlex.quote(python_path)} -X utf8 -m pip install -r "
        f"{shlex.quote(requirements_path)}"
    )
