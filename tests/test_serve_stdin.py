"""Tests for memnet serve TCP stdin field."""

from __future__ import annotations

import socket
import threading
import time

import pytest

from memnet.serve import probe, run_serve, send_command
from memnet.session import purge_expired, reset_registry


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _session_id(response: dict) -> str:
    for line in (response.get("stdout") or "").splitlines():
        if line.startswith("@SESSION:"):
            return line.split("|", 1)[0].replace("@SESSION:", "").strip()
    raise AssertionError(f"no session in response: {response!r}")


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


def test_send_command_without_stdin_unchanged(memnet_serve, schema_file):
    host, port = memnet_serve
    resp = send_command(
        ["session", "open", "--map-file", str(schema_file)],
        host=host,
        port=port,
    )
    assert resp["exit_code"] == 0
    assert "@SESSION:" in resp["stdout"]


def test_send_command_stdin_add(memnet_serve, schema_file):
    host, port = memnet_serve
    open_resp = send_command(
        ["session", "open", "--map-file", str(schema_file)],
        host=host,
        port=port,
    )
    sid = _session_id(open_resp)
    wire = "@PLR: PLR99|Test|1|0|0|0|bag"
    add_resp = send_command(
        ["add", "--stdin", "--session", sid],
        stdin=wire,
        host=host,
        port=port,
    )
    assert add_resp["exit_code"] == 0, add_resp
    get_resp = send_command(
        ["query", "pin-map", "--cue", "PLR99", "--session", sid],
        host=host,
        port=port,
    )
    assert get_resp["exit_code"] == 0
    assert "PLR99" in get_resp["stdout"]


def test_send_command_stdin_update(memnet_serve, schema_file):
    host, port = memnet_serve
    open_resp = send_command(
        ["session", "open", "--map-file", str(schema_file)],
        host=host,
        port=port,
    )
    sid = _session_id(open_resp)
    send_command(
        ["add", "--stdin", "--session", sid],
        stdin="@PLR: PLR98|Test|1|0|0|0|bag",
        host=host,
        port=port,
    )
    upd_resp = send_command(
        ["update", "--stdin", "--session", sid],
        stdin="@PLR: PLR98|Test|2|0|0|0|bag",
        host=host,
        port=port,
    )
    assert upd_resp["exit_code"] == 0, upd_resp
    get_resp = send_command(
        ["query", "pin-map", "--cue", "PLR98", "--session", sid],
        host=host,
        port=port,
    )
    assert get_resp["exit_code"] == 0, get_resp
    assert "2" in get_resp["stdout"]
