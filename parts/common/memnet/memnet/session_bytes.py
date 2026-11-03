"""Incremental session byte budget (MN-REQ-14.12).

One :class:`SessionBytes` ledger per registry entry keeps the escaped snapshot
byte total (schema + every record line) so the write-time budget check costs
O(changed rows + incident edges) instead of re-emitting the whole session.

A record line is ``"@" + TAG + ": " + "|".join(escaped values over the emit
field list)``; its length is ``core + (k_T - 1)`` where ``k_T`` is the emit
field count of the tag. Field order does not change the length, and a key a
record lacks emits an empty value. ``collect_undeclared_extras`` lists an
undeclared key once per row holding it, so with ``m`` rows holding key ``x``
the emit list has ``x`` m times and each such row emits its ``x`` value m
times. ``core`` is therefore kept as ``base`` (the line without separators and
without undeclared values) plus ``m * value bytes`` per undeclared key, summed
per tag (``extra_bytes``), so widening or narrowing a tag costs O(1) per tag:

    total = schema + sum_T(tag_core[T] + sum_x m_T[x] * S_T[x] + c_T * N_T + tag_n[T] * (k_T - 1))

``c_T * N_T`` covers a declared tag without ``id`` in its fields: every row
emits its nick in each of the ``c_T`` id columns (``m_T["id"]``, or the one
column ``_append_id_column`` adds).

The store marks changed hids in its dirty journal (``MemStore.mark_dirty``);
:meth:`SessionBytes._sync` drains it, re-emits the dirty rows plus every edge
incident to a row whose nick or presence changed (a hot node costs its degree),
and falls back to a full rebuild when the journal says so, the schema changed,
or the row count disagrees. Lines are emitted by ``snapshot._emit_one_record_line``
so relation folding, endpoint nick substitution and id-less edges match save.

``snapshot`` is imported lazily: snapshot -> session -> registry -> here.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import TYPE_CHECKING

from memnet.exceptions import MemNetError
from memnet.fixed_tags import FIXED_TAGS
from memnet.models import Record, TagDef, TagMap
from memnet.tag_map import leftover_wire_nick, tag_map_to_lines, validate_id
from memnet.wire import escaped_utf8_len

if TYPE_CHECKING:
    from memnet.mem_store import MemStore
    from memnet.session import SessionStore

ENV_DEBUG = "MEMNET_DEBUG_SESSION_BYTES"  # "1" => every check also recounts and asserts equality

# Nick kinds: a valid ``id``, a minted leftover nick, or the empty id-less EDG nick.
_ID, _LEFT, _NONE = 0, 1, 2


def _debug() -> bool:
    return os.environ.get(ENV_DEBUG) == "1"


def _nick_for(rec: Record) -> tuple[str, int]:
    """Same nick as ``snapshot._snapshot_emit_nick`` when no leftover nick collides."""
    nick = rec.fields.get("id") or ""
    if nick:
        try:
            validate_id(nick)
            return nick, _ID
        except MemNetError:
            pass
    if rec.tag == "EDG":
        return "", _NONE
    return leftover_wire_nick(rec.hid, kind=rec.tag, used=set()), _LEFT


class SessionBytes:
    """Running escaped byte total of one session (see module doc)."""

    def __init__(self) -> None:
        self.valid = False
        self._store: MemStore | None = None
        self._reset()

    def _reset(self) -> None:
        # Per hid.
        self.nick: dict[str, str] = {}
        self._nick_kind: dict[str, int] = {}
        # (canonical tag, undeclared keys but id, their escaped value bytes,
        #  has an undeclared id, fixed-tag extra, escaped nick bytes on a no-id tag)
        self.undecl: dict[str, tuple[str, tuple[str, ...], tuple[int, ...], bool, bool, int]] = {}
        self.core: dict[str, int] = {}
        self.ctag: dict[str, str] = {}
        # Per canonical tag.
        self.tag_n: Counter[str] = Counter()
        self.tag_core: Counter[str] = Counter()
        self.extras: dict[str, dict[str, int]] = {}  # key -> rows holding it (m)
        self.extra_bytes: dict[str, Counter[str]] = {}  # key -> sum of escaped values (S)
        self.nick_bytes: Counter[str] = Counter()  # N_T for declared tags without id
        self._no_id: frozenset[str] = frozenset()
        self._bases: dict[str, frozenset[str]] = {}
        # Nick bookkeeping for the leftover-collision taint.
        self.id_count: Counter[str] = Counter()
        self.leftover: Counter[str] = Counter()
        self.fixed_extra = 0
        self.schema_sig: tuple = ()
        self.n_seen = 0
        self._emit_map: TagMap | None = None
        self._schema_bytes = 0
        self._tainted = False

    def invalidate(self) -> None:
        """The next sync does a full rebuild."""
        self.valid = False
        if self._store is not None:
            self._store._dirty_all = True

    # --- sync ------------------------------------------------------------

    def _sync(self, ss: SessionStore, hids=()) -> None:
        try:
            self._sync_body(ss, hids)
        except BaseException:
            # The journal is already drained: never keep a half-updated ledger.
            self.invalidate()
            raise

    def _sync_body(self, ss: SessionStore, hids) -> None:
        store = ss.store
        if store is not self._store:
            self._store = store
            self.valid = False
        dirty, dirty_all = store.drain_dirty()
        sig = tuple((tag, tuple(td.fields)) for tag, td in ss.tag_map.tags.items())
        if not self.valid or dirty_all or sig != self.schema_sig:
            self._rebuild(ss, sig)
            return
        dirty.update(hids)
        if dirty:
            self._apply(ss, dirty)
        if self.valid and len(store._by_hid) != self.n_seen:
            self._rebuild(ss, sig)

    def _rebuild(self, ss: SessionStore, sig: tuple) -> None:
        self._reset()
        self.schema_sig = sig
        tags = ss.tag_map.tags
        self._bases = {tag: frozenset(td.fields) for tag, td in tags.items()}
        self._no_id = frozenset(
            tag for tag, td in tags.items() if "id" not in td.fields and tag not in FIXED_TAGS
        )
        store = ss.store
        order = [rid for rid in store.write_order if rid in store._by_hid]
        for rid in order:
            self._set_meta(ss, rid, store._by_hid[rid])
        self._tainted = any(n > 1 or self.id_count[nick] for nick, n in self.leftover.items() if n)
        self.n_seen = len(self.nick)
        # A leftover nick collision needs the ``used``-order bump: full path, rebuild next sync.
        self.valid = not self._tainted
        if self._tainted:
            return
        emit_map = self._refresh_emit_map(ss)
        for rid in order:
            self._set_line(ss, rid, store._by_hid[rid], emit_map)

    def _apply(self, ss: SessionStore, dirty: set[str]) -> None:
        store = ss.store
        by_hid = store._by_hid
        todo = set(dirty)
        seen: set[str] = set()
        lines: set[str] = set()
        while todo:
            hid = todo.pop()
            seen.add(hid)
            lines.add(hid)
            if not self._update_meta(ss, hid, by_hid.get(hid)):
                continue
            # Edge lines embed endpoint nicks.
            for eid in (*store._edges_by_src.get(hid, ()), *store._edges_by_dist.get(hid, ())):
                lines.add(eid)
                if eid not in seen and eid not in self.nick and eid in by_hid:
                    todo.add(eid)
        self.n_seen = len(self.nick)
        if any(self._collides(hid) for hid in seen):
            self._tainted = True
            self.valid = False  # leftover nick collision: full path; next sync rebuilds
            return
        emit_map = self._refresh_emit_map(ss)
        for hid in lines:
            self._drop_line(hid)
            rec = by_hid.get(hid)
            if rec is not None and hid in self.nick:
                self._set_line(ss, hid, rec, emit_map)

    def _collides(self, hid: str) -> bool:
        kind = self._nick_kind.get(hid)
        if kind is None or kind == _NONE:
            return False
        nick = self.nick[hid]
        if kind == _ID:
            return self.leftover[nick] > 0
        return self.leftover[nick] > 1 or self.id_count[nick] > 0

    # --- per-row state -----------------------------------------------------

    def _update_meta(self, ss, hid: str, rec: Record | None) -> bool:
        """Replace hid's nick/extras entries. True when its nick or presence changed."""
        old = self.nick.get(hid)
        if old is not None:
            self._drop_meta(hid)
        if rec is None:
            return old is not None
        self._set_meta(ss, hid, rec)
        return self.nick[hid] != old

    def _set_meta(self, ss, hid: str, rec: Record) -> None:
        nick, kind = _nick_for(rec)
        self.nick[hid] = nick
        self._nick_kind[hid] = kind
        if kind == _ID:
            self.id_count[nick] += 1
        elif kind == _LEFT:
            self.leftover[nick] += 1
        canon = _snap()._canonical_tag(ss, rec.tag)
        td = ss.tag_map.get(canon)
        base = self._bases.get(td.tag) or frozenset(td.fields) if td else frozenset(("id",))
        keys = [k for k in rec.fields if k not in base]
        fixed = bool(keys) and (canon in FIXED_TAGS or rec.tag in FIXED_TAGS)
        has_id = "id" in keys
        if has_id:
            keys.remove("id")
        values = tuple(escaped_utf8_len(rec.fields[k]) for k in keys) if not fixed else ()
        enick = escaped_utf8_len(nick) if canon in self._no_id else 0
        self.undecl[hid] = (canon, tuple(keys), values, has_id, fixed, enick)
        if fixed:
            self.fixed_extra += 1
            return
        self.nick_bytes[canon] += enick
        if not keys and not has_id:
            return
        refs = self.extras.setdefault(canon, {})
        sums = self.extra_bytes.setdefault(canon, Counter())
        for key, n in zip(keys, values, strict=True):
            refs[key] = refs.get(key, 0) + 1
            sums[key] += n
        if has_id:
            refs["id"] = refs.get("id", 0) + 1
        self._emit_map = None  # k_T and the SCHEMA line changed

    def _drop_meta(self, hid: str) -> None:
        nick = self.nick.pop(hid)
        kind = self._nick_kind.pop(hid)
        if kind == _ID:
            self.id_count[nick] -= 1
        elif kind == _LEFT:
            self.leftover[nick] -= 1
        canon, keys, values, has_id, fixed, enick = self.undecl.pop(hid)
        if fixed:
            self.fixed_extra -= 1
            return
        self.nick_bytes[canon] -= enick
        if not keys and not has_id:
            return
        refs = self.extras[canon]
        sums = self.extra_bytes[canon]
        for key, n in zip(keys, values, strict=True):
            sums[key] -= n
            refs[key] -= 1
            if not refs[key]:
                del refs[key], sums[key]
        if has_id:
            refs["id"] -= 1
            if not refs["id"]:
                del refs["id"]
        if not refs:
            del self.extras[canon], self.extra_bytes[canon]
        self._emit_map = None

    def _extra_line_bytes(self, hid: str) -> int:
        """Bytes of hid's undeclared values (and no-id nick columns) on its line."""
        canon, keys, values, _has_id, _fixed, enick = self.undecl[hid]
        refs = self.extras.get(canon, {})
        n = sum(refs[key] * v for key, v in zip(keys, values, strict=True))
        if enick:
            n += (refs.get("id") or 1) * enick
        return n

    def _set_line(self, ss, hid: str, rec: Record, emit_map: TagMap) -> None:
        line = _snap()._emit_one_record_line(ss, rec, self.nick, emit_map)
        tag = self.undecl[hid][0]
        core = len(line.encode("utf-8")) - (self._k(tag) - 1) - self._extra_line_bytes(hid)
        self.core[hid] = core
        self.ctag[hid] = tag
        self.tag_n[tag] += 1
        self.tag_core[tag] += core

    def _drop_line(self, hid: str) -> None:
        core = self.core.pop(hid, None)
        if core is None:
            return
        tag = self.ctag.pop(hid)
        self.tag_n[tag] -= 1
        self.tag_core[tag] -= core

    # --- per-tag state -----------------------------------------------------

    def _k(self, tag: str) -> int:
        td = self._emit_map.tags.get(tag) if self._emit_map is not None else None
        return len(td.fields) if td is not None else 1

    def _refresh_emit_map(self, ss: SessionStore) -> TagMap:
        """Same TagDefs as ``snapshot._snapshot_emit_tag_map`` in O(#tags + extras).

        Extras order may differ from first-seen; no byte count depends on it.
        """
        if self._emit_map is not None:
            return self._emit_map
        append_id = _snap()._append_id_column
        extras = {
            tag: [key for key, m in refs.items() for _ in range(m)]
            for tag, refs in self.extras.items()
        }
        fields_by_tag: dict[str, list[str]] = {}
        for tag, td in ss.tag_map.tags.items():
            fields_by_tag[tag] = append_id(tag, list(td.fields) + extras.get(tag, []))
        for tag, extra in extras.items():
            if tag in fields_by_tag or not extra:
                continue
            fields_by_tag[tag] = append_id(tag, ["id", *extra])
        tags: dict[str, TagDef] = {}
        for tag, fields in fields_by_tag.items():
            td = ss.tag_map.get(tag)
            if td is not None:
                tags[tag] = TagDef(tag=td.tag, fields=fields, kind=td.kind)
            else:
                tags[tag] = TagDef(tag=tag, fields=fields, kind="node")
        self._emit_map = TagMap(tags=tags)
        self._schema_bytes = sum(
            len(line.encode("utf-8")) for line in tag_map_to_lines(self._emit_map)
        )
        return self._emit_map

    def _total(self, ss: SessionStore) -> int | None:
        if not self.valid or self._tainted or self.fixed_extra or self._emit_map is None:
            return None
        max_fields = ss.caps.max_fields
        if any(len(td.fields) > max_fields for td in self._emit_map.tags.values()):
            return None  # snapshot_unsaveable width; save reports it
        total = self._schema_bytes
        for tag, n in self.tag_n.items():
            if not n:
                continue
            total += self.tag_core[tag] + n * (self._k(tag) - 1)
            refs = self.extras.get(tag)
            if refs:
                sums = self.extra_bytes[tag]
                total += sum(m * sums[key] for key, m in refs.items() if key != "id")
            if self.nick_bytes[tag]:
                total += ((refs or {}).get("id") or 1) * self.nick_bytes[tag]
        return total


