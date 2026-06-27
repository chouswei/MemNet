"""Tests for opening loadout catalog and per-slot commits."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from novel_mcp.catalog_schema import CatalogSchema
from novel_mcp.opening_loadout import (
    catalog_slots,
    commit_opening_pick,
    has_mwu_edges,
    parse_catalog_md,
    slot_for_art,
    validate_opening_picks,
)

_CATALOG = """
```text
@ART: ART01|太玄經|綜合|超一流|1.75|俠客行|常駐
@ART: ART02|獨孤九劍|武學|超一流|1.85|笑傲|常駐
@ART: ART04|凌波微步|輕功|一流|1.70|天龍|常駐
```
"""


def test_parse_catalog_and_slots(wuxia_schema: CatalogSchema) -> None:
    arts = parse_catalog_md(_CATALOG, wuxia_schema)
    slots = catalog_slots(arts, wuxia_schema)
    assert slots["neigong"]["arts"][0]["id"] == "ART01"
    assert slots["martial"]["arts"][0]["id"] == "ART02"
    assert slots["qinggong"]["arts"][0]["id"] == "ART04"


def test_slot_for_art(wuxia_schema: CatalogSchema) -> None:
    k = wuxia_schema.kind_field
    assert slot_for_art({k: "綜合"}, wuxia_schema) == "neigong"
    assert slot_for_art({k: "武學"}, wuxia_schema) == "martial"
    assert slot_for_art({k: "輕功"}, wuxia_schema) == "qinggong"


def test_validate_opening_picks(wuxia_schema: CatalogSchema) -> None:
    arts = parse_catalog_md(_CATALOG, wuxia_schema)
    assert validate_opening_picks(["ART01", "ART02", "ART04"], arts, wuxia_schema) == []
    assert validate_opening_picks(["ART02", "ART02", "ART04"], arts, wuxia_schema)


def _patch_catalog(cat: Path, schema: CatalogSchema):
    rel = "catalog.md"
    schema_rel = "applications/novel_cursor/catalog_specs/wuxia_jinyong.json"

    def read_usr(_s, key):
        return {
            "opening_arts": "未定;未定;未定",
            "martial_catalog_md": rel,
            "catalog_schema": schema_rel,
        }.get(key)

    return patch(
        "novel_mcp.opening_loadout.read_usr_by_key", side_effect=read_usr
    ), patch(
        "novel_mcp.opening_loadout.read_catalog_schema", return_value=schema
    ), patch(
        "novel_mcp.opening_loadout.resolve_catalog_path", return_value=cat
    ), patch("novel_mcp.opening_loadout.setup_commit_errors", return_value=[])


def test_commit_opening_pick_wrong_slot_order(
    tmp_path: Path, wuxia_schema: CatalogSchema
) -> None:
    cat = tmp_path / "catalog.md"
    cat.write_text(_CATALOG, encoding="utf-8")

    patches = _patch_catalog(cat, wuxia_schema)
    with patches[0], patches[1], patches[2], patches[3]:
        out = commit_opening_pick("mn_x", "martial", "ART02")
    assert out["exit_code"] == 2


def test_commit_neigong_no_wire_until_third(
    tmp_path: Path, wuxia_schema: CatalogSchema
) -> None:
    cat = tmp_path / "catalog.md"
    cat.write_text(_CATALOG, encoding="utf-8")
    updates: list[list[str]] = []

    def fake_update(session, lines):
        updates.append(lines)
        return 0, []

    setup_after = {
        "exit_code": 0,
        "setup_complete": False,
        "profile": {"complete": True},
        "loadout": {"next_slot": "martial", "complete": False},
        "setup_guidance": {"next_action": "pick_martial"},
    }

    patches = _patch_catalog(cat, wuxia_schema)
    with patches[0], patches[1], patches[2], patches[3], patch(
        "novel_mcp.opening_loadout.graph_update", side_effect=fake_update
    ), patch("novel_mcp.player_setup.read_player_setup", return_value=setup_after):
        out = commit_opening_pick("mn_x", "neigong", "ART01")
    assert out["exit_code"] == 0
    assert any("USR58" in ln for ln in updates[0])
    assert not any("has_mwu" in ln for ln in updates[0])


def test_has_mwu_edges_false() -> None:
    with patch("novel_mcp.opening_loadout.list_tag_data_rows", return_value=[]):
        assert has_mwu_edges("mn_x", "P01") is False
