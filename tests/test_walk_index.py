"""Adjacency index (node, type, direction) for typed walks: exact on every write.

Red-first for symphony typed-walks (M1, node P-index; score §1 D3, D6, D8).
Pinned interface (lands in ENG):
``MemStore.typed_edges(node_hid, relation, direction) -> list[Record]``
(relation already standard; "out" = src is the node, "in" = dist is the node,
"both" = out and in merged, a self-loop once; order = edge first-insert
sequence, which is the RecordTable dict order). ``verify_indexes()`` also checks
the adjacency index (``adjacency index differs: ...``). ``memnet.typed_walk``
holds ``typed_walk`` and ``WalkResult``. The index is never written to a
snapshot, and a refused batch rolls back order-exact.

New names are looked up inside test bodies so collection never fails on 4b8ed16.
"""

from __future__ import annotations

import copy
import json
import pickle
import random
from pathlib import Path

import pytest

from memnet.config import standard_relation
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.snapshot import snapshot_text

_MAP = [
    "SCHEMA PRT ; fields=id name role",
    "SCHEMA MOD ; fields=id path note",
    "SCHEMA SYM ; fields=id kind refdes",
]
_DIRS = ("out", "in", "both")
TOKEN = "test-admin-token"


def _apply(ss, *stmts, mode="mutate"):
    return MutateGate(ss).apply(list(stmts), mode=mode, allow_new_relation=True)


def _extras(n: int) -> str:
    return ", ".join(f"x{i:03d}: 'v{i:03d}'" for i in range(n))


_OVER_FIELDS = f"CREATE (:PRT {{id: 'N_OVER', name: 'a', role: 'b', {_extras(62)}}})"


def _hid(store, nick: str) -> str:
    (rec,) = store.match_nickname(nick)
    return rec.hid


def _scan(store, hid: str, rel: str, direction: str) -> list:
    """Brute force: every EDG in dict (first-insert) order, filtered on type and end."""
    out = []
    for rec in dict.values(store._by_hid):
        if rec.tag != "EDG" or standard_relation(rec.fields.get("relation", "")) != rel:
            continue
        src, dist = rec.fields.get("src", ""), rec.fields.get("dist", "")
        if (
            (direction == "out" and src == hid)
            or (direction == "in" and dist == hid)
            or (direction == "both" and hid in (src, dist))
        ):
            out.append(rec)
    return out


def _assert_adj(store) -> None:
    """verify_indexes() is clean and typed_edges equals the scan for every key."""
    assert store.verify_indexes() == []
    by_hid = store._by_hid
    edges = [r for r in dict.values(by_hid) if r.tag == "EDG"]
    hids = {h for h, r in dict.items(by_hid) if r.tag != "EDG"}
    for e in edges:
        hids.update(x for x in (e.fields.get("src"), e.fields.get("dist")) if x)
    hids.add("__absent__")
    rels = {standard_relation(e.fields.get("relation", "")) for e in edges} | {"replaces"}
    for hid in sorted(hids):
        for rel in sorted(rels):
            for d in _DIRS:
                got = store.typed_edges(hid, rel, d)
                want = _scan(store, hid, rel, d)
                assert [r.hid for r in got] == [r.hid for r in want], (hid, rel, d)
                assert all(a is b for a, b in zip(got, want, strict=True)), (hid, rel, d)


def _body(ss) -> str:
    """Snapshot text without the @SNAP clock line (it moves on any touch)."""
    return "\n".join(ln for ln in snapshot_text(ss).splitlines() if not ln.startswith("@SNAP:"))


def _star(ss) -> None:
    """X-[:partOf]->A,B,C (E_A, E_B, E_C) plus other types and directions."""
    _apply(ss, *[f"CREATE (:PRT {{id: '{n}', name: 'n{n}', role: 'r'}})" for n in "XABCD"])
    _apply(
        ss,
        "MATCH (a {id: 'X'}), (b {id: 'A'}) CREATE (a)-[:partOf {id: 'E_A'}]->(b)",
        "MATCH (a {id: 'X'}), (b {id: 'B'}) CREATE (a)-[:partOf {id: 'E_B'}]->(b)",
        "MATCH (a {id: 'X'}), (b {id: 'C'}) CREATE (a)-[:partOf {id: 'E_C'}]->(b)",
        "MATCH (a {id: 'D'}), (b {id: 'X'}) CREATE (a)-[:partOf {id: 'E_DX'}]->(b)",
        "MATCH (a {id: 'X'}), (b {id: 'D'}) CREATE (a)-[:cites {id: 'E_XD'}]->(b)",
        "MATCH (a {id: 'A'}), (b {id: 'X'}) CREATE (a)-[:IN_SESSION {id: 'E_AX'}]->(b)",
        "MATCH (a {id: 'B'}), (b {id: 'B'}) CREATE (a)-[:partOf {id: 'E_BB'}]->(b)",
        "MATCH (a {id: 'X'}), (b {id: 'A'}) CREATE (a)-[:partOf {id: 'E_A2'}]->(b)",
    )


