"""Live probes for the cap contract. Never emit a session id (mn_ prefix)."""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from memnet.acl import check_permission
from memnet.cli import app
from memnet.config import (
    DEFAULT_INGEST_MAX_EDGES,
    DEFAULT_INGEST_MAX_NODES,
    DEFAULT_QUERY_DEPTH,
    DEFAULT_QUERY_MAX_ROWS,
    DEFAULT_SERVE_MAX_FRAME_BYTES,
    Caps,
    default_ttl_minutes,
)
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.output import format_err
from memnet.pin_map_composer import PinMapComposer
from memnet.pin_map_ingest import ingest_sysml
from memnet.session import (
    _seed_relations,
    get_session,
    open_session,
    purge_expired,
    reset_registry,
    set_now_override,
)
from memnet.tag_map import load_map_from_lines, load_user_map, parse_line
from memnet.walk_query import WalkQuery

runner = CliRunner()
_SID_RE = re.compile(r"mn_[0-9a-fA-F]+")
_TINY_MAP = ["SCHEMA CST ; fields=id name role"]
_SYSML_MAP = Path("parts/common/memnet/memnet/examples/schema.sysml.example.txt")


def redact(text: str) -> str:
    return _SID_RE.sub("<session>", text or "")


@contextmanager
def env_caps(**values: str | None):
    old: dict[str, str | None] = {}
    for key, val in values.items():
        old[key] = os.environ.get(key)
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val
    try:
        yield
    finally:
        for key, val in old.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val


@dataclass
class Case:
    name: str
    kind: str
    default: str
    knob: str
    library_code: str = ""
    library_message: str = ""
    wire: str = ""
    mcp: str = ""
    extra: dict[str, str] = field(default_factory=dict)
    bug: str = ""


def _cst(i: int, *, name: str | None = None) -> str:
    label = name or f"n{i}"
    return f"CREATE (:CST {{id: 'N{i:02d}', name: '{label}', role: 'node'}})"


def _clean() -> None:
    set_now_override(None)
    reset_registry()
    purge_expired()


def _open(caps: Caps | None = None):
    return open_session(map_lines=list(_TINY_MAP), caps=caps or Caps())


def _cli(args: list[str], *, stdin: str | None = None, extra_env: dict | None = None):
    env = {"MEMNET_TEST_INLINE": "1"}
    if extra_env:
        env.update(extra_env)
    result = runner.invoke(app, args, input=stdin, env=env)
    return result


def _cli_open(caps_env: dict | None = None) -> str:
    env = {"MEMNET_TEST_INLINE": "1"}
    if caps_env:
        env.update(caps_env)
    result = runner.invoke(
        app,
        ["session", "open", "--map"] + _TINY_MAP,
        env=env,
    )
    if result.exit_code != 0:
        raise AssertionError(redact(result.stderr or result.stdout))
    for line in result.stdout.splitlines():
        if line.startswith("@SESSION:"):
            return line.split("|", 1)[0].replace("@SESSION:", "").strip()
    raise AssertionError("session open produced no @SESSION line")


def defaults_record() -> dict[str, str | int]:
    caps = Caps()
    return {
        "max_rows": caps.max_rows,
        "max_relations": caps.max_relations,
        "max_law": caps.max_law,
        "max_tags": caps.max_tags,
        "max_fields": caps.max_fields,
        "max_value_bytes": caps.max_value_bytes,
        "max_line_bytes": caps.max_line_bytes,
        "max_batch_lines": caps.max_batch_lines,
        "max_sessions": caps.max_sessions,
        "max_depth": caps.max_depth,
        "max_fanout": caps.max_fanout,
        "lock_timeout_ms": caps.lock_timeout_ms,
        "ingest_max_nodes": DEFAULT_INGEST_MAX_NODES,
        "ingest_max_edges": DEFAULT_INGEST_MAX_EDGES,
        "ingest_max_files": 64,
        "query_max_rows": DEFAULT_QUERY_MAX_ROWS,
        "query_depth": DEFAULT_QUERY_DEPTH,
        "ttl_minutes": default_ttl_minutes(),
        "serve_max_frame_bytes": DEFAULT_SERVE_MAX_FRAME_BYTES,
        "seed_relation_count": len(_seed_relations()),
        "shell_max_nodes": 8,
        "shell_max_edges": 12,
        "warn_budget": 12,
        "outline_exemplar_limit": 3,
    }


