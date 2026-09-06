"""Honesty c: store-identity keys stay off product shaped emit."""

from __future__ import annotations

import asyncio
import json
import re

from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import examples_dir
from memnet.gql import emit_node_shaped
from memnet.models import SHAPE_DROP_KEYS, Record
from memnet.mutate_gate import MutateGate
from memnet.observable_rank import node_rank_key
from memnet.pin_map_composer import PinMapComposer
from memnet.pin_map_export import export_pin_map
from memnet.session import get_session, open_session

runner = CliRunner()
_CODING_MAP = examples_dir() / "schema.coding.example.txt"
_ID_PROP = re.compile(r"(?:\{|,)\s*id\s*:")


def _open() -> str:
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def _assert_clean_shape(text: str) -> None:
    assert "_el" not in text
    assert "_memnet_hid" not in text
    assert "elementId" not in text
    assert not _ID_PROP.search(text)
    for key in SHAPE_DROP_KEYS:
        assert f"{key}:" not in text


def _poison(rec: Record) -> None:
    rec.fields["hid"] = rec.hid
    rec.fields["_memnet_hid"] = rec.hid
    rec.fields["elementId"] = "4:cabinet"
    rec.fields["id"] = "NICK_POISON"


def test_shape_drop_keys_constant():
    assert SHAPE_DROP_KEYS == frozenset({"hid", "_memnet_hid", "elementId"})


def test_emit_node_shaped_drops_store_identity_even_with_nickname():
    line = emit_node_shaped(
        "TSK",
        "NICK",
        {
            "goal": "visible",
            "hid": "_el9",
            "_memnet_hid": "cab",
            "elementId": "4:x",
        },
        include_nickname=True,
    )
    assert "goal: 'visible'" in line
    assert "id: 'NICK'" in line
    _assert_clean_shape(line.replace("id: 'NICK'", ""))
    assert "_el9" not in line
    assert "4:x" not in line


def test_rank_key_excludes_element_id():
    a = Record(tag="TSK", fields={"goal": "same", "elementId": "4:aaa"})
    b = Record(tag="TSK", fields={"goal": "same", "elementId": "4:zzz"})
    a.hid = "_el99"
    b.hid = "_el1"
    assert node_rank_key(a) == node_rank_key(b)
    assert "elementId" not in str(node_rank_key(a))
    assert "4:aaa" not in str(node_rank_key(a))


def test_poisoned_fields_off_pin_map_find_export_jsonl(memnet_temp):
    del memnet_temp
    ss = open_session(map_file=str(_CODING_MAP))
    MutateGate(ss).apply(
        ["CREATE (:TSK {goal: 'poison-cut', status: 'in_progress'})"],
        mode="add",
    )
    rec = [r for r in ss.store.list_records("TSK") if r.fields.get("goal") == "poison-cut"][0]
    _poison(rec)

    _rows, mapped = PinMapComposer(ss).compose(
        anchor=None,
        kind="TSK",
        locators=[("goal", "poison-cut")],
    )
    _assert_clean_shape(mapped)
    assert "poison-cut" in mapped
    assert "NICK_POISON" not in mapped

    exported = export_pin_map(ss, kind="TSK", locators=[("goal", "poison-cut")])
    _assert_clean_shape(exported.body)
    assert exported.body == mapped

    find = runner.invoke(
        app,
        [
            "query",
            "find",
            "--kind",
            "TSK",
            "--locator",
            "goal=poison-cut",
            "--limit",
            "4",
            "--session",
            ss.meta.session_id,
        ],
    )
    assert find.exit_code == 0, find.stderr
    _assert_clean_shape(find.stdout)

    conflict_ss = open_session(map_file=str(_CODING_MAP))
    MutateGate(conflict_ss).apply(
        [
            "CREATE (:TSK {goal: 'same-goal', status: 'open'})",
            "CREATE (:TSK {goal: 'same-goal', status: 'open'})",
        ],
        mode="add",
    )
    for row in conflict_ss.store.list_records("TSK"):
        _poison(row)
    _crows, conflict = PinMapComposer(conflict_ss).compose(anchor=None, kind="TSK")
    assert "CueConflict" in conflict
    _assert_clean_shape(conflict)
    assert "NICK_POISON" not in conflict

    dump = ss.store.to_jsonl_rows()
    blob = json.dumps(dump)
    assert "_memnet_hid" not in blob
    assert "elementId" not in blob
    assert all("hid" not in row for row in dump)


def test_mutate_ack_and_cli_pin_map_hide_hid(memnet_temp):
    sid = _open()
    create = runner.invoke(
        app,
        ["mutate", "--stdin", "--session", sid],
        input="CREATE (:TSK {goal: 'ack-hid', status: 'in_progress'})\n",
    )
    assert create.exit_code == 0, create.stderr
    _assert_clean_shape(create.stdout)
    pin = runner.invoke(
        app,
        [
            "query",
            "pin-map",
            "--kind",
            "TSK",
            "--locator",
            "goal=ack-hid",
            "--session",
            sid,
        ],
    )
    assert pin.exit_code == 0, pin.stderr
    _assert_clean_shape(pin.stdout)
    outlined = runner.invoke(app, ["query", "pin-map", "--session", sid])
    assert outlined.exit_code == 0, outlined.stderr
    _assert_clean_shape(outlined.stdout)


def test_mcp_pin_map_and_find_drop_identity_keys(memnet_temp, monkeypatch):
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import find, pin_map, session_open

    open_raw = asyncio.run(
        session_open(map_lines=_CODING_MAP.read_text(encoding="utf-8").strip().splitlines())
    )
    payload = json.loads(open_raw)
    assert payload["exit_code"] == 0
    sid = payload["session_id"]
    monkeypatch.setenv("MEMNET_SESSION", sid)
    add = runner.invoke(
        app,
        ["mutate", "--stdin", "--session", sid],
        input="CREATE (:TSK {id: 'TSK_mcp', goal: 'mcp-wire', status: 'open'})\n",
    )
    assert add.exit_code == 0, add.stderr
    rec = get_session(sid).store.match_nickname("TSK_mcp")[0]
    _poison(rec)

    pin_raw = asyncio.run(
        pin_map(kind="TSK", locators=["goal=mcp-wire"], session=sid),
    )
    pin_payload = json.loads(pin_raw)
    assert pin_payload["exit_code"] == 0, pin_payload
    _assert_clean_shape(pin_payload["stdout"])
    assert "TSK_mcp" not in pin_payload["stdout"]
    assert "mcp-wire" in pin_payload["stdout"]

    find_raw = asyncio.run(find(limit=4, kind="TSK", locators=["goal=mcp-wire"], session=sid))
    find_payload = json.loads(find_raw)
    assert find_payload["exit_code"] == 0, find_payload
    _assert_clean_shape(find_payload["stdout"])
