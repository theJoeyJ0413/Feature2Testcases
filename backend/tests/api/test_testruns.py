"""testruns 路由接口测试：创建、列表、记录结果、统计、结束运行"""


def _create_project(client, name="运行接口项目"):
    return client.post("/api/projects", json={"name": name}).json()


def _create_feature(client, project_id, title="运行需求"):
    return client.post(f"/api/features/{project_id}", json={"title": title}).json()


def _create_testcase(client, feature_id, title="运行用例", priority="P2", stages=None):
    resp = client.post("/api/testcases", json={
        "feature_id": feature_id,
        "title": title,
        "priority": priority,
        "stages": stages or ["冒烟"],
    })
    assert resp.status_code == 200
    return resp.json()


def _create_run(client, project_id, **overrides):
    body = {
        "project_id": project_id,
        "mode": "smoke",
        "scope": {"type": "all"},
    }
    body.update(overrides)
    return client.post("/api/testruns", json=body)


def test_create_list_and_detail(client):
    p = _create_project(client)
    f = _create_feature(client, p["id"])
    _create_testcase(client, f["id"], "注册成功", "P0")
    _create_testcase(client, f["id"], "注册失败", "P1")

    resp = _create_run(client, p["id"])
    assert resp.status_code == 200
    run = resp.json()
    assert run["run_no"].startswith("R-")
    assert run["total"] == 2
    assert run["status"] == "running"
    assert run["project_name"] == "运行接口项目"
    assert len(run["items"]) == 2

    body = client.get("/api/testruns").json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == run["id"]
    assert body["items"][0]["total"] == 2

    detail = client.get(f"/api/testruns/{run['id']}").json()
    assert detail["id"] == run["id"]
    assert len(detail["items"]) == 2

    assert client.get("/api/testruns/9999").status_code == 404
    assert client.post("/api/testruns", json={"project_id": 9999}).status_code == 404


def test_create_validation(client):
    p = _create_project(client)
    f = _create_feature(client, p["id"])
    _create_testcase(client, f["id"])

    assert _create_run(client, p["id"], mode="bogus").status_code == 422
    assert _create_run(client, p["id"], scope={"type": "features", "feature_ids": []}).status_code == 400
    assert _create_run(client, p["id"], scope={"type": "features", "feature_ids": [9999]}).status_code == 400
    assert _create_run(client, p["id"], priority="P9").status_code == 422

    empty_project = _create_project(client, "空项目")
    assert _create_run(client, empty_project["id"]).status_code == 400


def test_update_item_syncs_testcase_and_finish(client):
    p = _create_project(client)
    f = _create_feature(client, p["id"])
    _create_testcase(client, f["id"])
    run = _create_run(client, p["id"]).json()
    item = run["items"][0]

    resp = client.patch(f"/api/testruns/{run['id']}/items/{item['id']}", json={
        "result": "pass",
        "actual": "实际通过",
    })
    assert resp.status_code == 200
    assert resp.json()["result"] == "pass"

    tc_after = client.get(f"/api/testcases?feature_id={f['id']}").json()["items"][0]
    assert tc_after["status"] == "pass"

    detail = client.get(f"/api/testruns/{run['id']}").json()
    assert detail["executed"] == 1
    assert detail["execution_rate"] == 100.0
    assert detail["pass_rate"] == 100.0

    finished = client.post(f"/api/testruns/{run['id']}/finish").json()
    assert finished["status"] == "completed"
    assert finished["finished_at"] is not None

    assert client.patch(
        f"/api/testruns/{run['id']}/items/{item['id']}", json={"result": "fail"}
    ).status_code == 409
    assert client.patch(
        "/api/testruns/9999/items/9999", json={"result": "fail"}
    ).status_code == 404
    assert client.post("/api/testruns/9999/finish").status_code == 404


def test_list_filters_and_stats(client):
    p = _create_project(client)
    f = _create_feature(client, p["id"])
    _create_testcase(client, f["id"], "用例一", "P0")
    _create_testcase(client, f["id"], "用例二", "P1")

    run1 = _create_run(client, p["id"], mode="smoke").json()
    run2 = _create_run(client, p["id"], mode="full").json()
    client.patch(
        f"/api/testruns/{run1['id']}/items/{run1['items'][0]['id']}",
        json={"result": "pass"},
    )
    client.patch(
        f"/api/testruns/{run2['id']}/items/{run2['items'][0]['id']}",
        json={"result": "fail"},
    )
    client.post(f"/api/testruns/{run2['id']}/finish")

    assert client.get(f"/api/testruns?project_id={p['id']}").json()["total"] == 2
    assert client.get(f"/api/testruns?project_id={p['id']}&mode=full").json()["total"] == 1
    assert client.get(f"/api/testruns?project_id={p['id']}&status=completed").json()["total"] == 1
    assert client.get(f"/api/testruns?project_id={p['id']}&keyword={run1['run_no']}").json()["total"] == 1
    assert client.get("/api/testruns?project_id=9999").json()["total"] == 0

    stats = client.get(f"/api/testruns/stats?project_id={p['id']}&days=30").json()
    assert stats["run_count"] == 2
    assert stats["total"] == 4
    assert stats["executed"] == 2
    assert stats["passed"] == 1
    assert stats["failed"] == 1
    assert stats["execution_rate"] == 50.0
    assert stats["pass_rate"] == 50.0
    assert stats["days"] == 30

    assert client.get("/api/testruns/stats?days=0").status_code == 422
