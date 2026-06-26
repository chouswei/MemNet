"""Workspace path resolution for novel output files (MCP cwd may differ from repo)."""

from __future__ import annotations

import os
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
REPO_ROOT = _PKG_DIR.parents[1]


def workspace_root(explicit: str | Path | None = None) -> Path:
    """Resolve novel output root: explicit arg → MEMNET_WORKSPACE_ROOT → package repo root."""
    if explicit:
        return Path(explicit)
    env = os.environ.get("MEMNET_WORKSPACE_ROOT")
    if env:
        return Path(env)
    return REPO_ROOT
