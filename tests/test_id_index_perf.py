"""Nickname id index timing guards: O(1) lookup and linear snapshot load.

Red-first for symphony range-where-id-index (M1). On 0639ad1 ``match_nickname``
scans every row and ``MemStore.load_records`` rebuilds a hid set per edge end, so
lookup is O(N) and load is O(N^2).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_LOOKUP_ROWS = 5000
_LOOKUPS = 5000
_RUNS = 5
_MAX_MS_PER_CALL = 0.02
_LOAD_SMALL = 2000
_LOAD_LARGE = 8000
_MAX_LOAD_RATIO = 8.0


@pytest.fixture
def big_caps(monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_ROWS", "20000")
    monkeypatch.setenv("MEMNET_DEBUG_SESSION_BYTES", "0")


def _lookup_store():
    from memnet.config import Caps
    from memnet.mem_store import MemStore
    from memnet.models import Record
    from memnet.tag_map import load_map_from_lines

    store = MemStore(load_map_from_lines(["@PRT: id|name|role"]), Caps())
    for i in range(_LOOKUP_ROWS):
        store.upsert(Record(tag="PRT", fields={"id": f"P{i}", "name": f"n{i}", "role": "r"}))
    assert len(store._by_hid) == _LOOKUP_ROWS
    return store


def _tokens() -> list[str]:
    # half hits spread over the store, half misses
    out: list[str] = []
    for i in range(_LOOKUPS // 2):
        out.append(f"P{(i * 7919) % _LOOKUP_ROWS}")
        out.append(f"MISS{i}")
    return out


def _best_ms_per_call(fn, tokens: list[str]) -> float:
    best = float("inf")
    for _ in range(_RUNS):
        t0 = time.perf_counter()
        for tok in tokens:
            fn(tok)
        best = min(best, time.perf_counter() - t0)
    return best * 1000.0 / len(tokens)


def test_resolve_one_is_constant_time(big_caps):
    store = _lookup_store()
    tokens = _tokens()
    assert store.resolve_one("P42") is not None
    assert store.resolve_one("MISS0") is None
    ms = _best_ms_per_call(store.resolve_one, tokens)
    print(
        f"resolve_one: {ms:.5f} ms/call on {_LOOKUP_ROWS} rows (limit {_MAX_MS_PER_CALL})",
        flush=True,
    )
    assert ms <= _MAX_MS_PER_CALL, f"resolve_one {ms:.4f} ms/call on {_LOOKUP_ROWS} rows"


def test_match_nickname_is_constant_time(big_caps):
    store = _lookup_store()
    tokens = _tokens()
    assert len(store.match_nickname("P42")) == 1
    assert store.match_nickname("MISS0") == []
    ms = _best_ms_per_call(store.match_nickname, tokens)
    print(
        f"match_nickname: {ms:.5f} ms/call on {_LOOKUP_ROWS} rows (limit {_MAX_MS_PER_CALL})",
        flush=True,
    )
    assert ms <= _MAX_MS_PER_CALL, f"match_nickname {ms:.4f} ms/call on {_LOOKUP_ROWS} rows"


def _write_snapshot(rows: int, path: Path) -> Path:
    """rows/2 nodes and rows/2 edges, written through the real snapshot path."""
    from memnet.models import Record
    from memnet.snapshot import write_snapshot

    ss = open_session(map_lines=["SCHEMA PRT ; fields=id name role"])
    store = ss.store
    nodes = rows // 2
    hids: list[str] = []
    for i in range(nodes):
        rec = Record(tag="PRT", fields={"id": f"P{i}", "name": f"n{i}", "role": "r"})
        store.upsert(rec)
        hids.append(rec.hid)
    ss.relations.add("links")
    for i in range(rows - nodes):
        store.upsert(
            Record(
                tag="EDG",
                fields={
                    "id": f"E{i + 1}",
                    "src": hids[i % nodes],
                    "relation": "links",
                    "dist": hids[(i * 7 + 1) % nodes],
                    "at": "",
                    "attrs": "",
                    "recycle": "persistent",
                },
            )
        )
    write_snapshot(ss, path)
    return path


def _best_load_seconds(path: Path, runs: int = 3) -> float:
    from memnet.snapshot import load_snapshot

    best = float("inf")
    for _ in range(runs):
        t0 = time.perf_counter()
        loaded = load_snapshot(path)
        best = min(best, time.perf_counter() - t0)
    assert loaded.store.row_count_non_law() > 0
    return best


def test_snapshot_load_is_linear(memnet_temp, big_caps, tmp_path: Path):
    small = _write_snapshot(_LOAD_SMALL, tmp_path / "small.snap")
    large = _write_snapshot(_LOAD_LARGE, tmp_path / "large.snap")
    _best_load_seconds(small, runs=1)  # warm imports and caches
    t_small = _best_load_seconds(small)
    t_large = _best_load_seconds(large)
    ratio = t_large / t_small
    print(
        f"load: {_LOAD_LARGE} rows {t_large:.4f}s, {_LOAD_SMALL} rows {t_small:.4f}s,"
        f" ratio {ratio:.2f} (limit {_MAX_LOAD_RATIO})",
        flush=True,
    )
    assert ratio <= _MAX_LOAD_RATIO, (
        f"load {_LOAD_LARGE} rows {t_large:.3f}s / {_LOAD_SMALL} rows {t_small:.3f}s"
        f" = {ratio:.1f} > {_MAX_LOAD_RATIO}"
    )


def test_loaded_snapshot_edges_resolve(memnet_temp, big_caps, tmp_path: Path):
    """Guard for the load fix (green on 0639ad1): every edge end is a live hid."""
    from memnet.snapshot import load_snapshot

    loaded = load_snapshot(_write_snapshot(200, tmp_path / "edges.snap"))
    store = loaded.store
    edges = store.list_records("EDG")
    assert len(edges) == 100
    for edge in edges:
        assert edge.fields["src"] in store._by_hid
        assert edge.fields["dist"] in store._by_hid
    assert len(store.match_nickname("P7")) == 1
    MutateGate(loaded).apply(
        ["MATCH (a {id: 'P1'}), (b {id: 'P2'}) CREATE (a)-[:links {id: 'E_new'}]->(b)"],
        mode="mutate",
    )
    assert store.resolve_one("E_new") is not None
