"""Efficiency regression guards (generous thresholds; not CI timing gates)."""

from __future__ import annotations

import time

from memnet.config import examples_dir
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
    assert elapsed_ms < 500, f"exact where scan too slow: {elapsed_ms:.1f} ms for 50x5000 rows"


def test_list_records_where_glob_under_budget():
    store = _populate_store(5000)
    t0 = time.perf_counter()
    for _ in range(50):
        rows = store.list_records("NPC", where=[("name", "*name1*")])
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert len(rows) == 1111  # names containing substring "name1"
    assert elapsed_ms < 800, f"glob where scan too slow: {elapsed_ms:.1f} ms for 50x5000 rows"


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
    assert elapsed_ms < 600, f"AND where scan too slow: {elapsed_ms:.1f} ms for 50x5000 rows"
