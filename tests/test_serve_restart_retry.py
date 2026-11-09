"""Restart-safe serve client (MN-REQ-06.19, MN-VER-06-S17): pause, never replay a write.

A scripted fake serve on a real loopback socket speaks the serve frame wire. A fake clock
makes the retry budget exact without real sleeps.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from memnet import __version__
from memnet.serve_pool import ServePool
from memnet.serve_retry import RequestKind, argv_kind, draining_retry_after, request_kind

HOST = "127.0.0.1"
OK = {"exit_code": 0, "stdout": "@STAT: ok|1\n", "stderr": ""}
DRAINING = {"exit_code": 2, "stdout": "", "stderr": "@ERR: serve_draining|retry_after_s=5\n"}
READ_ARGS = ["query", "find", "--kind", "TSK", "--session", "mn_x"]
WRITE_ARGS = ["mutate", "--stdin", "--session", "mn_x"]

# One reply per accepted connection: a dict is sent back, "drop" reads the whole frame
# and then resets the connection without a reply (the serve may have run it); "huge"
# announces a reply frame over the cap.
Step = dict[str, Any] | str


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        part = sock.recv(n - len(buf))
        if not part:
            raise ConnectionError("closed")
        buf += part
    return buf


class FakeServe:
    """Loopback listener that follows a script, one step per connection, and logs requests."""

    def __init__(self, port: int, script: list[Step], *, default: Step | None = None) -> None:
        self.port = port
        self.script = list(script)
        self.default = default
        self.delivered: list[dict[str, Any]] = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((HOST, port))
        self._sock.listen(8)
        self._sock.settimeout(0.05)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _next(self) -> Step | None:
        if self.script:
            return self.script.pop(0)
        return self.default

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            conn.settimeout(5)
            with conn:
                try:
                    (length,) = struct.unpack(">I", _recv_exact(conn, 4))
                    request = json.loads(_recv_exact(conn, length).decode("utf-8"))
                except (OSError, ValueError):
                    continue
                self.delivered.append(request)
                step = self._next()
                if step == "huge":
                    conn.sendall(struct.pack(">I", 2**31))
                    continue
                if step is None or step == "drop":
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                    continue
                body = json.dumps(step).encode("utf-8")
                conn.sendall(struct.pack(">I", len(body)) + body)

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        self._sock.close()


class FakeClock:
    """Monotonic clock that only moves when the pool sleeps; runs a hook on each sleep."""

    def __init__(self, on_sleep: Callable[[int], None] | None = None) -> None:
        self.now = 1000.0
        self.slept: list[float] = []
        self._on_sleep = on_sleep

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds
        if self._on_sleep is not None:
            self._on_sleep(len(self.slept))


@pytest.fixture(autouse=True)
def _one_shot(monkeypatch: pytest.MonkeyPatch) -> None:
    # One request per connection, so every attempt is a fresh connect.
    monkeypatch.setenv("MEMNET_SERVE_KEEPALIVE", "0")
    monkeypatch.delenv("MEMNET_SERVE_RETRY_S", raising=False)


def _pool(clock: FakeClock) -> ServePool:
    return ServePool(sleep=clock.sleep, clock=clock.clock)


@pytest.mark.parametrize("args", [READ_ARGS, WRITE_ARGS], ids=["read", "write"])
def test_connect_refused_then_accept_succeeds_for_read_and_write(args):
    port = _free_port()
    serves: list[FakeServe] = []

    def come_up(n: int) -> None:
        if n == 3:  # the serve is back after the third backoff
            serves.append(FakeServe(port, [OK]))

    clock = FakeClock(come_up)
    try:
        reply = _pool(clock).send(HOST, port, {"args": args}, timeout=5)
        assert reply == OK
        assert len(clock.slept) == 3
        assert sum(clock.slept) < 30
        assert [r["args"] for r in serves[0].delivered] == [args]
    finally:
        for serve in serves:
            serve.close()


@pytest.mark.parametrize("args", [READ_ARGS, WRITE_ARGS], ids=["read", "write"])
def test_draining_envelope_honours_retry_after_then_succeeds(args):
    port = _free_port()
    serve = FakeServe(port, [DRAINING, OK])
    clock = FakeClock()
    try:
        reply = _pool(clock).send(HOST, port, {"args": args}, timeout=5)
        assert reply == OK
        assert clock.slept and clock.slept[0] >= 5
        assert len(serve.delivered) == 2  # refused before any work, then run once
    finally:
        serve.close()


def test_reset_after_send_on_write_is_not_retried():
    port = _free_port()
    serve = FakeServe(port, ["drop"], default=OK)
    clock = FakeClock()
    try:
        with pytest.raises(OSError):
            _pool(clock).send(HOST, port, {"args": WRITE_ARGS, "stdin": "CREATE (:TSK)\n"}, 5)
        assert len(serve.delivered) == 1
        assert clock.slept == []
    finally:
        serve.close()


def test_reset_after_send_on_read_is_retried_and_succeeds():
    port = _free_port()
    serve = FakeServe(port, ["drop", OK])
    clock = FakeClock()
    try:
        reply = _pool(clock).send(HOST, port, {"args": READ_ARGS}, timeout=5)
        assert reply == OK
        assert len(serve.delivered) == 2
        assert len(clock.slept) == 1
    finally:
        serve.close()


def test_oversized_reply_on_read_is_not_retried():
    port = _free_port()
    serve = FakeServe(port, ["huge"], default=OK)
    clock = FakeClock()
    try:
        with pytest.raises(ConnectionError, match="exceeds cap"):
            _pool(clock).send(HOST, port, {"args": READ_ARGS}, timeout=5)
        assert len(serve.delivered) == 1
        assert clock.slept == []
    finally:
        serve.close()


def test_budget_is_bounded_then_the_connect_error_surfaces():
    port = _free_port()  # nothing ever listens
    clock = FakeClock()
    with pytest.raises(ConnectionRefusedError):
        _pool(clock).send(HOST, port, {"args": READ_ARGS}, timeout=5)
    assert sum(clock.slept) == pytest.approx(30)  # the last wait is clamped to the budget
    assert max(clock.slept) <= 2.0  # backoff cap


def test_draining_past_the_budget_returns_the_refusal():
    port = _free_port()
    serve = FakeServe(port, [], default=DRAINING)
    clock = FakeClock()
    try:
        reply = _pool(clock).send(HOST, port, {"args": WRITE_ARGS}, timeout=5, retry_s=12)
        assert draining_retry_after(reply) == 5
        assert sum(clock.slept) == pytest.approx(12)
    finally:
        serve.close()


def test_retry_off_by_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMNET_SERVE_RETRY_S", "0")
    clock = FakeClock()
    with pytest.raises(ConnectionRefusedError):
        _pool(clock).send(HOST, _free_port(), {"args": READ_ARGS}, timeout=5)
    assert clock.slept == []


@pytest.mark.parametrize(
    "argv",
    [
        ["version"],
        ["query", "pin-map", "--cue", "TSK_a", "--session", "s"],
        ["query", "find", "--kind", "TSK"],
        ["query", "typed-walk", "--start", "x"],
        ["query", "walk"],
        ["read", "list"],
        ["housekeep", "stats"],
        ["session", "current"],
        ["session", "list"],
        ["session", "expire-status"],
        ["export", "pin-map", "--cue", "TSK_a"],
        ["admin", "usage-report"],
    ],
)
def test_read_verbs(argv):
    assert argv_kind(argv) is RequestKind.READ


@pytest.mark.parametrize(
    "argv",
    [
        ["mutate", "--stdin"],
        ["add", "TSK"],
        ["update", "TSK_a"],
        ["delete", "TSK_a"],
        ["import-slice"],
        ["session", "open", "--map-file", "m"],
        ["session", "save", "--file", "f"],
        ["session", "load", "--file", "f"],
        ["session", "close", "s"],
        ["session", "acl-enable"],
        ["session", "acl-grant"],
        ["session", "acl-bind"],
        ["reserve"],
        ["extend"],
        ["release"],
        ["ingest", "sysml", "x.sysml"],
        ["snap", "model", "x"],
        ["housekeep", "prune", "stale"],
        ["export", "pin-map", "--cue", "TSK_a", "--out", "f.gql"],
        ["export", "pin-map", "--out=f.gql"],
        ["admin", "checkpoint"],
        ["admin", "upgrade-prepare"],
        ["no-such-verb"],
        [],
    ],
)
def test_write_verbs_and_unknown_fail_closed(argv):
    assert argv_kind(argv) is RequestKind.WRITE


def test_request_kind_admin_flags():
    assert request_kind({"args": [], "admin_usage": True}) is RequestKind.READ
    assert request_kind({"args": ["version"], "upgrade_prepare": True}) is RequestKind.WRITE


def test_gateway_pauses_through_backend_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Gateway owned call: the backend restarts between calls; the caller pauses, then works."""
    from memnet_mcp.product_gateway import ProductGateway
    from test_product_gateway import ENDLEAF, _config

    monkeypatch.setenv("MEMNET_SERVE_RETRY_S", "10")
    version = {"exit_code": 0, "stdout": f"@VER: memnet|{__version__}\n", "stderr": ""}
    opened = {"exit_code": 0, "stdout": "@SESSION: mn_gw1|soon|60\n", "stderr": ""}
    port_a, port_b = _free_port(), _free_port()
    cfg, state = tmp_path / "gw.json", tmp_path / "owners.json"
    _config(cfg, state, port_a, port_b)
    gw = ProductGateway.load(str(cfg))

    def call(args: list[str], **extra: Any):
        body = {"args": args, **extra}
        return gw.handle(
            method="POST",
            path="/gateway",
            authorization=f"Bearer {ENDLEAF}",
            body=json.dumps(body).encode(),
        )

    # Backend a is down when the open arrives and comes up 0.3 s later.
    late: list[FakeServe] = []
    timer = threading.Timer(0.3, lambda: late.append(FakeServe(port_a, [version, opened])))
    timer.start()
    try:
        first = call(["session", "open", "--map-file", "m.txt"], house="syson")
        assert first.exit_code == 0, first.stderr
        assert "mn_gw1" in first.stdout
    finally:
        timer.join()
        for serve in late:
            serve.close()

    # Restart: down now, back 0.3 s later. The write is delivered exactly once.
    back: list[FakeServe] = []
    timer = threading.Timer(0.3, lambda: back.append(FakeServe(port_a, [version, OK])))
    timer.start()
    try:
        second = call(WRITE_ARGS[:-1] + ["mn_gw1"], session="mn_gw1", stdin="CREATE (:TSK)\n")
        assert second.exit_code == 0, second.stderr
        assert [r["args"][0] for r in back[0].delivered] == ["version", "mutate"]
    finally:
        timer.join()
        for serve in back:
            serve.close()


