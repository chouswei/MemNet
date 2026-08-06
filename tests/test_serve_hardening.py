"""Tests for memnet serve TCP hardening (frame cap, bind gate)."""

from __future__ import annotations

import json
import socket
import struct
import threading
import time

import pytest

from memnet.config import DEFAULT_SERVE_MAX_FRAME_BYTES
from memnet.serve import (
    ServeBindError,
    is_loopback_bind_host,
    probe,
    run_serve,
    send_command,
    validate_serve_bind_host,
)
from memnet.session import purge_expired, reset_registry


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    chunks: list[bytes] = []
    got = 0
    while got < n:
        part = sock.recv(n - got)
        if not part:
            raise ConnectionError("connection closed")
        chunks.append(part)
        got += len(part)
    return b"".join(chunks)


@pytest.fixture
def memnet_serve(monkeypatch: pytest.MonkeyPatch):
    reset_registry()
    purge_expired()
    port = _free_port()
    host = "127.0.0.1"
    monkeypatch.setenv("MEMNET_SERVE_PORT", str(port))
    monkeypatch.setenv("MEMNET_SERVE_HOST", host)
    monkeypatch.delenv("MEMNET_TEST_INLINE", raising=False)
    monkeypatch.delenv("MEMNET_SERVE_INTERNAL", raising=False)
    monkeypatch.delenv("MEMNET_SESSION", raising=False)
    monkeypatch.delenv("MEMNET_SERVE_ALLOW_REMOTE", raising=False)

    thread = threading.Thread(target=run_serve, kwargs={"host": host, "port": port}, daemon=True)
    thread.start()
    for _ in range(100):
        if probe(host=host, port=port):
            break
        time.sleep(0.05)
    else:
        pytest.fail("memnet serve did not start")

    yield host, port
    reset_registry()
    purge_expired()


def test_is_loopback_bind_host_literals():
    assert is_loopback_bind_host("127.0.0.1")
    assert is_loopback_bind_host("localhost")
    assert is_loopback_bind_host("::1")
    assert not is_loopback_bind_host("0.0.0.0")
    assert not is_loopback_bind_host("10.0.0.10")


def test_remote_bind_refused_without_opt_in(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MEMNET_SERVE_ALLOW_REMOTE", raising=False)
    with pytest.raises(ServeBindError, match="MEMNET_SERVE_ALLOW_REMOTE"):
        validate_serve_bind_host("0.0.0.0")
    with pytest.raises(ServeBindError):
        validate_serve_bind_host("10.0.0.10")


def test_remote_bind_allowed_with_opt_in(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMNET_SERVE_ALLOW_REMOTE", "1")
    validate_serve_bind_host("0.0.0.0")
    validate_serve_bind_host("10.0.0.10")


def test_oversized_request_frame_rejected(memnet_serve, monkeypatch: pytest.MonkeyPatch):
    host, port = memnet_serve
    cap = 4096
    monkeypatch.setenv("MEMNET_SERVE_MAX_FRAME_BYTES", str(cap))
    oversized = cap + 1
    with socket.create_connection((host, port), timeout=5.0) as sock:
        sock.sendall(struct.pack(">I", oversized))
        raw_len = _recv_exact(sock, 4)
        (resp_len,) = struct.unpack(">I", raw_len)
        assert resp_len <= cap
        body = _recv_exact(sock, resp_len)
    resp = json.loads(body.decode("utf-8"))
    assert resp["exit_code"] == 1
    assert "frame_too_large" in resp["stderr"]


def test_bad_json_frame_returns_error(memnet_serve):
    host, port = memnet_serve
    payload = b"not-json"
    with socket.create_connection((host, port), timeout=5.0) as sock:
        sock.sendall(struct.pack(">I", len(payload)) + payload)
        raw_len = _recv_exact(sock, 4)
        (resp_len,) = struct.unpack(">I", raw_len)
        body = _recv_exact(sock, resp_len)
    resp = json.loads(body.decode("utf-8"))
    assert resp["exit_code"] == 1
    assert "bad_frame" in resp["stderr"]


def test_send_command_still_works(memnet_serve, schema_file):
    host, port = memnet_serve
    resp = send_command(
        ["session", "open", "--map-file", str(schema_file)],
        host=host,
        port=port,
    )
    assert resp["exit_code"] == 0
    assert "@SESSION:" in resp["stdout"]


def test_send_command_rejects_oversized_payload(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMNET_SERVE_MAX_FRAME_BYTES", "20")
    resp = send_command(["session", "open", "--map-file", "parts/common/memnet/memnet/examples/schema.example.txt"])
    assert resp["exit_code"] == 1
    assert "frame_too_large" in resp["stderr"]


def test_default_frame_cap_is_four_mib():
    assert DEFAULT_SERVE_MAX_FRAME_BYTES == 4 * 1024 * 1024
