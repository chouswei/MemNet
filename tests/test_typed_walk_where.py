"""MN-REQ-14.3 + 14.1 / issue #247 item 2: far-node WHERE on a typed walk.

Red-first for symphony typed-walks (node P-walk). Contract: /tmp/s247/score.md
D5. ``--where`` (engine ``where=``) is a predicate on ``n``, the row's end node,
parsed by ``gql.parse_where_clause`` and evaluated by ``gql.eval_where`` with the
#250 rules: three-valued, UNKNOWN is no match, NOT over UNKNOWN stays UNKNOWN, a
missing / empty / mixed-type / non-finite field is UNKNOWN. A range on ``n.id`` is
refused ``unsupported_predicate`` (bare or nested); equality on ``n.id`` works. Any
variable other than ``n`` is refused. WHERE filters rows, not traversal.

rowRev note (L-247-1, 14.1 rule 5): '000124' fully reads as a number, so
``n.rowRev > 123`` compares numerically and ``n.rowRev > '000123'`` is a mixed pair
(UNKNOWN, no rows).

New names are looked up inside test bodies so collection never fails on 4b8ed16.
"""

from __future__ import annotations

import importlib

import pytest

from memnet.exceptions import MemNetError
from memnet.in_process_engine import run_argv
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_MAP = [
    "SCHEMA ASK ; fields=id title",
    "SCHEMA ROW ; fields=id toBot rowRev x k",
]


def _tw():
    try:
        return importlib.import_module("memnet.typed_walk")
    except ModuleNotFoundError as exc:  # red on 4b8ed16: the feature is missing
        pytest.fail(f"missing feature: memnet.typed_walk ({exc})")


def _gql_str(val: str) -> str:
    return "'" + val.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _apply(ss, *stmts):
    return MutateGate(ss).apply(list(stmts), mode="mutate", allow_new_relation=True)


def _board(*rows: dict[str, str]):
    """ASK A1; each row dict is a ROW node with a PART_OF edge to A1, in order."""
    ss = open_session(map_lines=list(_MAP))
    _apply(ss, "CREATE (:ASK {id: 'A1', title: 'claim'})")
    for i, fields in enumerate(rows):
        props = ", ".join(f"{k}: {_gql_str(v)}" for k, v in fields.items())
        _apply(ss, f"CREATE (:ROW {{{props}}})")
        _apply(
            ss,
            f"MATCH (a:ROW {{{props}}}), (b {{id: 'A1'}}) "
            f"CREATE (a)-[:PART_OF {{id: 'E{i}'}}]->(b)",
        )
    return ss


def _walk(ss, where: str, *extra: str) -> dict:
    return run_argv(
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
            *extra,
            "--session",
            ss.session_id,
        ]
    )


def _ids(ss, where: str, *extra: str) -> list[str]:
    """End-node ids (CLI) and the same rows from the engine."""
    out = _walk(ss, where, *extra)
    assert "No such command" not in out["stderr"], "missing feature: query typed-walk"
    assert out["exit_code"] == 0, out["stderr"]
    got = []
    for ln in out["stdout"].splitlines():
        if ln.startswith("@PATH: "):
            end = ln[ln.rfind("(") :]
            got.append(end.split("id: '", 1)[1].split("'", 1)[0] if "id: '" in end else "")
    tw = _tw()
    res = tw.typed_walk(ss.store, start="A1", relation="PART_OF", direction="in", where=where)
    assert [p.end.fields.get("id", "") for p in res.paths] == got, where
    return got


def _refused(ss, where: str, code: str = "unsupported_predicate") -> str:
    out = _walk(ss, where)
    assert "No such command" not in out["stderr"], "missing feature: query typed-walk"
    assert out["exit_code"] != 0, (where, out)
    assert f"@ERR: {code}|" in out["stderr"], (where, out["stderr"])
    assert "@ERR: internal" not in out["stderr"]
    assert "@PATH" not in out["stdout"]
    tw = _tw()
    with pytest.raises(MemNetError) as ei:
        tw.typed_walk(ss.store, start="A1", relation="PART_OF", direction="in", where=where)
    assert ei.value.code == code, (where, ei.value.code, ei.value.message)
    return out["stderr"]


@pytest.fixture
def rows(memnet_temp):
    return _board(
        {"id": "R1", "toBot": "x", "rowRev": "000124", "x": "7", "k": "a"},
        {"id": "R2", "toBot": "x", "rowRev": "000123", "x": "3", "k": "b"},
        {"id": "R3", "toBot": "y", "rowRev": "000200", "x": "10", "k": "a"},
        {"id": "R4", "toBot": "x", "k": "c"},
    )


