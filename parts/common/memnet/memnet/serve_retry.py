"""Restart-safe client retry for ``memnet serve`` requests (MN-REQ-06.19).

One place says which serve requests are safe to send twice. ``ServePool.send``
asks it after a failure:

- not delivered (connect refused or reset, or the frame was never fully
  written): retry any request, because the serve never read it;
- ``@ERR: serve_draining|retry_after_s=N``: the serve refused before any work,
  so retry any request after ``N`` seconds;
- reset after the whole frame was written: the serve may have run it, so retry
  READ only. A WRITE surfaces the error and is never replayed.

The wait is bounded by ``MEMNET_SERVE_RETRY_S`` (default 30 s; ``0`` turns
retry off).
"""

from __future__ import annotations

import os
import random
import re
from enum import Enum
from typing import Any

ENV_RETRY_BUDGET = "MEMNET_SERVE_RETRY_S"
DEFAULT_RETRY_BUDGET_S = 30.0
BACKOFF_BASE_S = 0.1
BACKOFF_CAP_S = 2.0

_DRAINING_RE = re.compile(r"^@ERR: serve_draining\|retry_after_s=(\d+(?:\.\d+)?)\s*$", re.M)


class RequestKind(Enum):
    READ = "read"
    WRITE = "write"


# (argv[0], argv[1]) pairs that only read. ``None`` as argv[1] means the verb
# has no subcommand. Anything not listed is a WRITE: unknown verbs fail closed.
_READ_VERBS: frozenset[tuple[str, str | None]] = frozenset(
    {
        ("version", None),
        ("guide", None),
        ("examples", None),
        ("examples", "map"),
        ("examples", "workflow"),
        ("examples", "add"),
        ("examples", "path"),
        ("examples", "agent-guide"),
        ("tagmap", "fields"),
        ("tagmap", "show"),
        ("map", "fields"),
        ("map", "show"),
        ("relations", "list"),
        ("session", "current"),
        ("session", "list"),
        ("session", "resume"),
        ("session", "expire-status"),
        ("read", "list"),
        ("query", "pin-map"),
        ("query", "warm"),
        ("query", "find"),
        ("query", "walk"),
        ("query", "typed-walk"),
        ("query", "neighbors"),
        ("query", "path"),
        ("query", "context"),
        ("housekeep", "stats"),
        ("housekeep", "stale"),
        ("housekeep", "orphans"),
        ("housekeep", "dangling"),
        ("housekeep", "recyclable"),
        ("admin", "usage-report"),
    }
)
_SUBCOMMAND_VERBS = frozenset(v for v, sub in _READ_VERBS if sub is not None) | {
    "session",
    "admin",
    "export",
    "ingest",
    "snap",
}


def argv_kind(argv: Any) -> RequestKind:
    """READ when every effect of ``argv`` is a read; WRITE otherwise."""
    if not isinstance(argv, list) or not argv:
        return RequestKind.WRITE
    words = [str(a) for a in argv]
    verb = words[0]
    sub = words[1] if len(words) > 1 and verb in _SUBCOMMAND_VERBS else None
    if (verb, sub) == ("export", "pin-map"):
        # --out writes a file on the serve host.
        return (
            RequestKind.WRITE
            if any(w == "--out" or w.startswith("--out=") for w in words)
            else RequestKind.READ
        )
    return RequestKind.READ if (verb, sub) in _READ_VERBS else RequestKind.WRITE


def request_kind(payload: dict[str, Any]) -> RequestKind:
    """Kind of one serve envelope (``args`` plus the admin flags)."""
    if payload.get("upgrade_prepare") is True:
        return RequestKind.WRITE
    if payload.get("admin_usage") is True:
        return RequestKind.READ
    return argv_kind(payload.get("args"))


def draining_retry_after(reply: Any) -> float | None:
    """``retry_after_s`` of a serve_draining refusal, else ``None``."""
    if not isinstance(reply, dict) or int(reply.get("exit_code", 0) or 0) == 0:
        return None
    match = _DRAINING_RE.search(str(reply.get("stderr") or ""))
    return float(match.group(1)) if match else None


def retry_budget_s() -> float:
    raw = (os.environ.get(ENV_RETRY_BUDGET) or "").strip()
    if not raw:
        return DEFAULT_RETRY_BUDGET_S
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_RETRY_BUDGET_S
    return max(0.0, value)


def backoff_s(attempt: int, rng: random.Random | None = None) -> float:
    """Exponential backoff with jitter: half to all of ``base * 2**attempt``, capped."""
    ceiling = min(BACKOFF_CAP_S, BACKOFF_BASE_S * (2 ** min(attempt, 16)))
    return ceiling * (0.5 + 0.5 * (rng or random).random())
