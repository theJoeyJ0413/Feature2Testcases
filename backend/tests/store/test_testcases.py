"""testcases_store 存储层测试：CRUD、筛选、Agent 批量入库"""

import pytest

from app.services.feature_store import insert_feature
from app.services.project_store import insert_project
from app.services.testcases_store import (
    delete_testcase,
    get_testcase,
    insert_testcase,
    query_testcases,
    save_agent_testcases,
    update_testcase,
    upsert_testcase,
)


def _setup():
    """建一个项目 + 需求，返回 (project_id, feature_id)"""
    p = insert_project("用例项目", "", "manual")
    f = insert_feature(p["id"], "需求", "", "模块", [], {}, "manual")
    return p["id"], f["id"]


def _make_tc(feature_id, title="用例标题", **overrides):
    kw = dict(module="模块", priority="P2", dimension="功能", scenario="正常流",
              stages=["冒烟"], precondition="", steps=["步骤"], expected="预期")
    kw.update(overrides)
    return insert_testcase(feature_id, title, **kw)


# ---------- CRUD ----------
def test_insert_numbering_and_defaults():
    _, fid = _setup()
    tc1 = _make_tc(fid)
    tc2 = _make_tc(fid)
    assert tc1["testcase_no"] == "TC-001"
    assert tc2["testcase_no"] == "TC-002"
    assert tc1["status"] == "open"
    assert tc1["stages"] == ["冒烟"]
    assert tc1["steps"] == ["步骤"]


def test_update_and_validation():
    _, fid = _setup()
    tc = _make_tc(fid)

    updated = update_testcase(tc["id"], {"status": "pass", "actual": "实际结果", "stages": ["冒烟", "回归"]})
    assert updated["status"] == "pass"
    assert updated["actual"] == "实际结果"
    assert updated["stages"] == ["冒烟", "回归"]

    with pytest.raises(ValueError):
        update_testcase(tc["id"], {"status": "bogus"})
    with pytest.raises(ValueError):
        update_testcase(tc["id"], {"priority": "P9"})
    with pytest.raises(ValueError):
        update_testcase(tc["id"], {"stages": ["非法阶段"]})

    assert update_testcase(9999, {"title": "x"}) is None


def test_delete():
    _, fid = _setup()
    tc = _make_tc(fid)
    assert delete_testcase(tc["id"]) is True
    assert delete_testcase(tc["id"]) is False


# ---------- 查询筛选 ----------
def test_query_filters_join_and_stage():
    pid, fid = _setup()
    _make_tc(fid, title="登录成功", priority="P0", stages=["冒烟"])
    update_testcase(_make_tc(fid, title="登录失败", priority="P1", stages=["回归"], scenario="异常流")["id"],
                    {"status": "fail"})

    # 无筛选：join 后带需求编号与项目 id
    items, total = query_testcases(1, 10, None, None, None, None, None, None, None, None)
    assert total == 2
    assert items[0]["feature_ref"] == "FEATURE-001"
    assert items[0]["project_id"] == pid

    assert query_testcases(1, 10, pid, None, None, None, None, None, None, None)[1] == 2
    assert query_testcases(1, 10, None, fid, None, None, None, None, None, None)[1] == 2
    assert query_testcases(1, 10, None, None, "P0", None, None, None, None, None)[1] == 1
    assert query_testcases(1, 10, None, None, None, None, None, "fail", None, None)[1] == 1
    assert query_testcases(1, 10, None, None, None, None, None, None, "冒烟", None)[1] == 1  # 中文 stages like 匹配
    assert query_testcases(1, 10, None, None, None, None, None, None, None, "登录")[1] == 2
    assert query_testcases(1, 10, None, None, None, "异常流", None, None, None, None)[1] == 1
    assert query_testcases(1, 10, 9999, None, None, None, None, None, None, None)[1] == 0


# ---------- Agent 入库 ----------
def test_upsert_testcase_overwrites():
    _, fid = _setup()
    created = upsert_testcase(fid, "TC-001", "原始", "模块", "P2", "功能", "场景", [], "", [], "预期")
    assert created["status"] == "open"

    again = upsert_testcase(fid, "TC-001", "覆盖标题", "模块", "P2", "功能", "场景", [], "", [], "预期")
    assert again["id"] == created["id"]  # 同编号覆盖不新增
    assert again["title"] == "覆盖标题"
    assert query_testcases(1, 10, None, fid, None, None, None, None, None, None)[1] == 1


def test_save_agent_testcases_batch():
    pid, fid = _setup()  # feature_no = FEATURE-001
    result = save_agent_testcases(pid, [
        {"id": "TC-001", "requirement_ref": "FEATURE-001", "title": "合法",
         "priority": "P1", "stages": ["冒烟", "非法阶段"]},  # 非法阶段被过滤
        {"id": "TC-002", "requirement_ref": "FEATURE-999", "title": "引用不存在"},  # 跳过
        {"id": "", "requirement_ref": "FEATURE-001", "title": "缺编号"},  # 跳过
    ])
    assert result == {"saved": 1, "skipped": 2}
    saved = get_testcase(query_testcases(1, 10, None, fid, None, None, None, None, None, None)[0][0]["id"])
    assert saved["testcase_no"] == "TC-001"
    assert saved["stages"] == ["冒烟"]  # 非法元素被过滤
    assert saved["priority"] == "P1"
