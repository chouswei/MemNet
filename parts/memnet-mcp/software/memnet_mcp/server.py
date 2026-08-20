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

    Optional seed_lines are committed immediately after open (leftover ``add``
    path for Path-B / pipe seeds). Core LAW01–LAW05 are auto-included when missing
    (GQL by default; pipe only when seed_lines are leftover @TAG) so every
    pin_map carries engine invariants.

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
async def session_list() -> str:
    """List live session ids in this process (named strata; not ANN rank)."""
    return await _run(["session", "list"])


@mcp.tool()
async def snap_model(
    root: str,
    map_file: str | None = None,
    max_nodes: int = 200,
    max_files: int = 64,
    ttl: int | None = None,
) -> str:
    """Snap one SysML load tree into a catalog session plus package interiors.

    Catalog pins carry session= + qname= locators. Look = pin_map on one
    session id. Join = import_slice of a neighbourhood — not Absorb of a
    whole S, not one session per requirement, not Layer.
    """
    argv = [
        "snap",
        "model",
        "--root",
        root,
        "--max-nodes",
        str(max_nodes),
        "--max-files",
        str(max_files),
    ]
    if map_file:
        argv.extend(["--map-file", map_file])
    if ttl is not None:
        argv.extend(["--ttl", str(ttl)])
    return await _run(argv)


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
    Use before pin_map / mutate when resuming mid-task.
    leftover ``add`` / ``update`` names remain leftover façades.
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
    cue: str | None = None,
    anchor: str | None = None,
    depth: int = 2,
    max_rows: int = 50,
    session: str | None = None,
    view: str | None = None,
    caller: str | None = None,
    anchors: list[str] | None = None,
    kind: str | None = None,
    locators: list[str] | None = None,
    keyword: str | None = None,
) -> str:
    argv = [
        "query",
        "pin-map",
        "--depth",
        str(depth),
        "--max-rows",
        str(max_rows),
    ]
    ids: list[str] = []
    if cue and cue not in ids:
        ids.append(cue)
    for aid in list(anchors or []):
        if aid and aid not in ids:
            ids.append(aid)
    if anchor and anchor not in ids:
        ids.append(anchor)
    for aid in ids:
        argv.extend(["--cue", aid])
    if kind:
        argv.extend(["--kind", kind])
    for loc in locators or []:
        argv.extend(["--locator", loc])
    if keyword:
        argv.extend(["--keyword", keyword])
    if view:
        argv.extend(["--view", view])
    if caller:
        argv.extend(["--caller", caller])
    return await _run(argv, session=session)


@mcp.tool()
async def pin_map(
    cue: str | None = None,
    kind: str | None = None,
    locators: list[str] | None = None,
    keyword: str | None = None,
    depth: int = 2,
    max_rows: int = 50,
    view: str | None = None,
    session: str | None = None,
    caller: str | None = None,
    anchor: str | None = None,
    anchors: list[str] | None = None,
) -> str:
    """Live pin map: bounded shaped GQL neighbourhood.

    Goldfish caller (0.13): each turn call this with a cue ``q`` (or empty-q
    outline of S). Drop prior pin_map rows from the prompt before the next
    generate. Sparse Δ on mutate. Env blobs stay in the outer harness.

    Product cue: ``kind`` / ``locators`` / ``keyword`` / ``cue`` (nickname) /
    ``session``. leftover ``anchor`` / ``anchors`` are leftover nickname aliases,
    not TARGET law. Empty cue is session outline (0.11: kinds + LIMIT exemplars
    of S) regardless of ``view``. ``view=shell`` is grain on a seed — not the
    outline. When the cue yields |Q|>1 the emit carries CueConflict.

    Optional ``view``: ``shell`` | ``interior`` (teach); ``flowchart`` | ``parts`` |
    ``statechart`` accepted with soft shell caps (grain filters deferred).
    Optional ``caller``: CapsPolicy ACL who-check when session ACL is enabled.
    """
    return await _pin_map(
        cue,
        anchor,
        depth,
        max_rows,
        session,
        view,
        caller,
        anchors,
        kind,
        locators,
        keyword,
    )


