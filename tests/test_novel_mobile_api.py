"""Tests for novel_mobile FastAPI routes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "applications" / "novel_cursor"))
sys.path.insert(0, str(_root / "src"))

from app_config import NovelAppConfig
from novel_mobile.server import create_app


def _config(tmp_path: Path) -> NovelAppConfig:
    out = tmp_path / "out"
    out.mkdir()
    (out / "session_id.txt").write_text("mn_fixture\n", encoding="utf-8")
    return NovelAppConfig(
        app_id="shenjia_caifa",
        seed_md=tmp_path / "seed.md",
        title="工匠傳奇",
        output_dir=out,
        chapter_dir=out / "chapters",
        snapshot_file=out / "session_snap.json",
        session_id_file=out / "session_id.txt",
        last_beat_file=out / "last_beat.json",
        agents_dir=out / "agents",
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    monkeypatch.setattr("novel_mobile.server.probe_serve", lambda: True)
    monkeypatch.setattr("novel_mobile.server._llm_configured", lambda: True)
    monkeypatch.setattr(
        "novel_mobile.server.read_player_setup",
        lambda session, **kw: {
            "exit_code": 0,
            "setup_complete": False,
            "setup_guidance": {"next_action": "narrate_open"},
            "profile": {},
            "loadout": {},
        },
    )
    app = create_app(cfg)
    return TestClient(app)


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "工匠傳奇"
    assert data["ok"] is True


def test_setup_returns_guidance(client):
    r = client.get("/api/setup")
    assert r.status_code == 200
    assert "setup_guidance" in r.json()


def test_beat_409_when_job_active(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    monkeypatch.setattr("novel_mobile.server.probe_serve", lambda: True)
    monkeypatch.setattr("novel_mobile.server._llm_configured", lambda: True)
    monkeypatch.setattr(
        "novel_mobile.server.read_player_setup",
        lambda session, **kw: {"exit_code": 0, "setup_complete": True},
    )
    from novel_mobile.jobs import BeatJob, BeatJobStore
    import time

    store = BeatJobStore()
    job = BeatJob("jid", "running", time.time(), time.time())
    store._jobs[job.job_id] = job
    monkeypatch.setattr("novel_mobile.server._job_store", store)

    app = create_app(cfg)
    tc = TestClient(app)
    r = tc.post("/api/beat", json={"choice": 1})
    assert r.status_code == 409


def test_auth_required_when_token_set(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    monkeypatch.setattr("novel_mobile.server.probe_serve", lambda: True)
    monkeypatch.setattr("novel_mobile.server._llm_configured", lambda: True)
    monkeypatch.setattr(
        "novel_mobile.server.read_player_setup",
        lambda session, **kw: {"exit_code": 0, "setup_complete": False},
    )
    app = create_app(cfg, auth_token="secret")
    tc = TestClient(app)
    r = tc.get("/api/health")
    assert r.status_code == 401
    r2 = tc.get("/api/health", headers={"Authorization": "Bearer secret"})
    assert r2.status_code == 200


def test_player_sheet_route(tmp_path, monkeypatch):
    cfg = _config(tmp_path)
    monkeypatch.setattr("novel_mobile.server.probe_serve", lambda: True)
    monkeypatch.setattr("novel_mobile.server._llm_configured", lambda: True)
    monkeypatch.setattr(
        "novel_mobile.server.read_player_sheet",
        lambda session, **kw: {"exit_code": 0, "items": [], "arts": [], "production": {"nodes": []}},
    )
    app = create_app(cfg)
    tc = TestClient(app)
    r = tc.get("/api/player/sheet")
    assert r.status_code == 200
    assert "items" in r.json()
