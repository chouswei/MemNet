"""Tests for PLR/NPC field normalisation."""

from __future__ import annotations

from novel_mcp.character_gender import (
    PLR_IDX_BODY,
    PLR_IDX_GENDER,
    format_plr_wire,
    gender_from_body,
    normalise_npc_parts,
    normalise_plr_parts,
    npc_appearance,
    npc_personality,
    npc_traits,
    npc_voice,
    split_npc_trait_blob,
    split_traits_gender,
    strip_gender_from_body,
)


def test_strip_gender_from_body() -> None:
    body = "氣血:6/6；性別:男；疲勞:0"
    assert strip_gender_from_body(body) == "氣血:6/6；疲勞:0"
    assert gender_from_body(body) == "男"


def test_normalise_legacy_plr_seven_fields() -> None:
    parts = normalise_plr_parts(
        "P01|流民|1627|0|0|魂穿|氣血:6/6；性別:未定".split("|")
    )
    assert parts[PLR_IDX_GENDER] == "未定"
    assert "性別:" not in parts[PLR_IDX_BODY]


def test_normalise_plr_eight_fields() -> None:
    parts = normalise_plr_parts(
        "P01|流民|1627|女|0|0|魂穿|氣血:6/6".split("|")
    )
    assert parts[PLR_IDX_GENDER] == "女"
    assert format_plr_wire(parts).startswith("@PLR: P01|")


def test_split_npc_trait_blob() -> None:
    blob = "美貌、滿臉炭灰、匠戶孤女、聰慧、堅韌、僅土法"
    app, pers, voice, traits = split_npc_trait_blob(blob)
    assert app == "美貌、滿臉炭灰"
    assert pers == "聰慧、堅韌"
    assert voice == ""
    assert "匠戶孤女" in traits


def test_normalise_legacy_npc_twelve_fields() -> None:
    parts = normalise_npc_parts(
        [
            "N01",
            "沈芯",
            "1625",
            "女",
            "美貌、滿臉炭灰、匠戶孤女、聰慧、堅韌、溫柔、慾念、僅土法",
            "0",
            "土法",
            "sk",
            "it",
            "0",
            "常駐",
            "常駐",
        ]
    )
    assert npc_appearance(parts) == "美貌、滿臉炭灰"
    assert "聰慧" in npc_personality(parts)
    assert npc_traits(parts) == "匠戶孤女、僅土法"


def test_normalise_npc_fifteen_fields() -> None:
    parts = normalise_npc_parts(
        [
            "N01",
            "沈芯",
            "1625",
            "女",
            "美貌、滿臉炭灰",
            "聰慧、堅韌",
            "沉穩簡約",
            "匠戶孤女",
            "0",
            "土法",
            "sk",
            "it",
            "0",
            "常駐",
            "常駐",
        ]
    )
    assert npc_voice(parts) == "沉穩簡約"
    assert npc_traits(parts) == "匠戶孤女"


def test_split_traits_gender() -> None:
    assert split_traits_gender("女、美貌") == ("女", "美貌")
    assert split_traits_gender("聰慧") == ("未定", "聰慧")
