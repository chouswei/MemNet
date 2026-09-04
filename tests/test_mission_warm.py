"""Mission settle → warm integration."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app

runner = CliRunner()


def test_mission_warm_hides_settled(memnet_temp, schema_file, workflow_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])

    r2 = runner.invoke(
        app,
        ["update", "--stdin", "--session", sid],
        input="@TSK: T01|Upgrade workshop|0|settled|delete_on_settle\n",
    )
    assert r2.exit_code == 0
    assert "mission_settled" in r2.stderr

    warm = runner.invoke(
        app,
        ["query", "warm", "--anchor", "PLR01", "--session", sid],
    )
    assert warm.exit_code == 0
    assert "T01" not in warm.stdout or "delete_on_settle" not in warm.stdout
    assert "(:LAW" in warm.stdout
    assert "CREATE (:" not in warm.stdout

    still = runner.invoke(
        app, ["read", "list", "--tag", "TSK", "--where", "id=T01", "--session", sid]
    )
    assert still.exit_code == 0
    assert "settled" in still.stdout

    cold = runner.invoke(
        app,
        ["query", "context", "--anchor", "PLR01", "--session", sid],
    )
    assert cold.exit_code == 0
    assert "stale_in_store" in cold.stderr
