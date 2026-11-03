"""
测试用例管理相关接口

接口列表：
- GET    /testcases                分页/筛选查询
- POST   /testcases                手动新建
- POST   /testcases/save-agent     Agent 批量入库
- PUT    /testcases/{testcase_id}  更新（含状态徽标切换）
- DELETE /testcases/{testcase_id}  删除
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal, Optional, List

from ...services.testcases_store import (
    insert_testcase as store_insert_manual,
    save_agent_testcases as store_insert_agent,
    query_testcases as store_query,
    update_testcase as store_update,
    delete_testcase as store_delete,
)
from ...services.feature_store import get_feature_by_id as feature_get_by_id
from ...services.project_store import get_project as project_get

router = APIRouter()

# ================ Pydantic Models ================
class TestcaseCreate(BaseModel):
    """测试用例创建请求体"""
    feature_id: int
    title: str = Field(..., min_length=1, max_length=100)
    module: str = ""
    priority: Literal["P0", "P1", "P2", "P3"] = "P2"
    dimension: str = ""
    scenario: str = ""
    stages: List[str] = Field(default_factory=list)
    precondition: str = ""
    steps: list = Field(default_factory=list)
    expected: str = ""

class TestcaseUpdate(BaseModel):
    """测试用例更新请求体"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    module: Optional[str] = Field(None)
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    status: Optional[Literal["open", "pass", "fail", "blocked"]] = None
    dimension: Optional[str] = None
    scenario: Optional[str] = None
    stages: Optional[List[str]] = None
    precondition: Optional[str] = None
    steps: Optional[List] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    
class AgentTestcaseItem(BaseModel):
    """Agent测试用例项"""
    id: str = ""
    title: str = ""
    requirement_ref: str = ""
    module: str = ""
    priority: str = "P2"
    dimension: str = ""
    scenario: str = ""
    stages: list = Field(default_factory=list)
    precondition: str = ""
    steps: list = Field(default_factory=list)
    expected: str = ""
class AgentTestcaseSave(BaseModel):
    """Agent测试用例保存请求体"""
    project_id: int
    testcases: List[AgentTestcaseItem]

# ================ CRUD ===============
@router.get("/testcases")
def list_testcases(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    project_id: Optional[int] = None, 
    feature_id: Optional[int] = None, 
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None, 
    scenario:Optional[str] = None,
    dimension: Optional[str] = None, 
    status: Optional[Literal["open", "pass", "fail", "blocked"]] = None,
    stage: Optional[str] = None,
    keyword: Optional[str] = None
):
    """获取测试用例：分页、筛选（菜单进入-全量；需求点击进入-带筛选）"""
    items, total = store_query(page, page_size, project_id, feature_id, priority, scenario, dimension, status, stage, keyword)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/testcases")
def create_testcase_manual(testcase: TestcaseCreate):
    """手动创建测试用例"""
    if feature_get_by_id(testcase.feature_id) is None:
        raise HTTPException(status_code=404, detail="需求不存在")
    return store_insert_manual(testcase.feature_id, 
    testcase.title, testcase.module, testcase.priority,
    testcase.dimension, testcase.scenario, testcase.stages, testcase.precondition, 
    testcase.steps, testcase.expected)


@router.post("/testcases/save-agent")
def save_agent_testcases(body: AgentTestcaseSave):
    """保存Agent测试用例"""
    if project_get(body.project_id) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return store_insert_agent(body.project_id, [t.model_dump() for t in body.testcases])


@router.put("/testcases/{testcase_id}")
def update_testcase(testcase_id: int, testcase: TestcaseUpdate):
    """更新测试用例"""
    row = store_update(testcase_id, testcase.model_dump(exclude_unset=True))
    if row is None:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    return row


@router.delete("/testcases/{testcase_id}")
def delete_testcase(testcase_id: int):
    """删除测试用例"""
    if not store_delete(testcase_id):
        raise HTTPException(status_code=404, detail="测试用例不存在")
    return {"status": "ok"}
