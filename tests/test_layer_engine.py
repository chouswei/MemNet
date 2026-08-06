"""Layer engine slice: ingest + emit + MutateGate soft gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from memnet.exceptions import MemNetError
from memnet.layer import (
    emit,
    parse,
    soft_validate,
)
from memnet.mutate_gate import MutateGate, classify_batch
from memnet.pin_map_composer import PinMapComposer
from memnet.session import open_session

ROOT = Path(__file__).resolve().parents[1]
LAYER_EXAMPLES = ROOT / "docs" / "grammar" / "examples" / "layer"

_LAYER_MAP = ["SCHEMA CST ; fields=id name role ports law pseudo recycle R"]


def _open_layer_session():
    return open_session(map_lines=list(_LAYER_MAP))


def _fixture(name: str) -> str:
    return (LAYER_EXAMPLES / name).read_text(encoding="utf-8")


def _body_lines(text: str) -> list[str]:
    return [
        ln.strip()
        for ln in text.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]


@pytest.mark.parametrize(
    "name",
    [
        "layer_01_bind_good.txt",
        "layer_02_relation_good.txt",
        "layer_03_ports_law_alias_good.txt",
        "layer_04_named_fn_A_good.txt",
    ],
)
def test_layer_ingest_emit_roundtrip(memnet_temp, name: str):
    text = _fixture(name)
    lines = _body_lines(text)
    assert classify_batch(lines) == "layer"

    ss = open_session(map_lines=list(_LAYER_MAP))
    gate = MutateGate(ss)
    result = gate.apply(lines, mode="add")
    assert result.dialect == "layer"
    assert result.records

    # Re-emit from store via pin map on first CST
    nodes = [r for r in result.records if r.tag == "CST"]
    assert nodes
    pin = PinMapComposer(ss).compose(anchor=nodes[0].id, depth=2)[1]
    assert "CST [" in pin

    # Codec round-trip on fixture body
    doc = parse("\n".join(lines) + "\n")
    assert not [i for i in soft_validate(doc) if i.severity == "error"]
    emitted = emit(doc)
    doc2 = parse(emitted)
    assert len(doc.items) == len(doc2.items)


def test_layer_01_bind_stores_ports(memnet_temp):
    lines = _body_lines(_fixture("layer_01_bind_good.txt"))
    ss = _open_layer_session()
    result = MutateGate(ss).apply(lines, mode="add")
    edges = [r for r in result.records if r.tag == "EDG"]
    assert edges
    bind = next(e for e in edges if e.id == "E_c")
    assert bind.fields["src"] == "CST_Q1"
    assert bind.fields["src_port"] == "C"
    assert bind.fields["dist"] == "CST_Rc"
    assert bind.fields["dist_port"] == "a"
    assert bind.fields["relation"] == "bind"
    assert bind.fields["carries"] == "I"
    assert bind.fields["wire"] == "directed"

    undirected = next(e for e in edges if e.id == "E_ab")
    assert undirected.fields["wire"] == "non_directed"

    pin = PinMapComposer(ss).compose(anchor="CST_Q1", depth=2)[1]
    assert "[CST_Q1.C] --bind--> [CST_Rc.a]" in pin
    assert "carries=I" in pin
    assert "--(bind)-->" not in pin


def test_layer_02_relation_bare_endpoints(memnet_temp):
    lines = _body_lines(_fixture("layer_02_relation_good.txt"))
    ss = _open_layer_session()
    result = MutateGate(ss).apply(lines, mode="add")
    knows = ss.store.get("E_kb")
    assert knows is not None
    assert knows.fields["src"] == "CST_Alice"
    assert knows.fields["dist"] == "CST_Bob"
    assert knows.fields.get("src_port", "") == ""
    assert knows.fields["relation"] == "knows"
    pin = PinMapComposer(ss).compose(anchor="CST_Alice", depth=2)[1]
    assert "[CST_Alice] --knows--> [CST_Bob]" in pin
    assert "--member_of--" in pin


def test_layer_03_ports_law_on_node(memnet_temp):
    lines = _body_lines(_fixture("layer_03_ports_law_alias_good.txt"))
    ss = _open_layer_session()
    MutateGate(ss).apply(lines, mode="add")
    r = ss.store.get("CST_R")
    assert r is not None
    assert "ports=" not in r.fields["ports"]  # value only
    assert "direc=inout" in r.fields["ports"]
    assert "@va" in r.fields["law"]
    pin = PinMapComposer(ss).compose(anchor="CST_R", depth=1)[1]
    assert "law=" in pin
    assert "ports=" in pin


def test_layer_05_rejects_mixed_endpoints(memnet_temp):
    lines = _body_lines(_fixture("layer_05_bad_mixed_endpoints.txt"))
    ss = _open_layer_session()
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(lines, mode="add")
    assert ei.value.code == "mixed_endpoints"


def test_layer_06_rejects_law_on_edge(memnet_temp):
    lines = _body_lines(_fixture("layer_06_bad_law_on_edge.txt"))
    ss = _open_layer_session()
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(lines, mode="add")
    assert ei.value.code == "law_on_edge"


def test_layer_07_rejects_bag_on_law(memnet_temp):
    lines = _body_lines(_fixture("layer_07_bad_bag_on_law.txt"))
    ss = _open_layer_session()
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(lines, mode="add")
    assert ei.value.code == "bag_denylist"


def test_layer_08_parse_reject_brace_depth(memnet_temp):
    lines = _body_lines(_fixture("layer_08_bad_brace_depth3.txt"))
    ss = _open_layer_session()
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(lines, mode="add")
    assert ei.value.code == "parse_error"


def test_carries_rejected_on_relation(memnet_temp):
    lines = [
        "CST [CST_A] ; role=person",
        "CST [CST_B] ; role=person",
        "E1 [CST_A] --knows--> [CST_B] ; carries=token",
    ]
    ss = _open_layer_session()
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(lines, mode="add")
    assert ei.value.code == "carries_on_relation"


def test_tier_a_unchanged_by_layer_classifier(memnet_temp, schema_file):
    lines = [
        "+ PLR [NEW] ; identity=Hero ; wealth=1 ; cashflow=0 ; monopoly=0 ; "
        "reputation=0 ; inventory=bag",
    ]
    assert classify_batch(lines) == "tier_a"
    ss = open_session(map_file=str(schema_file))
    result = MutateGate(ss).apply(lines, mode="add")
    assert result.dialect == "tier_a"
