"""Hot-spot fixes keep behaviour (redesign step 1, no wire change).

1. Edge ids minted without a client id are the same ids the 0.20.7 allocator
   picks, on every sequence: mixed explicit ids (several prefixes, nodes that
   carry ``E<n>`` ids), deletes (the top id included), refused batches, import
   of id-less edges, save/load and checkpoint restore mid-sequence. The oracle
   is a copy of the 0.20.7 seeding (whole nickname set + regex scan), run on a
   twin session.
2. Recall order with the rank-key cache equals a cold rebuild (cache off), byte
   for byte, while writes and reads interleave: SET on an edge's endpoint,
   delete, rename, refused batch, import.
3. A finished session load freezes the GC heap (a 100k session is ~0.58M tracked
   objects; a full collection over them costs ~120 ms).

The id oracle checks equality with the old algorithm only; it never asserts an
id's value, order or sequence (ids stay opaque).
"""

from __future__ import annotations

import gc
import json
import random
import re
import weakref
from pathlib import Path

import pytest

from memnet.exceptions import MemNetError
from memnet.id_allocator import IdAllocator
from memnet.mem_store import MemStore
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

TOKEN = "test-admin-token"
_MAP = [
    "SCHEMA PRT ; fields=id name role",
    "SCHEMA TSK ; fields=id goal status recycle",
]

# --- oracle: the 0.20.7 edge-id allocator (copied, frozen) ---------------------

_OLD_NUM_SUFFIX = re.compile(r"^([A-Za-z_]+)(\d+)$")


class _OldIdAllocator:
    """IdAllocator.__init__/observe/mint as at 4a10ba1 (seed = scan of every id)."""

    def __init__(self, existing_ids: set[str]) -> None:
        self._used = set(existing_ids)
        self._seq: dict[str, int] = {}
        for rid in self._used:
            m = _OLD_NUM_SUFFIX.match(rid)
            if m:
                prefix, n = m.group(1), int(m.group(2))
                if n > self._seq.get(prefix, 0):
                    self._seq[prefix] = n

    def observe(self, rid: str) -> None:
        if rid and rid != "NEW":
            self._used.add(rid)
            m = _OLD_NUM_SUFFIX.match(rid)
            if m:
                prefix, n = m.group(1), int(m.group(2))
                self._seq[prefix] = max(self._seq.get(prefix, 0), n)

    def mint(self, prefix: str) -> str:
        prefix = prefix or "N"
        n = self._seq.get(prefix, 0) + 1
        while f"{prefix}{n}" in self._used:
            n += 1
        self._seq[prefix] = n
        rid = f"{prefix}{n}"
        self._used.add(rid)
        return rid


def _old_used(store, extra) -> set[str]:
    """The 0.20.7 seed set (MemStore.nickname_set + batch ids), rebuilt from the rows."""
    used = {r.fields["id"] for r in dict.values(store._by_hid) if r.fields.get("id")}
    used.update(f"{p}{n}" for p, n in store.id_high_water().items())
    used.update(extra)
    return used


def _use_old_allocator(m, store) -> None:
    """Every high-water mint on ``store`` (mutate, pipe edges, import) uses the oracle."""
    m.setattr(
        IdAllocator,
        "from_high_water",
        classmethod(lambda cls, hw, extra=(): _OldIdAllocator(_old_used(store, extra))),
    )


def _apply(ss, *stmts, mode="mutate"):
    return MutateGate(ss).apply(list(stmts), mode=mode, allow_new_relation=True)


def _edge_state(ss) -> list[tuple[str, str, str, str]]:
    """(id, relation, src nick, dist nick) of every edge, in write order."""
    store = ss.store
    out = []
    for hid in store.write_order:
        rec = store._by_hid[hid]
        if rec.tag != "EDG":
            continue
        src = store.resolve_one(rec.fields.get("src", ""))
        dist = store.resolve_one(rec.fields.get("dist", ""))
        out.append(
            (
                rec.fields.get("id", ""),
                rec.fields.get("relation", ""),
                src.fields.get("id", "") if src else "",
                dist.fields.get("id", "") if dist else "",
            )
        )
    return out


def _save_load(ss, tmp_path: Path, tag: str):
    from memnet.snapshot import load_snapshot, write_snapshot

    path = tmp_path / f"{tag}.snap"
    write_snapshot(ss, path)
    out = load_snapshot(path)
    path.unlink()
    return out


