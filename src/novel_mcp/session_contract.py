"""Shared-session playbook for memnet + novel-writer MCPs."""

from __future__ import annotations

from typing import Any

SESSION_CONTRACT: dict[str, Any] = {
    "one_session": "Pass the same session id to memnet-mcp and novel-writer MCP tools.",
    "memnet_for": [
        "session_open",
        "session_load",
        "session_save",
        "session_current",
        "ad_hoc add/update between beats",
        "debug read_get / query_walk",
    ],
    "novel_writer_for": [
        "beat_turn_begin — canonical per-beat read (presentation)",
        "beat_turn_finish — canonical per-beat commit",
    ],
    "do_not": [
        "query_warm on memnet in the same turn as beat_turn_begin",
        "memnet add/update after begin and before finish on the same beat",
    ],
}


def session_contract_block() -> dict[str, Any]:
    return dict(SESSION_CONTRACT)
