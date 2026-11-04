"""Serve wire keep_alive and the client ServePool, through real sockets (passthru-keepalive)."""

from __future__ import annotations

import json
import logging
import socket
import struct
import threading
import time
from typing import Any

import pytest

import memnet.serve as serve_mod
from memnet.serve import _Handler, _Server, probe, send_command

HOST = "127.0.0.1"


class _CountingServer(_Server):
    """In-process serve that counts accepted TCP connections and can drop them."""

    def __init__(self, addr: tuple[str, int]) -> None:
        self.accepts = 0
        self.conns: list[socket.socket] = []
        self._count_lock = threading.Lock()
        super().__init__(addr, _Handler)

    def get_request(self):  # type: ignore[override]
        sock, addr = super().get_request()
        with self._count_lock:
            self.accepts += 1
            self.conns.append(sock)
        return sock, addr

    def drop_conns(self) -> None:
        with self._count_lock:
            conns = list(self.conns)
        for conn in conns:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def _start(port: int = 0) -> tuple[_CountingServer, int]:
    server = _CountingServer((HOST, port))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, int(server.server_address[1])


def _stop(server: _CountingServer) -> None:
    server.shutdown()
    server.server_close()
    server.drop_conns()


def _reset_pool() -> None:
    try:
        from memnet.serve_pool import POOL
    except ImportError:
        return
    POOL.close_all()


@pytest.fixture
def served(memnet_temp, monkeypatch):
    monkeypatch.delenv("MEMNET_SERVE_KEEPALIVE", raising=False)
    _reset_pool()
    server, port = _start()
    try:
        yield server, port
    finally:
        _reset_pool()
        _stop(server)


@pytest.fixture
def seen_payloads(monkeypatch) -> list[dict[str, Any]]:
    """Record every payload the serve handles (keys as sent on the wire)."""
    seen: list[dict[str, Any]] = []
    real = serve_mod._handle_request

    def recording(payload: dict[str, Any]) -> dict[str, Any]:
        seen.append(dict(payload))
        return real(payload)

    monkeypatch.setattr(serve_mod, "_handle_request", recording)
    return seen


def _send_frame(sock: socket.socket, obj: dict[str, Any]) -> None:
    data = json.dumps(obj).encode("utf-8")
    sock.sendall(struct.pack(">I", len(data)) + data)


def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
    buf = b""
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            return None
        buf += part
    return buf


def _recv_frame(sock: socket.socket) -> dict[str, Any] | None:
    raw = _recv_exact(sock, 4)
    if raw is None:
        return None
    (length,) = struct.unpack(">I", raw)
    body = _recv_exact(sock, length)
    assert body is not None
    return json.loads(body.decode("utf-8"))


def _echo_args(marker: str) -> list[str]:
    # The serve echoes an unknown command name in its usage error.
    return [f"no-such-cmd-{marker}"]


class _FakeOneShotServe:
    """Old-style serve: one frame, reply without keep_alive, close. Records payloads."""

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST, 0))
        self.sock.listen(16)
        self.sock.settimeout(0.2)
        self.port = int(self.sock.getsockname()[1])
        self.accepts = 0
        self.payloads: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except (TimeoutError, OSError):
                continue
            self.accepts += 1
            with conn:
                conn.settimeout(5)
                try:
                    payload = _recv_frame(conn)
                except OSError:
                    continue
                if payload is None:
                    continue
                self.payloads.append(payload)
                _send_frame(
                    conn,
                    {"exit_code": 0, "stdout": f"echo {payload.get('args')}\n", "stderr": ""},
                )

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self.sock.close()


# (1) probe() then two send_command() calls share one TCP connection.
def test_probe_then_two_commands_use_one_connection(served):
    server, port = served
    assert probe(host=HOST, port=port) is True
    for _ in range(2):
        resp = send_command(["--version"], host=HOST, port=port)
        assert resp["exit_code"] == 0, resp
        assert "@VER:" in resp["stdout"]
    assert server.accepts == 1


# (2) A raw one-shot frame without keep_alive still gets a reply, then EOF.
def test_raw_one_shot_frame_reply_then_eof(served):
    _server, port = served
    with socket.create_connection((HOST, port), timeout=5) as sock:
        _send_frame(sock, {"args": ["--version"]})
        reply = _recv_frame(sock)
        assert reply is not None
        assert reply["exit_code"] == 0, reply
        assert "keep_alive" not in reply
        assert sock.recv(1) == b""


# (3) ServePool against an old one-shot serve that never sets keep_alive.
def test_pool_against_one_shot_serve(monkeypatch):
    from memnet.serve_pool import ServePool

    monkeypatch.delenv("MEMNET_SERVE_KEEPALIVE", raising=False)
    fake = _FakeOneShotServe()
    pool = ServePool()
    try:
        assert pool.probe(HOST, fake.port) is True
        for i in range(3):
            resp = pool.send(HOST, fake.port, {"args": [f"call-{i}"]}, 5.0)
            assert resp["exit_code"] == 0, resp
            assert f"call-{i}" in resp["stdout"]
            assert "keep_alive" not in resp
        assert [p["args"] for p in fake.payloads] == [["call-0"], ["call-1"], ["call-2"]]
        assert all(p.get("keep_alive") is True for p in fake.payloads)
        # The probe's fresh socket carries the first call; no reply set keep_alive.
        assert fake.accepts == 3
    finally:
        pool.close_all()
        fake.close()


