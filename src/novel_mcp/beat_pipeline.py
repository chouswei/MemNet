"""Novel beat orchestration — warm read + atomic prose/chapter/graph commit in-process."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from memnet_mcp.client import MemNetResponse, run_memnet
from novel_mcp.chapter_io import beat_prose_finalize
from novel_mcp.zh_text import parse_scene_band, prose_status

_ROW_RE = re.compile(r"^@(\w+):\s*(.+)$")

_PHASE_ACTIONS: dict[int, str] = {
    1: "draft @OLN → beat_turn_finish(oln_lines=…)",
    2: "refine @OLN if needed → draft prose ~target_chars",
    3: "local prose_count.py → beat_turn_finish(prose + persist)",
    4: "beat_turn_finish(prose + persist + snapshot)",
    5: "present outline + prose + options (no MCP)",
    6: "beat_turn_finish(persist only) if graph not yet saved",
}


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
        if uid == "USR05":
            pipeline["usr05_band"] = value
            try:
                mn, mx = parse_scene_band(value)
                pipeline["min_chars"] = mn
                pipeline["max_chars"] = mx
                pipeline["target_chars"] = (mn + mx) // 2
            except ValueError:
                pass
        if key == "chapter_out" or value.startswith("novel-output/"):
            pipeline["chapter_dir"] = value

    for body in rows.get("CHP", []):
        parts = body.split("|")
        if len(parts) >= 6 and parts[-1] == "open":
            pipeline["chp_num"] = int(parts[1])

    focus = pipeline.get("step_focus")
    if isinstance(focus, str) and focus.startswith("OLN"):
        for body in rows.get("OLN", []):
            if body.startswith(focus + "|"):
                pipeline["oln_row"] = body
                break

    return pipeline


def pipeline_next_action(step_n: int | str | None) -> str:
    if isinstance(step_n, str) and step_n.isdigit():
        step_n = int(step_n)
    if isinstance(step_n, int):
        return _PHASE_ACTIONS.get(step_n, "beat_turn_begin → draft → beat_turn_finish")
    return "beat_turn_begin → draft → beat_turn_finish"


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


def beat_turn_begin(
    *,
    session: str | None,
    anchor: str = "STEP01",
    depth: int = 2,
    max_rows: int = 55,
) -> dict[str, Any]:
    """One MCP call: warm read + parsed pipeline envelope (USR05 band, STEP, OLN, CHP)."""
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
    pipeline = parse_warm_stdout(resp.stdout)
    pipeline["next_action"] = pipeline_next_action(pipeline.get("step_n"))
    return {
        "exit_code": resp.exit_code,
        "errors": list(resp.errors),
        "session_id": resp.session_id,
        "warm_stdout": resp.stdout,
        "pipeline": pipeline,
        "local_draft": (
            "python scripts/prose_count.py --usr05 "
            f"{pipeline.get('usr05_band', '<USR05>')} --prose-file beat.txt"
        ),
        "mcp_budget_per_beat": {"memnet": 2, "novel_writer": 0},
        "tool": "beat_turn_begin",
    }


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
    snapshot_file: str | None = None,
    workspace_root: str | Path | None = None,
    replace_last_paragraph: bool = False,
    allow_new_relation: bool = False,
    prose_only_gate: bool = False,
) -> dict[str, Any]:
    """One MCP call: optional OLN → prose gate → chapter append → graph persist → session_save."""
    if usr05_band and (min_chars is None or max_chars is None):
        min_chars, max_chars = parse_scene_band(usr05_band)

    result: dict[str, Any] = {
        "exit_code": 0,
        "errors": [],
        "phases": [],
        "internal_memnet_calls": 0,
        "tool": "beat_turn_finish",
        "mcp_budget_per_beat": {"memnet": 2, "novel_writer": 0},
    }

    if oln_lines:
        mode = oln_mode if oln_mode in ("add", "update") else "add"
        oln_resp = _apply_wire_lines(
            oln_lines,
            mode=mode,
            session=session,
            allow_new_relation=allow_new_relation,
        )
        result["internal_memnet_calls"] += 1
        result["phases"].append({"phase": "oln", "mode": mode, "exit_code": oln_resp.exit_code})
        if oln_resp.exit_code != 0:
            result["exit_code"] = oln_resp.exit_code
            result["errors"].extend(oln_resp.errors)
            return result

    if prose is not None and min_chars is not None and max_chars is not None:
        status = prose_status(prose, min_chars=min_chars, max_chars=max_chars)
        result["prose"] = status
        if not status["ok"]:
            result["exit_code"] = 1
            result["gate_blocked"] = True
            result["errors"] = [f"@ERR: prose_{status['status']}|{status['hint']}"]
            result["next_action"] = status["next_action"]
            result["mcp_retry_forbidden"] = True
            return result

        if prose_only_gate:
            result["phases"].append({"phase": "prose_gate", "gate_ready": True})
        elif chapter_dir and chp_num is not None:
            gate = beat_prose_finalize(
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

    return result
