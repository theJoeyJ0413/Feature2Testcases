#!/usr/bin/env python3
"""
统一 Agent - 命令行入口

使用方法:
    # 完整流程：需求分析 + 测试用例生成
    python main.py "我想开发一个在线购物系统"
    python main.py -f input.txt

    # 只做需求分析（产出需求文档 + 结构化需求点 json）
    python main.py -f input.txt --stage analyze

    # 只做测试用例生成（输入为阶段1产出的需求点 json）
    python main.py -f features_xxx.json --stage testcases
"""

import argparse
import sys
from pathlib import Path
from rich.console import Console

# 兼容两种运行方式：
# 1. 独立脚本：cd 到本目录后 `python main.py ...`（把 backend 根目录加入 sys.path，统一走包导入）
# 2. 包内运行：`python -m app.agents.unified_agent.main ...`（直接相对导入）
if __package__ in (None, ""):
    BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.agents.unified_agent.agent import UnifiedAgent
    from app.agents.unified_agent.config import Config
else:
    from .agent import UnifiedAgent
    from .config import Config

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="统一 Agent - 需求分析 + 测试用例生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py "开发一个用户管理系统"
  python main.py -f input.txt --stage analyze
  python main.py -f features_xxx.json --stage testcases
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="需求描述（自然语言）或文件路径",
    )

    parser.add_argument(
        "-f", "--file",
        help="输入文件路径（支持 .txt, .md, .pdf；testcases 阶段为 .json）",
    )

    parser.add_argument(
        "--stage",
        choices=["analyze", "testcases", "all"],
        default="all",
        help="执行阶段：analyze 仅需求分析 / testcases 仅测试用例 / all 完整流程（默认）",
    )

    args = parser.parse_args()

    # 验证配置
    try:
        Config.validate()
    except ValueError as e:
        console.print(f"[bold red]配置错误:[/bold red] {e}")
        console.print("\n请复制 .env.example 为 .env 并填写 API Key:")
        console.print("  cp .env.example .env")
        sys.exit(1)

    input_source = args.file or args.input
    if not input_source:
        parser.print_help()
        return

    try:
        agent = UnifiedAgent()

        if args.stage == "analyze":
            result = agent.analyze(input_source)
            console.print(f"\n[bold green]✅ 需求文档: {result['doc_path']}[/bold green]")
            console.print(f"✅ 需求点数据: {result['features_path']}")
        elif args.stage == "testcases":
            path = agent.generate_testcases(input_source)
            console.print(f"\n[bold green]✅ 测试用例文件: {path}[/bold green]")
        else:
            result = agent.process(input_source)
            console.print(f"\n[bold green]✅ 需求文档: {result['doc_path']}[/bold green]")
            console.print(f"[bold green]✅ 测试用例文件: {result['testcase_path']}[/bold green]")

    except Exception as e:
        console.print(f"[bold red]❌ 错误:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
