"""MN-REQ-14.1 / MN-VER-14-S01: range WHERE (<, >, <=, >=) on node and relationship patterns.

Red-first tests for symphony range-where-id-index (node P-range). Interface
pinned for M2:

- RHS is a number literal or a quoted string; anything else (property, $param,
  true, null, bare word, literal on the left) is refused unsupported_predicate,
  "WHERE <op> operand is not honoured" for a bad RHS, with nothing written.
- A field is numeric iff it fullmatches -?\\d+(\\.\\d+)?([eE][+-]?\\d+)?.
  Number vs numeric field compares numerically; string vs non-numeric field
  compares by code point. Number vs non-numeric field and a missing or empty
  field: no match (never raise). A quoted string vs a numeric-looking field is
  refused where_type_mismatch (score /tmp/srs/score.md §1.6, D-T3), as is a
  quoted number operand such as '2000' (D-T2).
- NOT over a no-match range is still no match.
- Cardinality is unchanged: node SET / DELETE and relationship DELETE need
  exactly one match (0 -> not_found, >1 -> cue_conflict, nothing written);
  relationship SET updates every match.
- MATCH … WHERE <range> RETURN stays refused product_gate.
"""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.in_process_engine import run_argv
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_MAP = ["SCHEMA T ; fields=id name x y"]
_REL_MAP = ["SCHEMA PRT ; fields=id name role"]

_MISSING = object()


def _gql_str(val: str) -> str:
    return "'" + val.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _session(*values):
    """Nodes N0..Nk of label T; x is each value (str quoted, number bare, _MISSING omitted)."""
    ss = open_session(map_lines=_MAP)
    stmts = []
    for i, v in enumerate(values):
        if v is _MISSING:
            x = ""
        elif isinstance(v, str):
            x = f", x: {_gql_str(v)}"
        else:
            x = f", x: {v}"
        stmts.append(f"CREATE (:T {{id: 'N{i}', name: 'n{i}'{x}}})")
    MutateGate(ss).apply(stmts, mode="add")
    return ss


def _nodes(ss) -> dict[str, dict[str, str]]:
    return {r.fields["id"]: dict(r.fields) for r in ss.store.list_records("T")}


def _mutate(ss, stmt: str):
    return MutateGate(ss).apply([stmt], mode="mutate")


def _hits(ss) -> list[str]:
    return sorted(i for i, f in _nodes(ss).items() if f.get("y") == "hit")


def _set(ss, where: str) -> None:
    _mutate(ss, f"MATCH (n:T) WHERE {where} SET n.y = 'hit'")


def _assert_refused(ss, stmt: str, code: str) -> MemNetError:
    before = _nodes(ss)
    with pytest.raises(MemNetError) as ei:
        _mutate(ss, stmt)
    assert ei.value.code == code, (stmt, ei.value.code, ei.value.message)
    assert _nodes(ss) == before, f"{stmt!r} wrote despite {code}"
    return ei.value


