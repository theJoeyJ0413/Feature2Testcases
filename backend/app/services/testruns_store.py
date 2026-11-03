"""
SQLite store for test runs

数据模型：
- test_runs：运行批次（项目、模式、范围、筛选条件、状态）
- test_run_items：批次内用例快照 + 本次执行结果

快照策略：items 保存用例标题、步骤、预期等字段，运行结束后用例被编辑或删除
也不影响历史记录；testcase_id / feature_id 使用 on delete set null。
"""

from datetime import datetime, timedelta
import json
import re

from .db_conn import _connect
from .testcases_store import PRIORITY_VALUES, STAGE_VALUES

MODE_VALUES = {"smoke", "full", "regression", "custom"}
RUN_STATUS_VALUES = {"running", "completed"}
RESULT_VALUES = {"open", "pass", "fail", "blocked"}

COUNT_KEYS = (
    "total_count", "executed_count", "passed_count",
    "failed_count", "blocked_count", "open_count",
)


def init_testruns_db():
    """建表（幂等）"""
    conn = _connect()
    conn.execute(
        """
        create table if not exists test_runs (
            id integer primary key autoincrement,
            run_no text not null unique,
            project_id integer not null,
            mode text not null default 'smoke',
            scope text not null default '{"type":"all"}',
            priority text not null default '',
            stage text not null default '',
            status text not null default 'running',
            created_at text not null,
            started_at text not null,
            finished_at text,
            foreign key(project_id) references projects(id) on delete cascade
        )
        """
    )
    conn.execute(
        """
        create table if not exists test_run_items (
            id integer primary key autoincrement,
            run_id integer not null,
            testcase_id integer,
            feature_id integer,
            testcase_no text not null,
            title text not null,
            feature_no text not null default '',
            feature_title text not null default '',
            module text not null default '',
            priority text not null default 'P2',
            dimension text not null default '',
            scenario text not null default '',
            stages text not null default '[]',
            precondition text not null default '',
            steps text not null default '[]',
            expected text not null default '',
            result text not null default 'open',
            actual text not null default '',
            remark text not null default '',
            executed_at text,
            created_at text not null,
            updated_at text not null,
            foreign key(run_id) references test_runs(id) on delete cascade,
            foreign key(testcase_id) references testcases(id) on delete set null,
            foreign key(feature_id) references features(id) on delete set null
        )
        """
    )
    conn.execute(
        "create index if not exists idx_test_runs_project on test_runs(project_id, created_at)"
    )
    conn.execute(
        "create index if not exists idx_test_run_items_run on test_run_items(run_id)"
    )
    conn.commit()
    conn.close()


# ============== helpers ==============
def _next_run_no(conn) -> str:
    """生成 R-YYYYMMDD-NN，按天递增"""
    prefix = f"R-{datetime.now().strftime('%Y%m%d')}-"
    rows = conn.execute(
        "select run_no from test_runs where run_no like ?",
        (prefix + "%",)
    ).fetchall()
    max_seq = 0
    for r in rows:
        m = re.search(r"(\d+)$", r["run_no"])
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    return f"{prefix}{max_seq + 1:02d}"


def _rates(total: int, executed: int, passed: int) -> dict:
    return {
        "execution_rate": round(executed * 100.0 / total, 1) if total else 0.0,
        "pass_rate": round(passed * 100.0 / executed, 1) if executed else 0.0,
    }


def _stats_from_counts(row) -> dict:
    """把 SQL 聚合结果转成统一的统计结构"""
    total = row["total_count"]
    executed = row["executed_count"]
    passed = row["passed_count"]
    return {
        "total": total,
        "executed": executed,
        "passed": passed,
        "failed": row["failed_count"],
        "blocked": row["blocked_count"],
        "open": row["open_count"],
        **_rates(total, executed, passed),
    }