@mcp.tool()
async def query_warm(
    cue: str | None = None,
    kind: str | None = None,
    locators: list[str] | None = None,
    keyword: str | None = None,
    depth: int = 2,
    max_rows: int = 50,
    view: str | None = None,
    session: str | None = None,
    caller: str | None = None,
    anchor: str | None = None,
    anchors: list[str] | None = None,
) -> str:
    """leftover alias for ``pin_map`` — same params. Do not teach as primary."""
    return await _pin_map(
        cue, anchor, depth, max_rows, session, view, caller, anchors, kind, locators, keyword
    )


@mcp.tool()
async def find(
    limit: int,
    kind: str | None = None,
    locators: list[str] | None = None,
    keyword: str | None = None,
    session: str | None = None,
) -> str:
    """Bounded MATCH find: seed nodes only (hard LIMIT).

    When |Q|>1 emit CueConflict (do not copy-id).
    At least one of kind / locators (KEY=VAL) / keyword. Not rag_query.
    SHALL NOT absorb.
    """
    argv = ["query", "find", "--limit", str(limit)]
    if kind:
        argv.extend(["--kind", kind])
    for loc in locators or []:
        argv.extend(["--locator", loc])
    if keyword:
        argv.extend(["--keyword", keyword])
    return await _run(argv, session=session)


@mcp.tool()
async def query_walk(
    cue: str | None = None,
    anchor: str | None = None,
    depth: int = 2,
    max_rows: int = 50,
    session: str | None = None,
) -> str:
    """leftover hop debug (not goldfish): ``@WALK: src -[relation]-> dst``.

    Product read is cue then ``pin_map``. leftover ``anchor`` is a leftover
    nickname alias. Prefer ``find`` then ``pin_map``. Not ``require_anchor``.
    """
    nick = cue or anchor or ""
    argv = [
        "query",
        "walk",
        "--anchor",
        nick,
        "--depth",
        str(depth),
        "--max-rows",
        str(max_rows),
    ]
    return await _run(argv, session=session)


async def _commit(
    mode: str,
    wire_lines: list[str],
    *,
    allow_new_relation: bool = False,
    agent: str | None = None,
    session: str | None = None,
    caller: str | None = None,
    mission_id: str | None = None,
    lease: str | None = None,
    write_scope: str | None = None,
    llm_id: str | None = None,
) -> str:
    argv = [mode, "--stdin"]
    if allow_new_relation:
        argv.append("--allow-new-relation")
    if agent:
        argv.extend(["--agent", agent])
    if caller:
        argv.extend(["--caller", caller])
    if mission_id:
        argv.extend(["--mission-id", mission_id])
    if lease:
        argv.extend(["--lease", lease])
    if write_scope:
        argv.extend(["--write-scope", write_scope])
    if llm_id:
        argv.extend(["--llm-id", llm_id])
    stdin = "\n".join(wire_lines)
    return await _run(argv, stdin=stdin, session=session)


@mcp.tool()
async def mutate(
    wire_lines: list[str],
    allow_new_relation: bool = False,
    agent: str | None = None,
    session: str | None = None,
    caller: str | None = None,
    mission_id: str | None = None,
    lease: str | None = None,
    write_scope: str | None = None,
    llm_id: str | None = None,
) -> str:
    """Product GQL Commit: CREATE / MERGE / SET / DELETE (gated).

    Writes accept GQL only. Does not mint leftover NEW. leftover ``add`` /
    ``update`` names remain as leftover façades. When session ACL is enabled:
    pass ``caller``; optional ``mission_id``+``lease``; optional ``write_scope``.
    Pass ``llm_id`` when mutating under RSV.
    """
    return await _commit(
        "mutate",
        wire_lines,
        allow_new_relation=allow_new_relation,
        agent=agent,
        session=session,
        caller=caller,
        mission_id=mission_id,
        lease=lease,
        write_scope=write_scope,
        llm_id=llm_id,
    )