# (values, WHERE, index of the single matching node)
ONE_MATCH = [
    # int (bare numbers on CREATE)
    pytest.param((1, 5, 10), "n.x > 5", 2, id="int-gt"),
    pytest.param((1, 5, 10), "n.x >= 10", 2, id="int-ge"),
    pytest.param((1, 5, 10), "n.x < 5", 0, id="int-lt"),
    pytest.param((1, 5, 10), "n.x <= 1", 0, id="int-le"),
    pytest.param(("9", "10"), "n.x > 9", 1, id="int-numeric-not-lexical"),
    # float
    pytest.param(("1.5", "2.25", "10.0"), "n.x > 2.3", 2, id="float-gt"),
    pytest.param(("1.5", "2.25", "10.0"), "n.x >= 10.0", 2, id="float-ge"),
    pytest.param(("1.5", "2.25", "10.0"), "n.x < 1.6", 0, id="float-lt"),
    pytest.param(("1.5", "2.25", "10.0"), "n.x <= 1.5", 0, id="float-le"),
    # int field vs float literal, float field vs int literal
    pytest.param(("2", "3"), "n.x > 2.5", 1, id="int-vs-float-gt"),
    pytest.param(("2", "3"), "n.x < 2.5", 0, id="int-vs-float-lt"),
    pytest.param(("2", "3"), "n.x >= 3.0", 1, id="int-vs-float-ge"),
    pytest.param(("2", "3"), "n.x <= 2.0", 0, id="int-vs-float-le"),
    pytest.param(("2.5", "1"), "n.x > 2", 0, id="float-vs-int-gt"),
    pytest.param(("1e3", "5"), "n.x > 999", 0, id="exponent-field"),
    # negative
    pytest.param(("-10", "-2", "3"), "n.x < -5", 0, id="neg-lt"),
    pytest.param(("-10", "-2", "3"), "n.x <= -10", 0, id="neg-le"),
    pytest.param(("-10", "-2", "3"), "n.x > -3 AND n.x < 0", 1, id="neg-and"),
    pytest.param(("-10", "-2", "3"), "n.x >= 3", 2, id="neg-ge"),
    # ISO-date strings, code point order
    pytest.param(("2026-01-15", "2026-03-01", "2025-12-31"), "n.x > '2026-02-01'", 1, id="date-gt"),
    pytest.param(
        ("2026-01-15", "2026-03-01", "2025-12-31"), "n.x >= '2026-03-01'", 1, id="date-ge"
    ),
    pytest.param(("2026-01-15", "2026-03-01", "2025-12-31"), "n.x < '2026-01-01'", 2, id="date-lt"),
    pytest.param(
        ("2026-01-15", "2026-03-01", "2025-12-31"), "n.x <= '2025-12-31'", 2, id="date-le"
    ),
    pytest.param(("B", "a"), "n.x > 'Z'", 1, id="codepoint-case"),
    pytest.param(("z", "é"), "n.x > 'z'", 1, id="codepoint-non-ascii"),
    # NOT over a no-match range stays no match
    pytest.param((_MISSING, "3"), "NOT n.x > 5", 1, id="not-missing-is-no-match"),
    pytest.param(("abc", "3"), "NOT n.x > 5", 1, id="not-mismatch-is-no-match"),
]


@pytest.mark.parametrize(("values", "where", "want"), ONE_MATCH)
def test_node_range_set_one_match(memnet_temp, values, where, want):
    ss = _session(*values)
    before = _nodes(ss)
    _set(ss, where)
    assert _hits(ss) == [f"N{want}"]
    after = _nodes(ss)
    for nid, fields in before.items():
        if nid != f"N{want}":
            assert after[nid] == fields


@pytest.mark.parametrize(("values", "where", "want"), ONE_MATCH)
def test_node_range_delete_one_match(memnet_temp, values, where, want):
    ss = _session(*values)
    before = set(_nodes(ss))
    _mutate(ss, f"MATCH (n:T) WHERE {where} DELETE n")
    assert set(_nodes(ss)) == before - {f"N{want}"}


@pytest.mark.parametrize(
    ("where", "want"),
    [("n.x > 5", 2), ("n.x <= 1", 0), ("n.x >= 5 AND n.x < 10", 1)],
)
def test_node_inline_range_where_set(memnet_temp, where, want):
    ss = _session(1, 5, 10)
    _mutate(ss, f"MATCH (n:T WHERE {where}) SET n.y = 'hit'")
    assert _hits(ss) == [f"N{want}"]


@pytest.mark.parametrize("verb", ["SET n.y = 'hit'", "DELETE n"])
@pytest.mark.parametrize("where", ["n.x > 100", "n.x < -100", "n.x >= 11", "n.x <= 0.5"])
def test_node_range_zero_hits_not_found(memnet_temp, where, verb):
    ss = _session(1, 5, 10)
    _assert_refused(ss, f"MATCH (n:T) WHERE {where} {verb}", "not_found")


@pytest.mark.parametrize("verb", ["SET n.y = 'hit'", "DELETE n"])
@pytest.mark.parametrize("where", ["n.x > 1", "n.x < 10", "n.x >= 5", "n.x <= 5"])
def test_node_range_many_hits_cue_conflict(memnet_temp, where, verb):
    ss = _session(1, 5, 10)
    _assert_refused(ss, f"MATCH (n:T) WHERE {where} {verb}", "cue_conflict")


@pytest.mark.parametrize("verb", ["SET n.y = 'hit'", "DELETE n"])
def test_inline_range_zero_and_many_hits(memnet_temp, verb):
    ss = _session(1, 5, 10)
    _assert_refused(ss, f"MATCH (n:T WHERE n.x > 100) {verb}", "not_found")
    _assert_refused(ss, f"MATCH (n:T WHERE n.x > 1) {verb}", "cue_conflict")


# ----- mixed, missing, empty and odd fields: never raise, never match -----

