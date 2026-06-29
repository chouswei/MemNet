"""Tests for generic presentation compiler."""

from __future__ import annotations

from novel_mcp.presentation import compile_presentation

WUXIA_WARM = """\
@LAW: LAW-PROSE00|敘事|1|warm_prose|ban_telegraphic
@LAW: LAW-PERS02|選項|1|opt_readable_baihua|full_sentence;no_action_chain
@USR: USR51|prose_warm|second person; wuxia voice|persistent
@USR: USR23|beat_stage|oln|persistent
@USR: USR99|stage_hint_oln|Draft OLN: mood, beats, dialogue skeleton|persistent
@PLR: P01|vagrant|1627|未定|0|0|skills|qi:6/6
"""

RPG_WARM = """\
@LAW: LAW-HP01|CHR|1|cite_chr_attr|no_invent_stats
@USR: U01|beat_stage|scr|persistent
@USR: U02|stage_hint_scr|Draft script from storyboard|persistent
@USR: U03|prose_warm|third person limited|persistent
@PLR: H01|student|2010|女|0|0|bag|tired
"""


def test_presentation_wuxia_seed():
    pres = compile_presentation(
        WUXIA_WARM,
        {"beat_stage": "oln", "draft_target_chars": 800, "age_hint": "P01:10"},
        warm_walk="@WALK: STEP01 -[governs]-> USR51\n",
    )
    text = "\n".join(pres["contracts"])
    assert "Draft OLN" in text
    assert "second person" not in text
    assert pres["option_contracts"] == []
    assert pres["walk_hops"]


def test_presentation_rpg_seed_different_contract():
    pres = compile_presentation(RPG_WARM, {"beat_stage": "prose"})
    text = "\n".join(pres["contracts"])
    assert "third person" in text
    assert "LAW-HP01" in text


def test_scene_snapshot_npc_ages():
    warm = """\
@SYS: SYS01|1|1637-09-01T06|0|0|25|fx
@NPC: N01|沈芯|1625|女|美貌、滿臉炭灰|聰慧|沉穩簡約|匠戶孤女|0|土法|sk|it|0|需小工|常駐
@PLR: P01|流民|1627|未定|0|0|魂穿|氣血:6/6
"""
    pres = compile_presentation(
        warm,
        {
            "beat_stage": "prose",
            "character_ages": {"P01": 10, "N01": 12},
            "age_hint": "P01:10歲；N01:12歲",
        },
    )
    scene = pres["scene"]
    assert scene["npcs"][0]["age"] == 12
    assert scene["npcs"][0]["birth_year"] == 1625
    assert scene["npcs"][0]["appearance"] == "美貌、滿臉炭灰"
    assert scene["npcs"][0]["voice"] == "沉穩簡約"
    assert scene["npcs"][0]["traits"] == "匠戶孤女"
    assert scene["plr_age"] == 10


def test_option_contracts_on_prose_stage():
    pres = compile_presentation(
        WUXIA_WARM,
        {"beat_stage": "prose"},
    )
    assert pres["option_contracts"]
    assert any("opt_" in c.lower() or "PERS02" in c for c in pres["option_contracts"])
