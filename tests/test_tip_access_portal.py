"""Tip access portal: invite, mocked Google login, hashed Bearer, revoke, unauth refuse."""

from __future__ import annotations

import re
import sqlite3
import time

from starlette.testclient import TestClient

from tip_access_portal.app import create_app
from tip_access_portal.config import Settings
from tip_access_portal.gate import authorization_active
from tip_access_portal.google_oauth import GoogleOAuth
from tip_access_portal.signing import sign_payload
from tip_access_portal.status import Probe, parse_probes, probe_one
from tip_access_portal.store import PortalStore

ADMIN = "admin@example.com"
USER = "person@example.com"
WWW = "https://memnet.139-59-255-181.nip.io/mcp"


def _settings(db_path: str = ":memory:", probes: tuple[Probe, ...] = ()) -> Settings:
    return Settings(
        google_client_id="client-id",
        google_client_secret="client-secret",
        portal_secret="test-portal-secret",
        admin_email=ADMIN,
        base_url="http://testserver",
        db_path=db_path,
        cookie_secure=False,
        invite_ttl_hours=24,
        status_probes=probes,
    )


def _google(settings: Settings) -> GoogleOAuth:
    profiles = {
        "code-admin": {"sub": "sub-admin", "email": ADMIN, "email_verified": True},
        "code-user": {"sub": "sub-user", "email": USER, "email_verified": True},
        "code-unverified": {
            "sub": "sub-raw",
            "email": "raw@example.com",
            "email_verified": False,
        },
    }

    def post(url: str, form: dict) -> dict:
        assert url.endswith("/token")
        assert form["client_id"] == settings.google_client_id
        assert form["client_secret"] == settings.google_client_secret
        assert form["redirect_uri"] == settings.redirect_uri
        assert form["grant_type"] == "authorization_code"
        code = form["code"]
        if code not in profiles:
            raise ValueError("unknown_code")
        return {"access_token": "at-" + code}

    def get(url: str, access: str) -> dict:
        assert url.endswith("/userinfo")
        assert access.startswith("at-")
        return profiles[access.removeprefix("at-")]

    return GoogleOAuth(settings, post=post, get=get)


def _state(settings: Settings, invite: str = "") -> str:
    return sign_payload(
        {
            "kind": "oauth",
            "invite": invite,
            "nonce": "n",
            "exp": int(time.time()) + 600,
        },
        settings.portal_secret,
    )


def _app(
    db_path: str = ":memory:",
    *,
    probes: tuple[Probe, ...] = (),
    probe_http=None,
    probe_tcp=None,
):
    settings = _settings(db_path, probes)
    store = PortalStore(db_path)
    app = create_app(
        settings,
        store,
        _google(settings),
        probe_http=probe_http,
        probe_tcp=probe_tcp,
    )
    return settings, store, app


def _client(app) -> TestClient:
    return TestClient(app)


def _csrf(html: str) -> str:
    match = re.search(r"name='csrf' value='([^']+)'", html)
    assert match is not None
    return match.group(1)


def test_store_mint_redeem_hash_and_revoke():
    _settings_obj, store, _app_obj = _app()
    invite, token = store.mint_invite(label="ada", ttl_hours=2)
    assert invite.status == "open"
    assert store.invite_by_token(token).id == invite.id
    assert store.contains_plaintext(token) is False
    key = store.issue_key(invite, email=USER, google_sub="sub-user")
    assert key.startswith("mn_tip_")
    assert store.contains_plaintext(key) is False
    assert store.key_is_active(key) is True
    assert authorization_active(store, None) is False
    assert authorization_active(store, "Basic x") is False
    assert authorization_active(store, f"Bearer {key}") is True
    assert store.revoke_key(store.list_keys()[0].id) is True
    assert store.key_is_active(key) is False
    assert authorization_active(store, f"Bearer {key}") is False


def test_revoke_invite_refuses_issued_key():
    _settings_obj, store, _app_obj = _app()
    invite, _token = store.mint_invite(label="", ttl_hours=2)
    key = store.issue_key(invite, email=USER, google_sub="sub-user")
    assert store.revoke_invite(invite.id) is True
    assert store.key_is_active(key) is False
    assert authorization_active(store, f"Bearer {key}") is False