NO_MATCH = [
    pytest.param(("abc",), "n.x > 1", id="number-vs-word"),
    pytest.param(("abc",), "n.x < 1", id="number-vs-word-lt"),
    pytest.param((_MISSING, ""), "n.x < 1", id="missing-empty-lt-number"),
    pytest.param((_MISSING, ""), "n.x >= 0", id="missing-empty-ge-number"),
    pytest.param((_MISSING, ""), "n.x <= 0", id="missing-empty-le-number"),
    pytest.param((_MISSING, ""), "n.x < 'a'", id="missing-empty-lt-string"),
    pytest.param((_MISSING, ""), "n.x <= ''", id="missing-empty-le-empty-string"),
    pytest.param((_MISSING, "", "abc"), "NOT n.x > 5", id="not-over-no-match"),
]
for _odd in ("1e999", "-", "NaN", " 5"):
    for _w in ("n.x > -1000000", "n.x < 1000000", "n.x >= 0", "n.x <= 0"):
        NO_MATCH.append(pytest.param((_odd,), _w, id=f"odd-{_odd.strip() or 'space'}-{_w[4:]}"))


@pytest.mark.parametrize(("values", "where"), NO_MATCH)
def test_range_no_match_is_not_found(memnet_temp, values, where):
    ss = _session(*values)
    _assert_refused(ss, f"MATCH (n:T) WHERE {where} SET n.y = 'hit'", "not_found")
    _assert_refused(ss, f"MATCH (n:T) WHERE {where} DELETE n", "not_found")


# ----- quoted string vs a numeric field: refused where_type_mismatch (D-T3) -----

TYPE_MISMATCH = [
    pytest.param(("5",), "n.x < 'a'", id="string-vs-numeric-field"),
    pytest.param(("-2.5",), "n.x < 'a'", id="string-vs-negative-float-field"),
    pytest.param(("1e3",), "n.x < 'a'", id="string-vs-exponent-field"),
    pytest.param((_MISSING, "", "5"), "NOT n.x < 'a'", id="not-over-string-mismatch"),
]


@pytest.mark.parametrize(("values", "where"), TYPE_MISMATCH)
def test_range_string_vs_numeric_field_refused(memnet_temp, values, where):
    ss = _session(*values)
    want = "WHERE < on n.x: stored number vs quoted string; use a number literal"
    err = _assert_refused(ss, f"MATCH (n:T) WHERE {where} SET n.y = 'hit'", "where_type_mismatch")
    assert err.message == want
    err = _assert_refused(ss, f"MATCH (n:T) WHERE {where} DELETE n", "where_type_mismatch")
    assert err.message == want


def test_range_quoted_number_operand_refused(memnet_temp):
    # was string-skips-numeric: '2000' is a quoted number, refused at parse (D-T2)
    ss = _session("7", "2026-01-15")
    want = "WHERE > on n.x: quoted number '2000'; use a number literal"
    for stmt in (
        "MATCH (n:T) WHERE n.x > '2000' SET n.y = 'hit'",
        "MATCH (n:T) WHERE n.x > '2000' DELETE n",
    ):
        err = _assert_refused(ss, stmt, "where_type_mismatch")
        assert err.message == want


# ----- non-finite fields are UNKNOWN: kept out under NOT, OR and AND -----

_NON_FINITE = ("1e999", "-1e999", "nan")


@pytest.mark.parametrize("odd", _NON_FINITE)
@pytest.mark.parametrize(
    "where",
    [
        "NOT n.x < 5",
        "NOT n.x > 5",
        "NOT n.x >= 0",
        "NOT (n.x < 5 OR n.name = 'zzz')",
        "NOT n.x < 5 OR n.name = 'zzz'",
        "NOT (n.x < 5 AND n.name = 'n0')",
    ],
)
def test_non_finite_alone_no_match(memnet_temp, odd, where):
    ss = _session(odd)
    _assert_refused(ss, f"MATCH (n:T) WHERE {where} SET n.y = 'hit'", "not_found")
    _assert_refused(ss, f"MATCH (n:T) WHERE {where} DELETE n", "not_found")


@pytest.mark.parametrize("odd", _NON_FINITE)
def test_non_finite_not_excluded_with_finite_excluded(memnet_temp, odd):
    # 3 < 5 so NOT drops N1 too: nothing matches
    ss = _session(odd, "3")
    _assert_refused(ss, "MATCH (n:T) WHERE NOT n.x < 5 SET n.y = 'hit'", "not_found")


