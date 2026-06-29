"""Tests for party panel reader."""

from __future__ import annotations

import json
from pathlib import Path

from novel_mcp.catalog_schema import CatalogSchema
from novel_mcp.party_sheet import read_party_panel


def _aff_edg(eid, src, dst, intimacy, trust, respect, note=""):
    attrs = f"親密度:{intimacy};信任度:{trust};敬重:{respect}"
    if note:
        attrs += f";備註:{note}"
    return [eid, src, "aff_to", dst, "", attrs, "常駐"]


def _minimal_schema() -> CatalogSchema:
    data = json.loads(
        (Path(__file__).resolve().parents[1] / "applications/novel_cursor/catalog_specs/wuxia_jinyong.json").read_text(
            encoding="utf-8"
        )
    )
    return CatalogSchema.from_dict(data)


def test_read_party_panel_default_roster(monkeypatch):
    schema = _minimal_schema()

    def fake_schema(session, **kw):
        return schema

    def fake_usr(session, key):
        return {
            "party_roster": "P01;N01",
            "party_ui": "items,skills,attrs",
            "party_ui_note": "同行中",
        }.get(key)

    monkeypatch.setattr("novel_mcp.party_sheet.read_catalog_schema", fake_schema)
    monkeypatch.setattr("novel_mcp.party_sheet.read_usr_by_key", fake_usr)
    monkeypatch.setattr("novel_mcp.party_sheet.first_plr_id", lambda s: "P01")
    monkeypatch.setattr(
        "novel_mcp.party_sheet.list_tag_data_rows",
        lambda session, tag: {
            "PLR": [["P01", "主角", "1627", "未定", "0", "0", "魂穿", "氣血:6/6"]],
            "NPC": [["N01", "沈芯", "1625", "女", "美貌", "聰慧", "沉穩簡約", "匠戶孤女", "0", "土法", "基礎拳", "鐵鉗", "0", "常駐", "常駐"]],
            "ITM": [
                ["IM01", "P01", "傷藥", "2", "常駐"],
                ["IM02", "N01", "鐵鉗", "1", "常駐"],
            ],
            "MWU": [["MWU01", "P01", "ART01", "初学乍練", "1"]],
            "WUX": [["WUX01", "P01", "neigong", "未入門", "0"]],
            "ART": [["ART01", "太玄經", "內功", "一流", "1.2", "出處", "回收"]],
        }.get(tag, []),
    )
    monkeypatch.setattr(
        "novel_mcp.party_sheet.read_items_for_owner",
        lambda session, owner, schema, **kw: (
            [{"id": "IM02", "name": "鐵鉗", "qty": "1"}] if owner == "N01" else [{"id": "IM01", "name": "傷藥", "qty": "2"}]
        ),
    )
    monkeypatch.setattr(
        "novel_mcp.party_sheet.read_skills_for_owner",
        lambda session, owner, schema, **kw: (
            ([{"id": "MWU01", "name": "太玄經", "rank": "初学乍練"}], [{"id": "WUX01", "kind": "內功", "rank": "未入門"}])
            if owner == "P01"
            else ([], [])
        ),
    )

    panel = read_party_panel("mn_test")
    assert panel["exit_code"] == 0
    assert panel["ui_note"] == "同行中"
    assert len(panel["members"]) == 2
    assert panel["members"][0]["name"] == "主角"
    assert panel["members"][1]["items"][0]["name"] == "鐵鉗"
    assert panel["members"][0]["skills"][0]["name"] == "太玄經"


