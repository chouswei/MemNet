"""LocalIpcGateway — AF_UNIX share of session registry (MN-REQ-06.2).

Same length-prefixed JSON protocol as TcpServeBridge / ``memnet serve``, on a
local socket so two processes on one host need no TCP port. Shares the
in-process GraphStore + session registry (GQL pin_map, gated mutate, ACL).

Env: ``MEMNET_IPC_SOCKET`` — absolute or relative path to the Unix domain socket.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import socketserver
import struct
from pathlib import Path
from typing import Any

from memnet.config import (
    default_ipc_socket_path,
    ipc_socket_path,
    serve_max_frame_bytes,
)
from memnet.serve import _Handler, _protocol_envelope, _recv_exact

_LOG = logging.getLogger(__name__)

IMPLEMENTED = True

__all__ = [
    "IMPLEMENTED",
    "LocalIpcGateway",
    "LocalIpcError",
    "probe",
    "run_ipc_serve",
    "send_command",
    "resolve_ipc_path",
]


class LocalIpcError(RuntimeError):
    """Local IPC bind / platform failure."""


def resolve_ipc_path(path: str | None = None) -> str:
    """Resolve socket path: explicit arg, else ``MEMNET_IPC_SOCKET``, else default."""
    if path and path.strip():
        return path.strip()
    env = ipc_socket_path()
    if env:
        return env
    return default_ipc_socket_path()


def _require_af_unix() -> None:
    if not hasattr(socket, "AF_UNIX"):
        raise LocalIpcError(
            "AF_UNIX not available on this platform; use TcpServeBridge "
            "(memnet serve) or InProcessEngine"
        )


class _UnixServer(socketserver.ThreadingUnixStreamServer):
    allow_reuse_address = True
    daemon_threads = True


def run_ipc_serve(path: str | None = None) -> None:
    """Listen on AF_UNIX; same request handler as TCP ``memnet serve``."""
    _require_af_unix()
    sock_path = resolve_ipc_path(path)
    os.environ["MEMNET_IPC_SOCKET"] = sock_path
    os.environ["MEMNET_SERVE_INTERNAL"] = "1"
    try:
        from memnet.durable import get_sync_owner

        owner = get_sync_owner()
        _LOG.info("durable sync owner bound: adapter=%s", owner.adapter_name)
    except Exception:  # noqa: BLE001 — serve must start even if durable bind logs fail
        _LOG.exception("durable sync owner bind skipped")

    path_obj = Path(sock_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    if path_obj.exists():
        try:
            path_obj.unlink()
        except OSError as exc:
            raise LocalIpcError(f"cannot remove stale socket {sock_path}: {exc}") from exc

    server = _UnixServer(sock_path, _Handler)
    try:
        with server:
            server.serve_forever()
    finally:
        try:
            if path_obj.exists():
                path_obj.unlink()
        except OSError:
            pass


def send_command(
    args: list[str],
    *,
    stdin: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Send argv+stdin over AF_UNIX; return the JSON envelope (same as TCP)."""
    _require_af_unix()
    sock_path = resolve_ipc_path(path)
    payload_obj: dict[str, Any] = {"args": args}
    if stdin is not None:
        payload_obj["stdin"] = stdin
    payload = json.dumps(payload_obj).encode("utf-8")
    max_frame = serve_max_frame_bytes()
    if len(payload) + 4 > max_frame:
        return _protocol_envelope(
            "frame_too_large",
            f"request payload {len(payload)} bytes exceeds cap {max_frame}",
        )
    frame = struct.pack(">I", len(payload)) + payload
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(30.0)
        sock.connect(sock_path)
        sock.sendall(frame)
        raw_len = _recv_exact(sock, 4)
        (length,) = struct.unpack(">I", raw_len)
        if length > max_frame:
            raise ConnectionError(f"response frame {length} bytes exceeds cap {max_frame}")
        body = _recv_exact(sock, length)
    return json.loads(body.decode("utf-8"))


def probe(path: str | None = None) -> bool:
    """Return True when the LocalIpcGateway socket accepts a connection."""
    if not hasattr(socket, "AF_UNIX"):
        return False
    sock_path = path.strip() if path and path.strip() else ipc_socket_path()
    if not sock_path:
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            sock.connect(sock_path)
        return True
    except OSError:
        return False


class LocalIpcGateway:
    """Named AF_UNIX share of session registry (MN-REQ-06.2 LocalIpcShare)."""

    implemented = True

    def __init__(self, path: str | None = None) -> None:
        _require_af_unix()
        self.path = resolve_ipc_path(path)

    def run(self, path: str | None = None) -> None:
        run_ipc_serve(path or self.path)

    def send(self, argv: list[str], *, stdin: str | None = None) -> dict[str, Any]:
        return send_command(argv, stdin=stdin, path=self.path)

    def probe(self) -> bool:
        return probe(self.path)
