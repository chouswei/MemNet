"""Route CLI invocations to memnet serve or run in-process.

Canonical client entry point: dispatch(argv=None) -> int

dispatch decides whether to run inline (stateless commands, test mode, or when no serve is
running) or to proxy via TCP to a running memnet serve. It is the supported public API for
all CLI/MCP consumers.

Low-level TCP helpers (send_command, probe) live in memnet.serve and are re-exported here
for advanced clients that need direct control.
"""

from __future__ import annotations

import os
import sys

from memnet.exceptions import MemNetError
from memnet.output import emit_err
from memnet.serve import probe, send_command

_STATELESS = frozenset({"version", "guide", "examples", "serve"})


def _stateful(argv: list[str]) -> bool:
    if not argv:
        return False
    return argv[0] not in _STATELESS


def _inline_mode() -> bool:
    return bool(os.environ.get("MEMNET_SERVE_INTERNAL") or os.environ.get("MEMNET_TEST_INLINE"))


def dispatch(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv and argv[0] == "serve":
        return _run_app(argv)
    if not _stateful(argv) or _inline_mode():
        return _run_app(argv)
    if probe():
        return _emit_proxy_response(send_command(argv))
    emit_err(MemNetError("serve_required", "run memnet serve in another terminal first"))
    return 2


def _run_app(argv: list[str]) -> int:
    from memnet.cli import app

    try:
        app(argv, prog_name="memnet", standalone_mode=False)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    return 0


def _emit_proxy_response(response: dict) -> int:
    stdout = response.get("stdout", "")
    stderr = response.get("stderr", "")
    if stdout:
        sys.stdout.write(stdout if stdout.endswith("\n") else stdout + "\n")
    if stderr:
        sys.stderr.write(stderr if stderr.endswith("\n") else stderr + "\n")
    return int(response.get("exit_code", 1))


# Re-export low-level primitives so advanced clients have a single canonical import path.
from memnet.serve import probe, send_command  # noqa: F401
