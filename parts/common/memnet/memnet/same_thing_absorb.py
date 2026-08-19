"""SameThingAbsorb — in-session Commit rule (MN-REQ-13.2).

Agent-gated pattern collapse of two live GraphElements judged the same
world-thing. Not Recall, not a product verb, not ImportAbsorb (Path-B
slice + leftover id_policy only). Lookup is labels + properties; SHALL NOT
MERGE-by-id, MERGE-by-name, or invent a store key. Hidden handle stays off
the wire.
"""

from __future__ import annotations

from memnet.exceptions import MemNetError
from memnet.models import Record

_NAME_KEYS = frozenset({"aka", "AKA", "name", "id", "goal"})


def _aka_tokens(text: str) -> list[str]:
    parts = [p.strip() for p in (text or "").split(",")]
    return [p for p in parts if p]


def _merge_aka(keep: Record, drop: Record) -> str:
    tokens: list[str] = []
    seen: set[str] = set()
    for rec in (keep, drop):
        for key in ("aka", "AKA"):
            for tok in _aka_tokens(rec.fields.get(key, "")):
                if tok not in seen:
                    seen.add(tok)
                    tokens.append(tok)
    keep_names = {keep.fields.get(k, "") for k in ("name", "id", "goal")}
    for key in ("name", "id", "goal"):
        val = drop.fields.get(key, "")
        if val and val not in keep_names and val not in seen:
            seen.add(val)
            tokens.append(val)
    return ", ".join(tokens)


def absorb_same_thing(
    store,
    keep: Record,
    drop: Record,
    *,
    extra: dict[str, str] | None = None,
) -> tuple[Record, list[str]]:
    """Collapse ``drop`` into ``keep``. Survivor hid unchanged. Edges retarget."""
    if keep.hid == drop.hid:
        raise MemNetError(
            "invalid_merge",
            "SameThingAbsorb needs two distinct GraphElements",
        )
    if keep.tag == "EDG" or drop.tag == "EDG":
        raise MemNetError(
            "invalid_merge",
            "SameThingAbsorb applies to nodes only (not EDG)",
        )
    if keep.tag != drop.tag:
        raise MemNetError(
            "id_conflict",
            f"SameThingAbsorb tag mismatch {keep.tag}|{drop.tag}",
        )
    merged = dict(keep.fields)
    for key, val in drop.fields.items():
        if key in ("src", "dist", "relation"):
            continue
        if key in ("aka", "AKA"):
            continue
        cur = merged.get(key, "")
        if not cur and val:
            merged[key] = val
    aka = _merge_aka(keep, drop)
    if aka:
        merged["aka"] = aka
        merged.pop("AKA", None)
    if extra:
        for key, val in extra.items():
            if key in ("_memnet_hid", "hid"):
                continue
            merged[key] = val
    keep.fields = merged
    store.replace_row(keep)
    store._retarget_endpoints(drop.hid, keep.hid)
    _fold_duplicate_edges(store, keep.hid)
    store.delete(drop.hid)
    warnings = ["same_thing_absorb|collapsed"]
    return keep, warnings


def _fold_duplicate_edges(store, keep_hid: str) -> None:
    """After retarget, fold same type+ends (pattern identity for relationships)."""
    seen: dict[tuple[str, str, str], Record] = {}
    for rec in list(store.list_records("EDG")):
        src = rec.fields.get("src", "")
        dist = rec.fields.get("dist", "")
        if src != keep_hid and dist != keep_hid:
            continue
        key = (src, rec.fields.get("relation", ""), dist)
        prior = seen.get(key)
        if prior is None:
            seen[key] = rec
            continue
        for k, v in rec.fields.items():
            if k in ("src", "dist", "relation", "id"):
                continue
            if v and not prior.fields.get(k):
                prior.fields[k] = v
        store.replace_row(prior)
        store.delete(rec.hid)


SameThingAbsorb = absorb_same_thing
