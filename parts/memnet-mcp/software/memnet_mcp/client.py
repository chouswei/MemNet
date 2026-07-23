"""Run MemNet CLI commands via in-process engine (primary) or TCP fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from memnet.in_process_engine import run_argv
from memnet.serve import probe, send_command
from memnet_mcp.parse import extract_errors, extract_session_id

_SERVE_REQUIRED = "@ERR: serve_required|run memnet serve in another terminal first"


@dataclass
class MemNetResponse:
    exit_code: int
    stdout: str
    stderr: str
    session_id: str | None
    errors: list[str]

    def to_json(self) -> str:
        return json.dumps(
            {
                "exit_code": self.exit_code,
                "stdout": self.stdout,
                "stderr": self.stderr,
                "session_id": self.session_id,
                "errors": self.errors,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_raw(
        cls,
        raw: dict,
        *,
        session_hint: str | None = None,
    ) -> MemNetResponse:
        stdout = raw.get("stdout") or ""
        stderr = raw.get("stderr") or ""
        sid = extract_session_id(stdout, stderr) or session_hint
        errors = extract_errors(stderr)
        return cls(
            exit_code=int(raw.get("exit_code", 1)),
            stdout=stdout,
            stderr=stderr,
            session_id=sid,
            errors=errors,
        )

    @classmethod
    def serve_required(cls, *, session_hint: str | None = None) -> MemNetResponse:
        return cls(
            exit_code=2,
            stdout="",
            stderr=_SERVE_REQUIRED + "\n",
            session_id=session_hint or os.environ.get("MEMNET_SESSION"),
            errors=[_SERVE_REQUIRED],
        )

    @classmethod
    def merge(cls, primary: MemNetResponse, follow: MemNetResponse) -> MemNetResponse:
        """Chain responses (e.g. session open then seed add). Keeps primary session_id."""
        if primary.exit_code != 0:
            return primary
        stdout = primary.stdout
        if follow.stdout:
            stdout = f"{stdout}{follow.stdout}" if stdout else follow.stdout
        stderr = primary.stderr
        if follow.stderr:
            stderr = f"{stderr}{follow.stderr}" if stderr else follow.stderr
        return cls(
            exit_code=follow.exit_code,
            stdout=stdout,
            stderr=stderr,
            session_id=primary.session_id or follow.session_id,
            errors=primary.errors + follow.errors,
        )


_NO_SESSION_ARG = frozenset({
    ("session", "load"),
    ("session", "open"),
    ("session", "list"),
    ("session", "close"),
})


def _append_session(argv: list[str], session: str | None) -> list[str]:
    out = list(argv)
    key = (argv[0], argv[1]) if len(argv) >= 2 else ()
    if key in _NO_SESSION_ARG:
        return out
    if session and "--session" not in out:
        out.extend(["--session", session])
    return out


def _transport() -> str:
    """inprocess (default) | tcp — MN-REQ-06.1 primary / 06.3 fallback."""
    explicit = os.environ.get("MEMNET_MCP_TRANSPORT", "").strip().lower()
    if explicit in ("tcp", "serve"):
        return "tcp"
    if explicit in ("inprocess", "inline", "local"):
        return "inprocess"
    # Legacy test flag forces in-process
    if os.environ.get("MEMNET_TEST_INLINE"):
        return "inprocess"
    return "inprocess"


def run_memnet(
    argv: list[str],
    *,
    stdin: str | None = None,
    session: str | None = None,
) -> MemNetResponse:
    """Execute a memnet CLI argv list; return structured wire output.

    Default: InProcessEngine. Set MEMNET_MCP_TRANSPORT=tcp to use TcpServeBridge.
    """
    session = session or os.environ.get("MEMNET_SESSION")
    full_argv = _append_session(argv, session)
    mode = _transport()

    if mode == "tcp":
        if probe():
            raw = send_command(full_argv, stdin=stdin)
            return MemNetResponse.from_raw(raw, session_hint=session)
        return MemNetResponse.serve_required(session_hint=session)

    raw = run_argv(full_argv, stdin=stdin)
    return MemNetResponse.from_raw(raw, session_hint=session)
