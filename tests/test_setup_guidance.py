"""Tests for read_player_setup guidance next_action."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from novel_mcp.player_setup import read_player_setup


@contextmanager
def _patch_setup(*, name="未定", gender="未定", opening="未定;未定;未定", setup_ack=""):
    def read_usr(session, key):
        return {
            "pc_name": name,
            "pc_gender": gender,
            "opening_arts": opening,
            "setup_god_ack": setup_ack,
            "martial_catalog_md": "application-notes/novel-shenjia-martial-catalog.md",
            "catalog_schema": "applications/novel_cursor/catalog_specs/wuxia_jinyong.json",
            "setup_pick_offer_count": "1-3",
            "setup_god_line_open": "再熬夜啊～死了齁？",
            "setup_god_line_ask_name": "報個名",
            "setup_god_line_ask_gender": "性別？男或女",
            "setup_profile_name_rule": "cjk_2_4",
            "setup_profile_genders": "男;女",
            "opening_offer_neigong": "_",
            "opening_offer_martial": "_",
            "opening_offer_qinggong": "_",
            "setup_scene_neigong": "氣海長廊;hint",
            "setup_scene_martial": "試招石台;hint",
            "setup_scene_qinggong": "身法雲橋;hint",
            "setup_god_line_library": "喔，圖書館——進去翻。",
        }.get(key)

    arts = [
        {"id": "ART01", "名稱": "太玄經", "門類": "綜合"},
        {"id": "ART02", "名稱": "獨孤九劍", "門類": "武學"},
        {"id": "ART04", "名稱": "凌波微步", "門類": "輕功"},
    ]

    with patch("novel_mcp.player_profile.read_usr_by_key", side_effect=read_usr), patch(
        "novel_mcp.opening_loadout.read_usr_by_key", side_effect=read_usr
    ), patch("novel_mcp.player_setup.read_usr_by_key", side_effect=read_usr), patch(
        "novel_mcp.setup_ack.read_usr_by_key", side_effect=read_usr
    ), patch(
        "novel_mcp.setup_profile_rules.read_usr_by_key", side_effect=read_usr
    ), patch(
        "novel_mcp.opening_loadout.usr_id_for_key",
        side_effect=lambda _s, k: {
            "opening_offer_neigong": "USR74",
            "opening_offer_martial": "USR75",
            "opening_offer_qinggong": "USR76",
        }.get(k),
    ), patch(
        "novel_mcp.opening_loadout.graph_update", return_value=(0, [])
    ), patch(
        "novel_mcp.opening_loadout.read_catalog_schema"
    ) as mock_schema, patch(
        "novel_mcp.opening_loadout.resolve_catalog_path"
    ), patch(
        "novel_mcp.opening_loadout.load_catalog_from_path", return_value=arts
    ), patch(
        "novel_mcp.player_setup.read_usr_record",
        side_effect=lambda _s, uid: (
            ["USR63", "setup_tone", "god_banter;過勞吐槽", "persistent"]
            if uid == "USR63"
            else None
        ),
    ):
        from novel_mcp.catalog_schema import CatalogSchema
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        schema = CatalogSchema.load_json(
            root / "applications/novel_cursor/catalog_specs/wuxia_jinyong.json"
        )
        mock_schema.return_value = schema
        with patch("novel_mcp.player_setup.read_catalog_schema", return_value=schema):
            yield


def test_next_action_narrate_open() -> None:
    with _patch_setup():
        out = read_player_setup("mn_x")
    g = out["setup_guidance"]
    assert g["next_action"] == "narrate_open"
    assert g["suggested_lines"] == ["再熬夜啊～死了齁？"]
    assert g["follow_up_action"] == "narrate_ask_name"
    assert g["follow_up_lines"] == ["報個名"]


def test_next_action_ask_name_after_open_ack() -> None:
    with _patch_setup(setup_ack="narrate_open"):
        out = read_player_setup("mn_x")
    g = out["setup_guidance"]
    assert g["next_action"] == "narrate_ask_name"
    assert "再熬夜" in g["suggested_lines"][0]
    assert "報個名" in g["suggested_lines"][-1]


def test_next_action_ask_gender_after_name() -> None:
    with _patch_setup(name="北見硝", gender="未定"):
        out = read_player_setup("mn_x")
    assert out["setup_guidance"]["next_action"] == "narrate_ask_gender"
    assert "性別" in out["setup_guidance"]["suggested_lines"][0]


def test_next_action_after_profile() -> None:
    with _patch_setup(name="北見硝", gender="男"):
        out = read_player_setup("mn_x")
    assert out["setup_guidance"]["next_action"] == "narrate_pre_pick"


def test_narrate_transmigration_before_start_play() -> None:
    with _patch_setup(name="北見硝", gender="男", opening="ART01;ART02;ART04"):
        out = read_player_setup("mn_x")
    assert out["setup_complete"] is False
    assert out["setup_guidance"]["next_action"] == "narrate_transmigration"


def test_start_play() -> None:
    with _patch_setup(
        name="北見硝",
        gender="男",
        opening="ART01;ART02;ART04",
        setup_ack="narrate_open;narrate_pre_pick;narrate_transmigration",
    ):
        out = read_player_setup("mn_x")
    assert out["setup_complete"] is True
    assert out["setup_guidance"]["next_action"] == "start_play"
