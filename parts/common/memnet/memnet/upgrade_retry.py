"""Bounded retry while a serve is draining or briefly refusing connections.

Default window is 30 seconds (``MEMNET_UPGRADE_RETRY_S``). A window of 0
tries once. Timeout is not retried: the serve may already have accepted
the command. ``serve_draining`` is retried because the serve refused it.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from typing import Any

ENV_RETRY_S = "MEMNET_UPGRADE_RETRY_S"
DEFAULT_RETRY_S = 30.0
_RETRY_AFTER = re.compile(r"retry_after_s=(\d+(?:\.\d+)?)")
_RETRY_EXC = (ConnectionRefusedError, ConnectionResetError, ConnectionAbortedError, BrokenPipeError)


def retry_window_s() -> float:
    raw = os.environ.get(ENV_RETRY_S)
    if raw is None or raw.strip() == "":
        return DEFAULT_RETRY_S
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_RETRY_S


def _retry_after(stderr: str) -> float:
    match = _RETRY_AFTER.search(stderr or "")
    if not match:
        return 0.05
    return max(0.0, float(match.group(1)))


def call_with_upgrade_retry(fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Call ``fn`` until it returns or the retry window is spent.

    ``fn`` raises a connection-refusal error, or returns an envelope whose
    stderr contains ``serve_draining``.
    """
    window = retry_window_s()
    deadline = time.monotonic() + window
    delay = 0.05
    while True:
        try:
            raw = fn()
        except _RETRY_EXC:
            if window <= 0 or time.monotonic() >= deadline:
                raise
            remaining = deadline - time.monotonic()
            time.sleep(min(delay, remaining))
            delay = min(delay * 2, 2.0)
            continue
        stderr = ""
        if isinstance(raw, dict):
            stderr = str(raw.get("stderr") or "")
        if "serve_draining" in stderr and window > 0 and time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            pause = min(_retry_after(stderr), delay, remaining)
            time.sleep(pause)
            delay = min(delay * 2, 2.0)
            continue
        return raw