@mcp.tool()
async def add(
    wire_lines: list[str],
    allow_new_relation: bool = False,
    agent: str | None = None,
    session: str | None = None,
    caller: str | None = None,
    mission_id: str | None = None,
    lease: str | None = None,
    write_scope: str | None = None,
    llm_id: str | None = None,
) -> str:
    """leftover create-only façade (not product Commit). Prefer ``mutate``.

    GQL only on the product path; leftover ``add`` may still import @TAG pipe
    for Path-B seeds. Does not mint NEW. Fails if the leftover create-only
    mode rejects SET/DELETE. Prefer ``mutate`` for mixed CREATE/SET batches.
    """
    return await _commit(
        "add",
        wire_lines,
        allow_new_relation=allow_new_relation,
        agent=agent,
        session=session,
        caller=caller,
        mission_id=mission_id,
        lease=lease,
        write_scope=write_scope,
        llm_id=llm_id,
    )


@mcp.tool()
async def update(
    wire_lines: list[str],
    allow_new_relation: bool = False,
    agent: str | None = None,
    session: str | None = None,
    caller: str | None = None,
    mission_id: str | None = None,
    lease: str | None = None,
    write_scope: str | None = None,
    llm_id: str | None = None,
) -> str:
    """leftover patch-only façade (not product Commit). Prefer ``mutate``.

    GQL MATCH…SET / DELETE. Does not mint NEW. Prefer ``mutate`` for mixed
    CREATE/SET batches.
    """
    return await _commit(
        "update",
        wire_lines,
        allow_new_relation=allow_new_relation,
        agent=agent,
        session=session,
        caller=caller,
        mission_id=mission_id,
        lease=lease,
        write_scope=write_scope,
        llm_id=llm_id,
    )


@mcp.tool()
async def import_slice(
    from_session: str,
    anchors: list[str],
    id_policy: str = "keep",
    depth: int = 2,
    max_rows: int = 50,
    view: str | None = None,
    enable_guard: bool = True,
    agent: str | None = None,
    session: str | None = None,
    caller: str | None = None,
    mission_id: str | None = None,
    lease: str | None = None,
    write_scope: str | None = None,
) -> str:
    """Path B: import a bounded WorkingMemorySlice into the lead/mission session.

    Prefer path A (shared session re-pin_map) when Multitask already shares one
    session. Product absorb is pattern MERGE (labels+properties / type+ends).
    leftover ``id_policy`` keep|reject|remint is leftover, not a product command
    (keep = leftover MERGE-as-lookup / pattern match, not a PK policy teach).
    leftover ``anchors`` are leftover nickname cues for the export slice.
    """
    argv = [
        "import-slice",
        "--from-session",
        from_session,
        "--id-policy",
        id_policy,
        "--depth",
        str(depth),
        "--max-rows",
        str(max_rows),
    ]
    for a in anchors:
        argv.extend(["--anchor", a])
    if view:
        argv.extend(["--view", view])
    if not enable_guard:
        argv.append("--no-guard")
    if agent:
        argv.extend(["--agent", agent])
    if caller:
        argv.extend(["--caller", caller])
    if mission_id:
        argv.extend(["--mission-id", mission_id])
    if lease:
        argv.extend(["--lease", lease])
    if write_scope:
        argv.extend(["--write-scope", write_scope])
    return await _run(argv, session=session)


@mcp.tool()
async def session_acl_grant(
    caller: str,
    pin_map: bool = True,
    mutate: bool = True,
    write_scope: str | None = None,
    session: str | None = None,
) -> str:
    """Grant CapsPolicy ACL CallerId (pin_map and/or mutate + optional WorkerWriteScope)."""
    argv = ["session", "acl-grant", "--caller", caller]
    if pin_map:
        argv.append("--pin-map")
    else:
        argv.append("--no-pin-map")
    if mutate:
        argv.append("--mutate")
    else:
        argv.append("--no-mutate")
    if write_scope:
        argv.extend(["--write-scope", write_scope])
    return await _run(argv, session=session)


