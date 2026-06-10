"""Integration scheme registry (S01–S10 wave)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from memnet.cli import app

runner = CliRunner()


@pytest.mark.scheme("S01")
def test_s01_goldfish_refresh(memnet_temp, schema_file, workflow_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])
    warm = runner.invoke(app, ["query", "warm", "--anchor", "PLR01", "--session", sid])
    assert warm.exit_code == 0
    assert "@LAW:" in warm.stdout
    assert "@PLR:" in warm.stdout


@pytest.mark.scheme("S08")
def test_s08_pipe_escape(memnet_temp, schema_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    line = "@PLR: PLR01|note\\|extra|1|0|0|0|bag"
    w = runner.invoke(app, ["add", line, "--session", sid])
    assert w.exit_code == 0
    g = runner.invoke(app, ["read", "get", "--id", "PLR01", "--session", sid])
    assert "note|extra" in g.stdout or "note\\|extra" in g.stdout


@pytest.mark.scheme("S82")
def test_s82_no_session(memnet_temp):
    r = runner.invoke(app, ["read", "list"])
    assert r.exit_code == 2
    assert "no_session" in r.stderr
