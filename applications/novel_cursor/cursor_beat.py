#!/usr/bin/env python3
"""Run one novel beat via dual persistent Cursor SDK agents + MemNet MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import socket
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "src"))

from agent_session import reset_agent_ids, run_dual_beat_async
from app_config import MODEL, RESULT_MARKER, load_config, repo_root
from beat_prompt import (
    build_prose_primer,
    build_prose_turn,
    build_script_primer,
    build_script_turn,
)
from mcp_config import SERVE_HOST, SERVE_PORT

from novel_mcp.play_context import prose_beat_prepare, read_beat_stage, script_beat_prepare

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_LEGACY_SESSION = repo_root() / "applications" / "shenjia_caifa" / "session_id.txt"


def _migrate_legacy_session(config) -> None:
    if config.session_id_file.is_file():
        return
    if _LEGACY_SESSION.is_file() and config.app_id == "shenjia_caifa":
        config.session_id_file.parent.mkdir(parents=True, exist_ok=True)
        config.session_id_file.write_text(
            _LEGACY_SESSION.read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def _preflight_session(config, session: str) -> tuple[str, int]:
    from memnet_mcp.client import run_memnet

    snap = config.snapshot_file
    cur = run_memnet(["session", "current"], session=session)
    if cur.exit_code != 0 or not cur.session_id:
        if snap.is_file():
            load = run_memnet(
                ["session", "load", "--file", str(snap), "--keep-id"],
            )
            if load.exit_code != 0:
                print(f"error: session load failed: {load.stderr}", file=sys.stderr)
                return "oln", 1
        else:
            print("error: no active session and no snapshot", file=sys.stderr)
            return "oln", 1

    return read_beat_stage(session), 0


def _read_session_id(config, explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    _migrate_legacy_session(config)
    if config.session_id_file.is_file():
        line = config.session_id_file.read_text(encoding="utf-8").strip().splitlines()
        if line and line[0].startswith("mn_"):
            return line[0].strip()
    print(
        f"error: missing --session and no {config.session_id_file}",
        file=sys.stderr,
    )
    sys.exit(2)


def _probe_serve() -> bool:
    try:
        with socket.create_connection((SERVE_HOST, int(SERVE_PORT)), timeout=3):
            return True
    except OSError:
        return False


def _snap_rel(config) -> str:
    return str(config.snapshot_file.relative_to(repo_root())).replace("\\", "/")


def _parse_result_payload(text: str) -> dict[str, Any] | None:
    for match in _JSON_FENCE_RE.finditer(text):
        try:
            obj = json.loads(match.group(1))
            if isinstance(obj, dict) and "prose" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict) and "prose" in obj:
                return obj
        except json.JSONDecodeError:
            pass
    return None


def _normalise_result(raw: dict[str, Any], config, session: str) -> dict[str, Any]:
    options = raw.get("options") or []
    if not isinstance(options, list):
        options = []
    while len(options) < 6:
        options.append("")
    options = [str(o) for o in options[:6]]
    return {
        "exit_code": int(raw.get("exit_code", 0)),
        "session": str(raw.get("session") or session),
        "app_id": str(raw.get("app_id") or config.app_id),
        "prose": str(raw.get("prose") or ""),
        "options": options,
        "hud": str(raw.get("hud") or ""),
        "snapshot_saved": bool(raw.get("snapshot_saved", False)),
        "snapshot_file": str(raw.get("snapshot_file") or _snap_rel(config)),
        "beat_stage": str(raw.get("beat_stage") or "oln"),
        **({"error": raw["error"]} if raw.get("error") else {}),
    }


def _write_and_emit(config, result: dict[str, Any]) -> int:
    path = config.last_beat_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    line = RESULT_MARKER + "\t" + json.dumps(result, ensure_ascii=False)
    print(line)
    return 0 if int(result.get("exit_code", 0)) == 0 else 1


async def _run_beat_async(
    config,
    session: str,
    *,
    choice: int | None,
    steering: str | None,
    continue_beat: bool,
    script_only: bool,
    prose_only: bool,
    stream: bool,
) -> tuple[str, int]:
    snap_rel = _snap_rel(config)
    ch_dir = str(config.chapter_dir.relative_to(repo_root())).replace("\\", "/")

    run_script = not prose_only
    if continue_beat and read_beat_stage(session) == "prose":
        run_script = False

    script_prep: dict[str, Any] = {}
    if run_script:
        script_prep = script_beat_prepare(
            session=session,
            choice=choice,
            steering=steering,
            continue_beat=continue_beat and not choice and not steering,
            snapshot_file=snap_rel,
            chapter_dir=ch_dir,
        )
        if script_prep.get("exit_code", 1) != 0:
            print(f"error: {script_prep.get('errors')}", file=sys.stderr)
            return "", int(script_prep.get("exit_code", 2))

    if script_only:
        text, code = await run_dual_beat_async(
            config,
            session,
            script_prep,
            {},
            build_script_primer(config),
            build_script_turn(config, script_prep),
            "",
            "",
            stream=stream,
            script_only=True,
            prose_only=False,
        )
        if code != 0:
            return text, code
        if read_beat_stage(session) != "prose":
            return "", 4
        return "", 0

    if run_script:
        text, code = await run_dual_beat_async(
            config,
            session,
            script_prep,
            {},
            build_script_primer(config),
            build_script_turn(config, script_prep),
            "",
            "",
            stream=stream,
            script_only=True,
            prose_only=False,
        )
        if code != 0:
            return text, code
        if read_beat_stage(session) != "prose":
            text, code = await run_dual_beat_async(
                config,
                session,
                script_prep,
                {},
                build_script_primer(config),
                build_script_turn(config, script_prep) + "\n\n(Retry: handoff failed.)",
                "",
                "",
                stream=stream,
                script_only=True,
                prose_only=False,
            )
            if code != 0 or read_beat_stage(session) != "prose":
                return text, 4

    prose_prep = prose_beat_prepare(
        session=session,
        snapshot_file=snap_rel,
        chapter_dir=ch_dir,
    )
    if prose_prep.get("exit_code", 1) != 0:
        print(f"error: {prose_prep.get('errors')}", file=sys.stderr)
        return "", int(prose_prep.get("exit_code", 2))

    return await run_dual_beat_async(
        config,
        session,
        script_prep,
        prose_prep,
        build_script_primer(config),
        "",
        build_prose_primer(config),
        build_prose_turn(config, prose_prep),
        stream=stream,
        script_only=False,
        prose_only=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one novel beat (dual script + prose SDK agents)",
    )
    parser.add_argument("--app", metavar="ID")
    parser.add_argument("--seed", metavar="PATH")
    parser.add_argument("--session")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--choice", type=int, metavar="N")
    mode.add_argument("--steering", metavar="TEXT")
    mode.add_argument("--continue", dest="continue_beat", action="store_true")
    parser.add_argument("--script-only", action="store_true")
    parser.add_argument("--prose-only", action="store_true")
    parser.add_argument("--reset-agents", action="store_true")
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args(argv)

    if args.choice is not None and not (1 <= args.choice <= 6):
        print("error: --choice must be 1–6", file=sys.stderr)
        return 2
    if args.script_only and args.prose_only:
        print("error: --script-only and --prose-only are mutually exclusive", file=sys.stderr)
        return 2

    if not os.environ.get("CURSOR_API_KEY", "").strip():
        print("error: CURSOR_API_KEY not set", file=sys.stderr)
        return 1

    try:
        config = load_config(app_id=args.app, seed_md=args.seed)
    except (FileNotFoundError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    session = _read_session_id(config, args.session)

    if not _probe_serve():
        print(
            f"error: memnet serve not reachable at {SERVE_HOST}:{SERVE_PORT}",
            file=sys.stderr,
        )
        return 1

    _, pf_code = _preflight_session(config, session)
    if pf_code != 0:
        return pf_code

    if args.reset_agents:
        reset_agent_ids(config)

    if args.prose_only and read_beat_stage(session) != "prose":
        print("error: --prose-only requires USR23 beat_stage=prose", file=sys.stderr)
        return 2

    if args.continue_beat and read_beat_stage(session) == "oln" and not args.prose_only:
        print(
            "error: --continue but beat_stage is oln; use --choice",
            file=sys.stderr,
        )
        return 2

    text, code = asyncio.run(
        _run_beat_async(
            config,
            session,
            choice=args.choice,
            steering=args.steering,
            continue_beat=args.continue_beat,
            script_only=args.script_only,
            prose_only=args.prose_only,
            stream=args.stream,
        )
    )

    if args.script_only:
        return code

    if code != 0 and not text:
        return code

    raw = _parse_result_payload(text)
    if raw is None:
        fail = {
            "exit_code": 3,
            "session": session,
            "app_id": config.app_id,
            "prose": "",
            "options": [""] * 6,
            "hud": "",
            "snapshot_saved": False,
            "snapshot_file": _snap_rel(config),
            "beat_stage": "",
            "error": "no parseable JSON result from prose agent",
        }
        return _write_and_emit(config, fail)

    result = _normalise_result(raw, config, session)
    if code != 0 and result.get("exit_code") == 0:
        result["exit_code"] = code
    return _write_and_emit(config, result)


if __name__ == "__main__":
    sys.exit(main())