def case_ingest_node_budget(tmp_path: Path) -> Case:
    _clean()
    path = tmp_path / "nodes.sysml"
    path.write_text("package P {\n  part def A;\n  part def B;\n}\n", encoding="utf-8")
    with env_caps():
        try:
            ingest_sysml(None, path, max_nodes=1, dry_run=True)
            raise AssertionError("expected ingest_budget")
        except MemNetError as exc:
            wire = format_err(exc.code, exc.message)
            return Case(
                name="ingest_node_budget",
                kind="hard_refuse",
                default="2000",
                knob="--max-nodes / MCP max_nodes (DEFAULT_INGEST_MAX_NODES)",
                library_code=exc.code,
                library_message=exc.message,
                wire=wire,
                extra={"committed": "false", "rollback": "project refuses before commit"},
            )


def case_ingest_edge_budget(tmp_path: Path) -> Case:
    _clean()
    path = tmp_path / "edges.sysml"
    path.write_text(
        "package P {\n  part def A;\n  part def B { satisfy A; }\n}\n",
        encoding="utf-8",
    )
    try:
        ingest_sysml(None, path, max_edges=1, dry_run=True)
        raise AssertionError("expected ingest_budget")
    except MemNetError as exc:
        return Case(
            name="ingest_edge_budget",
            kind="hard_refuse",
            default="2000",
            knob="--max-edges / MCP max_edges (DEFAULT_INGEST_MAX_EDGES)",
            library_code=exc.code,
            library_message=exc.message,
            wire=format_err(exc.code, exc.message),
            extra={"committed": "false", "rollback": "project refuses before commit"},
        )


def case_ingest_file_budget(tmp_path: Path) -> Case:
    _clean()
    root = tmp_path / "many"
    root.mkdir()
    for i in range(3):
        (root / f"p{i}.sysml").write_text(f"package P{i} {{ part def A; }}\n", encoding="utf-8")
    try:
        ingest_sysml(None, root, max_files=2, dry_run=True)
        raise AssertionError("expected ingest_budget")
    except MemNetError as exc:
        return Case(
            name="ingest_file_budget",
            kind="hard_refuse",
            default="64",
            knob="--max-files / MCP max_files",
            library_code=exc.code,
            library_message=exc.message,
            wire=format_err(exc.code, exc.message),
        )


def case_session_row_cap() -> Case:
    _clean()
    with env_caps(MEMNET_MAX_ROWS="2"):
        caps = Caps()
        ss = _open(caps)
        gate = MutateGate(ss)
        gate.apply([_cst(1)], mode="add")
        gate.apply([_cst(2)], mode="add")
        filled = ss.store.row_count_non_law()
        err: MemNetError | None = None
        try:
            gate.apply([_cst(3)], mode="add")
        except MemNetError as exc:
            err = exc
        if err is None:
            raise AssertionError("expected row cap")
        after = ss.store.row_count_non_law()
        evicted = after != filled
        wire = format_err(err.code, err.message)
        sid = _cli_open({"MEMNET_MAX_ROWS": "2"})
        for line in (_cst(1), _cst(2)):
            add = _cli(
                ["add", "--stdin", "--session", sid],
                stdin=line + "\n",
                extra_env={"MEMNET_MAX_ROWS": "2"},
            )
            if add.exit_code != 0:
                raise AssertionError(redact(add.stderr))
        refused = _cli(
            ["add", "--stdin", "--session", sid],
            stdin=_cst(3) + "\n",
            extra_env={"MEMNET_MAX_ROWS": "2"},
        )
        mcp_err = ""
        try:
            from memnet_mcp.client import run_memnet

            mcp_sid = _cli_open({"MEMNET_MAX_ROWS": "2"})
            run_memnet(
                ["add", "--stdin"],
                stdin=_cst(1) + "\n",
                session=mcp_sid,
            )
            run_memnet(
                ["add", "--stdin"],
                stdin=_cst(2) + "\n",
                session=mcp_sid,
            )
            mcp = run_memnet(
                ["add", "--stdin"],
                stdin=_cst(3) + "\n",
                session=mcp_sid,
            )
            mcp_err = redact(";".join(mcp.errors))
        except ImportError:
            mcp_err = "mcp extra not installed"
        ok_fail = refused.stderr
        if "ok=0 fail=1" in refused.stderr:
            ok_fail = "ok=0 fail=1"
        else:
            ok_fail = redact(refused.stderr)
        return Case(
            name="session_row_cap",
            kind="hard_refuse",
            default="5000",
            knob="MEMNET_MAX_ROWS",
            library_code=err.code,
            library_message=err.message,
            wire=wire,
            mcp=mcp_err,
            extra={
                "cli_stderr": redact(refused.stderr.strip()),
                "rows_at_cap": str(filled),
                "rows_after_refuse": str(after),
                "evicted": str(evicted),
                "ok_fail": ok_fail,
            },
        )


