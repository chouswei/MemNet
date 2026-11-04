"""MN-REQ-14.1 rule (5): range WHERE type refusal ``where_type_mismatch``.

Red-first for symphony restart-restore (node P-type). Contract: /tmp/srs/score.md
§1.6 (D-T1..D-T7).

- Parse (data-independent): a quoted range operand whose text fully reads as a
  number ('123', '000123', '-2.5', '1e3') is refused
  ``@ERR: where_type_mismatch|WHERE > on n.rowRev: quoted number '123'; use a number literal``.
  A range on ``n.id`` stays ``unsupported_predicate``. '' and ' 5' stay plain strings.
- Evaluation: a quoted non-numeric string against a stored value that reads as a
  number (non-finite included) is refused ``@ERR: where_type_mismatch|WHERE < on
  n.x: stored number vs quoted string; use a number literal``, whatever the AND / OR
  sibling order.
- Kept as no match, no error: a missing or empty field, a number literal against
  'abc' / '-' / 'NaN' / ' 5', a non-finite field against a number literal.
- Equality is unchanged: exact text ('000124' = 124 does not match).
- Surfaces: node and relationship WHERE, SET and DELETE, inline WHERE, and
  ``query typed-walk --where``; nothing is written on refusal.
"""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.in_process_engine import run_argv
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_MAP = ["SCHEMA T ; fields=id name x y rowRev"]
_REL_MAP = ["SCHEMA PRT ; fields=id name role"]
_WALK_MAP = ["SCHEMA ASK ; fields=id title", "SCHEMA ROW ; fields=id toBot rowRev x k"]

_MISSING = object()
_CODE = "where_type_mismatch"
_VERBS = ["SET n.y = 'hit'", "DELETE n"]


def _gql_str(val: str) -> str:
    return "'" + val.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _session(*values, key: str = "x"):
    """Nodes N0..Nk of label T; *key* is each value (quoted), _MISSING omits it."""
    ss = open_session(map_lines=_MAP)
    stmts = []
    for i, v in enumerate(values):
        extra = "" if v is _MISSING else f", {key}: {_gql_str(v)}"
        stmts.append(f"CREATE (:T {{id: 'N{i}', name: 'n{i}'{extra}}})")
    MutateGate(ss).apply(stmts, mode="add")
    return ss


def _nodes(ss) -> dict[str, dict[str, str]]:
    return {r.fields["id"]: dict(r.fields) for r in ss.store.list_records("T")}


def _mutate(ss, stmt: str):
    return MutateGate(ss).apply([stmt], mode="mutate")


def _refused(ss, stmt: str, code: str = _CODE) -> MemNetError:
    before = _nodes(ss)
    with pytest.raises(MemNetError) as ei:
        _mutate(ss, stmt)
    assert ei.value.code == code, (stmt, ei.value.code, ei.value.message)
    assert _nodes(ss) == before, f"{stmt!r} wrote despite {code}"
    return ei.value


def _cli_mutate(ss, stmt: str) -> dict:
    return run_argv(["mutate", "--stdin", "--session", ss.session_id], stdin=stmt + "\n")


# ----- parse time: a quoted number is refused, whatever the data ------------------------

_QUOTED_NUMBERS = ["123", "000123", "-2.5", "1e3", "0", "-7", "2.50", "1E-3"]


@pytest.mark.parametrize("lit", _QUOTED_NUMBERS)
@pytest.mark.parametrize("op", [">", "<", ">=", "<="])
@pytest.mark.parametrize("verb", _VERBS)
def test_quoted_number_operand_refused(memnet_temp, lit, op, verb):
    ss = _session("5", "abc")
    err = _refused(ss, f"MATCH (n:T) WHERE n.x {op} '{lit}' {verb}")
    assert err.message == f"WHERE {op} on n.x: quoted number '{lit}'; use a number literal"


@pytest.mark.parametrize(
    "values",
    [("abc", "xyz"), (_MISSING, _MISSING), ("",), ()],
    ids=["non-numeric", "missing", "empty", "no-nodes"],
)
@pytest.mark.parametrize("verb", _VERBS)
def test_quoted_number_refused_without_numeric_data(memnet_temp, values, verb):
    # data-independent: refused at parse time, not not_found
    ss = _session(*values)
    err = _refused(ss, f"MATCH (n:T) WHERE n.x > '123' {verb}")
    assert err.message == "WHERE > on n.x: quoted number '123'; use a number literal"


