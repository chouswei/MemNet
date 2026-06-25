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

from novel_mcp.chapter_io import beat_prose_finalize as do_beat_prose_finalize
from novel_mcp.chapter_io import chapter_prose_gate as do_chapter_prose_gate
from novel_mcp.zh_text import prose_status

mcp = FastMCP("novel-writer")


@mcp.tool()
async def prose_metrics(
    prose: str,
    min_chars: int | None = None,
    max_chars: int | None = None,
) -> str:
    """DEPRECATED for draft loops — use local scripts/prose_count.py (0 MCP).

    This tool always returns exit_code=1 to block MCP metric loops. Draft with
    `python scripts/prose_count.py`, then call beat_prose_finalize once.
    """
    status = prose_status(prose, min_chars=min_chars, max_chars=max_chars)
    payload = {
        **status,
        "exit_code": 1,
        "errors": [
            "@ERR: mcp_draft_forbidden|Use python scripts/prose_count.py locally; "
            "call beat_prose_finalize once when gate_ready=true"
        ],
        "mcp_forbidden": True,
        "local_draft_tool": "python scripts/prose_count.py --usr05 <USR05> --prose-file <path>",
        "mcp_budget_per_beat": 1,
        "allowed_novel_writer_tools_per_beat": ["beat_prose_finalize"],
    }
    return json.dumps(payload, ensure_ascii=False)


@mcp.tool()
async def beat_prose_finalize(
    prose: str,
    chapter_dir: str,
    chp_num: int,
    min_chars: int,
    max_chars: int,
    workspace_root: str | None = None,
    replace_last_paragraph: bool = False,
) -> str:
    """**Preferred — one MCP call per beat.** Metrics + chapter append.

    Draft with scripts/prose_count.py until gate_ready=true, then call this once.
    On gate_blocked, rewrite the full beat and re-run local prose_count — do not retry
    this tool with minor edits.
    """
    result = await anyio.to_thread.run_sync(
        lambda: do_beat_prose_finalize(
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
async def chapter_prose_gate(
    prose: str,
    chapter_dir: str,
    chp_num: int,
    min_chars: int | None = None,
    max_chars: int | None = None,
    workspace_root: str | None = None,
    replace_last_paragraph: bool = False,
) -> str:
    """LEGACY — prefer beat_prose_finalize (one MCP call per beat).

    Call only after local scripts/prose_count.py returns gate_ready=true.
    On gate_blocked, rewrite the full beat and re-run prose_count locally — do not retry
    this tool with minor edits (each retry wastes an MCP round-trip).
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
    min_chars: int | None = None,
    max_chars: int | None = None,
    workspace_root: str | None = None,
    replace_last_paragraph: bool = False,
) -> str:
    """Append (or replace last) one beat block to a chapter file.

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