def test_read_party_panel_fallback_plr_only(monkeypatch):
    monkeypatch.setattr("novel_mcp.party_sheet.read_catalog_schema", lambda s, **kw: None)
    monkeypatch.setattr("novel_mcp.party_sheet.read_usr_by_key", lambda s, k: None)
    monkeypatch.setattr("novel_mcp.party_sheet.first_plr_id", lambda s: "P01")
    monkeypatch.setattr(
        "novel_mcp.party_sheet.list_tag_data_rows",
        lambda session, tag: {"PLR": [["P01", "流民", "1627", "未定", "0", "0", "", ""]]} .get(tag, []),
    )
    monkeypatch.setattr("novel_mcp.party_sheet.read_items_for_owner", lambda *a, **kw: [])
    monkeypatch.setattr("novel_mcp.party_sheet.read_skills_for_owner", lambda *a, **kw: ([], []))

    panel = read_party_panel("mn_test")
    assert len(panel["members"]) == 1
    assert panel["members"][0]["id"] == "P01"


def test_read_party_panel_plr_name_from_pc_name(monkeypatch):
    schema = _minimal_schema()

    def fake_usr(session, key):
        return {"pc_name": "北見硝"}.get(key)

    monkeypatch.setattr("novel_mcp.party_sheet.read_catalog_schema", lambda s, **kw: schema)
    monkeypatch.setattr("novel_mcp.party_sheet.read_usr_by_key", fake_usr)
    monkeypatch.setattr("novel_mcp.player_profile.read_usr_by_key", fake_usr)
    monkeypatch.setattr("novel_mcp.party_sheet.first_plr_id", lambda s: "P01")
    monkeypatch.setattr(
        "novel_mcp.party_sheet.list_tag_data_rows",
        lambda session, tag: {
            "PLR": [["P01", "流民", "1627", "男", "0", "0", "魂穿", "氣血:6/6"]],
        }.get(tag, []),
    )
    monkeypatch.setattr("novel_mcp.party_sheet.read_items_for_owner", lambda *a, **kw: [])
    monkeypatch.setattr("novel_mcp.party_sheet.read_skills_for_owner", lambda *a, **kw: ([], []))

    panel = read_party_panel("mn_test")
    assert panel["plr_name"] == "北見硝"
    assert panel["members"][0]["name"] == "北見硝"
    assert panel["members"][0]["attrs"][0] == {"label": "身份", "value": "流民"}


def test_read_party_panel_relations(monkeypatch):
    schema = _minimal_schema()

    def fake_usr(session, key):
        return {
            "party_roster": "P01;N01",
            "party_ui": "relations",
            "party_ui_note": "",
        }.get(key)

    monkeypatch.setattr("novel_mcp.party_sheet.read_catalog_schema", lambda s, **kw: schema)
    monkeypatch.setattr("novel_mcp.party_sheet.read_usr_by_key", fake_usr)
    monkeypatch.setattr("novel_mcp.party_sheet.first_plr_id", lambda s: "P01")
    def fake_rows(session, tag):
        return {
            "PLR": [["P01", "主角", "1627", "男", "0", "0", "魂穿", ""]],
            "NPC": [["N01", "沈芯", "1625", "女", "美貌", "聰慧", "沉穩簡約", "匠戶孤女", "0", "", "", "", "0", "常駐", "常駐"]],
            "EDG": [
                _aff_edg("EAFF01", "P01", "N01", "35", "60", "50", "姐弟日久"),
                _aff_edg("EAFF04", "N01", "P01", "40", "70", "55", "依賴姐姐"),
            ],
        }.get(tag, [])

    monkeypatch.setattr("novel_mcp.party_sheet.list_tag_data_rows", fake_rows)
    monkeypatch.setattr("novel_mcp.affinity_edges.list_tag_data_rows", fake_rows)
    monkeypatch.setattr("novel_mcp.party_sheet.read_items_for_owner", lambda *a, **kw: [])
    monkeypatch.setattr("novel_mcp.party_sheet.read_skills_for_owner", lambda *a, **kw: ([], []))

    panel = read_party_panel("mn_test")
    n01 = panel["members"][1]
    assert "relations" in n01
    assert n01["relations"]["to_member"]["dims"][0]["value"] == "35"
    assert n01["relations"]["to_member"]["dims"][1]["label"] == "信任度"
    assert n01["relations"]["from_member"]["dims"][1]["value"] == "70"
    assert n01["relations"]["to_member"]["note"] == "姐弟日久"


