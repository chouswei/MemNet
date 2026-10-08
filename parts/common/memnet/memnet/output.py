"""Wire-format stdout/stderr formatters."""

from __future__ import annotations

import io
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, TextIO

from memnet.exceptions import MemNetError
from memnet.models import Record, TagDef, TagMap
from memnet.wire import join_payload

_MAX_WRN = 12
_warn_emitted: ContextVar[int] = ContextVar("memnet_warn_emitted", default=0)


def reset_warn_budget() -> None:
    _warn_emitted.set(0)


def emit_stdout(line: str) -> None:
    sys.stdout.write(line + "\n")


def emit_stderr(line: str) -> None:
    sys.stderr.write(line + "\n")


def format_err(code: str, message: str, example: str | None = None) -> str:
    msg = message.replace("|", " ")
    if example:
        return f"@ERR: {code}|{msg}|{example}"
    return f"@ERR: {code}|{msg}"


def format_wrn(
    code: str,
    message: str,
    example: str | None = None,
    *,
    force: bool = False,
) -> str | None:
    if not force:
        emitted = _warn_emitted.get()
        if emitted >= _MAX_WRN:
            return None
        _warn_emitted.set(emitted + 1)
    msg = message.replace("|", " ")
    if example:
        return f"@WRN: {code}|{msg}|{example}"
    return f"@WRN: {code}|{msg}"


def emit_err(error: MemNetError) -> None:
    emit_stderr(format_err(error.code, error.message, error.example))


def emit_wrn(
    code: str,
    message: str,
    example: str | None = None,
    *,
    force: bool = False,
) -> None:
    line = format_wrn(code, message, example, force=force)
    if line:
        emit_stderr(line)


def emit_session(
    session_id: str,
    field2: str,
    field3: str = "",
    field4: str = "",
) -> None:
    parts = [session_id, field2]
    if field3:
        parts.append(field3)
    if field4:
        parts.append(field4)
    emit_stdout(f"@SESSION: {'|'.join(parts)}")


def emit_record_line(tag: str, values: list[str]) -> str:
    payload = join_payload(values)
    return f"@{tag}: {payload}"


def emit_record(record: Record, tag_map: TagMap) -> str:
    tag_def = tag_map.get(record.tag)
    if not tag_def:
        values = [record.fields.get("id", "")]
        values.extend(v for k, v in record.fields.items() if k != "id")
        return emit_record_line(record.tag, values)
    values = [record.fields.get(f, "") for f in tag_def.fields]
    return emit_record_line(record.tag, values)


def parse_err_line(line: str) -> tuple[str, str, str | None]:
    if not line.startswith("@ERR: "):
        raise ValueError("not an ERR line")
    rest = line[6:]
    parts = rest.split("|", 2)
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], None
    return parts[0], "", None


def values_from_record(record: Record, tag_def: TagDef) -> list[str]:
    return [record.fields.get(f, "") for f in tag_def.fields]


# Per-request stdio. A process-global swap of sys.stdout races on a threaded
# serve (MN-REQ-06.13). The proxy stays installed only while at least one
# capture is active; each request's buffers live on contextvars.
_stdout_buf: ContextVar[io.StringIO | None] = ContextVar("memnet_stdout_buf", default=None)
_stderr_buf: ContextVar[io.StringIO | None] = ContextVar("memnet_stderr_buf", default=None)
_stdin_buf: ContextVar[io.StringIO | None] = ContextVar("memnet_stdin_buf", default=None)
_capture_guard = threading.Lock()
_capture_depth = 0
_saved_stdio: tuple[TextIO, TextIO, TextIO] | None = None
_fallback_out: list[TextIO] = [sys.stdout]
_fallback_err: list[TextIO] = [sys.stderr]
_fallback_in: list[TextIO] = [sys.stdin]


class _TextAsBuffer:
    """Bytes view of a text stdin so ``sys.stdin.buffer.read`` stays in-request."""

    def __init__(self, textio: TextIO) -> None:
        self._textio = textio

    def read(self, n: int = -1) -> bytes:
        text = self._textio.read() if n < 0 else self._textio.read(n)
        return text.encode("utf-8")

    def readline(self, n: int = -1) -> bytes:
        text = self._textio.readline() if n < 0 else self._textio.readline(n)
        return text.encode("utf-8")


class _RoutingStream:
    def __init__(self, var: ContextVar[io.StringIO | None], fallback: list[TextIO]) -> None:
        self._var = var
        self._fallback = fallback

    def _target(self) -> TextIO:
        buf = self._var.get()
        if buf is not None:
            return buf
        return self._fallback[0]

    def write(self, s: str) -> int:
        return self._target().write(s)

    def flush(self) -> None:
        flush = getattr(self._target(), "flush", None)
        if flush:
            flush()

    def isatty(self) -> bool:
        fn = getattr(self._target(), "isatty", None)
        return bool(fn()) if fn else False

    def read(self, n: int = -1) -> str:
        return self._target().read(n)

    def readline(self, n: int = -1) -> str:
        return self._target().readline(n)

    def readlines(self, hint: int = -1) -> list[str]:
        return self._target().readlines(hint)

    def __iter__(self) -> Iterator[str]:
        return iter(self._target())

    @property
    def encoding(self) -> str:
        return getattr(self._target(), "encoding", None) or "utf-8"

    @property
    def errors(self) -> str | None:
        return getattr(self._target(), "errors", None)

    @property
    def buffer(self) -> Any:
        target = self._target()
        buf = getattr(target, "buffer", None)
        if buf is not None:
            return buf
        return _TextAsBuffer(target)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target(), name)


_OUT_PROXY = _RoutingStream(_stdout_buf, _fallback_out)
_ERR_PROXY = _RoutingStream(_stderr_buf, _fallback_err)
_IN_PROXY = _RoutingStream(_stdin_buf, _fallback_in)


def _enter_capture() -> None:
    global _capture_depth, _saved_stdio
    with _capture_guard:
        if _capture_depth == 0:
            _saved_stdio = (sys.stdout, sys.stderr, sys.stdin)
            _fallback_out[0] = sys.stdout
            _fallback_err[0] = sys.stderr
            _fallback_in[0] = sys.stdin
            sys.stdout = _OUT_PROXY
            sys.stderr = _ERR_PROXY
            sys.stdin = _IN_PROXY
        _capture_depth += 1


def _leave_capture() -> None:
    global _capture_depth, _saved_stdio
    with _capture_guard:
        _capture_depth -= 1
        if _capture_depth == 0 and _saved_stdio is not None:
            sys.stdout, sys.stderr, sys.stdin = _saved_stdio
            _saved_stdio = None


@contextmanager
def capture_request_stdio(
    stdin_text: str | None = None,
) -> Iterator[tuple[io.StringIO, io.StringIO]]:
    """Bind this context's stdout, stderr, and stdin for one serve command.

    Overlapping requests do not share buffers. The proxy is process-global
    only as a router; the bytes live on contextvars, so a threaded serve
    does not need a serve-wide lock.
    """
    out = io.StringIO()
    err = io.StringIO()
    inp = io.StringIO(stdin_text or "")
    _enter_capture()
    tok_out = _stdout_buf.set(out)
    tok_err = _stderr_buf.set(err)
    tok_in = _stdin_buf.set(inp)
    try:
        yield out, err
    finally:
        _stdout_buf.reset(tok_out)
        _stderr_buf.reset(tok_err)
        _stdin_buf.reset(tok_in)
        _leave_capture()
