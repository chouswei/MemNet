"""Drop idle / TTL-expired named sessions (not housekeep graph rows)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from typer.testing import CliRunner

from memnet.cli import app
from memnet.exceptions import MemNetError
from memnet.registry import contains
from memnet.session import (
    count_sessions,
    drop_stale_sessions,
    get_session,
    open_session,
    set_now_override,
    snapshot_expired_session,
)

runner = CliRunner()


def test_drop_stale_dry_run_keeps_ram(memnet_temp, schema_file):
    keep = open_session(map_file=str(schema_file), ttl_minutes=60)
    keep.touch()
    idle = open_session(map_file=str(schema_file), ttl_minutes=60)
    t0 = datetime.now(UTC)
    set_now_override(t0 + timedelta(minutes=10))
    dry = runner.invoke(
        app,
        ["session", "drop-stale", "--idle-minutes", "5", "--keep", keep.session_id],
    )
    assert dry.exit_code == 0, dry.output
    assert "@STAT: drop_stale|1|dry" in dry.stdout
    assert f"@SESSION: {idle.session_id}|idle|stale" in dry.stdout
    assert f"@SESSION: {keep.session_id}|" not in dry.stdout
    assert contains(keep.session_id)
    assert contains(idle.session_id)
    set_now_override(None)


def test_drop_stale_apply_drops_idle_keeps_current(memnet_temp, schema_file):
    keep = open_session(map_file=str(schema_file), ttl_minutes=60)
    keep.touch()
    idle = open_session(map_file=str(schema_file), ttl_minutes=60)
    set_now_override(datetime.now(UTC) + timedelta(minutes=10))
    applied = runner.invoke(
        app,
        [
            "session",
            "drop-stale",
            "--idle-minutes",
            "5",
            "--keep",
            keep.session_id,
            "--apply",
        ],
    )
    assert applied.exit_code == 0, applied.output
    assert "@STAT: drop_stale|1|applied" in applied.stdout
    assert f"@SESSION: {idle.session_id}|idle|dropped" in applied.stdout
    assert contains(keep.session_id)
    assert not contains(idle.session_id)
    set_now_override(None)


def test_drop_stale_ttl_expired_even_when_idle_window_is_long(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file), ttl_minutes=1)
    sid = ss.session_id
    set_now_override(datetime.now(UTC) + timedelta(minutes=5))
    expired, idle = drop_stale_sessions(idle_minutes=60, apply=True)
    assert sid in expired
    assert idle == []
    assert not contains(sid)
    set_now_override(None)


def test_sliding_ttl_is_not_activity(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file), ttl_minutes=60)
    sid = ss.session_id
    t0 = datetime.now(UTC)
    set_now_override(t0 + timedelta(minutes=2))
    get_session(sid)
    set_now_override(t0 + timedelta(minutes=12))
    expired, idle = drop_stale_sessions(idle_minutes=5, apply=False)
    assert expired == []
    assert idle == [sid]
    assert contains(sid)
    set_now_override(None)


def test_drop_stale_unlinks_expire_snap(memnet_temp, schema_file, tmp_path, monkeypatch):
    expire_dir = tmp_path / "expire"
    monkeypatch.setenv("MEMNET_SAVE_ON_EXPIRE", "1")
    monkeypatch.setenv("MEMNET_EXPIRE_SNAPSHOT_DIR", str(expire_dir))
    from memnet.config import Caps

    caps = Caps()
    ss = open_session(map_file=str(schema_file), ttl_minutes=60, caps=caps)
    sid = ss.session_id
    written = snapshot_expired_session(sid, caps)
    assert written
    snap = expire_dir / f"{sid}.snap"
    assert snap.is_file()
    set_now_override(datetime.now(UTC) + timedelta(minutes=10))
    drop_stale_sessions(idle_minutes=5, apply=True, caps=caps)
    assert not contains(sid)
    assert not snap.is_file()
    set_now_override(None)


def test_housekeep_prune_stale_does_not_drop_session(memnet_temp, schema_file, workflow_file):
    ss = open_session(map_file=str(schema_file), ttl_minutes=60)
    sid = ss.session_id
    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])
    prune = runner.invoke(app, ["housekeep", "prune", "stale", "--apply", "--session", sid])
    assert prune.exit_code == 0, prune.output
    assert contains(sid)
    assert count_sessions() == 1


def test_bad_idle_minutes(memnet_temp):
    with pytest.raises(MemNetError) as exc:
        drop_stale_sessions(idle_minutes=0, apply=False)
    assert exc.value.code == "bad_idle"
    bad = runner.invoke(app, ["session", "drop-stale", "--idle-minutes", "0"])
    assert bad.exit_code == 2
    assert "bad_idle" in bad.stderr
