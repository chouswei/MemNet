"""Aggregate player setup state + chat guidance (next_action)."""

from __future__ import annotations

from typing import Any

from novel_mcp.catalog_schema import read_catalog_schema, slot_order
from novel_mcp.opening_loadout import read_opening_catalog, read_opening_loadout
from novel_mcp.player_profile import read_profile
from novel_mcp.setup_constants import (
    FORMAT_GOD_REALM,
    FORMAT_PLAY_BEAT,
    OPENING_CATALOG_MD_KEY,
    SETUP_FORMAT_GOD_KEY,
    SETUP_FORMAT_PLAY_KEY,
    SETUP_GOD_LINE_ASK_GENDER,
    SETUP_GOD_LINE_ASK_NAME,
    SETUP_GOD_LINE_OPEN,
    SETUP_GOD_LINE_PROFILE,
    SETUP_GOD_LINE_TRANSMIGRATE,
    SETUP_PROFILE_GENDERS_KEY,
    SENTINEL,
)
from novel_mcp.setup_ack import is_setup_acked
from novel_mcp.setup_graph import read_usr_by_key, read_usr_record


def _parse_tone(usr63: list[str] | None) -> dict[str, list[str]]:
    if not usr63 or len(usr63) < 3:
        return {"tokens": [], "ban": []}
    raw = usr63[2]
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    if parts and parts[0] == "god_banter":
        parts = parts[1:]
    tokens: list[str] = []
    ban: list[str] = []
    for part in parts:
        if part.startswith("禁"):
            ban.append(part[1:])
        else:
            tokens.append(part)
    return {"tokens": tokens, "ban": ban}


