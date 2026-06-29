"""Prompt builder smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from app_config import load_config  # noqa: E402
from beat_prompt import build_prose_turn, build_script_turn  # noqa: E402


def test_script_turn_includes_choice_text() -> None:
    cfg = load_config(app_id="shenjia_caifa")
    prep = {
        "memnet_session": "mn_x",
        "continuation_anchor": "風箱在旁呼哧作響。",
        "player": {"choice": 2, "choice_text": "你決定先查看石板紋路。"},
        "fsm": {"start_stage": "oln"},
    }
    text = build_script_turn(cfg, prep)
    assert "查看石板紋路" in text
    assert "do **not** restart" in text


def test_script_turn_includes_anchor() -> None:
    cfg = load_config(app_id="shenjia_caifa")
    prep = {
        "memnet_session": "mn_x",
        "continuation_anchor": "風箱在旁呼哧作響。",
        "player": {"choice": 1},
        "fsm": {"start_stage": "oln"},
    }
    text = build_script_turn(cfg, prep)
    assert "風箱在旁呼哧作響" in text
    assert "mn_x" in text


def test_prose_user_includes_cast_block() -> None:
    from beat_prompt import build_prose_user

    cfg = load_config(app_id="shenjia_caifa")
    prep = {"memnet_session": "mn_x", "continuation_anchor": ""}
    begin = {
        "pipeline": {"scr_row": "@SCR: SCR01|1|1|…"},
        "presentation": {
            "scene": {
                "ages": {"N01": 12, "P01": 10},
                "age_hint": "P01:10歲；N01:12歲",
                "npcs": [{"id": "N01", "name": "沈芯", "age": 12, "traits": "女、聰慧"}],
                "plr_age": 10,
                "plr_identity": "流民",
            }
        },
        "finish_params": {},
    }
    text = build_prose_user(prep, begin)
    assert "沈芯" in text
    assert "12歲" in text
    assert "## Cast" in text


def test_prose_turn_includes_scr() -> None:
    cfg = load_config(app_id="shenjia_caifa")
    prep = {
        "memnet_session": "mn_x",
        "continuation_anchor": "上一段。",
        "scr_row": "@SCR: SCR02|2|…",
        "oln_row": "@OLN: OLN02|2|…",
        "finish_params": {"snapshot_file": "novel-output/shenjia_caifa/session_snap.json"},
    }
    text = build_prose_turn(cfg, prep)
    assert "@SCR: SCR02" in text
    assert "上一段" in text


def test_prose_system_is_seed_agnostic() -> None:
    from beat_prompt import build_prose_system

    cfg = load_config(app_id="shenjia_caifa")
    text = build_prose_system(cfg)
    for term in ("魂穿", "靈魂圖書館", "武俠", "台灣", "意識圖書館", "金庸"):
        assert term not in text


def test_prose_user_surfaces_seed_contracts() -> None:
    from beat_prompt import build_prose_user

    cfg = load_config(app_id="shenjia_caifa")
    prep = {"memnet_session": "mn_x", "continuation_anchor": ""}
    begin = {
        "pipeline": {"scr_row": "@SCR: SCR01|1|1|…"},
        "presentation": {
            "contracts": ["Narrative voice: second person; wuxia"],
            "option_contracts": ["Option slot layout: 1-4 traits;5 ledger;6 library"],
            "scene": {},
        },
        "finish_params": {},
    }
    text = build_prose_user(prep, begin)
    assert "## Seed contracts" in text
    assert "second person" in text
    assert "## Option contracts" in text
    assert "6 library" in text
