"""Opt-in streamable-http MCP transport for remote Cursor ``url`` clients.

Default bind is loopback ``127.0.0.1:18766`` path ``/mcp``. Non-loopback bind
requires ``MEMNET_MCP_ALLOW_REMOTE=1``. Optional shared bearer
``MEMNET_MCP_HTTP_TOKEN`` — when set, unauthenticated requests are rejected.
Empty token plus LAN bind is unsafe (documented warning).

FastMCP DNS-rebinding protection (Host / Origin allowlist) is refreshed for the
actual bind host. Override with ``MEMNET_MCP_HTTP_TRUSTED_HOSTS`` (comma list;
``*`` disables the Host check for LAN opt-in).
"""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING, Any

from memnet.serve import is_loopback_bind_host

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings

DEFAULT_MCP_HTTP_HOST = "127.0.0.1"
DEFAULT_MCP_HTTP_PORT = 18766
DEFAULT_MCP_HTTP_PATH = "/mcp"

# Loopback patterns FastMCP uses when host is localhost.
_LOOPBACK_HOST_PATTERNS = ("127.0.0.1:*", "localhost:*", "[::1]:*")
_LOOPBACK_ORIGIN_PATTERNS = (
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
)


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


def mcp_http_trusted_hosts() -> list[str] | None:
    """Extra Host allowlist entries from MEMNET_MCP_HTTP_TRUSTED_HOSTS.

    Returns ``None`` when unset. A sole entry of ``*`` / ``off`` / ``disable``
    means disable DNS-rebinding Host checks (LAN escape hatch).
    """
    raw = os.environ.get("MEMNET_MCP_HTTP_TRUSTED_HOSTS")
    if raw is None:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts


def _is_wildcard_disable(hosts: list[str] | None) -> bool:
    if not hosts or len(hosts) != 1:
        return False
    return hosts[0].lower() in {"*", "off", "disable", "none"}


def _host_pattern(host: str) -> str:
    """Normalise a host or host:port to an allowed_hosts pattern."""
    h = host.strip()
    if not h:
        return h
    if h.endswith(":*") or ":" in h.split("]")[-1]:
        # Already has a port (or IPv6 with port), or explicit :* wildcard.
        return h
    return f"{h}:*"


def _origin_pattern(host: str) -> str:
    """Build an http:// origin pattern from a host or Host-header pattern."""
    h = host.strip()
    if h.lower().startswith("http://") or h.lower().startswith("https://"):
        if h.endswith(":*") or ":" in h.rsplit("/", 1)[-1].split("]")[-1]:
            return h
        return f"{h}:*"
    # Strip :* or :port for origin base, then re-add :*
    base = h
    if base.endswith(":*"):
        base = base[:-2]
    elif ":" in base.split("]")[-1]:
        # host:port → host
        if base.startswith("["):
            # [ipv6]:port
            end = base.rfind("]:")
            if end != -1:
                base = base[: end + 1]
        else:
            base = base.rsplit(":", 1)[0]
    return f"http://{base}:*"


def _is_unspecified_bind(host: str) -> bool:
    return host.strip().lower() in {"0.0.0.0", "::", "[::]"}


def build_transport_security(
    bind_host: str,
    *,
    trusted_hosts: list[str] | None = None,
) -> TransportSecuritySettings | None:
    """Build FastMCP TransportSecuritySettings for the bind host.

    FastMCP defaults ``transport_security`` for localhost at construction time.
    When we later rebind to LAN / ``0.0.0.0``, that localhost-only allowlist must
    be replaced — otherwise clients with ``Host: 10.0.0.10:18766`` get 421
    ``Invalid Host header``.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    extra = trusted_hosts if trusted_hosts is not None else mcp_http_trusted_hosts()
    if _is_wildcard_disable(extra):
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    # 0.0.0.0 / :: with no allowlist: Host is the client-facing address (e.g.
    # 10.0.0.10:18766), not the bind address. Keep protection only when the
    # operator listed hosts; otherwise disable (LAN already requires ALLOW_REMOTE).
    if _is_unspecified_bind(bind_host) and not extra:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    allowed_hosts: list[str] = list(_LOOPBACK_HOST_PATTERNS)
    allowed_origins: list[str] = list(_LOOPBACK_ORIGIN_PATTERNS)

    if not is_loopback_bind_host(bind_host) and not _is_unspecified_bind(bind_host):
        allowed_hosts.append(_host_pattern(bind_host))
        allowed_origins.append(_origin_pattern(bind_host))

    if extra:
        for entry in extra:
            if entry.lower() in {"*", "off", "disable", "none"}:
                continue
            allowed_hosts.append(_host_pattern(entry))
            allowed_origins.append(_origin_pattern(entry))

    # Deduplicate while preserving order
    def _uniq(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_uniq(allowed_hosts),
        allowed_origins=_uniq(allowed_origins),
    )


def validate_mcp_http_bind_host(host: str, *, token: str | None = None) -> None:
    """Refuse non-loopback binds unless MEMNET_MCP_ALLOW_REMOTE is set.

    Warns when LAN bind is allowed with an empty token (unsafe).
    Warns when binding ``0.0.0.0`` without MEMNET_MCP_HTTP_TRUSTED_HOSTS.
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
    trusted = mcp_http_trusted_hosts()
    if _is_unspecified_bind(host) and not trusted:
        sys.stderr.write(
            "WARNING: bind is 0.0.0.0/:: without MEMNET_MCP_HTTP_TRUSTED_HOSTS — "
            "DNS-rebinding Host checks are off. Prefer "
            "MEMNET_MCP_HTTP_TRUSTED_HOSTS=10.0.0.10 (comma-separated) to pin "
            "allowed Host headers.\n"
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
    """Mutate FastMCP settings for streamable-http bind + Host allowlist."""
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.streamable_http_path = path
    mcp.settings.transport_security = build_transport_security(host)


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

    security = getattr(mcp.settings, "transport_security", None)
    if security is None or not getattr(security, "enable_dns_rebinding_protection", True):
        host_note = "dns_rebinding=off"
    else:
        hosts = ",".join(getattr(security, "allowed_hosts", ()) or ())
        host_note = f"trusted_hosts={hosts}"

    sys.stderr.write(
        f"MEMNET_MCP_HTTP={bind_host}:{bind_port}{bind_path} "
        f"transport=streamable-http "
        f"auth={'bearer' if effective_token else 'off'} "
        f"{host_note}\n"
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
