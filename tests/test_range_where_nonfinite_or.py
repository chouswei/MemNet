"""L-250b-3 / MN-REQ-14.1: a non-finite field still matches through a true OR sibling.

Positive cases for the #250 SET path (green on 4b8ed16). tests/test_range_where.py
pins the negative side (a non-finite field alone, or with a false OR sibling, is
kept out). Here the range on a non-finite field (1e999, -1e999, NaN) is UNKNOWN,
and UNKNOWN OR TRUE is TRUE, so the row is hit; UNKNOWN AND TRUE stays UNKNOWN, so
it is not.
"""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_MAP = ["SCHEMA T ; fields=id x k y"]
_REL_MAP = ["SCHEMA PRT ; fields=id name"]
_NON_FINITE = ("1e999", "-1e999", "NaN", "nan")


def _mutate(ss, stmt: str):
    return MutateGate(ss).apply([stmt], mode="mutate", allow_new_relation=True)


def _session(*rows: tuple[str, str]):
    """N0..Nk of label T with (x, k)."""
    ss = open_session(map_lines=list(_MAP))
    MutateGate(ss).apply(
        [f"CREATE (:T {{id: 'N{i}', x: '{x}', k: '{k}'}})" for i, (x, k) in enumerate(rows)],
        mode="add",
    )
    return ss


def _hits(ss) -> list[str]:
    return sorted(r.fields["id"] for r in ss.store.list_records("T") if r.fields.get("y") == "hit")


def _set(ss, where: str) -> None:
    _mutate(ss, f"MATCH (n:T) WHERE {where} SET n.y = 'hit'")


@pytest.mark.parametrize("odd", _NON_FINITE)
@pytest.mark.parametrize(
    "where",
    [
        "n.x > 5 OR n.k = 'a'",
        "n.k = 'a' OR n.x > 5",
        "n.x > 100 OR n.k = 'a'",
        "NOT n.x < 5 OR n.k = 'a'",
        "(n.x > 5 AND n.x < 9) OR n.k = 'a'",
        "n.x > 5 OR n.x < -5 OR n.k = 'a'",
    ],
)
def test_non_finite_hit_through_true_or_sibling(memnet_temp, odd, where):
    ss = _session((odd, "a"), ("3", "b"))
    _set(ss, where)
    assert _hits(ss) == ["N0"], where


@pytest.mark.parametrize("odd", _NON_FINITE)
def test_non_finite_or_counts_toward_cardinality(memnet_temp, odd):
    # x=7 matches by range and the odd row through k: two hits, so SET refuses
    ss = _session((odd, "a"), ("3", "b"), ("7", "b"))
    before = {r.fields["id"]: dict(r.fields) for r in ss.store.list_records("T")}
    with pytest.raises(MemNetError) as ei:
        _set(ss, "n.x > 5 OR n.k = 'a'")
    assert ei.value.code == "cue_conflict", ei.value.message
    assert "|Q|=2" in ei.value.message
    assert {r.fields["id"]: dict(r.fields) for r in ss.store.list_records("T")} == before
    # and with the finite match removed from the range, the odd row is the one hit
    _set(ss, "n.x > 8 OR n.k = 'a'")
    assert _hits(ss) == ["N0"]


@pytest.mark.parametrize("odd", _NON_FINITE)
@pytest.mark.parametrize(
    "where",
    [
        "n.x > 5 AND n.k = 'a'",
        "n.k = 'a' AND n.x < 5",
        "n.x >= -1000000 AND n.k = 'a'",
        "(n.x > 5 OR n.k = 'zzz') AND n.k = 'a'",
        "n.k = 'a' AND NOT n.x > 5",
    ],
)
def test_non_finite_under_and_with_true_sibling_no_match(memnet_temp, odd, where):
    ss = _session((odd, "a"), ("3", "b"))
    before = {r.fields["id"]: dict(r.fields) for r in ss.store.list_records("T")}
    with pytest.raises(MemNetError) as ei:
        _set(ss, where)
    assert ei.value.code == "not_found", (where, ei.value.message)
    assert {r.fields["id"]: dict(r.fields) for r in ss.store.list_records("T")} == before


@pytest.mark.parametrize("odd", _NON_FINITE)
def test_non_finite_or_delete_hits_one(memnet_temp, odd):
    ss = _session((odd, "a"), ("3", "b"))
    _mutate(ss, "MATCH (n:T) WHERE n.x > 5 OR n.k = 'a' DELETE n")
    assert sorted(r.fields["id"] for r in ss.store.list_records("T")) == ["N1"]


def _rel_session(odd: str):
    """P0 -> P1 (n = odd, kind a), P1 -> P2 (n = 3, kind b)."""
    ss = open_session(map_lines=list(_REL_MAP))
    gate = MutateGate(ss)
    gate.apply(
        [f"CREATE (:PRT {{id: 'P{i}', name: 'p{i}'}})" for i in range(3)],
        mode="mutate",
        allow_new_relation=True,
    )
    for eid, a, b, n, kind in (("E1", "P0", "P1", odd, "a"), ("E2", "P1", "P2", "3", "b")):
        gate.apply(
            [
                f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) "
                f"CREATE (a)-[:links {{id: '{eid}', kind: '{kind}', n: '{n}'}}]->(b)"
            ],
            mode="mutate",
            allow_new_relation=True,
        )
    return ss


def _attrs(rec) -> dict[str, str]:
    raw = rec.fields.get("attrs", "")
    return dict(kv.split("=", 1) for kv in raw.split(";") if kv)


@pytest.mark.parametrize("odd", _NON_FINITE)
def test_relationship_non_finite_hit_through_true_or_sibling(memnet_temp, odd):
    ss = _rel_session(odd)
    _mutate(ss, "MATCH ()-[r:links]-() WHERE r.n > 5 OR r.kind = 'a' SET r.tag = 'hit'")
    tags = {e.fields["id"]: _attrs(e).get("tag", "") for e in ss.store.list_records("EDG")}
    assert tags == {"E1": "hit", "E2": ""}


@pytest.mark.parametrize("odd", _NON_FINITE)
def test_relationship_non_finite_under_and_no_match(memnet_temp, odd):
    ss = _rel_session(odd)
    before = {e.fields["id"]: dict(e.fields) for e in ss.store.list_records("EDG")}
    with pytest.raises(MemNetError) as ei:
        _mutate(ss, "MATCH ()-[r:links]-() WHERE r.n > -1000000 AND r.kind = 'a' SET r.tag = 'hit'")
    assert ei.value.code == "not_found", ei.value.message
    after = {e.fields["id"]: dict(e.fields) for e in ss.store.list_records("EDG")}
    assert after == before
