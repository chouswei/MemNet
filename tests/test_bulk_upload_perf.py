"""Bulk-upload hot paths: the accepted-shape cache in gql and match_nodes."""

from __future__ import annotations

import pytest

import memnet.gql as gql
from memnet.gql import ParseError, parse
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_MAP = ["SCHEMA PRT ; fields=id name role", "SCHEMA REQ ; fields=id name"]


@pytest.fixture(autouse=True)
def _fresh_cache():
    gql._ACCEPTED_SHAPES.clear()
    yield
    gql._ACCEPTED_SHAPES.clear()


def _count_graphglot(monkeypatch) -> list[str]:
    calls: list[str] = []
    real = gql.parse_program

    def counting(text):
        calls.append(text)
        return real(text)

    monkeypatch.setattr(gql, "parse_program", counting)
    return calls


def test_same_shape_different_literals_parses_graphglot_once(monkeypatch):
    calls = _count_graphglot(monkeypatch)
    for i in range(5):
        doc = parse(f"CREATE (:PRT {{id: 'p{i}', name: 'part {i}'}})")
        assert len(doc.items) == 1
    assert len(calls) == 1


def test_different_shape_is_parsed_again(monkeypatch):
    calls = _count_graphglot(monkeypatch)
    parse("CREATE (:PRT {id: 'a'})")
    parse("CREATE (:PRT {id: 'a', name: 'b'})")
    assert len(calls) == 2


def test_unusual_literals_are_never_cached(monkeypatch):
    calls = _count_graphglot(monkeypatch)
    for _ in range(2):
        parse('CREATE (:PRT {id: "dq"})')
        parse("CREATE (:PRT {id: 'it\\'s'})")
    assert len(calls) == 4
    assert not gql._ACCEPTED_SHAPES


def test_rejected_statement_is_not_cached_and_keeps_failing():
    bad = "MATCH (a:PRT {id: 'x'}) RETURN a"
    for _ in range(3):
        with pytest.raises(ParseError):
            parse(bad)
    assert not gql._ACCEPTED_SHAPES


def test_cache_does_not_let_a_forbidden_clause_through():
    parse("CREATE (:PRT {id: 'ok'})")
    with pytest.raises(ParseError):
        parse("CREATE (:PRT {id: 'ok'}) WITH 1 AS x RETURN x")


def test_cache_is_bounded():
    for i in range(gql._ACCEPTED_SHAPES_MAX + 5):
        gql._accept_parse(f"MATCH (a {{id: 'a'}}), (b {{id: 'b'}}) CREATE (a)-[:r{i}]->(b)", 1)
    assert len(gql._ACCEPTED_SHAPES) <= gql._ACCEPTED_SHAPES_MAX


def _store():
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        [
            "CREATE (:PRT {id: 'a', name: 'n1', role: 'x'})",
            "CREATE (:PRT {id: 'b', name: 'n1', role: 'y'})",
            "CREATE (:REQ {id: 'c', name: 'n1'})",
        ],
        mode="mutate",
        allow_new_relation=True,
    )
    MutateGate(ss).apply(
        ["MATCH (a {id: 'a'}), (b {id: 'b'}) CREATE (a)-[:links]->(b)"],
        mode="mutate",
        allow_new_relation=True,
    )
    return ss.store


def _ids(recs):
    return sorted(r.fields.get("id", "") for r in recs)


def test_match_nodes_by_props_tag_and_none_value():
    st = _store()
    assert _ids(st.match_nodes(props={"name": "n1"})) == ["a", "b", "c"]
    assert _ids(st.match_nodes(tag="PRT", props={"name": "n1"})) == ["a", "b"]
    assert _ids(st.match_nodes(tag="prt", props={"name": "n1", "role": "y"})) == ["b"]
    assert _ids(st.match_nodes(tag="PRT", props={"name": "n1", "role": None})) == ["a", "b"]
    assert _ids(st.match_nodes(props={"name": "zzz"})) == []
    # a property the node does not have matches only the empty string
    assert _ids(st.match_nodes(tag="REQ", props={"role": ""})) == ["c"]


def test_match_nodes_never_returns_edges():
    st = _store()
    assert all(r.tag != "EDG" for r in st.match_nodes())
    assert st.list_records("EDG")


def test_bulk_batch_wires_edges_to_the_right_nodes():
    ss = open_session(map_lines=_MAP)
    n = 300
    lines = [f"CREATE (:PRT {{id: 'p{i}', name: 'part{i}'}})" for i in range(n)]
    lines += [
        f"MATCH (a {{id: 'p{i // 2}'}}), (b {{id: 'p{i}'}}) CREATE (a)-[:contains]->(b)"
        for i in range(1, n)
    ]
    MutateGate(ss).apply(lines, mode="mutate", allow_new_relation=True)
    by_id = {r.fields["id"]: r.hid for r in ss.store.list_records("PRT")}
    got = {(e.fields["src"], e.fields["dist"]) for e in ss.store.list_records("EDG")}
    assert got == {(by_id[f"p{i // 2}"], by_id[f"p{i}"]) for i in range(1, n)}
