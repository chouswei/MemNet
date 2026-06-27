"""Novel beat orchestration — warm read + atomic prose/chapter/graph commit in-process."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from memnet_mcp.client import MemNetResponse, run_memnet
from novel_mcp.presentation import compile_presentation
from novel_mcp.session_contract import session_contract_block
from novel_mcp.session_meta import fetch_session_modified
from novel_mcp.validators import validate_option_lines
from novel_mcp.warm_walk import fetch_warm_walk
from novel_mcp.chapter_io import chapter_prose_gate
from novel_mcp.game_time import (
    check_sys_time_update,
    parse_game_time,
    sys_time_field_from_wire,
    year_from_sys_time,
)
from novel_mcp.time_display import format_time_display
from novel_mcp.paths import workspace_root as resolve_workspace_root
from novel_mcp.warm_index import index_warm, pipeline_no_bundle
from novel_mcp.zh_text import parse_scene_band, prose_status

_ROW_RE = re.compile(r"^@(\w+):\s*(.+)$")
_QI_ZERO_RE = re.compile(r"氣血:0(?:/|;|$)")

_PHASE_ACTIONS: dict[int, str] = {
    1: "draft @OLN (大綱) → advance to 分鏡",
    2: "draft @SBD (分鏡) → advance to 腳本",
    3: "draft @SCR (腳本) → draft final prose ~draft_target_chars",
    4: "beat_turn_finish(prose + persist)",
    5: "beat_turn_finish(prose + persist + snapshot)",
    6: "present + options (no MCP)",
}

_PIPELINE_STAGES = ("oln", "sbd", "scr", "prose")
_STAGE_NEXT = {"oln": "sbd", "sbd": "scr", "scr": "prose", "prose": "oln"}

_STAGE_DRAFT_NOTES: dict[str, str] = {
    "oln": "LAW-PIPE20: draft @OLN; beat_turn_finish(oln_lines=… only)",
    "sbd": "LAW-PIPE20: draft @SBD from @OLN; beat_turn_finish(sbd_lines=… only)",
    "scr": "LAW-PIPE20: draft @SCR from @SBD; beat_turn_finish(scr_lines=… only)",
    "prose": (
        "LAW-PIPE20: draft prose from @SCR; "
        "beat_turn_finish(prose=…, option_lines, STEP/SYS/PLR updates)"
    ),
}


def _pipeline_provided(
    oln_lines: list[str] | None,
    sbd_lines: list[str] | None,
    scr_lines: list[str] | None,
    prose: str | None,
) -> dict[str, bool]:
    return {
        "oln": bool(oln_lines),
        "sbd": bool(sbd_lines),
        "scr": bool(scr_lines),
        "prose": prose is not None,
    }


def _validate_pipeline_commits(
    beat_stage: str,
    provided: dict[str, bool],
    *,
    auto_beat: bool,
    pipeline_bypass: bool,
    no_bundle: bool = False,
) -> list[str]:
    if pipeline_bypass:
        return []
    if beat_stage not in _PIPELINE_STAGES:
        beat_stage = "oln"

    if auto_beat:
        if provided["oln"] or provided["sbd"] or provided["scr"]:
            return ["@ERR: auto_beat_pipeline|昏厥拍禁 OLN/SBD/SCR；僅 prose + PLR update"]
        return []

    active = [s for s in _PIPELINE_STAGES if provided[s]]
    if not active:
        return []

    if no_bundle and len(active) > 1:
        return [
            "@ERR: pipeline_no_bundle|"
            f"beat_stage={beat_stage} USR23 FSM: one wire stage per finish "
            f"(got {','.join(active)})"
        ]

    idx = _PIPELINE_STAGES.index(beat_stage)
    remaining = _PIPELINE_STAGES[idx:]
    expected = list(remaining[: len(active)])
    if active != expected:
        return [
            "@ERR: pipeline_stage_mismatch|"
            f"stage={beat_stage} got={','.join(active)} "
            f"expected contiguous from {beat_stage} as {','.join(remaining)}"
        ]
    return []


def _stage_after_commits(beat_stage: str, provided: dict[str, bool]) -> str:
    active = [s for s in _PIPELINE_STAGES if provided[s]]
    if not active:
        return beat_stage
    last = active[-1]
    if last == "prose":
        return "oln"
    return _STAGE_NEXT[last]


def _ensure_beat_stage_update(
    update_lines: list[str] | None,
    new_stage: str,
    beat_stage_usr_id: str | None = None,
) -> list[str]:
    lines = list(update_lines or [])
    if beat_stage_usr_id:
        lines = [
            ln
            for ln in lines
            if not (
                ln.strip().startswith("@USR:")
                and ln.split("|", 2)[1:2] == [beat_stage_usr_id]
                and "|beat_stage|" in ln
            )
        ]
        lines.append(f"@USR: {beat_stage_usr_id}|beat_stage|{new_stage}|persistent")
    else:
        lines = [
            ln
            for ln in lines
            if not (ln.strip().startswith("@USR:") and "|beat_stage|" in ln)
        ]
        lines.append(f"@USR: USR23|beat_stage|{new_stage}|persistent")
    return lines


def _usr_value_from_rows(rows: dict[str, list[str]], uid: str) -> str | None:
    for body in rows.get("USR", []):
        parts = body.split("|")
        if len(parts) >= 3 and parts[0] == uid:
            return parts[2]
    return None


def _parse_prose_target_value(value: str) -> int | None:
    val = value.replace("_advisory", "")
    if val.endswith("_zh"):
        try:
            return int(val[:-3])
        except ValueError:
            return None
    return None


def _supplement_prose_target(
    pipeline: dict[str, Any],
    *,
    session: str | None,
    warm_stdout: str | None = None,
) -> None:
    """Fetch prose_target USR when missing from truncated warm."""
    if pipeline.get("draft_target_chars") is not None:
        return
    if warm_stdout:
        from novel_mcp.warm_index import index_warm, usr_value

        idx = index_warm(warm_stdout)
        for key in ("prose_target", "prose_draft"):
            val = usr_value(idx, key)
            if val:
                target = _parse_prose_target_value(val)
                if target is not None:
                    pipeline["draft_target_chars"] = target
                    pipeline["prose_advisory_zh"] = target
                    return
    resp = run_memnet(
        [
            "query",
            "warm",
            "--anchor",
            "STEP01",
            "--depth",
            "1",
            "--max-rows",
            "30",
        ],
        session=session,
    )
    extra = parse_warm_stdout(resp.stdout)
    target = extra.get("draft_target_chars")
    if target is not None:
        pipeline["draft_target_chars"] = target
        pipeline["prose_advisory_zh"] = target


_STAGE_HINT_USR: dict[str, str] = {
    "oln": "USR54",
    "sbd": "USR55",
    "scr": "USR56",
    "prose": "USR57",
}


def _wire_lines_from_read(resp: MemNetResponse) -> list[str]:
    if resp.exit_code != 0 or not resp.stdout:
        return []
    return [
        ln.strip()
        for ln in resp.stdout.splitlines()
        if ln.strip().startswith("@")
    ]


def _read_get_body(session: str | None, record_id: str) -> str | None:
    """Return wire body (after @TAG:) for a single record id."""
    if not session:
        return None
    resp = run_memnet(["read", "get", "--id", record_id], session=session)
    for line in _wire_lines_from_read(resp):
        if line.startswith("@") and ":" in line:
            return line.split(":", 1)[1].strip()
    return None


def _apply_authoritative_beat_stage(
    pipeline: dict[str, Any],
    *,
    session: str | None,
) -> None:
    """USR23 read_get is authoritative; warm context may be truncated or stale."""
    body = _read_get_body(session, "USR23")
    if not body:
        return
    parts = body.split("|")
    if len(parts) >= 3 and parts[0] == "USR23" and parts[1] == "beat_stage":
        stage = parts[2]
        if stage in _PIPELINE_STAGES:
            pipeline["beat_stage"] = stage
            pipeline["beat_stage_usr_id"] = "USR23"


def _supplement_pipeline_fsm(
    pipeline: dict[str, Any],
    *,
    session: str | None,
    warm_stdout: str,
) -> str:
    """Fetch FSM USR/LAW rows from store when warm is truncated or stale."""
    if not session:
        return ""
    from novel_mcp.warm_index import index_warm, pipeline_no_bundle, usr_value

    idx = index_warm(warm_stdout)
    extras: list[str] = []

    law_body = _read_get_body(session, "LAW-PIPE20")
    if law_body:
        extras.append(f"@LAW: {law_body}")

    usr_body = _read_get_body(session, "USR23")
    if usr_body:
        extras.append(f"@USR: {usr_body}")

    _apply_authoritative_beat_stage(pipeline, session=session)
    stage = pipeline.get("beat_stage", "oln")

    hint_key = f"stage_hint_{stage}"
    if not usr_value(idx, hint_key):
        uid = _STAGE_HINT_USR.get(stage)
        if uid:
            hint_body = _read_get_body(session, uid)
            if hint_body:
                extras.append(f"@USR: {hint_body}")

    if not extras:
        return ""

    merged = warm_stdout + "\n" + "\n".join(extras)
    pipeline["pipeline_no_bundle"] = pipeline_no_bundle(index_warm(merged))
    return "\n".join(extras)


def _sys_time_field(rows: dict[str, list[str]]) -> str | None:
    for body in rows.get("SYS", []):
        parts = body.split("|")
        if len(parts) >= 3:
            return parts[2]
    return None


def _sys_year_from_rows(rows: dict[str, list[str]]) -> int | None:
    raw = _sys_time_field(rows)
    if raw is None:
        return None
    return year_from_sys_time(raw)


def _plr_qi_zero_collapsed(rows: dict[str, list[str]]) -> bool:
    """True when PLR body state is unconscious (LAW-VIT03 auto_beat, no options)."""
    for body in rows.get("PLR", []):
        parts = body.split("|")
        if len(parts) < 7:
            continue
        state = parts[6]
        if "昏厥:是" in state or _QI_ZERO_RE.search(state):
            return True
    return False


def _character_ages_from_rows(rows: dict[str, list[str]]) -> dict[str, int]:
    """Age = SYS01 calendar year minus PLR/NPC 出生年."""
    year = _sys_year_from_rows(rows)
    if year is None:
        return {}
    ages: dict[str, int] = {}
    for tag in ("PLR", "NPC"):
        for body in rows.get(tag, []):
            parts = body.split("|")
            if len(parts) >= 3 and parts[2].isdigit():
                ages[parts[0]] = year - int(parts[2])
    return ages


def parse_warm_stdout(stdout: str) -> dict[str, Any]:
    """Extract pipeline fields from query warm stdout wire lines."""
    rows: dict[str, list[str]] = {}
    for line in stdout.splitlines():
        stripped = line.strip()
        m = _ROW_RE.match(stripped)
        if not m:
            continue
        tag, body = m.group(1), m.group(2)
        rows.setdefault(tag, []).append(body)

    pipeline: dict[str, Any] = {}

    for body in rows.get("STEP", []):
        parts = body.split("|")
        if parts[0] == "STEP01" and len(parts) >= 3:
            pipeline["step_n"] = int(parts[1]) if parts[1].isdigit() else parts[1]
            pipeline["step_focus"] = parts[2]

    for body in rows.get("USR", []):
        parts = body.split("|")
        if len(parts) < 3:
            continue
        uid, key, value = parts[0], parts[1], parts[2]
        if key == "scene_length":
            pipeline["usr05_band"] = value
            if "_" in value and value.endswith("_zh"):
                try:
                    mn, mx = parse_scene_band(value)
                    pipeline["min_chars"] = mn
                    pipeline["max_chars"] = mx
                    pipeline["target_chars"] = (mn + mx) // 2
                except ValueError:
                    pass
            else:
                pipeline["min_chars"] = None
                pipeline["max_chars"] = None
                pipeline["target_chars"] = None
        if key in ("prose_target", "prose_draft"):
            target = _parse_prose_target_value(value)
            if target is not None:
                pipeline["draft_target_chars"] = target
                pipeline["prose_advisory_zh"] = target
        if key == "chapter_out":
            pipeline["chapter_dir"] = value
        if key == "snapshot":
            pipeline["snapshot_file"] = value
        if key == "local_gate":
            pipeline["local_gate"] = value
        if key == "gate_retry":
            pipeline["gate_retry"] = value
        if key == "beat_stage":
            # Prefer USR23 when warm carries multiple beat_stage rows.
            prev_uid = pipeline.get("beat_stage_usr_id")
            if prev_uid != "USR23" or uid == "USR23":
                pipeline["beat_stage"] = value
                pipeline["beat_stage_usr_id"] = uid

    for body in rows.get("CHP", []):
        parts = body.split("|")
        if len(parts) >= 6 and parts[-1] == "open":
            pipeline["chp_num"] = int(parts[1])

    if "draft_target_chars" not in pipeline and "target_chars" in pipeline:
        pipeline["draft_target_chars"] = pipeline["target_chars"]

    # Normalize stage
    stage = pipeline.get("beat_stage", "oln")
    if stage not in ("oln", "sbd", "scr", "prose"):
        stage = "oln"
    pipeline["beat_stage"] = stage

    focus = pipeline.get("step_focus")
    if isinstance(focus, str):
        if focus.startswith("OLN"):
            for body in rows.get("OLN", []):
                if body.startswith(focus + "|"):
                    pipeline["oln_row"] = body
                    break
        elif focus.startswith("SBD"):
            for body in rows.get("SBD", []):
                if body.startswith(focus + "|"):
                    pipeline["sbd_row"] = body
                    break
        elif focus.startswith("SCR"):
            for body in rows.get("SCR", []):
                if body.startswith(focus + "|"):
                    pipeline["scr_row"] = body
                    break

    # Default stage if not set
    if "beat_stage" not in pipeline:
        if "oln_row" in pipeline:
            pipeline["beat_stage"] = "oln"
        else:
            pipeline["beat_stage"] = "oln"  # start with 大綱

    ages = _character_ages_from_rows(rows)
    if ages:
        pipeline["character_ages"] = ages
        pipeline["sys_year"] = _sys_year_from_rows(rows)
        pipeline["age_hint"] = "；".join(
            f"{cid}:{v}歲" for cid, v in sorted(ages.items())
        )

    raw_time = _sys_time_field(rows)
    if raw_time:
        pipeline["sys_time_raw"] = raw_time
        gt = parse_game_time(raw_time)
        if gt:
            pipeline["game_time"] = gt.to_canonical()
            usr43 = _usr_value_from_rows(rows, "USR43")
            pipeline["time_display"] = format_time_display(gt, usr43)

    if _plr_qi_zero_collapsed(rows):
        pipeline["auto_beat"] = True
        pipeline["no_options"] = True

    for body in rows.get("PLR", []):
        parts = body.split("|")
        if len(parts) >= 7:
            pipeline["plr_body"] = parts[6]
            break

    pipeline["pipeline_no_bundle"] = pipeline_no_bundle(index_warm(stdout))

    return pipeline


def pipeline_next_action(
    step_n: int | str | None,
    beat_stage: str | None = None,
    *,
    pipeline_no_bundle: bool = False,
) -> str:
    stage = beat_stage if beat_stage in _PIPELINE_STAGES else "oln"
    if pipeline_no_bundle:
        return _STAGE_DRAFT_NOTES[stage]
    if stage in ("sbd", "scr", "prose"):
        return _STAGE_DRAFT_NOTES[stage]
    if isinstance(step_n, str) and step_n.isdigit():
        step_n = int(step_n)
    if isinstance(step_n, int):
        return _PHASE_ACTIONS.get(step_n, "beat_turn_begin → draft → beat_turn_finish")
    return _STAGE_DRAFT_NOTES["oln"]


def _apply_wire_lines(
    lines: list[str],
    *,
    mode: str,
    session: str | None,
    allow_new_relation: bool,
) -> MemNetResponse:
    if not lines:
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])
    argv = [mode, "--stdin"]
    if allow_new_relation:
        argv.append("--allow-new-relation")
    return run_memnet(argv, stdin="\n".join(lines), session=session)


def _prose_gate_active(pipeline: dict[str, Any]) -> bool:
    return pipeline.get("min_chars") is not None and pipeline.get("max_chars") is not None


def _warm_pipeline(session: str | None) -> dict[str, Any]:
    """Lightweight warm read for USR14/CHP paths (internal to beat_turn_finish)."""
    resp = run_memnet(
        ["query", "warm", "--anchor", "STEP01", "--depth", "1", "--max-rows", "40"],
        session=session,
    )
    pipeline = parse_warm_stdout(resp.stdout)
    _supplement_prose_target(pipeline, session=session)
    _apply_authoritative_beat_stage(pipeline, session=session)
    return pipeline


def _finish_params_from_pipeline(pipeline: dict[str, Any]) -> dict[str, Any]:
    root = resolve_workspace_root()
    return {
        "chapter_dir": pipeline.get("chapter_dir"),
        "chp_num": pipeline.get("chp_num"),
        "snapshot_file": pipeline.get("snapshot_file"),
        "workspace_root": str(root),
        "min_chars": pipeline.get("min_chars"),
        "max_chars": pipeline.get("max_chars"),
        "usr05_band": pipeline.get("usr05_band"),
        "draft_target_chars": pipeline.get("draft_target_chars"),
    }


def _resolve_finish_defaults(
    *,
    session: str | None,
    chapter_dir: str | None,
    chp_num: int | None,
    snapshot_file: str | None,
    workspace_root: str | Path | None,
    min_chars: int | None,
    max_chars: int | None,
    usr05_band: str | None,
    prose: str | None,
    preloaded_pipeline: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], bool, dict[str, Any]]:
    """Fill missing chapter/snapshot paths from warm USR14/USR15/CHP when prose is set."""
    resolved: dict[str, Any] = {}
    warm_used = False
    pipeline: dict[str, Any] = dict(preloaded_pipeline or {})

    if workspace_root is None:
        workspace_root = resolve_workspace_root()
        resolved["workspace_root"] = str(workspace_root)

    needs_warm = prose is not None and (
        chapter_dir is None
        or chp_num is None
        or snapshot_file is None
        or (min_chars is None and max_chars is None)
    )
    draft_target_chars: int | None = pipeline.get("draft_target_chars")
    if needs_warm and not pipeline and session:
        pipeline = _warm_pipeline(session)
        warm_used = True
    elif prose is not None and not pipeline and session:
        pipeline = _warm_pipeline(session)
        warm_used = True
        draft_target_chars = pipeline.get("draft_target_chars")
    if needs_warm and pipeline:
        if chapter_dir is None and pipeline.get("chapter_dir"):
            chapter_dir = pipeline["chapter_dir"]
            resolved["chapter_dir"] = chapter_dir
        if chp_num is None and pipeline.get("chp_num") is not None:
            chp_num = pipeline["chp_num"]
            resolved["chp_num"] = chp_num
        if snapshot_file is None and pipeline.get("snapshot_file"):
            snapshot_file = pipeline["snapshot_file"]
            resolved["snapshot_file"] = snapshot_file
        if min_chars is None and max_chars is None and usr05_band is None:
            band = pipeline.get("usr05_band")
            if band and "_" in band and band.endswith("_zh"):
                usr05_band = band
                resolved["usr05_band"] = band
        if draft_target_chars is None:
            draft_target_chars = pipeline.get("draft_target_chars")

    return (
        {
            "chapter_dir": chapter_dir,
            "chp_num": chp_num,
            "snapshot_file": snapshot_file,
            "workspace_root": workspace_root,
            "min_chars": min_chars,
            "max_chars": max_chars,
            "usr05_band": usr05_band,
            "draft_target_chars": draft_target_chars,
        },
        resolved,
        warm_used,
        pipeline,
    )


def beat_turn_begin(
    *,
    session: str | None,
    anchor: str = "STEP01",
    depth: int = 2,
    max_rows: int = 55,
    include_warm: bool = False,
    since_modified: str | None = None,
    walk_filter: str = "law_usr",
    lib_query: bool = False,
) -> dict[str, Any]:
    """One MCP call: warm read + presentation envelope (novel-agnostic)."""
    read_modified = fetch_session_modified(session)
    resp = run_memnet(
        [
            "query",
            "warm",
            "--anchor",
            anchor,
            "--depth",
            str(depth),
            "--max-rows",
            str(max_rows),
        ],
        session=session,
    )
    warm_walk = fetch_warm_walk(
        session=session,
        anchor=anchor,
        depth=depth,
        max_rows=max_rows,
    )
    pipeline = parse_warm_stdout(resp.stdout)
    _supplement_prose_target(pipeline, session=session, warm_stdout=resp.stdout)
    fsm_extra = _supplement_pipeline_fsm(
        pipeline, session=session, warm_stdout=resp.stdout
    )
    warm_for_pres = resp.stdout + ("\n" + fsm_extra if fsm_extra else "")
    if pipeline.get("auto_beat"):
        pipeline["next_action"] = (
            "auto_beat: unconscious — no options; write rescue/wake prose → beat_turn_finish"
        )
    else:
        pipeline["next_action"] = pipeline_next_action(
            pipeline.get("step_n"),
            pipeline.get("beat_stage"),
            pipeline_no_bundle=bool(pipeline.get("pipeline_no_bundle")),
        )
    pipeline["prose_gate"] = _prose_gate_active(pipeline)
    if lib_query:
        pipeline["lib_query"] = True
    finish_params = _finish_params_from_pipeline(pipeline)
    presentation = compile_presentation(
        warm_for_pres,
        pipeline,
        warm_walk=warm_walk or None,
        walk_filter=walk_filter,
    )
    warnings: list[str] = []
    if since_modified and read_modified and since_modified != read_modified:
        warnings.append(
            f"session_stale: graph modified ({read_modified}); "
            "memnet writes since last begin — call beat_turn_begin again"
        )
    out: dict[str, Any] = {
        "exit_code": resp.exit_code,
        "errors": list(resp.errors),
        "session_id": resp.session_id or session,
        "session_modified": read_modified,
        "session_contract": session_contract_block(),
        "presentation": presentation,
        "writing_contract": presentation["contracts"] + presentation.get("option_contracts", []),
        "pipeline": pipeline,
        "finish_params": finish_params,
        "snapshot_file": pipeline.get("snapshot_file"),
        "gate_retry": pipeline.get("gate_retry", "once"),
        "mcp_budget_per_beat": {"memnet": 0, "novel_writer": 2},
        "tool": "beat_turn_begin",
    }
    if include_warm:
        out["warm_stdout"] = resp.stdout
        out["warm_walk"] = warm_walk
    else:
        out["warm_stdout"] = None
        out["warm_walk"] = None
    if warnings:
        out["warnings"] = warnings
    if pipeline["prose_gate"]:
        out["local_draft"] = (
            f"python scripts/{pipeline.get('local_gate', 'prose_count.py')} --usr05 "
            f"{pipeline.get('usr05_band', '<scene_length>')} --prose-file beat.txt  "
            f"(stage={pipeline.get('beat_stage', 'oln')})"
        )
    else:
        out["local_draft"] = None
    contracts = presentation["contracts"]
    if contracts:
        out["draft_note"] = contracts[0]
        if pipeline.get("draft_target_chars"):
            out["draft_note"] += f"; advisory ~{pipeline['draft_target_chars']} chars"
    if pipeline.get("draft_target_chars"):
        out["prose_advisory_zh"] = pipeline["draft_target_chars"]
    return out


def _validate_sys_time_updates(
    session: str | None,
    update_lines: list[str] | None,
) -> list[str]:
    if not update_lines:
        return []
    sys_updates = [
        ln for ln in update_lines if ln.strip().startswith("@SYS:")
    ]
    if not sys_updates:
        return []
    current: str | None = None
    if session:
        warm = _warm_pipeline(session)
        current = warm.get("sys_time_raw")
    errors: list[str] = []
    for line in sys_updates:
        new_time = sys_time_field_from_wire(line)
        if new_time is None or current is None:
            continue
        err = check_sys_time_update(current, new_time)
        if err:
            errors.append(err)
        else:
            current = new_time
    return errors


def beat_turn_finish(
    *,
    session: str | None,
    prose: str | None = None,
    chapter_dir: str | None = None,
    chp_num: int | None = None,
    min_chars: int | None = None,
    max_chars: int | None = None,
    usr05_band: str | None = None,
    add_lines: list[str] | None = None,
    update_lines: list[str] | None = None,
    oln_lines: list[str] | None = None,
    oln_mode: str = "add",
    sbd_lines: list[str] | None = None,
    sbd_mode: str = "add",
    scr_lines: list[str] | None = None,
    scr_mode: str = "add",
    snapshot_file: str | None = None,
    workspace_root: str | Path | None = None,
    replace_last_paragraph: bool = False,
    allow_new_relation: bool = False,
    prose_only_gate: bool = False,
    pipeline_bypass: bool = False,
    option_lines: list[str] | None = None,
    since_modified: str | None = None,
) -> dict[str, Any]:
    """One MCP call: OLN/SBD/SCR (LAW-PIPE20) → prose gate → chapter → graph → session_save."""
    finish_modified = fetch_session_modified(session)
    if since_modified and finish_modified and since_modified != finish_modified:
        return {
            "exit_code": 1,
            "errors": [
                "@ERR: session_stale|graph changed since beat_turn_begin; call beat_turn_begin again"
            ],
            "session_id": session,
            "session_modified": finish_modified,
            "tool": "beat_turn_finish",
        }

    session_pipeline: dict[str, Any] = {}
    warm_for_validate = ""
    if session:
        warm_resp = run_memnet(
            ["query", "warm", "--anchor", "STEP01", "--depth", "1", "--max-rows", "55"],
            session=session,
        )
        warm_for_validate = warm_resp.stdout
        session_pipeline = parse_warm_stdout(warm_for_validate)
        _supplement_prose_target(session_pipeline, session=session, warm_stdout=warm_for_validate)
        _supplement_pipeline_fsm(
            session_pipeline, session=session, warm_stdout=warm_for_validate
        )

    params, auto_resolved, warm_used, session_pipeline = _resolve_finish_defaults(
        session=session,
        chapter_dir=chapter_dir,
        chp_num=chp_num,
        snapshot_file=snapshot_file,
        workspace_root=workspace_root,
        min_chars=min_chars,
        max_chars=max_chars,
        usr05_band=usr05_band,
        prose=prose,
        preloaded_pipeline=session_pipeline,
    )
    chapter_dir = params["chapter_dir"]
    chp_num = params["chp_num"]
    snapshot_file = params["snapshot_file"]
    workspace_root = params["workspace_root"]
    min_chars = params["min_chars"]
    max_chars = params["max_chars"]
    usr05_band = params["usr05_band"]
    draft_target_chars = params.get("draft_target_chars")

    if usr05_band and (min_chars is None or max_chars is None):
        if "_" in usr05_band and usr05_band.endswith("_zh"):
            min_chars, max_chars = parse_scene_band(usr05_band)

    result: dict[str, Any] = {
        "exit_code": 0,
        "errors": [],
        "phases": [],
        "internal_memnet_calls": 1 if session else 0,
        "tool": "beat_turn_finish",
        "session_id": session,
        "session_contract": session_contract_block(),
        "mcp_budget_per_beat": {"memnet": 0, "novel_writer": 2},
        "finish_hints": {"warnings": [], "violations": []},
    }
    if auto_resolved:
        result["auto_resolved"] = auto_resolved
    if warm_used:
        result["internal_memnet_calls"] += 1
        result["phases"].append({"phase": "warm_resolve", "exit_code": 0})

    if option_lines and warm_for_validate:
        hints = validate_option_lines(
            option_lines,
            warm_stdout=warm_for_validate,
            auto_beat=session_pipeline.get("auto_beat", False),
        )
        result["finish_hints"] = hints
        if hints["violations"]:
            result["exit_code"] = 1
            result["errors"].extend(hints["violations"])
            result["option_blocked"] = True
            result["session_modified"] = finish_modified
            return result

    beat_stage = session_pipeline.get("beat_stage", "oln")
    auto_beat = session_pipeline.get("auto_beat", False)
    no_bundle = bool(session_pipeline.get("pipeline_no_bundle"))
    provided = _pipeline_provided(oln_lines, sbd_lines, scr_lines, prose)
    pipeline_errors = _validate_pipeline_commits(
        beat_stage,
        provided,
        auto_beat=auto_beat,
        pipeline_bypass=pipeline_bypass,
        no_bundle=no_bundle,
    )
    if pipeline_errors:
        result["exit_code"] = 1
        result["errors"].extend(pipeline_errors)
        result["pipeline_blocked"] = True
        result["beat_stage"] = beat_stage
        result["next_action"] = _STAGE_DRAFT_NOTES.get(beat_stage, _STAGE_DRAFT_NOTES["oln"])
        return result

    new_beat_stage = _stage_after_commits(beat_stage, provided)
    if new_beat_stage != beat_stage:
        update_lines = _ensure_beat_stage_update(
            update_lines,
            new_beat_stage,
            session_pipeline.get("beat_stage_usr_id"),
        )
        result["beat_stage"] = new_beat_stage
    else:
        result["beat_stage"] = beat_stage

    if prose is not None and (chapter_dir is None or chp_num is None):
        result["errors"].append(
            "@ERR: chapter_path_missing|set USR14 chapter_out + open CHP in seed, "
            "or pass chapter_dir/chp_num on beat_turn_finish"
        )

    time_errors = _validate_sys_time_updates(session, update_lines)
    if time_errors:
        result["exit_code"] = 1
        result["errors"].extend(time_errors)
        result["time_blocked"] = True
        return result

    for phase, lines, mode in (
        ("oln", oln_lines, oln_mode),
        ("sbd", sbd_lines, sbd_mode),
        ("scr", scr_lines, scr_mode),
    ):
        if not lines:
            continue
        wire_mode = mode if mode in ("add", "update") else "add"
        wire_resp = _apply_wire_lines(
            lines,
            mode=wire_mode,
            session=session,
            allow_new_relation=allow_new_relation,
        )
        result["internal_memnet_calls"] += 1
        result["phases"].append(
            {"phase": phase, "mode": wire_mode, "exit_code": wire_resp.exit_code}
        )
        if wire_resp.exit_code != 0:
            result["exit_code"] = wire_resp.exit_code
            result["errors"].extend(wire_resp.errors)
            return result

    if prose is not None:
        status = prose_status(
            prose,
            min_chars=min_chars,
            max_chars=max_chars,
            advisory_target=draft_target_chars,
        )
        result["prose"] = status
        if status.get("hint"):
            result["prose_advisory_hint"] = status["hint"]
        has_gate = min_chars is not None and max_chars is not None
        if has_gate and not status["ok"]:
            result["exit_code"] = 1
            result["gate_blocked"] = True
            result["errors"] = [f"@ERR: prose_{status['status']}|{status['hint']}"]
            result["next_action"] = status["next_action"]
            result["mcp_retry_forbidden"] = True
            return result

        if prose_only_gate:
            result["phases"].append({"phase": "prose_gate", "gate_ready": status.get("gate_ready", True)})
        elif chapter_dir and chp_num is not None:
            gate = chapter_prose_gate(
                prose,
                chapter_dir=chapter_dir,
                chp_num=chp_num,
                workspace_root=workspace_root,
                min_chars=min_chars,
                max_chars=max_chars,
                replace_last_paragraph=replace_last_paragraph,
            )
            result["chapter"] = gate
            result["phases"].append({"phase": "chapter", "path": gate.get("path")})
            if gate.get("exit_code", 1) != 0:
                result["exit_code"] = gate["exit_code"]
                result["errors"].extend(gate.get("errors", []))
                return result

    persist_resp: MemNetResponse | None = None
    for mode, lines in (("add", add_lines or []), ("update", update_lines or [])):
        resp = _apply_wire_lines(
            lines,
            mode=mode,
            session=session,
            allow_new_relation=allow_new_relation,
        )
        if not lines:
            continue
        result["internal_memnet_calls"] += 1
        result["phases"].append({"phase": mode, "exit_code": resp.exit_code})
        persist_resp = MemNetResponse.merge(persist_resp, resp) if persist_resp else resp
        if resp.exit_code != 0:
            result["exit_code"] = resp.exit_code
            result["errors"].extend(resp.errors)
            return result

    if persist_resp:
        result["persist_stdout"] = persist_resp.stdout

    if snapshot_file and result["exit_code"] == 0:
        save_resp = run_memnet(["session", "save", "--file", snapshot_file], session=session)
        result["internal_memnet_calls"] += 1
        result["phases"].append({"phase": "session_save", "exit_code": save_resp.exit_code})
        if save_resp.exit_code != 0:
            result["exit_code"] = save_resp.exit_code
            result["errors"].extend(save_resp.errors)

    result["session_modified"] = fetch_session_modified(session)
    return result
