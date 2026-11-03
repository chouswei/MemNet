"""Nickname id index in MemStore: robustness, never-reused mints, indexed find, field cap.

Red-first for symphony range-where-id-index (M1). Pinned interface (lands in M2):
``MemStore._by_hid`` is a dict subclass that indexes on every mutator;
``match_nickname(nick)`` returns the same rows in the same order as a scan of
``_by_hid``; ``verify_indexes() -> list[str]`` ([] = consistent), ``reindex(hid)``
and ``id_high_water() -> dict[str, int]`` are new. IdAllocator mints max suffix + 1
and the mint high-water survives snapshot save/load. ``refuse_mutate_field_cap`` and
``bounded_match_find`` keep their signatures and results.

New names are looked up inside test bodies so collection never fails on 0639ad1.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import close_session, open_session

_MAP = [
    "SCHEMA TSK ; fields=id goal status recycle",
    "SCHEMA MOD ; fields=id path note",
    "SCHEMA CST ; fields=id name role",
]
_PRT_MAP = ["SCHEMA PRT ; fields=id name role"]
_CST_DECLARED = 3
TOKEN = "test-admin-token"


def _apply(ss, *stmts, mode="mutate"):
    return MutateGate(ss).apply(list(stmts), mode=mode, allow_new_relation=True)


def _extras(n: int, *, start: int = 0, prefix: str = "x") -> str:
    return ", ".join(f"{prefix}{i:03d}: 'v{i:03d}'" for i in range(start, start + n))


def _scan(store, nick: str) -> list:
    return [r for r in store._by_hid.values() if r.fields.get("id") == nick]


def _assert_index(store, *extra_nicks: str) -> None:
    """verify_indexes() is clean and match_nickname equals the scan (dups included)."""
    by_hid = store._by_hid
    assert isinstance(by_hid, dict)
    assert type(by_hid) is not dict, "_by_hid must be the indexing dict subclass"
    assert store.verify_indexes() == []
    nicks = {r.fields.get("id") for r in by_hid.values() if r.fields.get("id")}
    for nick in sorted(nicks | set(extra_nicks) | {"__absent__"}):
        got = store.match_nickname(nick)
        want = _scan(store, nick)
        assert [r.hid for r in got] == [r.hid for r in want], nick
        assert all(a is b for a, b in zip(got, want, strict=True)), nick


def _state(store) -> list[tuple[str, str, dict[str, str]]]:
    return [(h, store._by_hid[h].tag, dict(store._by_hid[h].fields)) for h in store.write_order]


def _seeded(ss) -> None:
    """Duplicate nicknames, an id-less node, a node with edges, a CST row."""
    _apply(
        ss,
        "CREATE (:TSK {id: 'dup', goal: 'one', status: 'open'})",
        "CREATE (:TSK {id: 'dup', goal: 'two', status: 'open'})",
        "CREATE (:TSK {goal: 'alpha', status: 'open'})",
        "CREATE (:TSK {id: 'X', goal: 'beta', status: 'open'})",
        "CREATE (:TSK {id: 'Y', goal: 'gamma', status: 'open'})",
        "CREATE (:MOD {id: 'dup', path: 'p.md', note: 'n'})",
        "CREATE (:CST {id: 'C0', name: 'c', role: 'r'})",
        mode="add",
    )
    _apply(
        ss,
        "MATCH (a {id: 'X'}), (b {id: 'Y'}) CREATE (a)-[:links]->(b)",
        "MATCH (a {id: 'Y'}), (b {id: 'C0'}) CREATE (a)-[:links {id: 'E_yc'}]->(b)",
    )
    assert len(_scan(ss.store, "dup")) == 3


@pytest.fixture
def seeded(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _seeded(ss)
    return ss


# --- group 2: index robustness ------------------------------------------------


def test_index_after_create(seeded):
    _assert_index(seeded.store, "dup", "X")
    _apply(
        seeded,
        "CREATE (:TSK {id: 'dup', goal: 'three', status: 'open'})",
        "CREATE (:TSK {id: 'Z', goal: 'z', status: 'open'})",
        mode="add",
    )
    assert len(seeded.store.match_nickname("dup")) == 4
    _assert_index(seeded.store, "dup", "Z")


def test_index_after_gql_rename(seeded):
    _apply(seeded, "MATCH (n {id: 'Y'}) SET n.id = 'Y_renamed'", mode="update")
    assert seeded.store.match_nickname("Y") == []
    assert len(seeded.store.match_nickname("Y_renamed")) == 1
    _assert_index(seeded.store, "Y", "Y_renamed")
    # and back again
    _apply(seeded, "MATCH (n {id: 'Y_renamed'}) SET n.id = 'Y'", mode="update")
    _assert_index(seeded.store, "Y", "Y_renamed")


def test_index_after_delete(seeded):
    _apply(seeded, "MATCH (n {id: 'X'}) DETACH DELETE n")
    assert seeded.store.match_nickname("X") == []
    _assert_index(seeded.store, "X")
    _apply(seeded, "MATCH ()-[r {id: 'E_yc'}]-() DELETE r")
    assert seeded.store.match_nickname("E_yc") == []
    _assert_index(seeded.store, "E_yc")
    dup_hid = _scan(seeded.store, "dup")[1].hid
    seeded.store.delete(dup_hid)
    assert len(seeded.store.match_nickname("dup")) == 2
    _assert_index(seeded.store, "dup")


def test_index_after_refused_mutate_batch(seeded):
    before = _state(seeded.store)
    with pytest.raises(MemNetError) as ei:
        _apply(
            seeded,
            "CREATE (:TSK {id: 'dup', goal: 'four', status: 'open'})",
            "CREATE (:TSK {id: 'NEWBIE', goal: 'n', status: 'open'})",
            "MATCH (n:TSK {id: 'X'}) SET n.goal = 'changed'",
            "MATCH (a {id: 'NEWBIE'}), (b {id: 'X'}) CREATE (a)-[:links]->(b)",
            f"CREATE (:CST {{id: 'N_OVER', name: 'a', role: 'b', {_extras(62)}}})",
        )
    assert ei.value.code == "limit_exceeded"
    assert _state(seeded.store) == before
    assert seeded.store.match_nickname("NEWBIE") == []
    _assert_index(seeded.store, "NEWBIE", "N_OVER", "dup")


def test_index_after_refused_update_batch_with_rename(seeded):
    cap = seeded.caps.max_fields
    _apply(
        seeded,
        f"CREATE (:CST {{id: 'W', name: 'w', role: 'r', {_extras(cap - _CST_DECLARED)}}})",
        mode="add",
    )
    before = _state(seeded.store)
    with pytest.raises(MemNetError) as ei:
        _apply(
            seeded,
            "MATCH (n {id: 'Y'}) SET n.id = 'Y2'",
            "MATCH (n:CST {id: 'W'}) SET n.zz_over = 'nope'",
            mode="update",
        )
    assert ei.value.code == "limit_exceeded"
    assert _state(seeded.store) == before
    assert seeded.store.match_nickname("Y2") == []
    assert len(seeded.store.match_nickname("Y")) == 1
    _assert_index(seeded.store, "Y", "Y2", "W")


def test_index_after_bypass_guard_rollback(seeded):
    from memnet.bypass_caps import bypass_guard
    from memnet.models import Record

    store = seeded.store
    rows_before = len(store._by_hid)
    x_hid = _scan(store, "X")[0].hid
    with pytest.raises(MemNetError):
        with bypass_guard(seeded):
            store.upsert(
                Record(tag="TSK", fields={"id": "dup", "goal": "g", "status": "open"}),
                relations=seeded.relations,
            )
            store.upsert(
                Record(tag="TSK", fields={"id": "BYP", "goal": "g", "status": "open"}),
                relations=seeded.relations,
            )
            store.delete(x_hid)
            _assert_index(store, "BYP", "X", "dup")
            raise MemNetError("limit_exceeded", "test|1/0")
    assert len(store._by_hid) == rows_before
    assert store.match_nickname("BYP") == []
    assert [r.hid for r in store.match_nickname("X")] == [x_hid]
    assert len(store.match_nickname("dup")) == 3
    _assert_index(store, "BYP", "X", "dup")


def test_index_after_same_thing_absorb(seeded):
    store = seeded.store
    keep = next(r for r in store._by_hid.values() if r.fields.get("goal") == "alpha")
    assert not keep.fields.get("id")
    drop_hid = _scan(store, "X")[0].hid
    _apply(
        seeded,
        "MATCH (a:TSK {goal: 'alpha'}), (b:TSK {goal: 'beta'})\nSET a += b",
        mode="update",
    )
    assert drop_hid not in store._by_hid
    # the survivor took the absorbed nickname in place
    assert [r.hid for r in store.match_nickname("X")] == [keep.hid]
    _assert_index(store, "X", "dup")


def test_index_after_snapshot_save_load(seeded, tmp_path: Path):
    from memnet.snapshot import load_snapshot, write_snapshot

    _assert_index(seeded.store)
    path = tmp_path / "idx.snap"
    write_snapshot(seeded, path)
    loaded = load_snapshot(path)
    assert len(loaded.store.match_nickname("dup")) == 3
    _assert_index(loaded.store, "dup", "X", "Y", "E_yc")


def test_index_after_checkpoint_restore(seeded, monkeypatch, tmp_path: Path):
    from memnet.checkpoint import MANIFEST_NAME, run_checkpoint
    from memnet.snapshot import load_snapshot_text, materialise_snapshot_text

    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    result = run_checkpoint(TOKEN, directory=tmp_path)
    assert result.exit_code == 0
    dest = tmp_path / "checkpoint"
    manifest = json.loads((dest / MANIFEST_NAME).read_text(encoding="utf-8"))
    row = next(r for r in manifest["sessions"] if r["session_id"] == seeded.session_id)
    text = (dest / row["file"]).read_text(encoding="utf-8")
    for restored in (materialise_snapshot_text(text), load_snapshot_text(text)):
        assert len(restored.store.match_nickname("dup")) == 3
        _assert_index(restored.store, "dup", "X", "Y", "E_yc")


def test_index_after_cli_session_save_load(seeded, tmp_path: Path):
    from memnet.in_process_engine import run_argv
    from memnet.registry import get_entry

    sid = seeded.session_id
    path = tmp_path / "cli.snap"
    saved = run_argv(["session", "save", "--file", str(path), "--session", sid])
    assert saved["exit_code"] == 0, saved["stderr"]
    close_session(sid)
    loaded = run_argv(["session", "load", "--file", str(path), "--keep-id"])
    assert loaded["exit_code"] == 0, loaded["stderr"]
    entry = get_entry(sid)
    assert entry is not None
    assert len(entry.store.match_nickname("dup")) == 3
    _assert_index(entry.store, "dup", "X", "Y", "E_yc")


def test_verify_indexes_flags_in_place_edit_and_reindex_repairs(seeded):
    store = seeded.store
    rec = _scan(store, "Y")[0]
    _assert_index(store)
    rec.fields["id"] = "Y_inplace"  # bypasses every mutator
    problems = store.verify_indexes()
    assert isinstance(problems, list)
    assert problems and all(isinstance(p, str) for p in problems)
    store.reindex(rec.hid)
    assert [r.hid for r in store.match_nickname("Y_inplace")] == [rec.hid]
    assert store.match_nickname("Y") == []
    _assert_index(store, "Y", "Y_inplace")


def test_seeded_random_op_sequence_keeps_index(memnet_temp):
    from memnet.bypass_caps import bypass_guard
    from memnet.models import Record

    rng = random.Random(245)
    ss = open_session(map_lines=list(_MAP))
    store = ss.store
    pool = [f"N{i}" for i in range(8)]
    _assert_index(store, *pool)

    def nick() -> str:
        return rng.choice(pool)

    def op_create() -> None:
        _apply(ss, f"CREATE (:TSK {{id: '{nick()}', goal: 'g{rng.randrange(4)}'}})", mode="add")

    def op_create_idless() -> None:
        _apply(ss, f"CREATE (:TSK {{goal: 'g{rng.randrange(4)}'}})", mode="add")

    def op_rename() -> None:
        _apply(ss, f"MATCH (n {{id: '{nick()}'}}) SET n.id = '{nick()}'", mode="update")

    def op_set() -> None:
        _apply(ss, f"MATCH (n:TSK {{id: '{nick()}'}}) SET n.status = 's{rng.randrange(3)}'")

    def op_delete() -> None:
        _apply(ss, f"MATCH (n {{id: '{nick()}'}}) DETACH DELETE n")

    def op_link() -> None:
        _apply(ss, f"MATCH (a {{id: '{nick()}'}}), (b {{id: '{nick()}'}}) CREATE (a)-[:links]->(b)")

    def op_refused() -> None:
        _apply(
            ss,
            f"CREATE (:TSK {{id: '{nick()}', goal: 'r'}})",
            f"MATCH (n:TSK {{id: '{nick()}'}}) SET n.goal = 'rr'",
            f"CREATE (:CST {{id: 'N_OVER', name: 'a', role: 'b', {_extras(62)}}})",
        )

    def op_bypass() -> None:
        with bypass_guard(ss):
            store.upsert(Record(tag="TSK", fields={"id": nick(), "goal": "b"}), relations=None)
            hits = _scan(store, nick())
            if hits:
                store.delete(hits[0].hid)
            raise MemNetError("limit_exceeded", "test|1/0")

    def op_absorb() -> None:
        a, b = rng.randrange(4), rng.randrange(4)
        _apply(
            ss,
            f"MATCH (a:TSK {{goal: 'g{a}'}}), (b:TSK {{goal: 'g{b}'}})\nSET a += b",
            mode="update",
        )

    ops = [
        (op_create, 6),
        (op_create_idless, 2),
        (op_rename, 4),
        (op_set, 2),
        (op_delete, 3),
        (op_link, 3),
        (op_refused, 1),
        (op_bypass, 1),
        (op_absorb, 1),
    ]
    funcs = [f for f, _w in ops]
    weights = [w for _f, w in ops]
    done = 0
    for step in range(300):
        op = rng.choices(funcs, weights=weights)[0]
        try:
            op()
            done += 1
        except MemNetError:
            pass
        try:
            _assert_index(store, *pool)
        except AssertionError as exc:
            raise AssertionError(f"step {step} after {op.__name__}: {exc}") from exc
    assert done > 100


# --- group 3: minted ids are never reused -------------------------------------


def _prt_session():
    ss = open_session(map_lines=list(_PRT_MAP))
    _apply(ss, *[f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: 'r'}})" for i in range(4)])
    return ss


def _edge_ids(ss) -> set[str]:
    return {e.fields.get("id", "") for e in ss.store.list_records("EDG")}


def _mint_link(ss, a: str = "P0", b: str = "P1") -> str:
    before = _edge_ids(ss)
    _apply(ss, f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) CREATE (a)-[:links]->(b)")
    (new,) = _edge_ids(ss) - before
    return new


def _delete_edge(ss, eid: str) -> None:
    _apply(ss, f"MATCH ()-[r {{id: '{eid}'}}]-() DELETE r")
    assert eid not in _edge_ids(ss)


def test_mint_does_not_reuse_deleted_edge_id(memnet_temp):
    ss = _prt_session()
    assert _mint_link(ss, "P0", "P1") == "E1"
    assert _mint_link(ss, "P1", "P2") == "E2"
    _delete_edge(ss, "E2")
    assert ss.store.id_high_water().get("E") == 2
    assert _mint_link(ss, "P2", "P3") == "E3"


def test_mint_high_water_survives_snapshot_save_load(memnet_temp, tmp_path: Path):
    from memnet.snapshot import load_snapshot, write_snapshot

    ss = _prt_session()
    assert _mint_link(ss, "P0", "P1") == "E1"
    assert _mint_link(ss, "P1", "P2") == "E2"
    _delete_edge(ss, "E2")
    assert _mint_link(ss, "P2", "P3") == "E3"
    path = tmp_path / "mint.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path)
    assert _edge_ids(loaded) == {"E1", "E3"}
    assert loaded.store.id_high_water().get("E") == 3
    assert _mint_link(loaded, "P3", "P0") == "E4"


def test_mint_is_max_live_suffix_plus_one(memnet_temp):
    ss = _prt_session()
    _apply(
        ss,
        "MATCH (a {id: 'P0'}), (b {id: 'P1'}) CREATE (a)-[:links {id: 'E1'}]->(b)",
        "MATCH (a {id: 'P1'}), (b {id: 'P2'}) CREATE (a)-[:links {id: 'E3'}]->(b)",
    )
    assert _edge_ids(ss) == {"E1", "E3"}
    assert _mint_link(ss, "P2", "P3") == "E4"


def test_mint_after_refused_bypass_and_gate_batches(memnet_temp):
    from memnet.bypass_caps import bypass_guard

    ss = _prt_session()
    assert _mint_link(ss, "P0", "P1") == "E1"
    assert _mint_link(ss, "P1", "P2") == "E2"
    _delete_edge(ss, "E2")  # committed delete
    # refused through bypass_guard: rollback is clear() + re-set
    with pytest.raises(MemNetError):
        with bypass_guard(ss):
            _mint_link(ss, "P2", "P3")
            raise MemNetError("limit_exceeded", "test|1/0")
    assert _edge_ids(ss) == {"E1"}
    # refused through the mutate gate (field cap after the edge is written)
    over = f"CREATE (:PRT {{id: 'P_OVER', name: 'a', role: 'b', {_extras(62)}}})"
    with pytest.raises(MemNetError) as ei:
        _apply(
            ss,
            "MATCH (a {id: 'P2'}), (b {id: 'P3'}) CREATE (a)-[:links]->(b)",
            over,
        )
    assert ei.value.code == "limit_exceeded"
    assert _edge_ids(ss) == {"E1"}
    nxt = _mint_link(ss, "P3", "P0")
    assert nxt != "E2"
    assert nxt == "E3"


# --- group 5: bounded_match_find by id uses the index ---------------------------


def _reference_find(store, *, kind, locators, keyword, limit):
    """Copy of bounded_match_find on 0639ad1 (full list_records walk)."""
    from memnet.observable_rank import ranked

    if limit < 1:
        raise MemNetError("bad_limit", "find --limit must be >= 1")
    kind_u = kind.upper() if kind else None
    if kind_u:
        rows = store.list_records(kind_u, active_only=True)
    else:
        rows = [r for r in store.list_records(active_only=True) if r.tag not in {"LAW", "EDG"}]
    needle = (keyword or "").strip().lower()

    def _loc_ok(rec) -> bool:
        for key, val in locators:
            if str(rec.fields.get(key, "")) != val:
                return False
        return True

    def _kw_ok(rec) -> bool:
        if not needle:
            return True
        return any(needle in str(v).lower() for v in rec.fields.values())

    hits = [r for r in rows if _loc_ok(r) and _kw_ok(r)]
    hits = ranked(hits, resolve=getattr(store, "resolve_one", None))
    return hits[:limit], len(hits)


_FIND_CASES = [
    (None, [("id", "dup")], None, 10),
    ("TSK", [("id", "dup")], None, 10),
    ("tsk", [("id", "dup")], None, 10),
    ("TSK", [("id", "dup")], None, 1),
    ("TSK", [("id", "dup"), ("status", "open")], None, 10),
    (None, [("id", "dup")], "beta", 10),
    (None, [("id", "dup")], "PATH", 10),
    ("MOD", [("id", "dup")], None, 10),
    ("EDG", [("id", "dup")], None, 10),
    ("TSK", [("id", "gone")], None, 10),
    ("TSK", [("id", "missing")], None, 10),
    (None, [("status", "open"), ("id", "solo")], "SOL", 10),
    (None, [("id", "solo")], "nomatch", 10),
]


def _find_session():
    ss = open_session(map_lines=list(_MAP))
    _apply(
        ss,
        "CREATE (:TSK {id: 'dup', goal: 'alpha', status: 'open'})",
        "CREATE (:TSK {id: 'dup', goal: 'beta', status: 'done'})",
        "CREATE (:TSK {id: 'dup', goal: 'beta', status: 'open', recycle: 'delete_on_settle'})",
        "CREATE (:TSK {id: 'gone', goal: 'g', status: 'open', recycle: 'delete_on_expire'})",
        "CREATE (:TSK {id: 'solo', goal: 'solo goal', status: 'open'})",
        "CREATE (:MOD {id: 'dup', path: 'docs/path.md', note: 'beta'})",
        *[f"CREATE (:TSK {{id: 'T{i}', goal: 'filler', status: 'open'}})" for i in range(20)],
        mode="add",
    )
    _apply(ss, "MATCH (a {id: 'solo'}), (b {id: 'T0'}) CREATE (a)-[:links {id: 'dup'}]->(b)")
    return ss


@pytest.mark.parametrize(("kind", "locators", "keyword", "limit"), _FIND_CASES)
def test_find_by_id_locator_uses_index(memnet_temp, monkeypatch, kind, locators, keyword, limit):
    from memnet.mem_store import MemStore
    from memnet.pin_map_composer import bounded_match_find

    ss = _find_session()
    want_seeds, want_total = _reference_find(
        ss.store, kind=kind, locators=locators, keyword=keyword, limit=limit
    )
    calls: list[tuple] = []
    real = MemStore.list_records

    def counting(self, *args, **kwargs):
        calls.append((args, kwargs))
        return real(self, *args, **kwargs)

    monkeypatch.setattr(MemStore, "list_records", counting)
    got = bounded_match_find(ss.store, kind=kind, locators=locators, keyword=keyword, limit=limit)
    assert [r.hid for r in got.seeds] == [r.hid for r in want_seeds]
    assert got.total == want_total
    assert calls == [], "id locator must not walk list_records"


def test_find_reference_cases_cover_duplicates_and_recycle(memnet_temp):
    """Guards the case table itself (green on 0639ad1)."""
    ss = _find_session()
    seeds, total = _reference_find(
        ss.store, kind="TSK", locators=[("id", "dup")], keyword=None, limit=10
    )
    assert total == 2  # recyclable dup excluded
    seeds, total = _reference_find(
        ss.store, kind=None, locators=[("id", "dup")], keyword=None, limit=10
    )
    assert total == 3  # TSK x2 + MOD; EDG excluded without kind
    seeds, total = _reference_find(
        ss.store, kind="EDG", locators=[("id", "dup")], keyword=None, limit=10
    )
    assert total == 1


# --- group 6: field cap without walking every row -------------------------------


def _large_cst_session(monkeypatch, rows: int = 1000):
    monkeypatch.setenv("MEMNET_DEBUG_SESSION_BYTES", "0")
    ss = open_session(map_lines=list(_MAP))
    for b in range(rows // 100):
        _apply(
            ss,
            *[f"CREATE (:CST {{id: 'C{b * 100 + i}', name: 'n', role: 'r'}})" for i in range(100)],
        )
    assert ss.store.row_count_non_law() == rows
    return ss


def _spy_extras(monkeypatch) -> list[int]:
    from memnet import snapshot

    calls: list[int] = []
    real = snapshot.collect_undeclared_extras

    def spy(ss):
        calls.append(1)
        return real(ss)

    monkeypatch.setattr(snapshot, "collect_undeclared_extras", spy)
    return calls


def test_single_line_mutate_does_not_walk_rows_for_field_cap(memnet_temp, monkeypatch):
    ss = _large_cst_session(monkeypatch)
    calls = _spy_extras(monkeypatch)
    _apply(ss, "CREATE (:CST {id: 'C_new', name: 'n', role: 'r', extra1: 'e'})")
    assert ss.store.get("C_new") is not None
    assert calls == []
    _apply(ss, "MATCH (n:CST {id: 'C5'}) SET n.name = 'z'")
    assert ss.store.get("C5").fields["name"] == "z"
    assert calls == []


def test_over_cap_write_still_refused_on_large_session(memnet_temp, monkeypatch):
    from memnet.output import format_err

    ss = _large_cst_session(monkeypatch)
    cap = ss.caps.max_fields
    rows = ss.store.row_count_non_law()
    over_n = cap - _CST_DECLARED + 1
    with pytest.raises(MemNetError) as ei:
        _apply(ss, f"CREATE (:CST {{id: 'N_OVER', name: 'a', role: 'b', {_extras(over_n)}}})")
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == f"fields|{_CST_DECLARED + over_n}/{cap}"
    assert format_err(ei.value.code, ei.value.message) == (
        f"@ERR: limit_exceeded|fields {_CST_DECLARED + over_n}/{cap}"
    )
    assert ss.store.get("N_OVER") is None
    assert ss.store.row_count_non_law() == rows
    # one row fills the tag to the cap; a new extra on any other row is over
    _apply(ss, f"CREATE (:CST {{id: 'N_AT', name: 'a', role: 'b', {_extras(cap - 3)}}})")
    assert ss.store.get("N_AT") is not None
    with pytest.raises(MemNetError) as ei2:
        _apply(ss, "CREATE (:CST {id: 'N_ONE', name: 'a', role: 'b', y000: 'v'})")
    assert ei2.value.code == "limit_exceeded"
    assert ei2.value.message == f"fields|{cap + 1}/{cap}"
    assert ss.store.get("N_ONE") is None
    with pytest.raises(MemNetError) as ei3:
        _apply(ss, "MATCH (n:CST {id: 'C7'}) SET n.y001 = 'v'")
    assert ei3.value.code == "limit_exceeded"
    assert ei3.value.message == f"fields|{cap + 1}/{cap}"
    assert "y001" not in ss.store.get("C7").fields


def test_fixed_tag_extra_refused_as_on_base(memnet_temp, monkeypatch):
    ss = _large_cst_session(monkeypatch)
    rows = ss.store.row_count_non_law()
    with pytest.raises(MemNetError) as ei:
        _apply(ss, "CREATE (:LAW {id: 'LAW09', name: 'x', zzz: 'q'})")
    assert ei.value.code == "snapshot_unsaveable"
    assert ei.value.message == "LAW nick=LAW09 field=zzz fixed_tag extra"
    assert ss.store.get("LAW09") is None
    assert ss.store.row_count_non_law() == rows
