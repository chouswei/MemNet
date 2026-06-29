"""Tests for opening loadout catalog and per-slot commits."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from novel_mcp.catalog_schema import CatalogSchema
from novel_mcp.opening_loadout import (
    catalog_slots,
    commit_opening_pick,
    ensure_slot_offers,
    has_mwu_edges,
    parse_catalog_md,
    parse_pick_offer_count,
    roll_slot_offers,
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


def test_slot_counts_uses_schema_slots(wuxia_schema, fantasy_schema) -> None:
    from novel_mcp.martial_catalog_expand import slot_counts
    from novel_mcp.opening_loadout import catalog_slots

    arts = [{"id": "ART01", wuxia_schema.kind_field: "內功", wuxia_schema.tier_field: "一流", wuxia_schema.coeff_field: "1.0"}]
    arts[0][wuxia_schema.wire_columns[1]] = "測試"
    counts = slot_counts(arts, wuxia_schema)
    assert set(counts.keys()) == set(catalog_slots([], wuxia_schema).keys())
    fantasy_counts = slot_counts([], fantasy_schema)
    assert set(fantasy_counts.keys()) == {"neigong", "martial", "qinggong"}


def test_parse_pick_offer_count() -> None:
    assert parse_pick_offer_count("5-9") == (5, 9)
    assert parse_pick_offer_count("9-5") == (5, 9)
    assert parse_pick_offer_count(None)[0] >= 1


def test_roll_slot_offers_bounded() -> None:
    import random

    pool = [{"id": f"ART{i:02d}"} for i in range(1, 21)]
    rng = random.Random(42)
    ids = roll_slot_offers("mn_test", "neigong", pool, lo=5, hi=9, rng=rng)
    assert 5 <= len(ids) <= 9
    assert len(set(ids)) == len(ids)


def _offer_usr_map():
    return {
        "opening_arts": "未定;未定;未定",
        "martial_catalog_md": "catalog.md",
        "catalog_schema": "applications/novel_cursor/catalog_specs/wuxia_jinyong.json",
        "setup_pick_offer_count": "1-1",
        "opening_offer_neigong": "_",
        "opening_offer_martial": "_",
        "opening_offer_qinggong": "_",
    }


def _offer_uid_map():
    return {
        "opening_offer_neigong": "USR74",
        "opening_offer_martial": "USR75",
        "opening_offer_qinggong": "USR76",
    }


@contextmanager
def _patch_catalog(cat: Path, schema: CatalogSchema):
    usr_map = _offer_usr_map()

    def read_usr(_s, key):
        return usr_map.get(key)

    def uid_for_key(_s, key):
        return _offer_uid_map().get(key)

    with (
        patch("novel_mcp.opening_loadout.read_usr_by_key", side_effect=read_usr),
        patch("novel_mcp.opening_loadout.usr_id_for_key", side_effect=uid_for_key),
        patch("novel_mcp.opening_loadout.read_catalog_schema", return_value=schema),
        patch("novel_mcp.opening_loadout.resolve_catalog_path", return_value=cat),
        patch("novel_mcp.opening_loadout.setup_commit_errors", return_value=[]),
        patch("novel_mcp.opening_loadout.list_tag_data_rows", return_value=[]),
        patch("novel_mcp.opening_loadout.resolve_catalog_session_id", return_value=None),
    ):
        yield


def test_commit_opening_pick_wrong_slot_order(
    tmp_path: Path, wuxia_schema: CatalogSchema
) -> None:
    cat = tmp_path / "catalog.md"
    cat.write_text(_CATALOG, encoding="utf-8")

    with _patch_catalog(cat, wuxia_schema):
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

    with (
        _patch_catalog(cat, wuxia_schema),
        patch("novel_mcp.opening_loadout.graph_update", side_effect=fake_update),
        patch("novel_mcp.player_setup.read_player_setup", return_value=setup_after),
    ):
        out = commit_opening_pick("mn_x", "neigong", "ART01")
    assert out["exit_code"] == 0
    assert any("USR58" in ln for batch in updates for ln in batch)
    assert not any("has_mwu" in ln for batch in updates for ln in batch)


def test_read_martial_catalog_random_offers(
    tmp_path: Path, wuxia_schema: CatalogSchema
) -> None:
    from novel_mcp.opening_loadout import read_martial_catalog

    lines = ["@ART: ART01|太玄經|綜合|超一流|1.75|俠客行|常駐"]
    for i in range(10, 30):
        lines.append(f"@ART: ART{i:02d}|內功{i}|內功|二流|1.0|作品|常駐")
    cat = tmp_path / "catalog.md"
    cat.write_text("```text\n" + "\n".join(lines) + "\n```", encoding="utf-8")
    usr_map = _offer_usr_map()
    usr_map["setup_pick_offer_count"] = "5-9"

    def read_usr(_s, key):
        return usr_map.get(key)

    with (
        _patch_catalog(cat, wuxia_schema),
        patch("novel_mcp.opening_loadout.read_usr_by_key", side_effect=read_usr),
        patch("novel_mcp.opening_loadout.graph_update", return_value=(0, [])),
    ):
        out = read_martial_catalog("mn_seed_test")
    neigong = out["slots"]["neigong"]
    assert out["exit_code"] == 0
    assert 5 <= neigong["offer_count"] <= 9
    assert neigong["pool_count"] >= 20


def test_has_mwu_edges_false() -> None:
    with patch("novel_mcp.opening_loadout.list_tag_data_rows", return_value=[]):
        assert has_mwu_edges("mn_x", "P01") is False


def test_reroll_opening_offers_changes_pool(
    tmp_path: Path, wuxia_schema: CatalogSchema
) -> None:
    from novel_mcp.opening_loadout import reroll_opening_offers

    lines = ["@ART: ART01|太玄經|綜合|超一流|1.75|俠客行|常駐"]
    for i in range(10, 30):
        lines.append(f"@ART: ART{i:02d}|內功{i}|內功|二流|1.0|作品|常駐")
    cat = tmp_path / "catalog.md"
    cat.write_text("```text\n" + "\n".join(lines) + "\n```", encoding="utf-8")

    state = {
        "opening_offer_neigong": "ART10;ART11;ART12;ART13;ART14",
        "opening_offer_roll_neigong": "0",
    }
    usr_map = _offer_usr_map()
    usr_map["setup_pick_offer_count"] = "5-5"

    def read_usr(_s, key):
        if key in state:
            return state[key]
        return usr_map.get(key)

    def fake_update(_s, lines):
        for ln in lines:
            parts = ln.split("|")
            if len(parts) >= 3 and parts[1] == "opening_offer_neigong":
                state["opening_offer_neigong"] = parts[2]
            if len(parts) >= 3 and parts[1] == "opening_offer_roll_neigong":
                state["opening_offer_roll_neigong"] = parts[2]
        return 0, []

    setup_pick = {
        "exit_code": 0,
        "setup_complete": False,
        "setup_guidance": {"next_action": "pick_neigong"},
    }

    with (
        _patch_catalog(cat, wuxia_schema),
        patch("novel_mcp.opening_loadout.read_usr_by_key", side_effect=read_usr),
        patch("novel_mcp.opening_loadout.graph_update", side_effect=fake_update),
        patch("novel_mcp.player_setup.read_player_setup", return_value=setup_pick),
    ):
        before = state["opening_offer_neigong"]
        out = reroll_opening_offers("mn_x", "neigong")
        after = state["opening_offer_neigong"]
    assert out["exit_code"] == 0
    assert state["opening_offer_roll_neigong"] == "1"
    assert before != after or len(set(after.split(";"))) == 5