def case_row_cap_batch_rollback() -> Case:
    _clean()
    with env_caps(MEMNET_MAX_ROWS="2"):
        ss = _open(Caps())
        gate = MutateGate(ss)
        try:
            gate.apply([_cst(1), _cst(2), _cst(3)], mode="add")
            raise AssertionError("expected batch row cap")
        except MemNetError as exc:
            remaining = ss.store.row_count_non_law()
            return Case(
                name="row_cap_batch_rollback",
                kind="hard_refuse",
                default="5000",
                knob="MEMNET_MAX_ROWS (one mutate batch)",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message),
                extra={
                    "remaining_non_law_rows": str(remaining),
                    "rollback": "all-or-nothing" if remaining == 0 else "PARTIAL",
                },
                bug="" if remaining == 0 else "partial write: batch left rows after limit_exceeded",
            )


def case_relation_cap_safe() -> Case:
    _clean()
    seed_n = len(_seed_relations())
    with env_caps(MEMNET_MAX_RELATIONS=str(seed_n)):
        ss = _open(Caps())
        gate = MutateGate(ss)
        gate.apply([_cst(1), _cst(2)], mode="add")
        try:
            gate.apply(
                ["MATCH (a {id: 'N01'}), (b {id: 'N02'})\nCREATE (a)-[:zz_new {id: 'E01'}]->(b)"],
                mode="add",
                allow_new_relation=True,
            )
            raise AssertionError("expected relation cap")
        except MemNetError as exc:
            return Case(
                name="relation_type_cap",
                kind="hard_refuse",
                default="200",
                knob="MEMNET_MAX_RELATIONS",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message),
                extra={
                    "seed_relation_count": str(seed_n),
                    "seed_not_trimmed": "true",
                    "allow_new_relation": "required for a new type; else unknown_relation",
                },
            )


def case_unknown_relation() -> Case:
    _clean()
    ss = _open()
    gate = MutateGate(ss)
    gate.apply([_cst(1), _cst(2)], mode="add")
    try:
        gate.apply(
            ["MATCH (a {id: 'N01'}), (b {id: 'N02'})\nCREATE (a)-[:zz_new {id: 'E01'}]->(b)"],
            mode="add",
            allow_new_relation=False,
        )
        raise AssertionError("expected unknown_relation")
    except MemNetError as exc:
        return Case(
            name="unknown_relation",
            kind="hard_refuse",
            default="allow_new_relation=False on mutate/add",
            knob="--allow-new-relation / MCP allow_new_relation",
            library_code=exc.code,
            library_message=exc.message,
            wire=format_err(exc.code, exc.message),
        )


def case_law_cap() -> Case:
    _clean()
    with env_caps(MEMNET_MAX_LAW="1"):
        ss = _open(Caps())
        gate = MutateGate(ss)
        gate.apply(
            [
                "CREATE (:LAW {id: 'LAW_A', name: 'one', cycle: '*', "
                "mechanism: 'x', constraint: '*'})"
            ],
            mode="add",
        )
        try:
            gate.apply(
                [
                    "CREATE (:LAW {id: 'LAW_B', name: 'two', cycle: '*', "
                    "mechanism: 'y', constraint: '*'})"
                ],
                mode="add",
            )
            raise AssertionError("expected law cap")
        except MemNetError as exc:
            return Case(
                name="law_cap",
                kind="hard_refuse",
                default="100",
                knob="MEMNET_MAX_LAW",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message),
            )


def case_tag_and_field_caps() -> list[Case]:
    _clean()
    out: list[Case] = []
    with env_caps(MEMNET_MAX_TAGS="1"):
        try:
            load_user_map(
                [
                    "SCHEMA CST ; fields=id name",
                    "SCHEMA ABC ; fields=id name",
                ],
                Caps(),
            )
            raise AssertionError("expected tag cap")
        except MemNetError as exc:
            out.append(
                Case(
                    name="tag_map_cap",
                    kind="hard_refuse",
                    default="64",
                    knob="MEMNET_MAX_TAGS",
                    library_code=exc.code,
                    library_message=exc.message,
                    wire=format_err(exc.code, exc.message),
                )
            )
    with env_caps(MEMNET_MAX_FIELDS="2"):
        try:
            load_user_map(["SCHEMA CST ; fields=id name role extra"], Caps())
            raise AssertionError("expected field cap")
        except MemNetError as exc:
            out.append(
                Case(
                    name="fields_per_tag",
                    kind="hard_refuse",
                    default="32",
                    knob="MEMNET_MAX_FIELDS",
                    library_code=exc.code,
                    library_message=exc.message,
                    wire=format_err(exc.code, exc.message),
                )
            )
    return out


