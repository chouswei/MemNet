"""Session-bytes budget check is incremental, exact, same-semantics and rollback-safe.

Claim under test: the running session byte total kept by ``memnet.session_bytes``
(a) equals a full recount and the escaped schema+record lines of ``snapshot_text``
after every write path, (b) costs O(changed rows) per write, (c) reports the same
``session_bytes|<total>/<budget>`` refusal as before, and (d) survives rollbacks.

``memnet.session_bytes`` is imported inside each test body so this file collects on
trees where the module does not exist yet.
"""

from __future__ import annotations

import os
import random
import time

import pytest
from typer.testing import CliRunner

from memnet.bypass_caps import bypass_guard
from memnet.cli import app
from memnet.config import Caps
from memnet.durable import DurableSubgraph, DurableSyncOwner, FakeDurableAdapter
from memnet.exceptions import MemNetError
from memnet.housekeep import prune_rows
from memnet.import_absorb import (
    absorb_working_memory_slice,
    export_working_memory_slice,
    reset_import_guard_for_tests,
)
from memnet.models import Record
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.snapshot import load_snapshot_text, snapshot_text

runner = CliRunner()

_MAP = [
    "SCHEMA MOD ; fields=id path note",
    "SCHEMA SYM ; fields=id kind refdes",
]


@pytest.fixture(autouse=True)
def _reset_guard():
    reset_import_guard_for_tests()
    yield
    reset_import_guard_for_tests()


# --- helpers


def _body_lines(ss) -> list[str]:
    """Schema + record lines: exactly what the line cap and byte budget measure."""
    out: list[str] = []
    section = ""
    for ln in snapshot_text(ss).splitlines():
        if ln in ("# map", "# relations", "# records"):
            section = ln
        elif section in ("# map", "# records") and ln:
            out.append(ln)
    return out


def _body_bytes(ss) -> int:
    return sum(len(ln.encode("utf-8")) for ln in _body_lines(ss))


def _content(ss):
    return _body_lines(ss), set(ss.relations), list(ss.store.write_order)


def _assert_equal(ss) -> int:
    """incremental (when available) == full recount == bytes of the snapshot body."""
    import memnet.session_bytes as sb

    body = _body_bytes(ss)
    full = sb.full_recount_total(ss)
    assert full == body, f"full recount {full} != snapshot body {body}"
    inc = sb.incremental_total(ss)
    if inc is not None:
        assert inc == body, f"incremental {inc} != snapshot body {body}"
    return body


def _gate(ss) -> MutateGate:
    return MutateGate(ss)


def _try(ss, stmts, mode="add", **kw):
    """Apply GQL; a refusal by the gate is a legal outcome, anything else is not."""
    try:
        _gate(ss).apply(stmts, mode=mode, **kw)
    except MemNetError:
        return False
    return True


def _new_session(**kw):
    return open_session(map_lines=_MAP, **kw)


def _edge_stmt(a: str, b: str, eid: str) -> str:
    return (
        f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}})\nCREATE (a)-[:mentions {{id: '{eid}'}}]->(b)"
    )


def _member(tag_suffix: str):
    member = _new_session()
    _gate(member).apply(
        [
            f"CREATE (:MOD {{id: 'IM_{tag_suffix}', path: 'p', note: 'imp'}})",
            f"CREATE (:SYM {{id: 'IS_{tag_suffix}', kind: 'k', refdes: 'r'}})",
            _edge_stmt(f"IM_{tag_suffix}", f"IS_{tag_suffix}", f"IE_{tag_suffix}"),
        ],
        mode="add",
        allow_new_relation=True,
    )
    return member


def _owner_with(prefix: str) -> DurableSyncOwner:
    ego = Record(tag="MOD", fields={"id": f"{prefix}_ego", "path": "p", "note": "n"})
    other = Record(tag="SYM", fields={"id": f"{prefix}_o", "kind": "k", "refdes": "r"})
    edge = Record(
        tag="EDG",
        fields={
            "id": f"{prefix}_e",
            "src": f"{prefix}_ego",
            "relation": "MENTIONS",
            "dist": f"{prefix}_o",
        },
    )
    adapter = FakeDurableAdapter()
    adapter.seed(
        DurableSubgraph(
            ego_id=f"{prefix}_ego", nodes=[ego, other], edges=[edge], relations={"MENTIONS"}
        )
    )
    return DurableSyncOwner(adapter)


