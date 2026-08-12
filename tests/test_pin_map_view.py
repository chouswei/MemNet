"""Pin map view= shell / interior soft caps (GQL mutate + shaped emit)."""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.pin_map_composer import (
    SHELL_MAX_EDGES,
    SHELL_MAX_NODES,
    PinMapComposer,
    apply_shell_soft_cap,
    normalize_view,
    resolve_view_budget,
)
from memnet.session import open_session

_CST_MAP = ["SCHEMA CST ; fields=id name role ports law recycle"]


def _star_graph_lines(n_leaves: int = 12) -> list[str]:
    """Anchor CST_Hub with many member_of leaves (one-hop shell blow-up)."""
    lines = [
        "CREATE (:CST {id: 'CST_Hub', name: 'hub', role: 'person'})",
    ]
    for i in range(n_leaves):
        lid = f"CST_L{i:02d}"
        lines.append(f"CREATE (:CST {{id: '{lid}', name: 'leaf{i}', role: 'person'}})")
        lines.append(
            f"MATCH (a {{id: '{lid}'}}), (b {{id: 'CST_Hub'}})\n"
            f"CREATE (a)-[:member_of {{id: 'E_m{i:02d}'}}]->(b)"
        )
    return lines


def test_normalize_view_tokens():
    assert normalize_view(None) is None
    assert normalize_view("") is None
    assert normalize_view("default") is None
    assert normalize_view("SHELL") == "shell"
    assert normalize_view("interior") == "interior"
    assert normalize_view("flowchart") == "flowchart"
    with pytest.raises(MemNetError) as ei:
        normalize_view("persons")
    assert ei.value.code == "bad_view"


def test_resolve_view_budget_shell_vs_interior():
    d, m, soft = resolve_view_budget("shell", depth=2, max_rows=50)
    assert d == 1 and m == 50 and soft is True
    d, m, soft = resolve_view_budget("interior", depth=2, max_rows=50)
    assert d == 2 and m == 50 and soft is False
    d, m, soft = resolve_view_budget(None, depth=2, max_rows=50)
    assert d == 2 and soft is False
    d, m, soft = resolve_view_budget("flowchart", depth=3, max_rows=40)
    assert d == 1 and soft is True


def test_apply_shell_soft_cap_unit():
    from memnet.models import Record

    rows = [
        Record(tag="LAW", fields={"id": "LAW01", "name": "EDG"}),
        Record(tag="CST", fields={"id": "CST_Hub", "name": "hub"}),
    ]
    for i in range(10):
        rows.append(
            Record(tag="CST", fields={"id": f"CST_L{i:02d}", "name": f"l{i}"})
        )
        rows.append(
            Record(
                tag="EDG",
                fields={
                    "id": f"E{i:02d}",
                    "src": f"CST_L{i:02d}",
                    "relation": "member_of",
                    "dist": "CST_Hub",
                },
            )
        )
    capped = apply_shell_soft_cap(rows, anchor="CST_Hub")
    laws = [r for r in capped if r.tag == "LAW"]
    nodes = [r for r in capped if r.tag != "LAW" and r.tag != "EDG"]
    edges = [r for r in capped if r.tag == "EDG"]
    assert laws and laws[0].id == "LAW01"
    assert len(nodes) <= SHELL_MAX_NODES
    assert nodes[0].id == "CST_Hub"
    assert len(edges) <= SHELL_MAX_EDGES


def test_compose_view_shell_caps_fanout(memnet_temp):
    ss = open_session(map_lines=list(_CST_MAP))
    MutateGate(ss).apply(_star_graph_lines(12), mode="add", allow_new_relation=True)
    composer = PinMapComposer(ss)

    rows_default, _ = composer.compose(anchor="CST_Hub", depth=2, max_rows=50)
    nodes_default = [r for r in rows_default if r.tag == "CST"]
    assert len(nodes_default) > SHELL_MAX_NODES

    rows_shell, text_shell = composer.compose(
        anchor="CST_Hub", depth=2, max_rows=50, view="shell"
    )
    nodes_shell = [r for r in rows_shell if r.tag == "CST"]
    edges_shell = [r for r in rows_shell if r.tag == "EDG"]
    assert len(nodes_shell) <= SHELL_MAX_NODES
    assert len(edges_shell) <= SHELL_MAX_EDGES
    assert "CST_Hub" in text_shell
    assert "(:CST" in text_shell
    assert nodes_shell[0].id == "CST_Hub" or any(r.id == "CST_Hub" for r in nodes_shell)

    rows_int, _ = composer.compose(
        anchor="CST_Hub", depth=2, max_rows=50, view="interior"
    )
    nodes_int = [r for r in rows_int if r.tag == "CST"]
    assert len(nodes_int) > len(nodes_shell)


def test_compose_omit_view_unchanged(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply(
        [
            "CREATE (:PLR {id: 'PLR01', identity: 'Hero', wealth: 1, cashflow: 0, "
            "monopoly: 0, reputation: 0, inventory: 'bag'})"
        ],
        mode="add",
    )
    a = PinMapComposer(ss).compose(anchor="PLR01", depth=1)[1]
    b = PinMapComposer(ss).compose(anchor="PLR01", depth=1, view=None)[1]
    assert a == b
    assert "PLR01" in a
    assert "(:PLR" in a


def test_compose_bad_view(memnet_temp):
    ss = open_session(map_lines=list(_CST_MAP))
    MutateGate(ss).apply(
        ["CREATE (:CST {id: 'CST_A', name: 'a'})"],
        mode="add",
    )
    with pytest.raises(MemNetError) as ei:
        PinMapComposer(ss).compose(anchor="CST_A", view="org")
    assert ei.value.code == "bad_view"
