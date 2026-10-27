"""Relationship DELETE resolves by exact id or end nodes; id-less edges stay addressable."""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.output import emit_record
from memnet.pin_map_composer import record_to_gql_line
from memnet.session import open_session

_MAP = ["SCHEMA PRT ; fields=id name role"]


def _session():
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        [f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: 'r'}})" for i in range(3)],
        mode="mutate",
        allow_new_relation=True,
    )
    return ss


def _apply(ss, *stmts):
    return MutateGate(ss).apply(list(stmts), mode="mutate", allow_new_relation=True)


def _edges(ss):
    return [r for r in ss.store.list_records("EDG")]


def _link(ss, a, b, rel="links", props=""):
    _apply(ss, f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) CREATE (a)-[:{rel}{props}]->(b)")


def test_endpoint_delete_removes_only_that_edge():
    ss = _session()
    _link(ss, "P0", "P1")
    _link(ss, "P0", "P2")
    _link(ss, "P1", "P2")
    _apply(ss, "MATCH ({id: 'P0'})-[r:links]->({id: 'P2'}) DELETE r")
    left = {(e.fields["src"], e.fields["dist"]) for e in _edges(ss)}
    p = {r.fields["id"]: r.hid for r in ss.store.list_records("PRT")}
    assert left == {(p["P0"], p["P1"]), (p["P1"], p["P2"])}


def test_reverse_arrow_delete():
    ss = _session()
    _link(ss, "P0", "P1")
    _apply(ss, "MATCH ({id: 'P1'})<-[r:links]-({id: 'P0'}) DELETE r")
    assert _edges(ss) == []


def test_delete_by_internal_el_id():
    ss = _session()
    _link(ss, "P0", "P1")
    _link(ss, "P0", "P2")
    first = _edges(ss)[0]
    _apply(ss, f"MATCH ()-[r {{id: '{first.hid}'}}]-() DELETE r")
    assert [e.hid for e in _edges(ss)] and first.hid not in {e.hid for e in _edges(ss)}
    assert len(_edges(ss)) == 1


def test_empty_id_refused():
    ss = _session()
    _link(ss, "P0", "P1")
    with pytest.raises(MemNetError):
        _apply(ss, "MATCH ()-[r {id: ''}]-() DELETE r")
    assert len(_edges(ss)) == 1


def test_delete_without_id_or_endpoints_refused():
    # Relation-only DELETE (-[r:links]->()) is a deprecated shape that still works
    # (single match deletes, >1 is cue_conflict); only the fully unscoped form is refused.
    ss = _session()
    _link(ss, "P0", "P1")
    with pytest.raises(MemNetError):
        _apply(ss, "MATCH ()-[r]->() DELETE r")
    assert len(_edges(ss)) == 1


def test_multi_match_refused():
    ss = _session()
    _link(ss, "P0", "P1")
    _link(ss, "P0", "P1")
    with pytest.raises(MemNetError) as ei:
        _apply(ss, "MATCH ({id: 'P0'})-[r:links]->({id: 'P1'}) DELETE r")
    assert ei.value.code == "cue_conflict"
    assert len(_edges(ss)) == 2


def test_missing_end_is_not_found():
    ss = _session()
    _link(ss, "P0", "P1")
    with pytest.raises(MemNetError) as ei:
        _apply(ss, "MATCH ({id: 'NOPE'})-[r:links]->({id: 'P1'}) DELETE r")
    assert ei.value.code == "not_found"
    assert len(_edges(ss)) == 1


def test_create_without_id_mints_edge_id():
    ss = _session()
    _link(ss, "P0", "P1")
    _link(ss, "P0", "P2")
    ids = [e.fields.get("id") for e in _edges(ss)]
    assert all(i and i.startswith("E") for i in ids)
    assert len(set(ids)) == 2


def test_edge_reads_show_internal_id_when_no_user_id():
    ss = _session()
    _link(ss, "P0", "P1", props=" {id: 'KEEP'}")
    edge = _edges(ss)[0]
    # user id present: EDG dump shows it, pin_map line stays id-free (wire profile 2)
    assert "KEEP" in emit_record(edge, ss.tag_map)
    assert "KEEP" not in record_to_gql_line(edge, store=ss.store)
    # id-less edge (legacy only; CREATE mints E ids): dump shows the _elN handle,
    # pin_map still shows no edge id
    edge.fields.pop("id")
    line = record_to_gql_line(edge, store=ss.store)
    assert "id:" not in line
    dump = emit_record(edge, ss.tag_map)
    assert edge.hid in dump
    # and that shown id deletes the edge
    _apply(ss, f"MATCH ()-[r {{id: '{edge.hid}'}}]-() DELETE r")
    assert _edges(ss) == []