# (4) Serve restarted on the same port between calls: the next call succeeds.
def test_serve_restart_same_port(memnet_temp, monkeypatch):
    monkeypatch.delenv("MEMNET_SERVE_KEEPALIVE", raising=False)
    _reset_pool()
    server, port = _start()
    try:
        resp = send_command(_echo_args("before"), host=HOST, port=port)
        assert "before" in resp["stderr"], resp
        _stop(server)
        server, _ = _start(port)
        resp = send_command(_echo_args("after"), host=HOST, port=port)
        assert "after" in resp["stderr"], resp
        assert server.accepts == 1
    finally:
        _reset_pool()
        _stop(server)


# (5) 8 threads x 20 calls: every reply matches its request.
def test_threads_no_crossed_replies(served):
    server, port = served
    n_threads, n_calls = 8, 20
    barrier = threading.Barrier(n_threads)
    errors: list[str] = []

    def run(t: int) -> None:
        barrier.wait(timeout=30)
        for c in range(n_calls):
            marker = f"t{t}x{c}z"
            try:
                resp = send_command(_echo_args(marker), host=HOST, port=port)
            except Exception as exc:  # noqa: BLE001 — collected for the assertion
                errors.append(f"{marker}: {type(exc).__name__}: {exc}")
                continue
            if f"no-such-cmd-{marker}'" not in resp.get("stderr", "") or "keep_alive" in resp:
                errors.append(f"{marker}: {resp!r}")

    threads = [threading.Thread(target=run, args=(t,)) for t in range(n_threads)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=120)
    assert not errors, errors[:5]
    # At most one socket per concurrent caller; the rest are reused.
    assert server.accepts <= n_threads


# (6) MEMNET_SERVE_KEEPALIVE=0: one connection per call, no keep_alive key sent.
@pytest.mark.parametrize("off", ["0", "false", "no", "off"])
def test_keepalive_disabled_by_env(served, seen_payloads, monkeypatch, off):
    from memnet.serve_pool import keepalive_enabled

    server, port = served
    monkeypatch.setenv("MEMNET_SERVE_KEEPALIVE", off)
    assert keepalive_enabled() is False
    for _ in range(3):
        resp = send_command(["--version"], host=HOST, port=port)
        assert resp["exit_code"] == 0, resp
        assert "keep_alive" not in resp
    assert server.accepts == 3
    assert len(seen_payloads) == 3
    assert all("keep_alive" not in p for p in seen_payloads)


def test_keepalive_enabled_by_default(served, seen_payloads):
    from memnet.serve_pool import keepalive_enabled

    _server, port = served
    assert keepalive_enabled() is True
    send_command(["--version"], host=HOST, port=port)
    assert seen_payloads and seen_payloads[-1].get("keep_alive") is True


# (7) A pooled socket idle longer than idle_s is not reused.
def test_pool_idle_socket_not_reused(served):
    from memnet.serve_pool import ServePool

    server, port = served
    pool = ServePool(idle_s=0.2)
    try:
        assert pool.send(HOST, port, {"args": ["--version"]}, 5.0)["exit_code"] == 0
        assert pool.send(HOST, port, {"args": ["--version"]}, 5.0)["exit_code"] == 0
        assert server.accepts == 1
        time.sleep(0.5)
        assert pool.send(HOST, port, {"args": ["--version"]}, 5.0)["exit_code"] == 0
        assert server.accepts == 2
    finally:
        pool.close_all()


# (8) The returned envelope never carries keep_alive.
def test_envelope_has_no_keep_alive_key(served, seen_payloads):
    from memnet.serve_pool import POOL

    _server, port = served
    assert probe(host=HOST, port=port) is True
    replies = [send_command(["--version"], host=HOST, port=port) for _ in range(3)]
    replies.append(POOL.send(HOST, port, {"args": ["--version"]}, 5.0))
    replies.append(send_command(_echo_args("err"), host=HOST, port=port))
    for resp in replies:
        assert "keep_alive" not in resp, resp
    # The wire did ask for keep-alive; the pool stripped the serve's echo.
    assert all(p.get("keep_alive") is True for p in seen_payloads)


# (9) The serve closes an idle kept socket after MEMNET_SERVE_IDLE_S, quietly.
def test_serve_closes_idle_kept_socket(served, monkeypatch, caplog):
    monkeypatch.setenv("MEMNET_SERVE_IDLE_S", "0.3")
    _server, port = served
    caplog.set_level(logging.ERROR, logger="memnet.serve")
    with socket.create_connection((HOST, port), timeout=5) as sock:
        _send_frame(sock, {"args": ["--version"], "keep_alive": True})
        first = _recv_frame(sock)
        assert first is not None and first.get("keep_alive") is True, first
        _send_frame(sock, {"args": _echo_args("second"), "keep_alive": True})
        second = _recv_frame(sock)
        assert second is not None and "second" in second["stderr"], second
        assert second.get("keep_alive") is True
        t0 = time.monotonic()
        assert sock.recv(1) == b""
        waited = time.monotonic() - t0
    assert 0.2 <= waited < 4.0, waited
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
