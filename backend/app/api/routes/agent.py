"""
Agent 相关接口：提交分析任务、查询任务状态、下载生成文件

POST /pipeline               提交任务（文字或上传文件），返回 task_id
GET  /tasks/{task_id}        查询任务状态（前端每 2 秒轮询一次）
GET  /download/{task_id}/{kind}  下载生成文件（kind: requirement / testcase）

后端重启后内存任务丢失，任务查询与下载会回退 task_history 历史记录（见 routes/history.py）。
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ...config import OUTPUT_ROOT
from ...services.history_store import get_history, load_result_from_disk
from ...services.pipeline import run_pipeline
from ...tasks.manager import executor, task_manager

router = APIRouter()

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
# 可下载的文件类型
DOWNLOAD_KINDS = {"requirement", "testcase"}


@router.post("/pipeline")
async def create_pipeline(request: Request):
    """提交一个分析任务：表单里可以带文字（text）或文件（file）"""
    form = await request.form()
    text = (form.get("text") or "").strip()
    upload = form.get("file")

    if not text and upload is None:
        raise HTTPException(status_code=400, detail="请输入需求描述或上传文件")

    # 处理上传文件
    upload_data = None
    if upload is not None:
        filename = upload.filename or "upload.txt"
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型：{ext}，请上传 txt / md / pdf 文件",
            )
        content = await upload.read()
        if not content:
            raise HTTPException(status_code=400, detail="上传的文件是空的")
        upload_data = {"filename": filename, "content": content}

    # 创建任务并在后台线程中执行
    task_id = task_manager.create()
    executor.submit(run_pipeline, task_id, text or None, upload_data)

    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    """查询任务状态：内存任务优先，后端重启后回退历史记录（从磁盘重建 result）"""
    task = task_manager.get(task_id)
    if task is None:
        row = get_history(task_id)
        if row is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        task = {
            "id": row["task_id"],
            "status": row["status"],
            "stage": {"done": "完成", "failed": "失败"}.get(row["status"], ""),
            "result": load_result_from_disk(task_id, row) if row["status"] == "done" else None,
            "error": row["error"] or None,
            "created_at": row["created_at"],
        }
    return task


@router.get("/download/{task_id}/{kind}")
def download(task_id: str, kind: str):
    """下载生成的文件：内存任务优先，后端重启后回退历史记录取产物文件名"""
    if kind not in DOWNLOAD_KINDS:
        raise HTTPException(status_code=404, detail="文件类型不存在")

    filename = None
    task = task_manager.get(task_id)
    if task is not None and task.get("status") == "done":
        filename = ((task.get("result") or {}).get(kind) or {}).get("filename")

    if filename is None:
        row = get_history(task_id)
        if row is not None and row.get("status") == "done":
            filename = (
                row.get("requirement_filename")
                if kind == "requirement"
                else row.get("testcase_filename")
            )

    if not filename:
        raise HTTPException(status_code=404, detail="任务未完成或不存在")

    path = OUTPUT_ROOT / task_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件已被清理")

    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if kind == "testcase"
        else "text/markdown"
    )
    return FileResponse(path, media_type=media_type, filename=filename)
