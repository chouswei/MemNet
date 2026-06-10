"""memStore tests."""

from __future__ import annotations

from memnet.mem_store import MemStore
from memnet.models import Record
from memnet.tag_map import load_map_from_lines, parse_line


def _store_with_plr():
    tm = load_map_from_lines(
        [
            "@PLR: id|identity|wealth|cashflow|monopoly|reputation|inventory",
            "@NPC: id|name|traits|corruption|craft|funding_gap|status|recycle",
        ]
    )
    store = MemStore(tm)
    plr = parse_line("@PLR: PLR01|beggar|1|0|0|0|bag", tm)
    npc = parse_line("@NPC: N01|Bob|t|0|c|0|active|persistent", tm)
    store.upsert(plr, relations=set())
    store.upsert(npc, relations=set())
    edg = parse_line("@EDG: E01|N01|seeks_help|PLR01||persistent", tm)
    store.upsert(edg, relations={"seeks_help"})
    return store, tm


def test_dangling_edge_allowed():
    tm = load_map_from_lines(["@PLR: id|identity|wealth|cashflow|monopoly|reputation|inventory"])
    store = MemStore(tm)
    edg = parse_line("@EDG: E99|MISSING|seeks_help|PLR01||persistent", tm)
    warns = store.upsert(edg, relations={"seeks_help"})
    assert warns
    assert store.get("E99") is not None


def test_neighbors_and_path():
    store, _ = _store_with_plr()
    n = store.neighbors("PLR01", depth=2)
    ids = {r.id for r in n}
    assert "N01" in ids
    path = store.find_path("N01", "PLR01")
    assert path


def test_active_only_filters_recyclable():
    store, tm = _store_with_plr()
    npc = parse_line("@NPC: N99|Ghost|t|0|c|0|gone|delete_on_settle", tm)
    store.upsert(npc, relations=set())
    rows = store.context_pack(anchor_id="PLR01", active_only=True)
    assert all(r.id != "N99" for r in rows)


def test_edge_index_maintained_on_update_and_delete():
    store, tm = _store_with_plr()
    assert {e.id for e in store._edges_from("N01")} == {"E01"}
    assert {e.id for e in store._edges_to("PLR01")} == {"E01"}

    updated = parse_line("@EDG: E01|PLR01|seeks_help|N01||persistent", tm)
    store.replace_row(updated, relations={"seeks_help"})
    assert store._edges_from("N01") == []
    assert {e.id for e in store._edges_from("PLR01")} == {"E01"}
    assert {e.id for e in store._edges_to("N01")} == {"E01"}

    store.delete("E01")
    assert store._edges_by_src == {}
    assert store._edges_by_dist == {}


def test_edge_index_rebuilt_on_load_records():
    store, tm = _store_with_plr()
    records = [store.by_id[rid] for rid in store.write_order]
    reloaded = MemStore(tm)
    reloaded.load_records(records)
    assert {e.id for e in reloaded._edges_from("N01")} == {"E01"}
    assert {e.id for e in reloaded._edges_to("PLR01")} == {"E01"}
