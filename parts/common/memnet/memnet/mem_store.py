"""memStore — session store, indexes, graph queries."""

from __future__ import annotations

import re
import time
from collections import Counter, deque

from memnet.config import (
    DEFAULT_QUERY_DEPTH,
    DEFAULT_QUERY_MAX_ROWS,
    Caps,
    normalize_relation,
    standard_relation,
)
from memnet.exceptions import MemNetError
from memnet.filter import record_matches
from memnet.models import SHAPE_DROP_KEYS, Record, TagMap, new_hid
from memnet.observable_rank import node_rank_key, ranked
from memnet.output import emit_wrn

_ENGINE_LAW_IDS = frozenset({"LAW01", "LAW02", "LAW03", "LAW04", "LAW05"})
_LAW_LINK_RELATIONS = frozenset({"governs", "features", "constrains", "applies_to"})
_ENGINE_LAW_ID_RE = re.compile(r"^LAW0[1-5]$")
_ID_TOKEN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NUM_SUFFIX_RE = re.compile(r"^([A-Za-z_]+)(\d+)$")


def _split_suffix(nick: str) -> tuple[str, int] | None:
    m = _NUM_SUFFIX_RE.match(nick) if nick else None
    return (m.group(1), int(m.group(2))) if m else None


class RecordTable(dict):
    """``hid -> Record`` that keeps the nickname id index on every mutator.

    Indexes: nick -> hids, hid -> indexed (nick, tag, keys), hid -> first-insert
    seq (dict order), raw tag -> Counter(field key), per-prefix id high-water,
    and the typed-walk adjacency (node hid, standard relation, "out"|"in") ->
    edge hids, with edge hid -> indexed (src, dist, relation).
    Unindexing uses the indexed snapshot, never the record's current fields, so
    an in-place edit followed by a write (or ``reindex``) stays consistent.
    The high-water is never lowered (``clear`` included): minted ids are burnt.
    No index is ever written to a snapshot; every one is rebuilt on load.
    """

    _MISSING = object()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self._nick: dict[str, set[str]] = {}
        self._ix: dict[str, tuple[str, str, tuple[str, ...]]] = {}
        self._seq: dict[str, int] = {}
        self._next_seq = 0
        self._tag_keys: dict[str, Counter] = {}
        self._hw: dict[str, int] = {}
        self._adj: dict[tuple[str, str, str], set[str]] = {}
        self._eix: dict[str, tuple[str, str, str]] = {}
        self.update(*args, **kwargs)

    # --- index upkeep -------------------------------------------------------

    def _index(self, hid: str, rec: Record) -> None:
        nick = rec.fields.get("id") or ""
        keys = tuple(rec.fields)
        self._ix[hid] = (nick, rec.tag, keys)
        if nick:
            self._nick.setdefault(nick, set()).add(hid)
            split = _split_suffix(nick)
            if split is not None:
                prefix, n = split
                if n > self._hw.get(prefix, -1):
                    self._hw[prefix] = n
        self._tag_keys.setdefault(rec.tag, Counter()).update(keys)
        if rec.tag == "EDG":
            src = rec.fields.get("src") or ""
            dist = rec.fields.get("dist") or ""
            rel = standard_relation(rec.fields.get("relation") or "")
            self._eix[hid] = (src, dist, rel)
            if src:
                self._adj.setdefault((src, rel, "out"), set()).add(hid)
            if dist:
                self._adj.setdefault((dist, rel, "in"), set()).add(hid)

    def _unindex_adj(self, hid: str) -> None:
        esnap = self._eix.pop(hid, None)
        if esnap is None:
            return
        src, dist, rel = esnap
        for key in ((src, rel, "out"), (dist, rel, "in")):
            if not key[0]:
                continue
            bucket = self._adj.get(key)
            if bucket is not None:
                bucket.discard(hid)
                if not bucket:
                    del self._adj[key]

    def _unindex(self, hid: str) -> None:
        self._unindex_adj(hid)
        snap = self._ix.pop(hid, None)
        if snap is None:
            return
        nick, tag, keys = snap
        if nick:
            bucket = self._nick.get(nick)
            if bucket is not None:
                bucket.discard(hid)
                if not bucket:
                    del self._nick[nick]
        counter = self._tag_keys.get(tag)
        if counter is not None:
            counter.subtract(keys)
            for key in keys:
                if counter[key] <= 0:
                    del counter[key]
            if not counter:
                del self._tag_keys[tag]

    def reindex(self, hid: str) -> None:
        self._unindex(hid)
        rec = dict.get(self, hid)
        if rec is not None:
            self._index(hid, rec)

    # --- dict mutators ------------------------------------------------------

    def __setitem__(self, hid: str, rec: Record) -> None:
        if not dict.__contains__(self, hid):
            self._seq[hid] = self._next_seq
            self._next_seq += 1
        self._unindex(hid)
        dict.__setitem__(self, hid, rec)
        self._index(hid, rec)

    def __delitem__(self, hid: str) -> None:
        dict.__delitem__(self, hid)
        self._unindex(hid)
        self._seq.pop(hid, None)

    def pop(self, hid, default=_MISSING):
        if dict.__contains__(self, hid):
            rec = dict.__getitem__(self, hid)
            del self[hid]
            return rec
        if default is RecordTable._MISSING:
            raise KeyError(hid)
        return default

    def popitem(self):
        hid, rec = dict.popitem(self)
        self._unindex(hid)
        self._seq.pop(hid, None)
        return hid, rec

    def clear(self) -> None:
        dict.clear(self)
        self._nick.clear()
        self._ix.clear()
        self._seq.clear()
        self._tag_keys.clear()
        self._adj.clear()
        self._eix.clear()
        # self._hw is kept: the high-water is never lowered.

    def update(self, *args, **kwargs) -> None:
        for hid, rec in dict(*args, **kwargs).items():
            self[hid] = rec

    def setdefault(self, hid, default=None):
        if not dict.__contains__(self, hid):
            self[hid] = default
        return dict.__getitem__(self, hid)

    def __ior__(self, other):
        self.update(other)
        return self

    def __copy__(self) -> RecordTable:
        return _rebuild_record_table(dict(self), self._hw)

    def __deepcopy__(self, memo) -> RecordTable:
        import copy

        return _rebuild_record_table(copy.deepcopy(dict(self), memo), self._hw)

    def __reduce__(self):
        return (_rebuild_record_table, (dict(self), dict(self._hw)))

    # --- reads --------------------------------------------------------------

    def nick_hids(self, nick: str) -> list[str]:
        """Hids indexed under ``nick``, in dict (first-insert) order."""
        bucket = self._nick.get(nick)
        if not bucket:
            return []
        if len(bucket) == 1:
            return list(bucket)
        return sorted(bucket, key=self._seq.__getitem__)

    def indexed_edge(self, hid: str) -> tuple[str, str, str] | None:
        """(src, dist, relation) as last indexed for edge ``hid`` (None if not indexed)."""
        return self._eix.get(hid)

    def adjacent(self, node_hid: str, relation: str, direction: str) -> list[str]:
        """Edge hids of type ``relation`` at ``node_hid``, in first-insert order.

        ``direction`` is "out" (src is the node), "in" (dist is the node) or
        "both" (merged; a self-loop once). Reads only those index buckets.
        """
        if direction == "both":
            out = self._adj.get((node_hid, relation, "out"))
            inn = self._adj.get((node_hid, relation, "in"))
            if out and inn:
                hids = out | inn
            else:
                hids = out or inn
        else:
            hids = self._adj.get((node_hid, relation, direction))
        if not hids:
            return []
        if len(hids) == 1:
            return list(hids)
        return sorted(hids, key=self._seq.__getitem__)

    def restore(self, hid: str, rec: Record, seq: int) -> None:
        """Re-insert a deleted row under its original first-insert ``seq``.

        Rollback only: dict order is put back to seq order, so the table is
        order-exact with its state before the delete (O(N) when it moves).
        """
        if dict.__contains__(self, hid):
            self[hid] = rec
            return
        prev_last = next(reversed(dict.keys(self)), None)
        dict.__setitem__(self, hid, rec)
        self._seq[hid] = seq
        if seq >= self._next_seq:
            self._next_seq = seq + 1
        self._index(hid, rec)
        if prev_last is not None and self._seq[prev_last] > seq:
            items = sorted(dict.items(self), key=lambda kv: self._seq[kv[0]])
            dict.clear(self)
            for key, val in items:
                dict.__setitem__(self, key, val)


