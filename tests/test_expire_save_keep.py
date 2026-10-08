"""MN-REQ-01.9 — expire-save failure keeps the session live until save or close."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.registry import contains
from memnet.session import (
    count_sessions,
    expire_hold_count,
    get_session,
    open_session,
    purge_expired,
    set_now_override,
)

runner = CliRunner()
_PLR = (
    "CREATE (:PLR {id: 'PLR01', identity: 'Hero', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)
_TINY_MAP = ["SCHEMA N ; fields=id name"]
_TTL_WAIT_S = 62


def _make_unsaveable(ss) -> None:
    MutateGate(ss).apply([_PLR], mode="add")
    rec = ss.store.get("PLR01")
    rec.fields["identity"] = "x" * 9000


def _arm_expire(monkeypatch, tmp_path: Path) -> Caps:
    monkeypatch.setenv("MEMNET_SAVE_ON_EXPIRE", "1")
    monkeypatch.setenv("MEMNET_EXPIRE_SNAPSHOT_DIR", str(tmp_path))
    return Caps()


def _expire_now() -> None:
    set_now_override(datetime.now(UTC) + timedelta(minutes=5))


def test_unsaveable_expiry_keeps_session_and_warns(
    memnet_temp, schema_file, tmp_path: Path, monkeypatch
):
    caps = _arm_expire(monkeypatch, tmp_path)
    ss = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps)
    sid = ss.session_id
    _make_unsaveable(ss)
    _expire_now()
    pin = runner.invoke(app, ["query", "pin-map", "--cue", "PLR01", "--session", sid])
    assert pin.exit_code == 2
    assert "session_expired" in pin.stderr
    assert "overdue" in pin.stderr
    assert "expire_snapshot_failed" in pin.stderr
    assert "snapshot_unsaveable" in pin.stderr
    assert contains(sid)
    assert expire_hold_count() == 1
    assert list(tmp_path.glob("*.snap")) == []
    status = runner.invoke(app, ["session", "expire-status"])
    assert "@STAT: expire_snapshot_failed|1|" in status.stdout
    listed = runner.invoke(app, ["session", "list"])
    assert "@STAT: expire_snapshot_failed|1|" in listed.stdout
    set_now_override(None)


def test_unsaveable_expiry_later_save_clears_hold(
    memnet_temp, schema_file, tmp_path: Path, monkeypatch
):
    caps = _arm_expire(monkeypatch, tmp_path)
    ss = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps)
    sid = ss.session_id
    _make_unsaveable(ss)
    _expire_now()
    purge_expired(caps)
    assert contains(sid)
    assert expire_hold_count() == 1
    ss.store.get("PLR01").fields["identity"] = "Hero"
    dest = tmp_path / "fixed.snap"
    save = runner.invoke(app, ["session", "save", "--file", str(dest), "--session", sid])
    assert save.exit_code == 0, save.stderr
    assert dest.is_file()
    assert not contains(sid)
    assert expire_hold_count() == 0
    status = runner.invoke(app, ["session", "expire-status"])
    assert "@STAT: expire_snapshot_failed|0|" in status.stdout
    set_now_override(None)


def test_unsaveable_expiry_close_clears_hold(memnet_temp, schema_file, tmp_path: Path, monkeypatch):
    caps = _arm_expire(monkeypatch, tmp_path)
    ss = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps)
    sid = ss.session_id
    _make_unsaveable(ss)
    _expire_now()
    with pytest.raises(MemNetError) as exc:
        get_session(sid, caps)
    assert exc.value.code == "session_expired"
    assert exc.value.message == "overdue"
    assert contains(sid)
    closed = runner.invoke(app, ["session", "close", sid])
    assert closed.exit_code == 0, closed.stderr
    assert "closed" in closed.stdout
    assert not contains(sid)
    assert expire_hold_count() == 0
    set_now_override(None)


def test_unsaveable_expiry_counts_against_session_cap(
    memnet_temp, schema_file, tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("MEMNET_MAX_SESSIONS", "1")
    caps = _arm_expire(monkeypatch, tmp_path)
    ss = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps)
    sid = ss.session_id
    _make_unsaveable(ss)
    _expire_now()
    purge_expired(caps)
    assert contains(sid)
    assert count_sessions(caps) == 1
    with pytest.raises(MemNetError) as exc:
        open_session(map_file=str(schema_file), ttl_minutes=1, caps=Caps())
    assert exc.value.code == "limit_exceeded"
    assert "sessions|" in exc.value.message
    set_now_override(None)


def test_unwritable_dir_expiry_keeps_session(memnet_temp, schema_file, tmp_path: Path, monkeypatch):
    expire_dir = tmp_path / "expire"
    expire_dir.mkdir()
    caps = _arm_expire(monkeypatch, expire_dir)
    ss = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps)
    sid = ss.session_id
    MutateGate(ss).apply([_PLR], mode="add")
    os.chmod(expire_dir, 0o555)
    try:
        _expire_now()
        pin = runner.invoke(app, ["query", "pin-map", "--cue", "PLR01", "--session", sid])
        assert pin.exit_code == 2
        assert "overdue" in pin.stderr
        assert "expire_snapshot_failed" in pin.stderr
        assert contains(sid)
        assert expire_hold_count() == 1
        assert list(expire_dir.glob("*.snap")) == []
    finally:
        os.chmod(expire_dir, 0o755)
        set_now_override(None)


def test_save_on_expire_off_still_drops(memnet_temp, schema_file, monkeypatch):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    ss = open_session(map_file=str(schema_file), ttl_minutes=1)
    sid = ss.session_id
    _expire_now()
    with pytest.raises(MemNetError) as exc:
        get_session(sid)
    assert exc.value.code == "session_expired"
    assert exc.value.message == "snap_missing"
    assert not contains(sid)
    assert expire_hold_count() == 0
    set_now_override(None)


def _extras_create(n: int = 40) -> str:
    extras = ", ".join(f"x{i:02d}: 'v'" for i in range(n))
    return f"CREATE (:N {{id: 'N01', name: 'n', {extras}}})"


def _wait_ttl() -> None:
    time.sleep(_TTL_WAIT_S)


def test_live_unsaveable_expiry_keeps_warns_cap_and_close(tmp_path: Path):
    from tests.doc_gate_lib import running_serve

    with running_serve(tmp_path, ttl_minutes=1, max_sessions=1) as svc:
        sid, opened = svc.try_open_session(map_lines=list(_TINY_MAP), ttl=1)
        assert sid, opened.stderr
        created = svc.mutate(sid, _extras_create())
        assert created.exit_code == 0, created.stderr
        _wait_ttl()
        pin = svc.pin_map(sid, cue="N01")
        assert pin.exit_code == 2
        assert "session_expired" in pin.stderr
        assert "overdue" in pin.stderr
        assert "expire_snapshot_failed" in pin.stderr
        assert "snapshot_unsaveable" in pin.stderr
        n, mx = svc.live_count()
        assert n == 1
        assert mx == 1
        status = svc.expire_status()
        assert "@STAT: expire_snapshot_failed|1|" in status.stdout
        blocked, reply = svc.try_open_session(map_lines=list(_TINY_MAP), ttl=1)
        assert blocked is None
        assert "limit_exceeded" in reply.stderr
        assert "sessions|" in reply.stderr
        closed = svc.close(sid)
        assert closed.exit_code == 0, closed.stderr
        status2 = svc.expire_status()
        assert "@STAT: expire_snapshot_failed|0|" in status2.stdout
        sid2, opened2 = svc.try_open_session(map_lines=list(_TINY_MAP), ttl=1)
        assert sid2, opened2.stderr
        assert svc.close(sid2).exit_code == 0


def test_live_unwritable_expiry_save_clears_hold(tmp_path: Path):
    from tests.doc_gate_lib import running_serve

    with running_serve(tmp_path, ttl_minutes=1, max_sessions=2) as svc:
        sid = svc.open_session(map_lines=list(_TINY_MAP), ttl=1)
        created = svc.mutate(sid, "CREATE (:N {id: 'N01', name: 'ok'})")
        assert created.exit_code == 0, created.stderr
        os.chmod(svc.snap_dir, 0o555)
        try:
            _wait_ttl()
            pin = svc.pin_map(sid, cue="N01")
            assert pin.exit_code == 2
            assert "overdue" in pin.stderr
            assert "expire_snapshot_failed" in pin.stderr
            assert "@STAT: expire_snapshot_failed|1|" in svc.expire_status().stdout
        finally:
            os.chmod(svc.snap_dir, 0o755)
        dest = tmp_path / "fixed.snap"
        saved = svc.save(sid, dest)
        assert saved.exit_code == 0, saved.stderr
        assert dest.is_file()
        assert "@STAT: expire_snapshot_failed|0|" in svc.expire_status().stdout
        n, _mx = svc.live_count()
        assert n == 0
        pin2 = svc.pin_map(sid, cue="N01")
        assert pin2.exit_code == 2
        assert "session_expired" in pin2.stderr or "session_not_found" in pin2.stderr
        assert "overdue" not in pin2.stderr
