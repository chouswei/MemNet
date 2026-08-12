"""Local TCP server — holds the in-memory session registry for CLI clients.

Low-level TCP primitives:
- send_command: send argv+stdin to a running memnet serve and return the JSON envelope.
- probe: quick reachability check.
- run_serve: start the TCP server.

Most callers should use memnet.serve_client.dispatch (the canonical public client API)
which handles inline vs TCP routing, probe, and error surfacing.
"""

from __future__ import annotations

import io
import ipaddress
import json
import logging
import os
import socket
import socketserver
import struct
import sys
from typing import Any

from memnet.config import (
    serve_allow_remote,
    serve_host,
    serve_max_frame_bytes,
    serve_port,
)

_LOG = logging.getLogger(__name__)


class ServeBindError(RuntimeError):
    """Non-loopback bind refused without MEMNET_SERVE_ALLOW_REMOTE."""


def is_loopback_bind_host(host: str) -> bool:
    """Return True when host is a loopback literal (127.x, ::1, localhost)."""
    h = host.strip().lower()
    if h == "localhost":
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def validate_serve_bind_host(host: str) -> None:
    """Refuse non-loopback binds unless MEMNET_SERVE_ALLOW_REMOTE is set."""
    if is_loopback_bind_host(host):
        return
    if serve_allow_remote():
        sys.stderr.write(
            f"WARNING: memnet serve binding to non-loopback {host!r} "
            f"(MEMNET_SERVE_ALLOW_REMOTE=1). "
            "No session token or ACL yet — treat as LAN-trust exposure.\n"
        )
        sys.stderr.flush()
        return
    raise ServeBindError(
        f"refusing non-loopback bind {host!r}: set MEMNET_SERVE_ALLOW_REMOTE=1 "
        "to expose memnet serve beyond localhost (no session token/ACL yet)"
    )


def _protocol_envelope(code: str, detail: str) -> dict[str, Any]:
    return {
        "exit_code": 1,
        "stdout": "",
        "stderr": f"@ERR: {code}|{detail}\n",
    }


def _handle_request(payload: dict[str, Any]) -> dict[str, Any]:
    argv = payload.get("args", [])
    if not isinstance(argv, list):
        return {"exit_code": 1, "stdout": "", "stderr": "@ERR: bad_request|args must be a list\n"}
    stdin_text = payload.get("stdin")
    if stdin_text is not None and not isinstance(stdin_text, str):
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": "@ERR: bad_request|stdin must be a string\n",
        }
    os.environ["MEMNET_SERVE_INTERNAL"] = "1"
    from memnet.cli import app

    out = io.StringIO()
    err = io.StringIO()
    old_out, old_err, old_in = sys.stdout, sys.stderr, sys.stdin
    sys.stdout, sys.stderr = out, err
    if stdin_text:
        sys.stdin = io.StringIO(stdin_text)
    code = 0
    try:
        result = app(argv, prog_name="memnet", standalone_mode=False)
        if isinstance(result, int) and result != 0:
            code = result
    except SystemExit as exc:
        code = int(exc.code) if isinstance(exc.code, int) else 1
    except Exception as exc:
        code = 1
        err.write(f"@ERR: internal|{type(exc).__name__}: {exc}\n")
    finally:
        sys.stdout, sys.stderr, sys.stdin = old_out, old_err, old_in
    return {"exit_code": code, "stdout": out.getvalue(), "stderr": err.getvalue()}


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            raw_len = self._read_exact(4)
            if not raw_len:
                return
            (length,) = struct.unpack(">I", raw_len)
            max_frame = serve_max_frame_bytes()
            if length > max_frame:
                self._send_envelope(
                    _protocol_envelope(
                        "frame_too_large",
                        f"request frame {length} bytes exceeds cap {max_frame}",
                    )
                )
                return
            body = self._read_exact(length)
            if body is None:
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                self._send_envelope(_protocol_envelope("bad_frame", str(exc)))
                return
            if not isinstance(payload, dict):
                self._send_envelope(_protocol_envelope("bad_request", "payload must be a JSON object"))
                return
            response = _handle_request(payload)
            self._send_envelope(response)
        except Exception as exc:
            _LOG.exception("memnet serve handler error")
            try:
                self._send_envelope(
                    _protocol_envelope("serve_internal", f"{type(exc).__name__}: {exc}")
                )
            except OSError:
                pass

    def _send_envelope(self, response: dict[str, Any]) -> None:
        data = json.dumps(response).encode("utf-8")
        max_frame = serve_max_frame_bytes()
        if len(data) > max_frame:
            data = json.dumps(
                _protocol_envelope(
                    "response_too_large",
                    f"response {len(data)} bytes exceeds cap {max_frame}",
                )
            ).encode("utf-8")
        self.request.sendall(struct.pack(">I", len(data)) + data)

    def _read_exact(self, n: int) -> bytes | None:
        chunks: list[bytes] = []
        got = 0
        while got < n:
            part = self.request.recv(n - got)
            if not part:
                return None
            chunks.append(part)
            got += len(part)
        return b"".join(chunks)


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_serve(host: str | None = None, port: int | None = None) -> None:
    host = host or serve_host()
    port = port or serve_port()
    validate_serve_bind_host(host)
    os.environ["MEMNET_SERVE_INTERNAL"] = "1"
    # Bind the process-wide durable sync owner once (factory semantics).
    # URL set → AgensGraphAdapter client; else Fake seam — not dual-write.
    try:
        from memnet.durable import get_sync_owner

        owner = get_sync_owner()
        _LOG.info("durable sync owner bound: adapter=%s", owner.adapter_name)
    except Exception:  # noqa: BLE001 — serve must start even if durable bind logs fail
        _LOG.exception("durable sync owner bind skipped")
    with _Server((host, port), _Handler) as server:
        server.serve_forever()


def send_command(
    args: list[str],
    *,
    stdin: str | None = None,
    host: str | None = None,
    port: int | None = None,
) -> dict[str, Any]:
    host = host or serve_host()
    port = port or serve_port()
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
    with socket.create_connection((host, port), timeout=30.0) as sock:
        sock.sendall(frame)
        raw_len = _recv_exact(sock, 4)
        (length,) = struct.unpack(">I", raw_len)
        if length > max_frame:
            raise ConnectionError(
                f"response frame {length} bytes exceeds cap {max_frame}"
            )
        body = _recv_exact(sock, length)
    return json.loads(body.decode("utf-8"))


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


def probe(host: str | None = None, port: int | None = None) -> bool:
    host = host or serve_host()
    port = port or serve_port()
    try:
        with socket.create_connection((host, port), timeout=0.2):
            pass
        return True
    except OSError:
        return False
