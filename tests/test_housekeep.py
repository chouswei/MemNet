"""Housekeeping tests."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app

runner = CliRunner()


def test_prune_stale_dry_run(memnet_temp, schema_file, workflow_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])
    runner.invoke(
        app,
        ["update", "--stdin", "--session", sid],
        input="@TSK: T01|Upgrade workshop|0|settled|delete_on_settle\n",
    )
    dry = runner.invoke(app, ["housekeep", "prune", "stale", "--session", sid])
    assert dry.exit_code == 0
    assert "would-delete" in dry.stderr
    still = runner.invoke(
        app, ["read", "list", "--tag", "TSK", "--where", "id=T01", "--session", sid]
    )
    assert still.exit_code == 0
    assert "T01" in still.stdout
