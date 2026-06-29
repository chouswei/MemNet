"""Integration-style walkthrough of god-realm setup FSM (mocked graph)."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from novel_mcp.opening_loadout import ensure_slot_offers
from novel_mcp.player_setup import read_player_setup
from novel_mcp.setup_ack import commit_setup_ack


@contextmanager
def _flow_patch(*, name="未定", gender="未定", opening="未定;未定;未定", ack=""):
    state = {
        "pc_name": name,
        "pc_gender": gender,
        "opening_arts": opening,
        "setup_god_ack": ack,
        "martial_catalog_md": "application-notes/novel-shenjia-martial-catalog.md",
        "catalog_schema": "applications/novel_cursor/catalog_specs/wuxia_jinyong.json",
        "setup_pick_offer_count": "1-3",
        "setup_god_line_open": "開場",
        "setup_god_line_ask_name": "報名",
        "setup_god_line_ask_gender": "性別？",
        "setup_profile_name_rule": "cjk_2_4",
        "setup_profile_genders": "男;女",
        "setup_god_line_transmigrate": "穿越",
        "setup_scene_neigong": "氣海長廊;hint",
        "setup_scene_martial": "試招石台;hint",
        "setup_scene_qinggong": "身法雲橋;hint",
        "setup_god_line_library": "圖書館",
    }
    offer_state: dict[str, str] = {}
    usr_ids = {
        "opening_offer_neigong": "USR74",
        "opening_offer_martial": "USR75",
        "opening_offer_qinggong": "USR76",
        "setup_god_ack": "USR98",
        "pc_name": "USR03",
        "pc_gender": "USR53",
        "opening_arts": "USR58",
    }

    def read_usr(_s, key):
        if key in offer_state:
            return offer_state[key]
        return state.get(key)

    def uid_for_key(_s, key):
        return usr_ids.get(key)

    def fake_ensure(session, key, *, initial="_", preferred_ids=()):
        if key not in usr_ids:
            usr_ids[key] = preferred_ids[0] if preferred_ids else "USR90"
        if key not in offer_state and key.startswith("opening_offer_"):
            offer_state[key] = "_"
        return usr_ids.get(key)

    def fake_update(session, lines):
        for ln in lines:
            if ln.startswith("@USR:"):
                parts = ln.split(":", 1)[1].strip().split("|")
                if len(parts) >= 3:
                    state[parts[1]] = parts[2]
                    if parts[1].startswith("opening_offer_"):
                        offer_state[parts[1]] = parts[2]
        return 0, []

    arts = [
        {"id": "ART01", "名稱": "太玄經", "門類": "綜合"},
        {"id": "ART02", "名稱": "獨孤九劍", "門類": "武學"},
        {"id": "ART04", "名稱": "凌波微步", "門類": "輕功"},
    ]

    with (
        patch("novel_mcp.player_profile.read_usr_by_key", side_effect=read_usr),
        patch("novel_mcp.opening_loadout.read_usr_by_key", side_effect=read_usr),
        patch("novel_mcp.player_setup.read_usr_by_key", side_effect=read_usr),
        patch("novel_mcp.setup_ack.read_usr_by_key", side_effect=read_usr),
        patch("novel_mcp.setup_profile_rules.read_usr_by_key", side_effect=read_usr),
        patch("novel_mcp.opening_loadout.usr_id_for_key", side_effect=uid_for_key),
        patch("novel_mcp.setup_ack.usr_id_for_key", side_effect=uid_for_key),
        patch("novel_mcp.setup_ack.ensure_usr_row", side_effect=fake_ensure),
        patch("novel_mcp.opening_loadout.ensure_usr_row", side_effect=fake_ensure),
        patch("novel_mcp.opening_loadout.graph_update", side_effect=fake_update),
        patch("novel_mcp.setup_ack.graph_update", side_effect=fake_update),
        patch("novel_mcp.opening_loadout.graph_update", side_effect=fake_update),
        patch("novel_mcp.opening_loadout.load_catalog_from_path", return_value=arts),
        patch("novel_mcp.opening_loadout.resolve_catalog_path"),
        patch("novel_mcp.player_setup.read_usr_record", return_value=None),
    ):
        from novel_mcp.catalog_schema import CatalogSchema
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        schema = CatalogSchema.load_json(
            root / "applications/novel_cursor/catalog_specs/wuxia_jinyong.json"
        )
        with patch("novel_mcp.player_setup.read_catalog_schema", return_value=schema), patch(
            "novel_mcp.opening_loadout.read_catalog_schema", return_value=schema
        ):
            yield state


def test_setup_flow_ten_steps() -> None:
    """Walk open → name → gender → pre_pick → 3 picks → transmigrate → play."""
    with _flow_patch() as state:
        s = "mn_flow"
        steps: list[str] = []

        g = read_player_setup(s)["setup_guidance"]
        steps.append(g["next_action"])
        assert g["next_action"] == "narrate_open"

        commit_setup_ack(s, "narrate_open")
        state["setup_god_ack"] = "narrate_open"
        steps.append(read_player_setup(s)["setup_guidance"]["next_action"])
        assert steps[-1] == "narrate_ask_name"

        state["pc_name"] = "北見硝"
        steps.append("commit_name")
        state["pc_gender"] = "男"
        steps.append("commit_gender")
        g = read_player_setup(s)["setup_guidance"]
        steps.append(g["next_action"])
        assert g["next_action"] == "narrate_pre_pick"

        commit_setup_ack(s, "narrate_pre_pick")
        state["setup_god_ack"] = "narrate_open;narrate_pre_pick"
        steps.append(read_player_setup(s)["setup_guidance"]["next_action"])
        assert steps[-1] == "pick_neigong"

        pool = [{"id": "ART01"}, {"id": "ART11"}]
        ids, errs = ensure_slot_offers(s, "neigong", pool, roll=True)
        assert not errs
        assert ids

        state["opening_arts"] = "ART01;未定;未定"
        steps.append(read_player_setup(s)["setup_guidance"]["next_action"])
        assert steps[-1] == "pick_martial"

        state["opening_arts"] = "ART01;ART02;未定"
        steps.append(read_player_setup(s)["setup_guidance"]["next_action"])
        assert steps[-1] == "pick_qinggong"

        state["opening_arts"] = "ART01;ART02;ART04"
        g = read_player_setup(s)["setup_guidance"]
        steps.append(g["next_action"])
        assert g["next_action"] == "narrate_transmigration"

        commit_setup_ack(s, "narrate_transmigration")
        state["setup_god_ack"] = "narrate_open;narrate_pre_pick;narrate_transmigration"
        g = read_player_setup(s)["setup_guidance"]
        steps.append(g["next_action"])
        assert g["next_action"] == "start_play"
        assert read_player_setup(s)["setup_complete"] is True

        assert len(steps) == 10
