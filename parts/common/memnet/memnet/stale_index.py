"""Incremental stale counts (recyclable, dangling, orphans) for one ``RecordTable``.

``housekeep._scan_stale_counts`` classifies every row; running it after each write
costs O(rows) per mutate. This index keeps the same three numbers current at
O(rows touched) per write and is the product path; the scan stays as the
reference (``stale_counts(..., use_cache=False)``) that tests compare against.

How it stays exact:

* ``RecordTable`` notes every hid it indexes or unindexes (and ``MemStore.mark_dirty``
  notes the hids it is given) in ``touched``. Nothing is computed on write.
* ``settle`` runs lazily on the next read. For each touched hid it compares the
  row's last-seen summary with its current one; an unchanged summary costs nothing
  (a node update does not re-resolve its edges). A changed one removes the old
  contribution and adds the new, then re-resolves only the edges whose endpoint
  token (hid or nickname) a changed row could affect.
* Endpoint resolution is the scan's rule: the first node in table order that owns
  the token (its hid or nickname) wins; otherwise the unique-hid / unique-nickname
  fallback of ``MemStore.resolve_one``, ignoring EDG and LAW rows.
* A table ``clear`` (load / restore) or a ``mark_dirty()`` with no hids forces one
  full rebuild, which is the only O(rows) case.
"""

from __future__ import annotations

import threading
from typing import NamedTuple

from memnet.config import ORPHAN_EXEMPT_TAGS, RECYCLE_INACTIVE


class _Snap(NamedTuple):
    nick: str
    tokens: tuple[str, ...]  # tokens this row owns as a node (empty for EDG / LAW)
    recyclable: bool
    is_edge: bool
    src: str
    dist: str
    orphan_candidate: bool


def _snap(hid: str, rec) -> _Snap:
    fields = rec.fields
    nick = fields.get("id") or ""
    tag = rec.tag
    is_edge = tag == "EDG"
    node = not is_edge and tag != "LAW"
    tokens: tuple[str, ...] = ()
    if node:
        tokens = tuple({t for t in (rec.hid, hid, nick) if t})
    return _Snap(
        nick,
        tokens,
        fields.get("recycle") in RECYCLE_INACTIVE,
        is_edge,
        (fields.get("src", "") or "") if is_edge else "",
        (fields.get("dist", "") or "") if is_edge else "",
        node and tag not in ORPHAN_EXEMPT_TAGS,
    )


class StaleIndex:
    def __init__(self) -> None:
        self.touched: set[str] = set()
        self.full = True
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self.snap: dict[str, _Snap] = {}
        self.recyclable = 0
        self.owners: dict[str, set[str]] = {}  # token -> node hids that own it
        self.tok_edges: dict[str, set[str]] = {}  # endpoint token -> edge hids
        self.res: dict[str, tuple[str | None, str | None]] = {}
        self.refs: dict[str, int] = {}  # node hid -> edge endpoints resolved to it
        self.dangling: set[str] = set()
        self.orphans: set[str] = set()

    def invalidate(self) -> None:
        """Next read rebuilds from the table (load, restore, unknown change)."""
        self.full = True
        self.touched.clear()

    def counts(self, table) -> tuple[int, int, int]:
        # Warnings are emitted before the session lock is taken, so readers may overlap.
        with self._lock:
            self._settle(table)
            return self.recyclable, len(self.dangling), len(self.orphans)

    # --- resolution ---------------------------------------------------------

    def _resolve(self, table, token: str) -> str | None:
        if not token:
            return None
        own = self.owners.get(token)
        if own:
            hid = min(own, key=table._seq.__getitem__) if len(own) > 1 else next(iter(own))
            return dict.__getitem__(table, hid).hid
        rec = dict.get(table, token)
        if rec is None:
            hits = [
                r
                for h in table.nick_hids(token)
                if (r := dict.get(table, h)) is not None and r.fields.get("id") == token
            ]
            rec = hits[0] if len(hits) == 1 else None
        if rec is None or rec.tag in ("EDG", "LAW"):
            return None
        return rec.hid

    def _unresolve(self, eid: str, check: set[str]) -> None:
        res = self.res.pop(eid, None)
        self.dangling.discard(eid)
        if res is None:
            return
        for target in res:
            if target is None:
                continue
            n = self.refs.get(target, 0) - 1
            if n > 0:
                self.refs[target] = n
            else:
                self.refs.pop(target, None)
            check.add(target)

    def _resolve_edge(self, table, eid: str, check: set[str]) -> None:
        snap = self.snap[eid]
        src = self._resolve(table, snap.src)
        dist = self._resolve(table, snap.dist)
        self.res[eid] = (src, dist)
        if src is None or dist is None:
            self.dangling.add(eid)
        for target in (src, dist):
            if target is not None:
                self.refs[target] = self.refs.get(target, 0) + 1
                check.add(target)

    # --- settle -------------------------------------------------------------

    def _forget(self, hid: str, old: _Snap, tokens: set[str], check: set[str]) -> None:
        if old.recyclable:
            self.recyclable -= 1
        for tok in old.tokens:
            bucket = self.owners.get(tok)
            if bucket is not None:
                bucket.discard(hid)
                if not bucket:
                    del self.owners[tok]
        if old.is_edge:
            for tok in (old.src, old.dist):
                bucket = self.tok_edges.get(tok)
                if bucket is not None:
                    bucket.discard(hid)
                    if not bucket:
                        del self.tok_edges[tok]
            self._unresolve(hid, check)
        self.orphans.discard(hid)
        tokens.add(hid)
        if old.nick:
            tokens.add(old.nick)

    def _admit(self, hid: str, new: _Snap, tokens: set[str]) -> None:
        self.snap[hid] = new
        if new.recyclable:
            self.recyclable += 1
        for tok in new.tokens:
            self.owners.setdefault(tok, set()).add(hid)
        if new.is_edge:
            for tok in (new.src, new.dist):
                self.tok_edges.setdefault(tok, set()).add(hid)
        tokens.add(hid)
        if new.nick:
            tokens.add(new.nick)

    def _settle(self, table) -> None:
        if self.full:
            self._reset()
            self.full = False
            self.touched.clear()
            self.touched.update(list(dict.keys(table)))
        touched = self.touched
        if not touched:
            return
        tokens: set[str] = set()
        check: set[str] = set()
        edges: set[str] = set()
        while True:
            # pop, not swap: a write landing mid-settle stays queued for the next read
            try:
                hid = touched.pop()
            except KeyError:
                break
            rec = dict.get(table, hid)
            new = _snap(hid, rec) if rec is not None else None
            old = self.snap.get(hid)
            if old == new:
                continue
            if old is not None:
                self._forget(hid, old, tokens, check)
                del self.snap[hid]
            if new is not None:
                self._admit(hid, new, tokens)
                if new.is_edge:
                    edges.add(hid)
            check.add(hid)
        for tok in tokens:
            bucket = self.tok_edges.get(tok)
            if bucket:
                edges.update(bucket)
        for eid in edges:
            if eid in self.snap:
                self._unresolve(eid, check)
        for eid in edges:
            if eid in self.snap:
                self._resolve_edge(table, eid, check)
        for hid in check:
            snap = self.snap.get(hid)
            if snap is not None and snap.orphan_candidate and hid not in self.refs:
                self.orphans.add(hid)
            else:
                self.orphans.discard(hid)
