"""
FastAPI 入口

启动方式（在 backend 目录下）：
    python3 -m uvicorn app.main:app --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from .api.routes import router
from .config import BACKEND_ROOT
from .services.project_store import init_projects_db
from .services.feature_store import init_features_db
from .services.testcases_store import init_testcases_db
from .services.testruns_store import init_testruns_db
from .services.history_store import init_history_db, backfill_history

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_projects_db()  #启动时建表（幂等）
    init_features_db()
    init_testcases_db()
    init_testruns_db()
    init_history_db()
    try:
        backfill_history()  # 把 output/ 下未入库的旧任务补进历史（幂等）
    except Exception as e:
        print(f"[warn] 历史记录回填失败，不影响启动：{e}")
    yield

app = FastAPI(
    title="Feature2Testcases",
    description="需求分析 + 测试用例生成平台",
    version="1.0.0",
    lifespan=lifespan, #启动钩子
)

# 允许前端开发服务器（Vite，默认 5173 端口）跨域访问
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# 如果存在前端构建产物（npm run build 生成），则由后端直接托管
static_dir = BACKEND_ROOT / "static"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
