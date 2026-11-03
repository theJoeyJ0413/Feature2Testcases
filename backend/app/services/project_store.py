"""
SQLite CRUD for projects
"""

from datetime import datetime

from .db_conn import _connect

def init_projects_db():
    """建表"""
    conn = _connect()
    conn.execute(
        """
        create table if not exists projects (
            id integer primary key autoincrement,
            name text not null,
            description text default '',
            source text not null check (source in ('agent', 'manual')),
            status text not null default 'active',
            created_at text not null,
            updated_at text not null
        )
        """
    )
    conn.commit()
    conn.close()

# CRUD
def insert_project(name:str, description:str, source:str)->dict:
    """新建项目"""
    now = datetime.now().isoformat()
    conn = _connect()
    cur = conn.execute(
        """
        insert into projects (name, description, source, status, created_at, updated_at)
        values (?, ?, ?, 'active', ?, ?)
        """,
        (name, description, source, now, now)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return get_project(row_id)

def get_project(project_id:int):
    """查询单个项目"""
    conn = _connect()
    row = conn.execute(
        """
        select * from projects where id = ?
        """,
        (project_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def query_projects(page:int, page_size:int, source:str=None, keyword:str=None):
    """分页/筛选查询项目"""
    where = "where 1=1"
    params = []
    if source:
        where += " and source = ?"
        params.append(source)
    if keyword:
        where += " and name like ?"
        params.append(f"%{keyword}%")

    conn = _connect()
    total = conn.execute(
        f"SELECT COUNT(*) AS c FROM projects {where}", params
    ).fetchone()["c"]
    rows = conn.execute(
        f"""
        select p.*, 
        ifnull(f.cnt, 0) as feature_count,
        ifnull(t.cnt, 0) as testcase_count
        from projects p
        left join (
            select project_id, count(*) as cnt from features group by project_id
        ) f on p.id = f.project_id
        left join (
            select f2.project_id, count(*) as cnt
            from testcases tc
            join features f2 on tc.feature_id = f2.id
            group by f2.project_id
        ) t on p.id = t.project_id
        {where} 
        order by p.created_at desc, p.id desc
        limit ? offset ?
        """,
        params + [page_size, (page-1)*page_size],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


ALLOWED_FIELDS = {"name", "description", "status"}
def update_project(project_id:int, fields: dict):
    """更新新传入的字段，返回更新后的记录，不存在则返回None"""
    clean_fields = {k:v for k,v in fields.items() if k in ALLOWED_FIELDS}
    if not clean_fields:
        return get_project(project_id)
    sets = ",".join(f"{k} = ?" for k in clean_fields)
    values = list(clean_fields.values()) + [datetime.now().isoformat(), project_id]

    conn = _connect()
    conn.execute(
        f"update projects set {sets}, updated_at = ? where id = ?", values
    )
    conn.commit()
    conn.close()
    return get_project(project_id)


def delete_project(project_id:int):
    """删除项目，级联删除关联的需求和测试用例，并把历史记录的保存联动清回未保存（防悬空）"""
    conn = _connect()
    
    cur_testcases = conn.execute(
        "delete from testcases where feature_id in (select id from features where project_id=?)",
        (project_id,)
    )
    cur_features = conn.execute("delete from features where project_id = ?", (project_id,))
    cur_project = conn.execute("delete from projects where id = ?", (project_id,))
    # 历史记录防悬空：项目已不存在，指向它的保存联动统一清回 0（未保存）
    cur_history = conn.execute(
        "update task_history set project_id = 0 where project_id = ?",
        (project_id,)
    )
    
    conn.commit()
    conn.close()

    if cur_project.rowcount == 0:
        return None
    return {
        "deleted_testcases": cur_testcases.rowcount,
        "deleted_features": cur_features.rowcount,
        "unlinked_history": cur_history.rowcount,
    }
