"""CLI for the LangChain travel guide agent.

Examples:
    python main.py "想去安阳玩3天，喜欢人文历史"
    python main.py "成都重庆5天" --save
    python main.py "苏州周末两日" --profile local-profile-id
    python main.py --check
"""

import argparse
import asyncio
import inspect
import os
import re
from datetime import date
from pathlib import Path


def _has_environment_model_config() -> bool:
    names = (
        "TRAVEL_LLM_URL", "TRAVEL_LLM_MODEL", "TRAVEL_LLM_PROVIDER",
        "TRAVEL_LLM_PROTOCOL",
    )
    if any(os.environ.get(name, "").strip() for name in names):
        return True
    key = os.environ.get("TRAVEL_LLM_KEY", "").strip()
    return bool(key and not key.startswith("YOUR_") and key != "sk-no-key-needed")


def _safe_generation_error(exc: Exception) -> str:
    try:
        from orchestrator_llm import GenerationStageTimeout
        if isinstance(exc, GenerationStageTimeout):
            return "生成阶段等待超时，请检查接口地址和模型服务后重试。"
    except Exception:
        pass
    try:
        from tools.llm_client import classify_model_error, safe_model_error_message
        return safe_model_error_message(classify_model_error(exc, structured=False))
    except Exception:
        return "生成失败，请检查模型配置、接口地址和本机依赖后重试。"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成中国旅行攻略（LangChain Agent）")
    parser.add_argument("query", nargs="?", help="旅行需求，例如：想去安阳玩3天")
    parser.add_argument("--save", action="store_true", help="将 Markdown 保存到 output/ 目录")
    parser.add_argument("--profile", help="选择本机已保存的模型档案 ID")
    parser.add_argument("--check", action="store_true", help="离线检查依赖、数据目录和配置是否存在")
    research = parser.add_mutually_exclusive_group()
    research.add_argument("--web-research", dest="web_research", action="store_true",
                          help="本次启用 DeepSeek 网页 Search/Fetch（可能产生费用）")
    research.add_argument("--no-web-research", dest="web_research", action="store_false",
                          help="本次关闭联网 Search/Fetch")
    parser.set_defaults(web_research=None)
    return parser


def _safe_output_path(output_root: str | Path, title: str, generated_at: str) -> Path:
    """Build a Windows-safe filename and enforce that it stays under output_root."""
    cleaned_title = str(title or "").replace("《", "").replace("》", "")
    cleaned_title = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "", cleaned_title)
    cleaned_title = re.sub(r"\s+", " ", cleaned_title).strip().rstrip(". ")
    cleaned_title = cleaned_title[:80].rstrip(". ")
    if not cleaned_title or cleaned_title in {".", ".."}:
        raise ValueError("攻略标题清理后为空，无法安全保存；请调整生成标题后重试。")
    if cleaned_title.split(".", 1)[0].rstrip(" .").upper() in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(1, 10)),
        *(f"LPT{n}" for n in range(1, 10)),
    }:
        cleaned_title = f"_{cleaned_title}"

    date_match = re.match(r"^\d{4}-\d{2}-\d{2}", str(generated_at or ""))
    date_part = date_match.group(0) if date_match else date.today().isoformat()
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = (root / f"{cleaned_title}_{date_part}.md").resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("保存路径超出 output 目录，已取消写入。") from None
    return target


async def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.check:
        from tools.readiness import check_local_readiness, format_readiness_report

        result = check_local_readiness()
        print(format_readiness_report(result))
        return 0 if result["ready"] else 1

    if not args.query:
        _parser().print_help()
        return 0

    from config import (
        ModelConfigError,
        ModelProfileNotFoundError,
        default_config,
        resolve_model_config,
    )
    from tools.model_profiles import ModelProfileStore, ProfileStoreError
    from tools.deepseek_search_settings import (
        DeepSeekResearchConfig, DeepSeekSearchSettingsError,
        DeepSeekSearchSettingsStore, OFFICIAL_BASE_URL,
    )

    profiles = ModelProfileStore()
    try:
        model_config = resolve_model_config(args.profile, profiles)
    except (ModelConfigError, ModelProfileNotFoundError, ProfileStoreError) as exc:
        print(f"模型配置不可用：{exc}")
        if args.profile:
            print("CLI 在独立进程中运行，网页端“仅本次运行”的配置不会传递到 CLI；请保存本机档案或配置 TRAVEL_LLM_* 环境变量。")
        return 1

    if model_config.profile_id is None and not _has_environment_model_config():
        print("CLI 未发现本机已保存的默认模型档案或 TRAVEL_LLM_* 配置。")
        print("网页端“仅本次运行”的模型配置只保存在 Web 进程内，独立 CLI 无法读取；请保存本机档案或配置环境变量后重试。")
        return 1

    search_settings = DeepSeekSearchSettingsStore()
    try:
        research_config = search_settings.resolve(profiles, enabled_override=args.web_research)
    except DeepSeekSearchSettingsError:
        research_config = DeepSeekResearchConfig(
            enabled=bool(args.web_research), base_url=OFFICIAL_BASE_URL,
            availability="profile_unavailable" if args.web_research else "disabled",
        )
    if args.web_research and research_config.availability != "ready":
        print("联网检索已请求，但没有可用的 Search 凭据；仍会继续生成文本攻略。请先在网页设置中配置独立 Search Key 或明确选择官方 DeepSeek 档案。")

    print()
    print("=" * 50)
    print("  🧳 中国旅游攻略 Agent")
    print("  [LangChain Agent]")
    print("=" * 50)
    print()

    def show_progress(progress: int, stage: str, message: str):
        bar_len = 20
        filled = int(bar_len * progress / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  [{bar}] {progress:3d}%  {message}")

    orch = None
    try:
        from orchestrator_llm import TravelOrchestrator

        orch = TravelOrchestrator(model_config, research_config=research_config)
        guide = await orch.generate(args.query, on_progress=show_progress)
        markdown = orch.compiler.to_markdown(guide)
    except Exception as exc:
        print(f"攻略生成失败：{_safe_generation_error(exc)}")
        return 1
    finally:
        close = getattr(orch, "aclose", None) if orch is not None else None
        if callable(close):
            try:
                close_result = close()
                if inspect.isawaitable(close_result):
                    await close_result
            except Exception:
                pass

    print()
    print("=" * 50)
    print()

    research_status = getattr(guide, "web_research", None)
    if research_status is not None:
        print(
            f"  网页来源：{research_status.status}；Search {research_status.search_count} 次，"
            f"Fetch {research_status.fetch_count} 次。"
        )

    if args.save:
        try:
            filepath = _safe_output_path(default_config.output_dir, guide.title, guide.generated_at)
            with filepath.open("w", encoding="utf-8") as output_file:
                output_file.write(markdown)
        except (OSError, ValueError) as exc:
            print(f"攻略保存失败：{exc}")
            return 1
        print(f"  ✅ 攻略已保存: {filepath}")
        print(f"  📝 {len(markdown)} 字符")
    else:
        print(markdown)

    print()
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
