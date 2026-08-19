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
from memnet.models import Record
from memnet.session import SessionStore


@dataclass
class _Buckets:
    recyclable: list[Record] = field(default_factory=list)
    dangling: list[Record] = field(default_factory=list)
    orphans: list[Record] = field(default_factory=list)
    rows_non_law: int = 0
    edges: int = 0


def _categorise(
    store: SessionStore,
    *,
    orphan_tag: str | None = None,
    orphan_include_tags: set[str] | None = None,
) -> _Buckets:
    """One pass over the store; emits all housekeep buckets + counts."""
    by_id = store.store._by_hid
    node_ids: set[str] = set()
    incident: set[str] = set()
    records: list[Record] = []
    buckets = _Buckets()
    for rid, rec in by_id.items():
        if rec.tag == "LAW":
            continue
        buckets.rows_non_law += 1
        records.append(rec)
        if rec.tag == "EDG":
            buckets.edges += 1
            incident.add(rec.fields.get("src", ""))
            incident.add(rec.fields.get("dist", ""))
        elif rec.kind == "node":
            node_ids.add(rid)
    incident.discard("")
    exempt = ORPHAN_EXEMPT_TAGS - (orphan_include_tags or set())
    tag_filter = orphan_tag.upper() if orphan_tag else None
    for rec in records:
        if rec.is_recyclable():
            buckets.recyclable.append(rec)
        if rec.tag == "EDG":
            src = rec.fields.get("src", "")
            dist = rec.fields.get("dist", "")
            if src not in node_ids or dist not in node_ids:
                buckets.dangling.append(rec)
            continue
        if rec.kind != "node":
            continue
        if rec.tag in exempt:
            continue
        if tag_filter and rec.tag != tag_filter:
            continue
        if rec.id not in incident:
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
            if rec.id not in seen:
                seen.add(rec.id)
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
    deleted: list[Record] = []
    for rec in rows:
        if store.store.delete(rec.id):
            deleted.append(rec)
    return deleted


def prune_stale(store: SessionStore) -> list[Record]:
    buckets = _categorise(store)
    seen: set[str] = set()
    out: list[Record] = []
    for group in (buckets.recyclable, buckets.dangling, buckets.orphans):
        for rec in group:
            if rec.id in seen:
                continue
            if store.store.delete(rec.id):
                seen.add(rec.id)
                out.append(rec)
    return out
