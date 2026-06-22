"""Novel writer MCP server — prose length gates and chapter file I/O (not MemNet graph)."""

from __future__ import annotations

import json

try:
    import anyio
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError(
        "novel-mcp requires the mcp package. Install with: pip install memnet-llm[novel-mcp]"
    ) from exc

from novel_mcp.chapter_io import chapter_prose_gate as do_chapter_prose_gate
from novel_mcp.zh_text import prose_status

mcp = FastMCP("novel-writer")


@mcp.tool()
async def prose_metrics(
    prose: str,
    min_chars: int = 300,
    max_chars: int = 600,
) -> str:
    """Count Traditional Chinese narrative chars (RULE09). No file I/O.

    Returns count, ok, short_by, long_by, min, max, hint. Use before chapter append.
    """
    payload = prose_status(prose, min_chars=min_chars, max_chars=max_chars)
    payload["exit_code"] = 0
    payload["errors"] = []
    return json.dumps(payload, ensure_ascii=False)


@mcp.tool()
async def chapter_prose_gate(
    prose: str,
    chapter_dir: str,
    chp_num: int,
    min_chars: int = 300,
    max_chars: int = 600,
    workspace_root: str | None = None,
    replace_last_paragraph: bool = False,
) -> str:
    """Preferred step-2 entry: metrics + append in one call (no separate prose_metrics).

    Fails without writing when prose is outside min_chars..max_chars. Returns count, ok,
    appended_chars, file_char_total, paragraph_count, path, hint. workspace_root defaults to cwd.
    """
    result = await anyio.to_thread.run_sync(
        lambda: do_chapter_prose_gate(
            prose,
            chapter_dir=chapter_dir,
            chp_num=chp_num,
            workspace_root=workspace_root,
            min_chars=min_chars,
            max_chars=max_chars,
            replace_last_paragraph=replace_last_paragraph,
        )
    )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def chapter_prose_append(
    prose: str,
    chapter_dir: str,
    chp_num: int,
    min_chars: int = 300,
    max_chars: int = 600,
    workspace_root: str | None = None,
    replace_last_paragraph: bool = False,
) -> str:
    """Validate prose length and append (or replace last) one beat block to a chapter file.

    Prefer chapter_prose_gate for step 2 (same behaviour, one call).
    """
    return await chapter_prose_gate(
        prose,
        chapter_dir,
        chp_num,
        min_chars=min_chars,
        max_chars=max_chars,
        workspace_root=workspace_root,
        replace_last_paragraph=replace_last_paragraph,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