_WEIRD = ["a|b", "back\\slash", "line1\nline2", "caf\u00e9 \u2603 \U0001f600", "p|\\|\n|\u00e9"]


# --- A: random op sequences


class _World:
    """One session plus the bookkeeping the random ops need."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.ss = _new_session()
        self.k = 0
        self.nodes: list[str] = []
        self.edges: list[str] = []

    def fresh(self, p: str) -> str:
        self.k += 1
        return f"{p}{self.k}"

    def pick_node(self):
        return self.rng.choice(self.nodes) if self.nodes else None

    def _refresh(self) -> None:
        live = {r.fields.get("id") for r in self.ss.store.list_records(None)}
        self.nodes = [n for n in self.nodes if n in live]
        self.edges = [e for e in self.edges if e in live]

    # --- ops -------------------------------------------------------------
    def op_create_node(self):
        nid = self.fresh("N")
        tag = self.rng.choice(["MOD", "SYM"])
        body = "path: 'p', note: 'n'" if tag == "MOD" else "kind: 'k', refdes: 'r'"
        if _try(self.ss, [f"CREATE (:{tag} {{id: '{nid}', {body}}})"]):
            self.nodes.append(nid)

    def op_set_field(self):
        nid = self.pick_node()
        if nid:
            val = "v" * self.rng.randint(0, 40)
            _try(self.ss, [f"MATCH (n {{id: '{nid}'}}) SET n.kind = '{val}'"], mode="mutate")
            _try(self.ss, [f"MATCH (n {{id: '{nid}'}}) SET n.note = '{val}'"], mode="mutate")

    def op_set_weird(self):
        nid = self.pick_node()
        if nid:
            raw = self.rng.choice(_WEIRD)
            esc = raw.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
            _try(self.ss, [f"MATCH (n {{id: '{nid}'}}) SET n.note = '{esc}'"], mode="mutate")

    def op_delete_node(self):
        nid = self.pick_node()
        if nid:
            _try(self.ss, [f"MATCH (n {{id: '{nid}'}}) DETACH DELETE n"], mode="mutate")
            self._refresh()

    def op_delete_edge(self):
        if self.edges:
            eid = self.rng.choice(self.edges)
            _try(self.ss, [f"MATCH ()-[e {{id: '{eid}'}}]->() DELETE e"], mode="mutate")
            self._refresh()

    def op_create_edge(self):
        if len(self.nodes) >= 2:
            a, b = self.rng.sample(self.nodes, 2)
            eid = self.fresh("E")
            if _try(self.ss, [_edge_stmt(a, b, eid)], allow_new_relation=True):
                self.edges.append(eid)

    def op_rename(self):
        nid = self.pick_node()
        if nid:
            new = self.fresh("R") + "x" * self.rng.randint(0, 12)
            if _try(self.ss, [f"MATCH (n {{id: '{nid}'}}) SET n.id = '{new}'"], mode="update"):
                self.nodes[self.nodes.index(nid)] = new

    def op_set_undeclared(self):
        nid = self.pick_node()
        if nid:
            key = f"x{self.rng.randint(0, 3)}"
            _try(self.ss, [f"MATCH (n {{id: '{nid}'}}) SET n.{key} = 'u'"], mode="mutate")

    def op_remove_last_extra_row(self):
        for rec in list(self.ss.store.list_records(None)):
            if rec.tag in ("MOD", "SYM") and any(k.startswith("x") for k in rec.fields):
                _try(
                    self.ss,
                    [f"MATCH (n {{id: '{rec.fields['id']}'}}) DETACH DELETE n"],
                    mode="mutate",
                )
                self._refresh()
                return

    def op_save_load(self):
        self.ss = load_snapshot_text(snapshot_text(self.ss))

    def op_import_slice(self):
        suffix = self.fresh("i")
        member = _member(suffix)
        sl = export_working_memory_slice(member, anchors=[f"IM_{suffix}"], depth=2)
        try:
            absorb_working_memory_slice(self.ss, sl, enable_guard=False)
        except MemNetError:
            return
        self.nodes += [f"IM_{suffix}", f"IS_{suffix}"]
        self.edges.append(f"IE_{suffix}")

    def op_hydrate(self):
        prefix = self.fresh("H")
        owner = _owner_with(prefix)
        try:
            owner.hydrate_into_session(self.ss, f"{prefix}_ego")
        except MemNetError:
            return
        self.nodes += [f"{prefix}_ego", f"{prefix}_o"]
        self.edges.append(f"{prefix}_e")

    def op_cli_delete(self):
        nid = self.pick_node()
        if nid:
            runner.invoke(app, ["delete", "--id", nid, "--session", self.ss.session_id])
            self._refresh()

    OPS = (
        "op_create_node",
        "op_create_node",
        "op_create_node",
        "op_set_field",
        "op_set_weird",
        "op_delete_node",
        "op_delete_edge",
        "op_create_edge",
        "op_create_edge",
        "op_rename",
        "op_set_undeclared",
        "op_remove_last_extra_row",
        "op_save_load",
        "op_import_slice",
        "op_hydrate",
        "op_cli_delete",
    )


@pytest.mark.parametrize("seed", range(60))
def test_random_ops_incremental_equals_full_recount(memnet_temp, seed):
    world = _World(random.Random(seed))
    _assert_equal(world.ss)
    for _ in range(25):
        getattr(world, world.rng.choice(_World.OPS))()
        _assert_equal(world.ss)


# --- B: targeted cases


def test_b_leftover_nick_invalid_or_absent_id(memnet_temp):
    ss = _new_session()
    _gate(ss).apply(["CREATE (:MOD {id: 'A', path: 'p', note: 'n'})"], mode="add")
    ss.store.upsert(Record(tag="MOD", fields={"path": "no id"}))
    ss.store.upsert(Record(tag="MOD", fields={"id": "bad id!", "path": "p"}))
    ss.mark_written()
    _assert_equal(ss)
    _gate(ss).apply(["MATCH (n {id: 'A'}) SET n.note = 'again'"], mode="mutate")
    _assert_equal(ss)


def test_b_undeclared_key_widens_schema_for_all_rows_of_tag(memnet_temp):
    ss = _new_session()
    n_mod = 5
    _gate(ss).apply(
        [f"CREATE (:MOD {{id: 'M{i}', path: 'p', note: 'n'}})" for i in range(n_mod)]
        + ["CREATE (:SYM {id: 'S0', kind: 'k', refdes: 'r'})"],
        mode="add",
    )
    base = _assert_equal(ss)
    for step, key in enumerate(["extra1", "ex2"], start=1):
        _gate(ss).apply([f"MATCH (n {{id: 'M0'}}) SET n.{key} = 'val'"], mode="mutate")
        total = _assert_equal(ss)
        # schema line grows by " <key>", every MOD row by one "|", M0 also by its value
        expect = base + (1 + len(key)) + n_mod + len("val")
        assert total == expect, f"step {step}: {total} != {expect}"
        base = total


def test_b_removing_last_row_with_key_narrows_schema(memnet_temp):
    ss = _new_session()
    _gate(ss).apply(
        [
            "CREATE (:MOD {id: 'M0', path: 'p', note: 'n'})",
            "CREATE (:MOD {id: 'M1', path: 'p', note: 'n'})",
        ],
        mode="add",
    )
    before = _assert_equal(ss)
    _gate(ss).apply(["MATCH (n {id: 'M0'}) SET n.wide = 'w'"], mode="mutate")
    assert _assert_equal(ss) > before
    _gate(ss).apply(["MATCH (n {id: 'M0'}) DETACH DELETE n"], mode="mutate")
    _assert_equal(ss)
    _gate(ss).apply(["MATCH (n {id: 'M1'}) SET n.wide = 'w'"], mode="mutate")
    _gate(ss).apply(["MATCH (n {id: 'M1'}) DETACH DELETE n"], mode="mutate")
    assert _assert_equal(ss) == _body_bytes(_new_session())


def test_b_rename_changes_incident_edge_lines_by_nick_delta(memnet_temp):
    ss = _new_session()
    _gate(ss).apply(
        [
            "CREATE (:MOD {id: 'A', path: 'p', note: 'n'})",
            "CREATE (:SYM {id: 'B', kind: 'k', refdes: 'r'})",
            "CREATE (:SYM {id: 'C', kind: 'k', refdes: 'r'})",
        ],
        mode="add",
    )
    _gate(ss).apply(
        [_edge_stmt("A", "B", "E1"), _edge_stmt("C", "A", "E2")],
        mode="add",
        allow_new_relation=True,
    )
    before = _assert_equal(ss)
    new = "A_much_longer_name"
    _gate(ss).apply([f"MATCH (n {{id: 'A'}}) SET n.id = '{new}'"], mode="update")
    after = _assert_equal(ss)
    delta = len(new) - len("A")
    assert after - before == delta * 3  # the node line and its two incident edge lines


def test_b_relation_folding_raw_vs_folded(memnet_temp):
    ss = _new_session()
    _gate(ss).apply(
        [
            "CREATE (:MOD {id: 'A', path: 'p', note: 'n'})",
            "CREATE (:SYM {id: 'B', kind: 'k', refdes: 'r'})",
        ],
        mode="add",
    )
    ss.store.upsert(
        Record(tag="EDG", fields={"id": "E_raw", "src": "A", "relation": "HAS_FACT", "dist": "B"}),
        allow_new_relation=True,
    )
    ss.mark_written()
    _assert_equal(ss)
    ss.store.upsert(
        Record(tag="EDG", fields={"id": "E_fold", "src": "A", "relation": "hasFact", "dist": "B"}),
        allow_new_relation=True,
    )
    ss.mark_written()
    _assert_equal(ss)
    lines = {ln.split("|")[0]: ln for ln in _body_lines(ss) if ln.startswith("@EDG: E_")}
    # The stored-raw edge is emitted folded: same line shape as the already-folded one.
    assert len(lines["@EDG: E_fold"]) - len(lines["@EDG: E_raw"]) == len("E_fold") - len("E_raw")


def test_b_idless_legacy_edge_row(memnet_temp):
    ss = _new_session()
    _gate(ss).apply(
        [
            "CREATE (:MOD {id: 'A', path: 'p', note: 'n'})",
            "CREATE (:SYM {id: 'B', kind: 'k', refdes: 'r'})",
        ],
        mode="add",
    )
    ss.store.upsert(
        Record(tag="EDG", fields={"id": "", "src": "A", "relation": "mentions", "dist": "B"}),
        allow_new_relation=True,
    )
    ss.mark_written()
    _assert_equal(ss)
    _gate(ss).apply(["MATCH (n {id: 'A'}) SET n.id = 'A_renamed'"], mode="update")
    _assert_equal(ss)


# --- C: rollback


def _seed_two(ss):
    _gate(ss).apply(
        [
            "CREATE (:MOD {id: 'MOD_a', path: 'p', note: 'n'})",
            "CREATE (:SYM {id: 'SYM_b', kind: 'k', refdes: 'r'})",
            _edge_stmt("MOD_a", "SYM_b", "E_ab"),
        ],
        mode="add",
        allow_new_relation=True,
    )


def _assert_refused_unchanged_then_writes(ss, before_bytes, before_content):
    assert _assert_equal(ss) == before_bytes
    assert _content(ss) == before_content
    _gate(ss).apply(["CREATE (:SYM {id: 'NEXT', kind: 'k', refdes: 'r'})"], mode="add")
    _assert_equal(ss)


def test_c_import_over_budget_rolls_back(memnet_temp):
    ss = _new_session()
    _seed_two(ss)
    member = _member("z")
    sl = export_working_memory_slice(member, anchors=["IM_z"], depth=2)
    before_bytes, before_content = _assert_equal(ss), _content(ss)
    ss.caps.max_session_bytes = before_bytes + 5
    with pytest.raises(MemNetError) as ei:
        absorb_working_memory_slice(ss, sl, enable_guard=False)
    assert ei.value.message.startswith("session_bytes|")
    ss.caps.max_session_bytes = Caps().max_session_bytes
    _assert_refused_unchanged_then_writes(ss, before_bytes, before_content)


def test_c_hydrate_over_budget_rolls_back(memnet_temp):
    ss = _new_session()
    _seed_two(ss)
    owner = _owner_with("HY")
    before_bytes, before_content = _assert_equal(ss), _content(ss)
    ss.caps.max_session_bytes = before_bytes + 5
    with pytest.raises(MemNetError) as ei:
        owner.hydrate_into_session(ss, "HY_ego")
    assert ei.value.message.startswith("session_bytes|")
    ss.caps.max_session_bytes = Caps().max_session_bytes
    _assert_refused_unchanged_then_writes(ss, before_bytes, before_content)


def test_c_prune_line_cap_refusal_rolls_back(memnet_temp, monkeypatch):
    ss = _new_session()
    _seed_two(ss)
    _gate(ss).apply(["CREATE (:SYM {id: 'L1', kind: 'k', refdes: 'r'})"], mode="add")
    rows = [ss.store.get("L1")]
    before_bytes, before_content = _assert_equal(ss), _content(ss)

    def boom(*_a, **_k):
        raise MemNetError("limit_exceeded", "line_bytes|9/8")

    monkeypatch.setattr("memnet.snapshot.refuse_mutate_line_cap", boom)
    with pytest.raises(MemNetError):
        prune_rows(ss, rows)
    monkeypatch.undo()
    _assert_refused_unchanged_then_writes(ss, before_bytes, before_content)


def test_c_cli_delete_line_cap_refusal_rolls_back(memnet_temp, monkeypatch):
    ss = _new_session()
    eid = "E1_" + "e" * 40
    _gate(ss).apply(
        [
            "CREATE (:SYM {id: 'A1', kind: 'k', refdes: 'r'})",
            "CREATE (:SYM {id: 'B1', kind: 'k', refdes: 'r'})",
            _edge_stmt("A1", "B1", eid),
        ],
        mode="add",
        allow_new_relation=True,
    )
    fit = max(len(ln.encode()) for ln in _body_lines(ss))
    before_bytes, before_content = _assert_equal(ss), _content(ss)
    monkeypatch.setenv("MEMNET_MAX_LINE_BYTES", str(fit))
    # The CLI reads caps from the registered session; set it on the live caps too.
    ss.caps.max_line_bytes = fit
    r = runner.invoke(app, ["delete", "--id", "A1", "--session", ss.session_id])
    assert r.exit_code != 0 and "line_bytes" in r.stderr
    ss.caps.max_line_bytes = Caps().max_line_bytes
    _assert_refused_unchanged_then_writes(ss, before_bytes, before_content)


def test_c_plain_raise_inside_bypass_guard(memnet_temp):
    ss = _new_session()
    _seed_two(ss)
    before_bytes, before_content = _assert_equal(ss), _content(ss)
    with pytest.raises(RuntimeError), bypass_guard(ss):
        ss.relations.add("NEWREL")
        ss.store.delete("SYM_b")
        ss.store.upsert(Record(tag="SYM", fields={"id": "TMP", "kind": "k", "refdes": "r"}))
        raise RuntimeError("boom")
    _assert_refused_unchanged_then_writes(ss, before_bytes, before_content)


def test_c_rename_inside_bypass_guard_then_raise(memnet_temp):
    """The store keeps in-place edits on rollback; only incremental == full is pinned."""
    ss = _new_session()
    _seed_two(ss)
    with pytest.raises(RuntimeError), bypass_guard(ss):
        ss.store.rename_id("MOD_a", "MOD_a_renamed_longer")
        raise RuntimeError("boom")
    _assert_equal(ss)
    _gate(ss).apply(["CREATE (:SYM {id: 'NEXT', kind: 'k', refdes: 'r'})"], mode="add")
    _assert_equal(ss)


def test_c_merge_inside_bypass_guard_then_raise(memnet_temp):
    ss = _new_session()
    _seed_two(ss)
    _gate(ss).apply(["CREATE (:MOD {id: 'MOD_dup', path: 'q', note: 'm'})"], mode="add")
    _gate(ss).apply([_edge_stmt("MOD_dup", "SYM_b", "E_dup")], mode="add")
    with pytest.raises(RuntimeError), bypass_guard(ss):
        ss.store.rename_id("MOD_dup", "MOD_a", merge=True)
        raise RuntimeError("boom")
    _assert_equal(ss)
    _gate(ss).apply(["MATCH (n {id: 'SYM_b'}) SET n.kind = 'changed'"], mode="mutate")
    _assert_equal(ss)


def test_c_mutate_gate_refusal_then_success(memnet_temp):
    ss = _new_session()
    _seed_two(ss)
    before_bytes, before_content = _assert_equal(ss), _content(ss)
    # over budget
    ss.caps.max_session_bytes = before_bytes + 3
    with pytest.raises(MemNetError) as ei:
        _gate(ss).apply(["CREATE (:SYM {id: 'BIG', kind: 'kkkkkkkk', refdes: 'r'})"], mode="add")
    assert ei.value.message.startswith("session_bytes|")
    ss.caps.max_session_bytes = Caps().max_session_bytes
    # over line cap
    ss.caps.max_line_bytes = 40
    with pytest.raises(MemNetError) as ei:
        _gate(ss).apply(
            ["CREATE (:SYM {id: 'LONG', kind: '" + "k" * 80 + "', refdes: 'r'})"], mode="add"
        )
    assert ei.value.message.startswith("line_bytes|")
    ss.caps.max_line_bytes = Caps().max_line_bytes
    _assert_refused_unchanged_then_writes(ss, before_bytes, before_content)


def test_c_exception_inside_reemit_then_fixed(memnet_temp, monkeypatch):
    """An unsaveable state (EDG with no emit row) raises mid-check; fixing it resyncs."""
    import memnet.session_bytes as sb

    ss = _new_session()
    _seed_two(ss)
    _assert_equal(ss)
    saved = ss.store.get("E_ab")
    ss.store.delete("E_ab")
    # a record whose tag has no emit row: fixed tag stripped from the emit map
    bad = Record(
        tag="EDG", fields={"id": "", "src": "MOD_a", "relation": "mentions", "dist": "SYM_b"}
    )
    ss.store.upsert(bad, allow_new_relation=True)
    import memnet.snapshot as snap

    real = snap._snapshot_emit_tag_map

    def no_edg_row(s):
        tm = real(s)
        tm.tags.pop("EDG", None)
        return tm

    with monkeypatch.context() as mp:
        mp.setattr(snap, "_snapshot_emit_tag_map", no_edg_row)
        try:
            _gate(ss).apply(["MATCH (n {id: 'MOD_a'}) SET n.note = 'z'"], mode="mutate")
        except MemNetError as exc:
            assert exc.code == "snapshot_unsaveable"
        with pytest.raises(MemNetError):
            sb.full_recount_total(ss)
    # fix the state, then the next total equals the full recount
    ss.store.delete(bad.hid)
    ss.store.upsert(saved, allow_new_relation=True)
    ss.mark_written()
    _assert_equal(ss)
    _gate(ss).apply(["MATCH (n {id: 'MOD_a'}) SET n.note = 'fixed'"], mode="mutate")
    _assert_equal(ss)


# --- D: semantics (green before and after)


def _build_rows(n: int, budget: int | None = None):
    ss = _new_session()
    _gate(ss).apply(
        [f"CREATE (:MOD {{id: 'M{i}', path: 'p', note: '{'x' * 100}'}})" for i in range(n)],
        mode="add",
    )
    if budget is not None:
        ss.caps.max_session_bytes = budget
    return ss


def _legacy_message(ss) -> str:
    """Call the pre-existing budget path directly on ``ss``; return its refusal message."""
    import memnet.snapshot as snap

    emit_map = snap._snapshot_emit_tag_map(ss)
    schema_total = sum(len(ln.encode()) for ln in snap.tag_map_to_lines(emit_map))
    with pytest.raises(MemNetError) as ei:
        snap._refuse_session_bytes(ss, snap._snapshot_nicks(ss), emit_map, schema_total)
    assert ei.value.code == "limit_exceeded"
    return ei.value.message


def test_d_default_budget_constant(monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_SESSION_BYTES", raising=False)
    assert Caps().max_session_bytes == 163840000
    try:
        from memnet.config import DEFAULT_MAX_SESSION_BYTES
    except ImportError:
        return
    assert DEFAULT_MAX_SESSION_BYTES == 163840000


def test_d_refused_total_equals_legacy_partial_sum(memnet_temp):
    n_rows = 6
    new_stmt = f"CREATE (:MOD {{id: 'M{n_rows}', path: 'p', note: '{'x' * 100}'}})"
    probe = _build_rows(n_rows)
    _gate(probe).apply([new_stmt], mode="add")
    full = _body_bytes(probe)
    row = len(f"@MOD: M0|p|{'x' * 100}".encode())
    budget = full - 3 * row - 5  # crossed while summing rows, long before the last one
    probe.caps.max_session_bytes = budget
    expected = _legacy_message(probe)
    reported = int(expected.split("|")[1].split("/")[0])
    assert expected == f"session_bytes|{reported}/{budget}"
    assert reported != full  # a partial sum in write_order, not the whole total

    ss = _build_rows(n_rows, budget)
    before = _body_lines(ss)
    with pytest.raises(MemNetError) as ei:
        _gate(ss).apply([new_stmt], mode="add")
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == expected
    assert _body_lines(ss) == before  # a refused write leaves the snapshot unchanged


def test_d_delete_and_prune_not_refused_by_budget(memnet_temp):
    ss = _new_session()
    _seed_two(ss)
    _gate(ss).apply(["CREATE (:SYM {id: 'LONE', kind: 'k', refdes: 'r'})"], mode="add")
    ss.caps.max_session_bytes = 1
    _gate(ss).apply(["MATCH (n {id: 'SYM_b'}) DETACH DELETE n"], mode="mutate")
    assert ss.store.get("SYM_b") is None
    prune_rows(ss, [ss.store.get("LONE")])
    assert ss.store.get("LONE") is None


def test_d_delete_still_refused_by_line_cap(memnet_temp, monkeypatch):
    ss = _new_session()
    eid = "E1_" + "e" * 40
    _gate(ss).apply(
        [
            "CREATE (:SYM {id: 'A1', kind: 'k', refdes: 'r'})",
            "CREATE (:SYM {id: 'B1', kind: 'k', refdes: 'r'})",
            _edge_stmt("A1", "B1", eid),
        ],
        mode="add",
        allow_new_relation=True,
    )
    fit = max(len(ln.encode()) for ln in _body_lines(ss))
    monkeypatch.setenv("MEMNET_MAX_LINE_BYTES", str(fit))
    monkeypatch.setenv("MEMNET_MAX_SESSION_BYTES", "1")
    before = _body_lines(ss)
    r = runner.invoke(app, ["delete", "--id", "A1", "--session", ss.session_id])
    assert r.exit_code != 0
    assert "line_bytes" in r.stderr and "session_bytes" not in r.stderr
    assert _body_lines(ss) == before


# --- E: cost guard


class _Counter:
    def __init__(self, real) -> None:
        self.real = real
        self.n = 0

    def __call__(self, fields):
        self.n += 1
        return self.real(fields)


def _install_counter(monkeypatch) -> _Counter:
    import memnet.output
    import memnet.wire

    counter = _Counter(memnet.wire.join_payload)
    monkeypatch.setattr(memnet.output, "join_payload", counter)
    monkeypatch.setattr(memnet.wire, "join_payload", counter)
    return counter


def _big_session(n_rows: int, note_len: int):
    ss = _new_session()
    note = "n" * note_len
    for i in range(n_rows):
        ss.store.upsert(Record(tag="MOD", fields={"id": f"R{i:04d}", "path": "p", "note": note}))
    ss.mark_written()
    return ss


def test_e_one_write_reencodes_few_rows(memnet_temp, monkeypatch):
    monkeypatch.delenv("MEMNET_DEBUG_SESSION_BYTES", raising=False)
    ss = _big_session(300, 2000)
    ss.store.upsert(Record(tag="SYM", fields={"id": "HUB", "kind": "k", "refdes": "r"}))
    ss.store.upsert(Record(tag="SYM", fields={"id": "DEL", "kind": "k", "refdes": "r"}))
    ss.mark_written()
    _gate(ss).apply(
        [
            _edge_stmt("DEL", "HUB", "ED1"),
            _edge_stmt("HUB", "DEL", "ED2"),
            _edge_stmt("DEL", "R0001", "ED3"),
        ],
        mode="add",
        allow_new_relation=True,
    )
    _gate(ss).apply(["MATCH (n {id: 'R0000'}) SET n.path = 'warm'"], mode="mutate")
    counter = _install_counter(monkeypatch)

    _gate(ss).apply(["MATCH (n {id: 'R0100'}) SET n.path = 'changed'"], mode="mutate")
    assert counter.n <= 25, f"SET re-encoded {counter.n} lines"

    counter.n = 0
    _gate(ss).apply(["CREATE (:MOD {id: 'FRESH', path: 'p', note: 'n'})"], mode="add")
    assert counter.n <= 25, f"CREATE re-encoded {counter.n} lines"

    counter.n = 0
    _gate(ss).apply(["MATCH (n {id: 'DEL'}) DETACH DELETE n"], mode="mutate")
    assert counter.n <= 25, f"DELETE re-encoded {counter.n} lines"


# --- F: perf guard + flag-off exactness


@pytest.mark.perf
@pytest.mark.skipif(
    not os.environ.get("MEMNET_PERF"), reason="near-cap timing guard: MEMNET_PERF=1"
)
def test_f_perf_near_cap_write_is_fast(memnet_temp, monkeypatch):
    monkeypatch.delenv("MEMNET_DEBUG_SESSION_BYTES", raising=False)
    ss = _big_session(600, 30000)
    total = _body_bytes(ss)
    monkeypatch.setenv("MEMNET_MAX_SESSION_BYTES", str(int(total * 1.01)))
    ss.caps.max_session_bytes = int(total * 1.01)
    _gate(ss).apply(["MATCH (n {id: 'R0000'}) SET n.path = 'warm'"], mode="mutate")
    t0 = time.perf_counter()
    _gate(ss).apply(["MATCH (n {id: 'R0300'}) SET n.path = 'timed'"], mode="mutate")
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.300, f"one GQL SET near the cap took {elapsed:.3f}s"

    ss.caps.max_session_bytes = _body_bytes(ss) + 100
    t0 = time.perf_counter()
    with pytest.raises(MemNetError) as ei:
        _gate(ss).apply(
            ["CREATE (:MOD {id: 'OVER', path: 'p', note: '" + "o" * 30000 + "'})"], mode="add"
        )
    elapsed = time.perf_counter() - t0
    assert ei.value.message.startswith("session_bytes|")
    assert elapsed < 1.0, f"budget refusal took {elapsed:.3f}s"


def test_f_flag_off_incremental_is_exact(memnet_temp, monkeypatch):
    import memnet.session_bytes as sb

    monkeypatch.delenv("MEMNET_DEBUG_SESSION_BYTES", raising=False)
    world = _World(random.Random(7))
    for _ in range(40):
        getattr(world, world.rng.choice(_World.OPS))()
    inc = sb.incremental_total(world.ss)
    assert inc is not None
    assert inc == _body_bytes(world.ss)
