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
from novel_mcp.bootstrap import bootstrap_from_md
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
    include_warm: bool = False,
    since_modified: str | None = None,
    walk_filter: str = "law_usr",
    lib_query: bool = False,
) -> str:
    """**Novel pipeline — call 1 of 2 per beat.** Presentation + pipeline (same session as memnet-mcp).

    Prefer ``presentation.contracts`` over raw warm. Set ``include_warm=true`` only for audit.
    Pass ``since_modified`` from the prior begin/finish to detect stale graph edits via memnet.
    Set ``lib_query=true`` when player chose option 6 (soul library) — injects ``library_contracts``.
    """
    result = await anyio.to_thread.run_sync(
        lambda: do_beat_turn_begin(
            session=session,
            anchor=anchor,
            depth=depth,
            max_rows=max_rows,
            include_warm=include_warm,
            since_modified=since_modified,
            walk_filter=walk_filter,
            lib_query=lib_query,
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
    option_lines: list[str] | None = None,
    since_modified: str | None = None,
) -> str:
    """**Novel pipeline — call 2 of 2 per beat.** Atomic commit on the shared memnet session.

    Optional ``option_lines`` (1–6 strings) validated against seed LAW tokens.
    Pass ``since_modified`` from ``beat_turn_begin.session_modified``.
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
            option_lines=option_lines,
            since_modified=since_modified,
        )
    )
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def bootstrap_from_seed(
    md_path: str,
) -> str:
    """Open a memnet session from an application seed markdown (tag map + opening seed fences)."""
    result = await anyio.to_thread.run_sync(lambda: bootstrap_from_md(md_path))
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def prose_metrics(
    prose: str,
    min_chars: int | None = None,
    max_chars: int | None = None,
) -> str:
    """DEPRECATED — use local scripts/prose_count.py; prefer beat_turn_begin/finish."""
    status = prose_status(prose, min_chars=min_chars, max_chars=max_chars)
    payload = {
        **status,
        "exit_code": 1,
        "errors": [
            "@ERR: mcp_draft_forbidden|Use beat_turn_begin + beat_turn_finish; "
            "local scripts/prose_count.py for length checks"
        ],
        "mcp_forbidden": True,
        "deprecated": True,
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
    """DEPRECATED — use beat_turn_finish (single commit on shared session)."""
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
    out = {**result, "deprecated": True}
    return json.dumps(out, ensure_ascii=False)


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
    """DEPRECATED — use beat_turn_finish."""
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
    out = {**result, "deprecated": True}
    return json.dumps(out, ensure_ascii=False)


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
    """DEPRECATED — use beat_turn_finish."""
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
