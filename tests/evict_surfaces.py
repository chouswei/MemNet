"""MN-REQ-05.5 surface lists, shared by the runtime and sysml sync tests.

A helper, not a test module: pytest does not collect it. The READ-SURFACES,
NON-TOUCH-READS and MAINTENANCE-SAVES blocks in sysml-models/models/requirements.sysml
name the same entries; tests/test_sysml_session_evict.py asserts they stay equal.
Also the shared clock, the CLI runner and the caller_read driver used by the
runtime tests (tests/test_session_evict.py, tests/test_read_touch_regression.py).
"""

import asyncio
import json
from datetime import UTC, datetime

from typer.testing import CliRunner

from memnet.cli import app
from memnet.session import get_session

BASE = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
runner = CliRunner()

# Caller reads: each one SHALL set modified_at through SessionStore.touch().
# READ_SURFACES is the MCP read tools plus the CLI-only reads (CLI_READ_ARGV)
# plus the in-process get_session.
READ_SURFACES = (
    "get_session",
    "pin_map",
    "query_warm",
    "find",
    "query_walk",
    "read_list",
    "export_pin_map",
    "housekeep_stats",
    "session_current",
    "session_resume",
    "tagmap_show",
    "relations_list",
    "query_neighbors",
    "query_path",
    "query_context",
    "housekeep_stale",
    "housekeep_orphans",
    "housekeep_dangling",
    "housekeep_recyclable",
)
# Reads that SHALL NOT touch: status, listing, usage and checkpoint verification.
NON_TOUCH_READS = (
    "serve_status",
    "session_list",
    "admin_usage_report",
    "admin_checkpoint_verify",
)
# Saves that SHALL NOT touch: they write a file, they are not reads.
# evict_save is the eviction's own save, so it has no surface of its own yet.
MAINTENANCE_SAVES = (
    "session_save",
    "expire_save",
    "admin_checkpoint",
    "evict_save",
)
# Maintenance saves with no MCP tool or admin command of their own; the engine runs them.
ENGINE_SAVES = frozenset({"expire_save", "evict_save"})
# CLI-only caller reads (no MCP tool). "{sid}" is the session id; each argv
# names ids that workflow.example.txt seeds (PLR01, TEC01, E02).
CLI_READ_ARGV = {
    "session_resume": ("session", "resume", "{sid}"),
    "tagmap_show": ("tagmap", "show", "--session", "{sid}"),
    "relations_list": ("relations", "list", "--session", "{sid}"),
    "query_neighbors": ("query", "neighbors", "PLR01", "--session", "{sid}"),
    "query_path": ("query", "path", "PLR01", "TEC01", "--session", "{sid}"),
    "query_context": ("query", "context", "--session", "{sid}"),
    "housekeep_stale": ("housekeep", "stale", "--session", "{sid}"),
    "housekeep_orphans": ("housekeep", "orphans", "--session", "{sid}"),
    "housekeep_dangling": ("housekeep", "dangling", "--session", "{sid}"),
    "housekeep_recyclable": ("housekeep", "recyclable", "--session", "{sid}"),
}
# Registered MCP tools that are not caller reads: writes, lifecycle, lease verbs.
# Every other registered tool must be a READ-SURFACES or NON-TOUCH-READS entry, so a
# new tool fails test_every_caller_mcp_read_tool_is_listed until it is classified.
MCP_NON_READ_TOOLS = frozenset(
    {
        "add",
        "extend",
        "import_slice",
        "ingest_codebase",
        "ingest_pcba",
        "ingest_skills",
        "ingest_sysml",
        "mutate",
        "release",
        "reserve",
        "session_acl_bind",
        "session_acl_enable",
        "session_acl_grant",
        "session_close",
        "session_load",
        "session_open",
        "session_save",
        "snap_model",
        "update",
    }
)
# CLI function name -> surface name, where the CLI function is named differently
# from its MCP tool or classification entry. Other session-scoped commands match by name.
CLI_SURFACE_ALIAS = {
    "add_cmd": "add",
    "delete_cmd": "delete",
    "export_pin_map_cmd": "export_pin_map",
    "extend_cmd": "extend",
    "import_slice_cmd": "import_slice",
    "ingest_codebase_cmd": "ingest_codebase",
    "ingest_pcba_cmd": "ingest_pcba",
    "ingest_skills_cmd": "ingest_skills",
    "ingest_sysml_cmd": "ingest_sysml",
    "mutate_cmd": "mutate",
    "prune_stale_cmd": "prune_stale",
    "query_find": "find",
    "query_pin_map": "pin_map",
    "release_cmd": "release",
    "reserve_cmd": "reserve",
    "update_cmd": "update",
}
# Session-scoped CLI writes and prunes with no MCP tool of the same name.
CLI_ONLY_NON_READ = frozenset(
    {"delete", "prune_dangling", "prune_orphans", "prune_recyclable", "prune_stale"}
)

# Arguments beyond the session for the MCP caller reads that need them.
_READ_ARGS = {
    "find": {"limit": 5, "kind": "PLR"},
    "query_walk": {"cue": "PLR01"},
    "read_list": {"tag": "PLR"},
}
# Engine saves (ENGINE_SAVES) to the dotted path of the function that runs them.
# tests/test_sysml_session_evict.py asserts each path imports and names a callable.
ENGINE_SAVE_FUNCS = {
    "expire_save": "memnet.session.snapshot_expired_session",
    "evict_save": "memnet.session.save_evict_victim",
}


def caller_read(surface: str, sid: str) -> int:
    """One session-scoped caller read through the surface named in READ_SURFACES.

    Returns the exit code. The text of a failure is not returned: it can name ids.
    get_session() raises on failure, so its exit code is 0 or the call raises.
    """
    if surface == "get_session":
        get_session(sid)
        return 0
    if surface in CLI_READ_ARGV:
        argv = [a.format(sid=sid) for a in CLI_READ_ARGV[surface]]
        return runner.invoke(app, argv).exit_code
    from memnet_mcp import server as mcp_server

    call = getattr(mcp_server, surface)
    resp = json.loads(asyncio.run(call(session=sid, **_READ_ARGS.get(surface, {}))))
    return resp["exit_code"]
