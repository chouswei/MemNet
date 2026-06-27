"""Compile walk presentation from MemNet wire output (novel-writer fallback)."""

from __future__ import annotations

import re

from memnet.context_view import format_walk_hop
from memnet_mcp.client import run_memnet

_WALK_RE = re.compile(r"^@WALK:\s*(.+?)\s*-\[([^\]]+)\]->\s*(.+)$")

_GOVERNS_RELATIONS = frozenset({"governs", "features", "constrains", "applies_to"})


def hops_from_wire(stdout: str, *, max_rows: int = 55) -> list[tuple[str, str, str]]:
    hops: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("@EDG:"):
            continue
        parts = stripped[5:].strip().split("|")
        if len(parts) < 4:
            continue
        src, rel, dst = parts[1], parts[2], parts[3]
        if not src or not rel or not dst:
            continue
        key = (src, rel, dst)
        if key in seen:
            continue
        seen.add(key)
        hops.append(key)
        if len(hops) >= max_rows:
            break
    return sorted(hops)


def walk_stdout_from_wire(stdout: str, *, max_rows: int = 55) -> str:
    lines = [format_walk_hop(s, r, d) for s, r, d in hops_from_wire(stdout, max_rows=max_rows)]
    return "\n".join(lines) + ("\n" if lines else "")


def fetch_warm_walk(
    *,
    session: str | None,
    anchor: str,
    depth: int,
    max_rows: int,
) -> str:
    """Prefer ``query walk``; fall back to ``query neighbors`` wire on stale serve."""
    walk_resp = run_memnet(
        [
            "query",
            "walk",
            "--anchor",
            anchor,
            "--depth",
            str(depth),
            "--max-rows",
            str(max_rows),
        ],
        session=session,
    )
    if walk_resp.exit_code == 0 and walk_resp.stdout.strip():
        return walk_resp.stdout

    nb = run_memnet(
        ["query", "neighbors", anchor, "--depth", str(depth)],
        session=session,
    )
    if nb.exit_code == 0:
        compiled = walk_stdout_from_wire(nb.stdout, max_rows=max_rows)
        if compiled.strip():
            return compiled
    return ""


def hops_from_walk_stdout(stdout: str) -> list[tuple[str, str, str]]:
    hops: list[tuple[str, str, str]] = []
    for line in stdout.splitlines():
        m = _WALK_RE.match(line.strip())
        if m:
            hops.append((m.group(1), m.group(2), m.group(3)))
    return hops


def curated_walk_lines(
    warm_walk: str,
    *,
    walk_filter: str = "governs",
    max_rows: int = 12,
) -> list[str]:
    """Filter hops for presentation; novel-agnostic relation/tag heuristics."""
    hops = hops_from_walk_stdout(warm_walk) or [
        (s, r, d) for s, r, d in hops_from_wire(warm_walk, max_rows=max_rows * 4)
    ]
    out: list[str] = []
    for src, rel, dst in hops:
        if walk_filter == "governs" and rel not in _GOVERNS_RELATIONS:
            continue
        if walk_filter == "law_usr" and not (
            dst.startswith("LAW") or dst.startswith("USR") or src.startswith("USR")
        ):
            continue
        line = format_walk_hop(src, rel, dst).replace("@WALK: ", "")
        out.append(line)
        if len(out) >= max_rows:
            break
    return out