def test_google_exchange_mock_and_unverified():
    settings = _settings()
    google = _google(settings)
    identity = google.exchange("code-user")
    assert identity.email == USER
    assert identity.email_verified is True
    try:
        google.exchange("code-unverified")
    except ValueError as exc:
        assert str(exc) == "email_unverified"
    else:
        raise AssertionError("unverified email must be refused")


def test_admin_mints_invitee_sees_key_once_gate_checks():
    settings, store, app = _app()
    admin = _client(app)
    admin.get(f"/auth/callback?code=code-admin&state={_state(settings)}")
    page = admin.get("/admin")
    assert page.status_code == 200
    minted = admin.post(
        "/admin/invites",
        data={"csrf": _csrf(page.text), "label": "pilot"},
    )
    assert minted.status_code == 200
    match = re.search(r"http://testserver/invite/([A-Za-z0-9_\-]+)", minted.text)
    assert match is not None
    token = match.group(1)
    assert store.contains_plaintext(token) is False
    assert "pilot" in minted.text

    stranger = _client(app)
    refused = stranger.post("/admin/invites", data={"csrf": "nope", "label": "x"})
    assert refused.status_code == 403

    invitee = _client(app)
    shown = invitee.get(
        f"/auth/callback?code=code-user&state={_state(settings, token)}",
        follow_redirects=True,
    )
    assert shown.status_code == 200
    key_match = re.search(r"id='bearer'>(mn_tip_[^<]+)", shown.text)
    assert key_match is not None
    key = key_match.group(1)
    assert store.contains_plaintext(key) is False
    again = invitee.get("/key")
    assert key not in again.text
    assert "displayed once" in again.text

    replay = _client(app)
    second = replay.get(
        f"/auth/callback?code=code-admin&state={_state(settings, token)}",
        follow_redirects=True,
    )
    assert "cannot be redeemed" in second.text
    assert "mn_tip_" not in second.text

    no_auth = invitee.get("/auth/validate")
    assert no_auth.status_code == 401
    bad = invitee.get("/internal/bearer-check", headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401
    ok = invitee.get("/auth/validate", headers={"Authorization": f"Bearer {key}"})
    assert ok.status_code == 200
    used = store.list_keys()[0]
    assert used.use_count == 1
    assert used.last_used_at is not None

    admin_page = admin.get("/admin")
    key_id = store.list_keys()[0].id
    revoked = admin.post(
        f"/admin/keys/{key_id}/revoke",
        data={"csrf": _csrf(admin_page.text)},
    )
    assert revoked.status_code == 200
    after = invitee.get("/auth/validate", headers={"Authorization": f"Bearer {key}"})
    assert after.status_code == 401
    assert WWW not in after.text


def test_stranger_without_invite_gets_no_key():
    settings, store, app = _app()
    client = _client(app)
    page = client.get(f"/auth/callback?code=code-user&state={_state(settings)}")
    assert page.status_code == 200
    assert "does not give a free MemNet" in page.text
    assert store.list_keys() == []
    home = client.get("/")
    assert "open a project" in home.text
    unverified = client.get(
        f"/auth/callback?code=code-unverified&state={_state(settings, 'missing')}"
    )
    assert "verified email" in unverified.text


def test_parse_probes_and_http_401_is_up():
    probes = parse_probes(
        "tip-mcp=https://memnet.139-59-255-181.nip.io/mcp,serve=tcp://127.0.0.1:18765"
    )
    assert probes[0].name == "tip-mcp"
    assert probes[1].target == "tcp://127.0.0.1:18765"
    http_ok = probe_one(probes[0], http_request=lambda _url: 401)
    assert http_ok.up is True
    assert "401" in http_ok.detail
    tcp_ok = probe_one(probes[1], tcp_connect=lambda _host, _port: None)
    assert tcp_ok.up is True
    tcp_down = probe_one(
        Probe("serve", "tcp://127.0.0.1:18765"),
        tcp_connect=_raise_oserror,
    )
    assert tcp_down.up is False
    unsupported = probe_one(Probe("weird", "ftp://nope"))
    assert unsupported.up is False


def _raise_oserror(_host: str, _port: int) -> None:
    raise ConnectionRefusedError("refused")


def test_validate_records_use_and_status_hides_targets_from_public(tmp_path):
    target = "https://memnet.139-59-255-181.nip.io/mcp"
    probes = (Probe("tip-mcp", target), Probe("serve", "tcp://127.0.0.1:18765"))
    settings, store, app = _app(
        str(tmp_path / "portal.sqlite"),
        probes=probes,
        probe_http=lambda url: 401 if url == target else 500,
        probe_tcp=lambda _host, _port: None,
    )
    public = _client(app)
    home = public.get("/")
    assert home.status_code == 200
    assert "tip-mcp" in home.text
    assert "class='up'>up" in home.text
    assert target not in home.text
    assert "tcp://127.0.0.1:18765" not in home.text
    status = public.get("/status")
    assert status.status_code == 200
    assert "Look only" in status.text
    assert USER not in status.text
    assert "admin-only" in status.text
    assert target not in status.text

    invite, _token = store.mint_invite(label="pilot", ttl_hours=2)
    key = store.issue_key(invite, email=USER, google_sub="sub-user")
    assert store.list_keys()[0].use_count == 0
    assert store.list_keys()[0].last_used_at is None
    ok = public.get("/auth/validate", headers={"Authorization": f"Bearer {key}"})
    assert ok.status_code == 200
    row = store.list_keys()[0]
    assert row.use_count == 1
    assert row.last_used_at is not None
    again = public.get("/auth/validate", headers={"Authorization": f"Bearer {key}"})
    assert again.status_code == 200
    assert store.list_keys()[0].use_count == 2
    hidden = public.get("/status")
    assert USER not in hidden.text
    assert target not in hidden.text
    store.revoke_key(row.id)
    refused = public.get("/auth/validate", headers={"Authorization": f"Bearer {key}"})
    assert refused.status_code == 401
    assert store.list_keys()[0].use_count == 2

    admin = _client(app)
    admin.get(f"/auth/callback?code=code-admin&state={_state(settings)}")
    admin_status = admin.get("/status")
    assert target in admin_status.text
    assert USER in admin_status.text
    assert "Calls" in admin_status.text
    assert "2" in admin_status.text
    admin_page = admin.get("/admin")
    assert "Last used" in admin_page.text
    assert USER in admin_page.text
    assert "Revoke" in admin_page.text


def test_status_probes_from_env(monkeypatch):
    monkeypatch.setenv("MEMNET_GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("MEMNET_GOOGLE_CLIENT_SECRET", "csec")
    monkeypatch.setenv("MEMNET_TIP_PORTAL_SECRET", "psec")
    monkeypatch.setenv("MEMNET_TIP_ADMIN_EMAIL", ADMIN)
    monkeypatch.setenv("MEMNET_TIP_PORTAL_BASE_URL", "https://memnet.example")
    monkeypatch.setenv(
        "MEMNET_STATUS_PROBES",
        "serve=tcp://127.0.0.1:18765,tip-mcp=https://already.example/mcp",
    )
    monkeypatch.setenv("MEMNET_TIP_MCP_PROBE", "https://memnet.139-59-255-181.nip.io/mcp")
    settings = Settings.from_env()
    names = [item.name for item in settings.status_probes]
    assert names == ["serve", "tip-mcp"]
    assert settings.status_probes[1].target == "https://already.example/mcp"
    monkeypatch.setenv("MEMNET_STATUS_PROBES", "serve=tcp://127.0.0.1:18765")
    extra = Settings.from_env()
    assert [item.name for item in extra.status_probes] == ["serve", "tip-mcp"]
    assert extra.status_probes[1].target == "https://memnet.139-59-255-181.nip.io/mcp"


def test_key_columns_migrate(tmp_path):
    path = tmp_path / "old.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE invites (
            id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            redeemed_at TEXT,
            redeemed_email TEXT,
            redeemed_sub TEXT,
            revoked INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE keys (
            id TEXT PRIMARY KEY,
            key_hash TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            google_sub TEXT NOT NULL,
            invite_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conn.commit()
    conn.close()
    store = PortalStore(str(path))
    invite, _token = store.mint_invite(label="old", ttl_hours=2)
    key = store.issue_key(invite, email=USER, google_sub="sub-user")
    assert store.record_use(key) is True
    row = store.list_keys()[0]
    assert row.use_count == 1
    assert row.last_used_at is not None
    store.close()
