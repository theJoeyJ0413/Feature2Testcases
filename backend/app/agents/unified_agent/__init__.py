"""
统一 Agent（unified_agent）

两个阶段共享同一次需求分析结果：
  阶段1 需求分析：输入 → 需求文档（.md）+ 结构化需求点（.json）
  阶段2 测试用例：结构化需求点 → 测试用例（.xlsx）

后端可直接使用：
    from app.agents.unified_agent import UnifiedAgent

    agent = UnifiedAgent(output_dir="输出目录")
    result = agent.analyze("需求描述或文件路径")
    testcase_path = agent.generate_testcases(result["features_path"])
"""

from .agent import UnifiedAgent

__all__ = ["UnifiedAgent"]
