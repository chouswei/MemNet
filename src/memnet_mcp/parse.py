"""Parse MemNet wire control lines from CLI stdout/stderr."""

from __future__ import annotations

import os
import re

_SESSION_RE = re.compile(r"^@SESSION:\s*(\S+)")
_ERR_RE = re.compile(r"^@ERR:\s*(.+)$")


def extract_session_id(stdout: str, stderr: str) -> str | None:
    for block in (stdout, stderr):
        for line in block.splitlines():
            m = _SESSION_RE.match(line.strip())
            if m:
                sid = m.group(1).split("|", 1)[0].strip()
                if sid and sid != "none":
                    return sid
    env = os.environ.get("MEMNET_SESSION")
    return env if env else None


def extract_errors(stderr: str) -> list[str]:
    errors: list[str] = []
    for line in stderr.splitlines():
        m = _ERR_RE.match(line.strip())
        if m:
            errors.append(line.strip())
    return errors
