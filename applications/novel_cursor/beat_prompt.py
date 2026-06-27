"""Prompts for dual-loop script + prose Cursor SDK agents."""

from __future__ import annotations

from typing import Any

from app_config import MODEL, NovelAppConfig


def build_script_primer(config: NovelAppConfig) -> str:
    return f"""You are the **{config.title}** script agent (編劇). Model: {MODEL}.

Role: run LAW-PIPE20 **script stages only** — `oln → sbd → scr`. **No** player-facing novel prose.

Rules:
1. Always pass `session` on every `beat_turn_begin` / `beat_turn_finish`.
2. One wire type per finish (`no_bundle`): oln_lines, sbd_lines, or scr_lines only.
3. Max 6 novel-writer calls (3 begin+finish pairs) per turn.
4. Honour `continuation_anchor` and warm context; do not invent unrelated plot (no 錦衣衛/滅門 unless in graph).
5. Choice 6 (library): encode query in **OLN only** per LAW-LIB03 — same scene, consciousness frame.
6. Never output `@TAG:` wires to the player.

SSOT seed: `{config.seed_md_rel}`.

Acknowledge with "script agent ready".
"""


def build_script_turn(config: NovelAppConfig, prep: dict[str, Any]) -> str:
    session = prep["memnet_session"]
    anchor = prep.get("continuation_anchor") or ""
    player = prep.get("player") or {}
    start = prep.get("fsm", {}).get("start_stage", "oln")

    if "choice" in player:
        player_block = (
            f"Player chose option **{player['choice']}**. "
            f"Start from stage `{start}`; run until USR23 beat_stage becomes **prose**."
        )
        if player.get("lib_query"):
            player_block += " Library query: reflect in OLN only (LAW-LIB03)."
    elif "steering" in player:
        player_block = (
            f'Player steering: "{player["steering"]}". '
            f"Start from `{start}`; run until beat_stage **prose**."
        )
    else:
        player_block = (
            f"Resume script pipeline from stage `{start}`; run until beat_stage **prose**."
        )

    anchor_block = (
        f"## Continuation anchor (committed prose — continue from here)\n{anchor}"
        if anchor
        else "## Continuation anchor\n(empty — opening beat)"
    )

    return f"""Session: `{session}`

{anchor_block}

## Task
{player_block}

Run beat_turn_begin → draft current stage only → beat_turn_finish (one wire).
Repeat until `USR23|beat_stage|prose`.

Do not write novel prose. Do not call prose finish.
"""


def build_prose_primer(config: NovelAppConfig) -> str:
    snap = str(config.snapshot_file.relative_to(config.output_dir.parent.parent)).replace(
        "\\", "/"
    )
    try:
        from app_config import repo_root

        snap = str(config.snapshot_file.relative_to(repo_root())).replace("\\", "/")
    except ValueError:
        pass

    return f"""You are the **{config.title}** prose agent (作者). Model: {MODEL}.

Role: **prose stage only** — expand committed `@SCR` into novel text per LAW-PROSE16.

Rules:
1. Always pass `session` on beat_turn_begin and beat_turn_finish.
2. One prose finish: prose + option_lines (6) + update_lines + snapshot_file.
3. Do not modify OLN/SBD/SCR in this turn.
4. Honour continuation_anchor and scr_row; stay in current scene.
5. After success, emit **only** fenced JSON (see schema below).

Snapshot path: `{snap}`

JSON schema:
```json
{{
  "exit_code": 0,
  "session": "<mn_…>",
  "app_id": "{config.app_id}",
  "prose": "<正文>",
  "options": ["…", "…", "…", "…", "…", "…"],
  "hud": "<狀態欄>",
  "snapshot_saved": true,
  "snapshot_file": "{snap}",
  "beat_stage": "oln"
}}
```

Acknowledge with "prose agent ready".
"""


def build_prose_turn(config: NovelAppConfig, prep: dict[str, Any]) -> str:
    session = prep["memnet_session"]
    anchor = prep.get("continuation_anchor") or ""
    scr = prep.get("scr_row") or "(read from beat_turn_begin presentation)"
    oln = prep.get("oln_row") or ""
    fp = prep.get("finish_params") or {}
    snap = fp.get("snapshot_file") or prep.get("snapshot_file") or ""

    return f"""Session: `{session}`

## Continuation anchor
{anchor or "(none)"}

## Current OLN
{oln}

## Current SCR (expand this)
{scr}

## finish_params
snapshot_file: `{snap}`
chapter_dir: `{fp.get("chapter_dir", prep.get("chapter_dir", ""))}`
chp_num: {fp.get("chp_num", prep.get("chp_num", 1))}

## Task
beat_turn_begin → write prose from SCR → beat_turn_finish with prose, 6 option_lines, updates, snapshot.

Emit only the success JSON block when done.
"""
