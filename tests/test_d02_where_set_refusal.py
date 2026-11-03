"""MN-VER-14-D02 fix test: relationship WHERE + SET is honoured, not refused as DELETE.

D02 was: a single GQL statement that puts a WHERE on a relationship pattern and
then SETs a relationship property was refused unsupported_predicate with a
message about relationship DELETE, though the statement has no DELETE.
MN-REQ-03.4 asks for honour-or-refuse with an accurate code. WhereSetRefusalFix:
the SET applies to exactly the matching relationships and deletes nothing; a
relationship WHERE shape that stays unsupported (a range) is refused
unsupported_predicate naming the clause used, never DELETE, with no partial write.

Node WHERE + SET (MATCH (n:X) WHERE n.k = 'a' SET n.v = 'b') is honoured already
(tests/test_engine_roundtrip_where_acl.py).
"""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_MAP = ["SCHEMA PRT ; fields=id name role"]

D02_STATEMENTS = [
    "MATCH ()-[r:links]-() WHERE r.kind = 'a' SET r.kind = 'b'",
    "MATCH (a)-[r:links]->(b) WHERE r.kind = 'a' SET r.kind = 'b'",
    "MATCH ()-[r {id: 'E1'}]-() WHERE r.kind = 'a' SET r.kind = 'b'",
]


def _apply(ss, *stmts, **kw):
    return MutateGate(ss).apply(list(stmts), mode="mutate", **kw)


def _session():
    """P0-[E1 links kind=a]->P1-[E2 links kind=c]->P2."""
    ss = open_session(map_lines=_MAP)
    _apply(
        ss,
        *[f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: 'r'}})" for i in range(3)],
        allow_new_relation=True,
    )
    _apply(
        ss,
        "MATCH (a {id: 'P0'}), (b {id: 'P1'}) CREATE (a)-[:links {id: 'E1', kind: 'a', n: 2}]->(b)",
        allow_new_relation=True,
    )
    _apply(
        ss,
        "MATCH (a {id: 'P1'}), (b {id: 'P2'}) CREATE (a)-[:links {id: 'E2', kind: 'c', n: 0}]->(b)",
        allow_new_relation=True,
    )
    return ss


def _attrs(rec) -> dict[str, str]:
    raw = rec.fields.get("attrs", "")
    return dict(kv.split("=", 1) for kv in raw.split(";") if kv)


def _edges(ss) -> dict[str, dict[str, str]]:
    return {e.fields["id"]: _attrs(e) for e in ss.store.list_records("EDG")}


def _state(ss):
    nodes = sorted((r.hid, tuple(sorted(r.fields.items()))) for r in ss.store.list_records("PRT"))
    edges = sorted((e.hid, tuple(sorted(e.fields.items()))) for e in ss.store.list_records("EDG"))
    return nodes, edges


@pytest.mark.parametrize("statement", D02_STATEMENTS)
def test_d02_relationship_where_set_updates_only_matching(memnet_temp, statement):
    """WHERE + SET on a relationship sets kind='b' on E1 only; nothing is deleted."""
    ss = _session()
    assert _edges(ss)["E1"]["kind"] == "a"
    assert _edges(ss)["E2"]["kind"] == "c"
    n_nodes = len(ss.store.list_records("PRT"))
    n_edges = len(ss.store.list_records("EDG"))

    _apply(ss, statement)

    edges = _edges(ss)
    assert len(ss.store.list_records("PRT")) == n_nodes
    assert len(ss.store.list_records("EDG")) == n_edges
    assert set(edges) == {"E1", "E2"}
    assert edges["E1"]["kind"] == "b"
    assert edges["E1"]["n"] == "2"
    assert edges["E2"] == {"kind": "c", "n": "0"}


def test_d02_unsupported_relationship_where_refused_without_delete(memnet_temp):
    """A range WHERE on a relationship is refused unsupported_predicate, not as DELETE."""
    ss = _session()
    before = _state(ss)
    statement = "MATCH ()-[r:links]-() WHERE r.n > 1 SET r.kind = 'b'"
    with pytest.raises(MemNetError) as ei:
        _apply(ss, statement)
    assert ei.value.code == "unsupported_predicate"
    msg = str(ei.value)
    assert "DELETE" not in msg.upper(), f"refusal names DELETE: {msg!r}"
    assert _state(ss) == before
