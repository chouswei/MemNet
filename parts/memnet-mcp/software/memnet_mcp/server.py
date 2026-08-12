"""MemNet MCP server — stdio (default) or opt-in streamable-http."""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import anyio
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError(
        "memnet-mcp requires the mcp package. Install with: pip install memnet-llm[mcp]"
    ) from exc

from memnet.config import serve_host, serve_port
from memnet.serve import probe
from memnet_mcp.client import MemNetResponse, run_memnet
from memnet_mcp.http_transport import (
    DEFAULT_MCP_HTTP_HOST,
    DEFAULT_MCP_HTTP_PATH,
    DEFAULT_MCP_HTTP_PORT,
    McpHttpBindError,
    mcp_http_host,
    mcp_http_path,
    mcp_http_port,
    run_streamable_http,
)
from memnet_mcp.seed import supplement_seed_lines

mcp = FastMCP("memnet")


def _json(resp: MemNetResponse) -> str:
    return resp.to_json()


async def _run(argv: list[str], *, stdin: str | None = None, session: str | None = None) -> str:
    resp = await anyio.to_thread.run_sync(
        lambda: run_memnet(argv, stdin=stdin, session=session),
    )
    return _json(resp)


@mcp.tool()
async def serve_status() -> str:
    """Transport probe for TCP ``memnet serve`` (optional under default in-process)."""
    return json.dumps(
        {
            "running": probe(),
            "host": serve_host(),
            "port": serve_port(),
        }
    )


@mcp.tool()
async def session_open(
    map_lines: list[str] | None = None,
    map_file: str | None = None,
    ttl: int | None = None,
    seed_lines: list[str] | None = None,
    allow_new_relation: bool = False,
) -> str:
    """Open a new MemNet session with a tag map (map_lines preferred over map_file).

    Optional seed_lines are added via add --stdin immediately after open (e.g. CFG/domain
    rows). Core LAW01–LAW05 are auto-included when missing (GQL by default; pipe only
    when seed_lines are legacy @TAG) so every warm/pin map carries engine invariants.

    Set allow_new_relation=True when seed_lines include EDG relations beyond
    relations.seed.txt (session_open default vocabulary); otherwise the seed batch will
    abort on the first unknown relation and roll back, leaving the session empty.
    """
    if map_file:
        argv: list[str] = ["session", "open", "--map-file", map_file]
    elif map_lines:
        argv = ["session", "open"]
        for line in map_lines:
            argv.extend(["--map", line])
    else:
        return _json(
            MemNetResponse(
                exit_code=1,
                stdout="",
                stderr="@ERR: no_map|provide map_lines or map_file\n",
                session_id=os.environ.get("MEMNET_SESSION"),
                errors=["@ERR: no_map|provide map_lines or map_file"],
            )
        )
    if ttl is not None:
        argv.extend(["--ttl", str(ttl)])

    open_resp = await anyio.to_thread.run_sync(lambda: run_memnet(argv))
    effective_seed = supplement_seed_lines(seed_lines)
    if open_resp.exit_code == 0 and open_resp.session_id and effective_seed:
        add_argv = ["add", "--stdin"]
        if allow_new_relation:
            add_argv.append("--allow-new-relation")
        seed_resp = await anyio.to_thread.run_sync(
            lambda: run_memnet(
                add_argv,
                stdin="\n".join(effective_seed),
                session=open_resp.session_id,
            )
        )
        return _json(MemNetResponse.merge(open_resp, seed_resp))
    return _json(open_resp)


@mcp.tool()
async def session_current(session: str | None = None) -> str:
    """Return the current session id and TTL metadata."""
    return await _run(["session", "current"], session=session)


@mcp.tool()
async def session_load(
    file: str,
    keep_id: bool = True,
    ttl: int | None = None,
) -> str:
    """Load a snapshot file into the MemNet graph (restores session state).

    Works in-process (default) or via TCP ``memnet serve`` when configured.
    Returns session id in stdout/stderr. Does not require an existing session.
    Use before pin_map / add / update when resuming mid-task.
    """
    argv = ["session", "load", "--file", file]
    if keep_id:
        argv.append("--keep-id")
    if ttl is not None:
        argv.extend(["--ttl", str(ttl)])
    resp = await anyio.to_thread.run_sync(lambda: run_memnet(argv))
    return _json(resp)


@mcp.tool()
async def session_save(
    file: str,
    session: str | None = None,
) -> str:
    """Write the current session graph to a snapshot file."""
    return await _run(["session", "save", "--file", file], session=session)


async def _pin_map(
    anchor: str,
    depth: int = 2,
    max_rows: int = 50,
    session: str | None = None,
    view: str | None = None,
) -> str:
    argv = [
        "query",
        "pin-map",
        "--anchor",
        anchor,
        "--depth",
        str(depth),
        "--max-rows",
        str(max_rows),
    ]
    if view:
        argv.extend(["--view", view])
    return await _run(argv, session=session)


