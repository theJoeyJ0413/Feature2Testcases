"""projects 与 features 路由接口测试：CRUD、删除联动、Agent 入库、生成用例"""

import json

from app.services.history_store import insert_history, update_history


def _create_project(client, name="接口项目", source="manual"):
    resp = client.post("/api/projects", json={"name": name, "source": source})
    assert resp.status_code == 200
    return resp.json()


def _create_feature(client, project_id, title="接口需求"):
    resp = client.post(f"/api/features/{project_id}", json={"title": title})
    assert resp.status_code == 200
    return resp.json()


# ---------- projects ----------
def test_projects_crud_flow(client):
    # 参数校验：空名 422、非法来源 422
    assert client.post("/api/projects", json={"name": ""}).status_code == 422
    assert client.post("/api/projects", json={"name": "x", "source": "other"}).status_code == 422

    p = _create_project(client)
    assert p["source"] == "manual"

    body = client.get("/api/projects").json()
    assert body["total"] == 1 and body["items"][0]["id"] == p["id"]

    assert client.get(f"/api/projects/{p['id']}").status_code == 200
    assert client.get("/api/projects/9999").status_code == 404

    updated = client.put(f"/api/projects/{p['id']}", json={"name": "改名项目"}).json()
    assert updated["name"] == "改名项目"
    assert client.put("/api/projects/9999", json={"name": "x"}).status_code == 404


def test_delete_project_unlinks_history_via_api(client):
    """端到端回归：删除项目后，之前绑定的历史记录恢复未保存（防悬空）"""
    p = _create_project(client, name="悬空测试项目")
    tid = "d" * 32
    insert_history(tid, "关联任务", "text", "输入", "")
    update_history(tid, status="done", finished_at="2026-09-15T12:00:00")
    assert client.put(f"/api/history/{tid}", json={"project_id": p["id"]}).status_code == 200

    resp = client.delete(f"/api/projects/{p['id']}")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "deleted_testcases": 0, "deleted_features": 0, "unlinked_history": 1}

    detail = client.get(f"/api/history/{tid}").json()
    assert detail["project_id"] == 0  # 已恢复未保存
    assert client.get("/api/history?saved=true").json()["total"] == 0
    assert client.delete(f"/api/projects/{p['id']}").status_code == 404


# ---------- features ----------
def test_features_flow(client):
    assert client.get("/api/features/9999").status_code == 404
    assert client.post("/api/features/9999", json={"title": "x"}).status_code == 404

    p = _create_project(client)
    assert client.post(f"/api/features/{p['id']}", json={"title": "x", "priority": "P9"}).status_code == 422

    f = _create_feature(client, p["id"])
    assert f["feature_no"] == "FEATURE-001" and f["status"] == "open"

    body = client.get(f"/api/features/{p['id']}").json()
    assert body["total"] == 1

    updated = client.put(f"/api/features/{p['id']}/{f['id']}", json={"status": "closed", "priority": "P0"}).json()
    assert updated["status"] == "closed" and updated["priority"] == "P0"
    assert client.put(f"/api/features/{p['id']}/9999", json={"title": "x"}).status_code == 404

    assert client.delete(f"/api/features/{p['id']}/{f['id']}").json() == {"status": "ok"}
    assert client.delete(f"/api/features/{p['id']}/{f['id']}").status_code == 404


def test_save_agent_features_api(client):
    assert client.post("/api/features/9999/save-agent", json={"features": []}).status_code == 404

    p = _create_project(client)
    resp = client.post(f"/api/features/{p['id']}/save-agent", json={"features": [
        {"id": "FEATURE-001", "title": "需求一", "priority": "P1"},
        {"id": "", "title": "缺编号"},
    ]})
    assert resp.json() == {"saved": 1, "skipped": 1}
    assert client.get(f"/api/features/{p['id']}").json()["total"] == 1


# ---------- generate-testcases（mock LLM） ----------
class _FakeGenerator:
    def __init__(self, payload=None, error=None):
        self.payload, self.error = payload, error

    def testcases_generator(self, _text):
        if self.error:
            raise RuntimeError(self.error)
        return self.payload


def _patch_generator(monkeypatch, payload=None, error=None):
    monkeypatch.setattr(
        "app.api.routes.features.TestcasesGenerator",
        lambda: _FakeGenerator(payload=payload, error=error),
    )


def test_generate_testcases_success(client, monkeypatch):
    p = _create_project(client)
    f = _create_feature(client, p["id"])

    payload = "```json\n" + json.dumps({"testcases": [
        {"id": "TC-001", "title": "用例一", "requirement_ref": "被忽略的值", "priority": "P2", "stages": ["冒烟"]},
        {"id": "TC-002", "title": "用例二", "requirement_ref": ""},
    ]}, ensure_ascii=False) + "\n```"
    _patch_generator(monkeypatch, payload=payload)

    resp = client.post(f"/api/features/{p['id']}/{f['id']}/generate-testcases")
    assert resp.json() == {"saved": 2, "skipped": 0}

    # requirement_ref 被强制关联到当前需求
    items = client.get(f"/api/testcases?feature_id={f['id']}").json()["items"]
    assert len(items) == 2
    assert all(i["feature_ref"] == "FEATURE-001" for i in items)


def test_generate_testcases_llm_error_and_empty(client, monkeypatch):
    p = _create_project(client)
    f = _create_feature(client, p["id"])

    _patch_generator(monkeypatch, error="网络超时")
    assert client.post(f"/api/features/{p['id']}/{f['id']}/generate-testcases").status_code == 500

    _patch_generator(monkeypatch, payload=json.dumps({"testcases": []}))
    assert client.post(f"/api/features/{p['id']}/{f['id']}/generate-testcases").status_code == 500

    assert client.post(f"/api/features/{p['id']}/9999/generate-testcases").status_code == 404
