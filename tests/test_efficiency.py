"""Soft local efficiency guards (generous wall-clock budgets; not CI timing gates).

Windows host noise can push scans ~2× over tight budgets; thresholds here absorb
that variance. Correctness asserts (row counts / non-empty results) stay strict.
"""

from __future__ import annotations

import time

from memnet.config import Caps, examples_dir
from memnet.mem_store import MemStore
from memnet.tag_map import load_map_from_file, parse_line
from memnet.wire import emit_record_line


def _populate_store(n_nodes: int) -> MemStore:
    schema = load_map_from_file(str(examples_dir() / "schema.example.txt"))
    store = MemStore(schema)
    relations: set[str] = set()
    for i in range(n_nodes):
        line = emit_record_line(
            "NPC",
            [f"N{i:04d}", f"name{i}", "t", "0", "c", "0", "active", "persistent"],
        )
        store.upsert(parse_line(line, schema), relations=relations)
    return store


def test_list_records_where_exact_under_budget():
    store = _populate_store(5000)
    t0 = time.perf_counter()
    for _ in range(50):
        rows = store.list_records("NPC", where=[("status", "active")])
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert len(rows) == 5000
    assert elapsed_ms < 2000, f"exact where scan too slow: {elapsed_ms:.1f} ms for 50x5000 rows"


def test_list_records_where_glob_under_budget():
    store = _populate_store(5000)
    t0 = time.perf_counter()
    for _ in range(50):
        rows = store.list_records("NPC", where=[("name", "*name1*")])
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert len(rows) == 1111  # names containing substring "name1"
    assert elapsed_ms < 3000, f"glob where scan too slow: {elapsed_ms:.1f} ms for 50x5000 rows"


def test_list_records_where_and_under_budget():
    store = _populate_store(5000)
    t0 = time.perf_counter()
    for _ in range(50):
        rows = store.list_records(
            "NPC",
            where=[("status", "active"), ("recycle", "persistent")],
        )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert len(rows) == 5000
    assert elapsed_ms < 2000, f"AND where scan too slow: {elapsed_ms:.1f} ms for 50x5000 rows"


def test_neighbors_large_graph_under_budget():
    schema = load_map_from_file(str(examples_dir() / "schema.example.txt"))
    caps = Caps()
    caps.max_rows = 15000
    store = MemStore(schema, caps)
    relations: set[str] = {"links"}
    for i in range(5000):
        line = emit_record_line(
            "NPC",
            [f"N{i:04d}", f"name{i}", "t", "0", "c", "0", "active", "persistent"],
        )
        store.upsert(parse_line(line, schema), relations=relations)
    for i in range(8000):
        src = f"N{i % 5000:04d}"
        dst = f"N{(i + 1) % 5000:04d}"
        line = emit_record_line("EDG", [f"E{i:04d}", src, "links", dst, "", "persistent"])
        store.upsert(parse_line(line, schema), relations=relations)

    t0 = time.perf_counter()
    for _ in range(100):
        result = store.neighbors("N0000", depth=2)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert result
    assert elapsed_ms < 3000, f"indexed neighbors too slow: {elapsed_ms:.1f} ms for 100x depth=2 on 13k rows"
