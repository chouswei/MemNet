"""MN-REQ-01.9 / 01.10 / 03.4 / 05.3 — snapshot round-trip, WHERE, ACL who."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import get_session, open_session, snapshot_expired_session
from memnet.snapshot import load_snapshot, write_snapshot
from memnet.wire import join_payload, split_payload

runner = CliRunner()
FIXTURE = Path(__file__).parent / "fixtures" / "snapshot-0.19.18.snap"

_PLR = (
    "CREATE (:PLR {id: 'PLR01', identity: 'Hero', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)


def _gql_escape(val: str) -> str:
    return val.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")


def test_split_join_newlines_and_specials():
    raw = "a|b\nc\\d\r测例$\"'{x}"
    wire = join_payload([raw])
    assert "\n" not in wire and "\r" not in wire
    assert split_payload(wire) == [raw]


def test_legacy_0_19_18_snapshot_loads(memnet_temp):
    ss = load_snapshot(FIXTURE)
    rec = ss.store.get("PLR_V118")
    assert rec is not None
    assert rec.fields["identity"] == r"pipe|slash\q {x} $ cjk测例"


def test_snapshot_roundtrip_specials_and_newlines(memnet_temp, schema_file, tmp_path: Path):
    ss = open_session(map_file=str(schema_file))
    blob = "line1\nline2\r" + r"""slash\ quotes"' $ {brace} |pipe| 测例"""
    MutateGate(ss).apply(
        [
            "CREATE (:PLR {id: 'PLR_RT', identity: '"
            + _gql_escape(blob)
            + "', wealth: 1, cashflow: 0, monopoly: 0, reputation: 0, inventory: 'bag'})"
        ],
        mode="add",
    )
    path = tmp_path / "rt.snap"
    write_snapshot(ss, path)
    text = path.read_text(encoding="utf-8")
    assert "\n@PLR:" in text or text.splitlines()[0] == "# memnet-snapshot-v1"
    rec_line = next(ln for ln in text.splitlines() if ln.startswith("@PLR:"))
    assert "\n" not in rec_line[1:] or rec_line.count("@PLR:") == 1
    loaded = load_snapshot(path)
    got = loaded.store.get("PLR_RT")
    assert got is not None
    assert got.fields["identity"] == blob


def test_gql_mutate_value_bytes_hard_cap(memnet_temp, schema_file, monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_VALUE_BYTES", "8")
    ss = open_session(map_file=str(schema_file), caps=Caps())
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            [
                "CREATE (:PLR {id: 'PLR_BIG', identity: 'toolongval', wealth: 1, "
                "cashflow: 0, monopoly: 0, reputation: 0, inventory: 'bag'})"
            ],
            mode="add",
        )
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message.startswith("value_bytes|")
    assert ss.store.get("PLR_BIG") is None


