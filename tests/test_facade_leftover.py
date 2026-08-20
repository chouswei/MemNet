"""Product façade: cue pin_map, mutate Commit, leftover names leftover."""

from __future__ import annotations

import asyncio
import json

import pytest
from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import examples_dir
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

runner = CliRunner()
_CODING_MAP = examples_dir() / "schema.coding.example.txt"


def _open() -> str:
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def test_product_mutate_gql_commit_no_new_mint(memnet_temp):
    sid = _open()
    create = runner.invoke(
        app,
        ["mutate", "--stdin", "--session", sid],
        input="CREATE (:TSK {goal: 'facade', status: 'in_progress'})\n",
    )
    assert create.exit_code == 0, create.stderr
    assert "NEW" not in create.stdout
    patch = runner.invoke(
        app,
        ["mutate", "--stdin", "--session", sid],
        input="MATCH (t:TSK {goal: 'facade'}) SET t.status = 'settled'\n",
    )
    assert patch.exit_code == 0, patch.stderr
    pin = runner.invoke(
        app,
        ["query", "pin-map", "--kind", "TSK", "--locator", "goal=facade", "--session", sid],
    )
    assert pin.exit_code == 0, pin.stderr
    assert "facade" in pin.stdout
    assert "settled" in pin.stdout
    assert "_el" not in pin.stdout
    assert "_memnet_hid" not in pin.stdout


def test_product_mutate_rejects_leftover_pipe(memnet_temp):
    ss = open_session(map_file=str(_CODING_MAP))
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(["@TSK: TSK01|goal|in_progress|persistent"], mode="mutate")
    assert ei.value.code == "leftover_pipe"


def test_leftover_add_help_does_not_teach_new():
    help_r = runner.invoke(app, ["add", "--help"])
    assert help_r.exit_code == 0
    assert "leftover" in help_r.stdout.lower()
    assert "optional NEW" not in help_r.stdout
    mutate_h = runner.invoke(app, ["mutate", "--help"])
    assert mutate_h.exit_code == 0
    assert "GQL" in mutate_h.stdout or "CREATE" in mutate_h.stdout
    assert "NEW" in mutate_h.stdout  # "Does not mint NEW"


def test_pin_map_cue_is_product_nickname(memnet_temp):
    sid = _open()
    runner.invoke(
        app,
        ["mutate", "--stdin", "--session", sid],
        input="CREATE (:TSK {id: 'TSK_cue', goal: 'cued', status: 'in_progress'})\n",
    )
    pin = runner.invoke(app, ["query", "pin-map", "--cue", "TSK_cue", "--session", sid])
    assert pin.exit_code == 0, pin.stderr
    assert "TSK_cue" in pin.stdout
    leftover = runner.invoke(app, ["query", "pin-map", "--anchor", "TSK_cue", "--session", sid])
    assert leftover.exit_code == 0, leftover.stderr
    assert "TSK_cue" in leftover.stdout
    help_r = runner.invoke(app, ["query", "pin-map", "--help"])
    assert "leftover" in help_r.stdout.lower()
    assert "--cue" in help_r.stdout


def test_leftover_query_walk_help_named_leftover():
    walk = runner.invoke(app, ["query", "walk", "--help"])
    assert walk.exit_code == 0
    assert "leftover" in walk.stdout.lower()
    ctx = runner.invoke(app, ["query", "context", "--help"])
    assert ctx.exit_code == 0
    assert "leftover" in ctx.stdout.lower()
    assert "require_anchor" in ctx.stdout.lower() or "not require_anchor" in ctx.stdout


def test_leftover_import_slice_id_policy_help():
    help_r = runner.invoke(app, ["import-slice", "--help"])
    assert help_r.exit_code == 0
    assert "leftover" in help_r.stdout.lower()
    assert "id-policy" in help_r.stdout or "--id-policy" in help_r.stdout


def test_mcp_mutate_and_cue_schema(monkeypatch):
    mcp = pytest.importorskip("mcp")
    del mcp
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import mcp as server

    names = {t.name for t in asyncio.run(server.list_tools())}
    assert "mutate" in names
    assert "read_get" not in names
    assert "rag_query" not in names


def test_mcp_product_pin_map_cue(memnet_temp, monkeypatch):
    mcp = pytest.importorskip("mcp")
    del mcp
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import mutate, pin_map, session_open

    open_raw = asyncio.run(
        session_open(map_file=str(_CODING_MAP)),
    )
    open_payload = json.loads(open_raw)
    assert open_payload["exit_code"] == 0, open_payload
    sid = open_payload["session_id"]
    mut = asyncio.run(
        mutate(
            wire_lines=["CREATE (:TSK {id: 'TSK_mcp', goal: 'mcp-cue', status: 'in_progress'})"],
            session=sid,
        )
    )
    mut_payload = json.loads(mut)
    assert mut_payload["exit_code"] == 0, mut_payload
    pin = asyncio.run(pin_map(cue="TSK_mcp", session=sid))
    payload = json.loads(pin)
    assert payload["exit_code"] == 0, payload
    assert "TSK_mcp" in payload["stdout"]
    assert "_el" not in payload["stdout"]
