"""Leftover IdAllocator NEW mint — not a product contract (0.10 identity cut)."""

from __future__ import annotations

from memnet.id_allocator import IdAllocator
from memnet.records import Document, EdgeRec, Field, NodeRec, Op


def _node(nid: str) -> NodeRec:
    fields = [Field("type", "=", "fact"), Field("code", "=", "x")]
    fields.append(Field("recycle", "=", "persistent"))
    return NodeRec(op=Op.CREATE, kind="CLM", id=nid, fields=fields)


def test_leftover_mint_new_nodes_and_edges() -> None:
    """leftover AssignedIdMap / NEW mint still works; product Commit does not use it."""
    edge = EdgeRec(op=Op.CREATE, edge_id="NEW", frm="A1", rel="about", to="A1")
    edge.fields.append(Field("recycle", "=", "persistent"))
    doc = Document(items=[_node("NEW"), edge])
    alloc = IdAllocator(existing_ids={"A1"})
    assigned = alloc.mint_document(doc)
    assert assigned.mapping
    assert doc.items[0].id.startswith("CLM")
    assert doc.items[0].id != "NEW"
    assert doc.items[1].edge_id is not None
    assert doc.items[1].edge_id.startswith("E")


def test_leftover_mint_noop_when_no_new() -> None:
    doc = Document(items=[_node("C10")])
    alloc = IdAllocator()
    assigned = alloc.mint_document(doc)
    assert assigned.mapping == {}
    assert doc.items[0].id == "C10"


def test_leftover_allocate_from_locator_not_product() -> None:
    """leftover helper still deterministic; product ingest does not use it as PK."""
    alloc = IdAllocator()
    a = alloc.allocate_from_locator("CMP", "R1")
    b = alloc.allocate_from_locator("CMP", "R1")
    assert a == "CMP_R1"
    assert a == b
