"""Stale-scan cache: ``housekeep.stale_counts`` is keyed on the store change counter.

Reads must not rescan (per-command cost flat in session size); every write must
invalidate; the @WRN output must be byte-identical with and without the cache.
"""

from __future__ import annotations

import time

import pytest

from memnet import housekeep
from memnet.config import Caps
from memnet.housekeep import stale_counts
from memnet.mem_store import MemStore, RecordTable
from memnet.models import Record
from memnet.mutate_gate import MutateGate
from memnet.output import capture_request_stdio, reset_warn_budget
from memnet.session import open_session
from memnet.tag_map import load_map_from_lines
from memnet.warnings import emit_stale_warnings

_MAP = ["SCHEMA PRT ; fields=id name role recycle"]


def _wrn(ss, *, use_cache: bool, monkeypatch) -> list[str]:
    """The @WRN lines ``emit_stale_warnings`` writes, cached or forced rescan."""
    from memnet import warnings as warnings_mod

    real = housekeep.stale_counts
    monkeypatch.setattr(
        warnings_mod, "stale_counts", lambda s: real(s, use_cache=use_cache), raising=True
    )
    reset_warn_budget()
    with capture_request_stdio(None) as (_out, err):
        emit_stale_warnings(ss)
        return [ln for ln in err.getvalue().splitlines() if ln.startswith("@WRN:")]


def _assert_same(ss, monkeypatch, step: str) -> list[str]:
    cold = _wrn(ss, use_cache=False, monkeypatch=monkeypatch)
    first = _wrn(ss, use_cache=True, monkeypatch=monkeypatch)
    again = _wrn(ss, use_cache=True, monkeypatch=monkeypatch)
    assert first == cold == again, step
    assert stale_counts(ss) == stale_counts(ss, use_cache=False), step
    return first


def _add(ss, *lines: str) -> None:
    MutateGate(ss).apply(list(lines), mode="add", allow_new_relation=True)


def _hid(ss, nick: str) -> str:
    rec = ss.store.resolve_one(nick)
    assert rec is not None, nick
    return rec.hid


# (a) identical warnings, cache vs forced rescan, across every kind of change.
def test_warnings_identical_across_writes_deletes_edges_recycle(memnet_temp, monkeypatch):
    ss = open_session(map_lines=_MAP)
    store = ss.store
    assert _assert_same(ss, monkeypatch, "empty") == []

    _add(ss, "@PRT: P1|a|r|persistent", "@PRT: P2|b|r|persistent")
    assert any("stale_orphans" in ln for ln in _assert_same(ss, monkeypatch, "two orphans"))

    _add(ss, "@EDG: E1|P1|links|P2|||")
    assert _assert_same(ss, monkeypatch, "edge joins them") == []

    _add(ss, "@PRT: P3|c|r|delete_on_settle", "@PRT: P4|d|r|delete_on_expire")
    assert any("stale_in_store" in ln for ln in _assert_same(ss, monkeypatch, "recyclable"))

    # in-place recycle flip followed by a write through the store
    p3 = store.resolve_one("P3")
    p3.fields["recycle"] = "persistent"
    store.replace_row(p3)
    _assert_same(ss, monkeypatch, "recycle flipped off")
    p3.fields["recycle"] = "delete_on_expire"
    store.replace_row(p3)
    _assert_same(ss, monkeypatch, "recycle flipped on")

    # edge endpoint goes away -> dangling
    store.delete(_hid(ss, "P2"))
    assert any("stale_dangling" in ln for ln in _assert_same(ss, monkeypatch, "dangling"))

    # edge deleted -> P1 orphan again
    store.delete(_hid(ss, "E1"))
    _assert_same(ss, monkeypatch, "edge deleted")

    # nickname change (edge endpoints by nickname vs hid)
    _add(ss, "@PRT: P5|e|r|persistent", "@EDG: E2|P5|links|P1|||")
    _assert_same(ss, monkeypatch, "second edge")
    store.rename_id("P5", "P9")
    _assert_same(ss, monkeypatch, "renamed")

    # in-place endpoint edit through reindex
    e2 = store.resolve_one("E2")
    e2.fields["dist"] = "NO_SUCH"
    store.reindex(e2.hid)
    _assert_same(ss, monkeypatch, "endpoint edit")

    # expiry/recycle: prune recyclable rows, then everything stale
    housekeep.prune_rows(ss, [r for r in housekeep.recyclable_rows(ss)])
    _assert_same(ss, monkeypatch, "pruned recyclable")
    housekeep.prune_stale(ss)
    _assert_same(ss, monkeypatch, "pruned stale")

    # whole-store reload
    store.load_records([Record(tag="PRT", fields={"id": "Z1", "recycle": "delete_on_settle"})])
    assert any("stale_in_store" in ln for ln in _assert_same(ss, monkeypatch, "reload"))


