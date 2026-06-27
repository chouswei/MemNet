"""Tests for read_player_setup guidance next_action."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from novel_mcp.player_setup import read_player_setup


@contextmanager
def _patch_setup(*, name="未定", gender="未定", opening="未定;未定;未定"):
    def read_usr(session, key):
        return {
            "pc_name": name,
            "pc_gender": gender,
            "opening_arts": opening,
            "martial_catalog_md": "application-notes/novel-shenjia-martial-catalog.md",
            "setup_god_line_open": "再熬夜啊～死了齁？",
            "setup_god_line_profile": "報到姓名性別",
        }.get(key)

    arts = [
        {"id": "ART01", "名稱": "太玄經", "門類": "綜合"},
        {"id": "ART02", "名稱": "獨孤九劍", "門類": "武學"},
        {"id": "ART04", "名稱": "凌波微步", "門類": "輕功"},
    ]

    def read_rec(session, uid):
        return {
            "USR60": ["USR60", "setup_scene_neigong", "氣海長廊;hint", "persistent"],
            "USR61": ["USR61", "setup_scene_martial", "試招石台;hint", "persistent"],
            "USR62": ["USR62", "setup_scene_qinggong", "身法雲橋;hint", "persistent"],
            "USR63": ["USR63", "setup_tone", "god_banter;過勞吐槽", "persistent"],
            "USR63": ["USR63", "setup_tone", "god_banter", "過勞吐槽;禁肅穆"],
        }.get(uid)

    with patch("novel_mcp.player_profile.read_usr_by_key", side_effect=read_usr), patch(
        "novel_mcp.opening_loadout.read_usr_by_key", side_effect=read_usr
    ), patch("novel_mcp.player_setup.read_usr_by_key", side_effect=read_usr), patch(
        "novel_mcp.opening_loadout.read_catalog_schema"
    ) as mock_schema, patch(
        "novel_mcp.opening_loadout.resolve_catalog_path"
    ), patch(
        "novel_mcp.opening_loadout.load_catalog_from_path", return_value=arts
    ), patch(
        "novel_mcp.player_setup.read_usr_record", side_effect=read_rec
    ):
        from novel_mcp.catalog_schema import CatalogSchema
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        mock_schema.return_value = CatalogSchema.load_json(
            root / "applications/novel_cursor/catalog_specs/wuxia_jinyong.json"
        )
        yield


def test_next_action_narrate_open() -> None:
    with _patch_setup():
        out = read_player_setup("mn_x")
    assert out["setup_guidance"]["next_action"] == "narrate_open"
    assert "再熬夜" in out["setup_guidance"]["suggested_lines"][0]


def test_next_action_after_profile() -> None:
    with _patch_setup(name="北見硝", gender="男"):
        out = read_player_setup("mn_x")
    assert out["setup_guidance"]["next_action"] == "narrate_library"


def test_next_action_start_play() -> None:
    with _patch_setup(name="北見硝", gender="男", opening="ART01;ART02;ART04"):
        out = read_player_setup("mn_x")
    assert out["setup_complete"] is True
    assert out["setup_guidance"]["next_action"] == "start_play"
