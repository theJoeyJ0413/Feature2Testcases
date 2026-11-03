"""
Agent 任务历史相关接口

每次分析任务都会在 task_history 表留一条持久化记录（后端重启不丢失）：

- GET    /history            历史列表（分页 + 关键字 / 状态 / 保存联动筛选）
- PUT    /history/{task_id}  回写保存结果（body: {"project_id": 项目ID}，由前端「保存为项目」成功后调用）
- GET    /history/{task_id}  历史详情（含从磁盘重建的 result，可直接还原结果视图）
- DELETE /history/{task_id}  删除历史记录，同时清理 output 下的任务目录（项目库数据不受影响）
"""

import re
import shutil
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from ...config import OUTPUT_ROOT
from ...services.history_store import (
    delete_history as store_delete,
    get_history as store_get,
    load_result_from_disk,
    query_history as store_query,
    update_history as store_update,
)

router = APIRouter()

# task_id 为 uuid4().hex（32 位小写十六进制），删除时用它做路径安全校验
TASK_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@router.get("/history")
def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    saved: Optional[bool] = None,
):
    """历史列表：分页 + 关键字 / 状态 / 保存联动筛选（saved 不传=全部，true=已保存为项目，false=未保存）"""
    items, total = store_query(
        page,
        page_size,
        (keyword or "").strip() or None,
        (status or "").strip() or None,
        saved,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/history/{task_id}")
def get_history(task_id: str):
    """历史详情：元数据 + result（按记录中的文件名从磁盘重建）"""
    row = store_get(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="历史记录不存在")

    result = load_result_from_disk(task_id, row) if row["status"] == "done" else None
    return {**row, "result": result}


class HistoryUpdate(BaseModel):
    """更新历史记录请求体（当前仅支持回写保存结果）"""
    project_id: int = Field(ge=1, description="保存到的项目 ID")


@router.put("/history/{task_id}")
def update_history(task_id: str, body: HistoryUpdate):
    """回写保存结果：由前端「保存为项目」成功后调用（仅已完成的任务可回写）"""
    row = store_get(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    if row["status"] != "done":
        raise HTTPException(status_code=400, detail="仅已完成的任务可回写保存结果")
    return store_update(task_id, project_id=body.project_id)


@router.delete("/history/{task_id}")
def delete_history(task_id: str):
    """删除历史记录，并清理对应的任务目录（项目库数据独立，不受影响）"""
    if not store_delete(task_id):
        raise HTTPException(status_code=404, detail="历史记录不存在")

    # 路径安全校验：task_id 必须是 uuid4().hex 格式，且目录确实位于 OUTPUT_ROOT 下
    task_dir = (OUTPUT_ROOT / task_id).resolve()
    if TASK_ID_PATTERN.match(task_id) and task_dir.parent == OUTPUT_ROOT.resolve() and task_dir.is_dir():
        shutil.rmtree(task_dir)

    return {"deleted": True}
