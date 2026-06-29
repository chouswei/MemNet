"""Tests for novel_mobile Google auth and app JWT."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "applications" / "novel_cursor"))
sys.path.insert(0, str(_root / "src"))

from app_config import NovelAppConfig
from novel_mobile.auth import (
    AuthConfig,
    exchange_google_login,
    issue_app_token,
    load_auth_config,
    resolve_user_id,
    user_id_from_google_sub,
    verify_app_token,
)
from novel_mobile.auth import AuthContext
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


def _google_cfg() -> AuthConfig:
    return AuthConfig(
        mode="google",
        google_client_id="test-client.apps.googleusercontent.com",
        jwt_secret="unit-test-jwt-secret-key-32b",
    )


def test_user_id_from_google_sub() -> None:
    assert user_id_from_google_sub("123456789012345678901") == "google_123456789012345678901"


def test_load_auth_config_google_requires_jwt_secret(monkeypatch) -> None:
    monkeypatch.delenv("NOVEL_MOBILE_JWT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid.apps.googleusercontent.com")
    with pytest.raises(ValueError, match="NOVEL_MOBILE_JWT_SECRET"):
        load_auth_config()


def test_google_exchange_and_jwt_roundtrip(monkeypatch) -> None:
    cfg = _google_cfg()
    monkeypatch.setattr(
        "novel_mobile.auth.verify_google_credential",
        lambda _cred, _cid: {"sub": "acct-99", "email": "player@example.com"},
    )
    out = exchange_google_login(cfg, "fake-id-token")
    assert out["user_id"] == "google_acct-99"
    assert out["email"] == "player@example.com"
    ctx = verify_app_token(cfg, out["access_token"])
    assert ctx.user_id == "google_acct-99"
    assert ctx.email == "player@example.com"


def test_load_auth_config_guest_when_jwt_only(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.setenv("NOVEL_MOBILE_JWT_SECRET", "unit-test-jwt-secret-key-32b")
    cfg = load_auth_config()
    assert cfg.mode == "guest"


def test_guest_exchange_and_world_isolation(tmp_path, monkeypatch) -> None:
    from novel_mobile.auth import exchange_guest_login
    from novel_mobile.world_registry import create_world_record, list_worlds_for_owner

    auth_cfg = AuthConfig(mode="guest", jwt_secret="unit-test-jwt-secret-key-32b")
    a = exchange_guest_login(auth_cfg)
    b = exchange_guest_login(auth_cfg)
    assert a["user_id"] != b["user_id"]

    base = _config(tmp_path)
    create_world_record(base, a["user_id"], title="A world")
    create_world_record(base, b["user_id"], title="B world")
    assert len(list_worlds_for_owner(base, a["user_id"])) == 1
    assert len(list_worlds_for_owner(base, b["user_id"])) == 1


def test_guest_mode_requires_jwt(tmp_path) -> None:
    cfg = _config(tmp_path)
    auth_cfg = AuthConfig(mode="guest", jwt_secret="unit-test-jwt-secret-key-32b")
    app = create_app(cfg, auth_config=auth_cfg)
    tc = TestClient(app)
    assert tc.get("/api/health").status_code == 401
    guest = tc.post("/api/auth/guest")
    assert guest.status_code == 200
    token = guest.json()["access_token"]
    r = tc.get("/api/worlds", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["worlds"] == []


def test_resolve_user_id_google_ignores_spoofed_header() -> None:
    ctx = AuthContext(user_id="google_real12", email="a@b.com")
    assert resolve_user_id(ctx, None, auth_mode="google") == "google_real12"
    with pytest.raises(ValueError, match="user_id_mismatch"):
        resolve_user_id(ctx, "google_fake12345678", auth_mode="google")


def test_auth_config_endpoint_open(tmp_path) -> None:
    app = create_app(_config(tmp_path))
    tc = TestClient(app)
    r = tc.get("/api/auth/config")
    assert r.status_code == 200
    assert r.json()["auth_mode"] == "open"


def test_google_login_endpoint(tmp_path, monkeypatch) -> None:
    cfg = _config(tmp_path)
    auth_cfg = _google_cfg()
    monkeypatch.setattr(
        "novel_mobile.server.exchange_google_login",
        lambda _cfg, _cred: {
            "access_token": issue_app_token(
                auth_cfg,
                user_id="google_acct-99",
                email="player@example.com",
                google_sub="acct-99",
            )[0],
            "token_type": "bearer",
            "expires_in": 3600,
            "user_id": "google_acct-99",
            "email": "player@example.com",
        },
    )
    app = create_app(cfg, auth_config=auth_cfg)
    tc = TestClient(app)
    r = tc.post("/api/auth/google", json={"credential": "id-token"})
    assert r.status_code == 200
    assert r.json()["user_id"] == "google_acct-99"


def test_google_mode_requires_jwt(tmp_path) -> None:
    cfg = _config(tmp_path)
    auth_cfg = _google_cfg()
    app = create_app(cfg, auth_config=auth_cfg)
    tc = TestClient(app)
    assert tc.get("/api/health").status_code == 401