def _snap():
    from memnet import snapshot

    return snapshot


def ledger_for(ss: SessionStore) -> SessionBytes:
    """The ledger of ``ss``'s registry entry (created lazily; dies with the entry)."""
    entry = getattr(ss, "_entry", ss)
    ledger = getattr(entry, "bytes_ledger", None)
    if ledger is None:
        ledger = SessionBytes()
        entry.bytes_ledger = ledger
    return ledger


def _sync_view(ss: SessionStore, hids=()) -> tuple[dict[str, str], TagMap] | None:
    """Sync and return (hid_to_nick, emit_map) when the ledger is exact, else None."""
    ledger = ledger_for(ss)
    try:
        ledger._sync(ss, hids)
    except MemNetError as exc:
        if exc.code == "snapshot_unsaveable":
            return None
        raise
    if ledger._total(ss) is None:
        return None
    return ledger.nick, ledger._emit_map


def incremental_total(ss: SessionStore) -> int | None:
    """Sync the ledger; return the FULL escaped total (schema + all record lines, no early break).

    None when the ledger cannot be exact (tainted / unsaveable fixed-tag width); caller falls back.
    """
    if _sync_view(ss) is None:
        return None
    return ledger_for(ss)._total(ss)


def full_recount_total(ss: SessionStore) -> int:
    """Reference: tag_map_to_lines(_snapshot_emit_tag_map) bytes + every _emit_one_record_line.

    No early break. Pure old code. Raises MemNetError snapshot_unsaveable exactly like
    _snapshot_emit_tag_map.
    """
    from memnet import snapshot as snap

    emit_map = snap._snapshot_emit_tag_map(ss)
    hid_to_nick = snap._snapshot_nicks(ss)
    total = sum(len(line.encode("utf-8")) for line in tag_map_to_lines(emit_map))
    store = ss.store
    for rid in store.write_order:
        rec = store._by_hid.get(rid)
        if rec:
            line = snap._emit_one_record_line(ss, rec, hid_to_nick, emit_map)
            total += len(line.encode("utf-8"))
    return total


