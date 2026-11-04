"""memnet-mcp console entry: check the mcp extra before loading the server."""

from __future__ import annotations

import sys

MCP_EXTRA_HINT = "pip install 'memnet-llm[mcp]'"


def _missing(exc: ImportError, tried: str) -> str:
    return (exc.name or tried).split(".")[0]


def require_mcp_extra() -> None:
    """Exit 2 with one stderr line when the mcp extra (mcp, uvicorn) is missing."""
    for module in ("mcp.server.fastmcp", "uvicorn"):
        try:
            __import__(module)
        except ImportError as exc:
            sys.stderr.write(
                "@ERR: mcp_extra_missing|memnet-mcp needs the mcp extra "
                f"(missing module: {_missing(exc, module)}); install with: {MCP_EXTRA_HINT}\n"
            )
            sys.stderr.flush()
            raise SystemExit(2) from None


def main(argv: list[str] | None = None) -> None:
    require_mcp_extra()
    from memnet_mcp.server import main as server_main

    server_main(argv)
