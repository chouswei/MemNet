"""Bootstrap 工匠傳奇 session from novel-shenjia-initial-state.md."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from memnet_mcp.client import run_memnet
from memnet.config import serve_host
from novel_mcp.beat_pipeline import beat_turn_begin

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "application-notes" / "novel-shenjia-initial-state.md"


def _fence_lines(text: str, heading: str) -> list[str]:
    # tolerate optional blank lines between heading and opening ```text fence
    pattern = rf"## {re.escape(heading)}\s*\n(?:\s*\n)*```text\s*\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        # broader fallback
        pattern2 = rf"## {re.escape(heading)}[\s\S]*?```text\s*\n([\s\S]*?)\n```"
        match = re.search(pattern2, text)
        if not match:
            return []
    return [ln for ln in match.group(1).strip().splitlines() if ln.strip()]


def _seed_lines(text: str) -> list[str]:
    """Engine first, then World; legacy single Opening seed fence still supported."""
    engine = _fence_lines(text, "Opening seed — Engine")
    world = _fence_lines(text, "Opening seed — World")
    if engine or world:
        return engine + world
    legacy = _fence_lines(text, "Opening seed")
    if not legacy:
        raise SystemExit("no seed fence found (Engine / World / Opening seed)")
    return legacy


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    map_lines = _fence_lines(text, "Tag map")
    if not map_lines:
        raise SystemExit("section not found: Tag map")
    seed_lines = _seed_lines(text)

    argv = ["session", "open"]
    for line in map_lines:
        argv.extend(["--map", line])
    resp = run_memnet(argv)
    if resp.exit_code != 0:
        print(resp.stderr, file=sys.stderr)
        raise SystemExit(resp.exit_code)

    sid = resp.session_id
    seed_resp = run_memnet(
        ["add", "--stdin", "--allow-new-relation"],
        stdin="\n".join(seed_lines),
        session=sid,
    )
    if seed_resp.exit_code != 0:
        print(seed_resp.stderr, file=sys.stderr)
        raise SystemExit(seed_resp.exit_code)

    begin = beat_turn_begin(session=sid)
    out = {
        "session_id": sid,
        "serve_host": serve_host(),
        "exit_code": begin.get("exit_code"),
        "pipeline": begin.get("pipeline"),
        "pc_name_unset": "USR03|pc_name|未定" in begin.get("warm_stdout", ""),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