@mcp.tool()
async def session_acl_bind(
    mission_id: str,
    lease: str,
    session: str | None = None,
) -> str:
    """Set optional SessionBind (missionId+lease). Mutate must match when set.

    In-process trusted path MAY skip bind; InvestorApi / TCP shared require who+bind.
    """
    argv = [
        "session",
        "acl-bind",
        "--mission-id",
        mission_id,
        "--lease",
        lease,
    ]
    return await _run(argv, session=session)


@mcp.tool()
async def session_acl_enable(session: str | None = None) -> str:
    """Enable CapsPolicy ACL gates on the session."""
    return await _run(["session", "acl-enable"], session=session)


@mcp.tool()
async def reserve(
    anchor: str,
    llm_id: str,
    depth: int = 2,
    ttl_s: int = 120,
    session: str | None = None,
) -> str:
    """Reserve pin-map ego neighbourhood for ``llm_id`` (MN-REQ-12.13 RSV)."""
    argv = [
        "reserve",
        "--anchor",
        anchor,
        "--llm-id",
        llm_id,
        "--depth",
        str(depth),
        "--ttl",
        str(ttl_s),
    ]
    return await _run(argv, session=session)


@mcp.tool()
async def extend(
    llm_id: str,
    rid: str | None = None,
    anchor: str | None = None,
    ttl_s: int = 120,
    session: str | None = None,
) -> str:
    """Extend neighbourhood reserve TTL (holder ``llm_id`` must match)."""
    argv = ["extend", "--llm-id", llm_id, "--ttl", str(ttl_s)]
    if rid:
        argv.extend(["--rid", rid])
    if anchor:
        argv.extend(["--anchor", anchor])
    return await _run(argv, session=session)


@mcp.tool()
async def release(
    llm_id: str,
    rid: str | None = None,
    anchor: str | None = None,
    session: str | None = None,
) -> str:
    """Release neighbourhood reserve (holder ``llm_id`` must match)."""
    argv = ["release", "--llm-id", llm_id]
    if rid:
        argv.extend(["--rid", rid])
    if anchor:
        argv.extend(["--anchor", anchor])
    return await _run(argv, session=session)


@mcp.tool()
async def export_pin_map(
    cue: str | None = None,
    kind: str | None = None,
    locators: list[str] | None = None,
    keyword: str | None = None,
    depth: int = 2,
    max_rows: int = 50,
    view: str | None = None,
    out: str | None = None,
    session: str | None = None,
    caller: str | None = None,
    anchor: str | None = None,
    anchors: list[str] | None = None,
) -> str:
    """Write out a cue pin_map (or empty-q outline) as shaped GQL.

    MN-REQ-11.1–11.5 / #66. Ingest is not export. Empty cue is 0.11 outline
    (not a dump of S). Hard bounds stay. CueConflict if |Q|>1. Distinct from
    ``session_save``. Not Absorb. Product cue: ``kind`` / ``locators`` /
    ``keyword`` / ``cue``. leftover ``anchor`` / ``anchors`` are leftover
    nickname aliases. Optional ``out`` writes the GQL body to a path.
    """
    argv = [
        "export",
        "pin-map",
        "--depth",
        str(depth),
        "--max-rows",
        str(max_rows),
    ]
    if kind:
        argv.extend(["--kind", kind])
    for loc in locators or []:
        argv.extend(["--locator", loc])
    if keyword:
        argv.extend(["--keyword", keyword])
    if view:
        argv.extend(["--view", view])
    if out:
        argv.extend(["--out", out])
    if caller:
        argv.extend(["--caller", caller])
    ids: list[str] = []
    if cue and cue not in ids:
        ids.append(cue)
    for aid in list(anchors or []):
        if aid and aid not in ids:
            ids.append(aid)
    if anchor and anchor not in ids:
        ids.append(anchor)
    for aid in ids:
        argv.extend(["--cue", aid])
    return await _run(argv, session=session)


