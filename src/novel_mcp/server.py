"""Novel writer MCP server — beat orchestration, prose gates, chapter file I/O.

Uses memnet serve via ``run_memnet`` (same session id as memnet-mcp). Graph primitives
remain on memnet-mcp; per-beat pipeline is here (LAW-PIPE21).
"""

from __future__ import annotations

import json

try:
    import anyio
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError(
        "novel-mcp requires the mcp package. Install with: pip install memnet-llm[novel-mcp]"
    ) from exc

from novel_mcp.beat_pipeline import beat_turn_begin as do_beat_turn_begin
from novel_mcp.beat_pipeline import beat_turn_finish as do_beat_turn_finish
from novel_mcp.chapter_io import beat_prose_finalize as do_beat_prose_finalize
from novel_mcp.chapter_io import chapter_prose_gate as do_chapter_prose_gate
from novel_mcp.zh_text import prose_status

mcp = FastMCP("novel-writer")


@mcp.tool()
async def beat_turn_begin(
    session: str | None = None,
    anchor: str = "STEP01",
    depth: int = 2,
    max_rows: int = 55,
) -> str:
    """**Novel pipeline — call 1 of 2 per beat.** Warm read + parsed USR05/STEP/OLN/CHP.

    Shares MemNet session with memnet-mcp (pass the same session id).
    Returns pipeline, finish_params, and warm_stdout.
    """
    result = await anyio.to_thread.run_sync(
        lambda: do_beat_turn_begin(
            session=session,
            anchor=anchor,
            depth=depth,
            max_rows=max_rows,
        )
    )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def beat_turn_finish(
    session: str | None = None,
    prose: str | None = None,
    chapter_dir: str | None = None,
    chp_num: int | None = None,
    min_chars: int | None = None,
    max_chars: int | None = None,
    usr05_band: str | None = None,
    add_lines: list[str] | None = None,
    update_lines: list[str] | None = None,
    oln_lines: list[str] | None = None,
    oln_mode: str = "add",
    sbd_lines: list[str] | None = None,
    sbd_mode: str = "add",
    scr_lines: list[str] | None = None,
    scr_mode: str = "add",
    snapshot_file: str | None = None,
    workspace_root: str | None = None,
    replace_last_paragraph: bool = False,
    allow_new_relation: bool = False,
    prose_only_gate: bool = False,
    pipeline_bypass: bool = False,
) -> str:
    """**Novel pipeline — call 2 of 2 per beat.** Atomic: OLN→SBD→SCR→prose (LAW-PIPE20) → chapter → graph → save.

    Shares MemNet session with memnet-mcp. chapter_dir/chp_num/snapshot_file auto-filled from warm when omitted.
    """
    result = await anyio.to_thread.run_sync(
        lambda: do_beat_turn_finish(
            session=session,
            prose=prose,
            chapter_dir=chapter_dir,
            chp_num=chp_num,
            min_chars=min_chars,
            max_chars=max_chars,
            usr05_band=usr05_band,
            add_lines=add_lines,
            update_lines=update_lines,
            oln_lines=oln_lines,
            oln_mode=oln_mode,
            sbd_lines=sbd_lines,
            sbd_mode=sbd_mode,
            scr_lines=scr_lines,
            scr_mode=scr_mode,
            snapshot_file=snapshot_file,
            workspace_root=workspace_root,
            replace_last_paragraph=replace_last_paragraph,
            allow_new_relation=allow_new_relation,
            prose_only_gate=prose_only_gate,
            pipeline_bypass=pipeline_bypass,
        )
    )
    return json.dumps(result, ensure_ascii=False)


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
