#!/usr/bin/env python3
"""Run one novel beat: Python-orchestrated MCP pipeline + stateless LLM drafts."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "src"))

from app_config import RESULT_MARKER, load_config, repo_root
from chat_thread import reset_threads
from beat_orchestrator import run_prose_phase, run_script_phase
from mcp_config import SERVE_HOST, SERVE_PORT

from memnet_mcp.client import run_memnet

from novel_mcp.opening_loadout import commit_opening_loadout
from novel_mcp.player_profile import commit_profile
from novel_mcp.player_setup import player_setup_gate_payload, read_player_setup
from novel_mcp.play_context import prose_beat_prepare, read_beat_stage, script_beat_prepare

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


def _session_live(resp) -> bool:
    import re

    for line in resp.stdout.splitlines():
        m = re.match(r"^@SESSION:\s*(\S+)", line.strip())
        if m:
            sid = m.group(1).split("|", 1)[0].strip()
            return bool(sid and sid != "none")
    return False


def _preflight_session(config, session: str) -> tuple[str, int]:
    from memnet_mcp.client import run_memnet

    snap = config.snapshot_file
    cur = run_memnet(["session", "current"], session=session)
    if not _session_live(cur):
        if snap.is_file():
            load = run_memnet(
                ["session", "load", "--file", str(snap), "--keep-id"],
            )
            if load.exit_code != 0:
                print(f"error: session load failed: {load.stderr}", file=sys.stderr)
                return session, 1
            if load.session_id:
                session = load.session_id
                config.session_id_file.parent.mkdir(parents=True, exist_ok=True)
                config.session_id_file.write_text(session.strip() + "\n", encoding="utf-8")
        else:
            print("error: no active session and no snapshot", file=sys.stderr)
            return session, 1

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


def _phase(msg: str) -> None:
    print(f"[cursor_beat +{time.perf_counter() - _PHASE_T0:.1f}s] {msg}", file=sys.stderr)


_PHASE_T0 = 0.0


def _probe_serve() -> bool:
    try:
        with socket.create_connection((SERVE_HOST, int(SERVE_PORT)), timeout=3):
            return True
    except OSError:
        return False


def _snap_rel(config) -> str:
    return str(config.snapshot_file.relative_to(repo_root())).replace("\\", "/")


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


def _fail_result(config, session: str, code: int, error: str) -> dict[str, Any]:
    return {
        "exit_code": code,
        "session": session,
        "app_id": config.app_id,
        "prose": "",
        "options": [""] * 6,
        "hud": "",
        "snapshot_saved": False,
        "snapshot_file": _snap_rel(config),
        "beat_stage": read_beat_stage(session),
        "error": error,
    }


def _run_setup(
    config,
    session: str,
    *,
    name: str,
    gender: str,
    arts: str,
) -> int:
    prof = commit_profile(session, name, gender)
    if prof.get("exit_code") != 0:
        print(f"error: {prof.get('errors')}", file=sys.stderr)
        return int(prof.get("exit_code", 2))
    art_ids = [x.strip() for x in arts.split(",") if x.strip()]
    loadout = commit_opening_loadout(session, art_ids)
    if loadout.get("exit_code") != 0:
        print(f"error: {loadout.get('errors')}", file=sys.stderr)
        return int(loadout.get("exit_code", 2))
    save = run_memnet(["session", "save", "--file", str(config.snapshot_file)], session=session)
    if save.exit_code != 0:
        print(f"error: session save failed: {save.stderr}", file=sys.stderr)
        return 1
    out = {
        "exit_code": 0,
        "session": session,
        "app_id": config.app_id,
        "setup_complete": loadout.get("setup_complete"),
        "player_setup": loadout,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def _run_beat(
    config,
    session: str,
    *,
    choice: int | None,
    steering: str | None,
    continue_beat: bool,
    script_only: bool,
    prose_only: bool,
    stream: bool,
) -> tuple[dict[str, Any] | None, int]:
    snap_rel = _snap_rel(config)
    ch_dir = str(config.chapter_dir.relative_to(repo_root())).replace("\\", "/")

    run_script = not prose_only
    if continue_beat and read_beat_stage(session) == "prose":
        run_script = False

    script_prep: dict[str, Any] = {}
    if run_script:
        _phase("script_beat_prepare")
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
            return None, int(script_prep.get("exit_code", 2))

    if run_script:
        _phase("script phase (oln→sbd→scr)")
        code, errors = run_script_phase(
            config,
            session,
            script_prep,
            stream=stream,
        )
        if code != 0:
            print(f"error: {errors}", file=sys.stderr)
            return None, code

    if script_only:
        return None, 0

    _phase("prose_beat_prepare")
    prose_prep = prose_beat_prepare(
        session=session,
        snapshot_file=snap_rel,
        chapter_dir=ch_dir,
    )
    if prose_prep.get("exit_code", 1) != 0:
        print(f"error: {prose_prep.get('errors')}", file=sys.stderr)
        return None, int(prose_prep.get("exit_code", 2))

    _phase("prose phase")
    result, code, errors = run_prose_phase(
        config,
        session,
        prose_prep,
        stream=stream,
    )
    if code != 0:
        print(f"error: {errors}", file=sys.stderr)
        if result is None:
            return None, code
        result["exit_code"] = code
        result["error"] = "; ".join(errors)
    return result, code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one novel beat (orchestrated MCP + LLM drafts)",
    )
    parser.add_argument("--app", metavar="ID")
    parser.add_argument("--seed", metavar="PATH")
    parser.add_argument("--session")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--setup", action="store_true", help="CI: commit profile + opening loadout")
    mode.add_argument("--choice", type=int, metavar="N")
    mode.add_argument("--steering", metavar="TEXT")
    mode.add_argument("--continue", dest="continue_beat", action="store_true")
    parser.add_argument("--name", metavar="TEXT", help="With --setup: protagonist name")
    parser.add_argument("--gender", choices=["男", "女"], help="With --setup: protagonist gender")
    parser.add_argument(
        "--arts",
        metavar="ID,ID,ID",
        help="With --setup: neigong,martial,qinggong ART ids",
    )
    parser.add_argument("--script-only", action="store_true")
    parser.add_argument("--prose-only", action="store_true")
    parser.add_argument("--reset-agents", action="store_true")
    parser.add_argument("--reset-threads", action="store_true")
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args(argv)

    if args.choice is not None and not (1 <= args.choice <= 6):
        print("error: --choice must be 1–6", file=sys.stderr)
        return 2
    if args.script_only and args.prose_only:
        print("error: --script-only and --prose-only are mutually exclusive", file=sys.stderr)
        return 2
    if args.setup:
        if not args.name or not args.gender or not args.arts:
            print("error: --setup requires --name, --gender, and --arts", file=sys.stderr)
            return 2

    has_llm_key = any(
        os.environ.get(k, "").strip()
        for k in ("LLM_API_KEY", "DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "OPENAI_API_KEY", "CURSOR_API_KEY")
    )
    if not has_llm_key and not args.setup:
        print(
            "error: set LLM_API_KEY, DEEPSEEK_API_KEY, MOONSHOT_API_KEY, OPENAI_API_KEY, or CURSOR_API_KEY",
            file=sys.stderr,
        )
        return 1

    global _PHASE_T0
    _PHASE_T0 = time.perf_counter()
    _phase("start")

    try:
        config = load_config(app_id=args.app, seed_md=args.seed)
    except (FileNotFoundError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    _phase(
        f"models: script={config.model_script} prose={config.model_prose} "
        f"(thinking {config.thinking_script}/{config.thinking_prose})"
    )

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
    session = _read_session_id(config, args.session)

    if args.reset_agents:
        _phase("reset-agents ignored (orchestrated mode has no SDK agent ids)")

    if args.reset_threads:
        reset_threads(config)
        _phase("reset script + prose chat threads")

    if args.setup:
        return _run_setup(
            config,
            session,
            name=args.name,
            gender=args.gender,
            arts=args.arts,
        )

    setup = read_player_setup(session)
    if not setup.get("setup_complete") and (
        args.choice is not None or args.steering or args.continue_beat
    ):
        gate = player_setup_gate_payload(session)
        print(json.dumps(gate, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    if args.prose_only and read_beat_stage(session) != "prose":
        print("error: --prose-only requires USR23 beat_stage=prose", file=sys.stderr)
        return 2

    if args.continue_beat and read_beat_stage(session) == "oln" and not args.prose_only:
        print(
            "error: --continue but beat_stage is oln; use --choice",
            file=sys.stderr,
        )
        return 2

    result, code = _run_beat(
        config,
        session,
        choice=args.choice,
        steering=args.steering,
        continue_beat=args.continue_beat,
        script_only=args.script_only,
        prose_only=args.prose_only,
        stream=args.stream,
    )

    if args.script_only:
        return code

    if result is None:
        return code

    return _write_and_emit(config, result)


if __name__ == "__main__":
    sys.exit(main())