def case_pipe_value_and_line_bytes() -> list[Case]:
    _clean()
    out: list[Case] = []
    tag_map = load_map_from_lines(list(_TINY_MAP), Caps())
    with env_caps(MEMNET_MAX_VALUE_BYTES="4"):
        caps = Caps()
        try:
            parse_line("@CST: N01|toolong|x", tag_map, caps)
            raise AssertionError("expected value_bytes")
        except MemNetError as exc:
            out.append(
                Case(
                    name="pipe_value_bytes",
                    kind="hard_refuse",
                    default="4096",
                    knob="MEMNET_MAX_VALUE_BYTES (pipe parse_line only)",
                    library_code=exc.code,
                    library_message=exc.message,
                    wire=format_err(exc.code, exc.message),
                    extra={"gql_mutate": "does not enforce this cap"},
                    bug="GQL mutate does not check max_value_bytes",
                )
            )
    with env_caps(MEMNET_MAX_LINE_BYTES="8"):
        caps = Caps()
        try:
            parse_line("@CST: N01|ab|cd", tag_map, caps)
            raise AssertionError("expected line_bytes")
        except MemNetError as exc:
            out.append(
                Case(
                    name="pipe_line_bytes",
                    kind="hard_refuse",
                    default="32768",
                    knob="MEMNET_MAX_LINE_BYTES (pipe parse_line only)",
                    library_code=exc.code,
                    library_message=exc.message,
                    wire=format_err(exc.code, exc.message),
                    extra={"gql_mutate": "does not enforce this cap"},
                    bug="GQL mutate does not check max_line_bytes",
                )
            )
    return out


def case_batch_lines() -> Case:
    _clean()
    with env_caps(MEMNET_MAX_BATCH_LINES="2"):
        sid = _cli_open({"MEMNET_MAX_BATCH_LINES": "2"})
        refused = _cli(
            ["add", "--stdin", "--session", sid],
            stdin="\n".join([_cst(1), _cst(2), _cst(3)]) + "\n",
            extra_env={"MEMNET_MAX_BATCH_LINES": "2"},
        )
    return Case(
        name="mutate_batch_lines",
        kind="hard_refuse",
        default="1000",
        knob="MEMNET_MAX_BATCH_LINES",
        library_code="limit_exceeded",
        library_message="batch_lines|3/2",
        wire=redact(
            next(
                (ln for ln in refused.stderr.splitlines() if ln.startswith("@ERR:")),
                refused.stderr,
            )
        ),
        extra={"exit_code": str(refused.exit_code)},
    )


def _star_session(*, leaves: int, caps: Caps | None = None):
    ss = _open(caps)
    lines = [_cst(0, name="hub")]
    for i in range(1, leaves + 1):
        lines.append(_cst(i, name=f"leaf{i}"))
        lines.append(
            f"MATCH (hub {{id: 'N00'}}), (leaf {{id: 'N{i:02d}'}})\n"
            f"CREATE (hub)-[:member_of {{id: 'E{i:02d}'}}]->(leaf)"
        )
    MutateGate(ss).apply(lines, mode="add", allow_new_relation=False)
    return ss


def case_pin_map_max_rows() -> Case:
    _clean()
    ss = _star_session(leaves=8)
    _rows, text = PinMapComposer(ss).compose(anchor="N00", depth=1, max_rows=4)
    trunc = next((ln for ln in text.splitlines() if ln.startswith("## Truncation")), "")
    return Case(
        name="pin_map_max_rows",
        kind="signalled_clip",
        default="50 (DEFAULT_QUERY_MAX_ROWS / --max-rows / MCP max_rows)",
        knob="pin_map max_rows argument (not MEMNET_MAX_ROWS)",
        wire=trunc,
        extra={"silent": "false"},
    )


def case_pin_map_depth() -> Case:
    _clean()
    with env_caps(MEMNET_MAX_DEPTH="1"):
        ss = _star_session(leaves=3, caps=Caps())
        _rows, text = PinMapComposer(ss).compose(anchor="N00", depth=4, max_rows=50)
        trunc = next((ln for ln in text.splitlines() if ln.startswith("## Truncation")), "")
        return Case(
            name="pin_map_depth",
            kind="signalled_clip",
            default="4",
            knob="MEMNET_MAX_DEPTH (request depth is min()'d)",
            wire=trunc,
            extra={"requested_depth": "4", "kept_depth": "1"},
        )


def case_pin_map_fanout() -> Case:
    _clean()
    with env_caps(MEMNET_MAX_FANOUT="2"):
        ss = _star_session(leaves=6, caps=Caps())
        _rows, text = PinMapComposer(ss).compose(anchor="N00", depth=1, max_rows=50)
        trunc = next((ln for ln in text.splitlines() if ln.startswith("## Truncation")), "")
        return Case(
            name="pin_map_fanout",
            kind="signalled_clip",
            default="256",
            knob="MEMNET_MAX_FANOUT",
            wire=trunc,
            extra={"also_wrn": "fanout_clamped on stderr when a CLI load path emits warnings"},
        )


