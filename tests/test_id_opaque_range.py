"""Owner rule (18:47 TPE): an id is opaque identity; no meaning from its value, order or sequence.

Red-first for symphony range-where-id-index (P-index-2). Range WHERE (<, >, <=, >=)
on the ``id`` property of a node or relationship pattern is refused
unsupported_predicate, number or string operand, bare or inside AND / OR / NOT,
with nothing written (rows unchanged; session text unchanged apart from the
``#@IDHW:`` line). Equality on ``id`` keeps working.
"""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.snapshot import snapshot_text

_MAP = ["SCHEMA PRT ; fields=id name role"]


def _session():
    """P1..P5 (P1 has no edges); E1 P2->P3 kind a, E2 P3->P4 kind c, E3 P4->P5 kind a."""
    ss = open_session(map_lines=_MAP)
    gate = MutateGate(ss)
    gate.apply(
        [f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: 'r'}})" for i in range(1, 6)],
        mode="add",
    )
    for eid, a, b, kind in [
        ("E1", "P2", "P3", "a"),
        ("E2", "P3", "P4", "c"),
        ("E3", "P4", "P5", "a"),
    ]:
        gate.apply(
            [
                f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) "
                f"CREATE (a)-[:links {{id: '{eid}', kind: '{kind}'}}]->(b)"
            ],
            mode="mutate",
            allow_new_relation=True,
        )
    return ss


def _mutate(ss, stmt: str):
    return MutateGate(ss).apply([stmt], mode="mutate")


def _rows(ss) -> dict[str, tuple[str, dict[str, str]]]:
    return {h: (r.tag, dict(r.fields)) for h, r in ss.store._by_hid.items()}


def _text(ss) -> str:
    return "\n".join(ln for ln in snapshot_text(ss).split("\n") if not ln.startswith("#@IDHW:"))


def _assert_refused_unchanged(ss, stmt: str) -> MemNetError:
    rows, text = _rows(ss), _text(ss)
    with pytest.raises(MemNetError) as ei:
        _mutate(ss, stmt)
    assert ei.value.code == "unsupported_predicate", (stmt, ei.value.code, ei.value.message)
    assert _rows(ss) == rows, f"{stmt!r} wrote rows despite refusal"
    assert _text(ss) == text, f"{stmt!r} changed session text despite refusal"
    return ei.value


_NODE_RANGE = [
    # single-match on code-point order (honoured today), many-match, number operands
    "MATCH (n) WHERE n.id < 'P2' SET n.role = 'b'",
    "MATCH (n) WHERE n.id < 'P5' SET n.role = 'b'",
    "MATCH (n:PRT) WHERE n.id > 'P4' SET n.role = 'b'",
    "MATCH (n) WHERE n.id <= 'P1' SET n.role = 'b'",
    "MATCH (n) WHERE n.id >= 'P5' SET n.role = 'b'",
    "MATCH (n) WHERE n.id > 3 SET n.role = 'b'",
    "MATCH (n) WHERE n.id <= 2.5 SET n.role = 'b'",
    "MATCH (n) WHERE n.id < 'P2' DELETE n",
    "MATCH (n) WHERE n.id < 'P5' DELETE n",
    "MATCH (n) WHERE n.id >= 1 DELETE n",
    "MATCH (n) WHERE n.id < 'P2' DETACH DELETE n",
    # inside AND / OR / NOT
    "MATCH (n) WHERE n.name = 'part1' AND n.id < 'P2' SET n.role = 'b'",
    "MATCH (n) WHERE n.id < 'P2' AND n.name = 'part1' DELETE n",
    "MATCH (n) WHERE n.id < 'P2' OR n.name = 'zzz' SET n.role = 'b'",
    "MATCH (n) WHERE n.name = 'zzz' OR n.id <= 'P1' DELETE n",
    "MATCH (n) WHERE NOT n.id >= 'P2' SET n.role = 'b'",
    "MATCH (n) WHERE NOT n.id > 0 DELETE n",
]

_REL_RANGE = [
    "MATCH ()-[r]->() WHERE r.id >= 'E1' SET r.kind = 'b'",
    "MATCH ()-[r]->() WHERE r.id >= 'E3' SET r.kind = 'b'",
    "MATCH ()-[r:links]-() WHERE r.id < 'E2' SET r.kind = 'b'",
    "MATCH ()-[r]->() WHERE r.id > 1 SET r.kind = 'b'",
    "MATCH ()-[r:links]->() WHERE r.id >= 'E1' DELETE r",
    "MATCH ()-[r:links]->() WHERE r.id > 'E2' DELETE r",
    "MATCH ()-[r:links]-() WHERE r.id <= 'E1' DELETE r",
    "MATCH ()-[r:links]->() WHERE r.id <= 2 DELETE r",
    # inside AND / OR / NOT
    "MATCH ()-[r]->() WHERE r.kind = 'a' AND r.id > 'E2' SET r.kind = 'b'",
    "MATCH ()-[r:links]->() WHERE r.id > 'E2' AND r.kind = 'a' DELETE r",
    "MATCH ()-[r]->() WHERE r.id >= 'E3' OR r.kind = 'zzz' SET r.kind = 'b'",
    "MATCH ()-[r:links]->() WHERE r.kind = 'zzz' OR r.id < 'E2' DELETE r",
    "MATCH ()-[r]->() WHERE NOT r.id < 'E3' SET r.kind = 'b'",
    "MATCH ()-[r:links]->() WHERE NOT r.id <= 2 DELETE r",
]


@pytest.mark.parametrize("stmt", _NODE_RANGE)
def test_node_id_range_refused_unchanged(memnet_temp, stmt):
    _assert_refused_unchanged(_session(), stmt)


@pytest.mark.parametrize("stmt", _REL_RANGE)
def test_relationship_id_range_refused_unchanged(memnet_temp, stmt):
    _assert_refused_unchanged(_session(), stmt)


def test_id_equality_still_works(memnet_temp):
    ss = _session()
    _mutate(ss, "MATCH (n) WHERE n.id = 'P1' SET n.role = 'b'")
    roles = {r.fields["id"]: r.fields.get("role") for r in ss.store.list_records("PRT")}
    assert roles == {"P1": "b", "P2": "r", "P3": "r", "P4": "r", "P5": "r"}
    _mutate(ss, "MATCH ()-[r]->() WHERE r.id = 'E2' SET r.kind = 'b'")
    kinds = {e.fields["id"]: e.fields.get("attrs", "") for e in ss.store.list_records("EDG")}
    assert "kind=b" in kinds["E2"]
    assert "kind=b" not in kinds["E1"] and "kind=b" not in kinds["E3"]
    _mutate(ss, "MATCH ()-[r:links]->() WHERE r.id = 'E3' DELETE r")
    assert {e.fields["id"] for e in ss.store.list_records("EDG")} == {"E1", "E2"}
    _mutate(ss, "MATCH (n) WHERE n.id = 'P1' DELETE n")
    assert ss.store.get("P1") is None
    assert ss.store.get("P2") is not None


def test_range_on_non_id_field_still_honoured(memnet_temp):
    """Guard: the refusal is for id only; range on another field keeps working."""
    ss = _session()
    _mutate(ss, "MATCH (n) WHERE n.name > 'part4' SET n.role = 'b'")
    roles = {r.fields["id"]: r.fields.get("role") for r in ss.store.list_records("PRT")}
    assert roles["P5"] == "b"
    assert [k for k, v in roles.items() if v == "b"] == ["P5"]
