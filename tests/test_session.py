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

    r4 = runner.invoke(app, ["read", "get", "--id", "PLR01", "--session", sid])
    assert r4.exit_code == 0
    assert "@PLR:" in r4.stdout


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
