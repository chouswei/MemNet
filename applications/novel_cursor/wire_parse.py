"""Parse wire lines and prose JSON from LLM drafts."""

from __future__ import annotations

import json
import re
from typing import Any

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_STAGE_TAGS = {"oln": "OLN", "sbd": "SBD", "scr": "SCR"}


def extract_wire_lines(text: str, stage: str) -> list[str]:
    """Return @OLN/@SBD/@SCR lines for the given stage."""
    tag = _STAGE_TAGS.get(stage.lower())
    if not tag:
        return []
    prefix = f"@{tag}:"
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            lines.append(line)
    return lines


def parse_prose_payload(text: str) -> dict[str, Any] | None:
    """Parse prose beat JSON (prose + options + hud)."""
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


def normalise_options(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return [""] * 6
    opts = [str(o) for o in raw[:6]]
    while len(opts) < 6:
        opts.append("")
    return opts
