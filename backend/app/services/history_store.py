"""
SQLite CRUD for task_history（Agent 任务历史）

历史记录只存任务元数据与产物文件名，文档全文 / 需求点 / 测试用例等大块内容
仍保存在 output/<task_id>/ 目录中，详情接口按记录里的文件名从磁盘重建。
"""

from datetime import datetime
from pathlib import Path
import json
import re

from ..config import OUTPUT_ROOT
from .db_conn import _connect

STATUS_VALUES = {"pending", "running", "done", "failed"}


def init_history_db():
    """建表（幂等）"""
    conn = _connect()
    conn.execute(
        """
        create table if not exists task_history (
            task_id text primary key,
            title text not null default '',
            input_source text not null default 'text',
            input_text text not null default '',
            input_filename text not null default '',
            status text not null default 'pending',
            project_id integer not null default 0,
            error text not null default '',
            requirement_filename text not null default '',
            features_filename text not null default '',
            testcase_filename text not null default '',
            created_at text not null,
            finished_at text not null default ''
        )
        """
    )
    # 旧库迁移：补 project_id 列（0=未保存为项目），并清理早期遗留的 archived 列
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(task_history)")]
    if "project_id" not in cols:
        conn.execute("alter table task_history add column project_id integer not null default 0")
    if "archived" in cols:
        conn.execute("alter table task_history drop column archived")
    conn.commit()
    conn.close()


# helper functions
def extract_title(md_text: str, fallback: str = "") -> str:
    """从需求文档正文中提取标题（第一个一级标题），失败时回退 fallback"""
    m = re.search(r"^#\s+(.+)$", md_text or "", re.MULTILINE)
    if m:
        return m.group(1).strip()
    return (fallback or "").strip()


def _read_json(path: Path, key: str):
    """读取结构化产物（features_*.json / testcases_*.json），失败时回退空列表"""
    if not path.is_file():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get(key, [])
    except (json.JSONDecodeError, OSError):
        return []


def load_result_from_disk(task_id: str, row: dict = None):
    """按历史记录中的文件名从任务目录重建 result（形状与 GET /tasks/{id} 一致）

    文件被清理时对应字段降级为空，保证历史详情接口不因磁盘缺失而报错。
    """
    if row is None:
        row = get_history(task_id)
    if row is None:
        return None

    task_dir = OUTPUT_ROOT / task_id

    # 需求分析文档（md 全文 + 文件信息）
    requirement_info = None
    requirement_content = ""
    req_name = row.get("requirement_filename") or ""
    req_path = task_dir / req_name if req_name else None
    if req_path and req_path.is_file():
        requirement_content = req_path.read_text(encoding="utf-8", errors="ignore")
        requirement_info = {"filename": req_name, "size": req_path.stat().st_size}

    # 测试用例（xlsx 只取文件信息，结构化用例来自同时间戳的 json）
    testcase_info = None
    tc_name = row.get("testcase_filename") or ""
    tc_path = task_dir / tc_name if tc_name else None
    if tc_path and tc_path.is_file():
        testcase_info = {"filename": tc_name, "size": tc_path.stat().st_size}

    tc_json_path = task_dir / Path(tc_name).with_suffix(".json") if tc_name else None
    if tc_json_path and not tc_json_path.is_file():
        json_files = sorted(task_dir.glob("testcases_*.json"))  # 兜底：取最新的结构化产物
        tc_json_path = json_files[-1] if json_files else None

    features_name = row.get("features_filename") or ""

    return {
        "requirement": requirement_info,
        "testcase": testcase_info,
        "requirement_content": requirement_content,
        "features": _read_json(task_dir / features_name, "features") if features_name else [],
        "testcases": _read_json(tc_json_path, "testcases") if tc_json_path else [],
    }


