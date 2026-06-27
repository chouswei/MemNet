"""Session metadata via memnet CLI (shared across MCPs)."""

from __future__ import annotations

import re

from memnet_mcp.client import run_memnet

_SESSION_RE = re.compile(r"^@SESSION:\s*(\S+)\|([^|]*)\|?(.*)$")


def fetch_session_modified(session: str | None) -> str | None:
    if not session:
        return None
    resp = run_memnet(["session", "current"], session=session)
    if resp.exit_code != 0:
        return None
    for line in resp.stdout.splitlines():
        m = _SESSION_RE.match(line.strip())
        if m and m.group(1) not in ("none", ""):
            mod = (m.group(3) or "").strip()
            return mod if mod and mod != "-" else None
    return None
