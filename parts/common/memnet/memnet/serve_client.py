"""Route CLI invocations to LocalIpc / TCP serve or run in-process.

Canonical client entry point: dispatch(argv=None) -> int

dispatch decides whether to run inline (stateless commands, test mode, or when no serve is
running) or to proxy via LocalIpcGateway (AF_UNIX, MN-REQ-06.2) or TCP memnet serve
(MN-REQ-06.3). Preference when both are up: IPC first (local share preferred over TCP).

Low-level TCP helpers (send_command, probe) live in memnet.serve and are re-exported here
for advanced clients that need direct control.
"""

from __future__ import annotations

import os
import sys

from memnet.exceptions import MemNetError
from memnet.output import emit_err
from memnet.serve import probe as probe_tcp
from memnet.serve import send_command as send_command_tcp

_STATELESS = frozenset({"version", "guide", "examples", "serve"})
# Run in this process and talk to the serve themselves (work against any serve version).
_CLIENT_SIDE = frozenset({("admin", "upgrade-verify")})


def _stateful(argv: list[str]) -> bool:
    if not argv:
        return False
    return argv[0] not in _STATELESS


def _inline_mode() -> bool:
    return bool(os.environ.get("MEMNET_SERVE_INTERNAL") or os.environ.get("MEMNET_TEST_INLINE"))


def _stdin_for_proxy(argv: list[str]) -> str | None:
    """Forward process stdin when CLI asked for --stdin (match TCP/IPC API)."""
    if "--stdin" not in argv:
        return None
    if hasattr(sys.stdin, "buffer"):
        raw = sys.stdin.buffer.read()
        return raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
    return sys.stdin.read()


def dispatch(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv and argv[0] == "serve":
        return _run_app(argv)
    if not _stateful(argv) or _inline_mode() or tuple(argv[:2]) in _CLIENT_SIDE:
        return _run_app(argv)
    # MN-REQ-06.2 preferred over TCP when MEMNET_IPC_SOCKET is set and listening.
    from memnet.local_ipc_gateway import probe as probe_ipc
    from memnet.local_ipc_gateway import send_command as send_command_ipc

    if probe_ipc():
        stdin_text = _stdin_for_proxy(argv)
        return _emit_proxy_response(send_command_ipc(argv, stdin=stdin_text))
    if probe_tcp():
        stdin_text = _stdin_for_proxy(argv)
        return _emit_proxy_response(send_command_tcp(argv, stdin=stdin_text))
    emit_err(
        MemNetError(
            "serve_required",
            "run memnet serve (or memnet serve --ipc) in another terminal first",
        )
    )
    return 2


def _run_app(argv: list[str]) -> int:
    from memnet.in_process_engine import invoke_cli

    try:
        result = invoke_cli(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    # Non-standalone click returns the typer.Exit code instead of raising it.
    return result if isinstance(result, int) else 0


def _emit_proxy_response(response: dict) -> int:
    stdout = response.get("stdout", "")
    stderr = response.get("stderr", "")
    if stdout:
        sys.stdout.write(stdout if stdout.endswith("\n") else stdout + "\n")
    if stderr:
        sys.stderr.write(stderr if stderr.endswith("\n") else stderr + "\n")
    return int(response.get("exit_code", 1))


# Re-export low-level TCP primitives so advanced clients have a single canonical import path.
probe = probe_tcp
send_command = send_command_tcp
