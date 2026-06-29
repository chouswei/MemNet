"""Parse wire lines and prose JSON from LLM drafts."""

from __future__ import annotations

import json
import re
from typing import Any

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_STAGE_TAGS = ("OLN", "SBD", "SCR")


def _extract_tag_lines(text: str, tag: str) -> list[str]:
    prefix = f"@{tag}:"
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(prefix):
            lines.append(line)
    return lines


def extract_draft_bundle(text: str) -> tuple[list[str], list[str], list[str]]:
    """Return (oln_lines, sbd_lines, scr_lines) — each line starts with @TAG:"""
    return (
        _extract_tag_lines(text, "OLN"),
        _extract_tag_lines(text, "SBD"),
        _extract_tag_lines(text, "SCR"),
    )


def extract_scr_lines(text: str) -> list[str]:
    """script_review: extract @SCR lines only."""
    return _extract_tag_lines(text, "SCR")


def extract_wire_lines(text: str, stage: str) -> list[str]:
    """Return wire lines for a script stage (legacy helper)."""
    stage = stage.lower()
    if stage == "script_draft":
        oln, sbd, scr = extract_draft_bundle(text)
        return oln + sbd + scr
    if stage == "script_review":
        return extract_scr_lines(text)
    tag_map = {"oln": "OLN", "sbd": "SBD", "scr": "SCR"}
    tag = tag_map.get(stage)
    if not tag:
        return []
    return _extract_tag_lines(text, tag)


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