def _checkpoint_restore(pair, monkeypatch, tmp_path: Path, step: int):
    from memnet.checkpoint import MANIFEST_NAME, run_checkpoint
    from memnet.snapshot import load_snapshot_text

    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    dest_root = tmp_path / f"ckpt{step}"
    result = run_checkpoint(TOKEN, directory=dest_root)
    assert result.exit_code == 0
    dest = dest_root / "checkpoint"
    manifest = json.loads((dest / MANIFEST_NAME).read_text(encoding="utf-8"))
    out = []
    for ss in pair:
        row = next(r for r in manifest["sessions"] if r["session_id"] == ss.session_id)
        out.append(load_snapshot_text((dest / row["file"]).read_text(encoding="utf-8")))
    return out


def _source_with_id_less_edges():
    """A session holding legacy id-less edges (as a snapshot may carry them)."""
    from memnet.snapshot import load_snapshot_text, snapshot_text

    src = open_session(map_lines=list(_MAP))
    _apply(src, "CREATE (:PRT {id: 'Q0', name: 'q0', role: 'imp'})")
    _apply(src, "CREATE (:PRT {id: 'Q1', name: 'q1', role: 'imp'})")
    _apply(src, "MATCH (a {id: 'Q0'}), (b {id: 'Q1'}) CREATE (a)-[:links]->(b)")
    _apply(src, "MATCH (a {id: 'Q1'}), (b {id: 'Q0'}) CREATE (a)-[:knows]->(b)")
    text = re.sub(r"(?m)^@EDG: E\d+\|", "@EDG: |", snapshot_text(src))
    out = load_snapshot_text(text)
    assert [e[0] for e in _edge_state(out)] == ["", ""]
    return out


@pytest.mark.parametrize("seed", [1, 7, 42, 2026])
def test_minted_edge_ids_match_old_allocator(memnet_temp, monkeypatch, tmp_path, seed):
    from memnet.import_absorb import import_slice

    rng = random.Random(seed)
    # pair[0] runs the 0.20.7 allocator (oracle), pair[1] the code under test.
    pair = [open_session(map_lines=list(_MAP)) for _ in range(2)]
    source = _source_with_id_less_edges()
    nodes = [f"P{i}" for i in range(6)]
    # Nodes whose ids share the edge prefix, plus other prefixes and leading zeros.
    odd_nodes = ["E40", "E007", "Ex", "N3", "E_9"]
    for ss in pair:
        _apply(ss, *[f"CREATE (:PRT {{id: '{n}', name: 'n{n}', role: 'r'}})" for n in nodes])

    def ends() -> tuple[str, str]:
        return rng.choice(nodes), rng.choice(nodes)

    def op_link(k: int = 1) -> list[list[str]]:
        out = []
        for _ in range(k):
            a, b = ends()
            out.append(f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) CREATE (a)-[:links]->(b)")
        return [out]

    def op_link_batch() -> list[list[str]]:
        return op_link(rng.randrange(2, 5))

    def op_link_explicit() -> list[list[str]]:
        a, b = ends()
        eid = rng.choice(["E1", "E5", "E12", "E30", "E099", "Ezz", "F2", "E_3"])
        a2, b2 = ends()
        # One explicit id plus one minted in the same batch (the batch id seeds the mint).
        return [
            [
                f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) "
                f"CREATE (a)-[:links {{id: '{eid}'}}]->(b)",
                f"MATCH (a {{id: '{a2}'}}), (b {{id: '{b2}'}}) CREATE (a)-[:links]->(b)",
            ]
        ]

    def op_odd_node() -> list[list[str]]:
        nick = rng.choice(odd_nodes)
        return [[f"CREATE (:TSK {{id: '{nick}', goal: 'g'}})"]]

    def op_delete_top() -> list[list[str]]:
        ids = [e[0] for e in _edge_state(pair[1])]
        nums = [(int(i[1:]), i) for i in ids if re.fullmatch(r"E\d+", i)]
        if not nums:
            return []
        top = max(nums)[1]
        return [[f"MATCH ()-[r {{id: '{top}'}}]-() DELETE r"]]

    def op_delete_any() -> list[list[str]]:
        ids = [e[0] for e in _edge_state(pair[1])]
        if not ids:
            return []
        return [[f"MATCH ()-[r {{id: '{rng.choice(ids)}'}}]-() DELETE r"]]

    def op_delete_odd_node() -> list[list[str]]:
        return [[f"MATCH (n {{id: '{rng.choice(odd_nodes)}'}}) DETACH DELETE n"]]

    def op_refused() -> list[list[str]]:
        a, b = ends()
        # Mints an id, then the batch is refused on an unknown node: rolled back.
        return [
            [
                f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) CREATE (a)-[:links]->(b)",
                "MATCH (n:PRT {id: 'NOPE'}) SET n.role = 'x'",
            ]
        ]

    def op_import():
        # The source's edges carry no id: the import mints them in the lead.
        def run(ss):
            res = import_slice(
                lead_session_id=ss.session_id,
                source_session_id=source.session_id,
                anchors=["Q0"],
                id_policy=rng_policy,
                enable_guard=False,
            )
            return getattr(res, "ack_lines", None) or repr(getattr(res, "warnings", ""))

        rng_policy = rng.choice(["keep", "remint"])
        return [run]

    ops = [
        (op_link, 6),
        (op_link_batch, 2),
        (op_link_explicit, 2),
        (op_odd_node, 2),
        (op_delete_top, 2),
        (op_delete_any, 2),
        (op_delete_odd_node, 1),
        (op_refused, 1),
        (op_import, 1),
    ]
    funcs, weights = [f for f, _ in ops], [w for _, w in ops]
    minted_seen = 0
    imports_ok = 0
    for step in range(160):
        if step in (60, 120):
            pair = [_save_load(ss, tmp_path, f"s{step}_{i}") for i, ss in enumerate(pair)]
        if step in (40, 100):
            pair = _checkpoint_restore(pair, monkeypatch, tmp_path, step)
        op = rng.choices(funcs, weights=weights)[0]
        for stmts in op():
            outcomes = []
            for i, ss in enumerate(pair):
                with monkeypatch.context() as m:
                    if i == 0:
                        _use_old_allocator(m, ss.store)
                    try:
                        if callable(stmts):
                            outcomes.append(("ok", stmts(ss)))
                        else:
                            acks = _apply(ss, *stmts).ack_lines
                            # ``_elN`` handles are per session; endpoints are compared below.
                            outcomes.append(("ok", [re.sub(r"_el\d+", "_el", a) for a in acks]))
                    except MemNetError as exc:
                        outcomes.append(("err", exc.code))
            assert outcomes[0] == outcomes[1], (step, op.__name__, outcomes)
            if callable(stmts) and outcomes[0][0] == "ok":
                imports_ok += 1
            old, new = _edge_state(pair[0]), _edge_state(pair[1])
            assert old == new, (step, op.__name__)
            assert pair[0].store.id_high_water() == pair[1].store.id_high_water()
            minted_seen = max(minted_seen, len(new))
    assert minted_seen > 10
    assert imports_ok > 0


