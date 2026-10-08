"""Endleaf Keeper items 2–4: LF-only mutate, snapshot extras, MATCH and TTL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from memnet.cli import _read_ingest_input
from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import get_session, open_session, set_now_override
from memnet.snapshot import load_snapshot, write_snapshot
from memnet.wire import SPLITLINES_SEPARATORS

_MAP = ["SCHEMA CST ; fields=id name role"]
_INJECT_SEPS = [sep for sep in SPLITLINES_SEPARATORS if sep != "\n"]


def _nicks(ss) -> set[str]:
    return {rec.fields.get("id", "") for rec in ss.store._by_hid.values()}


@pytest.mark.parametrize("sep", _INJECT_SEPS)
def test_pipe_and_gql_keep_splitlines_separators_inside_values(memnet_temp, sep: str, monkeypatch):
    literal = f"@CST: GOOD|ok{sep}x|r"
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(literal))
    lines = _read_ingest_input(None, None, True, Caps())
    assert lines == [literal]
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(lines, mode="add")
    got = ss.store.get("GOOD")
    assert got is not None
    assert got.fields["name"] == f"ok{sep}x"

    injected = f"@CST: GOOD2|ok|r{sep}@CST: EVIL|injected|r"
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(injected))
    split = _read_ingest_input(None, None, True, Caps())
    assert len(split) == 1
    assert sep in split[0]
    try:
        MutateGate(ss).apply(split, mode="add")
    except MemNetError:
        pass
    assert "EVIL" not in _nicks(ss)

    gql_keep = f"CREATE (:CST {{id: 'GKEEP', name: 'a{sep}b', role: 'r'}})"
    MutateGate(ss).apply([gql_keep], mode="mutate")
    kept = ss.store.get("GKEEP")
    assert kept is not None
    assert kept.fields["name"] == f"a{sep}b"

    gql_inject = (
        "CREATE (:CST {id: 'G2', name: 'ok', role: 'r'})"
        + sep
        + "CREATE (:CST {id: 'EVIL', name: 'x', role: 'r'})"
    )
    try:
        MutateGate(ss).apply([gql_inject], mode="mutate")
    except MemNetError as exc:
        assert exc.code == "parse_error"
    assert "EVIL" not in _nicks(ss)


def test_lf_splits_statements_and_embedded_cr_does_not(memnet_temp):
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        [
            "CREATE (:CST {id: 'GOOD', name: 'ok', role: 'r'})\n"
            "CREATE (:CST {id: 'NEXT', name: 'n', role: 'r'})"
        ],
        mode="mutate",
    )
    assert ss.store.get("GOOD") is not None
    assert ss.store.get("NEXT") is not None
    cr = (
        "CREATE (:CST {id: 'CR1', name: 'ok', role: 'r'})\r"
        "CREATE (:CST {id: 'EVIL', name: 'x', role: 'r'})"
    )
    try:
        MutateGate(ss).apply([cr], mode="mutate")
    except MemNetError as exc:
        assert exc.code == "parse_error"
    assert ss.store.get("EVIL") is None


def test_snapshot_mixed_case_label_persists_extra(memnet_temp, tmp_path: Path):
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        ["CREATE (:Cst {id: 'N_X', name: 'keep', role: 'r', extra_k: 'extra_v'})"],
        mode="add",
    )
    rec = ss.store.get("N_X")
    assert rec is not None
    assert rec.tag == "CST"
    assert rec.fields["extra_k"] == "extra_v"
    rec.tag = "Cst"
    path = tmp_path / "case.snap"
    write_snapshot(ss, path)
    text = path.read_text(encoding="utf-8")
    assert "SCHEMA CST ; fields=id name role extra_k" in text
    loaded = load_snapshot(path)
    got = loaded.store.get("N_X")
    assert got is not None
    assert got.fields["extra_k"] == "extra_v"


def test_schema_without_id_saves_by_widening_snapshot_only(memnet_temp, tmp_path: Path):
    ss = open_session(map_lines=["SCHEMA SEC ; fields=title body status"])
    assert ss.tag_map.get("SEC").fields == ["title", "body", "status"]
    MutateGate(ss).apply(
        ["CREATE (:SEC {title: 'T', body: 'B', status: 'open'})"],
        mode="add",
    )
    live = next(rec for rec in ss.store._by_hid.values() if rec.tag == "SEC")
    assert "id" not in live.fields
    path = tmp_path / "noid.snap"
    write_snapshot(ss, path)
    text = path.read_text(encoding="utf-8")
    assert "SCHEMA SEC ; fields=title body status id" in text
    assert ss.tag_map.get("SEC").fields == ["title", "body", "status"]
    loaded = load_snapshot(path)
    got = next(rec for rec in loaded.store._by_hid.values() if rec.tag == "SEC")
    assert got.fields["title"] == "T"
    assert got.fields["body"] == "B"
    assert got.fields["status"] == "open"
    assert got.fields["id"]
    assert "id" in loaded.tag_map.get("SEC").fields


def test_unloadable_schema_key_fails_closed(memnet_temp, tmp_path: Path):
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        ["CREATE (:CST {id: 'N_S', name: 'keep', role: 'r'})"],
        mode="add",
    )
    rec = ss.store.get("N_S")
    assert rec is not None
    rec.fields["foo bar"] = "x"
    path = tmp_path / "space.snap"
    with pytest.raises(MemNetError) as ei:
        write_snapshot(ss, path)
    assert ei.value.code == "snapshot_unsaveable"
    assert not path.exists()


def test_labelled_match_set_folds_case_and_miss_is_not_found(memnet_temp):
    ss = open_session(
        map_lines=[
            "SCHEMA CST ; fields=id name role",
            "SCHEMA SEC ; fields=id title",
        ]
    )
    MutateGate(ss).apply(
        ["CREATE (:CST {id: 'N1', name: 'a', role: 'r'})"],
        mode="add",
    )
    for label in ("cst", "Cst", "CST"):
        MutateGate(ss).apply(
            [f"MATCH (n:{label} {{id: 'N1'}}) SET n.name = '{label}'"],
            mode="mutate",
        )
        assert ss.store.get("N1").fields["name"] == label
    MutateGate(ss).apply(
        ["CREATE (:Cst {id: 'N2', name: 'a', role: 'r'})"],
        mode="add",
    )
    assert ss.store.get("N2").tag == "CST"
    MutateGate(ss).apply(
        ["MATCH (n:Cst {id: 'N2'}) SET n.name = 'mixed'"],
        mode="mutate",
    )
    MutateGate(ss).apply(
        ["MATCH (n:CST {id: 'N2'}) SET n.name = 'upper'"],
        mode="mutate",
    )
    assert ss.store.get("N2").fields["name"] == "upper"
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            ["MATCH (n:SEC {id: 'N1'}) SET n.name = 'no'"],
            mode="mutate",
        )
    assert ei.value.code == "not_found"
    assert ss.store.get("N1").fields["name"] == "CST"


def test_match_match_edge_is_parse_error_comma_form_works(memnet_temp):
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        [
            "CREATE (:CST {id: 'A', name: 'a', role: 'r'})",
            "CREATE (:CST {id: 'B', name: 'b', role: 'r'})",
        ],
        mode="add",
    )
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            ["MATCH (a {id: 'A'}) MATCH (b {id: 'B'}) CREATE (a)-[:knows]->(b)"],
            mode="mutate",
            allow_new_relation=True,
        )
    assert ei.value.code == "parse_error"
    assert "MATCH" in ei.value.message
    assert not any(rec.tag == "EDG" for rec in ss.store._by_hid.values())
    MutateGate(ss).apply(
        ["MATCH (a {id: 'A'}), (b {id: 'B'}) CREATE (a)-[:knows]->(b)"],
        mode="mutate",
        allow_new_relation=True,
    )
    assert any(rec.tag == "EDG" for rec in ss.store._by_hid.values())


def test_ttl_is_minutes_and_access_after_expiry_refuses(memnet_temp):
    t0 = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
    set_now_override(t0)
    ss = open_session(map_lines=_MAP, ttl_minutes=60)
    sid = ss.session_id
    set_now_override(t0 + timedelta(seconds=130))
    got = get_session(sid)
    assert got.session_id == sid
    set_now_override(t0)
    fresh = open_session(map_lines=_MAP, ttl_minutes=60)
    fresh_id = fresh.session_id
    set_now_override(t0 + timedelta(minutes=61))
    with pytest.raises(MemNetError) as ei:
        get_session(fresh_id)
    assert ei.value.code == "session_expired"
    set_now_override(None)
