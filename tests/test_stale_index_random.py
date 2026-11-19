"""Incremental stale counts vs the full scan, on randomized write sequences.

The reference is ``housekeep.stale_counts(ss, use_cache=False)`` (the old
per-mutate scan). After every operation the incremental result and the emitted
@WRN lines must equal it exactly. Operations cover insert, update, delete,
rename/merge, in-place edit + reindex, recycle flips, edges by hid / nickname /
missing endpoint, duplicate nicknames, order-exact rollback, and load/restore.
"""

from __future__ import annotations

import random

import pytest

from memnet import housekeep
from memnet import warnings as warnings_mod
from memnet.exceptions import MemNetError
from memnet.housekeep import stale_counts
from memnet.models import Record
from memnet.output import capture_request_stdio, reset_warn_budget
from memnet.session import open_session

_MAP = ["SCHEMA PRT ; fields=id name recycle", "SCHEMA CFG ; fields=id name recycle"]
_RECYCLE = ["persistent", "delete_on_settle", "delete_on_expire", ""]
_NODE_TAGS = ["PRT", "PRT", "PRT", "CFG"]


def _lines(ss, monkeypatch, *, use_cache: bool) -> list[str]:
    real = housekeep.stale_counts
    monkeypatch.setattr(
        warnings_mod, "stale_counts", lambda s: real(s, use_cache=use_cache), raising=True
    )
    reset_warn_budget()
    with capture_request_stdio(None) as (_out, err):
        warnings_mod.emit_stale_warnings(ss)
        return [ln for ln in err.getvalue().splitlines() if ln.startswith("@WRN:")]


def _check(ss, monkeypatch, trace: list[str]) -> None:
    want = stale_counts(ss, use_cache=False)
    assert stale_counts(ss) == want, trace[-6:]
    assert _lines(ss, monkeypatch, use_cache=True) == _lines(ss, monkeypatch, use_cache=False), (
        trace[-6:]
    )


def _rows(ss, tag=None):
    return [r for r in list(ss.store._by_hid.values()) if tag is None or r.tag == tag]


def _step(ss, rng: random.Random, n: int, trace: list[str]) -> None:
    store = ss.store
    nodes = [r for r in _rows(ss) if r.tag not in ("EDG", "LAW")]
    edges = _rows(ss, "EDG")
    op = rng.choice(
        ["node", "node", "node", "edge", "edge", "edge", "dup", "del", "del", "rename",
         "recycle", "endpoint", "nick", "rollback", "load", "pipe"]
    )  # fmt: skip
    trace.append(op)

    def endpoint() -> str:
        if nodes and rng.random() < 0.85:
            r = rng.choice(nodes)
            return r.hid if rng.random() < 0.5 or not r.fields.get("id") else r.fields["id"]
        return f"MISSING{rng.randint(0, 3)}"

    if op in ("node", "dup"):
        nick = f"N{rng.randint(0, 25) if op == 'dup' else n}"
        rec = Record(
            tag=rng.choice(_NODE_TAGS),
            fields={"id": nick, "name": "x", "recycle": rng.choice(_RECYCLE)},
        )
        store.upsert(rec)
    elif op == "edge":
        rec = Record(
            tag="EDG",
            fields={
                "id": f"E{n}",
                "src": endpoint(),
                "relation": "links",
                "dist": endpoint(),
                "recycle": rng.choice(_RECYCLE),
            },
        )
        store.upsert(rec, allow_new_relation=True)
    elif op == "del":
        rows = _rows(ss)
        if rows:
            store.delete(rng.choice(rows).hid)
    elif op == "rename" and nodes:
        old = rng.choice(nodes)
        if old.fields.get("id"):
            store.rename_id(old.fields["id"], f"N{rng.randint(0, 25)}")
    elif op == "recycle" and (nodes or edges):
        rec = rng.choice(nodes + edges)
        rec.fields["recycle"] = rng.choice(_RECYCLE)
        store.replace_row(rec)
    elif op == "endpoint" and edges:
        rec = rng.choice(edges)
        rec.fields[rng.choice(["src", "dist"])] = endpoint()
        store.reindex(rec.hid)
    elif op == "nick" and nodes:
        rec = rng.choice(nodes)
        rec.fields["id"] = f"N{rng.randint(0, 25)}"
        store.reindex(rec.hid)
        store.mark_dirty(rec.hid)
    elif op == "rollback" and nodes:
        store.begin_order_journal()
        victims = rng.sample(nodes + edges, min(3, len(nodes + edges)))
        saved = [Record(tag=v.tag, fields=dict(v.fields), hid=v.hid) for v in victims]
        for v in victims:
            store.delete(v.hid)
        journal = store.end_order_journal()
        for rec in saved:
            store.restore_row(rec, journal)
        store.finish_restore(journal)
    elif op == "load":
        # restore: whole-table reload from the rows' own dump
        dump = [Record(tag=r.tag, fields=dict(r.fields), hid=r.hid) for r in _rows(ss)]
        rng.shuffle(dump)
        keep = dump[: rng.randint(0, len(dump))]
        store.load_records(keep)
    elif op == "pipe" and nodes:
        rec = rng.choice(nodes)
        rec.fields.pop("recycle", None)
        store.mark_dirty(rec.hid)


@pytest.mark.parametrize("seed", range(40))
def test_incremental_matches_full_scan(memnet_temp, monkeypatch, seed):
    rng = random.Random(seed)
    ss = open_session(map_lines=_MAP)
    trace: list[str] = []
    for n in range(120):
        try:
            _step(ss, rng, n, trace)
        except MemNetError:
            pass  # a refused op (cap, conflict) changes nothing it must not
        if n % 3 == 0 or n > 100:
            _check(ss, monkeypatch, trace)
    _check(ss, monkeypatch, trace)


def test_expired_rows_pruned_then_equal(memnet_temp, monkeypatch):
    ss = open_session(map_lines=_MAP)
    for i in range(6):
        ss.store.upsert(Record(tag="PRT", fields={"id": f"N{i}", "recycle": _RECYCLE[i % 3]}))
    ss.store.upsert(
        Record(tag="EDG", fields={"id": "E1", "src": "N0", "relation": "links", "dist": "N3"}),
        allow_new_relation=True,
    )
    trace = ["seed"]
    _check(ss, monkeypatch, trace)
    housekeep.prune_rows(ss, housekeep.recyclable_rows(ss))
    _check(ss, monkeypatch, trace)
    housekeep.prune_stale(ss)
    _check(ss, monkeypatch, trace)
    assert stale_counts(ss) == (0, 0, 0)
