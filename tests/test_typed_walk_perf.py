"""Typed walk cost bounds: a hop reads only type-T edges, linear, under budget.

Red-first for symphony typed-walks (M1, node P-index; score §1 D3, D7, D8).
``WalkResult.examined`` counts typed edge reads from the adjacency index and
``WalkResult.visited`` counts distinct nodes reached (start included). A walk
never calls ``MemStore._edges_from`` / ``_edges_to`` / ``list_records``. At the
default row cap (5,000) the edge-read budget never trips.

Cap note: the star below is A + 1,000 far nodes + 3,999 edges = 5,000 rows, the
default cap. The 1,000 matching edges stay exact; the other edges on A are
1,000 cites out + 1,000 partOf out + 999 inSession in (one short of 3,000, so
the session fits the cap). One hop returns 1,000 rows, so the tests raise
``WALK_MAX_LIMIT`` (read at call time, D3) to 1,000 for that call only.

New names are looked up inside test bodies so collection never fails on 4b8ed16.
"""

from __future__ import annotations

import statistics
import time

import pytest

from memnet.mem_store import MemStore
from memnet.models import Record
from memnet.session import open_session

_FAR = 1000
_RUNS = 5
_MAX_RATIO = 8.0
_LINEAR_SMALL = 500
_LINEAR_LARGE = 2000
_NONE = "n.name = 'no_such_name'"


@pytest.fixture
def quiet(memnet_temp, monkeypatch):
    monkeypatch.setenv("MEMNET_DEBUG_SESSION_BYTES", "0")


def _node(store, nick: str) -> str:
    rec = Record(tag="PRT", fields={"id": nick, "name": f"n_{nick}", "role": "r"})
    store.upsert(rec)
    return rec.hid


def _edge(store, src: str, rel: str, dist: str) -> None:
    store.upsert(
        Record(
            tag="EDG",
            fields={"src": src, "relation": rel, "dist": dist, "recycle": "persistent"},
        )
    )


def _session():
    ss = open_session(map_lines=["SCHEMA PRT ; fields=id name role"])
    ss.relations.update({"partOf", "inSession", "cites", "replaces", "next"})
    return ss


def _star():
    """A with 1,000 partOf in, 1,000 cites out, 1,000 partOf out, 999 inSession in."""
    ss = _session()
    store = ss.store
    a = _node(store, "A")
    far = [_node(store, f"P{i}") for i in range(_FAR)]
    for i, p in enumerate(far):
        _edge(store, p, "partOf", a)
        _edge(store, a, "cites", p)
        _edge(store, a, "partOf", p)
        if i < _FAR - 1:
            _edge(store, p, "inSession", a)
    assert store.row_count_non_law() == 5000 == ss.caps.max_rows
    return ss


@pytest.fixture
def star(quiet):
    return _star()


def _wide(monkeypatch) -> None:
    from memnet import typed_walk as tw

    monkeypatch.setattr(tw, "WALK_MAX_LIMIT", _FAR)


def test_examined_is_exact_for_one_hop(star, monkeypatch):
    from memnet.typed_walk import typed_walk

    _wide(monkeypatch)
    store = star.store
    res = typed_walk(store, start="A", relation="partOf", direction="in", limit=_FAR)
    assert res.examined == _FAR
    assert len(res.paths) == _FAR
    assert res.visited == _FAR + 1
    assert res.truncated is None
    assert {p.end.fields["id"] for p in res.paths} == {f"P{i}" for i in range(_FAR)}
    res = typed_walk(store, start="A", relation="cites", direction="out", limit=_FAR)
    assert res.examined == _FAR
    assert len(res.paths) == _FAR
    res = typed_walk(store, start="A", relation="replaces", direction="in", limit=_FAR)
    assert res.examined == 0
    assert res.paths == ()
    assert res.visited == 1
    assert res.truncated is None


def test_examined_never_exceeds_type_bucket_at_default_limit(star):
    from memnet.typed_walk import WALK_DEFAULT_LIMIT, WALK_MAX_LIMIT, typed_walk

    store = star.store
    res = typed_walk(store, start="A", relation="partOf", direction="in")
    assert len(res.paths) == WALK_DEFAULT_LIMIT
    assert res.truncated == "limit"
    assert WALK_DEFAULT_LIMIT < res.examined + 1 and res.examined <= _FAR
    res = typed_walk(store, start="A", relation="partOf", direction="in", limit=WALK_MAX_LIMIT)
    assert len(res.paths) == WALK_MAX_LIMIT
    assert res.truncated == "limit"
    assert res.examined <= _FAR
    # WHERE filters rows, not traversal: every typed edge is read, nothing else
    res = typed_walk(store, start="A", relation="partOf", direction="in", where=_NONE)
    assert res.paths == ()
    assert res.truncated is None
    assert res.examined == _FAR


