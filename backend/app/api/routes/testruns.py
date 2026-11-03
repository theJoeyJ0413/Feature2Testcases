"""
测试运行相关接口

接口列表：
- GET   /testruns                              分页/筛选查询运行批次（含统计）
- POST  /testruns                              创建运行批次（快照符合条件的用例）
- GET   /testruns/stats                        运行统计（执行率 / 通过率）
- GET   /testruns/{run_id}                     运行详情（用例清单 + 统计）
- PATCH /testruns/{run_id}/items/{item_id}     记录单条用例结果
- POST  /testruns/{run_id}/finish              结束运行
"""

from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.project_store import get_project as project_get
from ...services.testruns_store import (
    create_testrun as store_create,
    finish_testrun as store_finish,
    get_testrun as store_get,
    get_testrun_stats as store_stats,
    query_testruns as store_query,
    update_run_item as store_update_item,
)

router = APIRouter()


# ================ Pydantic Models ================
class RunScope(BaseModel):
    """运行范围：全部需求 / 指定需求"""
    type: Literal["all", "features"] = "all"
    feature_ids: List[int] = Field(default_factory=list)


class TestRunCreate(BaseModel):
    """创建运行批次请求体"""
    project_id: int
    mode: Literal["smoke", "full", "regression", "custom"] = "smoke"
    scope: RunScope = Field(default_factory=RunScope)
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    stage: Optional[str] = None


class RunItemUpdate(BaseModel):
    """记录单条用例结果请求体"""
    result: Optional[Literal["open", "pass", "fail", "blocked"]] = None
    actual: Optional[str] = None
    remark: Optional[str] = None


# ================ API ===============
@router.get("/testruns")
def list_testruns(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    project_id: Optional[int] = None,
    status: Optional[Literal["running", "completed"]] = None,
    mode: Optional[Literal["smoke", "full", "regression", "custom"]] = None,
    keyword: Optional[str] = None,
):
    """获取运行批次列表：分页、按项目/状态/模式筛选"""
    items, total = store_query(page, page_size, project_id, status, mode, keyword)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/testruns")
def create_testrun(body: TestRunCreate):
    """创建运行批次：按范围快照用例，初始状态为 running"""
    if project_get(body.project_id) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    try:
        return store_create(
            body.project_id,
            body.mode,
            body.scope.model_dump(),
            body.priority,
            body.stage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# 静态路径必须放在 /{run_id} 之前，避免被动态路由吞掉
@router.get("/testruns/stats")
def get_testrun_stats(
    project_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=365),
):
    """运行统计：时间窗口内的执行率、通过率与结果分布"""
    return store_stats(project_id, days)


@router.get("/testruns/{run_id}")
def get_testrun(run_id: int):
    """运行详情：批次信息 + 统计 + 按需求排序的用例清单"""
    run = store_get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="测试运行不存在")
    return run


@router.patch("/testruns/{run_id}/items/{item_id}")
def update_run_item(run_id: int, item_id: int, body: RunItemUpdate):
    """记录单条用例结果，并同步回写测试用例状态"""
    try:
        item = store_update_item(run_id, item_id, body.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if item is None:
        raise HTTPException(status_code=404, detail="测试运行或用例结果不存在")
    return item


@router.post("/testruns/{run_id}/finish")
def finish_testrun(run_id: int):
    """结束运行批次（幂等）"""
    run = store_finish(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="测试运行不存在")
    return run
