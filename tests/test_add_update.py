"""add vs update command behaviour."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app

runner = CliRunner()


def test_add_then_update(memnet_temp, schema_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    line = "@PLR: PLR01|Beggar|1|0|0|0|bag"
    assert runner.invoke(app, ["add", line, "--session", sid]).exit_code == 0
    updated = "@PLR: PLR01|Beggar|2|0|0|0|bag"
    assert runner.invoke(app, ["update", updated, "--session", sid]).exit_code == 0
    got = runner.invoke(app, ["read", "get", "--id", "PLR01", "--session", sid])
    assert "2" in got.stdout


def test_add_id_exists(memnet_temp, schema_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    line = "@PLR: PLR01|Beggar|1|0|0|0|bag"
    runner.invoke(app, ["add", line, "--session", sid])
    dup = runner.invoke(app, ["add", line, "--session", sid])
    assert dup.exit_code != 0
    assert "id_exists" in dup.stderr


def test_update_not_found(memnet_temp, schema_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    line = "@PLR: PLR0l|Beggar|1|0|0|0|bag"
    miss = runner.invoke(app, ["update", line, "--session", sid])
    assert miss.exit_code != 0
    assert "not_found" in miss.stderr