@pytest.mark.parametrize("odd", _NON_FINITE)
@pytest.mark.parametrize(
    "where",
    [
        "NOT n.x < 5",
        "NOT n.x <= 5",
        "NOT (n.x < 5 OR n.name = 'zzz')",
        "NOT n.x < 5 AND n.name <> 'zzz'",
    ],
)
def test_non_finite_not_selects_only_finite(memnet_temp, odd, where):
    ss = _session("7", odd)
    _set(ss, where)
    assert _hits(ss) == ["N0"]


@pytest.mark.parametrize("odd", _NON_FINITE)
@pytest.mark.parametrize("where", ["n.x < 5 OR n.name = 'zzz'", "n.x > -5 OR n.name = 'zzz'"])
def test_non_finite_or_selects_only_finite(memnet_temp, odd, where):
    ss = _session(odd, "3")
    _set(ss, where)
    assert _hits(ss) == ["N1"]


def _rel_n_session(*ns):
    """P0..Pk; edge E<i> P0->P<i+1> :links with n = ns[i] (quoted)."""
    ss = open_session(map_lines=_REL_MAP)
    gate = MutateGate(ss)
    gate.apply(
        [f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: '{i}'}})" for i in range(len(ns) + 1)],
        mode="mutate",
        allow_new_relation=True,
    )
    for i, n in enumerate(ns):
        gate.apply(
            [
                f"MATCH (a {{id: 'P0'}}), (b {{id: 'P{i + 1}'}}) "
                f"CREATE (a)-[:links {{id: 'E{i}', kind: 'a', n: {_gql_str(n)}}}]->(b)"
            ],
            mode="mutate",
            allow_new_relation=True,
        )
    return ss


@pytest.mark.parametrize("odd", _NON_FINITE)
@pytest.mark.parametrize("where", ["NOT r.n < 5", "NOT (r.n < 5 OR r.kind = 'zzz')"])
def test_relationship_non_finite_kept_out_under_not(memnet_temp, odd, where):
    ss = _rel_n_session("7", odd)
    before = _edges(ss)
    _mutate(ss, f"MATCH ()-[r:links]-() WHERE {where} SET r.kind = 'b'")
    after = _edges(ss)
    assert after["E0"] == {**before["E0"], "kind": "b"}
    assert after["E1"] == before["E1"]
    ss2 = _rel_n_session("7", odd)
    _mutate(ss2, f"MATCH ()-[r:links]-() WHERE {where} DELETE r")
    assert set(_edges(ss2)) == {"E1"}


# ----- refused shapes: unsupported_predicate, session unchanged -----


@pytest.mark.parametrize("op", [">", "<", ">=", "<="])
@pytest.mark.parametrize("rhs", ["n.y", "$p", "true", "null", "abc"])
@pytest.mark.parametrize("verb", ["SET n.y = 'hit'", "DELETE n"])
def test_range_bad_operand_refused(memnet_temp, op, rhs, verb):
    ss = _session("5", "7")
    err = _assert_refused(ss, f"MATCH (n:T) WHERE n.x {op} {rhs} {verb}", "unsupported_predicate")
    assert f"WHERE {op} operand is not honoured" in err.message


@pytest.mark.parametrize("verb", ["SET n.y = 'hit'", "DELETE n"])
def test_range_literal_on_left_refused(memnet_temp, verb):
    ss = _session("5", "7")
    _assert_refused(ss, f"MATCH (n:T) WHERE 5 < n.x {verb}", "unsupported_predicate")


def test_range_return_refused_product_gate(memnet_temp):
    ss = _session("5", "7")
    _assert_refused(ss, "MATCH (n:T) WHERE n.x > 1 RETURN n", "product_gate")


# ----- relationship patterns -----


def _rel_session():
    """P0-[E1 n=2]->P1-[E2 n=0]->P2-[E3 n=5]->P0, all :links."""
    ss = open_session(map_lines=_REL_MAP)
    gate = MutateGate(ss)
    gate.apply(
        [f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: '{i}'}})" for i in range(3)],
        mode="mutate",
        allow_new_relation=True,
    )
    for eid, a, b, n in (("E1", "P0", "P1", 2), ("E2", "P1", "P2", 0), ("E3", "P2", "P0", 5)):
        gate.apply(
            [
                f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) "
                f"CREATE (a)-[:links {{id: '{eid}', kind: 'a', n: {n}}}]->(b)"
            ],
            mode="mutate",
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


