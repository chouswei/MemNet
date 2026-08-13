"""Tests for LocalIpcGateway AF_UNIX share (MN-REQ-06.2)."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest

from memnet.local_ipc_gateway import (
    IMPLEMENTED,
    LocalIpcGateway,
    probe,
    run_ipc_serve,
    send_command,
)
from memnet.session import purge_expired, reset_registry

pytestmark = pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"),
    reason="AF_UNIX required for LocalIpcGateway",
)


@pytest.fixture
def ipc_serve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_registry()
    purge_expired()
    sock = str(tmp_path / "memnet.sock")
    monkeypatch.setenv("MEMNET_IPC_SOCKET", sock)
    monkeypatch.delenv("MEMNET_TEST_INLINE", raising=False)
    monkeypatch.delenv("MEMNET_SERVE_INTERNAL", raising=False)
    monkeypatch.delenv("MEMNET_SESSION", raising=False)

    thread = threading.Thread(target=run_ipc_serve, kwargs={"path": sock}, daemon=True)
    thread.start()
    for _ in range(100):
        if probe(path=sock):
            break
        time.sleep(0.05)
    else:
        pytest.fail("LocalIpcGateway did not start")

    yield sock
    reset_registry()
    purge_expired()


def _session_id(response: dict) -> str:
    for line in (response.get("stdout") or "").splitlines():
        if line.startswith("@SESSION:"):
            return line.split("|", 1)[0].replace("@SESSION:", "").strip()
    raise AssertionError(f"no session in response: {response!r}")


def test_local_ipc_gateway_implemented():
    assert IMPLEMENTED is True
    assert LocalIpcGateway.implemented is True


def test_second_client_pin_map_via_socket(ipc_serve, schema_file):
    """Two clients share one registry over AF_UNIX (MN-REQ-06.2)."""
    sock = ipc_serve
    open_resp = send_command(
        ["session", "open", "--map-file", str(schema_file)],
        path=sock,
    )
    assert open_resp["exit_code"] == 0, open_resp
    sid = _session_id(open_resp)

    add_resp = send_command(
        ["add", "--stdin", "--session", sid],
        stdin="@PLR: PLR50|IpcShare|1|0|0|0|bag",
        path=sock,
    )
    assert add_resp["exit_code"] == 0, add_resp

    # Second client (fresh connection) reads the same session via pin_map.
    pin_resp = send_command(
        ["query", "pin-map", "--anchor", "PLR50", "--session", sid],
        path=sock,
    )
    assert pin_resp["exit_code"] == 0, pin_resp
    assert "PLR50" in pin_resp["stdout"]


def test_ipc_probe_false_when_down(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    sock = str(tmp_path / "missing.sock")
    monkeypatch.setenv("MEMNET_IPC_SOCKET", sock)
    assert probe(path=sock) is False


def test_ipc_gateway_send_probe(ipc_serve):
    gw = LocalIpcGateway(path=ipc_serve)
    assert gw.probe() is True
    resp = gw.send(["version"])
    assert resp["exit_code"] == 0
    assert "memnet" in (resp.get("stdout") or "").lower() or "0." in (resp.get("stdout") or "")


def test_serve_client_prefers_ipc(ipc_serve, schema_file, monkeypatch: pytest.MonkeyPatch):
    from memnet.serve_client import dispatch

    monkeypatch.setenv("MEMNET_IPC_SOCKET", ipc_serve)
    monkeypatch.delenv("MEMNET_TEST_INLINE", raising=False)
    monkeypatch.delenv("MEMNET_SERVE_INTERNAL", raising=False)

    code = dispatch(["session", "open", "--map-file", str(schema_file)])
    assert code == 0