def test_escaped_under_value_cap_does_not_trip_line_bytes(
    memnet_temp, schema_file, tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("MEMNET_MAX_VALUE_BYTES", "64")
    monkeypatch.setenv("MEMNET_MAX_LINE_BYTES", "80")
    ss = open_session(map_file=str(schema_file), caps=Caps())
    blob = "n" * 20 + "\n" * 20
    MutateGate(ss).apply(
        [
            "CREATE (:PLR {id: 'PLR_ESC', identity: '"
            + _gql_escape(blob)
            + "', wealth: 1, cashflow: 0, monopoly: 0, reputation: 0, inventory: 'bag'})"
        ],
        mode="add",
    )
    path = tmp_path / "esc.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path, caps=Caps())
    assert loaded.store.get("PLR_ESC").fields["identity"] == blob


def test_where_contains_filters_and_false_set_is_noop(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    MutateGate(ss).apply(
        [
            "CREATE (:PLR {id: 'PLR02', identity: 'Villain', wealth: 1, cashflow: 0, "
            "monopoly: 0, reputation: 0, inventory: 'bag'})"
        ],
        mode="add",
    )
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            ["MATCH (n:PLR) WHERE n.identity CONTAINS 'nope' SET n.wealth = 9"],
            mode="mutate",
        )
    assert ei.value.code == "not_found"
    assert ss.store.get("PLR01").fields["wealth"] == "1"
    MutateGate(ss).apply(
        ["MATCH (n:PLR) WHERE n.identity CONTAINS 'Hero' SET n.wealth = 9"],
        mode="mutate",
    )
    assert ss.store.get("PLR01").fields["wealth"] == "9"
    assert ss.store.get("PLR02").fields["wealth"] == "1"


def test_where_equality_starts_ends_in_and_regex(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    MutateGate(ss).apply(
        ["MATCH (n:PLR) WHERE n.identity = 'Hero' SET n.cashflow = 2"],
        mode="mutate",
    )
    assert ss.store.get("PLR01").fields["cashflow"] == "2"
    MutateGate(ss).apply(
        ["MATCH (n:PLR) WHERE n.identity STARTS WITH 'He' SET n.monopoly = 3"],
        mode="mutate",
    )
    assert ss.store.get("PLR01").fields["monopoly"] == "3"
    MutateGate(ss).apply(
        ["MATCH (n:PLR) WHERE n.identity ENDS WITH 'ro' SET n.reputation = 4"],
        mode="mutate",
    )
    assert ss.store.get("PLR01").fields["reputation"] == "4"
    MutateGate(ss).apply(
        ["MATCH (n:PLR) WHERE n.identity =~ 'H.*o' SET n.inventory = 'box'"],
        mode="mutate",
    )
    assert ss.store.get("PLR01").fields["inventory"] == "box"
    MutateGate(ss).apply(
        ["MATCH (n:PLR {id: 'PLR01'}) SET n.inventory = '[\"bag\",\"key\"]'"],
        mode="mutate",
    )
    MutateGate(ss).apply(
        ["MATCH (n:PLR) WHERE 'key' IN n.inventory SET n.wealth = 8"],
        mode="mutate",
    )
    assert ss.store.get("PLR01").fields["wealth"] == "8"


def test_where_false_unique_match_does_not_set(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            ["MATCH (n:PLR {id: 'PLR01'}) WHERE n.identity CONTAINS 'zzz' SET n.wealth = 9"],
            mode="mutate",
        )
    assert ei.value.code == "not_found"
    assert ss.store.get("PLR01").fields["wealth"] == "1"


def test_where_false_delete_is_noop(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            ["MATCH (n:PLR) WHERE n.identity CONTAINS 'zzz' DELETE n"],
            mode="mutate",
        )
    assert ei.value.code == "not_found"
    assert ss.store.get("PLR01") is not None


def test_unsupported_where_refuses_nothing_applied(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            ["MATCH (n:PLR) WHERE n.wealth > 0 SET n.wealth = 9"],
            mode="mutate",
        )
    assert ei.value.code == "unsupported_predicate"
    assert "WHERE" in ei.value.message
    assert ss.store.get("PLR01").fields["wealth"] == "1"


def test_where_true_edge_delete_still_works(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    MutateGate(ss).apply(
        [
            "CREATE (:PLR {id: 'PLR02', identity: 'Villain', wealth: 1, cashflow: 0, "
            "monopoly: 0, reputation: 0, inventory: 'bag'})"
        ],
        mode="add",
    )
    MutateGate(ss).apply(
        ["MATCH (a {id: 'PLR01'}), (b {id: 'PLR02'}) CREATE (a)-[:knows {id: 'E_k'}]->(b)"],
        mode="add",
        allow_new_relation=True,
    )
    MutateGate(ss).apply(
        ["MATCH (n WHERE true)-[r {id: 'E_k'}]->() DELETE r"],
        mode="mutate",
    )
    assert ss.store.get("E_k") is None


def test_map_equality_still_filters(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    MutateGate(ss).apply(
        [
            "CREATE (:PLR {id: 'PLR02', identity: 'Villain', wealth: 1, cashflow: 0, "
            "monopoly: 0, reputation: 0, inventory: 'bag'})"
        ],
        mode="add",
    )
    MutateGate(ss).apply(
        ["MATCH (n:PLR {id: 'PLR02'}) SET n.wealth = 7"],
        mode="mutate",
    )
    assert ss.store.get("PLR01").fields["wealth"] == "1"
    assert ss.store.get("PLR02").fields["wealth"] == "7"


def test_cli_acl_save_load_close_who(memnet_temp, schema_file, tmp_path: Path):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    runner.invoke(app, ["session", "acl-enable", "--session", sid])
    runner.invoke(
        app,
        ["session", "acl-grant", "--caller", "owner", "--session", sid],
    )
    snap = tmp_path / "acl.snap"
    denied = runner.invoke(app, ["session", "save", "--file", str(snap), "--session", sid])
    assert denied.exit_code != 0
    assert "acl_who" in denied.stderr
    wrong = runner.invoke(
        app,
        ["session", "save", "--file", str(snap), "--session", sid, "--caller", "intruder"],
    )
    assert "acl_denied" in wrong.stderr
    ok = runner.invoke(
        app,
        ["session", "save", "--file", str(snap), "--session", sid, "--caller", "owner"],
    )
    assert ok.exit_code == 0, ok.stderr
    close_no = runner.invoke(app, ["session", "close", sid])
    assert "acl_who" in close_no.stderr
    assert get_session(sid).session_id == sid
    load_no = runner.invoke(app, ["session", "load", "--session", sid])
    assert "acl_who" in load_no.stderr
    closed = runner.invoke(app, ["session", "close", sid, "--caller", "owner"])
    assert closed.exit_code == 0, closed.stderr


def test_explicit_save_unsaveable_names_row(memnet_temp, schema_file, tmp_path: Path):
    ss = open_session(map_file=str(schema_file), caps=Caps())
    MutateGate(ss).apply([_PLR], mode="add")
    rec = ss.store.get("PLR01")
    rec.fields["identity"] = "x" * 9000
    path = tmp_path / "bad.snap"
    with pytest.raises(MemNetError) as ei:
        write_snapshot(ss, path)
    assert ei.value.code == "snapshot_unsaveable"
    assert "PLR" in ei.value.message
    assert "PLR01" in ei.value.message
    assert not path.exists()


def test_expire_save_unsaveable_writes_no_file(
    memnet_temp, schema_file, tmp_path: Path, monkeypatch
):
    """If round-trip verify fails, expire-save warns and leaves no snap file."""
    monkeypatch.setenv("MEMNET_SAVE_ON_EXPIRE", "1")
    monkeypatch.setenv("MEMNET_EXPIRE_SNAPSHOT_DIR", str(tmp_path))
    ss = open_session(map_file=str(schema_file), caps=Caps())
    MutateGate(ss).apply([_PLR], mode="add")
    rec = ss.store.get("PLR01")
    rec.fields["identity"] = "x" * 9000
    snapshot_expired_session(ss.session_id, Caps())
    snaps = list(tmp_path.glob("*.snap"))
    assert snaps == []
