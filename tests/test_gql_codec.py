"""GqlCodec unit tests — gated openCypher-shaped mutate + shaped emit."""

from __future__ import annotations

import pytest

from memnet.gql import ParseError, emit_item, parse, soft_validate
from memnet.gql_codec import GqlCodec
from memnet.tier_a import EdgeRec, NodeRec, Op


def test_parse_create_omits_leftover_new():
    doc = parse("CREATE (:PLR {id: 'NEW', identity: 'Hero', wealth: 1})")
    assert len(doc.items) == 1
    n = doc.items[0]
    assert isinstance(n, NodeRec)
    assert n.op == Op.CREATE
    assert n.kind == "PLR"
    assert n.id == ""
    assert {f.key: f.value for f in n.fields}["identity"] == "Hero"


def test_parse_match_create_rel():
    text = (
        "MATCH (a:CST {id: 'CST_Vin'}), (b:CST {id: 'CST_Rin'})\n"
        "CREATE (a)-[:bind {id: 'E_vin', fromPort: 'p', toPort: 'a', carries: 'I'}]->(b)"
    )
    doc = parse(text)
    assert len(doc.items) == 1
    e = doc.items[0]
    assert isinstance(e, EdgeRec)
    assert e.op == Op.CREATE
    assert e.frm == "CST_Vin"
    assert e.to == "CST_Rin"
    assert e.rel == "bind"
    assert e.edge_id == "E_vin"
    keys = {f.key: f.value for f in e.fields}
    assert keys["fromPort"] == "p"
    assert keys["toPort"] == "a"
    assert not soft_validate(doc)


def test_soft_validate_bind_requires_ports():
    doc = parse("MATCH (a {id: 'A'}), (b {id: 'B'})\nCREATE (a)-[:bind {id: 'E1'}]->(b)")
    errs = [i for i in soft_validate(doc) if i.severity == "error"]
    assert any(i.code == "bind_ports_required" for i in errs)


def test_soft_validate_mixed_grain():
    doc = parse(
        "MATCH (a {id: 'A'}), (b {id: 'B'})\nCREATE (a)-[:about {id: 'E1', fromPort: 'x'}]->(b)"
    )
    errs = [i for i in soft_validate(doc) if i.severity == "error"]
    assert any(i.code == "mixed_grain" for i in errs)


def test_parse_set_and_delete():
    doc = parse("MATCH (n {id: 'PLR01'}) SET n.wealth = 5, n.merge = true")
    assert doc.items[0].op == Op.PATCH
    doc2 = parse("MATCH (n {id: 'PLR01'}) DETACH DELETE n")
    assert doc2.items[0].op == Op.DROP


def test_parse_merge():
    doc = parse("MERGE (n:PLR {id: 'PLR01'}) SET n += {wealth: 2}")
    n = doc.items[0]
    assert n.op == Op.PATCH
    assert n.id == "PLR01"
    assert n.raw.upper().startswith("MERGE")


def test_shaped_present_emit_roundtrip_props():
    codec = GqlCodec()
    doc = codec.parse("CREATE (:TSK {id: 'T1', goal: 'x', status: 'in_progress'})")
    line = emit_item(doc.items[0], as_mutate=False)
    assert line.startswith("(:TSK")
    assert "id: 'T1'" in line


def test_reject_bad_create():
    with pytest.raises(ParseError):
        parse("CREATE something weird")
