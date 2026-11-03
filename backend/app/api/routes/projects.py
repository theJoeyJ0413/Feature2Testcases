"""
项目管理相关接口

可以通过Agent，用户确认是否添加当前项目
也可以用户自己手动添加

接口列表：
- GET       /projects       项目列表（分页、筛选）
- POST      /projects       新建项目，要表明来源：Agent、手动
- GET       /projects/{id}  查询单个项目详情
- PUT       /projects/{id}  更新单个项目
- DELETE    /projects/{id}  删除单个项目（级联删除需求/用例，并将关联历史记录恢复为未保存）
"""

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from ...services.project_store import (
    delete_project as store_delete,
    get_project as store_get,
    insert_project as store_insert,
    update_project as store_update,
    query_projects as store_query,
)

router = APIRouter()

# Pydantic 模型
class ProjectCreate(BaseModel):
    """新建项目请求体"""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    source: Literal["agent", "manual"] = "manual"

class ProjectUpdate(BaseModel):
    """更新项目请求体"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[Literal["active", "archived"]] = None

# 接口
@router.get("/projects")
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    source: Optional[Literal["agent", "manual"]] = None,
    keyword: Optional[str] = None,
):
    """项目列表：分页、筛选"""
    items, total = store_query(page, page_size, source, keyword)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/projects")
def create_project(body: ProjectCreate):
    """新建项目"""
    return store_insert(body.name, body.description, body.source)


@router.get("/projects/{project_id}")
def get_project(project_id: int):
    """查询单个项目"""
    row = store_get(project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return row


@router.put("/projects/{project_id}")
def update_project(project_id: int, body: ProjectUpdate):
    """更新项目"""
    row = store_update(project_id, body.model_dump(exclude_unset=True))
    if row is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return row


@router.delete("/projects/{project_id}")
def delete_project(project_id: int):
    """删除项目：级联删除其下需求与用例，已关联该项目的历史记录恢复为未保存（防悬空）"""
    result = store_delete(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"status": "ok", **result}
