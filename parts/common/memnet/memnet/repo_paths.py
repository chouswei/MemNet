"""Resolve repository root by walking up for project markers."""

from __future__ import annotations

from pathlib import Path

_MARKERS = ("project.toml", "pyproject.toml")


def find_repo_root(start: Path | None = None) -> Path:
    """Return the MemNet repo root containing project.toml or pyproject.toml."""
    cur = (start or Path.cwd()).resolve()
    if cur.is_file():
        cur = cur.parent
    for candidate in (cur, *cur.parents):
        if any((candidate / m).is_file() for m in _MARKERS):
            return candidate
    raise RuntimeError(f"could not locate repo root from {start or Path.cwd()}")