@pytest.mark.parametrize(
    ("where", "want"),
    [
        ("r.n > 1", {"E1", "E3"}),
        ("r.n >= 2", {"E1", "E3"}),
        ("r.n < 1", {"E2"}),
        ("r.n <= 2", {"E1", "E2"}),
        ("r.n > 4.5", {"E3"}),
    ],
)
def test_relationship_range_set_updates_every_match(memnet_temp, where, want):
    ss = _rel_session()
    n_nodes = len(ss.store.list_records("PRT"))
    before = _edges(ss)
    _mutate(ss, f"MATCH ()-[r:links]-() WHERE {where} SET r.kind = 'b'")
    after = _edges(ss)
    assert len(ss.store.list_records("PRT")) == n_nodes
    assert set(after) == {"E1", "E2", "E3"}
    for eid in after:
        if eid in want:
            assert after[eid] == {**before[eid], "kind": "b"}, eid
        else:
            assert after[eid] == before[eid], eid


@pytest.mark.parametrize(
    ("stmt", "gone"),
    [
        ("MATCH ()-[r:links]-() WHERE r.n > 4 DELETE r", "E3"),
        ("MATCH ()-[r:links]-() WHERE r.n < 1 DELETE r", "E2"),
        ("MATCH ()-[r:links]-() WHERE r.n >= 2 AND r.n <= 2 DELETE r", "E1"),
        ("MATCH (a)-[r:links]->(b) WHERE r.n <= 0 DELETE r", "E2"),
    ],
)
def test_relationship_range_delete_one_match(memnet_temp, stmt, gone):
    ss = _rel_session()
    n_nodes = len(ss.store.list_records("PRT"))
    before = _edges(ss)
    _mutate(ss, stmt)
    after = _edges(ss)
    assert len(ss.store.list_records("PRT")) == n_nodes
    assert set(after) == set(before) - {gone}
    for eid in after:
        assert after[eid] == before[eid]


@pytest.mark.parametrize(
    ("where", "code"),
    [
        ("r.n > 1", "cue_conflict"),
        ("r.n >= 0", "cue_conflict"),
        ("r.n > 9", "not_found"),
        ("r.n < -1", "not_found"),
        ("r.n > 'a'", "where_type_mismatch"),
    ],
)
def test_relationship_range_delete_cardinality(memnet_temp, where, code):
    ss = _rel_session()
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        _mutate(ss, f"MATCH ()-[r:links]-() WHERE {where} DELETE r")
    assert ei.value.code == code, ei.value.message
    assert _state(ss) == before


@pytest.mark.parametrize(
    "stmt",
    [
        "MATCH (a)-[r:links]->(b) WHERE a.role > 1 DELETE r",
        "MATCH (a)-[r:links]->(b) WHERE b.role < 1 DELETE r",
        "MATCH (a)-[r:links]->(b) WHERE r.n > 4 AND a.role > 1 DELETE r",
        "MATCH ()-[r:links]-() WHERE r.n > r.kind DELETE r",
        "MATCH ()-[r:links]-() WHERE r.n > $p SET r.kind = 'b'",
        "MATCH ()-[r:links]-() WHERE 1 < r.n SET r.kind = 'b'",
    ],
)
def test_relationship_range_refused_unsupported(memnet_temp, stmt):
    ss = _rel_session()
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        _mutate(ss, stmt)
    assert ei.value.code == "unsupported_predicate", ei.value.message
    assert "DELETE" not in ei.value.message.upper() or "DELETE" in stmt
    assert _state(ss) == before


# ----- CLI mutate (run_argv) -----


def test_run_argv_mutate_range_where(memnet_temp):
    ss = _session(1, 5, 10)
    out = run_argv(
        ["mutate", "--stdin", "--session", ss.session_id],
        stdin="MATCH (n:T) WHERE n.x > 6 SET n.y = 'hit'\n",
    )
    assert out["exit_code"] == 0, out["stderr"]
    assert "ok=1 fail=0" in out["stderr"]
    assert _hits(ss) == ["N2"]
    refused = run_argv(
        ["mutate", "--stdin", "--session", ss.session_id],
        stdin="MATCH (n:T) WHERE n.x > n.y SET n.y = 'hit'\n",
    )
    assert refused["exit_code"] != 0
    assert "@ERR: unsupported_predicate|WHERE > operand is not honoured" in refused["stderr"]
    assert _hits(ss) == ["N2"]
