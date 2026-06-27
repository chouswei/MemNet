"""Player beat context for dual-loop script + prose agents."""

from __future__ import annotations

from typing import Any

from memnet_mcp.client import run_memnet
from novel_mcp.beat_pipeline import beat_turn_begin
from novel_mcp.chapter_io import chapter_file_path, last_committed_paragraph
from novel_mcp.paths import workspace_root
from novel_mcp.player_setup import player_setup_gate_payload, read_player_setup
from novel_mcp.warm_index import index_warm, usr_value

_SCRIPT_STAGES = frozenset({"oln", "sbd", "scr"})


def read_beat_stage(session: str | None) -> str:
    """Return USR23 beat_stage (oln|sbd|scr|prose)."""
    resp = run_memnet(["read", "get", "--id", "USR23"], session=session)
    for line in resp.stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("@USR:"):
            continue
        parts = stripped.split(":", 1)[1].strip().split("|")
        if len(parts) >= 3 and parts[1] == "beat_stage":
            return parts[2]
    return "oln"


def _validate_player_input(
    *,
    choice: int | None,
    steering: str | None,
    continue_beat: bool,
) -> dict[str, Any] | None:
    if choice is not None and not (1 <= choice <= 6):
        return {"exit_code": 2, "errors": ["choice must be 1–6"]}
    modes = sum(
        1
        for x in (choice is not None, bool(steering), continue_beat)
        if x
    )
    if modes > 1:
        return {"exit_code": 2, "errors": ["use only one of choice, steering, continue_beat"]}
    return None


def _common_paths(
    *,
    session: str,
    begin: dict[str, Any],
    snapshot_file: str | None,
    chapter_dir: str | None,
    workspace_root_path: str | None,
) -> dict[str, Any]:
    pipeline = begin.get("pipeline") or {}
    finish_params = begin.get("finish_params") or {}
    root = workspace_root(workspace_root_path)
    ch_dir = chapter_dir or pipeline.get("chapter_dir") or finish_params.get("chapter_dir")
    chp_num = pipeline.get("chp_num") or finish_params.get("chp_num") or 1
    snap = snapshot_file or pipeline.get("snapshot_file") or finish_params.get("snapshot_file")
    anchor = ""
    if ch_dir and chp_num:
        path = chapter_file_path(root, ch_dir, int(chp_num))
        anchor = last_committed_paragraph(path)
    return {
        "chapter_dir": ch_dir,
        "chp_num": chp_num,
        "snapshot_file": snap,
        "continuation_anchor": anchor,
        "finish_params": finish_params,
    }


def _play_blocked_by_setup(
    session: str,
    *,
    choice: int | None,
    steering: str | None,
    continue_beat: bool,
    workspace_root_path: str | None = None,
) -> dict[str, Any] | None:
    if not (choice is not None or steering or continue_beat):
        return None
    setup = read_player_setup(session, workspace_root_path=workspace_root_path)
    if setup.get("setup_complete"):
        return None
    return player_setup_gate_payload(session, workspace_root_path=workspace_root_path)


def script_beat_prepare(
    *,
    session: str,
    choice: int | None = None,
    steering: str | None = None,
    continue_beat: bool = False,
    snapshot_file: str | None = None,
    chapter_dir: str | None = None,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    """Bundle context for script agent (oln → sbd → scr)."""
    err = _validate_player_input(
        choice=choice, steering=steering, continue_beat=continue_beat
    )
    if err:
        return err

    blocked = _play_blocked_by_setup(
        session,
        choice=choice,
        steering=steering,
        continue_beat=continue_beat,
        workspace_root_path=workspace_root_path,
    )
    if blocked:
        return blocked

    beat_stage = read_beat_stage(session)

    if continue_beat and beat_stage == "oln":
        return {
            "exit_code": 2,
            "errors": ["beat_stage already oln; pass choice instead of continue_beat"],
        }
    if continue_beat and beat_stage == "prose":
        return {
            "exit_code": 2,
            "errors": ["beat_stage is prose; use prose_beat_prepare or --prose-only"],
        }
    if not continue_beat and beat_stage in _SCRIPT_STAGES and choice is None and not steering:
        pass  # allow choice on next call; stage may be mid-script from crash

    if beat_stage == "prose" and (choice is not None or steering):
        return {
            "exit_code": 2,
            "errors": ["beat_stage is prose; use --prose-only or finish prose first"],
        }

    lib_query = choice == 6
    begin = beat_turn_begin(
        session=session,
        include_warm=True,
        lib_query=lib_query,
    )
    paths = _common_paths(
        session=session,
        begin=begin,
        snapshot_file=snapshot_file,
        chapter_dir=chapter_dir,
        workspace_root_path=workspace_root_path,
    )

    player: dict[str, Any] = {}
    if choice is not None:
        player["choice"] = choice
        player["lib_query"] = lib_query
    elif steering:
        player["steering"] = steering
    elif continue_beat:
        player["continue_beat"] = True

    start_stage = beat_stage if beat_stage in _SCRIPT_STAGES else "oln"

    player_setup = read_player_setup(session, workspace_root_path=workspace_root_path)

    return {
        "exit_code": 0,
        "phase": "script",
        "memnet_session": session,
        "beat_stage": beat_stage,
        "player": player,
        "begin": begin,
        "player_setup": player_setup,
        **paths,
        "fsm": {
            "stages": ["oln", "sbd", "scr"],
            "max_pairs": 3,
            "start_stage": start_stage,
        },
    }


def prose_beat_prepare(
    *,
    session: str,
    snapshot_file: str | None = None,
    chapter_dir: str | None = None,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    """Bundle context for prose agent; requires USR23 beat_stage=prose."""
    setup = read_player_setup(session, workspace_root_path=workspace_root_path)
    if not setup.get("setup_complete"):
        return player_setup_gate_payload(session, workspace_root_path=workspace_root_path)

    beat_stage = read_beat_stage(session)
    if beat_stage != "prose":
        return {
            "exit_code": 2,
            "errors": ["handoff: USR23 must be prose"],
        }

    begin = beat_turn_begin(session=session, include_warm=True)
    pipeline = begin.get("pipeline") or {}
    paths = _common_paths(
        session=session,
        begin=begin,
        snapshot_file=snapshot_file,
        chapter_dir=chapter_dir,
        workspace_root_path=workspace_root_path,
    )

    return {
        "exit_code": 0,
        "phase": "prose",
        "memnet_session": session,
        "beat_stage": "prose",
        "scr_row": pipeline.get("scr_row"),
        "oln_row": pipeline.get("oln_row"),
        "begin": begin,
        **paths,
        "fsm": {
            "stages": ["prose"],
            "max_pairs": 1,
        },
    }


def player_beat_prepare(
    *,
    session: str,
    choice: int | None = None,
    steering: str | None = None,
    continue_beat: bool = False,
    snapshot_file: str | None = None,
    chapter_dir: str | None = None,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    """Deprecated: alias for script_beat_prepare."""
    return script_beat_prepare(
        session=session,
        choice=choice,
        steering=steering,
        continue_beat=continue_beat,
        snapshot_file=snapshot_file,
        chapter_dir=chapter_dir,
        workspace_root_path=workspace_root_path,
    )