def case_pin_map_shell() -> Case:
    _clean()
    ss = _star_session(leaves=12)
    _rows, text = PinMapComposer(ss).compose(anchor="N00", depth=1, max_rows=50, view="shell")
    trunc = next((ln for ln in text.splitlines() if ln.startswith("## Truncation")), "")
    return Case(
        name="pin_map_shell",
        kind="signalled_clip",
        default="SHELL_MAX_NODES=8 SHELL_MAX_EDGES=12",
        knob="view=shell (soft grain; still emits Truncation)",
        wire=trunc,
    )


def case_query_walk_silent() -> Case:
    _clean()
    ss = _star_session(leaves=8)
    hops = WalkQuery(ss).hops(anchor="N00", depth=2, max_rows=3)
    blob = "\n".join(hops)
    silent = "## Truncation" not in blob and "@ERR:" not in blob
    return Case(
        name="query_walk_max_rows",
        kind="silent_clip" if silent else "signalled_clip",
        default="50 (leftover query walk --max-rows)",
        knob="query_walk / WalkQuery.hops max_rows",
        wire=f"hops_returned={len(hops)} (no Truncation mark)" if silent else blob,
        extra={"hop_count": str(len(hops))},
        bug="leftover query walk clips hops at max_rows with no Truncation/@ERR/@WRN"
        if silent
        else "",
    )


def case_leftover_context_silent() -> Case:
    _clean()
    ss = _star_session(leaves=8)
    rows = ss.store.context_pack(anchor_id="N00", depth=1, max_rows=4)
    return Case(
        name="leftover_query_context",
        kind="silent_clip",
        default="50",
        knob="leftover query context (context_pack without clip_notes)",
        wire=f"rows_returned={len(rows)} (no Truncation; leftover path)",
        extra={"clip_notes_arg": "None"},
        bug="leftover query context / context_pack(clip_notes=None) slices max_rows silently",
    )


def case_outline_clip() -> Case:
    _clean()
    ss = _open()
    lines = [_cst(i) for i in range(12)]
    MutateGate(ss).apply(lines, mode="add")
    _rows, text = PinMapComposer(ss).compose(anchor=None, max_rows=2)
    trunc = next((ln for ln in text.splitlines() if ln.startswith("## Truncation")), "")
    return Case(
        name="session_outline_max_rows",
        kind="signalled_clip",
        default="50 (empty cue outline) plus OUTLINE_EXEMPLAR_LIMIT=3 per kind",
        knob="pin_map max_rows on empty cue",
        wire=trunc,
    )


def case_find_cue_conflict() -> Case:
    _clean()
    from memnet.pin_map_composer import bounded_match_find, emit_cue_conflict

    ss = _open()
    MutateGate(ss).apply([_cst(1), _cst(2)], mode="add")
    found = bounded_match_find(ss.store, kind="CST", locators=[], keyword=None, limit=8)
    mark = emit_cue_conflict(found.seeds, cardinality=found.total, store=ss.store).splitlines()[0]
    return Case(
        name="find_limit_cue_conflict",
        kind="honesty_mark",
        default="limit is required (>=1); not optional",
        knob="find --limit / MCP find limit",
        wire=mark,
        extra={
            "total": str(found.total),
            "listed": str(len(found.seeds)),
            "note": (
                "MATCH_L |Q|>1 emits CueConflict; listed seeds may be LIMIT-sliced; |Q| is total"
            ),
        },
    )


def case_session_count() -> Case:
    _clean()
    with env_caps(MEMNET_MAX_SESSIONS="1"):
        _open(Caps())
        try:
            _open(Caps())
            raise AssertionError("expected session cap")
        except MemNetError as exc:
            return Case(
                name="max_sessions",
                kind="hard_refuse",
                default="1024",
                knob="MEMNET_MAX_SESSIONS",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message),
            )


