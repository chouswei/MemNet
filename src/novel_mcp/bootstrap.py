"""Bootstrap a novel session from an application-notes markdown seed file."""

from __future__ import annotations

import re
from pathlib import Path

from memnet_mcp.client import run_memnet


def fence_lines(text: str, heading: str) -> list[str]:
    pattern = rf"## {re.escape(heading)}\s*\n(?:\s*\n)*```text\s*\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        pattern2 = rf"## {re.escape(heading)}[\s\S]*?```text\s*\n([\s\S]*?)\n```"
        match = re.search(pattern2, text)
        if not match:
            return []
    return [ln for ln in match.group(1).strip().splitlines() if ln.strip()]


def seed_lines_from_md(text: str) -> list[str]:
    engine = fence_lines(text, "Opening seed — Engine")
    world = fence_lines(text, "Opening seed — World")
    if engine or world:
        return engine + world
    legacy = fence_lines(text, "Opening seed")
    if not legacy:
        raise ValueError("no seed fence found (Engine / World / Opening seed)")
    return legacy


def bootstrap_from_md(md_path: str | Path) -> dict:
    """Open session, ingest tag map + seed fences; return session_id and exit codes."""
    path = Path(md_path)
    text = path.read_text(encoding="utf-8")
    map_lines = fence_lines(text, "Tag map")
    if not map_lines:
        raise ValueError("section not found: Tag map")
    seeds = seed_lines_from_md(text)

    argv = ["session", "open"]
    for line in map_lines:
        argv.extend(["--map", line])
    open_resp = run_memnet(argv)
    if open_resp.exit_code != 0:
        return {
            "exit_code": open_resp.exit_code,
            "errors": open_resp.errors,
            "stderr": open_resp.stderr,
        }

    sid = open_resp.session_id
    seed_resp = run_memnet(
        ["add", "--stdin", "--allow-new-relation"],
        stdin="\n".join(seeds),
        session=sid,
    )
    return {
        "exit_code": seed_resp.exit_code if seed_resp.exit_code != 0 else 0,
        "session_id": sid,
        "seed_exit_code": seed_resp.exit_code,
        "errors": seed_resp.errors,
        "stderr": seed_resp.stderr,
        "seed_lines": len(seeds),
        "map_lines": len(map_lines),
    }
