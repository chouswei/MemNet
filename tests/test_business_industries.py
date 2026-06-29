"""Tests for @BIZ industry sheet reader."""

from __future__ import annotations

import json
from pathlib import Path

from novel_mcp.player_sheet import read_business_industries


def _schema():
    from novel_mcp.catalog_schema import CatalogSchema

    data = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "applications/novel_cursor/catalog_specs/wuxia_jinyong.json"
        ).read_text(encoding="utf-8")
    )
    return CatalogSchema.from_dict(data)


def _patch_rows(monkeypatch, edges, biz_rows=None):
    biz_rows = biz_rows or [
        ["B01", "沈家鐵坊", "鐵匠鋪", "江南河畔", "0", "2", "0", "0", "常駐"],
        ["B02", "城外煤窯", "礦務", "郊外", "10", "0", "3", "1", "常駐"],
    ]
    monkeypatch.setattr(
        "novel_mcp.player_sheet.list_tag_data_rows",
        lambda session, tag: {
            "BIZ": biz_rows,
            "NPC": [
                ["N01", "沈芯", "1625", "traits"],
                ["N02", "沈蘭", "1627", "traits"],
            ],
            "PRD": [
                ["PRD01", "焦炭", "物資", "0", "0", "未量產"],
                ["PRD02", "工業級生鐵", "物資", "0", "0", "未量產"],
            ],
            "EDG": edges,
        }.get(tag, []),
    )


def test_hiring_only_not_shown(monkeypatch):
    schema = _schema()
    _patch_rows(
        monkeypatch,
        [
            ["E09", "N01", "manages", "B01", "經營"],
            ["E11", "B01", "hiring", "P01", "待聘"],
        ],
    )
    assert read_business_industries("mn_x", "P01", schema) == []


def test_player_owned_and_managed_businesses(monkeypatch):
    schema = _schema()
    _patch_rows(
        monkeypatch,
        [
            ["E09", "N01", "manages", "B01", "經營"],
            ["E10", "N02", "assists", "B01", "協助"],
            ["EP1", "P01", "manages", "B01", "經營"],
            ["EP2", "P01", "owns", "B02", "持有"],
            ["E12", "B01", "upgrades", "T01", "任務"],
            ["EL04", "LIB01", "cite", "T01", ""],
            ["EL05", "LIB01", "cite", "TEC01", ""],
            ["EL06", "LIB01", "cite", "TEC02", ""],
            ["E03", "TEC01", "produce", "PRD01", ""],
            ["E04", "TEC02", "produce", "PRD02", ""],
        ],
    )

    rows = read_business_industries("mn_x", "P01", schema)
    assert len(rows) == 2
    by_id = {r["id"]: r for r in rows}

    b01 = by_id["B01"]
    assert b01["name"] == "沈家鐵坊"
    assert b01["plr_role"] == "manages"
    assert b01["manager"] == "沈芯"
    assert {p["name"] for p in b01["products"]} == {"焦炭", "工業級生鐵"}

    b02 = by_id["B02"]
    assert b02["name"] == "城外煤窯"
    assert b02["plr_role"] == "owns"
    assert b02["products"] == []