def case_ttl_and_expire(tmp_path: Path) -> list[Case]:
    _clean()
    out: list[Case] = []
    ss = open_session(map_lines=list(_TINY_MAP), ttl_minutes=1)
    set_now_override(datetime.now(UTC) + timedelta(minutes=5))
    try:
        get_session(ss.session_id)
        raise AssertionError("expected expire")
    except MemNetError as exc:
        out.append(
            Case(
                name="ttl_expire_unsaved",
                kind="hard_refuse",
                default="60 minutes (MEMNET_SESSION_TTL_MINUTES); range 1..1440",
                knob="session open --ttl / MCP ttl; MEMNET_SESSION_TTL_MINUTES",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message),
                extra={
                    "save_on_expire_default": "off",
                    "memory": "session dropped; no snapshot file",
                },
            )
        )
    finally:
        set_now_override(None)

    expire_dir = tmp_path / "expire"
    with env_caps(
        MEMNET_SAVE_ON_EXPIRE="1",
        MEMNET_EXPIRE_SNAPSHOT_DIR=str(expire_dir),
    ):
        from memnet.config import Caps as CapsCls
        from memnet.session import purge_expired

        ss = open_session(map_lines=list(_TINY_MAP), ttl_minutes=1, caps=CapsCls())
        MutateGate(ss).apply([_cst(1)], mode="add")
        set_now_override(datetime.now(UTC) + timedelta(minutes=5))
        try:
            purge_expired(CapsCls())
            try:
                get_session(ss.session_id, CapsCls())
                raise AssertionError("expected snap_available")
            except MemNetError as exc:
                snaps = list(expire_dir.glob("*.snap"))
                out.append(
                    Case(
                        name="ttl_expire_save_on",
                        kind="hard_refuse_then_restore",
                        default="MEMNET_SAVE_ON_EXPIRE off; dir unset",
                        knob="MEMNET_SAVE_ON_EXPIRE + MEMNET_EXPIRE_SNAPSHOT_DIR",
                        library_code=exc.code,
                        library_message=exc.message,
                        wire=format_err(exc.code, exc.message),
                        extra={
                            "snap_files": str(len(snaps)),
                            "restore": "session_load with the known id (keep_id)",
                        },
                    )
                )
        finally:
            set_now_override(None)

    with env_caps(MEMNET_SAVE_ON_EXPIRE="1", MEMNET_EXPIRE_SNAPSHOT_DIR=None):
        from memnet.config import Caps as CapsCls

        ss = open_session(map_lines=list(_TINY_MAP), ttl_minutes=1, caps=CapsCls())
        set_now_override(datetime.now(UTC) + timedelta(minutes=5))
        try:
            get_session(ss.session_id, CapsCls())
            raise AssertionError("expected snap_missing")
        except MemNetError as exc:
            out.append(
                Case(
                    name="ttl_save_on_expire_no_dir",
                    kind="hard_refuse",
                    default="dir unset",
                    knob="MEMNET_SAVE_ON_EXPIRE=1 without MEMNET_EXPIRE_SNAPSHOT_DIR",
                    library_code=exc.code,
                    library_message=exc.message,
                    wire=format_err(exc.code, exc.message),
                    extra={
                        "wrn": "@WRN: save_on_expire_no_dir|dir unset",
                        "after_purge": (
                            "a later get on an already-purged id is "
                            "session_not_found|unknown session, not session_expired"
                        ),
                    },
                )
            )
        finally:
            set_now_override(None)
    return out


def case_acl() -> list[Case]:
    _clean()
    out: list[Case] = []
    ss = _open()
    ss.grant_caller("owner", can_pin_map=True, can_mutate=True)
    try:
        check_permission(ss.acl, caller=None, permission="mutate")
    except MemNetError as exc:
        out.append(
            Case(
                name="acl_who",
                kind="hard_refuse",
                default="ACL off until session acl-enable / grant / bind or MEMNET_ACL=1",
                knob="session acl-enable + --caller / MEMNET_CALLER",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message, exc.example),
            )
        )
    try:
        check_permission(ss.acl, caller="intruder", permission="pin_map")
    except MemNetError as exc:
        out.append(
            Case(
                name="acl_denied",
                kind="hard_refuse",
                default="unknown caller",
                knob="session acl-grant",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message, exc.example),
            )
        )
    ss.grant_caller("reader", can_pin_map=True, can_mutate=False)
    try:
        MutateGate(ss).apply([_cst(1)], mode="add", caller="reader", require_bind=True)
    except MemNetError as exc:
        out.append(
            Case(
                name="acl_forbidden",
                kind="hard_refuse",
                default="pin_map vs mutate grant",
                knob="session acl-grant --no-mutate / --no-pin-map",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message),
            )
        )
    ss.set_bind("mission_a", "lease_1")
    try:
        MutateGate(ss).apply(
            [_cst(1)],
            mode="add",
            caller="owner",
            mission_id="wrong",
            lease="lease_1",
            require_bind=True,
        )
    except MemNetError as exc:
        out.append(
            Case(
                name="acl_bind",
                kind="hard_refuse",
                default="no bind until session acl-bind",
                knob="--mission-id + --lease / MEMNET_MISSION_ID + MEMNET_LEASE",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message, exc.example),
                extra={
                    "serve_path": (
                        "memnet serve sets MEMNET_SERVE_INTERNAL=1 so CLI require_bind "
                        "is False and bind match is skipped on serve/MCP in-process"
                    )
                },
                bug=(
                    "TCP/IPC serve sets MEMNET_SERVE_INTERNAL=1, so session bind is not "
                    "enforced on the product-gate serve path (who/scope still are)"
                ),
            )
        )
    from memnet.acl import WorkerWriteScope

    ss2 = _open()
    ss2.grant_caller(
        "worker",
        can_pin_map=True,
        can_mutate=True,
        write_scope=WorkerWriteScope(ids=frozenset({"N01"})),
    )
    MutateGate(ss2).apply([_cst(1)], mode="add", caller="worker", require_bind=True)
    try:
        MutateGate(ss2).apply([_cst(2)], mode="add", caller="worker", require_bind=True)
        raise AssertionError("expected acl_scope")
    except MemNetError as exc:
        out.append(
            Case(
                name="acl_scope",
                kind="hard_refuse",
                default="empty scope = no id-level gate",
                knob="acl-grant --write-scope / mutate write_scope",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message),
                extra={"partial": "first in-scope write stayed; second refused (separate batches)"},
            )
        )
    return out


