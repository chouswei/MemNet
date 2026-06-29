#!/usr/bin/env python3
"""Run one novel beat: Python-orchestrated MCP pipeline + stateless LLM drafts."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "src"))

from env_load import load_dotenv

load_dotenv()

from app_config import RESULT_MARKER, load_config
from chat_thread import reset_threads
from play_service import (
    fail_result,
    preflight_session,
    probe_serve,
    read_session_id,
    run_beat,
    write_last_beat,
)

from memnet_mcp.client import run_memnet

from novel_mcp.opening_loadout import commit_opening_loadout
from novel_mcp.player_profile import commit_profile
from novel_mcp.player_setup import player_setup_gate_payload, read_player_setup
from novel_mcp.play_context import read_beat_stage
from novel_mcp.setup_ack import seed_cli_setup_acks

_PHASE_T0 = 0.0


def _phase(msg: str) -> None:
    print(f"[cursor_beat +{time.perf_counter() - _PHASE_T0:.1f}s] {msg}", file=sys.stderr)


def _write_and_emit(config, result: dict[str, Any]) -> int:
    write_last_beat(config, result)
    line = RESULT_MARKER + "\t" + json.dumps(result, ensure_ascii=False)
    print(line)
    return 0 if int(result.get("exit_code", 0)) == 0 else 1


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
    seed_cli_setup_acks(session)
    setup = read_player_setup(session)
    save = run_memnet(["session", "save", "--file", str(config.snapshot_file)], session=session)
    if save.exit_code != 0:
        print(f"error: session save failed: {save.stderr}", file=sys.stderr)
        return 1
    out = {
        "exit_code": 0,
        "session": session,
        "app_id": config.app_id,
        "setup_complete": setup.get("setup_complete"),
        "player_setup": setup,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


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
        for k in ("DEEPSEEK_API_KEY", "LLM_API_KEY", "LLM_API_KEY_SCRIPT", "LLM_API_KEY_PROSE")
    )
    if not has_llm_key and not args.setup:
        print(
            "error: set DEEPSEEK_API_KEY (or LLM_API_KEY / LLM_API_KEY_SCRIPT / LLM_API_KEY_PROSE)",
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

    try:
        session = read_session_id(config, args.session)
    except FileNotFoundError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    if not probe_serve():
        from mcp_config import SERVE_HOST, SERVE_PORT

        print(
            f"error: memnet serve not reachable at {SERVE_HOST}:{SERVE_PORT}",
            file=sys.stderr,
        )
        return 1

    _, pf_code = preflight_session(config, session)
    if pf_code != 0:
        if pf_code == 1:
            print("error: no active session and no snapshot", file=sys.stderr)
        return pf_code
    session = read_session_id(config, args.session)

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

    if args.continue_beat and read_beat_stage(session) in ("oln", "script_draft", "script_review") and not args.prose_only:
        print(
            "error: --continue but beat_stage is oln; use --choice",
            file=sys.stderr,
        )
        return 2

    def on_phase(phase: str) -> None:
        _phase(phase)

    result, code = run_beat(
        config,
        session,
        choice=args.choice,
        steering=args.steering,
        continue_beat=args.continue_beat,
        script_only=args.script_only,
        prose_only=args.prose_only,
        stream=args.stream,
        on_phase=on_phase,
    )

    if args.script_only:
        return code

    if result is None:
        return code

    return _write_and_emit(config, result)


if __name__ == "__main__":
    sys.exit(main())