@pytest.mark.parametrize(
    "where",
    [
        "NOT n.x > '123'",
        "n.name = 'n0' AND n.x > '123'",
        "n.x > '123' AND n.name = 'n0'",
        "n.name = 'n0' OR n.x > '123'",
        "n.x > '123' OR n.name = 'n0'",
        "(n.name = 'zzz' AND n.x >= '1e3') OR n.name = 'n0'",
    ],
)
@pytest.mark.parametrize("verb", _VERBS)
def test_quoted_number_refused_nested(memnet_temp, where, verb):
    ss = _session("5", "abc")
    _refused(ss, f"MATCH (n:T) WHERE {where} {verb}")


@pytest.mark.parametrize("verb", _VERBS)
def test_quoted_number_refused_inline_where(memnet_temp, verb):
    ss = _session("5", "abc")
    err = _refused(ss, f"MATCH (n:T WHERE n.x <= '-2.5') {verb}")
    assert err.message == "WHERE <= on n.x: quoted number '-2.5'; use a number literal"


def test_quoted_number_cli_exact_line(memnet_temp):
    ss = _session("000124", "000123", key="rowRev")
    before = _nodes(ss)
    out = _cli_mutate(ss, "MATCH (n:T) WHERE n.rowRev > '123' SET n.y = 'hit'")
    assert out["exit_code"] == 1, out
    assert (
        "@ERR: where_type_mismatch|WHERE > on n.rowRev: quoted number '123'; use a number literal"
        in out["stderr"]
    ), out["stderr"]
    assert _nodes(ss) == before


@pytest.mark.parametrize("where", ["n.id > '5'", "n.id < '000123'", "n.id >= 'N1'"])
def test_range_on_id_stays_unsupported_predicate(memnet_temp, where):
    ss = _session("5", "abc")
    _refused(ss, f"MATCH (n:T) WHERE {where} SET n.y = 'hit'", "unsupported_predicate")


def test_empty_and_space_operands_stay_strings(memnet_temp):
    # '' and ' 5' do not read as numbers: compared as text against 'abc'
    ss = _session("abc")
    _mutate(ss, "MATCH (n:T) WHERE n.x > ' 5' SET n.y = 'hit'")
    assert _nodes(ss)["N0"]["y"] == "hit"
    ss = _session("abc")
    _mutate(ss, "MATCH (n:T) WHERE n.x > '' SET n.y = 'hit'")
    assert _nodes(ss)["N0"]["y"] == "hit"


# ----- evaluation: a quoted string against a stored number is refused --------------------

_STORED_NUMBERS = ["5", "000124", "-2.5", "1e3", "1e999", "-1e999", "0"]


@pytest.mark.parametrize("stored", _STORED_NUMBERS)
@pytest.mark.parametrize("op", [">", "<", ">=", "<="])
@pytest.mark.parametrize("verb", _VERBS)
def test_quoted_string_vs_stored_number_refused(memnet_temp, stored, op, verb):
    ss = _session(stored)
    err = _refused(ss, f"MATCH (n:T) WHERE n.x {op} 'a' {verb}")
    assert err.message == f"WHERE {op} on n.x: stored number vs quoted string; use a number literal"


@pytest.mark.parametrize(
    "values",
    [("abc", "5"), ("5", "abc"), (_MISSING, "7", "zzz")],
    ids=["word-first", "number-first", "missing-number-word"],
)
@pytest.mark.parametrize("verb", _VERBS)
def test_one_numeric_row_refuses_whole_statement(memnet_temp, values, verb):
    ss = _session(*values)
    _refused(ss, f"MATCH (n:T) WHERE n.x > 'a' {verb}")


