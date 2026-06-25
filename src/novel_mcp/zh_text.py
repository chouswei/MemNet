"""Traditional Chinese character counting for novel prose (RULE09)."""

from __future__ import annotations

import re

_ZH_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")


def count_zh_chars(text: str) -> int:
    """Count CJK unified + extension A characters (same basis as RULE09)."""
    return len(_ZH_RE.findall(text))


def parse_scene_band(usr05: str) -> tuple[int, int]:
    """Parse USR05 scene_length codes like 650_950_zh → (650, 950)."""
    parts = usr05.strip().split("_")
    if len(parts) < 2:
        raise ValueError(f"invalid USR05 band: {usr05!r}")
    return int(parts[0]), int(parts[1])


def prose_status(
    text: str,
    *,
    min_chars: int | None = None,
    max_chars: int | None = None,
) -> dict[str, int | bool | str | None]:
    """Count zh chars; length gate only when both min_chars and max_chars are set."""
    count = count_zh_chars(text)
    if min_chars is None or max_chars is None:
        return {
            "count": count,
            "ok": True,
            "gate_ready": False,
            "short_by": 0,
            "long_by": 0,
            "min": min_chars,
            "max": max_chars,
            "target_chars": None,
            "draft_vs_target": None,
            "status": "count_only",
            "hint": "",
            "next_action": "python scripts/prose_count.py --usr05 <USR05> --prose-file <beat.txt>",
            "forbidden_until_gate_ready": "prose_metrics;chapter_prose_gate;beat_prose_finalize",
        }
    short_by = max(0, min_chars - count)
    long_by = max(0, count - max_chars)
    ok = short_by == 0 and long_by == 0
    target = (min_chars + max_chars) // 2
    draft_vs_target = count - target
    if ok:
        status = "ok"
        hint = ""
        next_action = "beat_prose_finalize once (same min_chars/max_chars)"
        forbidden = ""
    elif short_by > 0:
        status = "short"
        hint = f"expand ~{short_by} zh chars; aim for target_chars ~{target}"
        next_action = "rewrite full beat from @OLN, then scripts/prose_count.py (no MCP)"
        forbidden = "prose_metrics;chapter_prose_gate;beat_prose_finalize; incremental padding"
    else:
        status = "long"
        hint = f"trim ~{long_by} zh chars"
        next_action = "trim beat, then scripts/prose_count.py (no MCP)"
        forbidden = "prose_metrics;chapter_prose_gate;beat_prose_finalize"
    return {
        "count": count,
        "ok": ok,
        "gate_ready": ok,
        "short_by": short_by,
        "long_by": long_by,
        "min": min_chars,
        "max": max_chars,
        "target_chars": target,
        "draft_vs_target": draft_vs_target,
        "status": status,
        "hint": hint,
        "next_action": next_action,
        "forbidden_until_gate_ready": forbidden,
    }
