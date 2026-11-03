"""
API 路由包 - 按业务域分类管理接口定义

- health.py        健康检查
- agent.py         Agent 相关：提交分析任务、查询任务状态、下载生成文件
- agent_settings.py 模型设置相关
- history.py       Agent 任务历史：列表 / 详情 / 删除
- projects.py      项目管理相关
- features.py      需求管理相关
- testcases.py     测试用例管理相关
- testruns.py      测试运行相关

新增接口时：直接在对应的业务域文件里加路由即可，
全新的业务域则新建一个文件，并在这里 include 进来。
"""

from fastapi import APIRouter

from .agent import router as agent_router
from .agent_settings import router as agent_settings_router
from .health import router as health_router
from .history import router as history_router
from .projects import router as projects_router
from .features import router as features_router
from .testcases import router as testcases_router
from .testruns import router as testruns_router

# 总路由：由 main.py 统一注册到 /api 前缀下
router = APIRouter()
router.include_router(health_router)

router.include_router(agent_router)
router.include_router(agent_settings_router)
router.include_router(history_router)

router.include_router(projects_router)
router.include_router(features_router)
router.include_router(testcases_router)
router.include_router(testruns_router)

