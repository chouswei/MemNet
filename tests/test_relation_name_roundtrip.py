"""One relation-name rule: whatever the write path accepts also saves and restores."""

from __future__ import annotations

from pathlib import Path

import pytest

from memnet.config import (
    RELATION_PATTERN,
    SNAPSHOT_RELATION_PATTERN,
    standard_relation,
    validate_relation,
    validate_snapshot_relation,
)
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.snapshot import load_snapshot_text, materialise_snapshot_text, snapshot_text

_MAP = ["SCHEMA PRT ; fields=id name role"]
_FIXTURE = Path(__file__).parent / "fixtures" / "snapshot-0.19.27.snap"

# written -> standard (stored, saved, returned)
_ACCEPTED = {
    "hasFact": "hasFact",
    "HAS_FACT": "hasFact",
    "SUPPLIES_TO": "suppliesTo",
    "Mixed_1": "mixed_1",
    "seeks_help": "seeks_help",
    "a": "a",
    "A": "a",
    "ABC": "abc",
    "A1_B2": "a1B2",
}
_REJECTED = ["1abc", "has-fact", "", "état", "has fact", "_x"]


def _session():
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        [f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: 'r'}})" for i in range(3)],
        mode="mutate",
        allow_new_relation=True,
    )
    return ss


def _link(ss, rel, a="P0", b="P1", props=""):
    MutateGate(ss).apply(
        [f"MATCH (x {{id: '{a}'}}), (y {{id: '{b}'}}) CREATE (x)-[:{rel}{props}]->(y)"],
        mode="mutate",
        allow_new_relation=True,
    )


def _write_accepts(rel: str) -> bool:
    ss = _session()
    try:
        _link(ss, rel)
    except Exception:
        return False
    return True


def _edge_view(entry):
    """Edges with endpoints resolved to node ids; includes link properties."""
    nid = {r.hid: r.fields.get("id") for r in entry.store.list_records("PRT")}
    return sorted(
        (
            nid[e.fields["src"]],
            e.fields["relation"],
            nid[e.fields["dist"]],
            e.fields.get("at", ""),
            e.fields.get("attrs", ""),
        )
        for e in entry.store.list_records("EDG")
    )


@pytest.mark.parametrize("rel", [*_ACCEPTED, *_REJECTED])
def test_write_save_restore_agree(rel):
    accepted = _write_accepts(rel)
    assert accepted == (rel in _ACCEPTED)
    if not accepted:
        with pytest.raises(MemNetError):
            validate_relation(rel)
        return
    std = _ACCEPTED[rel]
    assert standard_relation(rel) == std
    validate_snapshot_relation(std)
    ss = _session()
    _link(ss, rel, props=" {weight: '3'}")
    before = _edge_view(ss)
    assert len(before) == 1 and before[0][1] == std
    text = snapshot_text(ss)  # save is ok
    for restored in (materialise_snapshot_text(text), load_snapshot_text(text)):
        assert _edge_view(restored) == before
        assert std in restored.relations


def test_write_echoes_standard_type_only_when_it_differs():
    ss = _session()
    r1 = MutateGate(ss).apply(
        ["MATCH (x {id: 'P0'}), (y {id: 'P1'}) CREATE (x)-[:HAS_FACT]->(y)"],
        mode="mutate",
        allow_new_relation=True,
    )
    assert "relation_normalized|HAS_FACT->hasFact" in r1.warnings
    r2 = MutateGate(ss).apply(
        ["MATCH (x {id: 'P0'}), (y {id: 'P2'}) CREATE (x)-[:hasFact]->(y)"],
        mode="mutate",
        allow_new_relation=True,
    )
    assert not any(w.startswith("relation_normalized") for w in r2.warnings)


def test_case_variants_are_one_relation():
    ss = _session()
    _link(ss, "HAS_FACT", "P0", "P1", " {k: 'upper'}")
    _link(ss, "hasFact", "P0", "P2", " {k: 'lower'}")
    assert {e[1] for e in _edge_view(ss)} == {"hasFact"}
    assert "HAS_FACT" not in ss.relations and "hasFact" in ss.relations
    # one type between the same ends: writing both spellings is the same type
    _link(ss, "hasFact", "P1", "P2")
    _link(ss, "HAS_FACT", "P1", "P2")
    assert [e[1] for e in _edge_view(ss)].count("hasFact") == 4
    text = snapshot_text(ss)
    assert "HAS_FACT" not in text
    for restored in (materialise_snapshot_text(text), load_snapshot_text(text)):
        assert _edge_view(restored) == _edge_view(ss)


def _find(ss, pattern_rel):
    rows = MutateGate(ss).apply(
        [f"MATCH (x {{id: 'P0'}})-[e:{pattern_rel}]->(y) DELETE e"],
        mode="mutate",
        allow_new_relation=True,
    )
    return rows


def test_match_and_delete_normalize_the_pattern():
    ss = _session()
    _link(ss, "hasFact", "P0", "P1")
    _find(ss, "HAS_FACT")  # upper-case pattern finds and deletes the hasFact link
    assert _edge_view(ss) == []
    _link(ss, "HAS_FACT", "P0", "P1")
    _find(ss, "hasFact")
    assert _edge_view(ss) == []


