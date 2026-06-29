"""Shenjia martial catalog md meets schema min_slots and validates."""

from __future__ import annotations

from pathlib import Path

from novel_mcp.catalog_schema import CatalogSchema
from novel_mcp.martial_catalog_expand import slot_counts, validate_art_dict
from novel_mcp.opening_loadout import parse_catalog_md

_CATALOG_MD = Path(__file__).resolve().parents[1] / "application-notes/novel-shenjia-martial-catalog.md"


def test_shenjia_catalog_min_slots(wuxia_schema: CatalogSchema) -> None:
    schema = wuxia_schema
    text = _CATALOG_MD.read_text(encoding="utf-8")
    arts = parse_catalog_md(text, schema)
    counts = slot_counts(arts, schema)
    for slot, minimum in schema.min_slots.items():
        assert counts[slot] >= minimum, f"{slot}: {counts[slot]} < {minimum}"
    errors: list[str] = []
    for art in arts:
        errors.extend(validate_art_dict(art, schema))
    assert errors == [], errors
    names = [art[schema.wire_columns[1]] for art in arts]
    assert len(names) == len(set(names)), "duplicate art names"