def test_pipe_edge_mint_matches_old_allocator(memnet_temp, monkeypatch):
    """Legacy id-less edge rows go through the same allocator (``_mint_pipe_edge_ids``)."""
    from memnet.models import Record

    pair = [open_session(map_lines=list(_MAP)) for _ in range(2)]
    for ss in pair:
        _apply(ss, "CREATE (:PRT {id: 'A', name: 'a', role: 'r'})")
        _apply(ss, "CREATE (:PRT {id: 'E9', name: 'b', role: 'r'})")
    minted = []
    for i, ss in enumerate(pair):
        recs = [
            Record(tag="EDG", fields={"id": "E4", "src": "A", "dist": "E9", "relation": "links"}),
            Record(tag="EDG", fields={"src": "A", "dist": "E9", "relation": "links"}),
            Record(tag="EDG", fields={"src": "E9", "dist": "A", "relation": "links"}),
        ]
        with monkeypatch.context() as m:
            if i == 0:
                _use_old_allocator(m, ss.store)
            MutateGate(ss)._mint_pipe_edge_ids(recs)
        minted.append([r.fields["id"] for r in recs])
    assert minted[0] == minted[1]


# --- rank-key cache vs cold rebuild ---------------------------------------------


def _reads(ss, cues: list[str]) -> list[str]:
    from memnet.in_process_engine import run_argv

    sid = ss.session_id
    out = []
    argvs = [["query", "pin-map", "--session", sid]]
    for cue in cues:
        for d in ("1", "2", "3"):
            argvs.append(["query", "pin-map", "--cue", cue, "--depth", d, "--session", sid])
    argvs += [
        ["query", "find", "--kind", "PRT", "--limit", "50", "--session", sid],
        ["query", "find", "--keyword", "n", "--limit", "20", "--session", sid],
        [
            "query",
            "typed-walk",
            "--from",
            cues[0],
            "--type",
            "links",
            "--dir",
            "both",
            "--max-hops",
            "3",
            "--session",
            sid,
        ],
    ]
    for argv in argvs:
        r = run_argv(argv)
        out.append(f"{r['exit_code']}\n{r['stdout']}\n{r['stderr']}")
    return out


