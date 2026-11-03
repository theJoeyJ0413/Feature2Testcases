"""
pytest 公共夹具：测试数据全隔离，绝不触碰真实数据

隔离策略（不修改任何业务代码，全部在测试侧完成）：
1. 会话级临时目录：环境变量 OUTPUT_ROOT 指向 <临时目录>/output，
   必须在导入 app.config 之前设置（config.py 在导入时读取该变量）；
2. 数据库：把 app.services.db_conn.DB_PATH 替换为临时 SQLite 文件——
   所有 store 都通过 db_conn._connect() 访问数据库，单点替换即可隔离；
3. 每个用例前后清空四张表与 output 临时目录，用例之间互不影响。

真实数据位置（测试期间不会被读写）：
- backend/data/management.db
- backend/output/
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# tests/ 的上一级 = backend/，保证任意工作目录下都能 import app
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---- 必须先于 app 模块导入：config.py 在导入时读取环境变量 ----
_SESSION_TMP = Path(tempfile.mkdtemp(prefix="agent-tests-"))
os.environ["OUTPUT_ROOT"] = str(_SESSION_TMP / "output")

from app.services import db_conn  # noqa: E402

db_conn.DB_PATH = _SESSION_TMP / "test.db"  # 全局唯一的数据入口，指向临时文件

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.feature_store import init_features_db  # noqa: E402
from app.services.history_store import init_history_db  # noqa: E402
from app.services.project_store import init_projects_db  # noqa: E402
from app.services.testcases_store import init_testcases_db  # noqa: E402
from app.services.testruns_store import init_testruns_db  # noqa: E402

_TABLES = ("test_run_items", "test_runs", "testcases", "features", "task_history", "projects")


def _wipe_db():
    """清空四张表（顺序：先子表后父表，避免外键约束报错）"""
    conn = sqlite3.connect(db_conn.DB_PATH)
    try:
        for table in _TABLES:
            conn.execute(f"delete from {table}")
        conn.commit()
    finally:
        conn.close()


def _wipe_output():
    shutil.rmtree(os.environ["OUTPUT_ROOT"], ignore_errors=True)


@pytest.fixture(autouse=True)
def isolated_state():
    """每个用例独立：先建表并清空数据，用例结束后再清一次"""
    init_projects_db()
    init_features_db()
    init_testcases_db()
    init_testruns_db()
    init_history_db()
    _wipe_db()
    _wipe_output()
    yield
    _wipe_db()
    _wipe_output()


@pytest.fixture()
def output_root():
    """临时 OUTPUT_ROOT 路径（用例可往这里写产物文件）"""
    return Path(os.environ["OUTPUT_ROOT"])


@pytest.fixture()
def client():
    """FastAPI TestClient：走完整 lifespan（建表 + 回填，全部发生在临时目录内）"""
    with TestClient(app) as c:
        yield c


def pytest_sessionfinish(session, exitstatus):
    """整个测试会话结束后清理临时目录（数据库 + output）"""
    shutil.rmtree(_SESSION_TMP, ignore_errors=True)
