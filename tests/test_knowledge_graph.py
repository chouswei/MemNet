"""Tests for EDG-based knowledge view (replaces legacy @KNH)."""

from __future__ import annotations

from novel_mcp.entity_knowledge import (
    build_knowledge_view,
    can_speak_about,
    entity_refs_missing_from_warm,
    format_knowledge_hud,
    knowledge_gate_hint,
    merge_warm_catalog_lines,
    parse_warm_knowledge,
)

WARM = """\
@KNW: KNW01|焦炭製作|冶金|1637|常駐
@KNW: KNW03|欠債結繩賒炭|坊務|any|常駐
@EDG: EK10|P01|knows_via|KNW01||耳聞|圖書館|persistent
@EDG: EK11|P01|knows|KNW03||能述|親歷|persistent
@EDG: EK01|N01|knows|KNW03||能述|親歷|persistent
@EDG: EK07|N02|knows_via|KNW06||耳聞|聽聞|persistent
@PLR: P01|北見硝|1627|男|0|0|靈魂圖書館登峰|氣血:7/10
@NPC: N01|沈芯|1625|女|美貌|聰慧|沉穩簡約|匠戶孤女|0|土法|打鐵:略有小成|鐵鉗:1|0|需小工|常駐
"""


def test_parse_warm_knowledge():
    g = parse_warm_knowledge(WARM)
    assert len(g["catalog"]) == 2
    assert "P01" in g["by_holder"]
    assert g["by_holder"]["P01"][0]["名稱"] == "焦炭製作"
    assert g["by_holder"]["P01"][0]["深度"] == "耳聞"
    assert g["by_holder"]["P01"][0]["relation"] == "knows_via"


def test_can_speak_about():
    assert not can_speak_about("耳聞")
    assert can_speak_about("耳聞", min_depth="耳聞")
    assert can_speak_about("能述")


def test_knowledge_gate_hint():
    g = parse_warm_knowledge(WARM)
    assert "僅 耳聞" in (knowledge_gate_hint("P01", "焦炭製作", g) or "")
    assert knowledge_gate_hint("N01", "欠債結繩賒炭", g) is None


def test_entity_refs_missing_from_warm():
    warm = """\
@EDG: EK01|N01|knows|KNW04||能作|親歷|persistent
@KNW: KNW03|欠債|坊務|any|—|常駐
"""
    assert entity_refs_missing_from_warm(warm) == ["KNW04"]


def test_merge_warm_catalog_lines():
    warm = "@EDG: EK01|N01|knows|KNW04||能作|親歷|persistent\n"
    extra = "@KNW: KNW04|西堆防潮|工藝|any|常駐\n"
    merged = merge_warm_catalog_lines(warm, extra)
    g = parse_warm_knowledge(merged)
    assert g["by_holder"]["N01"][0]["名稱"] == "西堆防潮"


def test_format_knowledge_hud():
    g = build_knowledge_view(WARM)
    hud = format_knowledge_hud(g, holders=["P01", "N01", "N02"])
    assert "北見硝" in hud
    assert "焦炭製作" not in hud  # 耳聞 < 粗識 default
    assert "欠債" in hud or "賒炭" in hud
