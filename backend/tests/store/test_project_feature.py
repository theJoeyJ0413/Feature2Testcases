"""project_store 与 feature_store 存储层测试：CRUD、级联、Agent 批量入库"""

import pytest

from app.services.feature_store import (
    delete_feature,
    get_feature,
    insert_feature,
    query_features,
    save_agent_features,
    upsert_feature,
    update_feature,
)
from app.services.history_store import get_history, insert_history, update_history
from app.services.project_store import (
    delete_project,
    get_project,
    insert_project,
    query_projects,
    update_project,
)
from app.services.testcases_store import get_testcase, insert_testcase


def _make_project(name="测试项目", source="manual"):
    return insert_project(name, "描述", source)


def _make_feature(project_id, title="需求标题"):
    return insert_feature(project_id, title, "描述", "模块", ["功能点"], {"性能": "良好"}, "manual")


def _make_testcase(feature_id, title="用例标题"):
    return insert_testcase(feature_id, title, "模块", "P2", "维度", "场景", ["冒烟"], "前置", ["步骤1"], "预期")


# ---------- project_store ----------
def test_project_crud():
    p = _make_project()
    assert p["source"] == "manual" and p["status"] == "active"
    assert get_project(p["id"])["name"] == "测试项目"

    updated = update_project(p["id"], {"name": "改名", "status": "archived", "bogus": 1})
    assert updated["name"] == "改名"
    assert updated["status"] == "archived"  # 白名单内生效
    assert "bogus" not in updated

    assert update_project(9999, {"name": "x"}) is None
    assert get_project(9999) is None


def test_project_query_filters_and_counts():
    p1 = _make_project("相册项目", source="manual")
    p2 = _make_project("笔记项目", source="agent")
    f = _make_feature(p1["id"])
    _make_testcase(f["id"])
    _make_testcase(f["id"], title="用例2")

    items, total = query_projects(1, 10)
    assert total == 2
    by_name = {i["name"]: i for i in items}
    assert by_name["相册项目"]["feature_count"] == 1
    assert by_name["相册项目"]["testcase_count"] == 2  # 跨表 join 统计
    assert by_name["笔记项目"]["feature_count"] == 0

    assert query_projects(1, 10, source="agent")[1] == 1
    assert query_projects(1, 10, keyword="相册")[1] == 1


def test_delete_project_cascades_and_unlinks_history():
    """删除项目：级联删用例/需求，并把关联历史记录清回未保存（防悬空）"""
    p = _make_project()
    f = _make_feature(p["id"])
    tc = _make_testcase(f["id"])

    tid = "a" * 32
    insert_history(tid, "任务", "text", "输入", "")
    update_history(tid, status="done", project_id=p["id"])

    # 另一项目及其关联记录不应受影响
    other = _make_project("其他项目")
    tid2 = "b" * 32
    insert_history(tid2, "任务2", "text", "输入", "")
    update_history(tid2, status="done", project_id=other["id"])

    result = delete_project(p["id"])
    assert result == {"deleted_testcases": 1, "deleted_features": 1, "unlinked_history": 1}
    assert get_project(p["id"]) is None
    assert get_feature(p["id"], f["id"]) is None
    assert get_testcase(tc["id"]) is None
    assert get_history(tid)["project_id"] == 0  # 已恢复未保存
    assert get_history(tid2)["project_id"] == other["id"]  # 未误伤

    assert delete_project(p["id"]) is None  # 重复删除返回 None


# ---------- feature_store ----------
def test_feature_crud_and_numbering():
    p = _make_project()
    f1 = _make_feature(p["id"], "需求一")
    f2 = _make_feature(p["id"], "需求二")
    assert f1["feature_no"] == "FEATURE-001"
    assert f2["feature_no"] == "FEATURE-002"

    items, total = query_features(p["id"])
    assert total == 2
    assert all("testcases_count" in i for i in items)

    updated = update_feature(p["id"], f1["id"], {"status": "analyzed", "functional": ["新功能点"]})
    assert updated["status"] == "analyzed"
    assert updated["functional"] == ["新功能点"]  # JSON 字段序列化往返

    with pytest.raises(ValueError):
        update_feature(p["id"], f1["id"], {"status": "bogus"})
    with pytest.raises(ValueError):
        update_feature(p["id"], f1["id"], {"priority": "P9"})

    assert update_feature(p["id"], 9999, {"title": "x"}) is None


def test_feature_delete_cascades_testcases():
    p = _make_project()
    f = _make_feature(p["id"])
    tc = _make_testcase(f["id"])

    assert delete_feature(p["id"], f["id"]) is True
    assert get_testcase(tc["id"]) is None  # 用例随需求级联删除
    assert delete_feature(p["id"], f["id"]) is False


def test_upsert_feature_overwrites():
    p = _make_project()
    created = upsert_feature(p["id"], "FEATURE-001", "原始标题", "", "", [], {}, source="agent")
    assert created["status"] == "analyzed"  # Agent 入库初始状态
    assert created["source"] == "agent"

    again = upsert_feature(p["id"], "FEATURE-001", "覆盖标题", "", "", [], {})
    assert again["id"] == created["id"]  # 同编号不新增
    assert again["title"] == "覆盖标题"
    assert query_features(p["id"])[1] == 1


def test_save_agent_features_batch():
    p = _make_project()
    result = save_agent_features(p["id"], [
        {"id": "FEATURE-001", "title": "合法", "priority": "P0"},
        {"id": "FEATURE-002", "title": "非法优先级", "priority": "P9"},  # 回退 P2
        {"id": "", "title": "缺编号"},  # 跳过
    ])
    assert result == {"saved": 2, "skipped": 1}
    items, _ = query_features(p["id"])
    by_no = {i["feature_no"]: i for i in items}
    assert by_no["FEATURE-001"]["priority"] == "P0"
    assert by_no["FEATURE-002"]["priority"] == "P2"
