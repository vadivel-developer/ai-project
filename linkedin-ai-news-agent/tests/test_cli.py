import sys

import main
from agent import pipeline, store


def run_cli(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["main.py", *argv])
    main.main()


def test_demo_list_skip(monkeypatch, capsys, cfg):
    monkeypatch.setattr(main, "load_config", lambda: cfg)
    run_cli(monkeypatch, "demo")
    run_cli(monkeypatch, "list")
    assert "demo0001  [drafted]" in capsys.readouterr().out
    run_cli(monkeypatch, "skip", "demo0001")
    assert store.list_all(store.connect())[0]["status"] == "skipped"


def test_approve_command(monkeypatch, capsys, cfg):
    monkeypatch.setattr(main, "load_config", lambda: cfg)
    run_cli(monkeypatch, "demo")
    monkeypatch.setattr(pipeline, "publish", lambda t, i: "urn:x")
    run_cli(monkeypatch, "approve", "demo0001")
    assert "published: urn:x" in capsys.readouterr().out


def test_run_command_calls_pipeline(monkeypatch, cfg):
    called = {}
    monkeypatch.setattr(main, "load_config", lambda: cfg)
    monkeypatch.setattr(pipeline, "create_drafts", lambda c, log=print: called.setdefault("ok", True))
    run_cli(monkeypatch, "run")
    assert called["ok"]