def _cold_reads(ss, cues, monkeypatch) -> list[str]:
    """The same reads with the cache off: every key rebuilt (0.20.7 behaviour)."""
    with monkeypatch.context() as m:
        m.setattr(MemStore, "rank_key_function", None)
        return _reads(ss, cues)


def _assert_warm_equals_cold(ss, cues, monkeypatch, where: str) -> None:
    warm = _reads(ss, cues)
    warm_again = _reads(ss, cues)  # no write in between: served from the cache
    cold = _cold_reads(ss, cues, monkeypatch)
    assert warm == cold, where
    assert warm_again == cold, where


def test_rank_keys_reused_until_a_write(memnet_temp, monkeypatch):
    """The cache is live: a read with no write in between builds no key; a write resets."""
    import memnet.mem_store as ms

    ss = open_session(map_lines=list(_MAP))
    _apply(ss, *[f"CREATE (:PRT {{id: 'P{i}', name: 'n{i % 3}', role: 'r'}})" for i in range(4)])
    _apply(ss, "MATCH (a {id: 'P0'}), (b {id: 'P1'}) CREATE (a)-[:links]->(b)")
    built = []
    real = ms.record_rank_key
    monkeypatch.setattr(ms, "record_rank_key", lambda r, res=None: built.append(r) or real(r, res))
    first = _reads(ss, ["P0"])
    n_first = len(built)
    assert n_first > 0
    assert _reads(ss, ["P0"]) == first
    assert len(built) == n_first
    _apply(ss, "MATCH (n {id: 'P1'}) SET n.name = 'zz'")
    _reads(ss, ["P0"])
    assert len(built) > n_first


@pytest.mark.parametrize("seed", [3, 11, 99])
def test_recall_order_matches_cold_rebuild(memnet_temp, monkeypatch, seed):
    from memnet.import_absorb import import_slice

    rng = random.Random(seed)
    ss = open_session(map_lines=list(_MAP))
    other = open_session(map_lines=list(_MAP))
    nodes = [f"P{i}" for i in range(10)]
    _apply(
        ss,
        *[f"CREATE (:PRT {{id: '{n}', name: 'n{rng.randrange(3)}', role: 'r'}})" for n in nodes],
    )
    _apply(other, "CREATE (:PRT {id: 'Q0', name: 'n1', role: 'imp'})")
    _apply(other, "CREATE (:PRT {id: 'Q1', name: 'n0', role: 'imp'})")
    _apply(other, "MATCH (a {id: 'Q0'}), (b {id: 'Q1'}) CREATE (a)-[:links {w: '1'}]->(b)")
    for _ in range(25):
        a, b = rng.choice(nodes), rng.choice(nodes)
        _apply(
            ss,
            f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) "
            f"CREATE (a)-[:links {{w: '{rng.randrange(3)}'}}]->(b)",
        )
    cues = ["P0", "P3", "P7"]
    _assert_warm_equals_cold(ss, cues, monkeypatch, "initial")

    def w_set_endpoint():
        # Changes the payload of an edge endpoint: every edge key at that node moves.
        n = rng.choice(nodes)
        _apply(ss, f"MATCH (n {{id: '{n}'}}) SET n.name = 'n{rng.randrange(5)}'")

    def w_set_edge():
        ids = [e.fields["id"] for e in ss.store.list_records("EDG")]
        if ids:
            eid = rng.choice(ids)
            _apply(ss, f"MATCH ()-[r {{id: '{eid}'}}]-() SET r.w = '{rng.randrange(5)}'")

    def w_link():
        a, b = rng.choice(nodes), rng.choice(nodes)
        _apply(ss, f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) CREATE (a)-[:links]->(b)")

    def w_delete_edge():
        ids = [e.fields["id"] for e in ss.store.list_records("EDG")]
        if ids:
            try:  # an import can leave two edges with one id: DELETE refuses it
                _apply(ss, f"MATCH ()-[r {{id: '{rng.choice(ids)}'}}]-() DELETE r")
            except MemNetError:
                pass

    def w_delete_node():
        n = rng.choice(nodes[4:])
        try:
            _apply(ss, f"MATCH (n {{id: '{n}'}}) DETACH DELETE n")
        except MemNetError:
            pass

    def w_rename():
        n = rng.choice(nodes[4:])
        try:
            _apply(ss, f"MATCH (n {{id: '{n}'}}) SET n.id = '{n}r'", mode="update")
            _apply(ss, f"MATCH (n {{id: '{n}r'}}) SET n.id = '{n}'", mode="update")
        except MemNetError:
            pass

    def w_refused():
        try:
            _apply(
                ss,
                f"MATCH (n {{id: '{rng.choice(nodes)}'}}) SET n.name = 'refused'",
                "MATCH (n:PRT {id: 'NOPE'}) SET n.role = 'x'",
            )
        except MemNetError:
            pass

    def w_import():
        import_slice(
            lead_session_id=ss.session_id,
            source_session_id=other.session_id,
            anchors=["Q0"],
            enable_guard=False,
        )

    writes = [
        w_set_endpoint,
        w_set_edge,
        w_link,
        w_delete_edge,
        w_delete_node,
        w_rename,
        w_refused,
        w_import,
    ]
    for step in range(30):
        w = writes[step % len(writes)] if step < len(writes) else rng.choice(writes)
        try:  # a write on a node an earlier step deleted is refused (still a read check)
            w()
        except MemNetError:
            pass
        _assert_warm_equals_cold(ss, cues, monkeypatch, f"step {step} after {w.__name__}")


