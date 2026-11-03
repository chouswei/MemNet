"""Cap enforcement for write paths that bypass the mutate gate (MN-REQ-14.11).

Snapshot import (import_absorb), durable hydrate and CLI delete/prune write the
store directly. They reuse the mutate checks (value cap, whole-line cap, field
cap, session byte budget) and are atomic: the store is checkpointed, written,
verified, and rolled back on any refusal, so a refused call leaves the session
exactly as it was.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from memnet.exceptions import MemNetError
from memnet.models import Record
from memnet.session import SessionStore
from memnet.session_bytes import ledger_for
from memnet.tag_map import check_value_bytes

_RAISE = {
    "session_bytes": "raise MEMNET_MAX_SESSION_BYTES or shrink the session",
    "line_bytes": "raise MEMNET_MAX_LINE_BYTES or shorten the record",
    "value_bytes": "raise MEMNET_MAX_VALUE_BYTES or shorten the value",
}


def check_record_values(records: Iterable[Record], ss: SessionStore) -> None:
    """Value cap (and escaped value vs line cap) on every incoming field value."""
    for rec in records:
        for val in rec.fields.values():
            check_value_bytes(val if isinstance(val, str) else str(val), ss.caps)


@dataclass
class _Checkpoint:
    by_hid: dict[str, Record]
    order: list[str]
    relations: set[str]


def _checkpoint(ss: SessionStore) -> _Checkpoint:
    # Stores replace records rather than mutate them, so a shallow copy restores.
    store = ss.store
    return _Checkpoint(dict(store._by_hid), list(store.write_order), set(ss.relations))


def _restore(ss: SessionStore, cp: _Checkpoint) -> None:
    store = ss.store
    store._by_hid.clear()
    store.write_order.clear()
    store._edges_by_src.clear()
    store._edges_by_dist.clear()
    store._by_tag.clear()
    for hid in cp.order:
        rec = cp.by_hid[hid]
        store._by_hid[hid] = rec
        store.write_order.append(hid)
        store._index_tag(rec)
        if rec.tag == "EDG":
            store._index_edge(rec)
    ss.relations.clear()
    ss.relations.update(cp.relations)
    # Records may keep in-place edits (rename_id, _retarget_endpoints,
    # same_thing_absorb), so reconcile: the next check rebuilds the byte ledger.
    ledger_for(ss).invalidate()


class BypassGuard:
    """Checkpoint handle; call verify() after writing, before mark_written()."""

    def __init__(self, ss: SessionStore, *, budget: bool) -> None:
        self.ss = ss
        self.budget = budget

    def verify(self, hids: Iterable[str]) -> None:
        from memnet.snapshot import refuse_mutate_field_cap, refuse_mutate_line_cap

        touched = set(hids)
        if not touched:
            return
        try:
            refuse_mutate_field_cap(self.ss)
            refuse_mutate_line_cap(self.ss, touched, budget=self.budget)
        except MemNetError as exc:
            if exc.code == "limit_exceeded":
                key = exc.message.split("|", 1)[0]
                if key in _RAISE and exc.example is None:
                    exc.example = _RAISE[key]
            raise


@contextmanager
def bypass_guard(ss: SessionStore, *, budget: bool = True) -> Iterator[BypassGuard]:
    """Roll the store back to its entry state when the body raises."""
    cp = _checkpoint(ss)
    try:
        yield BypassGuard(ss, budget=budget)
    except BaseException:
        _restore(ss, cp)
        raise