def _suggested_lines(session: str | None, keys: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    for key in keys:
        resp = read_usr_by_key(session, key)
        if resp and resp != SENTINEL:
            lines.append(resp)
    return lines


def _read_format(session: str | None, key: str, default: str) -> str:
    val = read_usr_by_key(session, key)
    if val and val != SENTINEL:
        return val
    return default


def _ask_name_line(session: str | None) -> str | None:
    line = read_usr_by_key(session, SETUP_GOD_LINE_ASK_NAME)
    if line and line != SENTINEL:
        return line
    return read_usr_by_key(session, SETUP_GOD_LINE_PROFILE)


def _setup_line(session: str | None, key: str) -> str | None:
    val = read_usr_by_key(session, key)
    if val and val != SENTINEL:
        return val
    return None


def _profile_genders(session: str | None) -> list[str]:
    raw = read_usr_by_key(session, SETUP_PROFILE_GENDERS_KEY)
    if not raw or raw == SENTINEL:
        return ["男", "女"]
    return [p.strip() for p in raw.split(";") if p.strip()]


def _build_setup_guidance(
    session: str | None,
    *,
    profile: dict[str, Any],
    loadout: dict[str, Any],
    setup_complete: bool,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    tone_rec = read_usr_record(session, "USR63")
    tone = _parse_tone(tone_rec)
    fmt_god = _read_format(session, SETUP_FORMAT_GOD_KEY, FORMAT_GOD_REALM)
    fmt_play = _read_format(session, SETUP_FORMAT_PLAY_KEY, FORMAT_PLAY_BEAT)

    if (
        bool(profile.get("complete"))
        and bool(loadout.get("complete"))
        and not is_setup_acked(session, "narrate_transmigration")
    ):
        return {
            "phase": "transmigrate",
            "next_action": "narrate_transmigration",
            "format_god": fmt_god,
            "format_play": fmt_play,
            "tone": tone,
            "suggested_lines": _suggested_lines(
                session, (SETUP_GOD_LINE_TRANSMIGRATE,)
            ),
            "scene": None,
            "follow_up_action": "start_play",
        }

    if setup_complete:
        return {
            "phase": "ready",
            "next_action": "start_play",
            "format_god": fmt_god,
            "format_play": fmt_play,
            "tone": tone,
            "suggested_lines": [],
            "scene": None,
        }

    if not profile.get("complete"):
        name_set = bool(profile.get("name_set"))
        gender_set = bool(profile.get("gender_set"))
        if not name_set and not gender_set:
            if not is_setup_acked(session, "narrate_open"):
                ask = _ask_name_line(session)
                follow_up: list[str] = [ask] if ask and ask != SENTINEL else []
                return {
                    "phase": "open",
                    "next_action": "narrate_open",
                    "format_god": fmt_god,
                    "format_play": fmt_play,
                    "tone": tone,
                    "suggested_lines": _suggested_lines(
                        session, (SETUP_GOD_LINE_OPEN,)
                    ),
                    "scene": None,
                    "follow_up_action": "narrate_ask_name",
                    "follow_up_lines": follow_up,
                }
            ask = _ask_name_line(session)
            open_lines = _suggested_lines(session, (SETUP_GOD_LINE_OPEN,))
            ask_lines = [ask] if ask and ask != SENTINEL else []
            return {
                "phase": "ask_name",
                "next_action": "narrate_ask_name",
                "format_god": fmt_god,
                "format_play": fmt_play,
                "tone": tone,
                "suggested_lines": open_lines + ask_lines,
                "scene": None,
                "follow_up_action": "commit_player_profile",
            }
        if not name_set:
            ask = _ask_name_line(session)
            return {
                "phase": "ask_name",
                "next_action": "narrate_ask_name",
                "format_god": fmt_god,
                "format_play": fmt_play,
                "tone": tone,
                "suggested_lines": [ask] if ask and ask != SENTINEL else [],
                "scene": None,
                "follow_up_action": "commit_player_profile",
            }
        if not gender_set:
            return {
                "phase": "ask_gender",
                "next_action": "narrate_ask_gender",
                "format_god": fmt_god,
                "format_play": fmt_play,
                "tone": tone,
                "suggested_lines": _suggested_lines(
                    session, (SETUP_GOD_LINE_ASK_GENDER,)
                ),
                "scene": None,
                "genders": _profile_genders(session),
                "follow_up_action": "commit_player_profile",
            }
        return {
            "phase": "profile_fix",
            "next_action": "commit_player_profile",
            "format_god": fmt_god,
            "format_play": fmt_play,
            "tone": tone,
            "suggested_lines": [],
            "scene": None,
            "profile_errors": profile.get("errors", []),
        }

    next_slot = loadout.get("next_slot")
    schema = read_catalog_schema(session, workspace_root_path=workspace_root_path)
    order = slot_order(schema) if schema else ()
    first_slot = order[0] if order else None

    pre_pick_key = schema.loadout.pre_pick_line_usr_key if schema else None
    pre_pick_line = _setup_line(session, pre_pick_key) if pre_pick_key else None

    if (
        next_slot
        and first_slot
        and next_slot == first_slot
        and pre_pick_line
        and not is_setup_acked(session, "narrate_pre_pick")
    ):
        scene = loadout.get("slots", {}).get(first_slot, {}).get("scene")
        return {
            "phase": "pre_pick",
            "next_action": "narrate_pre_pick",
            "format_god": fmt_god,
            "format_play": fmt_play,
            "tone": tone,
            "suggested_lines": [pre_pick_line],
            "scene": scene,
            "follow_up_action": f"pick_{first_slot}",
        }

    if next_slot:
        scene = loadout.get("slots", {}).get(next_slot, {}).get("scene")
        return {
            "phase": "picks",
            "next_action": f"pick_{next_slot}",
            "format_god": fmt_god,
            "format_play": fmt_play,
            "tone": tone,
            "suggested_lines": [],
            "scene": scene,
        }

    return {
        "phase": "picks",
        "next_action": "commit_opening_pick",
        "format_god": fmt_god,
        "format_play": fmt_play,
        "tone": tone,
        "suggested_lines": [],
        "scene": None,
    }


def read_player_setup(
    session: str | None,
    *,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    profile = read_profile(session)
    loadout = read_opening_loadout(session, workspace_root_path=workspace_root_path)

    if read_usr_by_key(session, OPENING_CATALOG_MD_KEY) is None:
        return {
            "exit_code": 2,
            "errors": ["missing_opening_catalog_md_usr"],
            "profile": profile,
            "loadout": loadout,
            "setup_complete": False,
            "setup_guidance": {},
        }

    setup_complete = (
        bool(profile.get("complete"))
        and bool(loadout.get("complete"))
        and is_setup_acked(session, "narrate_transmigration")
    )
    guidance = _build_setup_guidance(
        session,
        profile=profile,
        loadout=loadout,
        setup_complete=setup_complete,
        workspace_root_path=workspace_root_path,
    )

    return {
        "exit_code": 0,
        "profile": {
            "name": profile.get("name"),
            "gender": profile.get("gender"),
            "name_set": profile.get("name_set"),
            "gender_set": profile.get("gender_set"),
            "complete": profile.get("complete"),
            "errors": profile.get("errors", []),
        },
        "loadout": loadout,
        "setup_complete": setup_complete,
        "setup_guidance": guidance,
        "errors": [],
    }


def player_setup_gate_payload(session: str | None, *, workspace_root_path: str | None = None) -> dict[str, Any]:
    """Minimal payload for play_context when setup incomplete."""
    setup = read_player_setup(session, workspace_root_path=workspace_root_path)
    return {
        "exit_code": 2,
        "errors": [
            "player_setup_incomplete: finish god-realm setup (profile + opening catalog picks) before first beat"
        ],
        "needs_player_setup": True,
        "player_setup": {
            "profile": {"complete": setup.get("profile", {}).get("complete", False)},
            "loadout": {"complete": setup.get("loadout", {}).get("complete", False)},
            "setup_complete": setup.get("setup_complete", False),
        },
    }