def _rebuild_record_table(items: dict, hw: dict[str, int]) -> RecordTable:
    out = RecordTable(items)
    for prefix, n in hw.items():
        if n > out._hw.get(prefix, -1):
            out._hw[prefix] = n
    return out


class MemStore:
    def __init__(self, tag_map: TagMap, caps: Caps | None = None) -> None:
        self.tag_map = tag_map
        self.caps = caps or Caps()
        # Graph is elements keyed by hidden handle (off the wire).
        # RecordTable keeps the nickname index on every write, rollbacks included.
        self._by_hid: RecordTable = RecordTable()
        self.write_order: list[str] = []
        self._edges_by_src: dict[str, set[str]] = {}
        self._edges_by_dist: dict[str, set[str]] = {}
        self._by_tag: dict[str, set[str]] = {}
        # Dirty journal for the session byte ledger (MN-REQ-14.12): hids whose
        # record changed since the last drain; _dirty_all forces a full rebuild.
        self._dirty: set[str] = set()
        self._dirty_all: bool = True
        # Delete journal for an order-exact rollback: hid -> (first-insert seq,
        # write_order index) at its first delete while a batch is open.
        self._order_journal: dict[str, tuple[int, int]] | None = None

    def mark_dirty(self, *hids: str) -> None:
        """Note hids whose stored record changed (over-marking is always safe)."""
        self._dirty.update(hids)

    def drain_dirty(self) -> tuple[set[str], bool]:
        dirty, dirty_all = self._dirty, self._dirty_all
        self._dirty = set()
        self._dirty_all = False
        return dirty, dirty_all

    def load_records(self, records: list[Record]) -> None:
        self._by_hid.clear()
        self.write_order.clear()
        self._edges_by_src.clear()
        self._edges_by_dist.clear()
        self._by_tag.clear()
        self._dirty_all = True
        nick_to_hid: dict[str, str] = {}
        loaded: list[Record] = []
        for rec in records:
            nick = rec.fields.get("id", "")
            if not rec.hid:
                rec.hid = nick or new_hid()
            if nick and nick not in nick_to_hid:
                nick_to_hid[nick] = rec.hid
            loaded.append(rec)
        for rec in loaded:
            if rec.tag == "EDG":
                for key in ("src", "dist"):
                    token = rec.fields.get(key, "")
                    if token and token not in self._by_hid and token in nick_to_hid:
                        rec.fields[key] = nick_to_hid[token]
            self._by_hid[rec.hid] = rec
            self.write_order.append(rec.hid)
            self._index_tag(rec)
            if rec.tag == "EDG":
                self._index_edge(rec)

    def row_count_non_law(self) -> int:
        return sum(len(s) for t, s in self._by_tag.items() if t != "LAW")

    def law_count(self) -> int:
        return len(self._by_tag.get("LAW", set()))

    def upsert(
        self,
        record: Record,
        *,
        agent: str | None = None,
        allow_new_relation: bool = False,
        relations: set[str] | None = None,
    ) -> list[str]:
        warnings: list[str] = []
        if record.tag == "EDG":
            for key in ("src", "dist"):
                token = record.fields.get(key, "")
                resolved = self.resolve_one(token) if token else None
                if resolved is not None:
                    record.fields[key] = resolved.hid
        rid = record.hid
        existing = self._by_hid.get(rid)
        if existing and existing.tag != record.tag:
            raise MemNetError(
                "id_conflict",
                f"id {rid} already used by tag {existing.tag}",
            )
        if record.tag == "LAW" and not existing:
            if self.law_count() >= self.caps.max_law:
                raise MemNetError(
                    "limit_exceeded",
                    f"law|{self.law_count() + 1}/{self.caps.max_law}",
                )
        elif record.tag != "LAW" and not existing:
            if self.row_count_non_law() >= self.caps.max_rows:
                raise MemNetError(
                    "limit_exceeded",
                    f"rows|{self.row_count_non_law() + 1}/{self.caps.max_rows}",
                )
        if record.tag == "EDG" and record.fields.get("relation"):
            record.fields["relation"] = normalize_relation(record.fields["relation"])
        if record.tag == "EDG" and relations is not None:
            rel = record.fields.get("relation", "")
            if rel and rel not in relations:
                if not allow_new_relation:
                    known = ",".join(sorted(relations)) or "none"
                    raise MemNetError(
                        "unknown_relation",
                        f"{rel}|known: {known}",
                    )
                if len(relations) >= self.caps.max_relations:
                    raise MemNetError(
                        "limit_exceeded",
                        f"relations|{len(relations) + 1}/{self.caps.max_relations}",
                    )
                relations.add(rel)
        if record.tag == "EDG":
            for endpoint_key in ("src", "dist"):
                eid = record.fields.get(endpoint_key, "")
                if eid and self.resolve_one(eid) is None and eid not in self._by_hid:
                    warnings.append(f"dangling_endpoint|{endpoint_key} {eid} not found")
        if agent:
            record.agent = agent
        record.written_at = time.time()
        if existing and existing.tag == "EDG":
            self._unindex_edge(existing)
        if not existing:
            self.write_order.append(rid)
            self._index_tag(record)
        self._by_hid[rid] = record
        self.mark_dirty(rid)
        if record.tag == "EDG":
            self._index_edge(record)
        return warnings

    def add_row(
        self,
        record: Record,
        *,
        agent: str | None = None,
        allow_new_relation: bool = False,
        relations: set[str] | None = None,
    ) -> list[str]:
        existing = self._by_hid.get(record.hid)
        if existing:
            raise MemNetError(
                "id_exists",
                f"element {record.hid} exists @{existing.tag}|use update",
            )
        return self.upsert(
            record,
            agent=agent,
            allow_new_relation=allow_new_relation,
            relations=relations,
        )

    def replace_row(
        self,
        record: Record,
        *,
        agent: str | None = None,
        allow_new_relation: bool = False,
        relations: set[str] | None = None,
    ) -> list[str]:
        if record.hid not in self._by_hid:
            raise MemNetError("not_found", f"element {record.hid}|use add")
        return self.upsert(
            record,
            agent=agent,
            allow_new_relation=allow_new_relation,
            relations=relations,
        )

    def delete(self, record_id: str) -> Record | None:
        target = self.resolve_one(record_id)
        hid = target.hid if target is not None else record_id
        existing = self._by_hid.get(hid)
        if existing is None:
            return None
        if existing.tag == "EDG":
            self._unindex_edge(existing)
        self._unindex_tag(existing)
        journal = self._order_journal
        if journal is not None and hid not in journal:
            seq = self._by_hid._seq.get(hid, -1)
            try:
                pos = self.write_order.index(hid)
            except ValueError:
                pos = -1
            journal[hid] = (seq, pos)
        rec = self._by_hid.pop(hid, None)
        self.mark_dirty(hid)
        if rec and hid in self.write_order:
            self.write_order.remove(hid)
        return rec

    # --- order-exact rollback (D8) --------------------------------------------

    def begin_order_journal(self) -> None:
        """Start noting deletes so a refused batch can put rows back in place."""
        self._order_journal = {}

    def end_order_journal(self) -> dict[str, tuple[int, int]]:
        """Stop noting deletes; return what was noted (empty when none was open)."""
        journal = self._order_journal or {}
        self._order_journal = None
        return journal

    def restore_row(self, rec: Record, journal: dict[str, tuple[int, int]]) -> None:
        """Rollback: put ``rec`` back as the stored row for ``rec.hid``.

        A live row is replaced in place (its position never moved). A row the
        batch deleted goes back under its first-insert seq from ``journal``;
        call ``finish_restore(journal)`` once afterwards to put write_order back.
        """
        hid = rec.hid
        cur = self._by_hid.get(hid)
        if cur is not None:
            if cur.tag == "EDG":
                self._unindex_edge(cur)
            self._unindex_tag(cur)
            self._by_hid[hid] = rec
        else:
            mark = journal.get(hid)
            if mark is not None and mark[0] >= 0:
                self._by_hid.restore(hid, rec, mark[0])
            else:
                self._by_hid[hid] = rec
            if mark is None or mark[1] < 0:
                if hid not in self.write_order:
                    self.write_order.append(hid)
        self.mark_dirty(hid)
        self._index_tag(rec)
        if rec.tag == "EDG":
            self._index_edge(rec)

    def finish_restore(self, journal: dict[str, tuple[int, int]]) -> None:
        """Put restored rows back at their write_order index (undo in reverse)."""
        if not journal:
            return
        present = set(self.write_order)
        for hid, (_seq, pos) in reversed(list(journal.items())):
            if pos < 0 or hid in present or hid not in self._by_hid:
                continue
            self.write_order.insert(pos, hid)
            present.add(hid)

    def rename_id(
        self,
        old_id: str,
        new_id: str,
        *,
        merge: bool = False,
    ) -> list[str]:
        """Leftover nickname SET. Identity stays the hidden handle.
        merge=true still collapses by nickname (leftover; not SameThingAbsorb).
        """
        warnings: list[str] = []
        if old_id == new_id:
            return warnings
        if new_id == "NEW" or not _ID_TOKEN_RE.match(new_id):
            raise MemNetError("invalid_id", f"id {new_id}")
        old = self.resolve_one(old_id)
        if old is None:
            raise MemNetError("not_found", f"id {old_id}|use add")
        target = self.resolve_one(new_id)
        if target is not None and target.hid != old.hid and not merge:
            raise MemNetError(
                "id_occupied",
                f"id {new_id} occupied @{target.tag}|use merge=true to merge into existing",
            )
        if target is not None and target.hid != old.hid and merge:
            if old.tag == "EDG" or target.tag == "EDG":
                raise MemNetError(
                    "invalid_merge",
                    "merge=true applies to nodes only (not EDG)",
                )
            if old.tag != target.tag:
                raise MemNetError(
                    "id_conflict",
                    f"merge {old_id}@{old.tag} into {new_id}@{target.tag} tag mismatch",
                )
            self._retarget_endpoints(old.hid, target.hid)
            self.delete(old.hid)
            warnings.append(f"merged|{old.fields.get('id') or old.hid}->{new_id}")
            return warnings

        old.fields["id"] = new_id
        self.reindex(old.hid)
        self.mark_dirty(old.hid)
        return warnings

    def _retarget_endpoints(self, old_hid: str, new_hid: str) -> None:
        affected = set(self._edges_by_src.get(old_hid, ())) | set(
            self._edges_by_dist.get(old_hid, ())
        )
        for eid in affected:
            edge = self._by_hid.get(eid)
            if edge is None or edge.tag != "EDG":
                continue
            self._unindex_edge(edge)
            self.mark_dirty(eid)
            if edge.fields.get("src") == old_hid:
                edge.fields["src"] = new_hid
            if edge.fields.get("dist") == old_hid:
                edge.fields["dist"] = new_hid
            self._index_edge(edge)

    def match_nickname(self, nick: str) -> list[Record]:
        """Rows whose ``fields['id']`` is ``nick``, in ``_by_hid`` order. O(hits)."""
        if not nick:
            return []
        by_hid = self._by_hid
        out: list[Record] = []
        for hid in by_hid.nick_hids(nick):
            rec = dict.get(by_hid, hid)
            if rec is not None and rec.fields.get("id") == nick:
                out.append(rec)
        return out

    def nickname_set(self) -> set[str]:
        """Every live nickname, plus ``{prefix}{high-water}`` for each id prefix.

        Read from the nickname index (no row scan). The high-water entries keep
        an IdAllocator seeded from this set from re-minting a deleted id.
        """
        by_hid = self._by_hid
        out = set(by_hid._nick)
        out.update(f"{p}{n}" for p, n in by_hid._hw.items())
        return out

    def reindex(self, hid: str) -> None:
        """Re-read one row into the indexes after an in-place field edit.

        For an edge, the src/dist sets are moved off the endpoints last indexed.
        """
        by_hid = self._by_hid
        old = by_hid.indexed_edge(hid)
        if old is not None:
            for node, index in ((old[0], self._edges_by_src), (old[1], self._edges_by_dist)):
                bucket = index.get(node) if node else None
                if bucket is not None:
                    bucket.discard(hid)
                    if not bucket:
                        del index[node]
        by_hid.reindex(hid)
        rec = dict.get(by_hid, hid)
        if rec is not None and rec.tag == "EDG":
            src = rec.fields.get("src", "")
            dist = rec.fields.get("dist", "")
            if src:
                self._edges_by_src.setdefault(src, set()).add(hid)
            if dist:
                self._edges_by_dist.setdefault(dist, set()).add(hid)

    def typed_edges(self, node_hid: str, relation: str, direction: str) -> list[Record]:
        """Edges of type ``relation`` (already standard) at ``node_hid``.

        ``direction``: "out" (src is the node), "in" (dist is the node) or "both"
        (merged; a self-loop once). Order: edge first-insert sequence. Reads only
        the adjacency buckets for (node, relation, direction), never other edges.
        """
        by_hid = self._by_hid
        return [dict.__getitem__(by_hid, h) for h in by_hid.adjacent(node_hid, relation, direction)]

    def id_high_water(self) -> dict[str, int]:
        """Per-prefix highest numeric id suffix ever stored (never lowered)."""
        return dict(self._by_hid._hw)

    def raise_id_high_water(self, hw: dict[str, int]) -> None:
        """Raise per-prefix high-water marks (snapshot ``#@IDHW``); never lowers."""
        cur = self._by_hid._hw
        for prefix, n in hw.items():
            if n > cur.get(prefix, -1):
                cur[prefix] = n

    def field_keys_by_tag(self) -> dict[str, set[str]]:
        """Raw stored tag -> every field key some row of that tag carries."""
        return {tag: set(counter) for tag, counter in self._by_hid._tag_keys.items()}

    def field_key_counts(self, tag: str) -> Counter:
        """Raw stored tag -> rows per field key (read-only view of the index)."""
        return self._by_hid._tag_keys.get(tag) or Counter()

    def verify_indexes(self) -> list[str]:
        """Problems between the indexes and the rows ([] = consistent). O(N)."""
        by_hid = self._by_hid
        if not isinstance(by_hid, RecordTable):
            return ["_by_hid is not a RecordTable"]
        problems: list[str] = []
        nick_want: dict[str, set[str]] = {}
        keys_want: dict[str, Counter] = {}
        live_max: dict[str, int] = {}
        last_seq = -1
        for hid, rec in dict.items(by_hid):
            nick = rec.fields.get("id") or ""
            snap = by_hid._ix.get(hid)
            if snap != (nick, rec.tag, tuple(rec.fields)):
                problems.append(f"stale index row {hid}: indexed={snap!r} nick={nick!r}")
            seq = by_hid._seq.get(hid)
            if seq is None or seq <= last_seq:
                problems.append(f"insert seq out of order at {hid}")
            else:
                last_seq = seq
            if nick:
                nick_want.setdefault(nick, set()).add(hid)
                split = _split_suffix(nick)
                if split is not None:
                    live_max[split[0]] = max(live_max.get(split[0], -1), split[1])
            keys_want.setdefault(rec.tag, Counter()).update(rec.fields.keys())
        live = set(dict.keys(by_hid))
        if set(by_hid._ix) - live:
            problems.append("index holds rows not in the store")
        if set(by_hid._seq) != live:
            problems.append("insert seq keys differ from the store")
        if by_hid._nick != nick_want:
            bad = sorted(set(by_hid._nick) ^ set(nick_want)) or sorted(
                n for n in nick_want if by_hid._nick.get(n) != nick_want[n]
            )
            problems.append(f"nickname index differs: {bad[:5]}")
        if by_hid._tag_keys != keys_want:
            problems.append("field-key counters differ")
        adj_want: dict[tuple[str, str, str], set[str]] = {}
        eix_want: dict[str, tuple[str, str, str]] = {}
        for hid, rec in dict.items(by_hid):
            if rec.tag != "EDG":
                continue
            src = rec.fields.get("src") or ""
            dist = rec.fields.get("dist") or ""
            rel = standard_relation(rec.fields.get("relation") or "")
            eix_want[hid] = (src, dist, rel)
            if src:
                adj_want.setdefault((src, rel, "out"), set()).add(hid)
            if dist:
                adj_want.setdefault((dist, rel, "in"), set()).add(hid)
        if by_hid._adj != adj_want or by_hid._eix != eix_want:
            bad = sorted(
                h for h in set(by_hid._eix) | set(eix_want) if by_hid._eix.get(h) != eix_want.get(h)
            )
            if not bad:
                bad = sorted(
                    f"{k[0]}:{k[1]}:{k[2]}"
                    for k in set(by_hid._adj) | set(adj_want)
                    if by_hid._adj.get(k) != adj_want.get(k)
                )
            problems.append(f"adjacency index differs: {bad[:5]}")
        for prefix, n in live_max.items():
            if by_hid._hw.get(prefix, -1) < n:
                problems.append(f"id high-water {prefix}={by_hid._hw.get(prefix)} < live {n}")
        return problems

    def resolve_one(self, token: str | None) -> Record | None:
        """Unique hid or unique nickname. None if missing or CueConflict cardinality."""
        if not token:
            return None
        if token in self._by_hid:
            return self._by_hid[token]
        hits = self.match_nickname(token)
        if len(hits) == 1:
            return hits[0]
        return None

    def match_nodes(
        self,
        *,
        tag: str | None = None,
        props: dict[str, str] | None = None,
    ) -> list[Record]:
        """Pattern lookup (labels + properties the node actually has)."""
        tag_u = tag.upper() if tag else None
        id_val = str(props["id"]) if props and props.get("id") is not None else ""
        if id_val:
            # Nickname index: candidates are the id hits, not the whole store.
            rows = self.match_nickname(id_val)
            if tag_u:
                rows = [r for r in rows if r.tag == tag_u]
        elif tag_u:
            rows = [self._by_hid[i] for i in self._by_tag.get(tag_u, set()) if i in self._by_hid]
        else:
            rows = [r for r in self._by_hid.values() if r.tag != "EDG"]
        want = [(k, str(v)) for k, v in (props or {}).items() if v is not None]
        out: list[Record] = []
        # Hot path (every relationship end of every CREATE batch scans the store):
        # plain loop with early exit instead of all() over a generator per record.
        for rec in rows:
            if rec.tag == "EDG":
                continue
            fields = rec.fields
            for k, val in want:
                if str(fields.get(k, "")) != val:
                    break
            else:
                out.append(rec)
        return ranked(out, resolve=self.resolve_one)

    def get(self, record_id: str) -> Record | None:
        """Leftover engine lookup (nickname or hid). Not a product command."""
        return self.resolve_one(record_id)

    def list_records(
        self,
        tag: str | None = None,
        *,
        active_only: bool = False,
        where: list[tuple[str, str]] | None = None,
    ) -> list[Record]:
        if tag:
            ids = self._by_tag.get(tag.upper(), set())
            rows = [self._by_hid[i] for i in ids if i in self._by_hid]
        else:
            rows = list(self._by_hid.values())
        if active_only:
            rows = [r for r in rows if not r.is_recyclable()]
        if where:
            rows = [r for r in rows if record_matches(r, where)]
        return ranked(rows, resolve=self.resolve_one)

    def _index_tag(self, rec: Record) -> None:
        self._by_tag.setdefault(rec.tag, set()).add(rec.hid)

    def _unindex_tag(self, rec: Record) -> None:
        bucket = self._by_tag.get(rec.tag)
        if bucket:
            bucket.discard(rec.hid)
            if not bucket:
                del self._by_tag[rec.tag]

    def _index_edge(self, edge: Record) -> None:
        src = edge.fields.get("src", "")
        dist = edge.fields.get("dist", "")
        if src:
            self._edges_by_src.setdefault(src, set()).add(edge.hid)
        if dist:
            self._edges_by_dist.setdefault(dist, set()).add(edge.hid)
        # Re-read the row too, so an in-place endpoint edit reaches the adjacency.
        if dict.get(self._by_hid, edge.hid) is edge:
            self._by_hid.reindex(edge.hid)

    def _unindex_edge(self, edge: Record) -> None:
        src = edge.fields.get("src", "")
        dist = edge.fields.get("dist", "")
        if src:
            bucket = self._edges_by_src.get(src)
            if bucket:
                bucket.discard(edge.hid)
                if not bucket:
                    del self._edges_by_src[src]
        if dist:
            bucket = self._edges_by_dist.get(dist)
            if bucket:
                bucket.discard(edge.hid)
                if not bucket:
                    del self._edges_by_dist[dist]

    def _edge_records(self, edge_ids: set[str] | None) -> list[Record]:
        if not edge_ids:
            return []
        rows = [self._by_hid[eid] for eid in edge_ids if eid in self._by_hid]
        return ranked(rows, resolve=self.resolve_one)

    def _edges_from(self, node_id: str) -> list[Record]:
        rec = self.resolve_one(node_id)
        hid = rec.hid if rec is not None else node_id
        return self._edge_records(self._edges_by_src.get(hid))

    def _edges_to(self, node_id: str) -> list[Record]:
        rec = self.resolve_one(node_id)
        hid = rec.hid if rec is not None else node_id
        return self._edge_records(self._edges_by_dist.get(hid))

    def neighbors(
        self,
        node_id: str,
        depth: int = 1,
        *,
        fanout_warnings: list[str] | None = None,
    ) -> list[Record]:
        depth = min(depth, self.caps.max_depth)
        rec0 = self.resolve_one(node_id)
        if rec0 is None:
            return []
        node_id = rec0.hid
        if node_id not in self._by_hid:
            return []
        visited: set[str] = {node_id}
        node_results: list[Record] = []
        edge_results: list[Record] = []
        edge_seen: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue:
            current, d = queue.popleft()
            if d >= depth:
                continue
            out_edges = ranked(self._edges_from(current), resolve=self.resolve_one)
            if len(out_edges) > self.caps.max_fanout:
                if fanout_warnings is not None:
                    fanout_warnings.append(
                        f"fanout_clamped|{current}|{len(out_edges)}/{self.caps.max_fanout}"
                    )
                out_edges = out_edges[: self.caps.max_fanout]
            in_edges = ranked(self._edges_to(current), resolve=self.resolve_one)
            for edge in ranked(out_edges + in_edges, resolve=self.resolve_one):
                if edge.hid in edge_seen:
                    continue
                edge_seen.add(edge.hid)
                edge_results.append(edge)
                for endpoint in (edge.fields.get("src"), edge.fields.get("dist")):
                    if not endpoint or endpoint in visited:
                        continue
                    if endpoint not in self._by_hid:
                        continue
                    visited.add(endpoint)
                    node_results.append(self._by_hid[endpoint])
                    queue.append((endpoint, d + 1))
        if node_id in self._by_hid:
            seed = self._by_hid[node_id]
            others = ranked(
                [r for r in node_results if r.hid != node_id],
                resolve=self.resolve_one,
            )
            node_results = [seed] + others
        return node_results + ranked(edge_results, resolve=self.resolve_one)

    def context_walk_hops(
        self,
        *,
        anchor_id: str | None = None,
        depth: int = DEFAULT_QUERY_DEPTH,
        max_rows: int = DEFAULT_QUERY_MAX_ROWS,
        active_only: bool = False,
    ) -> list[tuple[str, str, str]]:
        """BFS walk hops from anchor: (src, relation, dst) tuples."""
        depth = min(depth, self.caps.max_depth)
        rec0 = self.resolve_one(anchor_id) if anchor_id else None
        if rec0 is None:
            return []
        anchor_id = rec0.hid
        hops: list[tuple[str, str, str]] = []
        seen_edges: set[str] = set()
        visited: set[str] = {anchor_id}
        queue: deque[tuple[str, int]] = deque([(anchor_id, 0)])
        while queue and len(hops) < max_rows:
            current, d = queue.popleft()
            if d >= depth:
                continue
            out_edges = ranked(self._edges_from(current), resolve=self.resolve_one)
            if len(out_edges) > self.caps.max_fanout:
                out_edges = out_edges[: self.caps.max_fanout]
            in_edges = ranked(self._edges_to(current), resolve=self.resolve_one)
            for edge in ranked(out_edges + in_edges, resolve=self.resolve_one):
                if active_only and edge.is_recyclable():
                    continue
                if edge.hid in seen_edges:
                    continue
                seen_edges.add(edge.hid)
                src = edge.fields.get("src", "")
                dst = edge.fields.get("dist", "")
                rel = standard_relation(edge.fields.get("relation", ""))
                if not rel or not src or not dst:
                    continue
                if src not in self._by_hid or dst not in self._by_hid:
                    continue
                if current not in (src, dst):
                    continue
                hops.append((src, rel, dst))
                if len(hops) >= max_rows:
                    break
                for endpoint in (src, dst):
                    if endpoint in visited:
                        continue
                    node = self._by_hid.get(endpoint)
                    if not node or (active_only and node.is_recyclable()):
                        continue
                    visited.add(endpoint)
                    queue.append((endpoint, d + 1))

        def _hop_key(t: tuple[str, str, str]) -> tuple:
            src, rel, dst = t
            src_rec = self._by_hid.get(src)
            dst_rec = self._by_hid.get(dst)
            return (
                node_rank_key(src_rec) if src_rec is not None else ("", ()),
                rel,
                node_rank_key(dst_rec) if dst_rec is not None else ("", ()),
            )

        return sorted(hops, key=_hop_key)

    def find_path(self, source_id: str, target_id: str) -> list[Record]:
        src_rec = self.resolve_one(source_id)
        dst_rec = self.resolve_one(target_id)
        if src_rec is None or dst_rec is None:
            return []
        source_id, target_id = src_rec.hid, dst_rec.hid
        if source_id not in self._by_hid or target_id not in self._by_hid:
            return []
        if source_id == target_id:
            return [self._by_hid[source_id]]
        depth = self.caps.max_depth
        queue: deque[tuple[str, list[str]]] = deque([(source_id, [source_id])])
        visited: set[str] = {source_id}
        while queue:
            current, path = queue.popleft()
            if len(path) > depth + 1:
                continue
            for edge in self._edges_from(current):
                nxt = edge.fields.get("dist", "")
                if not nxt or nxt not in self._by_hid:
                    continue
                new_path = path + [nxt]
                if nxt == target_id:
                    return self._path_to_records(new_path)
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, new_path))
        return []

    def _path_to_records(self, node_path: list[str]) -> list[Record]:
        records: list[Record] = []
        for nid in node_path:
            records.append(self._by_hid[nid])
        for i in range(len(node_path) - 1):
            src, dst = node_path[i], node_path[i + 1]
            for edge in self._edges_from(src):
                if edge.fields.get("dist") == dst:
                    records.append(edge)
                    break
        return records

    def default_anchor(self) -> str | None:
        for rid in reversed(self.write_order):
            rec = self._by_hid.get(rid)
            if rec and rec.tag != "LAW":
                return rid
        return None

    def _law_scope_mode(self) -> str:
        """Return ``linked`` when LAW06 requests EDG-scoped warm; else ``all``."""
        for rid in self._by_tag.get("LAW", set()):
            rec = self._by_hid.get(rid)
            if rec and rec.fields.get("mechanism") == "law_scope":
                mode = rec.fields.get("constraint", "all")
                return "linked" if mode == "linked_from_anchor" else "all"
        return "all"

    @staticmethod
    def _is_engine_law_id(law_id: str) -> bool:
        return law_id in _ENGINE_LAW_IDS or bool(_ENGINE_LAW_ID_RE.match(law_id))

    @staticmethod
    def _is_universal_law(rec: Record) -> bool:
        return rec.fields.get("constraint") == "*"

    def _collect_linked_law_ids(
        self,
        anchor_id: str | None,
        context_node_ids: set[str],
        *,
        link_depth: int,
        active_only: bool,
    ) -> set[str]:
        law_ids: set[str] = set()
        for rid in self._by_tag.get("LAW", set()):
            rec = self._by_hid.get(rid)
            if not rec:
                continue
            if self._is_engine_law_id(rec.id) or self._is_universal_law(rec):
                law_ids.add(rid)

        seeds = set(context_node_ids)
        if anchor_id:
            seeds.add(anchor_id)

        queue: deque[tuple[str, int]] = deque()
        seen: set[str] = set()
        for sid in seeds:
            if sid in self._by_hid and sid not in seen:
                seen.add(sid)
                queue.append((sid, 0))

        while queue:
            nid, d = queue.popleft()
            rec = self._by_hid.get(nid)
            if rec and rec.tag == "LAW":
                law_ids.add(nid)
            if d >= link_depth:
                continue
            for edge in self._edges_from(nid) + self._edges_to(nid):
                if active_only and edge.is_recyclable():
                    continue
                rel = standard_relation(edge.fields.get("relation", ""))
                if rel not in _LAW_LINK_RELATIONS:
                    continue
                src = edge.fields.get("src", "")
                dist = edge.fields.get("dist", "")
                other = dist if src == nid else src if dist == nid else None
                if not other or other not in self._by_hid:
                    continue
                if other not in seen:
                    seen.add(other)
                    queue.append((other, d + 1))
        return law_ids

    def _law_rows_for_context(
        self,
        *,
        anchor_id: str | None,
        context_node_ids: set[str],
        depth: int,
        active_only: bool,
    ) -> list[Record]:
        if self._law_scope_mode() == "linked":
            link_depth = max(depth + 2, 4)
            linked = self._collect_linked_law_ids(
                anchor_id,
                context_node_ids,
                link_depth=link_depth,
                active_only=active_only,
            )
            return ranked(
                (self._by_hid[i] for i in linked if i in self._by_hid),
                resolve=self.resolve_one,
            )
        return ranked(
            (self._by_hid[i] for i in self._by_tag.get("LAW", set()) if i in self._by_hid),
            resolve=self.resolve_one,
        )

    def context_pack(
        self,
        *,
        anchor_id: str | None = None,
        anchor_ids: list[str] | None = None,
        depth: int = DEFAULT_QUERY_DEPTH,
        max_rows: int = DEFAULT_QUERY_MAX_ROWS,
        active_only: bool = False,
        stale_warnings: list[tuple[Record, str]] | None = None,
        clip_notes: list[dict] | None = None,
    ) -> list[Record]:
        if clip_notes is not None and depth > self.caps.max_depth:
            clip_notes.append(
                {
                    "reason": "depth",
                    "offered": depth,
                    "kept": self.caps.max_depth,
                }
            )
        depth = min(depth, self.caps.max_depth)
        ids: list[str] = []
        for aid in list(anchor_ids or []):
            rec = self.resolve_one(aid) if aid else None
            if rec is not None and rec.hid not in ids:
                ids.append(rec.hid)
        if anchor_id:
            rec = self.resolve_one(anchor_id)
            if rec is not None and rec.hid not in ids:
                ids.append(rec.hid)
        if not ids:
            fallback = self.default_anchor()
            if fallback:
                ids = [fallback]
        ids = [
            r.hid
            for r in ranked(
                (self._by_hid[i] for i in ids if i in self._by_hid),
                resolve=self.resolve_one,
            )
        ]
        payload: list[Record] = []
        context_node_ids: set[str] = set()
        seen: set[str] = set()
        for aid in ids:
            if aid not in self._by_hid:
                continue
            fanout: list[str] = []
            subgraph = self.neighbors(aid, depth, fanout_warnings=fanout)
            for w in fanout:
                emit_wrn(*w.split("|", 1))
                if clip_notes is not None:
                    parts = w.split("|")
                    offered = kept = None
                    if len(parts) >= 3 and "/" in parts[2]:
                        raw_n, raw_cap = parts[2].split("/", 1)
                        try:
                            offered, kept = int(raw_n), int(raw_cap)
                        except ValueError:
                            offered, kept = None, None
                    note: dict = {"reason": "fanout"}
                    if offered is not None and kept is not None:
                        note["offered"] = offered
                        note["kept"] = kept
                    clip_notes.append(note)
            for rec in subgraph:
                if rec.hid in seen:
                    continue
                if active_only and rec.is_recyclable():
                    if stale_warnings is not None:
                        stale_warnings.append((rec, "stale_in_context"))
                    continue
                seen.add(rec.hid)
                payload.append(rec)
                if rec.kind == "node":
                    context_node_ids.add(rec.hid)
        seed_set = set(ids)
        nodes = [r for r in payload if r.kind == "node"]
        edges = [r for r in payload if r.kind == "edge"]
        seed_nodes = [r for r in nodes if r.hid in seed_set]
        seed_nodes = ranked(seed_nodes, resolve=self.resolve_one)
        other_nodes = ranked(
            [r for r in nodes if r.hid not in seed_set],
            resolve=self.resolve_one,
        )
        combined = seed_nodes + other_nodes + ranked(edges, resolve=self.resolve_one)
        offered = len(combined)
        if offered > max_rows:
            if clip_notes is not None:
                clip_notes.append({"reason": "max_rows", "offered": offered, "kept": max_rows})
            combined = combined[:max_rows]
        if not active_only and stale_warnings is not None:
            for rec in combined:
                if rec.is_recyclable():
                    stale_warnings.append((rec, "stale_in_context"))
        law_anchor = ids[0] if ids else None
        law_rows = self._law_rows_for_context(
            anchor_id=law_anchor,
            context_node_ids=context_node_ids,
            depth=depth,
            active_only=active_only,
        )
        if self._law_scope_mode() == "linked":
            law_ids = {r.hid for r in law_rows}
            combined = [r for r in combined if r.tag != "LAW" or r.hid not in law_ids]
        return law_rows + combined

    def to_jsonl_rows(self) -> list[dict]:
        rows: list[dict] = []
        for rid in self.write_order:
            rec = self._by_hid.get(rid)
            if rec:
                dump = rec.model_dump()
                dump.pop("hid", None)
                fields = dump.get("fields")
                if isinstance(fields, dict):
                    for key in SHAPE_DROP_KEYS:
                        fields.pop(key, None)
                rows.append(dump)
        return rows

    @classmethod
    def from_jsonl_rows(
        cls, rows: list[dict], tag_map: TagMap, caps: Caps | None = None
    ) -> MemStore:
        store = cls(tag_map, caps)
        records = [Record.model_validate(r) for r in rows]
        store.load_records(records)
        return store
