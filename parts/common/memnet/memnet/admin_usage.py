"""Admin-only serve usage report (MN-REQ-06.11). Not an agent MCP tool.

Counts and caps only. Peek the live registry. MUST NOT emit mn_* session
ids, graph content, or locators. Unconfigured admin credential refuses
with ``admin_unconfigured`` and no report body.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from memnet import __version__
from memnet.config import Caps, expire_save_status, serve_max_frame_bytes
from memnet.exceptions import MemNetError
from memnet.registry import count as registry_count
from memnet.registry import list_entries

ENV_ADMIN_TOKEN = "MEMNET_ADMIN_TOKEN"
ERR_UNCONFIGURED = "admin_unconfigured"
ERR_DENIED = "admin_denied"
ERR_BAD_PRODUCT = "bad_product"

_PRODUCT_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,31}$")
_ALIAS_PREFIX = "s_"
_ALIAS_HEX_LEN = 16

_KNOWN_LIMIT_KINDS = (
    "sessions",
    "rows",
    "relations",
    "law",
    "tags",
    "fields",
    "value_bytes",
    "line_bytes",
    "batch_lines",
)
_KNOWN_ACL = (
    "acl_who",
    "acl_denied",
    "acl_forbidden",
    "acl_bind",
    "acl_scope",
    "acl_bad_caller",
    "acl_bad_bind",
    "acl_bad_scope",
)
_KNOWN_TRUNCATION = ("max_rows", "depth", "fanout", "shell")

_lock = threading.Lock()
_pressure: dict[tuple[str, ...], int] = {}
_started_mono = time.monotonic()
_caller_token: ContextVar[str | None] = ContextVar("memnet_admin_caller_token", default=None)


def reset_pressure() -> None:
    """Test helper — drop process tallies."""
    with _lock:
        _pressure.clear()


def mark_serve_start() -> None:
    """Record serve-start monotonic time (uptime origin)."""
    global _started_mono
    _started_mono = time.monotonic()


def set_caller_token(token: str | None) -> Any:
    """Bind envelope ``admin_token`` for the current serve request."""
    return _caller_token.set(token if token else None)


def reset_caller_token(token: Any) -> None:
    _caller_token.reset(token)


def caller_token() -> str | None:
    return _caller_token.get()


def configured_admin_token() -> str | None:
    raw = os.environ.get(ENV_ADMIN_TOKEN, "")
    raw = raw.strip() if raw else ""
    return raw or None


def validate_product_label(product: str | None) -> str | None:
    """Optional gate-side slug. MUST NOT look like a session id."""
    if product is None:
        return None
    raw = product.strip()
    if not raw:
        return None
    if raw.startswith("mn_") or not _PRODUCT_RE.fullmatch(raw):
        raise MemNetError(
            ERR_BAD_PRODUCT,
            "product label must be a short slug, not a session id",
        )
    return raw


def note_error(code: str, message: str = "") -> None:
    """Count a hard refuse. Ignores admin auth and unrelated codes."""
    if code == "limit_exceeded":
        kind = (message.split("|", 1)[0] or "unknown").strip() or "unknown"
        _inc(("limit_exceeded", kind))
    elif code in {"ingest_budget", "frame_too_large", "reserve_conflict", "session_expired"}:
        _inc((code,))
    elif code.startswith("acl_"):
        _inc(("acl", code))


def note_truncation(reasons: list[str]) -> None:
    """Count signalled pin_map Truncation reasons (not leftover silent clips)."""
    seen: set[str] = set()
    for raw in reasons:
        reason = (raw or "max_rows").strip() or "max_rows"
        if reason in seen:
            continue
        seen.add(reason)
        _inc(("truncation", reason))


def session_alias(session_id: str, *, token: str) -> str:
    digest = hmac.new(token.encode("utf-8"), session_id.encode("utf-8"), hashlib.sha256)
    return f"{_ALIAS_PREFIX}{digest.hexdigest()[:_ALIAS_HEX_LEN]}"


def authenticate(presented: str | None) -> str:
    """Return the configured token, or raise admin_unconfigured / admin_denied."""
    configured = configured_admin_token()
    if configured is None:
        raise MemNetError(
            ERR_UNCONFIGURED,
            f"{ENV_ADMIN_TOKEN} unset",
            exit_code=2,
        )
    got = (presented or "").strip()
    if not got or not hmac.compare_digest(got, configured):
        raise MemNetError(ERR_DENIED, "token mismatch", exit_code=2)
    return configured


def build_report(token: str) -> dict[str, Any]:
    """Peek-only snapshot. MUST NOT purge, slide TTL, or emit mn_* ids."""
    unavailable: list[str] = []
    caps = Caps()
    flags = expire_save_status()
    rss = _rss_bytes()
    if rss is None:
        unavailable.append("rss_bytes")
    live = registry_count()
    session_rows = _peek_session_rows(token, caps, flags["save_on_expire"], unavailable)
    report = {
        "ok": True,
        "sessions": {"live": live, "max": caps.max_sessions},
        "session_rows": session_rows,
        "process": {
            "version": __version__,
            "uptime_s": max(0, int(time.monotonic() - _started_mono)),
            "rss_bytes": rss,
            "save_on_expire": flags["save_on_expire"],
            "expire_snapshot_dir_set": flags["expire_snapshot_dir_set"],
            "caps": {
                "max_sessions": caps.max_sessions,
                "max_rows": caps.max_rows,
                "max_relations": caps.max_relations,
                "max_law": caps.max_law,
                "max_tags": caps.max_tags,
                "max_fields": caps.max_fields,
                "max_value_bytes": caps.max_value_bytes,
                "max_line_bytes": caps.max_line_bytes,
                "max_batch_lines": caps.max_batch_lines,
                "max_depth": caps.max_depth,
                "max_fanout": caps.max_fanout,
                "serve_max_frame_bytes": serve_max_frame_bytes(),
            },
        },
        "pressure": _pressure_snapshot(),
        "unavailable": unavailable,
    }
    _assert_no_session_ids(report)
    return report


def usage_report_envelope(presented: str | None) -> dict[str, Any]:
    """Serve/CLI result: ``exit_code`` / ``stdout`` / ``stderr``."""
    from memnet.output import format_err

    try:
        token = authenticate(presented)
        body = json.dumps(build_report(token), separators=(",", ":")) + "\n"
        return {"exit_code": 0, "stdout": body, "stderr": ""}
    except MemNetError as exc:
        return {
            "exit_code": exc.exit_code,
            "stdout": "",
            "stderr": format_err(exc.code, exc.message, exc.example) + "\n",
        }


def _inc(key: tuple[str, ...]) -> None:
    with _lock:
        _pressure[key] = _pressure.get(key, 0) + 1


def _pressure_snapshot() -> dict[str, Any]:
    with _lock:
        raw = dict(_pressure)
    limit: dict[str, int] = {k: 0 for k in _KNOWN_LIMIT_KINDS}
    acl: dict[str, int] = {k: 0 for k in _KNOWN_ACL}
    trunc: dict[str, int] = {k: 0 for k in _KNOWN_TRUNCATION}
    ingest = 0
    frame = 0
    rsv = 0
    expired = 0
    for key, n in raw.items():
        if key[0] == "limit_exceeded" and len(key) > 1:
            limit[key[1]] = limit.get(key[1], 0) + n
        elif key == ("ingest_budget",):
            ingest += n
        elif key == ("frame_too_large",):
            frame += n
        elif key == ("reserve_conflict",):
            rsv += n
        elif key == ("session_expired",):
            expired += n
        elif key[0] == "acl" and len(key) > 1:
            acl[key[1]] = acl.get(key[1], 0) + n
        elif key[0] == "truncation" and len(key) > 1:
            trunc[key[1]] = trunc.get(key[1], 0) + n
    return {
        "limit_exceeded": limit,
        "ingest_budget": ingest,
        "frame_too_large": frame,
        "acl": acl,
        "reserve_conflict": rsv,
        "session_expired": expired,
        "truncation": trunc,
    }


def _peek_session_rows(
    token: str,
    caps: Caps,
    save_on_expire: bool,
    unavailable: list[str],
) -> list[dict[str, Any]]:
    now = _utc_now()
    rows: list[dict[str, Any]] = []
    for entry in list_entries():
        sid = entry.meta.session_id
        alias = session_alias(sid, token=token)
        expires = datetime.fromisoformat(entry.meta.expires_at.replace("Z", "+00:00"))
        ttl_left = max(0, int((expires - now).total_seconds()))
        last = entry.meta.modified_at or entry.meta.created_at
        product = getattr(entry.meta, "product", None) or None
        sess_caps = getattr(entry.store, "caps", None) or caps
        try:
            n_rows = entry.store.row_count_non_law()
        except Exception:  # noqa: BLE001 — name the field, do not fake zero
            n_rows = None
            unavailable.append(f"session_rows.{alias}.rows")
        try:
            n_rel = len(entry.relations)
        except Exception:  # noqa: BLE001
            n_rel = None
            unavailable.append(f"session_rows.{alias}.relations")
        try:
            rows_max = int(sess_caps.max_rows)
        except Exception:  # noqa: BLE001
            rows_max = None
            unavailable.append(f"session_rows.{alias}.rows_max")
        try:
            rel_max = int(sess_caps.max_relations)
        except Exception:  # noqa: BLE001
            rel_max = None
            unavailable.append(f"session_rows.{alias}.relations_max")
        row: dict[str, Any] = {
            "alias": alias,
            "product": product,
            "rows": n_rows,
            "rows_max": rows_max,
            "relations": n_rel,
            "relations_max": rel_max,
            "last_access": last,
            "ttl_left_s": ttl_left,
            "save_on_expire_armed": save_on_expire,
        }
        rows.append(row)
    rows.sort(key=lambda r: str(r.get("alias") or ""))
    return rows


def _utc_now() -> datetime:
    try:
        from memnet.session import utc_now

        return utc_now()
    except Exception:  # noqa: BLE001
        return datetime.now(UTC)


def _rss_bytes() -> int | None:
    try:
        with open("/proc/self/statm", encoding="ascii") as fh:
            parts = fh.read().split()
        pages = int(parts[1])
        return pages * int(os.sysconf("SC_PAGE_SIZE"))
    except (OSError, IndexError, ValueError, AttributeError):
        try:
            import resource

            rss_kb = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            if rss_kb <= 0:
                return None
            return rss_kb * 1024
        except Exception:  # noqa: BLE001
            return None


def _assert_no_session_ids(obj: Any) -> None:
    blob = json.dumps(obj)
    if "mn_" in blob:
        raise MemNetError("internal", "usage report leaked a session id")
