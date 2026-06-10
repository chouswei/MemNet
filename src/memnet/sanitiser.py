"""Input sanitiser for add/update batches."""

from __future__ import annotations

import re

from memnet.exceptions import MemNetError

_THINK_RE = re.compile(
    r"^<think>.*?</think>\s*",
    re.DOTALL | re.IGNORECASE,
)


def sanitise_line(line: str) -> str | None:
    line = line.strip()
    if not line or line.lstrip().startswith("#"):
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
    if not line.startswith("@"):
        raise MemNetError("invalid_line", "line must start with @TAG:")
    return line


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
