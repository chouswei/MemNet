"""BoundedMatchFind (#73) — seed lookup, hard LIMIT, shaped emit."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import examples_dir

runner = CliRunner()
_CODING_MAP = examples_dir() / "schema.coding.example.txt"


def _open(memnet_temp) -> str:
    del memnet_temp
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def _seed_three_tsk(sid: str) -> None:
    batch = (
        "\n".join(
            [
                "CREATE (:TSK {id: 'TSK_a', goal: 'alpha', status: 'in_progress'})",
                "CREATE (:TSK {id: 'TSK_b', goal: 'beta', status: 'in_progress'})",
                "CREATE (:TSK {id: 'TSK_c', goal: 'gamma', status: 'in_progress'})",
                "CREATE (:MOD {id: 'MOD_z', path: 'z.py', summary: 'file', status: 'active'})",
            ]
        )
        + "\n"
    )
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input=batch)
    assert add.exit_code == 0, add.stderr


def test_find_requires_limit(memnet_temp):
    sid = _open(memnet_temp)
    r = runner.invoke(app, ["query", "find", "--kind", "TSK", "--session", sid])
    assert r.exit_code != 0
    assert "no_limit" in r.stderr


def test_find_requires_cue(memnet_temp):
    sid = _open(memnet_temp)
    r = runner.invoke(app, ["query", "find", "--limit", "2", "--session", sid])
    assert r.exit_code != 0
    assert "no_cue" in r.stderr


def test_find_kind_cue_conflict_not_silent_first_n(memnet_temp):
    sid = _open(memnet_temp)
    _seed_three_tsk(sid)
    r = runner.invoke(app, ["query", "find", "--kind", "TSK", "--limit", "2", "--session", sid])
    assert r.exit_code == 0, r.stderr
    assert "CueConflict" in r.stdout
    assert "|Q|=3" in r.stdout
    assert "MOD_z" not in r.stdout
    assert "RETURN" not in r.stdout
    assert "(:LAW" not in r.stdout
    assert "-[:" not in r.stdout


def test_find_empty_skip(memnet_temp):
    sid = _open(memnet_temp)
    r = runner.invoke(
        app,
        [
            "query",
            "find",
            "--kind",
            "TSK",
            "--keyword",
            "no-such-cue",
            "--limit",
            "5",
            "--session",
            sid,
        ],
    )
    assert r.exit_code == 0, r.stderr
    assert r.stdout.strip() == ""


def test_find_locator_and_keyword(memnet_temp):
    sid = _open(memnet_temp)
    _seed_three_tsk(sid)
    loc = runner.invoke(
        app,
        [
            "query",
            "find",
            "--kind",
            "MOD",
            "--locator",
            "path=z.py",
            "--limit",
            "3",
            "--session",
            sid,
        ],
    )
    assert loc.exit_code == 0, loc.stderr
    assert "MOD_z" in loc.stdout
    kw = runner.invoke(
        app,
        ["query", "find", "--keyword", "gamma", "--limit", "3", "--session", sid],
    )
    assert kw.exit_code == 0, kw.stderr
    assert "TSK_c" in kw.stdout
    assert "TSK_a" not in kw.stdout
