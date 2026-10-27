"""Relationship DELETE resolves by exact id or end nodes; id-less edges stay addressable."""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.gql import emit_item, parse
from memnet.mutate_gate import MutateGate
from memnet.output import emit_record
from memnet.pin_map_composer import record_to_gql_line
from memnet.session import open_session
from memnet.snapshot import load_snapshot_text, materialise_snapshot_text, snapshot_text
from memnet.tier_a import Op

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


def test_end_with_only_label_or_only_props_is_parse_error():
    ss = _session()
    _link(ss, "P0", "P1")
    with pytest.raises(MemNetError) as ei:
        _apply(ss, "MATCH ({id: 'P0'})-[r:links]->(:PRT) DELETE r")
    assert ei.value.code == "parse_error"
    with pytest.raises(MemNetError) as ei:
        _apply(ss, "MATCH ({id: 'P0'})-[r:links]->({name: 'part1'}) DELETE r")
    assert ei.value.code == "parse_error"
    assert len(_edges(ss)) == 1


def test_undirected_delete_with_end_id_refused():
    ss = _session()
    _link(ss, "P0", "P1")
    with pytest.raises(MemNetError) as ei:
        _apply(ss, "MATCH ({id: 'P0'})-[r:links]-({id: 'P1'}) DELETE r")
    assert ei.value.code == "parse_error"
    assert len(_edges(ss)) == 1


def test_both_arrows_delete_refused():
    ss = _session()
    _link(ss, "P0", "P1")
    with pytest.raises(MemNetError) as ei:
        _apply(ss, "MATCH ({id: 'P0'})<-[r:links]->({id: 'P1'}) DELETE r")
    assert ei.value.code == "parse_error"
    assert len(_edges(ss)) == 1


def test_single_end_delete_removes_only_matching_edge():
    ss = _session()
    _link(ss, "P0", "P1")
    _link(ss, "P2", "P1")
    _apply(ss, "MATCH ({id: 'P0'})-[r:links]->() DELETE r")
    p = {r.fields["id"]: r.hid for r in ss.store.list_records("PRT")}
    left = {(e.fields["src"], e.fields["dist"]) for e in _edges(ss)}
    assert left == {(p["P2"], p["P1"])}


def test_minted_edge_id_skips_existing_edge_ids():
    ss = _session()
    _link(ss, "P0", "P1", props=" {id: 'E1'}")
    _link(ss, "P0", "P2", props=" {id: 'E2'}")
    _link(ss, "P1", "P2")
    ids = [e.fields.get("id") for e in _edges(ss)]
    minted = [i for i in ids if i not in ("E1", "E2")]
    assert len(minted) == 1
    assert minted[0] == "E3"
    assert len(set(ids)) == 3


def test_emit_item_drop_round_trips_with_ends():
    (item,) = parse("MATCH ({id: 'P0'})-[r:links]->({id: 'P1'}) DELETE r").items
    assert (item.op, item.frm, item.rel, item.to) == (Op.DROP, "P0", "links", "P1")
    text = emit_item(item, as_mutate=True)
    (again,) = parse(text).items
    assert (again.op, again.frm, again.rel, again.to) == (Op.DROP, "P0", "links", "P1")


def test_edge_id_miss_is_not_found():
    ss = _session()
    _link(ss, "P0", "P1")
    with pytest.raises(MemNetError) as ei:
        _apply(ss, "MATCH ()-[r {id: 'E999'}]-() DELETE r")
    assert ei.value.code == "not_found"
    assert len(_edges(ss)) == 1


def test_pin_map_line_has_no_edge_id_or_el_handle():
    ss = _session()
    _link(ss, "P0", "P1", props=" {id: 'KEEP'}")
    _link(ss, "P1", "P2")
    for edge in _edges(ss):
        line = record_to_gql_line(edge, store=ss.store)
        assert "_el" not in line
        assert "id:" not in line
        assert "KEEP" not in line
        assert edge.hid not in line
        assert edge.fields["id"] not in line
    # legacy id-less edge: EDG dump shows its _elN handle, pin_map does not
    legacy = _edges(ss)[0]
    legacy.fields.pop("id")
    assert legacy.hid.startswith("_el")
    assert legacy.hid in emit_record(legacy, ss.tag_map)
    assert "_el" not in record_to_gql_line(legacy, store=ss.store)


def test_restore_leaves_legacy_id_less_edge_id_less():
    ss = _session()
    _link(ss, "P0", "P1")
    # legacy snapshot: the EDG line has an empty id column
    text = snapshot_text(ss).replace("@EDG: E1|", "@EDG: |")
    assert "@EDG: |" in text
    restored = materialise_snapshot_text(text)
    (edge,) = restored.store.list_records("EDG")
    assert not edge.fields.get("id")
    assert edge.hid.startswith("_el")
    assert edge.hid in emit_record(edge, restored.tag_map)
    assert "_el" not in record_to_gql_line(edge, store=restored.store)


def _id_less_edge_text():
    ss = _session()
    _link(ss, "P0", "P1")
    (edge,) = _edges(ss)
    edge.fields.pop("id")
    text = snapshot_text(ss)
    assert "sn_edg_" not in text
    assert "@EDG: |" in text
    return text


def test_legacy_id_less_edge_restores_via_both_loaders():
    text = _id_less_edge_text()
    for restored in (
        materialise_snapshot_text(text),
        load_snapshot_text(text),
    ):
        (edge,) = restored.store.list_records("EDG")
        assert not edge.fields.get("id")
        assert edge.hid.startswith("_el")
        assert edge.hid in emit_record(edge, restored.tag_map)
        assert "_el" not in record_to_gql_line(edge, store=restored.store)


def test_id_less_edge_survives_repeated_snapshot_restore():
    text = _id_less_edge_text()
    ss = load_snapshot_text(text)
    for _cycle in range(3):
        text = snapshot_text(ss)
        assert "sn_edg_" not in text
        ss = load_snapshot_text(text)
        (edge,) = _edges(ss)
        stored = edge.fields.get("id") or ""
        assert stored == ""
        assert "sn_edg_" not in stored
        assert not stored.startswith("E")
        assert edge.hid.startswith("_el")
        assert edge.hid in emit_record(edge, ss.tag_map)
        assert "_el" not in record_to_gql_line(edge, store=ss.store)


def test_id_less_edge_without_emit_row_refuses_snapshot(monkeypatch):
    from memnet import snapshot as snapshot_mod
    from memnet.models import TagMap

    ss = _session()
    _link(ss, "P0", "P1")
    (edge,) = _edges(ss)
    edge.fields.pop("id")
    real = snapshot_mod._snapshot_emit_tag_map

    def _no_edg_row(sess):
        full = real(sess)
        return TagMap(tags={t: d for t, d in full.tags.items() if t != "EDG"})

    monkeypatch.setattr(snapshot_mod, "_snapshot_emit_tag_map", _no_edg_row)
    with pytest.raises(MemNetError) as excinfo:
        snapshot_text(ss)
    assert excinfo.value.code == "snapshot_unsaveable"
