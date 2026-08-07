"""Tests for memnet-mcp streamable-http (bind gate, bearer, loopback smoke)."""

from __future__ import annotations

import socket
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from memnet_mcp.http_transport import (
    DEFAULT_MCP_HTTP_PORT,
    McpHttpBindError,
    SharedBearerASGI,
    build_streamable_http_app,
    build_transport_security,
    mcp_http_allow_remote,
    mcp_http_host,
    mcp_http_path,
    mcp_http_port,
    mcp_http_token,
    mcp_http_trusted_hosts,
    validate_mcp_http_bind_host,
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_mcp_http_env_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MEMNET_MCP_HTTP_HOST", raising=False)
    monkeypatch.delenv("MEMNET_MCP_HTTP_PORT", raising=False)
    monkeypatch.delenv("MEMNET_MCP_HTTP_PATH", raising=False)
    monkeypatch.delenv("MEMNET_MCP_HTTP_TOKEN", raising=False)
    monkeypatch.delenv("MEMNET_MCP_ALLOW_REMOTE", raising=False)
    monkeypatch.delenv("MEMNET_MCP_HTTP_TRUSTED_HOSTS", raising=False)
    assert mcp_http_host() == "127.0.0.1"
    assert mcp_http_port() == DEFAULT_MCP_HTTP_PORT == 18766
    assert mcp_http_path() == "/mcp"
    assert mcp_http_token() is None
    assert not mcp_http_allow_remote()
    assert mcp_http_trusted_hosts() is None


def test_trusted_hosts_parse(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMNET_MCP_HTTP_TRUSTED_HOSTS", "10.0.0.10, localhost")
    assert mcp_http_trusted_hosts() == ["10.0.0.10", "localhost"]


def test_transport_security_loopback():
    pytest.importorskip("mcp")
    sec = build_transport_security("127.0.0.1")
    assert sec is not None
    assert sec.enable_dns_rebinding_protection
    assert "127.0.0.1:*" in sec.allowed_hosts
    assert "localhost:*" in sec.allowed_hosts


def test_transport_security_lan_ip_adds_bind_host(monkeypatch: pytest.MonkeyPatch):
    pytest.importorskip("mcp")
    monkeypatch.delenv("MEMNET_MCP_HTTP_TRUSTED_HOSTS", raising=False)
    sec = build_transport_security("10.0.0.10")
    assert sec is not None
    assert sec.enable_dns_rebinding_protection
    assert "10.0.0.10:*" in sec.allowed_hosts
    assert "http://10.0.0.10:*" in sec.allowed_origins


def test_transport_security_unspecified_without_allowlist_disables(
    monkeypatch: pytest.MonkeyPatch,
):
    pytest.importorskip("mcp")
    monkeypatch.delenv("MEMNET_MCP_HTTP_TRUSTED_HOSTS", raising=False)
    sec = build_transport_security("0.0.0.0")
    assert sec is not None
    assert not sec.enable_dns_rebinding_protection


def test_transport_security_unspecified_with_allowlist(monkeypatch: pytest.MonkeyPatch):
    pytest.importorskip("mcp")
    monkeypatch.setenv("MEMNET_MCP_HTTP_TRUSTED_HOSTS", "10.0.0.10")
    sec = build_transport_security("0.0.0.0")
    assert sec is not None
    assert sec.enable_dns_rebinding_protection
    assert "10.0.0.10:*" in sec.allowed_hosts
    assert "127.0.0.1:*" in sec.allowed_hosts


def test_transport_security_star_disables(monkeypatch: pytest.MonkeyPatch):
    pytest.importorskip("mcp")
    monkeypatch.setenv("MEMNET_MCP_HTTP_TRUSTED_HOSTS", "*")
    sec = build_transport_security("10.0.0.10")
    assert sec is not None
    assert not sec.enable_dns_rebinding_protection


def test_mcp_http_path_normalises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMNET_MCP_HTTP_PATH", "mcp")
    assert mcp_http_path() == "/mcp"


def test_remote_bind_refused_without_allow(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MEMNET_MCP_ALLOW_REMOTE", raising=False)
    with pytest.raises(McpHttpBindError, match="MEMNET_MCP_ALLOW_REMOTE"):
        validate_mcp_http_bind_host("0.0.0.0")
    with pytest.raises(McpHttpBindError):
        validate_mcp_http_bind_host("10.0.0.10")


def test_remote_bind_allowed_with_opt_in(monkeypatch: pytest.MonkeyPatch, capsys):
    monkeypatch.setenv("MEMNET_MCP_ALLOW_REMOTE", "1")
    monkeypatch.delenv("MEMNET_MCP_HTTP_TOKEN", raising=False)
    validate_mcp_http_bind_host("10.0.0.10", token=None)
    err = capsys.readouterr().err
    assert "MEMNET_MCP_ALLOW_REMOTE" in err
    assert "MEMNET_MCP_HTTP_TOKEN is empty" in err


def test_loopback_bind_ok_without_allow(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MEMNET_MCP_ALLOW_REMOTE", raising=False)
    validate_mcp_http_bind_host("127.0.0.1")
    validate_mcp_http_bind_host("localhost")


async def _ok_app(scope, receive, send):
    if scope["type"] != "http":
        return
    body = b'{"ok":true}'
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", b"10"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def test_shared_bearer_rejects_without_token():
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    app = SharedBearerASGI(_ok_app, "secret-token")
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 401
    assert r.json()["error"] == "unauthorized"


def test_shared_bearer_accepts_matching_token():
    pytest.importorskip("starlette")
    from starlette.testclient import TestClient

    app = SharedBearerASGI(_ok_app, "secret-token")
    client = TestClient(app)
    r = client.get("/", headers={"Authorization": "Bearer secret-token"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


mcp_pkg = pytest.importorskip("mcp")


def test_loopback_streamable_http_smoke(monkeypatch: pytest.MonkeyPatch):
    """Start streamable-http on loopback; TCP accept + bearer gate."""
    import uvicorn
    from mcp.server.fastmcp import FastMCP

    monkeypatch.delenv("MEMNET_MCP_ALLOW_REMOTE", raising=False)
    monkeypatch.setenv("MEMNET_MCP_HTTP_TOKEN", "smoke-token")

    port = _free_port()
    path = "/mcp"
    host = "127.0.0.1"
    server_mcp = FastMCP("memnet-http-smoke", host=host, port=port, streamable_http_path=path)

    @server_mcp.tool()
    def ping() -> str:
        return "pong"

    app = build_streamable_http_app(
        server_mcp,
        host=host,
        port=port,
        path=path,
        token="smoke-token",
    )
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 8.0
    while time.time() < deadline:
        if server.started:
            break
        time.sleep(0.05)
    else:
        server.should_exit = True
        pytest.fail("uvicorn did not start")

    url = f"http://{host}:{port}{path}"
    try:
        with pytest.raises(HTTPError) as no_auth:
            urlopen(Request(url, method="GET"), timeout=3.0)
        assert no_auth.value.code == 401

        req = Request(url, method="GET", headers={"Authorization": "Bearer smoke-token"})
        try:
            with urlopen(req, timeout=3.0) as resp:
                # MCP may reject bare GET; any non-401 proves the gate passed.
                assert resp.status != 401
        except HTTPError as exc:
            assert exc.code != 401, "bearer should pass the shared-token gate"
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)


def test_cli_remote_bind_exits(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MEMNET_MCP_ALLOW_REMOTE", raising=False)
    from memnet_mcp.server import main

    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--transport",
                "streamable-http",
                "--host",
                "10.0.0.10",
                "--port",
                "18766",
            ]
        )
    assert exc.value.code == 2
