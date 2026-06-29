"""Tests for holder|knows|entity EDG acquaintance gating."""

from __future__ import annotations

from novel_mcp.entity_knowledge import (
    can_show_canonical_name,
    holder_knows_entity,
    knowledge_record,
    load_holder_knowledge,
    resolve_biz_display,
    resolve_npc_display_name,
)
from novel_mcp.presentation import compile_presentation

_NPC = ["N01", "沈芯", "1625", "女", "美貌、滿臉炭灰", "聰慧", "沉穩簡約", "匠戶孤女", "0", "土法", "sk", "it", "0", "需小工", "常駐"]
_BIZ = ["B01", "沈家鐵坊", "鐵坊", "嘉定西門外", "0", "2", "0", "0", "常駐"]


def _edg_rows():
    return [
        ["EK01", "P01", "knows", "N01", "", "初識", "persistent"],
        ["EK02", "P01", "knows_via", "B01", "", "耳聞", "persistent"],
    ]


def test_holder_knows_entity_from_edg(monkeypatch) -> None:
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: _edg_rows() if tag == "EDG" else [],
    )
    assert holder_knows_entity("mn_test", "P01", "N01")
    assert holder_knows_entity("mn_test", "P01", "B01")
    assert not holder_knows_entity("mn_test", "P01", "N02")
    assert not holder_knows_entity("mn_test", "P01", "TEC01")


def test_unknows_edge_is_not_acquaintance(monkeypatch) -> None:
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: (
            [["EN10", "N01", "unknows", "TEC01", "鎖定", "", "persistent"]] if tag == "EDG" else []
        ),
    )
    assert not holder_knows_entity("mn_test", "P01", "TEC01")
    assert not holder_knows_entity("mn_test", "N01", "TEC01")


def test_resolve_npc_display_name_masks_without_knows(monkeypatch) -> None:
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: [] if tag == "EDG" else [],
    )
    assert resolve_npc_display_name("mn_test", "P01", _NPC) == "匠戶孤女"


def test_resolve_biz_display_masks_without_knows(monkeypatch) -> None:
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: [] if tag == "EDG" else [],
    )
    out = resolve_biz_display("mn_test", "P01", _BIZ)
    assert out["known"] is False
    assert out["name"] == "鐵坊"
    assert out["location"] == "附近"


def test_resolve_biz_display_full_when_knows(monkeypatch) -> None:
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: (
            [["EK02", "P01", "knows", "B01", "", "熟識", "persistent"]] if tag == "EDG" else []
        ),
    )
    out = resolve_biz_display("mn_test", "P01", _BIZ)
    assert out["known"] is True
    assert out["name"] == "沈家鐵坊"


def test_knowledge_record_depth(monkeypatch) -> None:
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: (
            [["EK02", "P01", "knows_via", "B01", "", "耳聞", "persistent"]] if tag == "EDG" else []
        ),
    )
    rec = knowledge_record("mn_test", "P01", "B01")
    assert rec is not None
    assert rec["relation"] == "knows_via"
    assert rec["depth"] == "耳聞"


def test_resolve_biz_display_heard_name_via_knows_via(monkeypatch) -> None:
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: (
            [["EK02", "P01", "knows_via", "B01", "", "耳聞", "persistent"]] if tag == "EDG" else []
        ),
    )
    out = resolve_biz_display("mn_test", "P01", _BIZ)
    assert out["known"] is True
    assert out["name"] == "沈家鐵坊"
    assert out["name_visible"] is True
    assert out["location"] == "附近"  # 耳聞 < 粗識


def test_npc_name_stays_masked_on_knows_via_耳闻(monkeypatch) -> None:
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: (
            [["EK01", "P01", "knows_via", "N01", "", "耳聞", "persistent"]] if tag == "EDG" else []
        ),
    )
    assert resolve_npc_display_name("mn_test", "P01", _NPC) == "匠戶孤女"
    rec = knowledge_record("mn_test", "P01", "N01")
    assert rec is not None
    assert not can_show_canonical_name(rec, entity_kind="npc")


def test_presentation_masks_npc_and_biz(monkeypatch) -> None:
    warm = """\
@SYS: SYS01|1|1637-09-01T06|0|0|25|fx
@NPC: N01|沈芯|1625|女|美貌、滿臉炭灰|聰慧|沉穩簡約|匠戶孤女|0|土法|sk|it|0|需小工|常駐
@BIZ: B01|沈家鐵坊|鐵坊|嘉定西門外|0|2|0|0|常駐
@PLR: P01|流民|1627|未定|0|0|魂穿|氣血:6/6
"""
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: [] if tag == "EDG" else [],
    )
    pres = compile_presentation(warm, {"beat_stage": "prose"}, session="mn_test")
    assert pres["scene"]["npcs"][0]["name"] == "匠戶孤女"
    assert pres["scene"]["npcs"][0]["known"] is False
    assert pres["scene"]["npcs"][0]["name_visible"] is False
    assert pres["scene"]["biz"]["name"] == "鐵坊"
    assert pres["scene"]["biz"]["known"] is False


def test_presentation_shows_names_when_knows_edges(monkeypatch) -> None:
    warm = """\
@NPC: N01|沈芯|1625|女|美貌|聰慧|沉穩|匠戶孤女|0|土法|sk|it|0|需|常駐
@BIZ: B01|沈家鐵坊|鐵坊|嘉定|0|0|0|0|常駐
@PLR: P01|流民|1627|未定|0|0|魂穿|氣血:6/6
"""
    monkeypatch.setattr(
        "novel_mcp.entity_knowledge.list_tag_data_rows",
        lambda session, tag: (
            [
                ["EK01", "P01", "knows", "N01", "", "初識", "persistent"],
                ["EK02", "P01", "knows", "B01", "", "初識", "persistent"],
            ]
            if tag == "EDG"
            else []
        ),
    )
    pres = compile_presentation(warm, {"beat_stage": "prose"}, session="mn_test")
    assert pres["scene"]["npcs"][0]["name"] == "沈芯"
    assert pres["scene"]["biz"]["name"] == "沈家鐵坊"
