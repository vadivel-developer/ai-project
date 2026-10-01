import pytest

import app as webapp
from agent import pipeline


@pytest.fixture
def client(cfg, monkeypatch):
    monkeypatch.setattr(webapp, "load_config", lambda: cfg)
    return webapp.app.test_client()


def test_index_page_served(client):
    r = client.get("/")
    assert r.status_code == 200 and b"AI News Studio" in r.data


def test_config_endpoint(client):
    assert client.get("/api/config").json == {"company": "Acme AI"}


def test_empty_list(client):
    assert client.get("/api/drafts").json == []


def test_demo_then_list_has_card_and_text(client):
    assert client.post("/api/demo").json["ok"]
    d = client.get("/api/drafts").json[0]
    assert d["status"] == "drafted" and d["has_image"] and d["card"]["title"] and "#AI" in d["text"]


def test_image_endpoint_returns_png(client):
    client.post("/api/demo")
    r = client.get("/api/drafts/demo0001/image")
    assert r.status_code == 200 and r.mimetype == "image/png"


def test_save_text(client):
    client.post("/api/demo")
    client.post("/api/drafts/demo0001", json={"text": "new text"})
    assert client.get("/api/drafts").json[0]["text"] == "new text"


def test_regenerate_image_updates_card(client):
    client.post("/api/demo")
    r = client.post("/api/drafts/demo0001/image",
                    json={"title": "T2", "description": "D2", "new_background": False})
    assert r.json["ok"]
    assert client.get("/api/drafts").json[0]["card"] == {"title": "T2", "description": "D2", "prompt": ""}


def test_skip(client):
    client.post("/api/demo")
    client.post("/api/drafts/demo0001/skip")
    assert client.get("/api/drafts").json[0]["status"] == "skipped"


def test_approve_success_and_failure(client, monkeypatch):
    client.post("/api/demo")
    monkeypatch.setattr(pipeline, "publish", lambda t, i: "urn:1")
    r = client.post("/api/drafts/demo0001/approve")
    assert r.json == {"ok": True, "urn": "urn:1"}
    assert client.get("/api/drafts").json[0]["status"] == "published"


def test_approve_error_returns_message_not_crash(client, monkeypatch):
    client.post("/api/demo")
    def boom(t, i):
        raise RuntimeError("LinkedIn said no")
    monkeypatch.setattr(pipeline, "publish", boom)
    r = client.post("/api/drafts/demo0001/approve")
    assert r.status_code == 400 and "LinkedIn said no" in r.json["error"]


def test_run_endpoint_reports_error_cleanly(client, monkeypatch):
    def boom(cfg, log=None):
        raise RuntimeError("missing key")
    monkeypatch.setattr(pipeline, "create_drafts", boom)
    r = client.post("/api/run")
    assert r.status_code == 400 and r.json["error"] == "missing key"


def test_bad_id_does_not_escape_drafts_folder(client):
    assert client.get("/api/drafts/..%2Fsecret/image").status_code in (400, 404, 500)
