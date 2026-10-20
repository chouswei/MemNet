"""MN-REQ-05.5 surface lists, shared by the runtime and sysml sync tests.

A helper, not a test module: pytest does not collect it. The READ-SURFACES,
NON-TOUCH-READS and MAINTENANCE-SAVES blocks in sysml-models/models/requirements.sysml
name the same entries; tests/test_sysml_session_evict.py asserts they stay equal.
"""

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
