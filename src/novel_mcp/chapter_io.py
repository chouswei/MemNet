"""Chapter file append/replace for novel output (LAW-OUT01)."""

from __future__ import annotations

import re
from pathlib import Path

from novel_mcp.zh_text import count_zh_chars, prose_status

_DIGITS = "零一二三四五六七八九"
_PARA_SPLIT = re.compile(r"\n\s*\n")


def zh_chapter_label(chp_num: int) -> str:
    """Arabic chapter number to Chinese label (e.g. 1 → 一, 12 → 十二)."""
    if chp_num <= 0:
        return str(chp_num)
    if chp_num < 10:
        return _DIGITS[chp_num]
    if chp_num < 20:
        ones = chp_num % 10
        return "十" + (_DIGITS[ones] if ones else "")
    if chp_num < 100:
        tens, ones = divmod(chp_num, 10)
        head = _DIGITS[tens] + "十"
        return head + (_DIGITS[ones] if ones else "")
    return str(chp_num)


def chapter_heading(chp_num: int) -> str:
    return f"# 第{zh_chapter_label(chp_num)}回"


def chapter_file_path(workspace_root: Path | str, chapter_dir: str, chp_num: int) -> Path:
    return Path(workspace_root) / chapter_dir / f"第{chp_num:03d}回.md"


def _split_chapter_content(text: str) -> tuple[str | None, list[str]]:
    """Return (heading_line, prose_paragraphs). Paragraphs split on blank lines."""
    lines = text.splitlines()
    heading: str | None = None
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") and heading is None:
            heading = stripped
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).strip()
    if not body:
        return heading, []
    paragraphs = [p.strip() for p in _PARA_SPLIT.split(body) if p.strip()]
    return heading, paragraphs


def file_char_total(paragraphs: list[str]) -> int:
    return sum(count_zh_chars(p) for p in paragraphs)


def chapter_prose_gate(
    prose: str,
    *,
    chapter_dir: str,
    chp_num: int,
    workspace_root: Path | str | None = None,
    min_chars: int | None = None,
    max_chars: int | None = None,
    replace_last_paragraph: bool = False,
) -> dict:
    """Append one beat block; optional length gate when min_chars and max_chars both set."""
    status = prose_status(prose, min_chars=min_chars, max_chars=max_chars)
    root = Path(workspace_root or Path.cwd())
    path = chapter_file_path(root, chapter_dir, chp_num)

    if not status["ok"]:
        return {
            "exit_code": 1,
            "errors": [f"@ERR: prose_{status['status']}|{status['hint']}"],
            "path": str(path),
            "gate_blocked": True,
            "mcp_retry_forbidden": True,
            "local_draft_tool": "python scripts/prose_count.py --usr05 <USR05> --prose-file <beat.txt>",
            **status,
        }

    prose = prose.strip()
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        heading, paragraphs = _split_chapter_content(existing)
    else:
        heading = None
        paragraphs = []

    if replace_last_paragraph:
        if not paragraphs:
            return {
                "exit_code": 1,
                "errors": ["@ERR: no_paragraph|replace_last requires an existing paragraph"],
                "path": str(path),
                **status,
            }
        paragraphs[-1] = prose
    else:
        paragraphs.append(prose)

    if heading is None:
        heading = chapter_heading(chp_num)

    out_lines = [heading, ""]
    for para in paragraphs:
        for line in para.splitlines():
            out_lines.append(line)
        out_lines.append("")
    while out_lines and out_lines[-1] == "":
        out_lines.pop()
    content = "\n".join(out_lines) + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    total = file_char_total(paragraphs)
    return {
        "exit_code": 0,
        "errors": [],
        "gate_blocked": False,
        "appended_chars": status["count"],
        "file_char_total": total,
        "paragraph_count": len(paragraphs),
        "path": str(path),
        "replaced_last": replace_last_paragraph,
        **status,
    }


def chapter_prose_append(
    prose: str,
    *,
    chapter_dir: str,
    chp_num: int,
    workspace_root: Path | str | None = None,
    min_chars: int | None = None,
    max_chars: int | None = None,
    replace_last_paragraph: bool = False,
) -> dict:
    """Alias for chapter_prose_gate (backward compatible)."""
    return chapter_prose_gate(
        prose,
        chapter_dir=chapter_dir,
        chp_num=chp_num,
        workspace_root=workspace_root,
        min_chars=min_chars,
        max_chars=max_chars,
        replace_last_paragraph=replace_last_paragraph,
    )


def beat_prose_finalize(
    prose: str,
    *,
    chapter_dir: str,
    chp_num: int,
    min_chars: int,
    max_chars: int,
    workspace_root: Path | str | None = None,
    replace_last_paragraph: bool = False,
) -> dict:
    """Single MCP entry per beat: metrics check + chapter append. Requires min/max."""
    result = chapter_prose_gate(
        prose,
        chapter_dir=chapter_dir,
        chp_num=chp_num,
        workspace_root=workspace_root,
        min_chars=min_chars,
        max_chars=max_chars,
        replace_last_paragraph=replace_last_paragraph,
    )
    result["tool"] = "beat_prose_finalize"
    result["mcp_budget_per_beat"] = 1
    return result
