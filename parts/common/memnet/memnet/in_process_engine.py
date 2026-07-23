"""InProcessEngine — primary binding: run CLI/API in the same process."""

from __future__ import annotations

import io
import os
import sys
from typing import Any


def run_argv(argv: list[str], *, stdin: str | None = None) -> dict[str, Any]:
    """Execute memnet CLI argv in-process; return JSON-shaped envelope."""
    os.environ.setdefault("MEMNET_TEST_INLINE", "1")
    os.environ["MEMNET_SERVE_INTERNAL"] = "1"
    from memnet.cli import app

    out = io.StringIO()
    err = io.StringIO()
    old_out, old_err, old_in = sys.stdout, sys.stderr, sys.stdin
    sys.stdout, sys.stderr = out, err
    if stdin:
        sys.stdin = io.StringIO(stdin)
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


class InProcessEngine:
    """Primary GraphStore + SessionLifecycle binding (MN-REQ-06.1)."""

    def run(self, argv: list[str], *, stdin: str | None = None) -> dict[str, Any]:
        return run_argv(argv, stdin=stdin)
