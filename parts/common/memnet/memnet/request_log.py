"""Per-request engine log for ``memnet serve`` (TCP and AF_UNIX share one handler).

One JSON line per request, written after the reply is sent. Off unless a path is
set (``--request-log PATH`` or ``MEMNET_REQUEST_LOG``). Never carries payload text,
tokens or session ids: the session is a short one-way label, not the id.
"""

from __future__ import annotations

import contextvars
import hashlib
import itertools
import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from typing import Any

from memnet.config import request_log_backups, request_log_max_bytes, request_log_path

_LOG = logging.getLogger(__name__)

_OP_WORD = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_ERR = re.compile(r"@ERR:\s*([A-Za-z0-9_.-]{1,48})")
_conn_counter = itertools.count(1)
_conn_lock = threading.Lock()


def next_conn_id() -> int:
    with _conn_lock:
        return next(_conn_counter)


def session_label(session_id: str | None) -> str | None:
    """Short one-way label (``s_`` + 8 hex); the engine has no session names, only ids."""
    if not session_id:
        return None
    return "s_" + hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:8]


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


@dataclass
class RequestTrace:
    conn_id: int
    seq: int = 1
    received_ms: int = 0
    t_recv: float = 0.0
    t_work: float | None = None
    t_done: float = 0.0
    finished_ms: int = 0
    op: str | None = None
    session: str | None = None
    bytes_in: int = 0
    bytes_out: int = 0
    lines_in: int = 0
    lines_out: int = 0
    nodes_touched: int | None = None
    outcome: str = "ok"
    skip: bool = False


_current: contextvars.ContextVar[RequestTrace | None] = contextvars.ContextVar(
    "memnet_request_trace", default=None
)


def begin(conn_id: int) -> RequestTrace:
    trace = RequestTrace(conn_id=conn_id)
    trace.received_ms = _now_ms()
    trace.t_recv = time.perf_counter()
    _current.set(trace)
    return trace


def mark_received(trace: RequestTrace, body_bytes: int) -> None:
    """Frame fully read: the clock for queue wait starts here."""
    trace.bytes_in = body_bytes
    trace.received_ms = _now_ms()
    trace.t_recv = time.perf_counter()


def mark_work_start() -> None:
    """Called by the dispatch just before the command runs (after any gate or wait)."""
    trace = _current.get()
    if trace is not None and trace.t_work is None:
        trace.t_work = time.perf_counter()


def mark_lock_acquired() -> None:
    """Session lock taken: lock wait counts as queue wait, so restart the work clock."""
    trace = _current.get()
    if trace is not None:
        trace.t_work = time.perf_counter()


def describe_payload(trace: RequestTrace, payload: dict[str, Any]) -> None:
    """Fill op, session label and lines_in. Never keeps argument or stdin text."""
    for flag, name in (
        ("admin_usage", "admin_usage"),
        ("upgrade_prepare", "upgrade_prepare"),
        ("checkpoint", "checkpoint"),
    ):
        if payload.get(flag) is True:
            trace.op = name
            return
    argv = payload.get("args")
    if not isinstance(argv, list):
        return
    words = [a for a in argv if isinstance(a, str)]
    if words and _OP_WORD.match(words[0]):
        op = words[0]
        if words[0] in _group_names() and len(words) > 1 and _OP_WORD.match(words[1]):
            op = f"{words[0]} {words[1]}"
        trace.op = op
    sid: str | None = None
    for i, a in enumerate(words):
        if a == "--session" and i + 1 < len(words):
            sid = words[i + 1]
            break
        if a.startswith("--session="):
            sid = a.split("=", 1)[1]
            break
    trace.session = session_label(sid)
    stdin = payload.get("stdin")
    if isinstance(stdin, str) and stdin:
        trace.lines_in = stdin.count("\n") + (0 if stdin.endswith("\n") else 1)


_groups: frozenset[str] | None = None


