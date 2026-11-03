"""InProcessEngine — primary binding: run CLI/API in the same process."""

from __future__ import annotations

import os
import threading
from typing import Any

import click
import typer.main

from memnet.output import capture_request_stdio

_cli_command: click.Command | None = None
_cli_command_lock = threading.Lock()


def cli_command() -> click.Command:
    """Click command for ``memnet.cli.app``, built once per process."""
    global _cli_command
    cmd = _cli_command
    if cmd is not None:
        return cmd
    with _cli_command_lock:
        if _cli_command is None:
            from memnet import cli

            _cli_command = typer.main.get_command(cli.app)
        return _cli_command


def reset_cli_command() -> None:
    """Drop the cached click command (next use rebuilds it)."""
    global _cli_command
    with _cli_command_lock:
        _cli_command = None


def invoke_cli(argv: list[str]) -> Any:
    """Run memnet argv on the cached click command (non-standalone)."""
    return cli_command().main(args=list(argv), prog_name="memnet", standalone_mode=False)


def run_argv(argv: list[str], *, stdin: str | None = None) -> dict[str, Any]:
    """Execute memnet CLI argv in-process; return JSON-shaped envelope."""
    os.environ.setdefault("MEMNET_TEST_INLINE", "1")
    os.environ["MEMNET_SERVE_INTERNAL"] = "1"
    code = 0
    with capture_request_stdio(stdin) as (out, err):
        try:
            result = invoke_cli(argv)
            if isinstance(result, int) and result != 0:
                code = result
        except SystemExit as exc:
            code = int(exc.code) if isinstance(exc.code, int) else 1
        except Exception as exc:
            code = 1
            err.write(f"@ERR: internal|{type(exc).__name__}: {exc}\n")
        stdout = out.getvalue()
        stderr = err.getvalue()
    return {"exit_code": code, "stdout": stdout, "stderr": stderr}


class InProcessEngine:
    """Primary GraphStore + SessionLifecycle binding (MN-REQ-06.1)."""

    def run(self, argv: list[str], *, stdin: str | None = None) -> dict[str, Any]:
        return run_argv(argv, stdin=stdin)
