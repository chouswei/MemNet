"""Session-load advisory warnings."""

from __future__ import annotations

from memnet.config import Caps
from memnet.housekeep import dangling_rows, orphan_rows, recyclable_rows
from memnet.output import emit_wrn
from memnet.session import SessionStore, utc_now


def emit_cap_warnings(store: SessionStore, caps: Caps) -> None:
    checks = [
        ("rows", store.store.row_count_non_law(), caps.max_rows),
        ("law", store.store.law_count(), caps.max_law),
        ("relations", len(store.relations), caps.max_relations),
    ]
    for name, current, maximum in checks:
        if maximum <= 0:
            continue
        pct = current / maximum
        if pct >= 0.95:
            emit_wrn("near_cap_critical", f"{name}|{current}/{maximum}|housekeep required")
        elif pct >= 0.80:
            emit_wrn("near_cap", f"{name}|{current}/{maximum}|housekeep recommended")


def emit_ttl_warning(store: SessionStore) -> None:
    from datetime import datetime

    expires = datetime.fromisoformat(store.meta.expires_at.replace("Z", "+00:00"))
    now = utc_now()
    total = store.meta.ttl_minutes
    left = max(0, int((expires - now).total_seconds() // 60))
    if total > 0 and left / total < 0.10:
        emit_wrn("ttl_expiring", str(left))


def emit_stale_warnings(store: SessionStore) -> None:
    r = len(recyclable_rows(store))
    d = len(dangling_rows(store))
    o = len(orphan_rows(store))
    if r:
        emit_wrn(
            "stale_in_store",
            f"{r}|query warm or housekeep prune recyclable --apply",
        )
    if d:
        emit_wrn("stale_dangling", f"{d}|housekeep dangling or prune dangling --apply")
    if o:
        emit_wrn("stale_orphans", f"{o}|housekeep orphans or prune orphans --apply")
    if r or d or o:
        emit_wrn("stale_graph", f"{r}|{d}|{o}|housekeep stale")


def emit_session_warnings(store: SessionStore, caps: Caps | None = None) -> None:
    caps = caps or Caps()
    emit_cap_warnings(store, caps)
    emit_ttl_warning(store)
    emit_stale_warnings(store)
