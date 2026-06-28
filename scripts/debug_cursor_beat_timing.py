#!/usr/bin/env python3
"""Time cursor_beat local phases (no SDK) for latency debug."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from memnet_mcp.client import run_memnet
from novel_mcp.beat_pipeline import beat_turn_begin
from novel_mcp.play_context import read_beat_stage, script_beat_prepare

SNAP = ROOT / "novel-output" / "shenjia_caifa" / "session_snap.json"
SID_FILE = ROOT / "novel-output" / "shenjia_caifa" / "session_id.txt"


def _tick(label: str, t0: float) -> float:
    dt = time.perf_counter() - t0
    print(f"  {label}: {dt:.2f}s")
    return time.perf_counter()


def main() -> int:
    sid = SID_FILE.read_text(encoding="utf-8").strip().splitlines()[0]
    print(f"session={sid}")

    t = time.perf_counter()
    ld = run_memnet(["session", "load", "--file", str(SNAP), "--keep-id"])
    t = _tick(f"session_load exit={ld.exit_code} errors={ld.errors[:1]}", t)

    t = _tick(f"read_beat_stage -> {read_beat_stage(sid)}", t)

    prep = script_beat_prepare(
        session=sid,
        choice=1,
        snapshot_file="novel-output/shenjia_caifa/session_snap.json",
        chapter_dir="novel-output/shenjia_caifa/chapters",
    )
    warm = (prep.get("begin") or {}).get("warm_stdout") or ""
    t = _tick(
        f"script_beat_prepare exit={prep.get('exit_code')} warm_lines={len(warm.splitlines())}",
        t,
    )

    for i in range(3):
        t0 = time.perf_counter()
        b = beat_turn_begin(session=sid, include_warm=True)
        print(
            f"  beat_turn_begin #{i + 1}: {time.perf_counter() - t0:.2f}s "
            f"exit={b.get('exit_code')} lines={len((b.get('warm_stdout') or '').splitlines())}"
        )

    for name in ("DEEPSEEK_API_KEY", "LLM_API_KEY", "LLM_API_KEY_SCRIPT", "LLM_API_KEY_PROSE"):
        if os.environ.get(name, "").strip():
            print(f"{name}: set")
            break
    else:
        print("DEEPSEEK_API_KEY: missing")

    print("\nExpected orchestrated beat wall time (rough):")
    print("  local MCP (prepare + 4x begin/finish)     <5s")
    print("  LLM drafts (4x DeepSeek HTTP)             ~1-4 min total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
