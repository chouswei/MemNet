"""Minimal tests for IdAllocator NEW mint and no-op."""

from __future__ import annotations

from memnet.id_allocator import IdAllocator
from memnet.tier_a import parse


def test_mint_new_nodes_and_edges() -> None:
    doc = parse(
        "+ CLM [NEW] ; type=fact ; code=x ; recycle=persistent\n"
        "+ NEW [A1] --(about)--> [A1] ; recycle=persistent\n"
    )
    alloc = IdAllocator(existing_ids={"A1"})
    assigned = alloc.mint_document(doc)
    assert assigned.mapping
    assert doc.items[0].id.startswith("CLM")
    assert doc.items[0].id != "NEW"
    assert doc.items[1].edge_id is not None
    assert doc.items[1].edge_id.startswith("E")


def test_mint_noop_when_no_new() -> None:
    doc = parse("+ CLM [C10] ; type=fact ; code=x ; recycle=persistent\n")
    alloc = IdAllocator()
    assigned = alloc.mint_document(doc)
    assert assigned.mapping == {}
    assert doc.items[0].id == "C10"


def test_allocate_from_locator_leftover_not_product() -> None:
    """leftover helper still deterministic; product ingest does not use it as PK."""
    alloc = IdAllocator()
    a = alloc.allocate_from_locator("CMP", "R1")
    b = alloc.allocate_from_locator("CMP", "R1")
    assert a == "CMP_R1"
    assert a == b
