"""Tests for player_sheet graph readers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from novel_mcp.catalog_schema import CatalogSchema, resolve_item_actions
from novel_mcp.player_sheet import read_player_sheet, read_production_nodes


def _minimal_schema() -> CatalogSchema:
    data = json.loads(
        (Path(__file__).resolve().parents[1] / "applications/novel_cursor/catalog_specs/wuxia_jinyong.json").read_text(
            encoding="utf-8"
        )
    )
    return CatalogSchema.from_dict(data)


def test_resolve_item_actions_by_kind():
    schema = _minimal_schema()
    book = resolve_item_actions(schema, name="太玄經", kind="秘笈")
    assert book[0]["id"] == "read"
    assert "研讀" in book[0]["template"]
    med = resolve_item_actions(schema, name="傷藥", kind="藥品")
    assert "服用" in med[0]["template"]
    default = resolve_item_actions(schema, name="鐵鉗", kind="default")
    assert "使用" in default[0]["template"]


def test_read_player_sheet_items_and_arts(monkeypatch):
    schema = _minimal_schema()

    def fake_schema(session, **kw):
        return schema

    monkeypatch.setattr("novel_mcp.player_sheet.read_catalog_schema", fake_schema)
    monkeypatch.setattr("novel_mcp.player_sheet.first_plr_id", lambda s: "P01")
    monkeypatch.setattr(
        "novel_mcp.player_sheet.list_tag_data_rows",
        lambda session, tag: {
            "ITM": [["IM01", "P01", "傷藥", "2", "常駐"]],
            "MWU": [["MWU01", "P01", "ART01", "初学乍練", "1"]],
            "WUX": [["WUX01", "P01", "neigong", "未入門", "0"]],
            "ART": [["ART01", "太玄經", "內功", "一流", "1.2", "出處", "回收"]],
            "TEC": [],
            "EDG": [],
            "PRD": [],
        }.get(tag, []),
    )

    sheet = read_player_sheet("mn_test")
    assert sheet["exit_code"] == 0
    assert len(sheet["items"]) == 1
    assert sheet["items"][0]["kind"] == "藥品"
    assert len(sheet["arts"]) == 1
    assert sheet["arts"][0].get("actions")
    assert len(sheet["body_stats"]) == 1
    assert sheet["body_stats"][0].get("actions")


def test_read_skills_resolves_art_name_from_catalog_session(monkeypatch):
    schema = _minimal_schema()
    story_rows = {
        "MWU": [["MWU01", "P01", "ART10", "初学乍練", "1"]],
        "WUX": [],
        "ART": [],
    }
    catalog_rows = {
        "ART": [["ART10", "九陽神功", "內功", "絕頂", "2.00", "倚天", "回收"]],
    }

    def fake_list(session, tag):
        if session == "mn_story":
            return story_rows.get(tag, [])
        if session == "mn_catalog":
            return catalog_rows.get(tag, [])
        return []

    monkeypatch.setattr("novel_mcp.player_sheet.list_tag_data_rows", fake_list)
    monkeypatch.setattr(
        "novel_mcp.player_sheet.resolve_catalog_session_id",
        lambda story, sch, **kw: "mn_catalog" if story == "mn_story" else None,
    )
    monkeypatch.setattr(
        "novel_mcp.player_sheet._schema_path_for_session",
        lambda session, **kw: None,
    )

    from novel_mcp.player_sheet import read_skills_for_owner

    arts, _ = read_skills_for_owner("mn_story", "P01", schema)
    assert len(arts) == 1
    assert arts[0]["name"] == "九陽神功"
    assert arts[0]["art_id"] == "ART10"


def test_tec_status_not_unlocked_is_locked():
    from novel_mcp.player_sheet import _tec_status

    schema = _minimal_schema()
    prod = schema.production
    assert prod is not None
    status, unlocked = _tec_status(["TEC99", "測試", "域", "未解鎖"], prod)
    assert unlocked is False
    assert status == "鎖定"


def test_read_production_nodes_builtin_expand(monkeypatch):
    schema = _minimal_schema()
    monkeypatch.setattr(
        "novel_mcp.player_sheet.list_tag_data_rows",
        lambda session, tag: {
            "TEC": [["TEC01", "焦炭製作", "熱力冶金", "已解鎖", "效果"]],
            "EDG": [
                ["E03", "TEC01", "produce", "PRD01", "產出"],
                ["E04", "TEC01", "develop", "TEC02", "條件"],
            ],
            "PRD": [["PRD01", "焦炭", "物資", "0", "0", "量產中"]],
        }.get(tag, []),
    )
    monkeypatch.setattr("novel_mcp.player_sheet.read_usr_by_key", lambda s, k: "2" if "lines" in k else None)
    monkeypatch.setattr("novel_mcp.player_sheet.first_plr_id", lambda s: "P01")

    nodes = read_production_nodes("mn_test", schema)
    assert len(nodes) == 1
    node = nodes[0]
    assert node["asset_mode"] == "builtin"
    assert node["lines"] == 2
    action_ids = [a["id"] for a in node["actions"]]
    assert "produce" in action_ids
    assert "expand" in action_ids


def test_read_production_nodes_empty_when_no_tec(monkeypatch):
    schema = _minimal_schema()
    monkeypatch.setattr("novel_mcp.player_sheet.list_tag_data_rows", lambda s, t: [])
    assert read_production_nodes("mn_test", schema) == []