def _group_names() -> frozenset[str]:
    """Names of CLI sub-apps (their second word is a subcommand, not user text)."""
    global _groups
    if _groups is None:
        try:
            import typer.main

            from memnet.cli import app

            cmd = typer.main.get_command(app)
            _groups = frozenset(
                n for n, c in getattr(cmd, "commands", {}).items() if hasattr(c, "commands")
            )
        except Exception:  # noqa: BLE001 — logging must not break a request
            _groups = frozenset()
    return _groups


def describe_response(trace: RequestTrace, response: dict[str, Any] | None) -> None:
    if response is None:
        trace.outcome = "peer_gone"
        return
    stdout = response.get("stdout")
    if isinstance(stdout, str) and stdout:
        trace.lines_out = stdout.count("\n") + (0 if stdout.endswith("\n") else 1)
    code = response.get("exit_code")
    if code in (0, None):
        trace.outcome = "ok"
        return
    m = _ERR.search(str(response.get("stderr", "")))
    trace.outcome = m.group(1) if m else "error"


def to_line(trace: RequestTrace) -> str:
    done = trace.t_done or time.perf_counter()
    work = trace.t_work if trace.t_work is not None else trace.t_recv
    rec = {
        "received_ms": trace.received_ms,
        "finished_ms": trace.finished_ms,
        "queue_wait_ms": round(max(0.0, work - trace.t_recv) * 1000, 1),
        "server_ms": round(max(0.0, done - work) * 1000, 1),
        "op": trace.op,
        "session": trace.session,
        "bytes_in": trace.bytes_in,
        "bytes_out": trace.bytes_out,
        "lines_in": trace.lines_in,
        "lines_out": trace.lines_out,
        "nodes_touched": trace.nodes_touched,
        "outcome": trace.outcome,
        "conn_id": trace.conn_id,
        "seq": trace.seq,
    }
    return json.dumps(rec, separators=(",", ":"))


class _Sink:
    def __init__(self, path: str, max_bytes: int, backups: int) -> None:
        self.path = path
        self._warned = False
        self._handler: RotatingFileHandler | None = None
        try:
            handler = RotatingFileHandler(
                path, maxBytes=max_bytes, backupCount=max(1, backups), encoding="utf-8", delay=True
            )
            handler.handleError = self._on_error  # type: ignore[method-assign]
            self._handler = handler
        except Exception as exc:  # noqa: BLE001
            self._warn(exc)

    def _warn(self, exc: BaseException) -> None:
        if not self._warned:
            self._warned = True
            _LOG.warning("request log disabled for errors: %s: %s", type(exc).__name__, exc)

    def _on_error(self, record: logging.LogRecord) -> None:
        import sys

        self._warn(sys.exc_info()[1] or RuntimeError("request log write failed"))

    def close(self) -> None:
        try:
            if self._handler is not None:
                self._handler.close()
        except Exception:  # noqa: BLE001
            pass

    def write(self, line: str) -> None:
        handler = self._handler
        if handler is None:
            return
        record = logging.LogRecord("memnet.request_log", logging.INFO, "", 0, line, None, None)
        handler.handle(record)


_sink: _Sink | None = None
_sink_key: tuple[str, int, int] | None = None
_sink_lock = threading.Lock()


def _get_sink() -> _Sink | None:
    global _sink, _sink_key
    path = request_log_path()
    if not path:
        return None
    key = (path, request_log_max_bytes(), request_log_backups())
    with _sink_lock:
        if _sink_key != key:
            if _sink is not None:
                _sink.close()
            _sink = _Sink(*key)
            _sink_key = key
        return _sink


def finish(trace: RequestTrace) -> None:
    """Emit the line. Swallows every error: a log must never fail a request."""
    try:
        sink = _get_sink()
        if sink is None or trace.skip:
            return
        trace.t_done = time.perf_counter()
        trace.finished_ms = _now_ms()
        sink.write(to_line(trace))
    except Exception as exc:  # noqa: BLE001
        _LOG.debug("request log skipped: %s", type(exc).__name__)
    finally:
        _current.set(None)