def test_walk_never_scans_other_edges(star, monkeypatch):
    from memnet.typed_walk import typed_walk

    _wide(monkeypatch)
    calls: list[str] = []

    def spy(name):
        real = getattr(MemStore, name)

        def wrapped(self, *args, **kwargs):
            calls.append(name)
            return real(self, *args, **kwargs)

        return wrapped

    for name in ("_edges_from", "_edges_to", "list_records"):
        monkeypatch.setattr(MemStore, name, spy(name))
    store = star.store
    for direction in ("out", "in", "both"):
        res = typed_walk(store, start="A", relation="partOf", direction=direction, limit=_FAR)
        assert len(res.paths) == _FAR
    res = typed_walk(
        store, start="P7", relation="partOf", direction="both", max_hops=3, where=_NONE
    )
    assert res.paths == ()
    assert calls == [], f"typed_walk called {sorted(set(calls))}"


def _chain(hops: int):
    """N0-[:next]->N1 ... N<hops>, each chain node also carries 3 distractor edges."""
    ss = _session()
    store = ss.store
    nodes = [_node(store, f"N{i}") for i in range(hops + 1)]
    side = _node(store, "S")
    for i in range(hops):
        _edge(store, nodes[i], "next", nodes[i + 1])
    for n in nodes:
        _edge(store, n, "cites", side)
        _edge(store, side, "partOf", n)
        _edge(store, n, "replaces", n)
    return ss, hops


def test_ten_hop_chain_examined_bound(quiet):
    from memnet.typed_walk import WALK_MAX_HOPS, typed_walk

    assert WALK_MAX_HOPS == 10
    ss, edges = _chain(10)
    store = ss.store
    res = typed_walk(store, start="N0", relation="next", direction="out", max_hops=10)
    assert [p.end.fields["id"] for p in res.paths] == [f"N{i}" for i in range(1, 11)]
    assert [len(p.steps) for p in res.paths] == list(range(1, 11))
    assert res.examined <= edges
    assert res.visited == 11
    res = typed_walk(store, start="N0", relation="next", direction="both", max_hops=10)
    assert [p.end.fields["id"] for p in res.paths] == [f"N{i}" for i in range(1, 11)]
    assert res.examined <= 2 * edges
    res = typed_walk(store, start="N10", relation="next", direction="in", max_hops=10)
    assert [p.end.fields["id"] for p in res.paths] == [f"N{i}" for i in range(9, -1, -1)]
    assert res.examined <= edges


def _fan(matching: int):
    ss = _session()
    store = ss.store
    a = _node(store, "A")
    for i in range(matching):
        _edge(store, a, "partOf", _node(store, f"F{i}"))
    return ss


def _median_walk_seconds(store, reps: int) -> float:
    from memnet.typed_walk import typed_walk

    times: list[float] = []
    for _ in range(_RUNS):
        t0 = time.perf_counter()
        for _r in range(reps):
            typed_walk(store, start="A", relation="partOf", direction="out", where=_NONE)
        times.append(time.perf_counter() - t0)
    return statistics.median(times)


def test_one_hop_walk_is_linear_in_matching_edges(quiet):
    from memnet.typed_walk import typed_walk

    small = _fan(_LINEAR_SMALL).store
    large = _fan(_LINEAR_LARGE).store
    assert typed_walk(large, start="A", relation="partOf", where=_NONE).examined == _LINEAR_LARGE
    _median_walk_seconds(small, 1)  # warm imports and caches
    t_small = _median_walk_seconds(small, 4)
    t_large = _median_walk_seconds(large, 4)
    ratio = t_large / t_small
    print(
        f"typed_walk: {_LINEAR_LARGE} edges {t_large:.4f}s, {_LINEAR_SMALL} edges"
        f" {t_small:.4f}s, ratio {ratio:.2f} (limit {_MAX_RATIO})",
        flush=True,
    )
    assert ratio <= _MAX_RATIO, (
        f"walk {_LINEAR_LARGE} edges {t_large:.4f}s / {_LINEAR_SMALL} edges {t_small:.4f}s"
        f" = {ratio:.1f} > {_MAX_RATIO}"
    )


def test_default_caps_never_trip_the_budget(quiet):
    """4-ary tree of 2,500 nodes + 2,499 partOf edges = 4,999 rows, depth 6 (T5 is at depth 2)."""
    from memnet.typed_walk import WALK_MAX_EXAMINED, typed_walk

    ss = _session()
    store = ss.store
    nodes = [_node(store, f"T{i}") for i in range(2500)]
    for i in range(1, len(nodes)):
        _edge(store, nodes[(i - 1) // 4], "partOf", nodes[i])
    assert store.row_count_non_law() == 4999 < ss.caps.max_rows
    edges = len(nodes) - 1
    assert 2 * edges < WALK_MAX_EXAMINED
    for start, direction in (("T0", "out"), ("T0", "both"), ("T5", "both")):
        res = typed_walk(
            store, start=start, relation="partOf", direction=direction, max_hops=10, where=_NONE
        )
        assert res.truncated is None, (start, direction)
        assert res.paths == ()
        assert res.visited == len(nodes)
        assert res.examined <= 2 * edges
    res = typed_walk(store, start="T0", relation="partOf", direction="both", max_hops=10)
    assert res.truncated == "limit"
