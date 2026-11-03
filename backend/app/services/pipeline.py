"""
流水线服务 - 把"需求分析 → 测试用例生成"两步串起来

每个任务在自己的子目录中工作，直接 import 统一 Agent（unified_agent）分两个阶段调用：
1. 阶段1 analyze：分析输入，生成需求分析文档（.md）+ 结构化需求点（.json）
2. 阶段2 testcases：读取需求点，生成测试用例（.xlsx）

两个阶段共享同一次需求分析结果，保证文档与用例内容一致。
"""

from pathlib import Path
import json
from datetime import datetime

from ..agents.unified_agent import UnifiedAgent
from ..config import OUTPUT_ROOT
from ..tasks.manager import task_manager
from .history_store import extract_title, insert_history, update_history


def run_pipeline(task_id: str, text: str = None, upload: dict = None):
    """在后台线程中执行完整流水线，全程更新任务状态"""
    try:
        _run(task_id, text, upload)
    except Exception as e:
        task_manager.update(task_id, status="failed", stage="失败", error=str(e))
        update_history(task_id, status="failed", error=str(e), finished_at=datetime.now().isoformat())


def _run(task_id: str, text: str, upload: dict):
    task_dir = OUTPUT_ROOT / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    # 写入历史记录：元数据先落库，产物文件名等完成时再补充
    title_fallback = (text or (upload or {}).get("filename") or "").strip().replace("\n", " ")[:20] or "未命名任务"
    insert_history(
        task_id,
        title=title_fallback,
        input_source="file" if upload else "text",
        input_text=text or "",
        input_filename=(upload or {}).get("filename", ""),
    )

    # ---------- 0. 准备输入文件 ----------
    # 对应 routes.py 中 create_pipeline() 中对 upload_data 参数的处理
    task_manager.update(task_id, status="running", stage="正在准备输入文件…")
    update_history(task_id, status="running")
    if upload:
        ext = Path(upload["filename"]).suffix.lower() or ".txt"
        input_path = task_dir / f"input{ext}"
        input_path.write_bytes(upload["content"])
    else:
        input_path = task_dir / "input.txt"
        input_path.write_text(text, encoding="utf-8")

    # 一个 Agent 实例完成两个阶段，所有产物都写入本任务目录
    agent = UnifiedAgent(output_dir=task_dir)

    # ---------- 1. 需求分析 ----------
    task_manager.update(task_id, stage="正在生成需求分析文档（约 30~90 秒）…")
    result = agent.analyze(str(input_path))
    req_file = Path(result["doc_path"])
    requirement_content = req_file.read_text(encoding="utf-8", errors="ignore")

    # ---------- 2. 测试用例生成 ----------
    task_manager.update(task_id, stage="正在生成测试用例（约 1~3 分钟）…")
    tc_file = Path(agent.generate_testcases(result["features_path"]))
    
    # 读取结构化产物，便于后续一键保存的操作
    features_data = json.loads(Path(result["features_path"]).read_text(encoding="utf-8"))
    testcases = []
    json_files = sorted(task_dir.glob("testcases_*.json"))
    if json_files:
        testcases = json.loads(json_files[-1].read_text(encoding="utf-8")).get("testcases", [])

    # ---------- 3. 完成 ----------
    task_manager.update(
        task_id,
        status="done",
        stage="完成",
        result={
            "requirement": {
                "filename": req_file.name,
                "size": req_file.stat().st_size,
            },
            "testcase": {
                "filename": tc_file.name,
                "size": tc_file.stat().st_size,
            },
            "requirement_content": requirement_content,
            "features": features_data.get("features", []),
            "testcases": testcases,
        },
    )

    # 历史记录补充标题与产物文件名（title 优先取需求文档首行）
    update_history(
        task_id,
        status="done",
        title=extract_title(requirement_content, title_fallback),
        requirement_filename=req_file.name,
        features_filename=Path(result["features_path"]).name,
        testcase_filename=tc_file.name,
        finished_at=datetime.now().isoformat(),
    )