# ----- operators ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("where", "want"),
    [
        ("n.toBot = 'x'", ["R1", "R2", "R4"]),
        ("n.toBot <> 'x'", ["R3"]),
        ("n.toBot STARTS WITH 'y'", ["R3"]),
        ("n.x > 5", ["R1", "R3"]),
        ("n.x >= 7", ["R1", "R3"]),
        ("n.x < 5", ["R2"]),
        ("n.x <= 3", ["R2"]),
        ("n.x > 9", ["R3"]),  # numeric, not lexical
        ("n.toBot = 'x' AND n.x > 5", ["R1"]),
        ("n.k = 'c' OR n.x < 5", ["R2", "R4"]),
        ("NOT n.toBot = 'x'", ["R3"]),
        ("NOT (n.k = 'a' OR n.k = 'b')", ["R4"]),
        ("(n.k = 'a' OR n.k = 'c') AND n.toBot = 'x'", ["R1", "R4"]),
        ("TRUE", ["R1", "R2", "R3", "R4"]),
        ("FALSE", []),
        ("n.id = 'R2'", ["R2"]),
        ("n.id = 'R2' OR n.id = 'R4'", ["R2", "R4"]),
        ("n.id <> 'R1' AND n.k = 'a'", ["R3"]),
    ],
)
def test_where_operators(rows, where, want):
    assert _ids(rows, where) == want


def test_leading_where_keyword_is_stripped(rows):
    assert _ids(rows, "WHERE n.k = 'a'") == _ids(rows, "n.k = 'a'") == ["R1", "R3"]


# ----- three-valued -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("where", "want"),
    [
        # R4 has no x: UNKNOWN on every range, and NOT keeps it UNKNOWN
        ("n.x > 0", ["R1", "R2", "R3"]),
        ("NOT n.x > 5", ["R2"]),
        ("NOT n.x < 5", ["R1", "R3"]),
        # UNKNOWN OR TRUE is TRUE; UNKNOWN AND TRUE is UNKNOWN
        ("n.x > 5 OR n.k = 'c'", ["R1", "R3", "R4"]),
        ("n.x > 5 AND n.k = 'c'", []),
        ("NOT (n.x > 5 AND n.k = 'c')", ["R1", "R2", "R3"]),
        # UNKNOWN OR FALSE stays UNKNOWN
        ("n.x > 100 OR n.k = 'zzz'", []),
        # mixed pair: string literal vs a numeric field is UNKNOWN
        ("n.x > 'a'", []),
        ("NOT n.x > 'a'", []),
    ],
)
def test_three_valued(rows, where, want):
    assert _ids(rows, where) == want


_NON_FINITE = ("1e999", "-1e999", "NaN", "nan")


@pytest.fixture(params=_NON_FINITE)
def odd(request, memnet_temp):
    return _board(
        {"id": "Q0", "x": request.param, "k": "a"},
        {"id": "Q1", "x": "3", "k": "b"},
        {"id": "Q2", "x": "9", "k": "a"},
    )


@pytest.mark.parametrize(
    ("where", "want"),
    [
        ("n.x > 5", ["Q2"]),
        ("n.x < 5", ["Q1"]),
        ("n.x >= -1000000", ["Q1", "Q2"]),
        ("NOT n.x > 5", ["Q1"]),
        ("NOT n.x < 5", ["Q2"]),
        ("NOT (n.x < 5 OR n.k = 'zzz')", ["Q2"]),
        ("n.x < 5 OR n.k = 'zzz'", ["Q1"]),
        ("n.x > 5 AND n.k = 'a'", ["Q2"]),
    ],
)
def test_non_finite_field_is_unknown(odd, where, want):
    assert _ids(odd, where) == want


@pytest.mark.parametrize(
    ("where", "want"),
    [
        ("n.x > 5 OR n.k = 'a'", ["Q0", "Q2"]),
        ("n.k = 'a' OR n.x > 5", ["Q0", "Q2"]),
        ("n.x < 5 OR n.k = 'a'", ["Q0", "Q1", "Q2"]),
        ("NOT n.x > 5 OR n.k = 'a'", ["Q0", "Q1", "Q2"]),
        ("(n.x > 5 OR n.x <= 5) OR n.id = 'Q0'", ["Q0", "Q1", "Q2"]),
    ],
)
def test_non_finite_matches_through_true_or_sibling(odd, where, want):
    assert _ids(odd, where) == want


