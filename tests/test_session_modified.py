"""Session modified_at tracking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from typer.testing import CliRunner

from memnet.cli import app
from memnet.session import get_session, open_session, set_now_override

runner = CliRunner()


def test_modified_at_updates_on_read(memnet_temp, schema_file):
    t0 = datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC)
    set_now_override(t0)
    ss = open_session(map_file=str(schema_file))
    assert ss.meta.modified_at is None

    stats = runner.invoke(app, ["housekeep", "stats", "--session", ss.session_id])
    assert stats.exit_code == 0
    ss = get_session(ss.session_id)
    assert ss.meta.modified_at == "2026-06-10T12:00:00Z"
    assert ss.meta.has_writes is False
    set_now_override(None)


def test_modified_at_updates_on_mutate(memnet_temp, schema_file, workflow_file):
    t0 = datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC)
    set_now_override(t0)
    ss = open_session(map_file=str(schema_file))

    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", ss.session_id])
    ss = get_session(ss.session_id)
    assert ss.meta.modified_at == "2026-06-10T12:00:00Z"

    set_now_override(t0 + timedelta(minutes=5))
    runner.invoke(
        app,
        ["update", "@SYS: SYS01|1|Later|0|0|0|1:1", "--session", ss.session_id],
    )
    ss = get_session(ss.session_id)
    assert ss.meta.modified_at == "2026-06-10T12:05:00Z"
    set_now_override(None)


def test_session_list_and_current_include_modified(memnet_temp, schema_file, workflow_file):
    ss = open_session(map_file=str(schema_file))
    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", ss.session_id])

    listed = runner.invoke(app, ["session", "list"])
    assert listed.exit_code == 0
    assert ss.session_id in listed.stdout
    assert "T" in listed.stdout  # ISO timestamp present

    current = runner.invoke(
        app,
        ["session", "current"],
        env={"MEMNET_SESSION": ss.session_id},
    )
    assert current.exit_code == 0
    line = current.stdout.strip()
    assert line.startswith(f"@SESSION: {ss.session_id}|")
    assert line.count("|") >= 2
    assert "T" in line
