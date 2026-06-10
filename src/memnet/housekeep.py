"""Housekeeping — inspect and prune stale graph rows."""

from __future__ import annotations

from memnet.config import ORPHAN_EXEMPT_TAGS
from memnet.models import Record
from memnet.session import SessionStore


def _incident_edge_ids(store: SessionStore) -> set[str]:
    ids: set[str] = set()
    for rec in store.store.by_id.values():
        if rec.tag == "EDG":
            ids.add(rec.fields.get("src", ""))
            ids.add(rec.fields.get("dist", ""))
    ids.discard("")
    return ids


def recyclable_rows(store: SessionStore) -> list[Record]:
    return [r for r in store.store.by_id.values() if r.is_recyclable()]


def dangling_rows(store: SessionStore) -> list[Record]:
    node_ids = {rid for rid, r in store.store.by_id.items() if r.kind == "node"}
    out: list[Record] = []
    for rec in store.store.by_id.values():
        if rec.tag != "EDG":
            continue
        src = rec.fields.get("src", "")
        dist = rec.fields.get("dist", "")
        if src not in node_ids or dist not in node_ids:
            out.append(rec)
    return sorted(out, key=lambda r: r.id)


def orphan_rows(
    store: SessionStore,
    *,
    tag: str | None = None,
    include_tags: set[str] | None = None,
) -> list[Record]:
    incident = _incident_edge_ids(store)
    exempt = ORPHAN_EXEMPT_TAGS - (include_tags or set())
    out: list[Record] = []
    for rec in store.store.by_id.values():
        if rec.kind != "node":
            continue
        if rec.tag in exempt:
            continue
        if tag and rec.tag != tag.upper():
            continue
        if rec.id not in incident:
            out.append(rec)
    return sorted(out, key=lambda r: r.id)


def stale_rows(store: SessionStore) -> list[Record]:
    seen: set[str] = set()
    combined: list[Record] = []
    for group in (recyclable_rows(store), dangling_rows(store), orphan_rows(store)):
        for rec in group:
            if rec.id not in seen:
                seen.add(rec.id)
                combined.append(rec)
    return combined


def stats(store: SessionStore) -> dict[str, int]:
    rows = store.store.row_count_non_law()
    edges = sum(1 for r in store.store.by_id.values() if r.tag == "EDG")
    relations = len(store.relations)
    orphans = len(orphan_rows(store))
    dangling = len(dangling_rows(store))
    recyclable = len(recyclable_rows(store))
    return {
        "rows": rows,
        "edges": edges,
        "relations": relations,
        "orphans": orphans,
        "dangling": dangling,
        "recyclable": recyclable,
    }


def prune_rows(store: SessionStore, rows: list[Record]) -> list[Record]:
    deleted: list[Record] = []
    for rec in rows:
        if store.store.delete(rec.id):
            deleted.append(rec)
    return deleted


def prune_stale(store: SessionStore) -> list[Record]:
    rec = prune_rows(store, recyclable_rows(store))
    dan = prune_rows(store, dangling_rows(store))
    orp = prune_rows(store, orphan_rows(store))
    seen: set[str] = set()
    out: list[Record] = []
    for group in (rec, dan, orp):
        for r in group:
            if r.id not in seen:
                seen.add(r.id)
                out.append(r)
    return out