@pytest.mark.parametrize(
    "where",
    [
        "NOT n.x < 'a'",
        # a FALSE sibling first must not hide the mismatch
        "n.name = 'zzz' AND n.x < 'a'",
        "n.x < 'a' AND n.name = 'zzz'",
        # a TRUE sibling first must not hide the mismatch
        "n.name = 'n0' OR n.x < 'a'",
        "n.x < 'a' OR n.name = 'n0'",
        "NOT (n.name = 'n0' OR n.x < 'a')",
        "(n.name = 'zzz' AND n.x < 'a') OR n.name = 'n0'",
        "n.name = 'n0' OR (n.name = 'zzz' AND n.x < 'a')",
    ],
)
@pytest.mark.parametrize("verb", _VERBS)
def test_mismatch_refused_whatever_sibling_order(memnet_temp, where, verb):
    ss = _session("5")
    err = _refused(ss, f"MATCH (n:T) WHERE {where} {verb}")
    assert err.message == "WHERE < on n.x: stored number vs quoted string; use a number literal"


@pytest.mark.parametrize("verb", _VERBS)
def test_mismatch_refused_inline_where(memnet_temp, verb):
    ss = _session("5", "abc")
    _refused(ss, f"MATCH (n:T WHERE n.x >= 'a') {verb}")


def test_mismatch_cli_exact_line(memnet_temp):
    ss = _session("5", "abc")
    before = _nodes(ss)
    out = _cli_mutate(ss, "MATCH (n:T) WHERE n.x < 'a' SET n.y = 'hit'")
    assert out["exit_code"] == 1, out
    assert (
        "@ERR: where_type_mismatch|WHERE < on n.x: stored number vs quoted string; "
        "use a number literal" in out["stderr"]
    ), out["stderr"]
    assert _nodes(ss) == before


# ----- kept as no match, no error ------------------------------------------------------------


@pytest.mark.parametrize(
    ("values", "where"),
    [
        pytest.param((_MISSING, ""), "n.x < 'a'", id="missing-empty-vs-string"),
        pytest.param((_MISSING, ""), "n.x > 1", id="missing-empty-vs-number"),
        pytest.param(("abc",), "n.x > 1", id="number-vs-word"),
        pytest.param(("-",), "n.x < 1000000", id="number-vs-dash"),
        pytest.param(("NaN",), "n.x > -1000000", id="number-vs-NaN"),
        pytest.param((" 5",), "n.x >= 0", id="number-vs-space-5"),
        pytest.param(("1e999",), "n.x > 0", id="non-finite-vs-number"),
        pytest.param(("-1e999",), "n.x < 0", id="neg-non-finite-vs-number"),
        pytest.param(("abc", "-"), "n.x < '-'", id="string-vs-words"),
    ],
)
@pytest.mark.parametrize("verb", _VERBS)
def test_kept_unknown_is_not_found(memnet_temp, values, where, verb):
    ss = _session(*values)
    _refused(ss, f"MATCH (n:T) WHERE {where} {verb}", "not_found")


def test_number_literal_skips_placeholders(memnet_temp):
    # a placeholder in a numeric column must not block a numeric range over good rows
    ss = _session("-", "7", "n/a", "3")
    _mutate(ss, "MATCH (n:T) WHERE n.x > 5 SET n.y = 'hit'")
    assert sorted(i for i, f in _nodes(ss).items() if f.get("y") == "hit") == ["N1"]


# ----- equality unchanged ---------------------------------------------------------------------


def test_equality_is_exact_text(memnet_temp):
    ss = _session("000124", key="rowRev")
    _refused(ss, "MATCH (n:T) WHERE n.rowRev = 124 SET n.y = 'hit'", "not_found")
    _mutate(ss, "MATCH (n:T) WHERE n.rowRev = '000124' SET n.y = 'hit'")
    assert _nodes(ss)["N0"]["y"] == "hit"
    ss = _session("000124", key="rowRev")
    _mutate(ss, "MATCH (n:T) WHERE n.rowRev <> '124' SET n.y = 'hit'")
    assert _nodes(ss)["N0"]["y"] == "hit"


# ----- relationship WHERE ----------------------------------------------------------------------


def _rel_session(*ns: str):
    """P0..Pk; edge E<i> P0->P<i+1> :links with n = ns[i] (quoted)."""
    ss = open_session(map_lines=_REL_MAP)
    gate = MutateGate(ss)
    gate.apply(
        [f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: 'r'}})" for i in range(len(ns) + 1)],
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


