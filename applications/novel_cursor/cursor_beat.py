#!/usr/bin/env python3
"""Run one full novel beat via Cursor SDK + MemNet MCP (thin-chat backend)."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_config import MODEL, RESULT_MARKER, load_config, repo_root
from beat_prompt import build_beat_prompt
from mcp_config import SERVE_HOST, SERVE_PORT, inline_mcp_servers

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

# Legacy session file (pre-generic layout)
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
    """Ensure session is loaded in serve; return USR23 beat_stage."""
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
            session = load.session_id or session
        else:
            print("error: no active session and no snapshot", file=sys.stderr)
            return "oln", 1

    r = run_memnet(["read", "get", "--id", "USR23"], session=session)
    stage = "oln"
    for line in r.stdout.splitlines():
        if "|beat_stage|" in line:
            parts = line.split("|")
            for i, p in enumerate(parts):
                if p == "beat_stage" and i + 1 < len(parts):
                    stage = parts[i + 1]
    return stage, 0


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
    snap_rel = str(config.snapshot_file.relative_to(repo_root())).replace("\\", "/")
    return {
        "exit_code": int(raw.get("exit_code", 0)),
        "session": str(raw.get("session") or session),
        "app_id": str(raw.get("app_id") or config.app_id),
        "prose": str(raw.get("prose") or ""),
        "options": options,
        "hud": str(raw.get("hud") or ""),
        "snapshot_saved": bool(raw.get("snapshot_saved", False)),
        "snapshot_file": str(raw.get("snapshot_file") or snap_rel),
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
    code = int(result.get("exit_code", 0))
    return 0 if code == 0 else 1


async def _run_sdk_async(
    session: str,
    prompt: str,
    *,
    stream: bool,
) -> tuple[str, int]:
    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        print("error: CURSOR_API_KEY not set", file=sys.stderr)
        return "", 1

    try:
        from cursor_sdk import AgentOptions, AsyncClient, CursorAgentError
    except ImportError:
        print(
            "error: cursor-sdk not installed; pip install -r applications/novel_cursor/requirements.txt",
            file=sys.stderr,
        )
        return "", 1

    root = repo_root()
    try:
        async with await AsyncClient.launch_bridge(workspace=str(root)) as client:
            opts = AgentOptions(
                model=MODEL,
                api_key=api_key,
                mcp_servers=inline_mcp_servers(session),
            )
            agent = await client.agents.create(opts)
            async with agent:
                run = await agent.send(prompt)
                chunks: list[str] = []
                async for message in run.messages():
                    if stream:
                        print(message, file=sys.stderr)
                    if getattr(message, "type", None) != "assistant":
                        continue
                    inner = getattr(message, "message", None)
                    if inner is None:
                        continue
                    for block in getattr(inner, "content", ()) or ():
                        if getattr(block, "type", None) == "text":
                            chunks.append(getattr(block, "text", "") or "")
                run_result = await run.wait()
                text = "".join(chunks)
                if run_result.status == "error":
                    print(f"error: SDK run failed: {run_result.id}", file=sys.stderr)
                    return text, 1
                return text, 0
    except CursorAgentError as err:
        print(f"error: SDK startup failed: {err.message}", file=sys.stderr)
        return "", 1


def _run_sdk(session: str, prompt: str, *, stream: bool) -> tuple[str, int]:
    import asyncio

    return asyncio.run(_run_sdk_async(session, prompt, stream=stream))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one novel beat via Cursor SDK + MemNet MCP",
    )
    parser.add_argument(
        "--app",
        metavar="ID",
        help="Story instance id (applications/novel_cursor/instances/<ID>.json)",
    )
    parser.add_argument(
        "--seed",
        metavar="PATH",
        help="Seed markdown (application-notes/novel-*-initial-state.md); paths from USR14/USR15",
    )
    parser.add_argument("--session", help="MemNet session id (default: novel-output/.../session_id.txt)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--choice", type=int, metavar="N", help="Player choice 1–6")
    mode.add_argument("--steering", metavar="TEXT", help="Free-text steering")
    mode.add_argument(
        "--continue",
        dest="continue_beat",
        action="store_true",
        help="Resume mid-beat from USR23 stage",
    )
    parser.add_argument("--stream", action="store_true", help="Stream SDK events to stderr")
    args = parser.parse_args(argv)

    if args.choice is not None and not (1 <= args.choice <= 6):
        print("error: --choice must be 1–6", file=sys.stderr)
        return 2

    try:
        config = load_config(app_id=args.app, seed_md=args.seed)
    except (FileNotFoundError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    session = _read_session_id(config, args.session)

    if not _probe_serve():
        print(
            f"error: memnet serve not reachable at {SERVE_HOST}:{SERVE_PORT}; run memnet serve",
            file=sys.stderr,
        )
        return 1

    beat_stage, pf_code = _preflight_session(config, session)
    if pf_code != 0:
        return pf_code

    if args.continue_beat and beat_stage == "oln":
        print(
            "error: --continue but USR23 beat_stage is already oln; use --choice instead",
            file=sys.stderr,
        )
        return 2

    prompt = build_beat_prompt(
        config,
        session_id=session,
        beat_stage=beat_stage,
        choice=args.choice,
        steering=args.steering,
        continue_beat=args.continue_beat,
    )

    text, sdk_code = _run_sdk(session, prompt, stream=args.stream)
    if sdk_code != 0 and not text:
        return sdk_code

    snap_rel = str(config.snapshot_file.relative_to(repo_root())).replace("\\", "/")
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
            "snapshot_file": snap_rel,
            "beat_stage": "",
            "error": "no parseable JSON result from agent",
        }
        return _write_and_emit(config, fail)

    result = _normalise_result(raw, config, session)
    if sdk_code != 0 and result.get("exit_code") == 0:
        result["exit_code"] = sdk_code
    return _write_and_emit(config, result)


if __name__ == "__main__":
    sys.exit(main())
