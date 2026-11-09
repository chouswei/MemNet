"""Client-side keep-alive socket pool for ``memnet serve`` (passthru-keepalive)."""

from __future__ import annotations

import json
import os
import random
import select
import socket
import struct
import threading
import time
from collections.abc import Callable
from typing import Any

from memnet.config import serve_max_frame_bytes
from memnet.serve_retry import (
    RequestKind,
    backoff_s,
    draining_retry_after,
    request_kind,
    retry_budget_s,
)

_OFF_VALUES = frozenset({"0", "false", "no", "off"})
_TIMEOUT_ENVELOPE: dict[str, Any] = {
    "exit_code": 1,
    "stdout": "",
    "stderr": "@ERR: serve_timeout|wait exceeded\n",
}


def keepalive_enabled() -> bool:
    return os.environ.get("MEMNET_SERVE_KEEPALIVE", "").strip().lower() not in _OFF_VALUES


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


def _peer_closed(sock: socket.socket) -> bool:
    try:
        ready, _, _ = select.select([sock], [], [], 0)
        if not ready:
            return False
        return sock.recv(1, socket.MSG_PEEK) == b""
    except BlockingIOError:
        return False
    except (OSError, ValueError):
        return True


def _close(sock: socket.socket) -> None:
    try:
        sock.close()
    except OSError:
        pass


class _NotDelivered(Exception):
    """The serve cannot have read the request (connect failed or frame not fully sent)."""

    def __init__(self, cause: OSError) -> None:
        super().__init__(str(cause))
        self.cause = cause


class _ReplyTooLarge(ConnectionError):
    """The reply frame is over the cap: deterministic, so never retried."""


class ServePool:
    """Idle sockets per (host, port), LIFO; each socket is checked out exclusively."""

    def __init__(
        self,
        idle_s: float = 30.0,
        *,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
    ) -> None:
        self._idle_s = idle_s
        self._sleep = sleep
        self._clock = clock
        self._rng = rng
        self._lock = threading.Lock()
        self._idle: dict[tuple[str, int], list[tuple[socket.socket, float]]] = {}
        self._pid = os.getpid()

    def _drop_if_forked(self) -> None:
        # Caller holds the lock. A forked child must not share the parent's sockets.
        pid = os.getpid()
        if pid != self._pid:
            self._pid = pid
            for entries in self._idle.values():
                for sock, _ in entries:
                    _close(sock)
            self._idle.clear()

    def _checkout(self, key: tuple[str, int]) -> socket.socket | None:
        """Pop the newest reusable idle socket for ``key`` (discarding stale ones)."""
        while True:
            with self._lock:
                self._drop_if_forked()
                entries = self._idle.get(key)
                if not entries:
                    return None
                sock, parked = entries.pop()
            if time.monotonic() - parked < self._idle_s and not _peer_closed(sock):
                return sock
            _close(sock)

    def _park(self, key: tuple[str, int], sock: socket.socket) -> None:
        with self._lock:
            self._drop_if_forked()
            self._idle.setdefault(key, []).append((sock, time.monotonic()))

    def _has_reusable(self, key: tuple[str, int]) -> bool:
        sock = self._checkout(key)
        if sock is None:
            return False
        self._park_back(key, sock)
        return True

    def _park_back(self, key: tuple[str, int], sock: socket.socket) -> None:
        # Keep the original idle age out of play: a socket just validated is fresh enough.
        self._park(key, sock)

    def probe(self, host: str, port: int, timeout: float = 0.2) -> bool:
        key = (host, port)
        if self._has_reusable(key):
            return True
        try:
            sock = socket.create_connection(key, timeout=timeout)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            return False
        self._park(key, sock)
        return True

    def send(
        self,
        host: str,
        port: int,
        payload: dict,
        timeout: float,
        *,
        retry_s: float | None = None,
    ) -> dict:
        """One serve request. Pauses through a restart or drain (MN-REQ-06.19).

        Retries within ``retry_s`` (default ``MEMNET_SERVE_RETRY_S``) when the
        request was not delivered or the serve answered serve_draining. A reset
        after the frame was written is retried for READ requests only.
        """
        keep = keepalive_enabled()
        body_obj = dict(payload)
        if keep:
            body_obj["keep_alive"] = True
        data = json.dumps(body_obj).encode("utf-8")
        max_frame = serve_max_frame_bytes()
        if len(data) + 4 > max_frame:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"@ERR: frame_too_large|request payload {len(data)} bytes "
                f"exceeds cap {max_frame}\n",
            }
        frame = struct.pack(">I", len(data)) + data
        key = (host, port)
        budget = retry_budget_s() if retry_s is None else max(0.0, retry_s)
        deadline = self._clock() + budget
        attempt = 0
        while True:
            failure: OSError | None = None
            reply: dict | None = None
            try:
                reply = self._send_once(key, frame, timeout, keep, max_frame)
            except _NotDelivered as exc:
                failure = exc.cause
                wait = backoff_s(attempt, self._rng)
            except OSError as exc:
                if isinstance(exc, _ReplyTooLarge) or request_kind(payload) is not RequestKind.READ:
                    raise
                failure = exc
                wait = backoff_s(attempt, self._rng)
            else:
                retry_after = draining_retry_after(reply)
                if retry_after is None:
                    return reply
                wait = max(retry_after, backoff_s(attempt, self._rng))
            remaining = deadline - self._clock()
            if remaining <= 0:
                if failure is not None:
                    raise failure
                return reply  # type: ignore[return-value]
            self._sleep(min(wait, remaining))
            attempt += 1

    def _send_once(
        self,
        key: tuple[str, int],
        frame: bytes,
        timeout: float,
        keep: bool,
        max_frame: int,
    ) -> dict:
        """One attempt. Raises ``_NotDelivered`` when the serve cannot have read the frame."""
        sock: socket.socket | None = self._checkout(key) if keep else None
        try:
            if sock is not None:
                try:
                    sock.settimeout(timeout)
                    sock.sendall(frame)
                except TimeoutError:
                    raise
                except OSError:
                    _close(sock)
                    sock = None
            if sock is None:
                try:
                    sock = socket.create_connection(key, timeout=timeout)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    sock.sendall(frame)
                except TimeoutError:
                    raise
                except OSError as exc:
                    # Refused, reset, or the frame was not fully written: the serve acts
                    # only on a whole length-prefixed frame, so it did not run this one.
                    raise _NotDelivered(exc) from exc
            (length,) = struct.unpack(">I", _recv_exact(sock, 4))
            if length > max_frame:
                raise _ReplyTooLarge(f"response frame {length} bytes exceeds cap {max_frame}")
            reply = json.loads(_recv_exact(sock, length).decode("utf-8"))
        except TimeoutError:
            if sock is not None:
                _close(sock)
            return dict(_TIMEOUT_ENVELOPE)
        except BaseException:
            if sock is not None:
                _close(sock)
            raise
        if isinstance(reply, dict) and reply.pop("keep_alive", None) is True and keep:
            self._park(key, sock)
        else:
            _close(sock)
        return reply

    def close_all(self) -> None:
        with self._lock:
            entries = [s for lst in self._idle.values() for s, _ in lst]
            self._idle.clear()
        for sock in entries:
            _close(sock)


POOL = ServePool()