def test_set_on_edge_endpoint_then_recall_matches_cold(memnet_temp, monkeypatch):
    """The case a per-record cache gets wrong: an edge key holds its endpoints' keys."""
    ss = open_session(map_lines=list(_MAP))
    _apply(
        ss,
        "CREATE (:PRT {id: 'H', name: 'hub', role: 'r'})",
        "CREATE (:PRT {id: 'A', name: 'a', role: 'r'})",
        "CREATE (:PRT {id: 'B', name: 'b', role: 'r'})",
    )
    _apply(ss, "MATCH (h {id: 'H'}), (x {id: 'A'}) CREATE (h)-[:links]->(x)")
    _apply(ss, "MATCH (h {id: 'H'}), (x {id: 'B'}) CREATE (h)-[:links]->(x)")
    before = _reads(ss, ["H"])
    assert before == _cold_reads(ss, ["H"], monkeypatch)
    # Only the endpoint changes; edge H->A must now rank after H->B.
    _apply(ss, "MATCH (n {id: 'A'}) SET n.name = 'zzz'")
    after = _reads(ss, ["H"])
    assert after == _cold_reads(ss, ["H"], monkeypatch)
    assert after != before


# --- gc.freeze after load -------------------------------------------------------


def test_gc_freeze_after_load_finishes(memnet_temp, monkeypatch, tmp_path):
    from memnet.registry import count
    from memnet.snapshot import load_snapshot, write_snapshot

    ss = open_session(map_lines=list(_MAP))
    _apply(ss, "CREATE (:PRT {id: 'A', name: 'a', role: 'r'})")
    path = tmp_path / "gc.snap"
    write_snapshot(ss, path)
    before = count()
    calls: list[tuple[str, int]] = []
    monkeypatch.setattr(gc, "collect", lambda *a: calls.append(("collect", count())) or 0)
    monkeypatch.setattr(gc, "freeze", lambda: calls.append(("freeze", count())))
    loaded = load_snapshot(path)
    # Once, after the loaded session is registered (the load has finished).
    assert calls == [("collect", before + 1), ("freeze", before + 1)]
    assert loaded.store.match_nickname("A")


def test_gc_not_frozen_by_throwaway_verify(memnet_temp, monkeypatch):
    from memnet.snapshot import materialise_snapshot_text, snapshot_text

    ss = open_session(map_lines=list(_MAP))
    text = snapshot_text(ss)
    calls: list[str] = []
    monkeypatch.setattr(gc, "freeze", lambda: calls.append("freeze"))
    materialise_snapshot_text(text)
    assert calls == []


def test_frozen_session_still_freed_by_refcount(memnet_temp):
    """Freezing does not pin a loaded session: closing it frees the store, GC off."""
    from memnet.registry import remove_entry
    from memnet.snapshot import load_snapshot_text, snapshot_text

    ss = open_session(map_lines=list(_MAP))
    _apply(ss, "CREATE (:PRT {id: 'A', name: 'a', role: 'r'})")
    _apply(ss, "CREATE (:PRT {id: 'B', name: 'b', role: 'r'})")
    _apply(ss, "MATCH (a {id: 'A'}), (b {id: 'B'}) CREATE (a)-[:links]->(b)")
    loaded = load_snapshot_text(snapshot_text(ss))
    _reads(loaded, ["A"])  # fills the rank-key cache too
    gone = weakref.ref(loaded.store)
    sid = loaded.session_id
    del loaded
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        assert remove_entry(sid)
        assert gone() is None
    finally:
        if was_enabled:
            gc.enable()