def test_warnings_identical_through_cli_commands(memnet_temp, monkeypatch):
    from memnet import warnings as warnings_mod
    from memnet.in_process_engine import run_argv

    ss = open_session(map_lines=_MAP)
    sid = ss.meta.session_id
    real = housekeep.stale_counts

    def run(use_cache: bool, argv: list[str]) -> tuple[int, str, str]:
        monkeypatch.setattr(
            warnings_mod, "stale_counts", lambda s: real(s, use_cache=use_cache), raising=True
        )
        r = run_argv(argv)
        return r["exit_code"], r["stdout"], r["stderr"]

    steps = [
        ["mutate", "--stdin", "--session", sid],
        ["query", "find", "--kind", "PRT", "--limit", "9", "--session", sid],
        ["query", "find", "--kind", "PRT", "--limit", "9", "--session", sid],
    ]
    _add(ss, "@PRT: P1|a|r|persistent", "@PRT: P2|b|r|delete_on_settle")
    for argv in steps[1:]:
        cached = run(True, argv)
        forced = run(False, argv)
        assert cached == forced
        assert "@WRN: stale_orphans" in cached[2]
    _add(ss, "@EDG: E1|P1|links|P2|||")
    assert run(True, steps[1]) == run(False, steps[1])


# Reads do not rescan; the first command after a write rescans exactly once.
def test_read_skips_scan_write_rescans_once(memnet_temp, monkeypatch):
    ss = open_session(map_lines=_MAP)
    _add(ss, "@PRT: P1|a|r|persistent", "@PRT: P2|b|r|delete_on_settle")
    calls = [0]
    real = housekeep._categorise

    def spy(*a, **k):
        calls[0] += 1
        return real(*a, **k)

    monkeypatch.setattr(housekeep, "_categorise", spy)
    for _ in range(5):
        stale_counts(ss)
    assert calls[0] == 1
    ss.store.get("P1")
    ss.store.list_records()
    stale_counts(ss)
    assert calls[0] == 1
    _add(ss, "@PRT: P3|c|r|persistent")
    stale_counts(ss)
    stale_counts(ss)
    assert calls[0] == 2


def test_cache_is_per_store(memnet_temp):
    a = open_session(map_lines=_MAP)
    b = open_session(map_lines=_MAP)
    _add(a, "@PRT: P1|a|r|persistent")
    assert stale_counts(a) == (0, 0, 1)
    assert stale_counts(b) == (0, 0, 0)


# (b) every mutator bumps the counter.
def _store() -> MemStore:
    store = MemStore(load_map_from_lines(["@PRT: id|name|recycle"]), Caps())
    for nick in ("A", "B", "C"):
        store.upsert(Record(tag="PRT", fields={"id": nick, "name": "n", "recycle": "persistent"}))
    store.upsert(
        Record(
            tag="EDG",
            fields={"id": "E1", "src": "A", "relation": "links", "dist": "B", "recycle": "x"},
        ),
        allow_new_relation=True,
    )
    return store


def _node(store: MemStore, nick: str) -> Record:
    rec = store.resolve_one(nick)
    assert rec is not None
    return rec


def _new(nick: str) -> Record:
    return Record(tag="PRT", fields={"id": nick, "name": "n", "recycle": "persistent"})


def _journalled_delete(store: MemStore):
    store.begin_order_journal()
    store.delete("C")
    return store.end_order_journal()


