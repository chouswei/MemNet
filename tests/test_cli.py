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
    assert "query pin-map" in result.stdout


def test_query_pin_map_cli(memnet_temp, schema_file):
    open_result = runner.invoke(
        app,
        ["session", "open", "--map-file", str(schema_file)],
        env={"MEMNET_TEST_INLINE": "1"},
    )
    assert open_result.exit_code == 0
    sid = None
    for line in open_result.stdout.splitlines():
        if line.startswith("@SESSION:"):
            sid = line.split("|", 1)[0].replace("@SESSION:", "").strip()
    assert sid
    add_result = runner.invoke(
        app,
        ["add", "--stdin"],
        input="@PLR: PLR77|Test|1|0|0|0|bag",
        env={"MEMNET_TEST_INLINE": "1", "MEMNET_SESSION": sid},
    )
    assert add_result.exit_code == 0
    warm_result = runner.invoke(
        app,
        ["query", "pin-map", "--anchor", "PLR77", "--session", sid],
        env={"MEMNET_TEST_INLINE": "1"},
    )
    assert warm_result.exit_code == 0
    assert "PLR77" in warm_result.stdout

    shell_result = runner.invoke(
        app,
        [
            "query",
            "pin-map",
            "--anchor",
            "PLR77",
            "--view",
            "shell",
            "--session",
            sid,
        ],
        env={"MEMNET_TEST_INLINE": "1"},
    )
    assert shell_result.exit_code == 0
    assert "PLR77" in shell_result.stdout


def test_examples_map():
    result = runner.invoke(app, ["examples", "map"])
    assert result.exit_code == 0
    assert "SCHEMA EDG ;" in result.stdout
    assert "SCHEMA CFG ;" in result.stdout


def test_no_session_error(memnet_temp):
    result = runner.invoke(app, ["read", "list"])
    assert result.exit_code == 2
    assert "no_session" in result.stderr