def case_reserve() -> Case:
    _clean()
    ss = _open()
    MutateGate(ss).apply([_cst(1)], mode="add")
    from memnet.neighbourhood_reserve import reserve

    reserve(ss.reserves, ss.store, anchor="N01", llm_id="llm_a", depth=1, ttl_s=120)
    try:
        reserve(ss.reserves, ss.store, anchor="N01", llm_id="llm_b", depth=1, ttl_s=120)
        raise AssertionError("expected reserve_conflict")
    except MemNetError as exc:
        return Case(
            name="reserve_conflict",
            kind="hard_refuse",
            default="RSV off until reserve(); ttl_s 1..86400 default 120",
            knob="memnet reserve / MCP reserve",
            library_code=exc.code,
            library_message=exc.message,
            wire=format_err(exc.code, exc.message),
        )


def case_slice_budget() -> Case:
    _clean()
    from memnet.import_absorb import export_working_memory_slice

    ss = _star_session(leaves=6)
    try:
        sl = export_working_memory_slice(ss, anchors=["N00", "N01"], depth=2, max_rows=1)
        return Case(
            name="import_slice_budget",
            kind="not_reachable_via_pin_map",
            default="max_rows × anchors (DEFAULT_QUERY_MAX_ROWS=50)",
            knob="import-slice max_rows / anchors",
            extra={
                "exported": str(len(sl.records)),
                "note": (
                    "export_working_memory_slice clips each anchor with pin_map "
                    "first, so len(by_id) cannot exceed max_rows × anchors"
                ),
            },
        )
    except MemNetError as exc:
        return Case(
            name="import_slice_budget",
            kind="hard_refuse",
            default="max_rows × anchors (DEFAULT_QUERY_MAX_ROWS=50)",
            knob="import-slice max_rows / anchors",
            library_code=exc.code,
            library_message=exc.message,
            wire=format_err(exc.code, exc.message),
        )


def case_frame_too_large() -> Case:
    _clean()
    from memnet.serve import send_command

    with env_caps(MEMNET_SERVE_MAX_FRAME_BYTES="20"):
        resp = send_command(["session", "list"])
        return Case(
            name="serve_frame_cap",
            kind="hard_refuse",
            default="4194304 (4 MiB)",
            knob="MEMNET_SERVE_MAX_FRAME_BYTES",
            library_code="frame_too_large",
            library_message="request payload (varies) bytes exceeds cap 20",
            wire=redact((resp.get("stderr") or "").strip()),
            extra={"exit_code": str(resp.get("exit_code"))},
        )


def case_lock_timeout_unused() -> Case:
    _clean()
    stored = Caps().lock_timeout_ms
    return Case(
        name="lock_timeout_ms",
        kind="configured_not_enforced",
        default="2000",
        knob="MEMNET_LOCK_TIMEOUT_MS",
        extra={
            "stored": str(stored),
            "note": (
                "Caps.lock_timeout_ms is stored; SessionStore.lock uses "
                "threading.RLock with no timeout"
            ),
        },
        bug="MEMNET_LOCK_TIMEOUT_MS is read but never applied to session locks",
    )


def case_warn_budget() -> Case:
    _clean()
    from memnet.output import format_wrn, reset_warn_budget

    reset_warn_budget()
    emitted = 0
    dropped = 0
    for i in range(20):
        line = format_wrn("near_cap", f"rows|{i}/5000|housekeep recommended")
        if line:
            emitted += 1
        else:
            dropped += 1
    reset_warn_budget()
    return Case(
        name="warn_budget",
        kind="silent_clip",
        default="12 (@WRN lines per call)",
        knob="MAX_WRN_PER_CALL / output._MAX_WRN (not env)",
        extra={"emitted": str(emitted), "dropped": str(dropped)},
        bug="extra @WRN lines after 12 are dropped with no Truncation mark",
    )


