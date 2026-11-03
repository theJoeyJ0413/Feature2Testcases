"""history 路由接口测试：列表筛选、详情重建、回写防护、删除与路径安全"""

import json

from app.services.history_store import insert_history, update_history

TID = "0123456789abcdef0123456789abcdef"


def _insert_done(task_id=TID, title="已完成任务", **extra):
    insert_history(task_id, title, "text", "输入内容", "")
    return update_history(task_id, status="done", finished_at="2026-09-15T12:00:00", **extra)


def test_list_empty_and_param_validation(client):
    resp = client.get("/api/history")
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}

    assert client.get("/api/history?page=0").status_code == 422
    assert client.get("/api/history?page_size=101").status_code == 422


def test_list_saved_filter_three_states(client):
    _insert_done("a" * 32, title="已保存")
    update_history("a" * 32, project_id=7)
    _insert_done("b" * 32, title="未保存")

    assert client.get("/api/history").json()["total"] == 2
    assert client.get("/api/history?saved=true").json()["total"] == 1
    items = client.get("/api/history?saved=false").json()["items"]
    assert len(items) == 1 and items[0]["title"] == "未保存"


def test_list_status_keyword_pagination(client):
    _insert_done("a" * 32, title="手机相册需求")
    insert_history("b" * 32, "读书笔记需求", "text", "输入", "")

    assert client.get("/api/history?status=pending").json()["total"] == 1
    assert client.get("/api/history?keyword=相册").json()["total"] == 1
    body = client.get("/api/history?page=2&page_size=1").json()
    assert body["total"] == 2 and len(body["items"]) == 1


def test_get_detail_404_and_rebuild(client, output_root):
    assert client.get("/api/history/no-such-task").status_code == 404

    task_dir = output_root / TID
    task_dir.mkdir(parents=True)
    (task_dir / "requirements_20260915.md").write_text("# 需求文档\n正文", encoding="utf-8")
    (task_dir / "features_20260915.json").write_text(
        json.dumps({"features": [{"id": "FEATURE-001"}]}), encoding="utf-8"
    )
    _insert_done(requirement_filename="requirements_20260915.md", features_filename="features_20260915.json")

    body = client.get(f"/api/history/{TID}").json()
    assert body["status"] == "done"
    assert body["result"]["requirement"]["filename"] == "requirements_20260915.md"
    assert body["result"]["features"] == [{"id": "FEATURE-001"}]
    assert body["result"]["testcases"] == []


def test_put_backfill_flow(client):
    # 不存在 → 404
    assert client.put("/api/history/no-such-task", json={"project_id": 1}).status_code == 404
    # 未完成 → 400
    insert_history("c" * 32, "进行中", "text", "输入", "")
    assert client.put(f"/api/history/{'c' * 32}", json={"project_id": 1}).status_code == 400
    # 非法 project_id：0 / 缺失 → 422
    _insert_done()
    assert client.put(f"/api/history/{TID}", json={"project_id": 0}).status_code == 422
    assert client.put(f"/api/history/{TID}", json={}).status_code == 422
    # 正常回写
    resp = client.put(f"/api/history/{TID}", json={"project_id": 5})
    assert resp.status_code == 200
    assert resp.json()["project_id"] == 5
    assert client.get(f"/api/history/{TID}").json()["project_id"] == 5


def test_delete_removes_history_and_task_dir(client, output_root):
    task_dir = output_root / TID
    task_dir.mkdir(parents=True)
    (task_dir / "requirements_x.md").write_text("x", encoding="utf-8")
    _insert_done()

    resp = client.delete(f"/api/history/{TID}")
    assert resp.status_code == 200 and resp.json() == {"deleted": True}
    assert not task_dir.exists()  # 任务目录被清理
    assert client.delete(f"/api/history/{TID}").status_code == 404


def test_delete_non_hex_task_id_keeps_dir_safe(client, output_root):
    """非 uuid4().hex 格式的 task_id：只删记录，不触碰任何目录（路径安全）"""
    odd_id = "abc"
    task_dir = output_root / odd_id
    task_dir.mkdir(parents=True)
    (task_dir / "keep.md").write_text("x", encoding="utf-8")
    _insert_done(task_id=odd_id)

    assert client.delete(f"/api/history/{odd_id}").status_code == 200
    assert (task_dir / "keep.md").exists()  # 目录未被删除