def test_pipe_edg_and_snapshot_hand_edit_normalize():
    ss = _session()
    MutateGate(ss).apply(
        ["@EDG: E9|P0|SUPPLIES_TO|P1|||persistent"], mode="add", allow_new_relation=True
    )
    assert _edge_view(ss) == [("P0", "suppliesTo", "P1", "", "")]
    text = snapshot_text(ss)
    edited = text.replace("suppliesTo", "SUPPLIES_TO")  # hand-edited upper-case snapshot
    for restored in (materialise_snapshot_text(edited), load_snapshot_text(edited)):
        assert _edge_view(restored) == [("P0", "suppliesTo", "P1", "", "")]
        assert "suppliesTo" in restored.relations and "SUPPLIES_TO" not in restored.relations


def test_saved_snapshot_check_stays_strict_lower_camel():
    assert SNAPSHOT_RELATION_PATTERN == r"^[a-z][a-zA-Z0-9_]*$"
    with pytest.raises(MemNetError):
        validate_snapshot_relation("HAS_FACT")
    ss = _session()
    ss.relations.add("HAS_FACT")  # bypass the write path: save folds it
    assert "@REL: hasFact" in snapshot_text(ss)
    ss.relations.add("bad-name")  # not a valid name at all: save still refuses
    with pytest.raises(MemNetError):
        snapshot_text(ss)


def test_pattern_is_the_documented_single_rule():
    assert RELATION_PATTERN == r"^[A-Za-z][A-Za-z0-9_]*$"


def test_old_snapshot_from_0_19_27_restores_unchanged():
    text = _FIXTURE.read_text(encoding="utf-8")
    for restored in (materialise_snapshot_text(text), load_snapshot_text(text)):
        assert _edge_view(restored) == [
            ("P0", "dependsOn", "P2", "", "old"),
            ("P0", "links", "P1", "", "weight=3"),
            ("P1", "hasFact", "P2", "", ""),
        ]
    # Re-saving restores the same edges (round-trip stays stable).
    again = materialise_snapshot_text(snapshot_text(load_snapshot_text(text)))
    assert _edge_view(again) == _edge_view(materialise_snapshot_text(text))


def test_snapshot_with_invalid_relation_line_is_refused():
    ss = _session()
    _link(ss, "HAS_FACT")
    text = snapshot_text(ss).replace("hasFact", "has-fact")
    with pytest.raises(MemNetError):
        materialise_snapshot_text(text)


def test_seed_loader_rejects_bad_names(tmp_path, monkeypatch):
    from memnet import session

    seed = tmp_path / "relations.seed.txt"
    seed.write_text("good_one\nBAD-ONE\n", encoding="utf-8")
    monkeypatch.setattr(session, "examples_dir", lambda: tmp_path)
    with pytest.raises(MemNetError):
        session._seed_relations()


def test_trailing_newline_is_not_a_valid_name():
    with pytest.raises(MemNetError):
        validate_relation("bad\n")


def _raw_legacy_edge(ss, rel="ABOUT", a="P0", b="P1"):
    """An edge stored under its raw upper-case name, as pre-fix builds wrote it."""
    from memnet.models import Record

    nid = {r.fields["id"]: r.hid for r in ss.store.list_records("PRT")}
    edge = Record(
        tag="EDG",
        fields={
            "id": "",
            "src": nid[a],
            "dist": nid[b],
            "relation": rel,
            "at": "",
            "attrs": "",
            "recycle": "persistent",
        },
    )
    ss.store.write_order.append(edge.hid)
    ss.store._index_tag(edge)
    ss.store._by_hid[edge.hid] = edge
    ss.store._index_edge(edge)
    ss.relations.add(rel)


def _count(ss, rel):
    rows = MutateGate(ss).apply(
        [f"MATCH (x {{id: 'P0'}})-[e:{rel}]->(y) DELETE e"],
        mode="mutate",
        allow_new_relation=True,
    )
    return rows


def test_legacy_raw_upper_case_edge_is_found_and_deleted_by_both_spellings():
    # B1: an edge stored as ABOUT through the raw path (pre-fix store).
    for pattern in ("ABOUT", "about"):
        ss = _session()
        _raw_legacy_edge(ss)
        assert [e[1] for e in _edge_view(ss)] == ["ABOUT"]
        hops = ss.store.context_walk_hops(anchor_id="P0")
        assert [h[1] for h in hops] == ["about"]  # reads fold the stored name
        res = _count(ss, pattern)
        assert not any("not_found" in str(w) for w in res.warnings)
        assert _edge_view(ss) == [], pattern


@pytest.mark.parametrize(
    "rel", [*_ACCEPTED, "A", "X_", "HAS__FACT", "HAS_2X", "Mixed_1", "HAS_FACT_"]
)
def test_standard_relation_is_snapshot_valid_and_idempotent(rel):
    # B2
    std = standard_relation(rel)
    validate_snapshot_relation(std)
    assert standard_relation(std) == std


def test_pipe_edg_ack_carries_relation_normalized_warning():
    ss = _session()
    r = MutateGate(ss).apply(
        ["@EDG: E9|P0|HAS_FACT|P1|||persistent", "@EDG: E8|P0|hasFact|P2|||persistent"],
        mode="add",
        allow_new_relation=True,
    )
    assert r.warnings == ["relation_normalized|HAS_FACT->hasFact"]


def test_raw_stored_upper_case_edge_saves_and_restores_as_standard_name():
    # B3: a pre-fix raw ABOUT edge must not make session_save refuse.
    ss = _session()
    _raw_legacy_edge(ss)
    text = snapshot_text(ss)  # no snapshot_unsaveable
    assert "ABOUT" not in text
    for loaded in (materialise_snapshot_text(text), load_snapshot_text(text)):
        store = getattr(loaded, "store", loaded)
        rels = [r.fields.get("relation") for r in store.list_records("EDG")]
        assert rels == ["about"]
