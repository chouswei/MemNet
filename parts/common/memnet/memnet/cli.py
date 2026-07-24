"""MemNet command-line interface."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import typer

from memnet import __version__
from memnet.config import Caps, DEFAULT_QUERY_DEPTH, DEFAULT_QUERY_MAX_ROWS, serve_host, serve_port
from memnet.exceptions import MemNetError
from memnet.filter import parse_wheres
from memnet.help_text import (
    agent_guide_text,
    examples_map_text,
    examples_path_text,
    examples_workflow_text,
    fields_text,
    guide_text,
    add_example_text,
)
from memnet.housekeep import (
    dangling_rows,
    orphan_rows,
    prune_rows,
    prune_stale,
    recyclable_rows,
    stale_rows,
    stats,
)
from memnet.serve import run_serve
from memnet.snapshot import load_snapshot, write_snapshot
from memnet.output import (
    emit_err,
    emit_record,
    emit_session,
    emit_stdout,
    emit_wrn,
    reset_warn_budget,
)
from memnet.sanitiser import sanitise_batch
from memnet.session import (
    close_session,
    get_session,
    list_sessions,
    open_session,
    purge_expired,
    resolve_session_id,
)
from memnet.mutate_gate import MutateGate
from memnet.pin_map_composer import PinMapComposer
from memnet.tag_map import example_ingest_line
from memnet.warnings import emit_session_warnings
from memnet.walk_query import WalkQuery


def emit_del(record_id: str, tag: str) -> None:
    emit_stdout(f"@DEL: {record_id}|{tag}")


def emit_stat(key: str, value: int, cap: str = "-") -> None:
    emit_stdout(f"@STAT: {key}|{value}|{cap}")


app = typer.Typer(
    name="memnet",
    help="Net of Memory - in-memory NODE|EDGE graph for LLM agents. Run memnet guide.",
    no_args_is_help=True,
)
session_app = typer.Typer(help="Session lifecycle")
tagmap_app = typer.Typer(help="Tag map schema")
read_app = typer.Typer(help="Read memStore rows")
query_app = typer.Typer(help="Graph queries")
housekeep_app = typer.Typer(help="Inspect and prune stale graph")
relations_app = typer.Typer(help="EDG relation vocabulary")
examples_app = typer.Typer(help="Bundled examples")

app.add_typer(session_app, name="session")
app.add_typer(tagmap_app, name="tagmap")
app.add_typer(tagmap_app, name="map")
app.add_typer(read_app, name="read")
app.add_typer(query_app, name="query")
app.add_typer(housekeep_app, name="housekeep")
app.add_typer(relations_app, name="relations")
app.add_typer(examples_app, name="examples")


def _caps() -> Caps:
    return Caps()


def _handle_error(exc: MemNetError) -> None:
    emit_err(exc)
    raise typer.Exit(exc.exit_code) from exc


def _load_session(session: str | None, *, exclusive: bool = False):
    purge_expired(_caps())
    try:
        sid = resolve_session_id(session)
        ss = get_session(sid, _caps())
    except MemNetError as exc:
        _handle_error(exc)
        raise AssertionError("unreachable") from exc
    ss.touch()
    reset_warn_budget()
    emit_session_warnings(ss, _caps())
    if exclusive:
        return ss, ss.lock(exclusive=True)
    return ss, ss.lock(exclusive=False)


def _ingest_lines(
    ss,
    lines: list[str],
    *,
    mode: str,
    dry_run: bool = False,
    allow_new_relation: bool = False,
    agent: str | None = None,
) -> int:
    agent = agent or os.environ.get("MEMNET_AGENT")
    gate = MutateGate(ss)
    try:
        result = gate.apply(
            lines,
            mode=mode,
            dry_run=dry_run,
            allow_new_relation=allow_new_relation,
            agent=agent,
        )
    except MemNetError as exc:
        emit_err(exc)
        emit_stderr_summary(0, 1)
        raise typer.Exit(exc.exit_code) from exc
    if dry_run:
        emit_stderr("DRY-RUN")
    for w in result.warnings:
        parts = w.split("|", 1)
        emit_wrn(parts[0], parts[1] if len(parts) > 1 else "")
    for line in result.ack_lines:
        emit_stdout(line)
    # Assigned ids (Tier A NEW mint) as compact stderr hint for agents
    if result.assigned.mapping:
        for key, rid in result.assigned.mapping.items():
            emit_stderr(f"@ID: {key}|{rid}")
    emit_stderr_summary(len(result.ack_lines), 0)
    return 0


def emit_stderr(line: str) -> None:
    sys.stderr.write(line + "\n")


def emit_stderr_summary(ok: int, fail: int) -> None:
    emit_stderr(f"ok={ok} fail={fail}")


@app.command()
def version(
    json_out: Annotated[bool, typer.Option("--json", help="Emit JSON instead of wire line")] = False,
) -> None:
    """Show the installed MemNet version."""
    if json_out:
        import json as _json

        emit_stdout(_json.dumps({"name": "memnet", "version": __version__}))
    else:
        emit_stdout(f"@VER: memnet|{__version__}")


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host")] = "",
    port: Annotated[int | None, typer.Option("--port")] = None,
) -> None:
    """Run the in-memory graph server (required for multi-command CLI use)."""
    bind_host = host or serve_host()
    bind_port = port or serve_port()
    emit_stderr(f"MEMNET_SERVE={bind_host}:{bind_port}")
    run_serve(bind_host, bind_port)


@app.command()
def guide(
    loose: Annotated[bool, typer.Option("--loose")] = False,
) -> None:
    """Tier A / pin-map overview (honest about legacy pipe)."""
    emit_stdout(guide_text(loose=loose))


@examples_app.callback(invoke_without_command=True)
def examples_list(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        emit_stdout("map|workflow|add|path|agent-guide")


@examples_app.command("map")
def examples_map() -> None:
    emit_stdout(examples_map_text())


@examples_app.command("workflow")
def examples_workflow() -> None:
    emit_stdout(examples_workflow_text())


@examples_app.command("add")
def examples_add(
    tag: Annotated[str, typer.Option("--tag")],
) -> None:
    emit_stdout(add_example_text(tag))


@examples_app.command("path")
def examples_path() -> None:
    emit_stdout(examples_path_text())


@examples_app.command("agent-guide")
def examples_agent_guide() -> None:
    emit_stdout(agent_guide_text())


@tagmap_app.command("fields")
def tagmap_fields(
    tag: Annotated[str | None, typer.Option("--tag")] = None,
) -> None:
    emit_stdout(fields_text(tag))


@tagmap_app.command("show")
def tagmap_show(
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    with lock:
        for t in ss.tag_map.tag_names():
            td = ss.tag_map.tags[t]
            emit_stdout(f"@{t}: {'|'.join(td.fields)}")
            emit_stdout(example_ingest_line(td))


@session_app.command("open")
def session_open(
    map_file: Annotated[str | None, typer.Option("--map-file")] = None,
    ttl: Annotated[int | None, typer.Option("--ttl")] = None,
    map_line: Annotated[list[str] | None, typer.Option("--map")] = None,
) -> None:
    purge_expired(_caps())
    try:
        if map_file:
            ss = open_session(map_file=map_file, ttl_minutes=ttl, caps=_caps())
        elif map_line:
            ss = open_session(map_lines=map_line, ttl_minutes=ttl, caps=_caps())
        else:
            raise MemNetError("no_map", "provide --map-file or --map")
        emit_session(ss.session_id, ss.meta.expires_at, str(ss.meta.ttl_minutes))
        emit_stderr(f"MEMNET_SESSION={ss.session_id}")
    except MemNetError as exc:
        _handle_error(exc)


@session_app.command("resume")
def session_resume(session_id: str) -> None:
    purge_expired(_caps())
    try:
        ss = get_session(session_id, _caps())
        ss.touch()
        emit_session(ss.session_id, ss.meta.expires_at, str(ss.meta.ttl_minutes))
        emit_stderr(f"MEMNET_SESSION={ss.session_id}")
    except MemNetError as exc:
        _handle_error(exc)


@session_app.command("current")
def session_current(
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    sid = session or os.environ.get("MEMNET_SESSION")
    if not sid:
        emit_session("none", "")
        return
    try:
        ss = get_session(sid, _caps())
        ss.touch()
        from datetime import datetime

        expires = datetime.fromisoformat(ss.meta.expires_at.replace("Z", "+00:00"))
        from memnet.session import utc_now

        left = max(0, int((expires - utc_now()).total_seconds() // 60))
        modified = ss.meta.modified_at or "-"
        emit_session(sid, str(left), modified)
    except MemNetError:
        emit_session("none", "")


@session_app.command("list")
def session_list() -> None:
    purge_expired(_caps())
    for sid, exp, left, modified in list_sessions(_caps()):
        emit_session(sid, exp, str(left), modified)


@session_app.command("save")
def session_save(
    file: Annotated[Path, typer.Option("--file", help="User snapshot path (wire format)")],
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    with lock:
        rows = write_snapshot(ss, file)
        emit_stat("saved", rows, str(file))
        emit_stderr(f"saved {rows} rows to {file}")


@session_app.command("load")
def session_load(
    file: Annotated[Path, typer.Option("--file", help="Snapshot from session save")],
    ttl: Annotated[int | None, typer.Option("--ttl")] = None,
    keep_id: Annotated[bool, typer.Option("--keep-id", help="Reuse session id from snapshot")] = False,
) -> None:
    purge_expired(_caps())
    try:
        ss = load_snapshot(file, caps=_caps(), ttl_minutes=ttl, keep_id=keep_id)
        emit_session(ss.session_id, ss.meta.expires_at, str(ss.meta.ttl_minutes))
        emit_stderr(f"MEMNET_SESSION={ss.session_id}")
        emit_stat("loaded", ss.store.row_count_non_law(), str(file))
    except MemNetError as exc:
        _handle_error(exc)


@session_app.command("close")
def session_close(session_id: str) -> None:
    try:
        close_session(session_id, _caps())
        emit_session(session_id, "closed")
    except MemNetError as exc:
        _handle_error(exc)


@relations_app.command("list")
def relations_list(
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    with lock:
        for rel in sorted(ss.relations):
            emit_stdout(f"@REL: {rel}")


def _read_ingest_input(
    line: str | None,
    file: Path | None,
    stdin: bool,
    caps: Caps,
) -> list[str]:
    raw_lines: list[str] = []
    if line:
        raw_lines = [line]
    elif file:
        raw_lines = file.read_bytes().splitlines()
    elif stdin:
        if hasattr(sys.stdin, "buffer"):
            raw_lines = sys.stdin.buffer.read().splitlines()
        else:
            raw_lines = sys.stdin.read().splitlines()
    else:
        raise MemNetError("no_input", "provide line, --file, or --stdin")
    if len(raw_lines) > caps.max_batch_lines:
        _handle_error(
            MemNetError(
                "limit_exceeded",
                f"batch_lines|{len(raw_lines)}/{caps.max_batch_lines}",
            )
        )
    try:
        return sanitise_batch(raw_lines)
    except MemNetError as exc:
        _handle_error(exc)
        raise AssertionError("unreachable") from exc


def _ingest_cmd(
    mode: str,
    line: str | None,
    file: Path | None,
    stdin: bool,
    dry_run: bool,
    allow_new_relation: bool,
    agent: str | None,
    session: str | None,
) -> None:
    ss, lock = _load_session(session, exclusive=not dry_run)
    caps = _caps()
    lines = _read_ingest_input(line, file, stdin, caps)
    with lock:
        _ingest_lines(
            ss,
            lines,
            mode=mode,
            dry_run=dry_run,
            allow_new_relation=allow_new_relation,
            agent=agent,
        )


@app.command("add")
def add_cmd(
    line: Annotated[str | None, typer.Argument()] = None,
    file: Annotated[Path | None, typer.Option("--file")] = None,
    stdin: Annotated[bool, typer.Option("--stdin")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    allow_new_relation: Annotated[bool, typer.Option("--allow-new-relation")] = False,
    agent: Annotated[str | None, typer.Option("--agent")] = None,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    """Create new rows only (fails if id already exists)."""
    _ingest_cmd(
        "add",
        line,
        file,
        stdin,
        dry_run,
        allow_new_relation,
        agent,
        session,
    )


@app.command("update")
def update_cmd(
    line: Annotated[str | None, typer.Argument()] = None,
    file: Annotated[Path | None, typer.Option("--file")] = None,
    stdin: Annotated[bool, typer.Option("--stdin")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    allow_new_relation: Annotated[bool, typer.Option("--allow-new-relation")] = False,
    agent: Annotated[str | None, typer.Option("--agent")] = None,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    """Replace existing rows only (fails if id not found)."""
    _ingest_cmd(
        "update",
        line,
        file,
        stdin,
        dry_run,
        allow_new_relation,
        agent,
        session,
    )


@app.command("delete")
def delete_cmd(
    record_id: Annotated[str, typer.Option("--id")],
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session, exclusive=True)
    with lock:
        rec = ss.store.delete(record_id)
        if not rec:
            _handle_error(MemNetError("not_found", f"id {record_id}"))
        ss.mark_written()
        emit_del(rec.id, rec.tag)


@read_app.command("list")
def read_list(
    tag: Annotated[str | None, typer.Option("--tag")] = None,
    active_only: Annotated[bool, typer.Option("--active-only")] = False,
    where: Annotated[list[str] | None, typer.Option("--where", help="field=value filter; repeat for AND; * and ? wildcards")] = None,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    try:
        filters = parse_wheres(where or [])
    except MemNetError as exc:
        _handle_error(exc)
    ss, lock = _load_session(session)
    with lock:
        for rec in ss.store.list_records(tag, active_only=active_only, where=filters or None):
            emit_stdout(emit_record(rec, ss.tag_map))


@read_app.command("get")
def read_get(
    record_id: Annotated[str | None, typer.Option("--id")] = None,
    tag: Annotated[str | None, typer.Option("--tag")] = None,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    if not record_id:
        raise MemNetError("no_id", "provide --id")
    ss, lock = _load_session(session)
    with lock:
        rec = ss.store.get(record_id)
        if not rec:
            _handle_error(MemNetError("not_found", f"id {record_id}"))
        if tag and rec.tag != tag.upper():
            _handle_error(MemNetError("not_found", f"id {record_id} tag {tag}"))
        emit_stdout(emit_record(rec, ss.tag_map))


def _query_context(
    ss,
    *,
    anchor: str | None,
    depth: int,
    max_rows: int,
    active_only: bool,
    require_anchor: bool,
    tier_a: bool = False,
) -> None:
    if tier_a:
        composer = PinMapComposer(ss)
        try:
            _rows, text = composer.compose(
                anchor=anchor,
                depth=depth,
                max_rows=max_rows,
                active_only=active_only,
                require_anchor=require_anchor,
            )
        except MemNetError as exc:
            _handle_error(exc)
            return
        if text:
            for line in text.splitlines():
                emit_stdout(line)
        elif not anchor:
            emit_wrn("no_anchor", "store has no nodes")
        return

    if require_anchor and not anchor:
        _handle_error(MemNetError("no_anchor", "pin map requires --anchor"))
    stale_warnings: list = []
    if not anchor:
        anchor = ss.store.default_anchor()
        if not anchor:
            emit_wrn("no_anchor", "store has no nodes")
    rows = ss.store.context_pack(
        anchor_id=anchor,
        depth=depth,
        max_rows=max_rows,
        active_only=active_only,
        stale_warnings=stale_warnings,
    )
    if not active_only:
        stale_count = 0
        for rec, _kind in stale_warnings:
            stale_count += 1
            if stale_count <= 10:
                emit_wrn(
                    "stale_in_context",
                    f"{stale_count}|use query pin-map or --active-only",
                    emit_record(rec, ss.tag_map),
                )
        if stale_count > 10:
            emit_wrn(
                "stale_in_context_truncated",
                f"{stale_count}|housekeep recyclable",
            )
    for rec in rows:
        emit_stdout(emit_record(rec, ss.tag_map))


@query_app.command("neighbors")
def query_neighbors(
    node_id: str,
    depth: Annotated[int, typer.Option("--depth")] = 1,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    caps = _caps()
    depth = min(depth, caps.max_depth)
    with lock:
        fanout: list[str] = []
        rows = ss.store.neighbors(node_id, depth, fanout_warnings=fanout)
        for w in fanout:
            p = w.split("|", 1)
            emit_wrn(p[0], p[1] if len(p) > 1 else "")
        for rec in rows:
            emit_stdout(emit_record(rec, ss.tag_map))


@query_app.command("path")
def query_path(
    source_id: str,
    target_id: str,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    with lock:
        for rec in ss.store.find_path(source_id, target_id):
            emit_stdout(emit_record(rec, ss.tag_map))


@query_app.command("context")
def query_context(
    anchor: Annotated[str | None, typer.Option("--anchor")] = None,
    depth: Annotated[int, typer.Option("--depth")] = DEFAULT_QUERY_DEPTH,
    max_rows: Annotated[int, typer.Option("--max-rows")] = DEFAULT_QUERY_MAX_ROWS,
    active_only: Annotated[bool, typer.Option("--active-only")] = False,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    with lock:
        _query_context(
            ss,
            anchor=anchor,
            depth=depth,
            max_rows=max_rows,
            active_only=active_only,
            require_anchor=False,
        )


def _run_pin_map(
    *,
    anchor: str | None,
    depth: int,
    max_rows: int,
    session: str | None,
) -> None:
    ss, lock = _load_session(session)
    with lock:
        _query_context(
            ss,
            anchor=anchor,
            depth=depth,
            max_rows=max_rows,
            active_only=True,
            require_anchor=True,
            tier_a=True,
        )


@query_app.command("pin-map")
def query_pin_map(
    anchor: Annotated[str | None, typer.Option("--anchor")] = None,
    depth: Annotated[int, typer.Option("--depth")] = DEFAULT_QUERY_DEPTH,
    max_rows: Annotated[int, typer.Option("--max-rows")] = DEFAULT_QUERY_MAX_ROWS,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    """Live pin map (PinMapComposer). Emits Tier A Write=display."""
    _run_pin_map(anchor=anchor, depth=depth, max_rows=max_rows, session=session)


@query_app.command("warm")
def query_warm(
    anchor: Annotated[str | None, typer.Option("--anchor")] = None,
    depth: Annotated[int, typer.Option("--depth")] = DEFAULT_QUERY_DEPTH,
    max_rows: Annotated[int, typer.Option("--max-rows")] = DEFAULT_QUERY_MAX_ROWS,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    """Live pin map — deprecated alias for pin-map."""
    _run_pin_map(anchor=anchor, depth=depth, max_rows=max_rows, session=session)


@query_app.command("walk")
def query_walk(
    anchor: Annotated[str | None, typer.Option("--anchor")] = None,
    depth: Annotated[int, typer.Option("--depth")] = DEFAULT_QUERY_DEPTH,
    max_rows: Annotated[int, typer.Option("--max-rows")] = DEFAULT_QUERY_MAX_ROWS,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    """Anchored subgraph as hop lines: ``@WALK: src -[relation]-> dst``.

    For listing all rows of a tag (enumeration), use ``read list --tag T`` instead.
    """
    ss, lock = _load_session(session)
    with lock:
        walk = WalkQuery(ss)
        try:
            for line in walk.hops(anchor=anchor or "", depth=depth, max_rows=max_rows):
                emit_stdout(line)
        except MemNetError as exc:
            _handle_error(exc)


@housekeep_app.command("stats")
def housekeep_stats(
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    caps = _caps()
    with lock:
        s = stats(ss)
        emit_stat("rows", s["rows"], str(caps.max_rows))
        emit_stat("edges", s["edges"], "-")
        emit_stat("relations", s["relations"], str(caps.max_relations))
        emit_stat("orphans", s["orphans"], "-")
        emit_stat("dangling", s["dangling"], "-")
        emit_stat("recyclable", s["recyclable"], "-")
        modified = ss.meta.modified_at or "-"
        emit_stdout(f"@STAT: modified|{modified}|-")


@housekeep_app.command("stale")
def housekeep_stale(
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    with lock:
        for rec in stale_rows(ss):
            emit_stdout(emit_record(rec, ss.tag_map))


@housekeep_app.command("orphans")
def housekeep_orphans(
    tag: Annotated[str | None, typer.Option("--tag")] = None,
    include_tags: Annotated[str | None, typer.Option("--include-tags")] = None,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    inc = set(include_tags.split(",")) if include_tags else None
    with lock:
        for rec in orphan_rows(ss, tag=tag, include_tags=inc):
            emit_stdout(emit_record(rec, ss.tag_map))


@housekeep_app.command("dangling")
def housekeep_dangling(
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    with lock:
        for rec in dangling_rows(ss):
            emit_stdout(emit_record(rec, ss.tag_map))


@housekeep_app.command("recyclable")
def housekeep_recyclable(
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session)
    with lock:
        for rec in recyclable_rows(ss):
            emit_stdout(emit_record(rec, ss.tag_map))


prune_app = typer.Typer(help="Prune stale rows")
housekeep_app.add_typer(prune_app, name="prune")


@prune_app.callback(invoke_without_command=True)
def prune_help(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        raise typer.Exit(1)


@prune_app.command("stale")
def prune_stale_cmd(
    apply: Annotated[bool, typer.Option("--apply")] = False,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    _prune_kind(session, "stale", apply)


@prune_app.command("orphans")
def prune_orphans(
    apply: Annotated[bool, typer.Option("--apply")] = False,
    tag: Annotated[str | None, typer.Option("--tag")] = None,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    ss, lock = _load_session(session, exclusive=apply)
    with lock:
        rows = orphan_rows(ss, tag=tag)
        _prune_rows(ss, rows, apply, "orphans")


@prune_app.command("dangling")
def prune_dangling(
    apply: Annotated[bool, typer.Option("--apply")] = False,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    _prune_kind(session, "dangling", apply)


@prune_app.command("recyclable")
def prune_recyclable(
    apply: Annotated[bool, typer.Option("--apply")] = False,
    session: Annotated[str | None, typer.Option("--session")] = None,
) -> None:
    _prune_kind(session, "recyclable", apply)


def _prune_kind(session: str | None, kind: str, apply: bool) -> None:
    ss, lock = _load_session(session, exclusive=apply)
    with lock:
        if kind == "stale":
            rows = stale_rows(ss)
            if apply:
                deleted = prune_stale(ss)
            else:
                deleted = []
        elif kind == "recyclable":
            rows = recyclable_rows(ss)
            deleted = prune_rows(ss, rows) if apply else []
        elif kind == "dangling":
            rows = dangling_rows(ss)
            deleted = prune_rows(ss, rows) if apply else []
        else:
            rows = []
            deleted = []
        _prune_rows(ss, rows, apply, kind, deleted=deleted)


def _prune_rows(
    ss,
    rows: list,
    apply: bool,
    kind: str,
    *,
    deleted: list | None = None,
) -> None:
    for rec in rows:
        emit_stdout(emit_record(rec, ss.tag_map))
    if apply:
        deleted = deleted if deleted is not None else prune_rows(ss, rows)
        ss.mark_written()
        for rec in deleted:
            emit_del(rec.id, rec.tag)
        emit_stderr(f"deleted {len(deleted)} rows")
    else:
        emit_stderr(f"would-delete {len(rows)} rows ({kind})")


def main() -> None:
    from memnet.serve_client import dispatch

    raise SystemExit(dispatch())


if __name__ == "__main__":
    main()
