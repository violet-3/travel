"""
CLI 入口 v2 · Dify 模式

使用方式:
    # 直接运行（默认 Dify 模式）
    python main.py "想去安阳玩3天，喜欢人文历史"

    # 保存攻略到文件
    python main.py "成都重庆5天" --save

    # 直连 LLM 模式（不用 Dify，测原始 Python Agent）
    python main.py "云南7天" --direct
"""

import asyncio
import sys
import os


async def main():
    # ─── 解析参数 ───
    args = sys.argv[1:]
    if not args:
        print("=" * 50)
        print("  🧳 中国旅游攻略 Agent")
        print("=" * 50)
        print()
        print("用法: python main.py \"你的旅行需求\" [--save] [--direct]")
        print()
        print("示例:")
        print('  python main.py "想去安阳玩3天，喜欢人文历史"')
        print('  python main.py "成都重庆5天，吃火锅看熊猫" --save')
        print('  python main.py "云南7天" --direct    # 直连LLM，不用Dify')
        return

    user_input = args[0]
    save = "--save" in args
    use_direct = "--direct" in args

    # 延迟导入
    from config import default_config

    print()
    print("=" * 50)
    print("  🧳 中国旅游攻略 Agent")
    if use_direct:
        print("  [直连LLM模式]")
    else:
        print("  [Dify 工作流模式]")
    print("=" * 50)
    print()

    # ─── 进度回调 ───
    def show_progress(progress: int, stage: str, message: str):
        bar_len = 20
        filled = int(bar_len * progress / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  [{bar}] {progress:3d}%  {message}")

    # ─── 执行 ───
    if use_direct:
        from orchestrator_llm import TravelOrchestrator as LLMOrchestrator
        orch = LLMOrchestrator()
    else:
        from orchestrator import TravelOrchestrator
        orch = TravelOrchestrator()

    guide = await orch.generate(user_input, on_progress=show_progress)
    markdown = orch.compiler.to_markdown(guide)

    print()
    print("=" * 50)
    print()

    # ─── 输出 ───
    if save:
        output_dir = default_config.output_dir
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{guide.title.replace('《','').replace('》','')}_{guide.generated_at[:10]}.md"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"  ✅ 攻略已保存: {filepath}")
        print(f"  📝 {len(markdown)} 字符")
    else:
        print(markdown)

    print()
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
