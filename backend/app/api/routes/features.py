"""
需求管理相关接口

接口列表：
- POST   /features/{project_id}       在单个项目下新建需求：手动
- POST   /features/{project_id}/save-agent 在单个项目下保存Agent生成的需求
- GET    /features/{project_id}      查询单个项目下的需求列表
- PUT    /features/{project_id}/{id} 更新需求
- DELETE /features/{project_id}/{id} 删除需求
- POST   /features/{project_id}/{id}/generate-testcases  生成测试用例
"""
import json
from typing import Literal, Optional, List, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...services.feature_store import (
    insert_feature as store_insert_manual,
    save_agent_features as store_insert_agent,
    query_features as store_query,
    update_feature as store_update,
    delete_feature as store_delete,
    get_feature as store_get,
)
from ...services.project_store import (
    get_project as project_get,
)
from ...services.testcases_store import (
    save_agent_testcases as store_save_agent_testcases,
)
from ...agents.unified_agent import UnifiedAgent
from ...agents.unified_agent.src.testcases_generator import TestcasesGenerator

router = APIRouter()

# =================== Pydantic models ===================
class FeatureCreateManual(BaseModel):
    """手动创建需求请求体"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    module: str = ""
    functional: list = []
    non_functional: dict = {}
    priority: Literal["P0", "P1", "P2", "P3"] = "P2"

class FeatureUpdate(BaseModel):
    """更新需求请求体"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None)
    module: Optional[str] = Field(None)
    status: Optional[Literal["open", "analyzed", "closed"]] = None
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    functional: Optional[List] = None
    non_functional: Optional[Dict] = None

class AgentFeatureItem(BaseModel):
    """Agent 分析产出的单个需求点"""
    id: str = ""    #FEATURE-001
    module: str = ""
    title: str = ""
    description: str = ""
    functional: list = []
    non_functional: dict = {}
    priority: str = "P2"
class AgentFeaturesSave(BaseModel):
    """Agent 分析结果批量入库请求体"""
    features: list[AgentFeatureItem]


# =================== API ===================
@router.get("/features/{project_id}")
def list_features(project_id: int):
    """获取选中项目下的需求列表"""
    if project_get(project_id) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    items, total = store_query(project_id)
    return {
        "items": items,
        "total": total
    }


@router.post("/features/{project_id}")
def create_feature_manual(project_id: int, body: FeatureCreateManual):
    """手动创建需求"""
    if project_get(project_id) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return store_insert_manual(
        project_id, body.title, body.description, body.module, 
        body.functional, body.non_functional, 'manual', body.priority)

@router.post("/features/{project_id}/save-agent")
def save_agent_features(project_id: int, body: AgentFeaturesSave):
    """保存 Agent 分析结果：批量入库需求点"""
    if project_get(project_id) is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return store_insert_agent(project_id, [item.model_dump() for item in body.features])


@router.post("/features/{project_id}/{id}/generate-testcases")
def generate_testcases(project_id: int, id: int):
    """针对单个需求调用Agent生成测试用例，并直接入库"""
    feature = store_get(project_id, id)
    if feature is None:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    # 组装输入结构 -> TestcasesGenerator
    features_payload = {
        "project_name": "",
        "features": [{
            "id": feature["feature_no"],
            "module": feature["module"],
            "title": feature["title"],
            "description": feature["description"],
            "priority": feature["priority"],
            "functional": feature["functional"],
            "non_functional": feature["non_functional"]
        }],
    }
    # 调用LLM生成测试用例
    try:
        generator = TestcasesGenerator()
        text = generator.testcases_generator(
            json.dumps(features_payload, ensure_ascii=False, indent=2)
        )
        data = UnifiedAgent._parse_json(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成测试用例失败：{e}")
    
    testcases = data.get("testcases", [])
    if not testcases:
        raise HTTPException(status_code=500, detail="生成测试用例失败：LLM 未返回测试用例，请重试")
    
    # 强制关联到当前需求，再批量入库
    for tc in testcases:
        tc["requirement_ref"] = feature["feature_no"]
    return store_save_agent_testcases(project_id, testcases)


@router.put("/features/{project_id}/{id}")
def update_feature(project_id: int, id: int, body: FeatureUpdate):
    """更新需求"""
    row = store_update(project_id, id, body.model_dump(exclude_unset=True))
    if row is None:
        raise HTTPException(status_code=404, detail="需求不存在")
    return row

@router.delete("/features/{project_id}/{id}")
def delete_feature(project_id: int, id: int):
    """删除需求"""
    if not store_delete(project_id, id):
        raise HTTPException(status_code=404, detail="需求不存在")
    return {"status": "ok"}
