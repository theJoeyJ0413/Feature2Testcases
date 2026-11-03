"""
SQLite CRUD for features
"""
from datetime import datetime
import json
import re

from .db_conn import _connect

STATUS_VALUES = {"open", "analyzed", "closed"}
PRIORITY_VALUES = {"P0", "P1", "P2", "P3"}

def init_features_db():
    """建表（幂等），并对已存在的旧表做列迁移"""
    conn = _connect()
    conn.execute(
        """
        create table if not exists features (
            id integer primary key autoincrement,
            project_id integer not null,
            feature_no text not null,
            title text not null,
            description text default '',
            module text not null default '',
            functional text not null default '[]',
            non_functional text not null default '{}',
            source text not null check (source in ('agent', 'manual')),
            status text not null default 'open',
            priority text not null default 'P2',
            created_at text not null,
            updated_at text not null,
            foreign key(project_id) references projects(id),
            unique(project_id, feature_no)
        )
        """
    )
    # 旧库迁移：features 表已存在但缺 priority 列时补列
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(features)")]
    if "priority" not in cols:
        conn.execute("alter table features add column priority text not null default 'P2'")
    conn.commit()
    conn.close()

# helper functions
def _next_feature_no(conn, project_id:int) -> str:
    """扫描当前项目下所有需求编号，取数字后缀最大值 + 1"""
    rows = conn.execute(
        "select feature_no from features where project_id = ?",
        (project_id,)
    ).fetchall()
    max_seq = 0
    for r in rows:
        m = re.search(r"(\d+)$", r["feature_no"])
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    return f"FEATURE-{max_seq + 1:03d}"

def _row_to_dict(row):
    """数据库row - dict，并把 JSON 字段反序列化"""
    if row is None:
        return None
    d = dict(row)
    for key, fallback in (("functional", []), ("non_functional", {})):
        try:
            d[key] = json.loads(d[key])
        except (json.JSONDecodeError, TypeError):
            d[key] = fallback  # 解析失败回退为空结构
    return d

# CRUD
def query_features(project_id:int):
    """查询项目下的所有需求（含每个需求的测试用例数），返回 (items, total)"""
    conn = _connect()
    total = conn.execute(
        "select count(*) as c from features where project_id = ?",
        (project_id,)
    ).fetchone()["c"]
    rows = conn.execute(
        """
        select f.*, ifnull(t.cnt, 0) as testcases_count 
        from features f
        left join (
            select feature_id, count(*) as cnt 
            from testcases 
            group by feature_id
        ) t on t.feature_id = f.id
        where f.project_id = ? 
        order by f.created_at desc, f.id desc
        """,
        (project_id,)
    ).fetchall()
    conn.close()
    return [_row_to_dict(row) for row in rows], total

def insert_feature(project_id: int, title:str, description:str, module: str, functional, non_functional, source:str, priority:str="P2")->dict:
    """在当前项目下新建需求"""
    now = datetime.now().isoformat()
    conn = _connect()

    feature_no = _next_feature_no(conn, project_id)

    cur = conn.execute(
        """
        insert into features (project_id, feature_no, title, description, module, functional, non_functional, source, status, priority, created_at, updated_at)
        values (?,?,?,?,?,?,?,?,'open',?,?,?)
        """,
        (project_id, feature_no, title, description, module, json.dumps(functional), json.dumps(non_functional), source, priority, now, now)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return get_feature(project_id, row_id)

def get_feature(project_id:int, id:int):
    """查询项目下的单个需求"""
    conn = _connect()
    row = conn.execute(
        """
        select * from features where id = ? and project_id = ?
        """,
        (id, project_id)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)

def get_feature_by_id(id: int):
    """按ID查询单个需求"""
    conn = _connect()
    row = conn.execute(
        "select * from features where id = ?",
        (id,)
    ).fetchone()
    conn.close()
    return _row_to_dict(row=row)

ALLOWED_FIELDS = {"title", "description", "module", "functional", "non_functional", "status", "priority"}
def update_feature(project_id:int, id: int, fields: dict):
    """更新新传入的字段，返回更新后的记录，不存在则返回None"""
    # 白名单过滤：只保留允许修改的字段
    clean_fields = {k: v for k, v in fields.items() if k in ALLOWED_FIELDS}
    if not clean_fields:
        return get_feature(project_id, id)
    
    if "status" in clean_fields and clean_fields["status"] not in STATUS_VALUES:
        raise ValueError("非法的需求状态，仅支持 open / analyzed / closed")
    if "priority" in clean_fields and clean_fields["priority"] not in PRIORITY_VALUES:
        raise ValueError("非法的优先级，仅支持 P0 / P1 / P2 / P3")

    # JSON 字段序列化：传 list/dict 就要 dumps
    for key in ("functional", "non_functional"):
        if key in clean_fields and not isinstance(clean_fields[key], str):
            clean_fields[key] = json.dumps(clean_fields[key])

    # 拼接与执行
    sets = ",".join(f"{k} = ?" for k in clean_fields)
    values = list(clean_fields.values()) + [datetime.now().isoformat(), project_id, id]

    conn = _connect()
    conn.execute(
        f"update features set {sets}, updated_at = ? where project_id = ? and id = ?", 
        values
    )
    conn.commit()
    conn.close()
    return get_feature(project_id, id)


def delete_feature(project_id:int, id:int):
    """删除项目下的单个需求"""
    conn = _connect()

    conn.execute(
        "delete from testcases where feature_id = ?",
        (id,)
    )
    cur = conn.execute(
        "delete from features where project_id = ? and id=?",
        (project_id,id)
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ============= Agent =============
def upsert_feature(project_id:int, feature_no:str, title:str, description:str, module:str, functional, non_functional, source:str="agent", priority:str="P2") -> dict:
    """按照(project_id, feature_no)保存：已存在-覆盖；不存在则insert（仅Agent入库）"""
    now = datetime.now().isoformat()
    conn = _connect()

    existing = conn.execute(
        "select id from features where project_id = ? and feature_no = ?",
        (project_id, feature_no)
    ).fetchone()

    if existing:
        conn.execute(
            """
            update features
            set title = ?, description = ?, module = ?, functional = ?, non_functional = ?, source = ?, priority = ?, updated_at = ?
            where id = ?
            """,
            (title, description, module, json.dumps(functional), json.dumps(non_functional), source, priority, now, existing["id"])
        )
        row_id = existing["id"]
    else:
        cur = conn.execute(
            """
            insert into
            features(project_id, feature_no, title, description, module, functional, non_functional, source, status, priority, created_at, updated_at)
            values (?,?,?,?,?,?,?,?,'analyzed',?,?,?)
            """,
            (project_id, feature_no, title, description, module, json.dumps(functional), json.dumps(non_functional), source, priority, now, now)
        )
        row_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return get_feature(project_id, row_id)

def save_agent_features(project_id: int, features: list) -> dict:
    """批量入库 Agent 分析输出的 features 数组，返回保存/跳过条数"""
    saved, skipped = 0, 0
    for item in features:
        feature_no = (item.get("id") or "").strip()
        if not feature_no:
            skipped += 1
            continue
        priority = item.get("priority", "P2")
        if priority not in PRIORITY_VALUES:
            priority = "P2"  # Agent 输出非法值时回退默认
        upsert_feature(
            project_id=project_id,
            feature_no=feature_no,
            title=item.get("title", ""),
            description=item.get("description", ""),
            module=item.get("module", ""),
            functional=item.get("functional", []),
            non_functional=item.get("non_functional", {}),
            source="agent",
            priority=priority,
        )
        saved += 1
    return {"saved": saved, "skipped": skipped}