def test_gateway_placement_fails_over_past_a_dead_backend_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Unpinned open: backend a stays down, b is up. Placement skips a without the pause."""
    import time

    from memnet_mcp.product_gateway import ProductGateway
    from test_product_gateway import ENDLEAF, _config

    monkeypatch.setenv("MEMNET_SERVE_RETRY_S", "30")
    version = {"exit_code": 0, "stdout": f"@VER: memnet|{__version__}\n", "stderr": ""}
    opened = {"exit_code": 0, "stdout": "@SESSION: mn_gw2|soon|60\n", "stderr": ""}
    port_a, port_b = _free_port(), _free_port()
    cfg, state = tmp_path / "gw.json", tmp_path / "owners.json"
    _config(cfg, state, port_a, port_b)
    gw = ProductGateway.load(str(cfg))
    live = FakeServe(port_b, [version, opened])
    try:
        start = time.monotonic()
        resp = gw.handle(
            method="POST",
            path="/gateway",
            authorization=f"Bearer {ENDLEAF}",
            body=json.dumps({"args": ["session", "open", "--map-file", "m.txt"]}).encode(),
        )
        elapsed = time.monotonic() - start
    finally:
        live.close()
    assert resp.exit_code == 0, resp.stderr
    assert "mn_gw2" in resp.stdout
    assert [r["args"][0] for r in live.delivered] == ["version", "session"]
    assert elapsed < 2.0, f"placement paused {elapsed:.1f}s on the dead backend"
