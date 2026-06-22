"""Traditional Chinese character counting for novel prose (RULE09)."""

from __future__ import annotations

import re

_ZH_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def count_zh_chars(text: str) -> int:
    """Count CJK unified + extension A characters (same basis as RULE09)."""
    return len(_ZH_RE.findall(text))


def prose_status(
    text: str,
    *,
    min_chars: int = 300,
    max_chars: int = 600,
) -> dict[str, int | bool | str]:
    count = count_zh_chars(text)
    short_by = max(0, min_chars - count)
    long_by = max(0, count - max_chars)
    ok = short_by == 0 and long_by == 0
    if ok:
        status = "ok"
        hint = ""
    elif short_by > 0:
        status = "short"
        hint = f"expand ~{short_by} zh chars before append"
    else:
        status = "long"
        hint = f"trim ~{long_by} zh chars"
    return {
        "count": count,
        "ok": ok,
        "short_by": short_by,
        "long_by": long_by,
        "min": min_chars,
        "max": max_chars,
        "status": status,
        "hint": hint,
    }