def _state(ss):
    nodes = sorted((r.hid, tuple(sorted(r.fields.items()))) for r in ss.store.list_records("PRT"))
    edges = sorted((e.hid, tuple(sorted(e.fields.items()))) for e in ss.store.list_records("EDG"))
    return nodes, edges


def _rel_refused(ss, stmt: str, code: str = _CODE) -> MemNetError:
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        _mutate(ss, stmt)
    assert ei.value.code == code, (stmt, ei.value.code, ei.value.message)
    assert _state(ss) == before, f"{stmt!r} wrote despite {code}"
    return ei.value


@pytest.mark.parametrize("verb", ["SET r.kind = 'b'", "DELETE r"])
def test_relationship_quoted_number_refused(memnet_temp, verb):
    ss = _rel_session("2", "7")
    err = _rel_refused(ss, f"MATCH ()-[r:links]-() WHERE r.n > '5' {verb}")
    assert err.message == "WHERE > on r.n: quoted number '5'; use a number literal"


@pytest.mark.parametrize("verb", ["SET r.kind = 'b'", "DELETE r"])
@pytest.mark.parametrize(
    "where", ["r.n > 'a'", "r.kind = 'zzz' AND r.n > 'a'", "r.kind = 'a' OR r.n > 'a'"]
)
def test_relationship_mismatch_refused(memnet_temp, where, verb):
    ss = _rel_session("2", "7")
    err = _rel_refused(ss, f"MATCH ()-[r:links]-() WHERE {where} {verb}")
    assert err.message == "WHERE > on r.n: stored number vs quoted string; use a number literal"


# ----- query typed-walk --where ----------------------------------------------------------------


@pytest.fixture
def board(memnet_temp):
    ss = open_session(map_lines=list(_WALK_MAP))
    gate = MutateGate(ss)
    gate.apply(["CREATE (:ASK {id: 'A1', title: 'claim'})"], mode="mutate")
    rows = [
        {"id": "R1", "toBot": "x", "rowRev": "000124", "x": "7", "k": "a"},
        {"id": "R2", "toBot": "x", "rowRev": "000123", "x": "abc", "k": "b"},
    ]
    for i, fields in enumerate(rows):
        props = ", ".join(f"{k}: {_gql_str(v)}" for k, v in fields.items())
        gate.apply([f"CREATE (:ROW {{{props}}})"], mode="mutate")
        gate.apply(
            [
                f"MATCH (a:ROW {{{props}}}), (b {{id: 'A1'}}) "
                f"CREATE (a)-[:PART_OF {{id: 'E{i}'}}]->(b)"
            ],
            mode="mutate",
            allow_new_relation=True,
        )
    return ss


def _walk_refused(ss, where: str, line: str) -> None:
    out = run_argv(
        [
            "query",
            "typed-walk",
            "--from",
            "A1",
            "--type",
            "PART_OF",
            "--dir",
            "in",
            "--where",
            where,
            "--session",
            ss.session_id,
        ]
    )
    assert out["exit_code"] == 1, (where, out)
    assert line in out["stderr"], (where, out["stderr"])
    assert "@PATH" not in out["stdout"]
    from memnet.typed_walk import typed_walk

    with pytest.raises(MemNetError) as ei:
        typed_walk(ss.store, start="A1", relation="PART_OF", direction="in", where=where)
    assert ei.value.code == _CODE, (where, ei.value.code, ei.value.message)


@pytest.mark.parametrize(
    "where", ["n.rowRev > '123'", "n.toBot = 'x' AND n.rowRev > '123'", "NOT n.rowRev > '123'"]
)
def test_typed_walk_quoted_number_refused(board, where):
    _walk_refused(
        board,
        where,
        "@ERR: where_type_mismatch|WHERE > on n.rowRev: quoted number '123'; use a number literal",
    )


@pytest.mark.parametrize(
    "where", ["n.x < 'a'", "n.k = 'zzz' AND n.x < 'a'", "n.k = 'a' OR n.x < 'a'"]
)
def test_typed_walk_mismatch_refused(board, where):
    _walk_refused(
        board,
        where,
        "@ERR: where_type_mismatch|WHERE < on n.x: stored number vs quoted string; "
        "use a number literal",
    )
