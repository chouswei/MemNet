"""Input sanitiser for add/update batches (pipe + Tier A)."""

from __future__ import annotations

import re

from memnet.exceptions import MemNetError

_THINK_RE = re.compile(
    r"^<think>.*?</think>\s*",
    re.DOTALL | re.IGNORECASE,
)


def _looks_like_tier_a(line: str) -> bool:
    if line.startswith("##"):
        return True
    if line.startswith(("+", "~", "-")):
        return True
    # Match mutate_gate.looks_like_tier_a: LAW01… / LAW-CODE01 / LAW_SNAP01
    if line.startswith("LAW") and len(line) > 3 and (line[3].isdigit() or line[3] in "-_"):
        return True
    return False


def sanitise_line(line: str) -> str | None:
    line = line.strip()
    if not line or line.lstrip().startswith("#") and not line.startswith("##"):
        return None
    line = _THINK_RE.sub("", line).strip()
    line = line.strip("`").strip()
    if not line:
        return None
    if line[0] in "{[":
        raise MemNetError(
            "json_not_supported",
            "MemNet uses wire format not JSON",
            example="@PLR: P01|Alice|10",
        )
    if line.startswith("@") or _looks_like_tier_a(line):
        return line
    raise MemNetError("invalid_line", "line must start with @TAG: or Tier A op")


def _to_text(raw: str | bytes) -> str:
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MemNetError("encoding", "input must be UTF-8") from exc
    return raw


def sanitise_batch(raw_lines: list[str | bytes], *, strip_fences: bool = True) -> list[str]:
    lines = [_to_text(r) for r in raw_lines]
    if strip_fences and lines:
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
    out: list[str] = []
    for text in lines:
        cleaned = sanitise_line(text)
        if cleaned:
            out.append(cleaned)
    return out
