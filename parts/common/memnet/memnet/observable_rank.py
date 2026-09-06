"""Observable ranking key for Recall Shape order.

Hidden store handle ``Record.hid`` is off the agent wire and MUST NOT be a
ranking key. Optional nickname property ``id`` is a cue handle, not identity
and not a ranking key (ranking by nickname is the same class of leak as hid).

The pin_map sequence is a function of kind plus the remaining observable
payload (and, for edges, type plus endpoint observables). CREATE order is
not a ranking key.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from memnet.models import Record, SHAPE_DROP_KEYS

# Nickname ``id`` and internal endpoint tokens stay off the rank key.
# ``src`` / ``dist`` on EDG are hid (or leftover nick) handles, not payload.
RANK_EXCLUDE_KEYS = frozenset({"id", "src", "dist"}) | SHAPE_DROP_KEYS

ResolveFn = Callable[[str], Record | None]


def observable_payload(rec: Record) -> tuple[tuple[str, str], ...]:
    """Sorted (key, value) pairs that may appear on the shaped wire."""
    return tuple(
        sorted((str(k), str(v)) for k, v in rec.fields.items() if k not in RANK_EXCLUDE_KEYS)
    )


def node_rank_key(rec: Record) -> tuple:
    """Kind + observable payload. Excludes hid and nickname id."""
    return (rec.tag or "", observable_payload(rec))


def edge_rank_key(rec: Record, resolve: ResolveFn | None = None) -> tuple:
    """Relationship type + endpoint observables + remaining payload."""
    rel = str(rec.fields.get("relation") or "")
    src_tok = str(rec.fields.get("src") or "")
    dist_tok = str(rec.fields.get("dist") or "")
    src_rec = resolve(src_tok) if resolve and src_tok else None
    dist_rec = resolve(dist_tok) if resolve and dist_tok else None
    src_k = node_rank_key(src_rec) if src_rec is not None else ("", ())
    dist_k = node_rank_key(dist_rec) if dist_rec is not None else ("", ())
    return ("EDG", rel, src_k, dist_k, observable_payload(rec))


def record_rank_key(rec: Record, resolve: ResolveFn | None = None) -> tuple:
    if rec.tag == "EDG" or rec.kind == "edge":
        return edge_rank_key(rec, resolve)
    return node_rank_key(rec)


def ranked(
    records: Iterable[Record],
    *,
    resolve: ResolveFn | None = None,
) -> list[Record]:
    """Stable sort by observable rank key. Ties are not broken by hid."""
    return sorted(records, key=lambda r: record_rank_key(r, resolve))


def resolve_from_rows(rows: Iterable[Record]) -> ResolveFn:
    """Hid-or-unique-nickname lookup over an already-packed row list."""
    by_hid: dict[str, Record] = {}
    by_nick: dict[str, Record] = {}
    for rec in rows:
        by_hid[rec.hid] = rec
        nick = rec.id
        if nick and nick not in by_nick:
            by_nick[nick] = rec

    def _resolve(token: str) -> Record | None:
        if not token:
            return None
        hit = by_hid.get(token)
        if hit is not None:
            return hit
        return by_nick.get(token)

    return _resolve