# CRUD
def insert_history(task_id: str, title: str, input_source: str, input_text: str, input_filename: str) -> dict:
    """任务创建时写入一条历史记录（status=pending）"""
    conn = _connect()
    conn.execute(
        """
        insert into task_history (task_id, title, input_source, input_text, input_filename, status, created_at)
        values (?, ?, ?, ?, ?, 'pending', ?)
        """,
        (task_id, title, input_source, input_text, input_filename, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return get_history(task_id)


ALLOWED_FIELDS = {"title", "status", "project_id", "error", "requirement_filename", "features_filename", "testcase_filename", "finished_at"}
def update_history(task_id: str, **fields):
    """更新传入的字段（白名单过滤），返回更新后的记录，不存在则返回 None"""
    # project_id 统一归一化为整数（0=未保存/清空关联，防止异常类型入库）
    clean_fields = {
        k: int(v or 0) if k == "project_id" else v
        for k, v in fields.items() if k in ALLOWED_FIELDS
    }
    if not clean_fields:
        return get_history(task_id)

    if "status" in clean_fields and clean_fields["status"] not in STATUS_VALUES:
        raise ValueError("非法的任务状态，仅支持 pending / running / done / failed")

    sets = ",".join(f"{k} = ?" for k in clean_fields)
    values = list(clean_fields.values()) + [task_id]

    conn = _connect()
    conn.execute(f"update task_history set {sets} where task_id = ?", values)
    conn.commit()
    conn.close()
    return get_history(task_id)


def get_history(task_id: str):
    """查询单条历史记录"""
    conn = _connect()
    row = conn.execute(
        "select * from task_history where task_id = ?",
        (task_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def query_history(page: int, page_size: int, keyword: str = None, status: str = None, saved: bool = None):
    """历史列表：分页 + 关键字（标题 / 输入内容）+ 状态 / 保存联动筛选，按创建时间倒序，返回 (items, total)

    saved 传 None 表示不筛（全部）；False 只看未保存为项目，True 只看已保存为项目。
    注意必须用 is not None 判断——False 是有效筛选值，不能用真值判断跳过。
    """
    where = "where 1=1"
    params = []
    if status:
        where += " and status = ?"
        params.append(status)
    if saved is not None:
        where += " and project_id > 0" if saved else " and project_id = 0"
    if keyword:
        where += " and (title like ? or input_text like ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]

    conn = _connect()
    total = conn.execute(
        f"select count(*) as c from task_history {where}", params
    ).fetchone()["c"]
    rows = conn.execute(
        f"""
        select * from task_history
        {where}
        order by created_at desc, rowid desc
        limit ? offset ?
        """,
        params + [page_size, (page - 1) * page_size],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def delete_history(task_id: str) -> bool:
    """删除历史记录，返回是否存在"""
    conn = _connect()
    cur = conn.execute("delete from task_history where task_id = ?", (task_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ============= 启动回填 =============
def backfill_history() -> int:
    """把 output 目录下尚未入库的旧任务补进历史（幂等），返回补录条数

    旧任务缺少元数据：标题取需求文档首行（回退 input.txt 前 20 字），
    时间取任务目录的修改时间，状态统一按 done 处理。
    """
    if not OUTPUT_ROOT.is_dir():
        return 0

    count = 0
    for task_dir in sorted(OUTPUT_ROOT.iterdir()):
        if not task_dir.is_dir() or get_history(task_dir.name) is not None:
            continue

        req_files = sorted(task_dir.glob("requirements_*.md"))
        if not req_files:
            continue  # 没有需求文档的目录不算完整任务（如遗留空目录）
        req_file = req_files[-1]
        features_files = sorted(task_dir.glob("features_*.json"))
        testcase_files = sorted(task_dir.glob("testcases_*.xlsx"))

        input_file = task_dir / "input.txt"
        input_text = input_file.read_text(encoding="utf-8", errors="ignore") if input_file.is_file() else ""

        # 非 txt 的 input.* 说明当时走的是文件上传
        upload_files = [p for p in task_dir.glob("input.*") if p.suffix.lower() != ".txt"]

        created = datetime.fromtimestamp(task_dir.stat().st_mtime).isoformat()
        title = extract_title(
            req_file.read_text(encoding="utf-8", errors="ignore"),
            input_text.strip()[:20] or "未命名任务",
        )
        conn = _connect()
        conn.execute(
            """
            insert or ignore into task_history
                (task_id, title, input_source, input_text, status,
                 requirement_filename, features_filename, testcase_filename, created_at, finished_at)
            values (?, ?, ?, ?, 'done', ?, ?, ?, ?, ?)
            """,
            (
                task_dir.name,
                title,
                "file" if upload_files else "text",
                input_text,
                req_file.name,
                features_files[-1].name if features_files else "",
                testcase_files[-1].name if testcase_files else "",
                created,
                created,
            ),
        )
        conn.commit()
        conn.close()
        count += 1
    return count