def test_non_finite_and_true_sibling_does_not_match(odd):
    assert _ids(odd, "n.x > -1000000 AND n.k = 'a'") == ["Q2"]
    assert _ids(odd, "n.k = 'a' AND NOT n.x > 5") == []


# ----- refusals -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "where",
    [
        "n.id > 'R1'",
        "n.id <= 'R9'",
        "n.id >= 1",
        "NOT n.id < 'R2'",
        "n.k = 'a' OR n.id > 'R1'",
        "n.k = 'a' AND n.id < 'R3'",
        "NOT (n.k = 'zzz' OR n.id > 'R0')",
    ],
)
def test_range_on_id_refused(rows, where):
    _refused(rows, where)


@pytest.mark.parametrize(
    ("where", "name"),
    [
        ("m.k = 'a'", "m.k"),
        ("r.k = 'a'", "r.k"),
        ("n.k = 'a' AND a.title = 'claim'", "a.title"),
        ("NOT b.x > 1", "b.x"),
    ],
)
def test_other_variable_refused(rows, where, name):
    err = _refused(rows, where)
    assert f"@ERR: unsupported_predicate|WHERE {name}: walk WHERE names n only" in err


@pytest.mark.parametrize("where", ["n.x >", "n.x > n.k", "n.x > $p", "n.k = "])
def test_bad_where_refused_not_internal(rows, where):
    out = _walk(rows, where)
    assert "No such command" not in out["stderr"], "missing feature: query typed-walk"
    assert out["exit_code"] != 0
    assert "@ERR: " in out["stderr"]
    assert "@ERR: internal" not in out["stderr"]
    tw = _tw()
    with pytest.raises(MemNetError):
        tw.typed_walk(rows.store, start="A1", relation="PART_OF", direction="in", where=where)


# ----- WHERE filters rows, not traversal ------------------------------------------------


def test_where_filters_rows_not_traversal(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _apply(
        ss,
        "CREATE (:ROW {id: 'c0', k: 'a'})",
        "CREATE (:ROW {id: 'c1', k: 'skip'})",
        "CREATE (:ROW {id: 'c2', k: 'a'})",
    )
    for a, b in (("c0", "c1"), ("c1", "c2")):
        _apply(ss, f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) CREATE (a)-[:REPLACES]->(b)")
    out = run_argv(
        [
            "query",
            "typed-walk",
            "--from",
            "c0",
            "--type",
            "REPLACES",
            "--max-hops",
            "5",
            "--where",
            "n.k = 'a'",
            "--session",
            ss.session_id,
        ]
    )
    assert out["exit_code"] == 0, out["stderr"]
    paths = [ln for ln in out["stdout"].splitlines() if ln.startswith("@PATH: ")]
    assert len(paths) == 1
    assert paths[0].startswith("@PATH: 1|2|")
    assert "'c1'" in paths[0] and paths[0].rstrip(")").count("'c2'") == 1


def test_limit_counts_matching_rows(rows):
    tw = _tw()
    res = tw.typed_walk(
        rows.store, start="A1", relation="PART_OF", direction="in", where="n.toBot = 'x'", limit=3
    )
    assert [p.end.fields["id"] for p in res.paths] == ["R1", "R2", "R4"]
    assert res.truncated is None
    res = tw.typed_walk(
        rows.store, start="A1", relation="PART_OF", direction="in", where="n.toBot = 'x'", limit=2
    )
    assert [p.end.fields["id"] for p in res.paths] == ["R1", "R2"]
    assert res.truncated == "limit"


# ----- the issue's main use (rowRev) ----------------------------------------------------


def test_main_use_row_rev_number_operand(rows):
    assert _ids(rows, "n.toBot = 'x' AND n.rowRev > 123") == ["R1"]
    assert _ids(rows, "n.rowRev > 123") == ["R1", "R3"]
    assert _ids(rows, "n.rowRev >= 123 AND n.rowRev < 200") == ["R1", "R2"]


def test_main_use_row_rev_quoted_operand_gives_no_rows(rows):
    # '000124' fully reads as a number: a quoted operand is a mixed pair (UNKNOWN)
    assert _ids(rows, "n.toBot = 'x' AND n.rowRev > '000123'") == []
    assert _ids(rows, "n.rowRev > '000123'") == []
    assert _ids(rows, "n.rowRev = '000124'") == ["R1"]