# MemStore methods that change graph state, each with a driver on a fresh store.
_STORE_MUTATORS = {
    "mark_dirty": lambda s: s.mark_dirty(_node(s, "A").hid),
    "load_records": lambda s: s.load_records([_new("Q")]),
    "upsert": lambda s: s.upsert(_new("Q")),
    "add_row": lambda s: s.add_row(_new("Q")),
    "replace_row": lambda s: s.replace_row(_node(s, "A")),
    "delete": lambda s: s.delete("C"),
    "restore_row": lambda s: s.restore_row(_new("Q"), {}),
    "finish_restore": lambda s: s.finish_restore(_journalled_delete(s)),
    "rename_id": lambda s: s.rename_id("A", "A2"),
    "_retarget_endpoints": lambda s: s._retarget_endpoints(_node(s, "A").hid, _node(s, "C").hid),
    "reindex": lambda s: s.reindex(_node(s, "A").hid),
    "raise_id_high_water": lambda s: s.raise_id_high_water({"Z": 9}),
    "_index_tag": lambda s: s._index_tag(_new("Q")),
    "_unindex_tag": lambda s: s._unindex_tag(_node(s, "C")),
    "_index_edge": lambda s: s._index_edge(_node(s, "E1")),
    "_unindex_edge": lambda s: s._unindex_edge(_node(s, "E1")),
}

# Read-only or bookkeeping that never changes what stale_counts sees.
_STORE_NON_MUTATORS = {
    "change_count",
    "drain_dirty",
    "begin_order_journal",
    "end_order_journal",
    "row_count_non_law",
    "law_count",
    "match_nickname",
    "nickname_set",
    "typed_edges",
    "id_high_water",
    "field_keys_by_tag",
    "field_key_counts",
    "verify_indexes",
    "resolve_one",
    "match_nodes",
    "get",
    "list_records",
    "_edge_records",
    "_edges_from",
    "_edges_to",
    "neighbors",
    "context_walk_hops",
    "find_path",
    "_path_to_records",
    "default_anchor",
    "_law_scope_mode",
    "_is_engine_law_id",
    "_is_universal_law",
    "_collect_linked_law_ids",
    "_law_rows_for_context",
    "context_pack",
    "to_jsonl_rows",
    "from_jsonl_rows",
}

_TABLE_MUTATORS = {
    "_index": lambda t: t._index("X", _new("X")),
    "_unindex_adj": lambda t: t._unindex_adj(_hid_of(t, "E1")),
    "_unindex": lambda t: t._unindex(_hid_of(t, "A")),
    "reindex": lambda t: t.reindex(_hid_of(t, "A")),
    "__setitem__": lambda t: t.__setitem__("X", _new("X")),
    "__delitem__": lambda t: t.__delitem__(_hid_of(t, "C")),
    "pop": lambda t: t.pop(_hid_of(t, "C")),
    "popitem": lambda t: t.popitem(),
    "clear": lambda t: t.clear(),
    "update": lambda t: t.update({"X": _new("X")}),
    "setdefault": lambda t: t.setdefault("X", _new("X")),
    "__ior__": lambda t: t.__ior__({"X": _new("X")}),
    "restore": lambda t: t.restore("X", _new("X"), 99),
}

_TABLE_NON_MUTATORS = {
    "__init__",
    "__copy__",
    "__deepcopy__",
    "__reduce__",
    "nick_hids",
    "indexed_edge",
    "adjacent",
}


def _hid_of(table: RecordTable, nick: str) -> str:
    return next(h for h, r in dict.items(table) if r.fields.get("id") == nick)


def _fingerprint(store: MemStore):
    return (
        {h: (r.tag, dict(r.fields)) for h, r in dict.items(store._by_hid)},
        list(store.write_order),
        {k: set(v) for k, v in store._edges_by_src.items()},
        {k: set(v) for k, v in store._edges_by_dist.items()},
        {k: set(v) for k, v in store._by_tag.items()},
        {k: set(v) for k, v in store._by_hid._nick.items()},
        {k: set(v) for k, v in store._by_hid._adj.items()},
        dict(store._by_hid._hw),
    )


def _own_methods(cls) -> set[str]:
    return {
        name
        for name, val in vars(cls).items()
        if callable(val) or isinstance(val, (classmethod, staticmethod, property))
    }


