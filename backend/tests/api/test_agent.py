"""agent 路由接口测试：任务提交、状态回退历史、下载回退、模型设置"""

import json

from app.agents.unified_agent.config import Config
from app.services.history_store import insert_history, update_history


class _FakeExecutor:
    """替代线程池：只记录提交，不真正执行 pipeline（避免测试触发 LLM 调用）"""

    def __init__(self):
        self.calls = []

    def submit(self, fn, *args, **kwargs):
        self.calls.append((fn, args, kwargs))


def _insert_done(task_id, title="已完成任务", **extra):
    insert_history(task_id, title, "text", "输入内容", "")
    return update_history(task_id, status="done", finished_at="2026-09-15T12:00:00", **extra)


# ---------- 任务提交 ----------
def test_pipeline_submit_text(client, monkeypatch):
    fake = _FakeExecutor()
    monkeypatch.setattr("app.api.routes.agent.executor", fake)

    resp = client.post("/api/pipeline", data={"text": "请分析这个需求"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    assert len(task_id) == 32  # uuid4().hex

    assert len(fake.calls) == 1
    assert fake.calls[0][1] == (task_id, "请分析这个需求", None)  # submit(run_pipeline, task_id, text, None)

    task = client.get(f"/api/tasks/{task_id}").json()
    assert task["status"] == "pending"  # 内存任务优先
    assert task["result"] is None


def test_pipeline_submit_upload(client, monkeypatch):
    fake = _FakeExecutor()
    monkeypatch.setattr("app.api.routes.agent.executor", fake)

    resp = client.post("/api/pipeline", files={"file": ("req.txt", b"hello", "text/plain")})
    assert resp.status_code == 200
    assert fake.calls[0][1][2] == {"filename": "req.txt", "content": b"hello"}


def test_pipeline_validation(client):
    assert client.post("/api/pipeline", data={}).status_code == 400  # 既无文字也无文件
    assert client.post("/api/pipeline", files={"file": ("x.doc", b"data")}).status_code == 400  # 不支持的类型
    assert client.post("/api/pipeline", files={"file": ("x.txt", b"")}).status_code == 400  # 空文件


# ---------- 任务查询回退历史 ----------
def test_task_fallback_to_history(client, output_root):
    assert client.get(f"/api/tasks/{'0' * 32}").status_code == 404

    # pending 历史：无 result，stage 为空
    tid = "e" * 32
    insert_history(tid, "进行中任务", "text", "输入", "")
    body = client.get(f"/api/tasks/{tid}").json()
    assert body["status"] == "pending" and body["result"] is None and body["stage"] == ""

    # done 历史 + 磁盘产物：result 按文件名重建
    tid2 = "f" * 32
    task_dir = output_root / tid2
    task_dir.mkdir(parents=True)
    (task_dir / "requirements_20260915.md").write_text("# 需求文档\n正文", encoding="utf-8")
    (task_dir / "features_20260915.json").write_text(
        json.dumps({"features": [{"id": "FEATURE-001"}]}), encoding="utf-8"
    )
    _insert_done(tid2, requirement_filename="requirements_20260915.md", features_filename="features_20260915.json")

    body2 = client.get(f"/api/tasks/{tid2}").json()
    assert body2["status"] == "done" and body2["stage"] == "完成"
    assert body2["result"]["requirement"]["filename"] == "requirements_20260915.md"
    assert body2["result"]["features"] == [{"id": "FEATURE-001"}]


# ---------- 文件下载回退 ----------
def test_download_fallback_and_guards(client, output_root):
    tid = "f" * 32
    _insert_done(tid, requirement_filename="requirements_dl.md", testcase_filename="testcases_dl.xlsx")
    task_dir = output_root / tid
    task_dir.mkdir(parents=True)
    (task_dir / "requirements_dl.md").write_text("# 文档内容", encoding="utf-8")

    resp = client.get(f"/api/download/{tid}/requirement")
    assert resp.status_code == 200
    assert resp.content == "# 文档内容".encode("utf-8")

    assert client.get(f"/api/download/{tid}/testcase").status_code == 404  # 文件已被清理
    assert client.get(f"/api/download/{tid}/bogus").status_code == 404  # 非法类型
    assert client.get(f"/api/download/{'0' * 32}/requirement").status_code == 404  # 任务不存在


# ---------- 模型设置 ----------
def test_settings_get(client):
    body = client.get("/api/settings").json()
    assert set(body) == {"api_key_masked", "base_url", "model"}


def test_settings_update_writes_isolated_env(client, monkeypatch, tmp_path):
    # 参数校验：空值 400（在写文件之前拦截，无副作用）
    assert client.put("/api/settings", json={"model": "  "}).status_code == 400
    assert client.put("/api/settings", json={"base_url": ""}).status_code == 400

    # 隔离：ENV_FILE 指向临时文件，内存配置与环境变量由 monkeypatch 负责恢复
    env_file = tmp_path / ".env"
    monkeypatch.setattr("app.api.routes.agent_settings.ENV_FILE", env_file)
    monkeypatch.setattr(Config, "OPENAI_MODEL", Config.OPENAI_MODEL)
    monkeypatch.setattr(Config, "OPENAI_BASE_URL", Config.OPENAI_BASE_URL)
    monkeypatch.setattr(Config, "OPENAI_API_KEY", Config.OPENAI_API_KEY)
    monkeypatch.setenv("OPENAI_MODEL", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    resp = client.put("/api/settings", json={
        "api_key": "sk-test-1234567890",
        "base_url": "https://example.com/v1",
        "model": "test-model",
    })
    assert resp.json() == {"status": "ok"}
    assert Config.OPENAI_MODEL == "test-model"
    text = env_file.read_text(encoding="utf-8")
    assert "OPENAI_MODEL" in text and "test-model" in text
    assert "OPENAI_API_KEY" in text