def test_read_party_panel_relations_asymmetric(monkeypatch):
    """A hostile to B does not require B hostile to A — separate directed rows."""
    schema = _minimal_schema()

    def fake_usr(session, key):
        return {"party_roster": "P01;N03", "party_ui": "relations"}.get(key)

    monkeypatch.setattr("novel_mcp.party_sheet.read_catalog_schema", lambda s, **kw: schema)
    monkeypatch.setattr("novel_mcp.party_sheet.read_usr_by_key", fake_usr)
    monkeypatch.setattr("novel_mcp.party_sheet.first_plr_id", lambda s: "P01")
    def fake_rows(session, tag):
        return {
            "PLR": [["P01", "主角", "1627", "男", "0", "0", "", ""]],
            "NPC": [["N03", "仇家", "1600", "男", "", "", "", "世仇", "0", "", "", "", "0", "常駐", "常駐"]],
            "EDG": [
                _aff_edg("EAFF10", "P01", "N03", "-40", "-80", "-60", "世仇"),
                _aff_edg("EAFF11", "N03", "P01", "15", "25", "0", "不識此人"),
            ],
        }.get(tag, [])

    monkeypatch.setattr("novel_mcp.party_sheet.list_tag_data_rows", fake_rows)
    monkeypatch.setattr("novel_mcp.affinity_edges.list_tag_data_rows", fake_rows)
    monkeypatch.setattr("novel_mcp.party_sheet.read_items_for_owner", lambda *a, **kw: [])
    monkeypatch.setattr("novel_mcp.party_sheet.read_skills_for_owner", lambda *a, **kw: ([], []))

    panel = read_party_panel("mn_test")
    rel = panel["members"][1]["relations"]
    assert rel["directed"] is True
    assert rel["plr_to_member"]["dims"][0]["value"] == "-40"
    assert rel["member_to_plr"]["dims"][0]["value"] == "15"
    assert rel["member_to_plr"]["note"] == "不識此人"


def test_read_party_panel_relations_negative_and_zero(monkeypatch):
    schema = _minimal_schema()

    def fake_usr(session, key):
        return {"party_roster": "P01;N03", "party_ui": "relations"}.get(key)

    monkeypatch.setattr("novel_mcp.party_sheet.read_catalog_schema", lambda s, **kw: schema)
    monkeypatch.setattr("novel_mcp.party_sheet.read_usr_by_key", fake_usr)
    monkeypatch.setattr("novel_mcp.party_sheet.first_plr_id", lambda s: "P01")
    def fake_rows(session, tag):
        return {
            "PLR": [["P01", "主角", "1627", "男", "0", "0", "", ""]],
            "NPC": [["N03", "仇家", "1600", "男", "", "", "", "世仇", "0", "", "", "", "0", "常駐", "常駐"]],
            "EDG": [_aff_edg("EAFF10", "P01", "N03", "-40", "-80", "0", "世仇")],
        }.get(tag, [])

    monkeypatch.setattr("novel_mcp.party_sheet.list_tag_data_rows", fake_rows)
    monkeypatch.setattr("novel_mcp.affinity_edges.list_tag_data_rows", fake_rows)
    monkeypatch.setattr("novel_mcp.party_sheet.read_items_for_owner", lambda *a, **kw: [])
    monkeypatch.setattr("novel_mcp.party_sheet.read_skills_for_owner", lambda *a, **kw: ([], []))

    panel = read_party_panel("mn_test")
    rel = panel["members"][1]["relations"]["to_member"]
    assert rel["dims"][0]["value"] == "-40"
    assert rel["dims"][2]["value"] == "0"
    assert len(rel["dims"]) == 3