def _row_to_run(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    try:
        d["scope"] = json.loads(d["scope"])
    except (json.JSONDecodeError, TypeError):
        d["scope"] = {"type": "all"}
    return d


def _row_to_item(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for key, fallback in (("stages", []), ("steps", [])):
        try:
            d[key] = json.loads(d[key])
        except (json.JSONDecodeError, TypeError):
            d[key] = fallback
    return d


def _run_with_stats(row) -> dict:
    """运行行 + 聚合统计，移除临时的 count 字段"""
    run = _row_to_run(row)
    run.update(_stats_from_counts(row))
    for key in COUNT_KEYS:
        run.pop(key, None)
    return run


def _counts_for_run(conn, run_id: int):
    return conn.execute(
        """
        select
            count(*) as total_count,
            coalesce(sum(case when result != 'open' then 1 else 0 end), 0) as executed_count,
            coalesce(sum(case when result = 'pass' then 1 else 0 end), 0) as passed_count,
            coalesce(sum(case when result = 'fail' then 1 else 0 end), 0) as failed_count,
            coalesce(sum(case when result = 'blocked' then 1 else 0 end), 0) as blocked_count,
            coalesce(sum(case when result = 'open' then 1 else 0 end), 0) as open_count
        from test_run_items
        where run_id = ?
        """,
        (run_id,)
    ).fetchone()


# ============== query ==============
def query_testruns(page: int, page_size: int,
    project_id: int, status: str, mode: str, keyword: str
    ):
    """分页/筛选查询运行批次，返回 (items, total)，items 内含统计"""
    if status and status not in RUN_STATUS_VALUES:
        raise ValueError("非法的运行状态，仅支持 running / completed")
    if mode and mode not in MODE_VALUES:
        raise ValueError("非法的运行模式")

    where = "where 1=1"
    params = []
    if project_id:
        where += " and r.project_id = ?"
        params.append(project_id)
    if status:
        where += " and r.status = ?"
        params.append(status)
    if mode:
        where += " and r.mode = ?"
        params.append(mode)
    if keyword:
        where += " and r.run_no like ?"
        params.append(f"%{keyword}%")

    conn = _connect()
    total = conn.execute(
        f"select count(*) as c from test_runs r {where}",
        params
    ).fetchone()["c"]
    rows = conn.execute(
        f"""
        select r.*, p.name as project_name,
            count(i.id) as total_count,
            coalesce(sum(case when i.result != 'open' then 1 else 0 end), 0) as executed_count,
            coalesce(sum(case when i.result = 'pass' then 1 else 0 end), 0) as passed_count,
            coalesce(sum(case when i.result = 'fail' then 1 else 0 end), 0) as failed_count,
            coalesce(sum(case when i.result = 'blocked' then 1 else 0 end), 0) as blocked_count,
            coalesce(sum(case when i.result = 'open' then 1 else 0 end), 0) as open_count
        from test_runs r
        join projects p on p.id = r.project_id
        left join test_run_items i on i.run_id = r.id
        {where}
        group by r.id
        order by r.created_at desc, r.id desc
        limit ? offset ?
        """,
        params + [page_size, (page - 1) * page_size]
    ).fetchall()
    conn.close()
    return [_run_with_stats(row) for row in rows], total


def get_testrun(run_id: int):
    """运行详情：批次信息 + 统计 + 用例清单，不存在返回 None"""
    conn = _connect()
    row = conn.execute(
        """
        select r.*, p.name as project_name
        from test_runs r
        join projects p on p.id = r.project_id
        where r.id = ?
        """,
        (run_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return None

    counts = _counts_for_run(conn, run_id)
    items = conn.execute(
        """
        select * from test_run_items
        where run_id = ?
        order by feature_id is null, feature_id asc, id asc
        """,
        (run_id,)
    ).fetchall()
    conn.close()

    run = _row_to_run(row)
    run.update(_stats_from_counts(counts))
    run["items"] = [_row_to_item(item) for item in items]
    return run


def get_testrun_stats(project_id: int = None, days: int = 30) -> dict:
    """按时间窗口统计运行情况（执行率 / 通过率），可按项目筛选"""
    since = (datetime.now() - timedelta(days=days)).isoformat()
    where = "where r.created_at >= ?"
    params = [since]
    if project_id:
        where += " and r.project_id = ?"
        params.append(project_id)

    conn = _connect()
    row = conn.execute(
        f"""
        select
            count(distinct r.id) as run_count,
            count(i.id) as total_count,
            coalesce(sum(case when i.result != 'open' then 1 else 0 end), 0) as executed_count,
            coalesce(sum(case when i.result = 'pass' then 1 else 0 end), 0) as passed_count,
            coalesce(sum(case when i.result = 'fail' then 1 else 0 end), 0) as failed_count,
            coalesce(sum(case when i.result = 'blocked' then 1 else 0 end), 0) as blocked_count,
            coalesce(sum(case when i.result = 'open' then 1 else 0 end), 0) as open_count
        from test_runs r
        left join test_run_items i on i.run_id = r.id
        {where}
        """,
        params
    ).fetchone()
    conn.close()

    stats = _stats_from_counts(row)
    stats["run_count"] = row["run_count"]
    stats["days"] = days
    return stats


# ============== create / update ==============
def create_testrun(project_id: int, mode: str, scope: dict,
    priority: str = None, stage: str = None
    ) -> dict:
    """创建运行批次：按项目/需求/优先级/阶段快照用例，初始结果均为 open"""
    if mode not in MODE_VALUES:
        raise ValueError("非法的运行模式，仅支持 smoke / full / regression / custom")
    if priority and priority not in PRIORITY_VALUES:
        raise ValueError("非法的优先级，仅支持 P0 / P1 / P2 / P3")
    if stage and stage not in STAGE_VALUES:
        raise ValueError("非法的测试阶段，仅支持 冒烟 / 通道 / 灰度 / 系统 / 回归 / 验收")

    scope = scope or {"type": "all"}
    scope_type = scope.get("type", "all")
    if scope_type not in ("all", "features"):
        raise ValueError("非法的运行范围类型，仅支持 all / features")

    feature_ids = []
    if scope_type == "features":
        try:
            feature_ids = sorted({int(fid) for fid in scope.get("feature_ids", [])})
        except (TypeError, ValueError):
            raise ValueError("feature_ids 必须为整数数组")
        if not feature_ids:
            raise ValueError("指定需求运行时，feature_ids 不能为空")
        scope = {"type": "features", "feature_ids": feature_ids}
    else:
        scope = {"type": "all"}

    conn = _connect()
    try:
        if feature_ids:
            placeholders = ",".join("?" for _ in feature_ids)
            found = conn.execute(
                f"""
                select count(*) as c from features
                where project_id = ? and id in ({placeholders})
                """,
                [project_id, *feature_ids]
            ).fetchone()["c"]
            if found != len(feature_ids):
                raise ValueError("部分需求不存在或不属于该项目")

        where = "where f.project_id = ?"
        params = [project_id]
        if feature_ids:
            where += f" and t.feature_id in ({','.join('?' for _ in feature_ids)})"
            params.extend(feature_ids)
        if priority:
            where += " and t.priority = ?"
            params.append(priority)
        if stage:
            where += " and t.stages like ?"
            params.append(f'%"{stage}"%')

        rows = conn.execute(
            f"""
            select t.*, f.feature_no, f.title as feature_title
            from testcases t
            join features f on t.feature_id = f.id
            {where}
            order by f.id asc, t.testcase_no asc
            """,
            params
        ).fetchall()
        if not rows:
            raise ValueError("没有符合条件的测试用例")

        now = datetime.now().isoformat()
        run_no = _next_run_no(conn)
        cur = conn.execute(
            """
            insert into test_runs
                (run_no, project_id, mode, scope, priority, stage, status, created_at, started_at)
            values (?, ?, ?, ?, ?, ?, 'running', ?, ?)
            """,
            (
                run_no, project_id, mode,
                json.dumps(scope, ensure_ascii=False),
                priority or "", stage or "", now, now,
            )
        )
        run_id = cur.lastrowid

        conn.executemany(
            """
            insert into test_run_items
                (run_id, testcase_id, feature_id, testcase_no, title,
                 feature_no, feature_title, module, priority, dimension, scenario,
                 stages, precondition, steps, expected, created_at, updated_at)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id, r["id"], r["feature_id"], r["testcase_no"], r["title"],
                    r["feature_no"], r["feature_title"], r["module"], r["priority"],
                    r["dimension"], r["scenario"], r["stages"], r["precondition"],
                    r["steps"], r["expected"], now, now,
                )
                for r in rows
            ]
        )
        conn.commit()
    finally:
        conn.close()

    return get_testrun(run_id)


def update_run_item(run_id: int, item_id: int, fields: dict):
    """记录单条用例结果；已结束的批次不可修改。结果同步回写 testcases.status"""
    clean_fields = {k: v for k, v in fields.items() if k in {"result", "actual", "remark"}}
    if "result" in clean_fields and clean_fields["result"] not in RESULT_VALUES:
        raise ValueError("非法的执行结果，仅支持 open / pass / fail / blocked")
    if not clean_fields:
        return get_run_item(run_id, item_id)

    conn = _connect()
    try:
        run = conn.execute(
            "select status from test_runs where id = ?",
            (run_id,)
        ).fetchone()
        if run is None:
            return None
        if run["status"] != "running":
            raise ValueError("运行已结束，不能再修改结果")

        item = conn.execute(
            "select * from test_run_items where id = ? and run_id = ?",
            (item_id, run_id)
        ).fetchone()
        if item is None:
            return None

        now = datetime.now().isoformat()
        if "result" in clean_fields:
            clean_fields["executed_at"] = (
                None if clean_fields["result"] == "open" else now
            )
        clean_fields["updated_at"] = now

        sets = ",".join(f"{k} = ?" for k in clean_fields)
        conn.execute(
            f"update test_run_items set {sets} where id = ? and run_id = ?",
            list(clean_fields.values()) + [item_id, run_id]
        )

        if "result" in clean_fields and item["testcase_id"] is not None:
            conn.execute(
                "update testcases set status = ?, updated_at = ? where id = ?",
                (clean_fields["result"], now, item["testcase_id"])
            )

        conn.commit()
        row = conn.execute(
            "select * from test_run_items where id = ?",
            (item_id,)
        ).fetchone()
        return _row_to_item(row)
    finally:
        conn.close()


def get_run_item(run_id: int, item_id: int):
    """查询批次内的单条用例结果"""
    conn = _connect()
    row = conn.execute(
        "select * from test_run_items where id = ? and run_id = ?",
        (item_id, run_id)
    ).fetchone()
    conn.close()
    return _row_to_item(row)


def finish_testrun(run_id: int):
    """结束运行批次（幂等），返回最新详情；不存在返回 None"""
    conn = _connect()
    row = conn.execute(
        "select status from test_runs where id = ?",
        (run_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return None

    if row["status"] == "running":
        conn.execute(
            "update test_runs set status = 'completed', finished_at = ? where id = ?",
            (datetime.now().isoformat(), run_id)
        )
        conn.commit()
    conn.close()
    return get_testrun(run_id)
