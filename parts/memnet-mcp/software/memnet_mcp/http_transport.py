"""Opt-in streamable-http MCP transport for remote Cursor ``url`` clients.

Default bind is loopback ``127.0.0.1:18766`` path ``/mcp``. Non-loopback bind
requires ``MEMNET_MCP_ALLOW_REMOTE=1``. Optional shared bearer
``MEMNET_MCP_HTTP_TOKEN`` — when set, unauthenticated requests are rejected.
Empty token plus LAN bind is unsafe (documented warning).
"""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING, Any

from memnet.serve import is_loopback_bind_host

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

DEFAULT_MCP_HTTP_HOST = "127.0.0.1"
DEFAULT_MCP_HTTP_PORT = 18766
DEFAULT_MCP_HTTP_PATH = "/mcp"


class McpHttpBindError(RuntimeError):
    """Non-loopback MCP HTTP bind refused without MEMNET_MCP_ALLOW_REMOTE."""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def mcp_http_host() -> str:
    return os.environ.get("MEMNET_MCP_HTTP_HOST", DEFAULT_MCP_HTTP_HOST)


def mcp_http_port() -> int:
    return _env_int("MEMNET_MCP_HTTP_PORT", DEFAULT_MCP_HTTP_PORT)


def mcp_http_path() -> str:
    raw = os.environ.get("MEMNET_MCP_HTTP_PATH", DEFAULT_MCP_HTTP_PATH).strip()
    if not raw:
        return DEFAULT_MCP_HTTP_PATH
    if not raw.startswith("/"):
        return f"/{raw}"
    return raw


def mcp_http_token() -> str | None:
    """Shared bearer token; None when unset or empty (auth disabled)."""
    raw = os.environ.get("MEMNET_MCP_HTTP_TOKEN")
    if raw is None:
        return None
    token = raw.strip()
    return token or None


def mcp_http_allow_remote() -> bool:
    raw = os.environ.get("MEMNET_MCP_ALLOW_REMOTE", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def validate_mcp_http_bind_host(host: str, *, token: str | None = None) -> None:
    """Refuse non-loopback binds unless MEMNET_MCP_ALLOW_REMOTE is set.

    Warns when LAN bind is allowed with an empty token (unsafe).
    """
    if is_loopback_bind_host(host):
        return
    if not mcp_http_allow_remote():
        raise McpHttpBindError(
            f"refusing non-loopback MCP HTTP bind {host!r}: set "
            "MEMNET_MCP_ALLOW_REMOTE=1 to expose memnet-mcp beyond localhost"
        )
    sys.stderr.write(
        f"WARNING: memnet-mcp streamable-http binding to non-loopback {host!r} "
        f"(MEMNET_MCP_ALLOW_REMOTE=1).\n"
    )
    effective = token if token is not None else mcp_http_token()
    if not effective:
        sys.stderr.write(
            "WARNING: MEMNET_MCP_HTTP_TOKEN is empty — LAN MCP HTTP has no "
            "bearer gate. Set a shared token before advertising this URL.\n"
        )
    sys.stderr.flush()


class SharedBearerASGI:
    """Reject HTTP requests without ``Authorization: Bearer <token>`` when set."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers") or ()
        }
        auth = headers.get("authorization", "")
        expected = f"Bearer {self.token}"
        if auth == expected:
            await self.app(scope, receive, send)
            return
        body = json.dumps(
            {"error": "unauthorized", "error_description": "Bearer token required"}
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"www-authenticate", b'Bearer error="invalid_token"'),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def apply_http_settings(
    mcp: FastMCP,
    *,
    host: str,
    port: int,
    path: str,
) -> None:
    """Mutate FastMCP settings for streamable-http bind."""
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.streamable_http_path = path


def build_streamable_http_app(
    mcp: FastMCP,
    *,
    host: str | None = None,
    port: int | None = None,
    path: str | None = None,
    token: str | None = None,
) -> Any:
    """Configure FastMCP and return the ASGI app (optional bearer wrap)."""
    bind_host = host if host is not None else mcp_http_host()
    bind_port = port if port is not None else mcp_http_port()
    bind_path = path if path is not None else mcp_http_path()
    effective_token = token if token is not None else mcp_http_token()

    validate_mcp_http_bind_host(bind_host, token=effective_token)
    apply_http_settings(mcp, host=bind_host, port=bind_port, path=bind_path)

    app = mcp.streamable_http_app()
    if effective_token:
        return SharedBearerASGI(app, effective_token)
    return app


def run_streamable_http(
    mcp: FastMCP,
    *,
    host: str | None = None,
    port: int | None = None,
    path: str | None = None,
    token: str | None = None,
) -> None:
    """Run uvicorn with streamable-http (blocking). Same tool surface as stdio."""
    import anyio
    import uvicorn

    bind_host = host if host is not None else mcp_http_host()
    bind_port = port if port is not None else mcp_http_port()
    bind_path = path if path is not None else mcp_http_path()
    effective_token = token if token is not None else mcp_http_token()

    app = build_streamable_http_app(
        mcp,
        host=bind_host,
        port=bind_port,
        path=bind_path,
        token=effective_token,
    )

    sys.stderr.write(
        f"MEMNET_MCP_HTTP={bind_host}:{bind_port}{bind_path} "
        f"transport=streamable-http "
        f"auth={'bearer' if effective_token else 'off'}\n"
    )
    sys.stderr.flush()

    async def _serve() -> None:
        config = uvicorn.Config(
            app,
            host=bind_host,
            port=bind_port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()

    anyio.run(_serve)
