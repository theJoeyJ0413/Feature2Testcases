"""
SQLite store for test cases
"""
from datetime import datetime
import json
import re

from .db_conn import _connect

STATUS_VALUES = {"open", "pass", "fail", "blocked"}
PRIORITY_VALUES = {"P0", "P1", "P2", "P3"}
STAGE_VALUES = {"冒烟", "通道", "灰度", "系统", "回归", "验收"}

def init_testcases_db():
    """建表"""
    conn = _connect()
    conn.execute(
        """
        create table if not exists testcases (
            id integer primary key autoincrement,
            feature_id integer not null,
            testcase_no text not null,
            title text not null,
            module text not null default '',
            priority text not null default 'P2',
            status text not null default 'open',
            dimension text not null default '',
            scenario text not null default '',
            stages text not null default '[]',
            precondition text not null default '',
            steps text not null default '[]',
            expected text not null default '',
            actual text not null default '',
            created_at text not null,
            updated_at text not null,
            foreign key(feature_id) references features (id),
            unique(feature_id, testcase_no)
        )
        """
    )
    # 存量表补列：create table if not exists 不会给已存在的表加列
    cols = {r["name"] for r in conn.execute("pragma table_info(testcases)").fetchall()}
    if "stages" not in cols:
        conn.execute("alter table testcases add column stages text not null default '[]'")
    conn.commit()
    conn.close()

# Helper functions
def _next_testcase_no(conn, feature_id: int) -> str:
    """扫描需求下所有用例编号，取数字后缀最大值 + 1"""
    rows = conn.execute(
        "select testcase_no from testcases where feature_id = ?",
        (feature_id,)
    ).fetchall()
    max_seq = 0
    for r in rows:
        m = re.search(r"(\d+)$", r["testcase_no"])
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    return f"TC-{max_seq + 1:03d}"

def _row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for key, fallback in (("steps", []), ("stages", [])):
        try:
            d[key] = json.loads(d[key])
        except (json.JSONDecodeError, TypeError):
            d[key] = fallback
    return d

# CRUD
def query_testcases(page: int, page_size: int,
    project_id: int, feature_id: int, priority: str, scenario: str,
    dimension: str, status: str, stage: str, keyword: str
    ):
    """分页/筛选测试用例（join features 取项目维度与需求编号），返回 (items, total)"""
    where = "where 1=1"
    params = []
    if project_id:
        where += " and f.project_id = ?"
        params.append(project_id)
    if feature_id:
        where += " and t.feature_id = ?"
        params.append(feature_id)
    if priority:
        where += " and t.priority = ?"
        params.append(priority)
    if scenario:
        where += " and t.scenario = ?"
        params.append(scenario)
    if dimension:
        where += " and t.dimension = ?"
        params.append(dimension)
    if status:
        where += " and t.status = ?"
        params.append(status)
    if stage:
        # stages 为 JSON 数组字符串，按元素包含匹配
        where += " and t.stages like ?"
        params.append(f'%"{stage}"%')
    if keyword:
        where += " and t.title like ?"
        params.append(f"%{keyword}%")

    conn = _connect()
    total = conn.execute(
        f"""
        select count(*) as c
        from testcases t
        join features f on t.feature_id = f.id
        {where}
        """,
        params
    ).fetchone()["c"]
    rows = conn.execute(
        f"""
        select t.*, f.feature_no as feature_ref, f.project_id
        from testcases t
        join features f on t.feature_id = f.id
        {where}
        order by t.created_at desc, t.id desc
        limit ? offset ?
        """,
        params + [page_size, (page-1)*page_size]
    ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows], total

