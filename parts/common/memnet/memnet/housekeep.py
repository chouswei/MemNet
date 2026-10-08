"""Housekeeping — inspect and prune stale graph rows.

Public functions (``recyclable_rows``, ``dangling_rows``, ``orphan_rows``,
``stale_rows``, ``stats``, ``prune_rows``, ``prune_stale``) are kept stable;
internally the aggregate consumers (``stats``, ``stale_rows``, ``prune_stale``)
share a single categorising pass via ``_categorise`` rather than walking the
store three times.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from memnet.config import ORPHAN_EXEMPT_TAGS
from memnet.exceptions import MemNetError
from memnet.models import Record
from memnet.session import SessionStore


@dataclass
class _Buckets:
    recyclable: list[Record] = field(default_factory=list)
    dangling: list[Record] = field(default_factory=list)
    orphans: list[Record] = field(default_factory=list)
    rows_non_law: int = 0
    edges: int = 0
    referenced: set[str] = field(default_factory=set)


def _node_tokens(rec: Record, dict_key: str) -> set[str]:
    """Identities an edge endpoint may use: hid, dict key, optional nickname."""
    tokens = {rec.hid, dict_key}
    nick = rec.fields.get("id", "")
    if nick:
        tokens.add(nick)
    return tokens


def _resolve_endpoint(store: SessionStore, token: str, token_to_hid: dict[str, str]) -> str | None:
    """Map an edge src/dist token to a live node hid.

    GQL stores ``_elN``. Leftover pipe and older snapshots may store the
    nickname. Both count. An unresolved token is a dangling end.
    """
    if not token:
        return None
    hid = token_to_hid.get(token)
    if hid is not None:
        return hid
    found = store.store.resolve_one(token)
    if found is None or found.tag == "EDG" or found.tag == "LAW":
        return None
    return found.hid


def _refuse_referenced(rows: list[Record], referenced: set[str]) -> None:
    """Do not delete a node that any edge still names."""
    blocked = [
        rec
        for rec in rows
        if rec.tag not in ("EDG", "LAW") and rec.kind == "node" and rec.hid in referenced
    ]
    if not blocked:
        return
    sample = blocked[0]
    nick = sample.fields.get("id") or sample.hid
    raise MemNetError(
        "prune_referenced",
        (f"{len(blocked)} node(s) still referenced by an edge|refusing delete {nick}"),
        example="housekeep dangling; do not prune nodes an edge still names",
    )


def _categorise(
    store: SessionStore,
    *,
    orphan_tag: str | None = None,
    orphan_include_tags: set[str] | None = None,
) -> _Buckets:
    """Classify rows. Edges are resolved before orphan decisions.

    Endpoint tokens match a node by hidden element id (``_elN``) or by
    the optional ``id`` nickname. A node is an orphan only when no edge
    names it. An edge is dangling when either end does not resolve.
    """
    by_id = store.store._by_hid
    token_to_hid: dict[str, str] = {}
    records: list[Record] = []
    buckets = _Buckets()
    for rid, rec in by_id.items():
        if rec.tag == "LAW":
            continue
        buckets.rows_non_law += 1
        records.append(rec)
        if rec.tag != "EDG" and rec.kind == "node":
            for token in _node_tokens(rec, rid):
                token_to_hid.setdefault(token, rec.hid)
    exempt = ORPHAN_EXEMPT_TAGS - (orphan_include_tags or set())
    tag_filter = orphan_tag.upper() if orphan_tag else None
    for rec in records:
        if rec.is_recyclable():
            buckets.recyclable.append(rec)
        if rec.tag != "EDG":
            continue
        buckets.edges += 1
        src = _resolve_endpoint(store, rec.fields.get("src", ""), token_to_hid)
        dist = _resolve_endpoint(store, rec.fields.get("dist", ""), token_to_hid)
        if src is None or dist is None:
            buckets.dangling.append(rec)
        if src is not None:
            buckets.referenced.add(src)
        if dist is not None:
            buckets.referenced.add(dist)
    for rec in records:
        if rec.tag == "EDG" or rec.kind != "node":
            continue
        if rec.tag in exempt:
            continue
        if tag_filter and rec.tag != tag_filter:
            continue
        if rec.hid not in buckets.referenced:
            buckets.orphans.append(rec)
    buckets.dangling.sort(key=lambda r: r.id)
    buckets.orphans.sort(key=lambda r: r.id)
    return buckets


def recyclable_rows(store: SessionStore) -> list[Record]:
    return [r for r in store.store._by_hid.values() if r.is_recyclable()]


def dangling_rows(store: SessionStore) -> list[Record]:
    return _categorise(store).dangling


def orphan_rows(
    store: SessionStore,
    *,
    tag: str | None = None,
    include_tags: set[str] | None = None,
) -> list[Record]:
    return _categorise(store, orphan_tag=tag, orphan_include_tags=include_tags).orphans


def stale_rows(store: SessionStore) -> list[Record]:
    buckets = _categorise(store)
    seen: set[str] = set()
    combined: list[Record] = []
    for group in (buckets.recyclable, buckets.dangling, buckets.orphans):
        for rec in group:
            if rec.hid not in seen:
                seen.add(rec.hid)
                combined.append(rec)
    return combined


def stats(store: SessionStore) -> dict[str, int]:
    buckets = _categorise(store)
    return {
        "rows": buckets.rows_non_law,
        "edges": buckets.edges,
        "relations": len(store.relations),
        "orphans": len(buckets.orphans),
        "dangling": len(buckets.dangling),
        "recyclable": len(buckets.recyclable),
    }


def prune_rows(store: SessionStore, rows: list[Record]) -> list[Record]:
    """Delete ``rows`` after a fresh categorisation.

    Refuses, and deletes nothing, when a node is still an edge endpoint.
    """
    buckets = _categorise(store)
    _refuse_referenced(rows, buckets.referenced)
    deleted: list[Record] = []
    for rec in rows:
        if store.store.delete(rec.hid):
            deleted.append(rec)
    return deleted


def prune_stale(store: SessionStore) -> list[Record]:
    """Recompute stale rows, then delete them.

    Same refusal as ``prune_rows``: a node any edge still references is
    not deleted, and neither is the rest of the batch.
    """
    buckets = _categorise(store)
    seen: set[str] = set()
    rows: list[Record] = []
    for group in (buckets.recyclable, buckets.dangling, buckets.orphans):
        for rec in group:
            if rec.hid in seen:
                continue
            seen.add(rec.hid)
            rows.append(rec)
    _refuse_referenced(rows, buckets.referenced)
    out: list[Record] = []
    for rec in rows:
        if store.store.delete(rec.hid):
            out.append(rec)
    return out
