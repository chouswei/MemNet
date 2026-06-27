"""Aggregate player setup state + chat guidance (next_action)."""

from __future__ import annotations

from typing import Any

from novel_mcp.opening_loadout import read_martial_catalog, read_opening_loadout
from novel_mcp.player_profile import read_profile
from novel_mcp.setup_constants import FORMAT_GOD_REALM, FORMAT_PLAY_BEAT, SENTINEL
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


def _build_setup_guidance(
    session: str | None,
    *,
    profile: dict[str, Any],
    loadout: dict[str, Any],
    setup_complete: bool,
) -> dict[str, Any]:
    tone_rec = read_usr_record(session, "USR63")
    tone = _parse_tone(tone_rec)

    if setup_complete:
        return {
            "phase": "ready",
            "next_action": "start_play",
            "format_god": FORMAT_GOD_REALM,
            "format_play": FORMAT_PLAY_BEAT,
            "tone": tone,
            "suggested_lines": [],
            "scene": None,
        }

    if not profile.get("complete"):
        return {
            "phase": "open",
            "next_action": "narrate_open",
            "format_god": FORMAT_GOD_REALM,
            "format_play": FORMAT_PLAY_BEAT,
            "tone": tone,
            "suggested_lines": _suggested_lines(
                session, ("setup_god_line_open", "setup_god_line_profile")
            ),
            "scene": None,
        }

    if loadout.get("complete"):
        return {
            "phase": "transmigrate",
            "next_action": "narrate_transmigration",
            "format_god": FORMAT_GOD_REALM,
            "format_play": FORMAT_PLAY_BEAT,
            "tone": tone,
            "suggested_lines": _suggested_lines(session, ("setup_god_line_transmigrate",)),
            "scene": None,
        }

    next_slot = loadout.get("next_slot")
    if next_slot == "neigong":
        scene = loadout.get("slots", {}).get("neigong", {}).get("scene")
        return {
            "phase": "library",
            "next_action": "narrate_library",
            "format_god": FORMAT_GOD_REALM,
            "format_play": FORMAT_PLAY_BEAT,
            "tone": tone,
            "suggested_lines": [],
            "scene": scene,
            "follow_up_action": "pick_neigong",
        }

    if next_slot in ("martial", "qinggong"):
        scene = loadout.get("slots", {}).get(next_slot, {}).get("scene")
        return {
            "phase": "picks",
            "next_action": f"pick_{next_slot}",
            "format_god": FORMAT_GOD_REALM,
            "format_play": FORMAT_PLAY_BEAT,
            "tone": tone,
            "suggested_lines": [],
            "scene": scene,
        }

    return {
        "phase": "picks",
        "next_action": "commit_opening_pick",
        "format_god": FORMAT_GOD_REALM,
        "format_play": FORMAT_PLAY_BEAT,
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

    if read_usr_by_key(session, "martial_catalog_md") is None:
        return {
            "exit_code": 2,
            "errors": ["missing_usr67_martial_catalog_md"],
            "profile": profile,
            "loadout": loadout,
            "setup_complete": False,
            "setup_guidance": {},
        }

    setup_complete = bool(profile.get("complete")) and bool(loadout.get("complete"))
    guidance = _build_setup_guidance(
        session,
        profile=profile,
        loadout=loadout,
        setup_complete=setup_complete,
    )

    return {
        "exit_code": 0,
        "profile": {
            "name": profile.get("name"),
            "gender": profile.get("gender"),
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
            "player_setup_incomplete: finish god-realm setup (profile + 3 martial picks) before first beat"
        ],
        "needs_player_setup": True,
        "player_setup": {
            "profile": {"complete": setup.get("profile", {}).get("complete", False)},
            "loadout": {"complete": setup.get("loadout", {}).get("complete", False)},
            "setup_complete": setup.get("setup_complete", False),
        },
    }
