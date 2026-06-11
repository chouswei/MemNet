"""Local TCP server — holds the in-memory session registry for CLI clients."""

from __future__ import annotations

import io
import json
import os
import socket
import socketserver
import struct
import sys
from typing import Any

from memnet.config import serve_host, serve_port


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
        app(argv, prog_name="memnet", standalone_mode=False)
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
            body = self._read_exact(length)
            if body is None:
                return
            payload = json.loads(body.decode("utf-8"))
            response = _handle_request(payload)
            data = json.dumps(response).encode("utf-8")
            self.request.sendall(struct.pack(">I", len(data)) + data)
        except Exception:
            return

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
    os.environ["MEMNET_SERVE_INTERNAL"] = "1"
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
    frame = struct.pack(">I", len(payload)) + payload
    with socket.create_connection((host, port), timeout=30.0) as sock:
        sock.sendall(frame)
        raw_len = _recv_exact(sock, 4)
        (length,) = struct.unpack(">I", raw_len)
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
