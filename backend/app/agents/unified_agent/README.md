# 统一 Agent（unified_agent）

把原来的「需求分析 Agent」和「测试用例 Agent」合并为一个 Agent，两个阶段共享同一次需求分析结果：

```
输入（文字 / txt / md / pdf）
  → 阶段1 需求分析（1 次 LLM 调用）
      产出① 需求分析文档（.md，可下载）
      产出② 结构化需求点（features_xxx.json，供阶段2使用）
  → 阶段2 测试用例生成（1 次 LLM 调用，输入=阶段1的产出②）
      产出 测试用例（.xlsx，可下载）
```

相比原来两个 Agent 的优势：

- LLM 调用从 3 次降到 2 次（更快、更省）
- 测试用例直接基于需求文档的同一份分析结果生成，两者内容一致
- 一个入口、两个阶段，与网页上的两个步骤一一对应

## 作为 Python 库使用（后端流水线即这种方式）

```python
from app.agents.unified_agent import UnifiedAgent

agent = UnifiedAgent(output_dir="输出目录")  # 不传则用 config.py 的默认输出目录

# 阶段1：需求分析（输入为文件路径或自然语言）
result = agent.analyze("开发一个用户管理系统")
print(result["doc_path"])        # 需求文档 .md 路径
print(result["features_path"])   # 结构化需求点 .json 路径

# 阶段2：测试用例生成（输入为阶段1产出的 json）
testcase_path = agent.generate_testcases(result["features_path"])
print(testcase_path)             # 测试用例 .xlsx 路径
```

## 命令行用法

在 `backend/` 目录下执行（依赖由 `backend/pyproject.toml` 统一管理、`uv.lock` 锁定）：

```bash
cd backend

# 完整流程
uv run python -m app.agents.unified_agent.main "开发一个用户管理系统"

# 只做需求分析
uv run python -m app.agents.unified_agent.main -f input.txt --stage analyze

# 只做测试用例生成（输入为阶段1产出的 json）
uv run python -m app.agents.unified_agent.main -f features_xxx.json --stage testcases
```

配置方式：复制 `.env.example` 为 `.env` 并填写 API Key。