@mcp.tool()
async def pin_map(
    anchor: str,
    depth: int = 2,
    max_rows: int = 50,
    view: str | None = None,
    session: str | None = None,
) -> str:
    """Live pin map: bounded bare-present NODE|EDGE slice (shared dialect).

    Optional ``view``: ``shell`` | ``interior`` (teach); ``flowchart`` | ``parts`` |
    ``statechart`` accepted with soft shell caps (grain filters deferred).
    Omit ``view`` for default depth/max_rows behaviour.

    Returns LAW-prepended shared-dialect lines (no leading +/~/-). Primary agent read.
    """
    return await _pin_map(anchor, depth, max_rows, session, view)


@mcp.tool()
async def query_warm(
    anchor: str,
    depth: int = 2,
    max_rows: int = 50,
    view: str | None = None,
    session: str | None = None,
) -> str:
    """Deprecated alias for ``pin_map`` — same params and behaviour."""
    return await _pin_map(anchor, depth, max_rows, session, view)


@mcp.tool()
async def query_walk(
    anchor: str,
    depth: int = 2,
    max_rows: int = 50,
    session: str | None = None,
) -> str:
    """Hop debug (not the primary pin map): ``@WALK: src -[relation]-> dst``.

    For agent reason each turn prefer ``pin_map`` (live pin map). For enumeration
    by tag, prefer ``read_list``.
    """
    argv = [
        "query",
        "walk",
        "--anchor",
        anchor,
        "--depth",
        str(depth),
        "--max-rows",
        str(max_rows),
    ]
    return await _run(argv, session=session)


@mcp.tool()
async def add(
    wire_lines: list[str],
    allow_new_relation: bool = False,
    agent: str | None = None,
    session: str | None = None,
) -> str:
    """Create rows via shared-dialect mutate lines (leading ``+``, optional NEW).

    Prefer shared dialect in wire_lines (Write=display). Fails if id already exists.
    """
    argv = ["add", "--stdin"]
    if allow_new_relation:
        argv.append("--allow-new-relation")
    if agent:
        argv.extend(["--agent", agent])
    stdin = "\n".join(wire_lines)
    return await _run(argv, stdin=stdin, session=session)


@mcp.tool()
async def update(
    wire_lines: list[str],
    allow_new_relation: bool = False,
    agent: str | None = None,
    session: str | None = None,
) -> str:
    """Patch or drop rows via shared-dialect mutate lines (``~`` / ``-`` on known ids).

    Prefer shared dialect in wire_lines. Fails if id is missing.
    """
    argv = ["update", "--stdin"]
    if allow_new_relation:
        argv.append("--allow-new-relation")
    if agent:
        argv.extend(["--agent", agent])
    stdin = "\n".join(wire_lines)
    return await _run(argv, stdin=stdin, session=session)


@mcp.tool()
async def read_get(id: str, session: str | None = None) -> str:
    """Fetch a single row by id."""
    return await _run(["read", "get", "--id", id], session=session)


@mcp.tool()
async def read_list(
    tag: str | None = None,
    active_only: bool = False,
    where: list[str] | None = None,
    session: str | None = None,
) -> str:
    """List rows, optionally filtered by tag, active state, or field=value conditions.

    Use this for enumeration ("all rows of tag X") without needing prior IDs.
    `where` items are "field=value" or "field=*glob*"; repeat for AND.
    """
    argv = ["read", "list"]
    if tag:
        argv.extend(["--tag", tag])
    if active_only:
        argv.append("--active-only")
    if where:
        for w in where:
            argv.extend(["--where", w])
    return await _run(argv, session=session)


@mcp.tool()
async def housekeep_stats(session: str | None = None) -> str:
    """Return row counts and caps for the session."""
    return await _run(["housekeep", "stats"], session=session)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="memnet-mcp",
        description=(
            "MemNet MCP server. Default transport is stdio (in-process graph). "
            "Use --transport streamable-http for remote Cursor url clients "
            f"(default {DEFAULT_MCP_HTTP_HOST}:{DEFAULT_MCP_HTTP_PORT}"
            f"{DEFAULT_MCP_HTTP_PATH})."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio; streamable-http is opt-in remote)",
    )
    parser.add_argument(
        "--host",
        default=None,
        help=f"HTTP bind host (default: env MEMNET_MCP_HTTP_HOST or {DEFAULT_MCP_HTTP_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"HTTP bind port (default: env MEMNET_MCP_HTTP_PORT or {DEFAULT_MCP_HTTP_PORT})",
    )
    parser.add_argument(
        "--path",
        default=None,
        help=f"HTTP MCP path (default: env MEMNET_MCP_HTTP_PATH or {DEFAULT_MCP_HTTP_PATH})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    host = args.host if args.host is not None else mcp_http_host()
    port = args.port if args.port is not None else mcp_http_port()
    path = args.path if args.path is not None else mcp_http_path()
    try:
        run_streamable_http(mcp, host=host, port=port, path=path)
    except McpHttpBindError as exc:
        sys.stderr.write(f"@ERR: mcp_http_bind|{exc}\n")
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
