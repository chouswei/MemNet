"""CLI smoke tests."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.startswith("@VER: memnet|")


def test_version_json():
    import json

    result = runner.invoke(app, ["version", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip())
    assert payload["name"] == "memnet"
    assert payload["version"].count(".") >= 2


def test_guide_loose():
    result = runner.invoke(app, ["guide", "--loose"])
    assert result.exit_code == 0
    assert "query warm" in result.stdout


def test_examples_map():
    result = runner.invoke(app, ["examples", "map"])
    assert result.exit_code == 0
    assert "@EDG:" in result.stdout
    assert "@CFG:" in result.stdout


def test_no_session_error(memnet_temp):
    result = runner.invoke(app, ["read", "list"])
    assert result.exit_code == 2
    assert "no_session" in result.stderr