def insert_testcase(
    feature_id: int, title: str, module:str,
    priority: str, dimension: str, scenario: str, stages, precondition: str,
    steps, expected: str
    ) -> dict:
    """新建用例"""
    now = datetime.now().isoformat()
    conn = _connect()

    testcase_no = _next_testcase_no(conn, feature_id)

    cur = conn.execute(
        """
        insert into testcases(feature_id, testcase_no, title, module, priority, status, dimension, scenario, stages, precondition, steps, expected, created_at, updated_at)
        values (?,?,?,?,?,'open',?,?,?,?,?,?,?,?)
        """, 
        (feature_id,testcase_no,title, module,priority,dimension,scenario,json.dumps(stages, ensure_ascii=False),precondition,json.dumps(steps),expected, now, now)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return get_testcase(row_id)

def get_testcase(testcase_id: int) -> dict:
    """按 id 查询单个测试用例"""
    conn = _connect()
    row = conn.execute(
        "select * from testcases where id = ?",
        (testcase_id,)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)

ALLOWED_FIELDS = {"title","module","priority", "status","dimension","scenario","stages","precondition","steps","expected","actual"}
def update_testcase(id: int, fields: dict):
    """更新测试用例"""
    clean_fields = {k: v for k, v in fields.items() if k in ALLOWED_FIELDS}
    if not clean_fields:
        return get_testcase(id)

    if "status" in clean_fields and clean_fields["status"] not in STATUS_VALUES:
        raise ValueError("非法的用例状态，仅支持 open / pass / fail / blocked")
    if "priority" in clean_fields and clean_fields["priority"] not in PRIORITY_VALUES:
        raise ValueError("非法的优先级，仅支持 P0 / P1 / P2 / P3")
    if "stages" in clean_fields:
        invalid = [s for s in clean_fields["stages"] if s not in STAGE_VALUES]
        if invalid:
            raise ValueError("非法的测试阶段，仅支持 冒烟 / 通道 / 灰度 / 系统 / 回归 / 验收")

    for key in ("steps", "stages"):
        if key in clean_fields and not isinstance(clean_fields[key], str):
            # ensure_ascii=False：stages 含中文，需以原文存储才能支持 like 包含筛选
            clean_fields[key] = json.dumps(clean_fields[key], ensure_ascii=False)

    sets = ",".join(f"{k} = ?" for k in clean_fields)
    values = list(clean_fields.values()) + [datetime.now().isoformat(), id]

    conn = _connect()
    conn.execute(
        f"update testcases set {sets}, updated_at = ? where id = ?",
        values
    )
    conn.commit()
    conn.close()
    return get_testcase(id)

def delete_testcase(testcase_id: int):
    """删除测试用例"""
    conn = _connect()
    cur = conn.execute(
        "delete from testcases where id = ?",
        (testcase_id,)
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ============== Agent ==============
def upsert_testcase(
    feature_id: int, testcase_no: str, 
    title: str, module: str, priority: str, dimension: str, 
    scenario: str, stages, precondition: str, steps, expected: str
    ) -> dict:
    """按照(feature_id, testcase_no)保存"""
    now = datetime.now().isoformat()
    conn = _connect()

    existing = conn.execute(
        "select id from testcases where feature_id = ? and testcase_no = ?",
        (feature_id, testcase_no)
    ).fetchone()

    if existing:
        conn.execute(
            """
            update testcases
            set title = ?, module = ?, priority = ?, dimension = ?, scenario = ?, stages = ?, precondition = ?, steps = ?, expected = ?, updated_at = ?
            where id = ?
            """,
            (title, module, priority, dimension, scenario, json.dumps(stages, ensure_ascii=False), precondition, json.dumps(steps), expected, now, existing["id"])
        )
        row_id = existing["id"]
    else:
        cur = conn.execute(
            """
            insert into testcases(feature_id, testcase_no, title, module, priority, status, dimension, scenario, stages, precondition, steps, expected, created_at, updated_at)
            values (?,?,?,?,?,'open',?,?,?,?,?,?,?,?)
            """,
            (feature_id, testcase_no, title, module, priority, dimension, scenario, json.dumps(stages, ensure_ascii=False), precondition, json.dumps(steps), expected, now, now)
        )
        row_id = cur.lastrowid

    conn.commit()
    conn.close()
    return get_testcase(row_id)

def save_agent_testcases(project_id: int, testcases: list) -> dict:
    """批量入库 Agent 分析输出的用例数组：按 requirement_ref 匹配 feature_id，返回保存/跳过条数"""
    # 一次性查出该项目下 feature_no -> id 映射，供 requirement_ref 匹配
    conn = _connect()
    rows = conn.execute(
        "select id, feature_no from features where project_id = ?",
        (project_id,)
    ).fetchall()
    conn.close()
    no_to_id = {r["feature_no"]: r["id"] for r in rows}

    saved, skipped = 0, 0
    for item in testcases:
        testcase_no = (item.get("id") or "").strip()
        feature_id = no_to_id.get((item.get("requirement_ref") or "").strip())
        if not testcase_no or feature_id is None:
            skipped += 1  # 缺编号或引用的需求不存在：跳过，不阻塞整体
            continue
        priority = item.get("priority", "P2")
        if priority not in PRIORITY_VALUES:
            priority = "P2"  # Agent 输出非法值时回退默认
        # 阶段：过滤非法元素（兑底策略同 priority）
        stages = [s for s in item.get("stages", []) if s in STAGE_VALUES]
        upsert_testcase(
            feature_id=feature_id,
            testcase_no=testcase_no,
            title=item.get("title", ""),
            module=item.get("module", ""),
            priority=priority,
            dimension=item.get("dimension", ""),
            scenario=item.get("scenario", ""),
            stages=stages,
            precondition=item.get("precondition", ""),
            steps=item.get("steps", []),
            expected=item.get("expected", "")
        )
        saved += 1
    return {"saved": saved, "skipped": skipped}