@mcp.tool()
async def ingest_sysml(
    path: str,
    max_nodes: int = 200,
    max_files: int = 64,
    root: str | None = None,
    dry_run: bool = False,
    session: str | None = None,
) -> str:
    """Path-B SysML pin-map ingest (MN-REQ-11.16). Stable qname=/path= locators; no client NEW."""
    argv = [
        "ingest",
        "sysml",
        "--path",
        path,
        "--max-nodes",
        str(max_nodes),
        "--max-files",
        str(max_files),
    ]
    if root:
        argv.extend(["--root", root])
    if dry_run:
        argv.append("--dry-run")
    return await _run(argv, session=session)


def _ingest_argv(
    domain: str,
    path: str,
    *,
    max_nodes: int,
    max_files: int,
    root: str | None,
    dry_run: bool,
) -> list[str]:
    argv = [
        "ingest",
        domain,
        "--path",
        path,
        "--max-nodes",
        str(max_nodes),
        "--max-files",
        str(max_files),
    ]
    if root:
        argv.extend(["--root", root])
    if dry_run:
        argv.append("--dry-run")
    return argv


@mcp.tool()
async def ingest_codebase(
    path: str,
    max_nodes: int = 200,
    max_files: int = 64,
    root: str | None = None,
    dry_run: bool = False,
    session: str | None = None,
) -> str:
    """Path-B codebase ingest (MN-REQ-11.6–11.8). MOD/SYM; path=/line=/signature=."""
    return await _run(
        _ingest_argv(
            "codebase",
            path,
            max_nodes=max_nodes,
            max_files=max_files,
            root=root,
            dry_run=dry_run,
        ),
        session=session,
    )


@mcp.tool()
async def ingest_pcba(
    path: str,
    max_nodes: int = 200,
    max_files: int = 64,
    root: str | None = None,
    dry_run: bool = False,
    session: str | None = None,
) -> str:
    """Path-B PCBA .ato ingest (MN-REQ-11.9, 11.14–11.15). CMP/NET/PIN locators."""
    return await _run(
        _ingest_argv(
            "pcba",
            path,
            max_nodes=max_nodes,
            max_files=max_files,
            root=root,
            dry_run=dry_run,
        ),
        session=session,
    )


@mcp.tool()
async def ingest_skills(
    path: str,
    max_nodes: int = 200,
    max_files: int = 64,
    root: str | None = None,
    dry_run: bool = False,
    session: str | None = None,
) -> str:
    """Path-B skills/rules ingest (MN-REQ-11.10–11.12). SKL/RUL; skill_id=/phrase=."""
    return await _run(
        _ingest_argv(
            "skills",
            path,
            max_nodes=max_nodes,
            max_files=max_files,
            root=root,
            dry_run=dry_run,
        ),
        session=session,
    )


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


def _bind_durable_sync_owner() -> None:
    """Bind one DurableSyncOwner from env (same factory as memnet serve)."""
    try:
        from memnet.durable import get_sync_owner

        owner = get_sync_owner()
        sys.stderr.write(f"# durable sync owner bound: adapter={owner.adapter_name}\n")
    except Exception as exc:  # noqa: BLE001 — MCP should still start
        sys.stderr.write(f"# durable sync owner bind skipped: {type(exc).__name__}: {exc}\n")


def _maybe_install_import_guard() -> None:
    """Install CheapLlmImportGuard when MEMNET_IMPORT_GUARD_API_KEY is set (#63)."""
    try:
        from memnet.cheap_llm_import_guard import maybe_install_cheap_llm_import_guard

        if maybe_install_cheap_llm_import_guard():
            sys.stderr.write("# CheapLlmImportGuard installed (env key present)\n")
    except Exception as exc:  # noqa: BLE001 — MCP should still start
        sys.stderr.write(f"# CheapLlmImportGuard install skipped: {type(exc).__name__}: {exc}\n")


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    _maybe_install_import_guard()
    _bind_durable_sync_owner()
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