def _drift(inc: int, full: int) -> AssertionError:
    return AssertionError(f"session_bytes ledger drift: incremental={inc} full={full}")


def assert_consistent(ss: SessionStore) -> None:
    """Test hook: AssertionError('session_bytes ledger drift: incremental=<a> full=<b>')."""
    inc = incremental_total(ss)
    if inc is None:
        return
    full = full_recount_total(ss)
    if inc != full:
        raise _drift(inc, full)


def check_budget(ss: SessionStore, schema_total: int, hid_to_nick, emit_map) -> None:
    """Called by snapshot.refuse_mutate_line_cap when budget=True.

    Raises limit_exceeded session_bytes|<partial>/<budget>.
    """
    from memnet import snapshot as snap

    t = incremental_total(ss)
    if t is None:
        snap._refuse_session_bytes(ss, hid_to_nick, emit_map, schema_total)
        return
    debug = _debug()
    if debug:
        full = full_recount_total(ss)
        if t != full:
            raise _drift(t, full)
    if t <= ss.caps.max_session_bytes:
        return
    # Refusal path: the old walk reports the partial sum in write_order.
    snap._refuse_session_bytes(ss, snap._snapshot_nicks(ss), emit_map, schema_total)
    if debug:
        raise _drift(t, full_recount_total(ss))
    ledger_for(ss).invalidate()