def test_every_memstore_method_is_classified():
    """A new MemStore method must be added to the mutator or the non-mutator list."""
    known = set(_STORE_MUTATORS) | _STORE_NON_MUTATORS | {"__init__"}
    unknown = _own_methods(MemStore) - known
    assert not unknown, f"classify as mutator (bump change_count) or reader: {sorted(unknown)}"
    stale = known - _own_methods(MemStore) - {"__init__"}
    assert not stale, f"classified but gone: {sorted(stale)}"


def test_every_recordtable_method_is_classified():
    known = set(_TABLE_MUTATORS) | _TABLE_NON_MUTATORS
    unknown = _own_methods(RecordTable) - known
    assert not unknown, f"classify as mutator (bump version) or reader: {sorted(unknown)}"
    stale = known - _own_methods(RecordTable)
    assert not stale, f"classified but gone: {sorted(stale)}"


@pytest.mark.parametrize("name", sorted(_STORE_MUTATORS))
def test_memstore_mutator_bumps_change_count(name):
    store = _store()
    before = store.change_count
    _STORE_MUTATORS[name](store)
    assert store.change_count > before, f"MemStore.{name} did not bump change_count"


@pytest.mark.parametrize("name", sorted(_TABLE_MUTATORS))
def test_recordtable_mutator_bumps_version(name):
    store = _store()
    table = store._by_hid
    before = table.version
    _TABLE_MUTATORS[name](table)
    assert table.version > before, f"RecordTable.{name} did not bump version"
    assert store.change_count > 0


def test_readers_leave_change_count_alone():
    store = _store()
    a = _node(store, "A")
    before = store.change_count
    store.get(a.hid)
    store.resolve_one("A")
    store.match_nickname("A")
    store.nickname_set()
    store.list_records()
    store.match_nodes()
    store.neighbors("A")
    store.find_path("A", "B")
    store.typed_edges(a.hid, "links", "out")
    store.to_jsonl_rows()
    store.verify_indexes()
    store.id_high_water()
    assert store.change_count == before


def test_state_change_always_bumps():
    """Backstop: whatever a driver does, a changed fingerprint implies a bumped counter."""
    for name, drive in _STORE_MUTATORS.items():
        store = _store()
        fp, before = _fingerprint(store), store.change_count
        drive(store)
        if _fingerprint(store) != fp:
            assert store.change_count > before, name


# (c) per-command time is flat in session size.
_SMALL = 1000
_LARGE = 5000
_MAX_RATIO = 1.5
_RUNS = 5
_CMDS = 40


def _grow(sid: str, run_argv, start: int, stop: int) -> None:
    for lo in range(start, stop, 250):
        body = "".join(
            f"CREATE (:PRT {{id: 'P{i:05d}', name: 'n{i % 50}', role: 'r'}})\n"
            for i in range(lo, min(lo + 250, stop))
        )
        r = run_argv(["mutate", "--stdin", "--session", sid], stdin=body)
        assert r["exit_code"] == 0, r["stderr"]


def _best_ms(run_argv, argv: list[str]) -> float:
    run_argv(argv)  # cold: the one rescan after the last write
    best = float("inf")
    for _ in range(_RUNS):
        t0 = time.perf_counter()
        for _ in range(_CMDS):
            run_argv(argv)
        best = min(best, (time.perf_counter() - t0) / _CMDS)
    return best * 1000.0


def test_read_command_time_flat_in_session_size(memnet_temp, monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_ROWS", "20000")
    from memnet.in_process_engine import run_argv

    sid = run_argv(["session", "open", "--map", "SCHEMA PRT ; fields=id name role recycle"])[
        "stdout"
    ]
    sid = sid.split("\n")[0].split("|")[0].replace("@SESSION: ", "").strip()
    argv = ["query", "find", "--limit", "1", "--locator", "id=P00037", "--session", sid]
    _grow(sid, run_argv, 0, _SMALL)
    small = _best_ms(run_argv, argv)
    _grow(sid, run_argv, _SMALL, _LARGE)
    large = _best_ms(run_argv, argv)
    assert large <= small * _MAX_RATIO, (
        f"find at {_LARGE} rows {large:.2f} ms vs {small:.2f} ms at {_SMALL} rows"
    )
