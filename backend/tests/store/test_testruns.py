"""testruns_store 存储层测试：批次快照、筛选、结果记录、统计与结束运行"""

import pytest

from app.services.feature_store import insert_feature
from app.services.project_store import delete_project, insert_project
from app.services.testcases_store import delete_testcase, get_testcase, insert_testcase
from app.services.testruns_store import (
    create_testrun,
    finish_testrun,
    get_testrun,
    get_testrun_stats,
    query_testruns,
    update_run_item,
)


def _setup():
    """建一个项目 + 两个需求 + 三条用例"""
    p = insert_project("运行项目", "", "manual")
    f1 = insert_feature(p["id"], "用户注册", "", "用户", [], {}, "manual")
    f2 = insert_feature(p["id"], "用户登录", "", "用户", [], {}, "manual")
    tc1 = _make_tc(f1["id"], "注册成功", "P0", ["冒烟"])
    tc2 = _make_tc(f1["id"], "注册格式非法", "P1", ["回归"])
    tc3 = _make_tc(f2["id"], "登录成功", "P0", ["冒烟"])
    return p["id"], f1["id"], f2["id"], [tc1, tc2, tc3]


def _make_tc(feature_id, title, priority="P2", stages=None):
    return insert_testcase(
        feature_id, title, "模块", priority, "功能", "正向",
        stages or ["冒烟"], "前置", ["步骤"], "预期"
    )


def test_create_run_snapshots_cases_and_defaults():
    pid, _, _, _ = _setup()
    run = create_testrun(pid, "smoke", {"type": "all"})

    assert run["run_no"].startswith("R-")
    assert run["project_id"] == pid
    assert run["project_name"] == "运行项目"
    assert run["mode"] == "smoke"
    assert run["scope"] == {"type": "all"}
    assert run["status"] == "running"
    assert run["total"] == 3
    assert run["executed"] == 0
    assert run["execution_rate"] == 0.0
    assert run["pass_rate"] == 0.0
    assert len(run["items"]) == 3

    first = run["items"][0]
    assert first["title"] == "注册成功"
    assert first["feature_no"] == "FEATURE-001"
    assert first["stages"] == ["冒烟"]
    assert first["steps"] == ["步骤"]
    assert first["result"] == "open"


def test_create_run_filters_by_feature_priority_stage():
    pid, f1, f2, _ = _setup()

    run = create_testrun(pid, "full", {"type": "features", "feature_ids": [f1]}, "P0")
    assert [i["title"] for i in run["items"]] == ["注册成功"]

    run = create_testrun(pid, "regression", {"type": "all"}, None, "冒烟")
    assert {i["title"] for i in run["items"]} == {"注册成功", "登录成功"}

    with pytest.raises(ValueError, match="没有符合条件"):
        create_testrun(pid, "smoke", {"type": "features", "feature_ids": [f2]}, "P3")
    with pytest.raises(ValueError, match="部分需求"):
        create_testrun(pid, "smoke", {"type": "features", "feature_ids": [9999]})
    with pytest.raises(ValueError, match="feature_ids 不能为空"):
        create_testrun(pid, "smoke", {"type": "features", "feature_ids": []})
    with pytest.raises(ValueError):
        create_testrun(pid, "bogus", {"type": "all"})
    with pytest.raises(ValueError):
        create_testrun(pid, "smoke", {"type": "all"}, "P9")