def case_ingest_vs_row_cap(tmp_path: Path) -> Case:
    _clean()
    if not _SYSML_MAP.is_file():
        return Case(
            name="ingest_commit_row_cap",
            kind="skipped",
            default="",
            knob="",
            extra={"reason": "sysml example map missing"},
        )
    path = tmp_path / "house.sysml"
    parts = "\n".join(f"  part def P{i:04d};" for i in range(8))
    path.write_text(f"package House {{\n{parts}\n}}\n", encoding="utf-8")
    with env_caps(MEMNET_MAX_ROWS="3"):
        ss = open_session(map_file=str(_SYSML_MAP), caps=Caps())
        before = ss.store.row_count_non_law()
        try:
            ingest_sysml(ss, path, max_nodes=2000, max_edges=2000)
            raise AssertionError("expected row cap on ingest commit")
        except MemNetError as exc:
            after = ss.store.row_count_non_law()
            return Case(
                name="ingest_commit_row_cap",
                kind="hard_refuse",
                default="session MEMNET_MAX_ROWS still applies after ingest_budget",
                knob="MEMNET_MAX_ROWS during Path-B commit",
                library_code=exc.code,
                library_message=exc.message,
                wire=format_err(exc.code, exc.message),
                extra={
                    "rows_before": str(before),
                    "rows_after": str(after),
                    "rollback": "all-or-nothing" if after == before else "PARTIAL",
                },
                bug=""
                if after == before
                else "ingest commit left partial rows after session row cap",
            )


def collect_all(tmp_path: Path) -> list[Case]:
    cases: list[Case] = [
        case_ingest_node_budget(tmp_path),
        case_ingest_edge_budget(tmp_path),
        case_ingest_file_budget(tmp_path),
        case_session_row_cap(),
        case_row_cap_batch_rollback(),
        case_relation_cap_safe(),
        case_unknown_relation(),
        case_law_cap(),
        *case_tag_and_field_caps(),
        *case_pipe_value_and_line_bytes(),
        case_batch_lines(),
        case_pin_map_max_rows(),
        case_pin_map_depth(),
        case_pin_map_fanout(),
        case_pin_map_shell(),
        case_query_walk_silent(),
        case_leftover_context_silent(),
        case_outline_clip(),
        case_find_cue_conflict(),
        case_session_count(),
        *case_ttl_and_expire(tmp_path),
        *case_acl(),
        case_reserve(),
        case_slice_budget(),
        case_frame_too_large(),
        case_lock_timeout_unused(),
        case_warn_budget(),
        case_ingest_vs_row_cap(tmp_path),
    ]
    return cases


def render_proof(cases: list[Case], *, defaults: dict) -> str:
    lines = [
        "MemNet cap-contract proof log",
        "Session ids redacted. No product names.",
        "",
        "== library defaults ==",
    ]
    for key, val in defaults.items():
        lines.append(f"{key}={val}")
    lines.append("")
    lines.append("== cases ==")
    for case in cases:
        lines.append(f"[{case.name}]")
        lines.append(f"  kind: {case.kind}")
        lines.append(f"  default: {case.default}")
        lines.append(f"  knob: {case.knob}")
        if case.library_code:
            lines.append(f"  library_code: {case.library_code}")
        if case.library_message:
            lines.append(f"  library_message: {redact(case.library_message)}")
        if case.wire:
            lines.append(f"  wire: {redact(case.wire)}")
        if case.mcp:
            lines.append(f"  mcp: {redact(case.mcp)}")
        for key, val in case.extra.items():
            lines.append(f"  {key}: {redact(str(val))}")
        if case.bug:
            lines.append(f"  BUG: {case.bug}")
        lines.append("")
    blob = "\n".join(lines) + "\n"
    if _SID_RE.search(blob):
        raise AssertionError("proof log leaked a session id")
    return blob


def dump_json(cases: list[Case], *, defaults: dict) -> str:
    payload = {
        "defaults": defaults,
        "cases": [
            {
                "name": c.name,
                "kind": c.kind,
                "default": c.default,
                "knob": c.knob,
                "library_code": c.library_code,
                "library_message": redact(c.library_message),
                "wire": redact(c.wire),
                "mcp": redact(c.mcp),
                "extra": {k: redact(str(v)) for k, v in c.extra.items()},
                "bug": c.bug,
            }
            for c in cases
        ],
    }
    blob = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if _SID_RE.search(blob):
        raise AssertionError("proof json leaked a session id")
    return blob
