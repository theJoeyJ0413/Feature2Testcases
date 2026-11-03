"""testcases 路由接口测试：筛选、手动创建、状态更新、Agent 入库、删除"""


def _create_project(client, name="用例接口项目"):
    return client.post("/api/projects", json={"name": name}).json()


def _create_feature(client, project_id):
    return client.post(f"/api/features/{project_id}", json={"title": "用例需求"}).json()


def _create_testcase(client, feature_id, title="接口用例"):
    resp = client.post("/api/testcases", json={
        "feature_id": feature_id, "title": title, "priority": "P1",
        "scenario": "正常流", "stages": ["冒烟"],
    })
    assert resp.status_code == 200
    return resp.json()


def test_list_filters(client):
    assert client.get("/api/testcases").json()["total"] == 0  # 初始为空

    p = _create_project(client)
    f = _create_feature(client, p["id"])
    _create_testcase(client, f["id"], "登录成功")
    tc2 = _create_testcase(client, f["id"], "登录失败")
    client.put(f"/api/testcases/{tc2['id']}", json={"status": "fail"})

    body = client.get(f"/api/testcases?project_id={p['id']}").json()
    assert body["total"] == 2
    assert body["items"][0]["feature_ref"] == "FEATURE-001"

    assert client.get(f"/api/testcases?feature_id={f['id']}").json()["total"] == 2
    assert client.get("/api/testcases?status=fail").json()["total"] == 1
    assert client.get("/api/testcases?stage=冒烟").json()["total"] == 2
    assert client.get("/api/testcases?keyword=登录").json()["total"] == 2
    assert client.get(f"/api/testcases?project_id=9999").json()["total"] == 0


def test_create_manual_validation(client):
    p = _create_project(client)
    f = _create_feature(client, p["id"])

    tc = _create_testcase(client, f["id"])
    assert tc["testcase_no"] == "TC-001"
    assert tc["status"] == "open"

    assert client.post("/api/testcases", json={"feature_id": f["id"], "title": ""}).status_code == 422
    assert client.post("/api/testcases", json={"feature_id": 9999, "title": "x"}).status_code == 404


def test_update_status_flow(client):
    p = _create_project(client)
    f = _create_feature(client, p["id"])
    tc = _create_testcase(client, f["id"])

    updated = client.put(f"/api/testcases/{tc['id']}", json={"status": "pass", "actual": "通过"}).json()
    assert updated["status"] == "pass" and updated["actual"] == "通过"

    # 非法状态被 Pydantic 拦截
    assert client.put(f"/api/testcases/{tc['id']}", json={"status": "bogus"}).status_code == 422
    assert client.put("/api/testcases/9999", json={"status": "pass"}).status_code == 404


def test_save_agent_testcases_api(client):
    assert client.post("/api/testcases/save-agent", json={"project_id": 9999, "testcases": []}).status_code == 404

    p = _create_project(client)
    f = _create_feature(client, p["id"])
    resp = client.post("/api/testcases/save-agent", json={
        "project_id": p["id"],
        "testcases": [
            {"id": "TC-001", "requirement_ref": f["feature_no"], "title": "Agent 用例", "stages": ["回归"]},
            {"id": "TC-002", "requirement_ref": "FEATURE-999", "title": "引用不存在"},
        ],
    })
    assert resp.json() == {"saved": 1, "skipped": 1}


def test_delete(client):
    p = _create_project(client)
    f = _create_feature(client, p["id"])
    tc = _create_testcase(client, f["id"])

    assert client.delete(f"/api/testcases/{tc['id']}").json() == {"status": "ok"}
    assert client.delete(f"/api/testcases/{tc['id']}").status_code == 404
    assert client.get("/api/testcases").json()["total"] == 0