@pytest.fixture
def star(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _star(ss)
    return ss


def _nicks(recs) -> list[str]:
    return [r.fields.get("id") for r in recs]


# --- typed_edges basics ---------------------------------------------------------


def test_typed_edges_by_type_and_direction(star):
    store = star.store
    x = _hid(store, "X")
    assert _nicks(store.typed_edges(x, "partOf", "out")) == ["E_A", "E_B", "E_C", "E_A2"]
    assert _nicks(store.typed_edges(x, "partOf", "in")) == ["E_DX"]
    assert _nicks(store.typed_edges(x, "partOf", "both")) == [
        "E_A",
        "E_B",
        "E_C",
        "E_DX",
        "E_A2",
    ]
    assert _nicks(store.typed_edges(x, "cites", "out")) == ["E_XD"]
    assert store.typed_edges(x, "cites", "in") == []
    # IN_SESSION was folded on write and is indexed under the standard name
    assert _nicks(store.typed_edges(x, "inSession", "in")) == ["E_AX"]
    assert store.typed_edges(x, "replaces", "both") == []
    # a self-loop is out and in, but once under both
    b = _hid(store, "B")
    assert _nicks(store.typed_edges(b, "partOf", "out")) == ["E_BB"]
    assert _nicks(store.typed_edges(b, "partOf", "in")) == ["E_B", "E_BB"]
    assert _nicks(store.typed_edges(b, "partOf", "both")) == ["E_B", "E_BB"]
    assert store.typed_edges("__absent__", "partOf", "both") == []
    _assert_adj(store)


def test_legacy_raw_relation_spelling_is_indexed_standard(memnet_temp):
    from memnet.models import Record

    ss = open_session(map_lines=list(_MAP))
    store = ss.store
    store.load_records(
        [
            Record(tag="PRT", fields={"id": "P", "name": "p", "role": "r"}, hid="h_p"),
            Record(tag="PRT", fields={"id": "Q", "name": "q", "role": "r"}, hid="h_q"),
            Record(
                tag="EDG",
                fields={"id": "E1", "src": "h_p", "relation": "PART_OF", "dist": "h_q"},
                hid="h_e1",
            ),
            Record(
                tag="EDG",
                fields={"id": "E2", "src": "h_p", "relation": "PartOf", "dist": "h_q"},
                hid="h_e2",
            ),
        ]
    )
    assert _nicks(store.typed_edges("h_p", "partOf", "out")) == ["E1", "E2"]
    assert _nicks(store.typed_edges("h_q", "partOf", "in")) == ["E1", "E2"]
    _assert_adj(store)


# --- every write path -------------------------------------------------------------


def test_adj_after_create_delete_and_relationship_set(star):
    store = star.store
    _assert_adj(store)
    _apply(star, "MATCH (a {id: 'C'}), (b {id: 'X'}) CREATE (a)-[:partOf {id: 'E_CX'}]->(b)")
    _assert_adj(store)
    _apply(star, "MATCH ()-[r {id: 'E_B'}]-() DELETE r")
    assert "E_B" not in _nicks(store.typed_edges(_hid(store, "X"), "partOf", "out"))
    _assert_adj(store)
    _apply(star, "MATCH (a {id: 'X'})-[r:cites]->(b {id: 'D'}) DELETE r")
    assert store.typed_edges(_hid(store, "X"), "cites", "out") == []
    _assert_adj(store)
    _apply(star, "MATCH ()-[r {id: 'E_C'}]-() SET r.kind = 'b'")
    (e_c,) = store.typed_edges(_hid(store, "C"), "partOf", "in")
    assert e_c is store.resolve_one("E_C")
    _assert_adj(store)


def test_adj_after_detach_delete(star):
    from memnet.typed_walk import typed_walk

    store = star.store
    _apply(star, "MATCH (n {id: 'A'}) DETACH DELETE n")
    assert store.match_nickname("A") == []
    _assert_adj(store)  # whatever edges stay stored stay indexed, nothing more
    rows = typed_walk(store, start="X", relation="partOf", direction="out").paths
    assert [p.end.fields.get("id") for p in rows] == ["B", "C"]
    _apply(star, "MATCH (n {id: 'X'}) DETACH DELETE n")
    _assert_adj(store)
    assert typed_walk(store, start="D", relation="partOf", direction="both").paths == ()
    assert typed_walk(store, start="B", relation="partOf", direction="in").paths == ()


def test_adj_after_rename_and_rename_merge(star):
    store = star.store
    x = _hid(store, "X")
    _apply(star, "MATCH (n {id: 'X'}) SET n.id = 'X_renamed'", mode="update")
    assert _nicks(store.typed_edges(x, "partOf", "out")) == ["E_A", "E_B", "E_C", "E_A2"]
    _assert_adj(store)
    # merge C into A: C's in edge E_C is retargeted onto A in place
    a, c = _hid(store, "A"), _hid(store, "C")
    store.rename_id("C", "A", merge=True)
    assert c not in store._by_hid
    assert _nicks(store.typed_edges(a, "partOf", "in")) == ["E_A", "E_C", "E_A2"]
    assert store.typed_edges(c, "partOf", "in") == []
    _assert_adj(store)


def test_adj_after_same_thing_absorb(star):
    store = star.store
    keep, drop = _hid(store, "D"), _hid(store, "A")
    _apply(
        star,
        "MATCH (a:PRT {name: 'nD'}), (b:PRT {name: 'nA'})\nSET a += b",
        mode="update",
    )
    assert drop not in store._by_hid
    assert keep in store._by_hid
    # X's partOf edges to A now end on the survivor (absorb may fold the parallel pair)
    x = _hid(store, "X")
    moved = [e for e in store.typed_edges(keep, "partOf", "in") if e.fields["src"] == x]
    assert {e.fields.get("id") for e in moved} & {"E_A", "E_A2"}
    assert store.typed_edges(drop, "partOf", "both") == []
    _assert_adj(store)


def test_verify_flags_in_place_endpoint_edit_and_reindex_repairs(star):
    store = star.store
    _assert_adj(store)
    edge = store.resolve_one("E_C")
    d = _hid(store, "D")
    edge.fields["dist"] = d  # bypasses every mutator
    problems = store.verify_indexes()
    assert any(p.startswith("adjacency index differs") for p in problems), problems
    store.reindex(edge.hid)
    assert "E_C" in _nicks(store.typed_edges(d, "partOf", "in"))
    assert "E_C" not in _nicks(store.typed_edges(_hid(store, "C"), "partOf", "in"))
    _assert_adj(store)


def test_adj_after_snapshot_save_load(star, tmp_path: Path):
    from memnet.snapshot import load_snapshot, write_snapshot

    _assert_adj(star.store)
    path = tmp_path / "adj.snap"
    write_snapshot(star, path)
    loaded = load_snapshot(path)
    store = loaded.store
    assert _nicks(store.typed_edges(_hid(store, "X"), "partOf", "out")) == [
        "E_A",
        "E_B",
        "E_C",
        "E_A2",
    ]
    _assert_adj(store)


def test_adj_after_checkpoint_restore(star, monkeypatch, tmp_path: Path):
    from memnet.checkpoint import MANIFEST_NAME, run_checkpoint
    from memnet.snapshot import load_snapshot_text, materialise_snapshot_text

    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    result = run_checkpoint(TOKEN, directory=tmp_path)
    assert result.exit_code == 0
    dest = tmp_path / "checkpoint"
    manifest = json.loads((dest / MANIFEST_NAME).read_text(encoding="utf-8"))
    row = next(r for r in manifest["sessions"] if r["session_id"] == star.session_id)
    text = (dest / row["file"]).read_text(encoding="utf-8")
    for restored in (materialise_snapshot_text(text), load_snapshot_text(text)):
        store = restored.store
        assert _nicks(store.typed_edges(_hid(store, "X"), "partOf", "both")) == [
            "E_A",
            "E_B",
            "E_C",
            "E_DX",
            "E_A2",
        ]
        _assert_adj(store)


def test_adj_after_bypass_import_over_line_cap(star):
    from memnet.import_absorb import (
        absorb_working_memory_slice,
        export_working_memory_slice,
        reset_import_guard_for_tests,
    )

    reset_import_guard_for_tests()
    member = open_session(map_lines=list(_MAP))
    _apply(
        member,
        f"CREATE (:MOD {{id: 'MOD_a', path: '{'p' * 60}', note: '{'n' * 60}'}})",
        "CREATE (:SYM {id: 'SYM_b', kind: 'k', refdes: 'r'})",
        "MATCH (a {id: 'MOD_a'}), (b {id: 'SYM_b'}) CREATE (a)-[:partOf {id: 'E_ab'}]->(b)",
    )
    store = star.store
    before = (list(store.write_order), list(store._by_hid), _body(star))
    star.caps.max_line_bytes = 100
    with pytest.raises(MemNetError) as ei:
        absorb_working_memory_slice(
            star,
            export_working_memory_slice(member, anchors=["MOD_a"], depth=2),
            enable_guard=False,
        )
    reset_import_guard_for_tests()
    assert ei.value.code == "limit_exceeded"
    assert (list(store.write_order), list(store._by_hid), _body(star)) == before
    assert store.match_nickname("E_ab") == []
    _assert_adj(store)


def test_adj_after_bypass_guard_rollback(star):
    from memnet.bypass_caps import bypass_guard
    from memnet.models import Record

    store = star.store
    x, d = _hid(store, "X"), _hid(store, "D")
    with pytest.raises(MemNetError):
        with bypass_guard(star):
            store.upsert(
                Record(tag="EDG", fields={"id": "E_new", "src": x, "relation": "partOf", "dist": d})
            )
            store.delete(store.resolve_one("E_A").hid)
            _assert_adj(store)
            raise MemNetError("limit_exceeded", "test|1/0")
    assert _nicks(store.typed_edges(x, "partOf", "out")) == ["E_A", "E_B", "E_C", "E_A2"]
    _assert_adj(store)


def test_adj_survives_copy_deepcopy_pickle(star):
    store = star.store
    _assert_adj(store)
    x = _hid(store, "X")
    want = _nicks(store.typed_edges(x, "partOf", "out"))
    clones = [copy.deepcopy(store), pickle.loads(pickle.dumps(store))]
    for table in (copy.copy(store._by_hid), copy.deepcopy(store._by_hid)):
        assert type(table) is type(store._by_hid)
        clone = copy.copy(store)
        clone._by_hid = table
        clones.append(clone)
    for clone in clones:
        assert _nicks(clone.typed_edges(x, "partOf", "out")) == want
        assert clone.verify_indexes() == []
        # the clone's index is its own: a delete there leaves the original alone
        clone._by_hid.pop(clone.resolve_one("E_B").hid)
        assert "E_B" not in _nicks(clone.typed_edges(x, "partOf", "out"))
        assert _nicks(store.typed_edges(x, "partOf", "out")) == want
    _assert_adj(store)


# --- order-exact rollback (D6, D8) --------------------------------------------------


def _store_order(ss) -> tuple:
    store = ss.store
    return list(store.write_order), list(dict.keys(store._by_hid)), _body(ss)


_REFUSED = {
    "edge_delete_field_cap": (["MATCH ()-[r {id: 'E_A'}]-() DELETE r", _OVER_FIELDS], None),
    "edge_delete_line_cap": (
        [
            "MATCH ()-[r {id: 'E_A'}]-() DELETE r",
            f"CREATE (:PRT {{id: 'N_LONG', name: '{'a' * 70}', role: '{'b' * 70}'}})",
        ],
        120,
    ),
    "edge_delete_by_ends_field_cap": (
        ["MATCH (a {id: 'X'})-[r:partOf]->(b {id: 'B'}) DELETE r", _OVER_FIELDS],
        None,
    ),
    "detach_delete_node_field_cap": (["MATCH (n {id: 'A'}) DETACH DELETE n", _OVER_FIELDS], None),
}


@pytest.mark.parametrize("case", sorted(_REFUSED))
def test_refused_batch_rollback_is_order_exact(star, case):
    stmts, line_cap = _REFUSED[case]
    store = star.store
    x = _hid(store, "X")
    before = _store_order(star)
    want_edges = ["E_A", "E_B", "E_C", "E_A2"]
    if line_cap is not None:
        star.caps.max_line_bytes = line_cap
    with pytest.raises(MemNetError) as ei:
        _apply(star, *stmts)
    assert ei.value.code == "limit_exceeded"
    after = _store_order(star)
    assert after[0] == before[0], "write_order changed by a refused batch"
    assert after[1] == before[1], "RecordTable dict order changed by a refused batch"
    assert after[2] == before[2], "snapshot text changed by a refused batch"
    from memnet.typed_walk import typed_walk

    assert _nicks(store.typed_edges(x, "partOf", "out")) == want_edges
    res = typed_walk(store, start="X", relation="partOf", direction="out")
    assert [p.end.fields.get("id") for p in res.paths] == ["A", "B", "C"]
    assert [p.steps[0].edge.fields.get("id") for p in res.paths] == ["E_A", "E_B", "E_C"]
    _assert_adj(store)


def test_refused_batch_rollback_keeps_walk_rows_from_both_ends(star):
    from memnet.typed_walk import typed_walk

    store = star.store
    rows = {
        (n, d): [
            p.end.hid for p in typed_walk(store, start=n, relation="partOf", direction=d).paths
        ]
        for n in "XAD"
        for d in _DIRS
    }
    with pytest.raises(MemNetError):
        _apply(
            star,
            "MATCH ()-[r {id: 'E_A'}]-() DELETE r",
            "MATCH ()-[r {id: 'E_DX'}]-() DELETE r",
            "MATCH (n {id: 'B'}) DETACH DELETE n",
            _OVER_FIELDS,
        )
    for (n, d), want in rows.items():
        got = [p.end.hid for p in typed_walk(store, start=n, relation="partOf", direction=d).paths]
        assert got == want, (n, d)
    _assert_adj(store)


# --- the index is never stored ----------------------------------------------------

# Records section of the star graph's snapshot as written on 4b8ed16 (no index).
_STAR_RECORDS = [
    "@PRT: X|nX|r",
    "@PRT: A|nA|r",
    "@PRT: B|nB|r",
    "@PRT: C|nC|r",
    "@PRT: D|nD|r",
    "@EDG: E_A|X|partOf|A|||persistent",
    "@EDG: E_B|X|partOf|B|||persistent",
    "@EDG: E_C|X|partOf|C|||persistent",
    "@EDG: E_DX|D|partOf|X|||persistent",
    "@EDG: E_XD|X|cites|D|||persistent",
    "@EDG: E_AX|A|inSession|X|||persistent",
    "@EDG: E_BB|B|partOf|B|||persistent",
    "@EDG: E_A2|X|partOf|A|||persistent",
]
_SNAP_LINE_PREFIXES = ("# ", "#@ACL:", "SCHEMA ", "@REL: ", "@PRT: ", "@EDG: ")


def test_index_is_never_written_to_a_snapshot(star, tmp_path: Path):
    from memnet.snapshot import load_snapshot, write_snapshot

    _assert_adj(star.store)  # the index exists and is in use
    body = _body(star)
    lines = body.splitlines()
    assert lines[lines.index("# records") + 1 :] == _STAR_RECORDS
    assert lines[lines.index("# map") + 1 : lines.index("# relations")] == [
        "SCHEMA EDG ; fields=id src relation dist at attrs recycle",
        "SCHEMA LAW ; fields=id name cycle mechanism constraint",
        *sorted(_MAP),
    ]
    assert all(ln.startswith(_SNAP_LINE_PREFIXES) or ln == "" for ln in lines), lines
    # after a typed read, a save, a load and a re-save the text is byte-equal
    star.store.typed_edges(_hid(star.store, "X"), "partOf", "both")
    assert _body(star) == body
    path = tmp_path / "never.snap"
    write_snapshot(star, path)
    loaded = load_snapshot(path)
    _assert_adj(loaded.store)
    assert _body(loaded) == body


# --- seeded random op sequence ------------------------------------------------------


def test_seeded_random_op_sequence_keeps_adjacency(memnet_temp):
    from memnet.bypass_caps import bypass_guard
    from memnet.models import Record

    rng = random.Random(247)
    ss = open_session(map_lines=list(_MAP))
    store = ss.store
    rels = ["partOf", "PART_OF", "cites", "IN_SESSION", "replaces"]
    fresh = iter(range(10_000))
    _assert_adj(store)

    def nick() -> str:
        """A live node nickname (rarely a dead or duplicate one, which may refuse)."""
        live = sorted({r.fields.get("id") for r in dict.values(store._by_hid) if r.tag != "EDG"})
        return rng.choice(live) if live and rng.random() < 0.95 else "N_gone"

    def new_nick() -> str:
        return f"N{next(fresh)}"

    def edge_nick() -> str:
        eids = [r.fields.get("id") for r in dict.values(store._by_hid) if r.tag == "EDG"]
        return rng.choice(eids) if eids else "E_none"

    def node_hid() -> str:
        hids = [h for h, r in dict.items(store._by_hid) if r.tag != "EDG"]
        return rng.choice(hids) if hids else "__absent__"

    def op_create() -> None:
        _apply(ss, f"CREATE (:PRT {{id: '{new_nick()}', name: 'g{rng.randrange(6)}', role: 'r'}})")

    def op_link() -> None:
        _apply(
            ss,
            f"MATCH (a {{id: '{nick()}'}}), (b {{id: '{nick()}'}}) "
            f"CREATE (a)-[:{rng.choice(rels)}]->(b)",
        )

    def op_delete_edge() -> None:
        _apply(ss, f"MATCH ()-[r {{id: '{edge_nick()}'}}]-() DELETE r")

    def op_set_edge() -> None:
        _apply(ss, f"MATCH ()-[r {{id: '{edge_nick()}'}}]-() SET r.kind = 'k{rng.randrange(3)}'")

    def op_detach() -> None:
        _apply(ss, f"MATCH (n {{id: '{nick()}'}}) DETACH DELETE n")

    def op_rename() -> None:
        _apply(ss, f"MATCH (n {{id: '{nick()}'}}) SET n.id = '{new_nick()}'", mode="update")

    def op_rename_merge() -> None:
        store.rename_id(nick(), nick(), merge=True)

    def op_absorb() -> None:
        a, b = rng.randrange(6), rng.randrange(6)
        _apply(
            ss,
            f"MATCH (a:PRT {{name: 'g{a}'}}), (b:PRT {{name: 'g{b}'}})\nSET a += b",
            mode="update",
        )

    def op_refused() -> None:
        _apply(
            ss,
            f"MATCH ()-[r {{id: '{edge_nick()}'}}]-() DELETE r",
            f"MATCH (a {{id: '{nick()}'}}), (b {{id: '{nick()}'}}) CREATE (a)-[:cites]->(b)",
            _OVER_FIELDS,
        )

    def op_bypass() -> None:
        with bypass_guard(ss):
            store.upsert(
                Record(
                    tag="EDG",
                    fields={
                        "src": node_hid(),
                        "relation": rng.choice(rels[:2]),
                        "dist": node_hid(),
                    },
                )
            )
            eids = [h for h, r in dict.items(store._by_hid) if r.tag == "EDG"]
            if eids:
                store.delete(rng.choice(eids))
            raise MemNetError("limit_exceeded", "test|1/0")

    def op_in_place_retarget() -> None:
        eids = [h for h, r in dict.items(store._by_hid) if r.tag == "EDG"]
        if eids:
            edge = store._by_hid[rng.choice(eids)]
            edge.fields[rng.choice(["src", "dist"])] = node_hid()
            store.reindex(edge.hid)
            store.mark_dirty(edge.hid)

    ops = [
        (op_create, 6),
        (op_link, 8),
        (op_delete_edge, 3),
        (op_set_edge, 2),
        (op_detach, 2),
        (op_rename, 3),
        (op_rename_merge, 1),
        (op_absorb, 1),
        (op_refused, 2),
        (op_bypass, 1),
        (op_in_place_retarget, 1),
    ]
    funcs = [f for f, _w in ops]
    weights = [w for _f, w in ops]
    done = 0
    capped = 0
    for step in range(320):
        op = rng.choices(funcs, weights=weights)[0]
        order_before = (list(store.write_order), list(dict.keys(store._by_hid)))
        code = None
        try:
            op()
            done += 1
        except MemNetError as exc:
            code = exc.code
        try:
            if op is op_refused and code == "limit_exceeded":
                capped += 1
                assert (list(store.write_order), list(dict.keys(store._by_hid))) == order_before
            _assert_adj(store)
        except AssertionError as exc:
            raise AssertionError(f"step {step} after {op.__name__}: {exc}") from exc
    assert done > 150
    assert capped >= 5
    assert sum(1 for r in dict.values(store._by_hid) if r.tag == "EDG") > 10