def test_update_item_records_result_and_stats():
    pid, _, _, _ = _setup()
    run = create_testrun(pid, "smoke", {"type": "all"})
    first = run["items"][0]

    updated = update_run_item(run["id"], first["id"], {"result": "pass", "actual": "注册成功"})
    assert updated["result"] == "pass"
    assert updated["actual"] == "注册成功"
    assert updated["executed_at"] is not None
    assert get_testcase(first["testcase_id"])["status"] == "pass"

    detail = get_testrun(run["id"])
    assert detail["executed"] == 1
    assert detail["passed"] == 1
    assert detail["execution_rate"] == 33.3
    assert detail["pass_rate"] == 100.0

    update_run_item(run["id"], run["items"][1]["id"], {"result": "fail"})
    detail = get_testrun(run["id"])
    assert detail["executed"] == 2
    assert detail["failed"] == 1
    assert detail["pass_rate"] == 50.0

    update_run_item(run["id"], first["id"], {"result": "open"})
    assert get_testcase(first["testcase_id"])["status"] == "open"
    detail = get_testrun(run["id"])
    assert detail["executed"] == 1
    assert detail["passed"] == 0
    assert detail["pass_rate"] == 0.0

    with pytest.raises(ValueError, match="非法的执行结果"):
        update_run_item(run["id"], first["id"], {"result": "bogus"})
    assert update_run_item(run["id"], 9999, {"result": "pass"}) is None
    assert update_run_item(9999, first["id"], {"result": "pass"}) is None


def test_finish_locks_run():
    pid, _, _, _ = _setup()
    run = create_testrun(pid, "smoke", {"type": "all"})

    finished = finish_testrun(run["id"])
    assert finished["status"] == "completed"
    assert finished["finished_at"] is not None

    with pytest.raises(ValueError, match="运行已结束"):
        update_run_item(run["id"], run["items"][0]["id"], {"result": "pass"})

    assert finish_testrun(run["id"])["status"] == "completed"
    assert finish_testrun(9999) is None


def test_run_history_survives_testcase_delete():
    pid, _, _, _ = _setup()
    run = create_testrun(pid, "smoke", {"type": "all"})
    item = run["items"][0]

    assert delete_testcase(item["testcase_id"]) is True
    detail = get_testrun(run["id"])
    kept = next(i for i in detail["items"] if i["id"] == item["id"])
    assert kept["testcase_id"] is None
    assert kept["title"] == item["title"]
    assert kept["feature_no"] == "FEATURE-001"


def test_query_and_global_stats():
    pid, f1, _, _ = _setup()
    run1 = create_testrun(pid, "smoke", {"type": "all"})
    run2 = create_testrun(pid, "full", {"type": "features", "feature_ids": [f1]}, "P0")
    update_run_item(run1["id"], run1["items"][0]["id"], {"result": "pass"})
    update_run_item(run2["id"], run2["items"][0]["id"], {"result": "fail"})
    finish_testrun(run2["id"])

    items, total = query_testruns(1, 10, pid, None, None, None)
    assert total == 2
    assert {i["mode"] for i in items} == {"smoke", "full"}
    assert all("execution_rate" in i for i in items)
    assert items[0]["id"] == run2["id"]  # 最新批次在前

    items, total = query_testruns(1, 10, pid, "running", None, None)
    assert total == 1 and items[0]["mode"] == "smoke"

    items, total = query_testruns(1, 10, pid, "completed", "full", run2["run_no"])
    assert total == 1 and items[0]["id"] == run2["id"]

    with pytest.raises(ValueError):
        query_testruns(1, 10, pid, "bogus", None, None)

    stats = get_testrun_stats(pid, 30)
    assert stats["run_count"] == 2
    assert stats["total"] == 4
    assert stats["executed"] == 2
    assert stats["passed"] == 1
    assert stats["failed"] == 1
    assert stats["execution_rate"] == 50.0
    assert stats["pass_rate"] == 50.0

    empty = get_testrun_stats(9999, 30)
    assert empty["run_count"] == 0 and empty["total"] == 0


def test_project_delete_cascades_runs():
    pid, _, _, _ = _setup()
    run = create_testrun(pid, "smoke", {"type": "all"})

    result = delete_project(pid)
    assert result["deleted_testcases"] == 3
    assert get_testrun(run["id"]) is None
    assert query_testruns(1, 10, None, None, None, None)[1] == 0
