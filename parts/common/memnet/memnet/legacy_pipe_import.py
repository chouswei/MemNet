"""LegacyPipeImport — DEPRECATED one-shot @TAG pipe import (not agent dialect)."""

from __future__ import annotations

from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.models import Record, TagMap
from memnet.tag_map import parse_line


def looks_like_pipe(line: str) -> bool:
    s = line.strip()
    return bool(s) and not s.startswith("#") and s.startswith("@")


def import_pipe_lines(
    lines: list[str],
    tag_map: TagMap,
    caps: Caps | None = None,
) -> list[Record]:
    """Parse historical @TAG pipe rows into Records. Import once then discard dialect."""
    caps = caps or Caps()
    out: list[Record] = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if not looks_like_pipe(s):
            raise MemNetError("mixed_dialect", "legacy pipe batch contains non-pipe line")
        out.append(parse_line(s, tag_map, caps))
    return out
