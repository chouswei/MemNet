"""Session lifecycle tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from typer.testing import CliRunner

from memnet.cli import app
from memnet.registry import contains
from memnet.session import get_session, open_session, set_now_override

runner = CliRunner()


def test_open_write_resume_cross_process(memnet_temp, schema_file, workflow_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file), "--ttl", "60"])
    assert r1.exit_code == 0, r1.output
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    assert sid.startswith("mn_")
    assert f"MEMNET_SESSION={sid}" in r1.stderr

    r2 = runner.invoke(
        app,
        ["add", "--file", str(workflow_file), "--session", sid],
    )
    assert r2.exit_code == 0, r2.stderr

    r3 = runner.invoke(app, ["session", "resume", sid])
    assert r3.exit_code == 0

    r4 = runner.invoke(app, ["query", "pin-map", "--cue", "PLR01", "--session", sid])
    assert r4.exit_code == 0, r4.stderr
    assert "PLR01" in r4.stdout


def test_session_expired(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file), ttl_minutes=1)
    set_now_override(datetime.now(UTC) + timedelta(minutes=5))
    from memnet.exceptions import MemNetError

    with pytest.raises(MemNetError) as exc:
        get_session(ss.session_id)
    assert exc.value.code == "session_expired"
    set_now_override(None)


def test_close_removes_session(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    assert contains(ss.session_id)
    r = runner.invoke(app, ["session", "close", ss.session_id])
    assert r.exit_code == 0
    assert not contains(ss.session_id)


def test_default_max_sessions_is_256(memnet_temp, monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_SESSIONS", raising=False)
    from memnet.config import Caps

    assert Caps().max_sessions == 256


def test_max_sessions_override(memnet_temp, schema_file, monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_SESSIONS", "2")
    from memnet.config import Caps
    from memnet.exceptions import MemNetError
    from memnet.session import count_sessions, open_session as open_ss

    assert Caps().max_sessions == 2
    open_ss(map_file=str(schema_file), caps=Caps())
    open_ss(map_file=str(schema_file), caps=Caps())
    with pytest.raises(MemNetError) as exc:
        open_ss(map_file=str(schema_file), caps=Caps())
    assert exc.value.code == "limit_exceeded"
    assert exc.value.message == "sessions|3/2"
    assert count_sessions() == 2


def test_session_list_emits_counter_header(memnet_temp, schema_file):
    from memnet.config import Caps

    ss = open_session(map_file=str(schema_file))
    listed = runner.invoke(app, ["session", "list"])
    assert listed.exit_code == 0
    lines = [ln for ln in listed.stdout.splitlines() if ln.strip()]
    assert lines[0] == f"@STAT: sessions|1/{Caps().max_sessions}"
    assert ss.session_id in listed.stdout


def test_cli_close_decrements_so_open_can_mint(memnet_temp, schema_file, monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_SESSIONS", "1")
    from memnet.config import Caps
    from memnet.exceptions import MemNetError
    from memnet.session import count_sessions, open_session as open_ss

    first = open_ss(map_file=str(schema_file), caps=Caps())
    with pytest.raises(MemNetError) as exc:
        open_ss(map_file=str(schema_file), caps=Caps())
    assert exc.value.message == "sessions|2/1"
    closed = runner.invoke(app, ["session", "close", first.session_id])
    assert closed.exit_code == 0
    assert count_sessions() == 0
    second = open_ss(map_file=str(schema_file), caps=Caps())
    assert second.session_id != first.session_id
    assert count_sessions() == 1
