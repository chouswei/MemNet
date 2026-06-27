"""Inline MCP server definitions for Cursor SDK beat runner."""

from __future__ import annotations

import sys
from pathlib import Path

from cursor_sdk import StdioMcpServerConfig

from app_config import repo_root

SERVE_HOST = "127.0.0.1"
SERVE_PORT = "18765"


def memnet_env(session_id: str | None = None) -> dict[str, str]:
    root = repo_root()
    env = {
        "MEMNET_SERVE_HOST": SERVE_HOST,
        "MEMNET_SERVE_PORT": SERVE_PORT,
        "MEMNET_WORKSPACE_ROOT": str(root),
    }
    if session_id:
        env["MEMNET_SESSION"] = session_id
    return env


def inline_mcp_servers(session_id: str | None = None) -> dict[str, StdioMcpServerConfig]:
    exe = sys.executable
    env = memnet_env(session_id)
    root = repo_root()
    return {
        "memnet": StdioMcpServerConfig(
            command=exe,
            args=["-m", "memnet_mcp.server"],
            env=env,
            cwd=root,
        ),
        "novel-writer": StdioMcpServerConfig(
            command=exe,
            args=["-m", "novel_mcp.server"],
            env=env,
            cwd=root,
        ),
    }
