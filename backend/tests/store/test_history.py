"""history_store 存储层测试：CRUD、筛选、磁盘结果重建、启动回填"""

import json

import pytest

from app.services.history_store import (
    backfill_history,
    delete_history,
    extract_title,
    get_history,
    insert_history,
    load_result_from_disk,
    query_history,
    update_history,
)

TID = "0123456789abcdef0123456789abcdef"


def _insert(task_id=TID, title="测试任务", input_text="输入内容"):
    return insert_history(task_id, title, "text", input_text, "")


def _to_done(task_id=TID, **extra):
    return update_history(task_id, status="done", finished_at="2026-09-15T12:00:00", **extra)


# ---------- 基础 CRUD ----------
def test_insert_and_get():
    row = _insert()
    assert row["task_id"] == TID
    assert row["title"] == "测试任务"
    assert row["status"] == "pending"
    assert row["project_id"] == 0
    assert row["created_at"]


def test_update_whitelist_and_invalid_status():
    _insert()
    row = update_history(TID, title="新标题", unknown_field="x")
    assert row["title"] == "新标题"
    assert "unknown_field" not in row  # 白名单外字段被过滤

    with pytest.raises(ValueError):
        update_history(TID, status="bogus")


def test_update_project_id_normalized():
    _insert()
    assert update_history(TID, project_id="5")["project_id"] == 5  # str 归一化为 int
    assert update_history(TID, project_id=None)["project_id"] == 0  # None 清回未保存


def test_update_missing_task_returns_none():
    assert update_history("no-such-task", title="x") is None
    assert get_history("no-such-task") is None


# ---------- 查询筛选 ----------
def test_query_saved_filter_false_is_valid():
    """saved=False 必须生效筛选未保存（False 是有效值，经典陷阱）"""
    _insert("a" * 32, title="已保存")
    update_history("a" * 32, project_id=7)
    _insert("b" * 32, title="未保存")
    _insert("c" * 32, title="未保存2")

    assert query_history(1, 10)[1] == 3
    assert query_history(1, 10, saved=True)[1] == 1
    items, total = query_history(1, 10, saved=False)
    assert total == 2


def test_query_status_and_keyword():
    _insert("a" * 32, title="需求A", input_text="手机相册")
    _to_done("a" * 32)
    _insert("b" * 32, title="需求B", input_text="读书笔记")

    assert query_history(1, 10, status="done")[1] == 1
    assert query_history(1, 10, status="pending")[1] == 1
    assert query_history(1, 10, keyword="相册")[1] == 1  # 命中 input_text
    assert query_history(1, 10, keyword="需求")[1] == 2  # 命中 title


def test_query_pagination():
    for i in range(3):
        _insert(f"{i:032x}", title=f"任务{i}")
    page1 = query_history(1, 2)
    page2 = query_history(2, 2)
    assert len(page1[0]) == 2 and page1[1] == 3
    assert len(page2[0]) == 1 and page2[1] == 3


def test_delete_history():
    _insert()
    assert delete_history(TID) is True
    assert delete_history(TID) is False


# ---------- 辅助函数 ----------
def test_extract_title():
    assert extract_title("# 我的需求文档\n正文") == "我的需求文档"
    assert extract_title("没有标题", fallback="兜底") == "兜底"
    assert extract_title("", fallback="") == ""


# ---------- 磁盘结果重建 ----------
def test_load_result_missing_files_degrades_gracefully():
    """记录存在但磁盘文件缺失：不报错，字段降级为空"""
    _insert()
    _to_done(requirement_filename="req.md", features_filename="f.json", testcase_filename="t.xlsx")
    result = load_result_from_disk(TID)
    assert result["requirement"] is None
    assert result["requirement_content"] == ""
    assert result["features"] == [] and result["testcases"] == []


def test_load_result_rebuild_from_disk(output_root):
    task_dir = output_root / TID
    task_dir.mkdir(parents=True)
    (task_dir / "requirements_20260915.md").write_text("# 需求文档\n内容", encoding="utf-8")
    (task_dir / "features_20260915.json").write_text(
        json.dumps({"features": [{"id": "FEATURE-001"}]}), encoding="utf-8"
    )
    (task_dir / "testcases_20260915.xlsx").write_bytes(b"fake-xlsx")
    (task_dir / "testcases_20260915.json").write_text(
        json.dumps({"testcases": [{"id": "TC-001"}]}), encoding="utf-8"
    )

    _insert()
    _to_done(
        requirement_filename="requirements_20260915.md",
        features_filename="features_20260915.json",
        testcase_filename="testcases_20260915.xlsx",
    )
    result = load_result_from_disk(TID)
    assert result["requirement"]["filename"] == "requirements_20260915.md"
    assert result["requirement"]["size"] > 0
    assert result["requirement_content"].startswith("# 需求文档")
    assert result["features"] == [{"id": "FEATURE-001"}]
    assert result["testcases"] == [{"id": "TC-001"}]
    assert result["testcase"]["filename"] == "testcases_20260915.xlsx"

    assert load_result_from_disk("no-such-task") is None


# ---------- 启动回填 ----------
def test_backfill_history(output_root):
    tid = "f" * 32
    task_dir = output_root / tid
    task_dir.mkdir(parents=True)
    (task_dir / "requirements_20260901.md").write_text("# 回填任务标题\n正文", encoding="utf-8")
    (task_dir / "input.txt").write_text("原始输入", encoding="utf-8")
    # 无需求文档的目录不算完整任务，应被跳过
    (output_root / ("e" * 32)).mkdir()

    assert backfill_history() == 1
    row = get_history(tid)
    assert row["status"] == "done"
    assert row["title"] == "回填任务标题"
    assert row["input_source"] == "text"
    assert row["requirement_filename"] == "requirements_20260901.md"

    assert backfill_history() == 0  # 幂等：已入库的不再补


def test_backfill_no_output_dir():
    assert backfill_history() == 0  # OUTPUT_ROOT 不存在时安全返回
