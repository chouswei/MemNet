"""MN-REQ-14.11 — write paths that bypass the mutate gate enforce the same caps.

Snapshot import (import_absorb), durable hydrate and CLI delete/prune: value cap,
whole-line cap, session byte budget. Refusal is atomic (session unchanged).
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from memnet.bypass_caps import bypass_guard
from memnet.cli import app
from memnet.durable import DurableSubgraph, DurableSyncOwner, FakeDurableAdapter, HydrateBudget
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
from memnet.snapshot import snapshot_text

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


def _state(ss):
    # Content only: the @SNAP clock line moves on any session touch, refused or not.
    return _body_lines(ss), set(ss.relations), list(ss.store.write_order)


def _member(path: str = "p", note: str = "n"):
    member = open_session(map_lines=_MAP)
    MutateGate(member).apply(
        [
            f"CREATE (:MOD {{id: 'MOD_a', path: '{path}', note: '{note}'}})",
            "CREATE (:SYM {id: 'SYM_b', kind: 'k', refdes: 'r'})",
            "MATCH (a {id: 'MOD_a'}), (b {id: 'SYM_b'})\nCREATE (a)-[:mentions {id: 'E_ab'}]->(b)",
        ],
        mode="add",
        allow_new_relation=True,
    )
    return member


def _slice(member):
    return export_working_memory_slice(member, anchors=["MOD_a"], depth=2)


def _lead_with_seed():
    lead = open_session(map_lines=_MAP)
    MutateGate(lead).apply(["CREATE (:SYM {id: 'SYM_seed', kind: 'k', refdes: 'r'})"], mode="add")
    return lead


def _import(lead, member):
    return absorb_working_memory_slice(lead, _slice(member), enable_guard=False)


# ---------------------------------------------------------------- import


def test_import_value_cap_refused_and_session_unchanged(memnet_temp):
    member = _member(note="x" * 200)
    lead = _lead_with_seed()
    lead.caps.max_value_bytes = 199
    before = _state(lead)
    with pytest.raises(MemNetError) as ei:
        _import(lead, member)
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == "value_bytes|200/199"
    assert _state(lead) == before


def test_import_value_cap_just_fitting_ok(memnet_temp):
    member = _member(note="x" * 200)
    lead = _lead_with_seed()
    lead.caps.max_value_bytes = 200
    res = _import(lead, member)
    assert len(res.imported_ids) == 3


def test_import_line_cap_refused_and_session_unchanged(memnet_temp):
    member = _member(path="p" * 60, note="n" * 60)
    probe = open_session(map_lines=_MAP)
    _import(probe, member)
    longest = max(len(ln.encode()) for ln in _body_lines(probe))

    lead = _lead_with_seed()
    lead.caps.max_line_bytes = longest - 1
    before = _state(lead)
    with pytest.raises(MemNetError) as ei:
        _import(lead, member)
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == f"line_bytes|{longest}/{longest - 1}"
    assert _state(lead) == before


def test_import_line_cap_just_fitting_ok(memnet_temp):
    member = _member(path="p" * 60, note="n" * 60)
    probe = open_session(map_lines=_MAP)
    _import(probe, member)
    longest = max(len(ln.encode()) for ln in _body_lines(probe))
    lead = _lead_with_seed()
    lead.caps.max_line_bytes = longest
    assert len(_import(lead, member).imported_ids) == 3


def test_import_session_budget_refused_and_session_unchanged(memnet_temp):
    member = _member()
    probe = _lead_with_seed()
    _import(probe, member)
    total = sum(len(ln.encode()) for ln in _body_lines(probe))

    lead = _lead_with_seed()
    lead.caps.max_session_bytes = total - 1
    before = _state(lead)
    with pytest.raises(MemNetError) as ei:
        _import(lead, member)
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == f"session_bytes|{total}/{total - 1}"
    assert "MEMNET_MAX_SESSION_BYTES" in (ei.value.example or "")
    assert _state(lead) == before
    assert lead.store.get("MOD_a") is None


def test_import_session_budget_just_fitting_ok(memnet_temp):
    member = _member()
    probe = _lead_with_seed()
    _import(probe, member)
    total = sum(len(ln.encode()) for ln in _body_lines(probe))
    lead = _lead_with_seed()
    lead.caps.max_session_bytes = total
    assert len(_import(lead, member).imported_ids) == 3
    assert lead.store.get("MOD_a") is not None


def test_import_merge_refusal_restores_replaced_row(memnet_temp):
    """keep-policy MERGE replaces an existing row; a refusal puts the old row back."""
    member = _member(note="n" * 100)
    lead = open_session(map_lines=_MAP)
    MutateGate(lead).apply(["CREATE (:MOD {id: 'MOD_a', path: 'old', note: 'old'})"], mode="add")
    lead.caps.max_line_bytes = 60
    before = _state(lead)
    with pytest.raises(MemNetError):
        _import(lead, member)
    assert _state(lead) == before
    assert lead.store.get("MOD_a").fields["note"] == "old"


# --------------------------------------------------------------- hydrate


def _owner(subgraph: DurableSubgraph) -> DurableSyncOwner:
    adapter = FakeDurableAdapter()
    adapter.seed(subgraph)
    return DurableSyncOwner(adapter)


def _ego(note: str = "n") -> DurableSubgraph:
    ego = Record(tag="MOD", fields={"id": "MOD_ego", "path": "p", "note": note})
    other = Record(tag="SYM", fields={"id": "SYM_o", "kind": "k", "refdes": "r"})
    edge = Record(
        tag="EDG",
        fields={"id": "E_eo", "src": "MOD_ego", "relation": "MENTIONS", "dist": "SYM_o"},
    )
    return DurableSubgraph(
        ego_id="MOD_ego", nodes=[ego, other], edges=[edge], relations={"MENTIONS"}
    )


def test_hydrate_value_cap_refused_and_session_unchanged(memnet_temp):
    owner = _owner(_ego(note="x" * 200))
    ss = _lead_with_seed()
    ss.caps.max_value_bytes = 199
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        owner.hydrate_into_session(ss, "MOD_ego")
    assert ei.value.message == "value_bytes|200/199"
    assert _state(ss) == before


def test_hydrate_value_cap_just_fitting_ok(memnet_temp):
    owner = _owner(_ego(note="x" * 200))
    ss = _lead_with_seed()
    ss.caps.max_value_bytes = 200
    owner.hydrate_into_session(ss, "MOD_ego")
    assert ss.store.get("MOD_ego") is not None


def test_hydrate_line_cap_refused_and_session_unchanged(memnet_temp):
    owner = _owner(_ego(note="n" * 80))
    probe = open_session(map_lines=_MAP)
    owner.hydrate_into_session(probe, "MOD_ego")
    longest = max(len(ln.encode()) for ln in _body_lines(probe))

    ss = _lead_with_seed()
    ss.caps.max_line_bytes = longest - 1
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        owner.hydrate_into_session(ss, "MOD_ego")
    assert ei.value.message == f"line_bytes|{longest}/{longest - 1}"
    assert _state(ss) == before

    ss.caps.max_line_bytes = longest
    owner.hydrate_into_session(ss, "MOD_ego")
    assert ss.store.get("MOD_ego") is not None


def test_hydrate_over_budget_refuses_atomically_and_durable_untouched(memnet_temp):
    owner = _owner(_ego())
    probe = _lead_with_seed()
    owner.hydrate_into_session(probe, "MOD_ego")
    total = sum(len(ln.encode()) for ln in _body_lines(probe))

    ss = _lead_with_seed()
    ss.caps.max_session_bytes = total - 1
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        owner.hydrate_into_session(ss, "MOD_ego")
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == f"session_bytes|{total}/{total - 1}"
    assert "MEMNET_MAX_SESSION_BYTES" in (ei.value.example or "")
    assert _state(ss) == before
    # durable data untouched: the same ego still hydrates in full
    again = owner.adapter.hydrate("MOD_ego", HydrateBudget())
    assert len(again.nodes) == 2 and len(again.edges) == 1

    ss.caps.max_session_bytes = total  # just fitting
    owner.hydrate_into_session(ss, "MOD_ego")
    assert ss.store.get("MOD_ego") is not None


def test_hydrate_into_session_already_over_lowered_budget_refuses(memnet_temp):
    owner = _owner(_ego())
    ss = _lead_with_seed()
    owner.hydrate_into_session(ss, "MOD_ego")  # fits under the default budget
    ss.caps.max_session_bytes = 10  # setting lowered afterwards
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        owner.hydrate_into_session(ss, "MOD_ego")
    assert ei.value.message.startswith("session_bytes|")
    assert _state(ss) == before


# ------------------------------------------------------------ CLI delete


_EID = "E1_" + "e" * 40  # edge line longer than any SCHEMA line


def _cli_session(monkeypatch=None):
    sid = open_session(map_lines=_MAP).session_id
    from memnet.session import get_session

    ss = get_session(sid)
    MutateGate(ss).apply(
        [
            "CREATE (:SYM {id: 'A1', kind: 'k', refdes: 'r'})",
            "CREATE (:SYM {id: 'B1', kind: 'k', refdes: 'r'})",
            "MATCH (a {id: 'A1'}), (b {id: 'B1'})\nCREATE (a)-[:mentions {id: '"
            + _EID
            + "'}]->(b)",
        ],
        mode="add",
        allow_new_relation=True,
    )
    return sid, ss


def _edge_line_len(ss) -> int:
    return max(len(ln.encode()) for ln in _body_lines(ss) if _EID in ln)


def test_cli_delete_node_whose_edge_line_would_exceed_cap_is_refused(memnet_temp, monkeypatch):
    # Deleting A1 leaves edge E1 pointing at A1's longer hidden handle.
    sid, ss = _cli_session()
    fit = _edge_line_len(ss)
    monkeypatch.setenv("MEMNET_MAX_LINE_BYTES", str(fit))
    before = _state(ss)
    r = runner.invoke(app, ["delete", "--id", "A1", "--session", sid])
    assert r.exit_code != 0
    assert "limit_exceeded" in r.stderr and "line_bytes" in r.stderr
    assert _state(ss) == before
    assert ss.store.get("A1") is not None


def test_cli_delete_node_edge_line_just_fitting_ok(memnet_temp, monkeypatch):
    sid, ss = _cli_session()
    fit = _edge_line_len(ss)
    r0 = runner.invoke(app, ["delete", "--id", "A1", "--session", sid])  # uncapped probe
    assert r0.exit_code == 0
    grown = _edge_line_len(ss)
    assert grown > fit
    sid2, ss2 = _cli_session()
    monkeypatch.setenv("MEMNET_MAX_LINE_BYTES", str(grown))
    r = runner.invoke(app, ["delete", "--id", "A1", "--session", sid2])
    assert r.exit_code == 0
    assert ss2.store.get("A1") is None


def test_cli_delete_never_refused_by_session_budget(memnet_temp, monkeypatch):
    sid, ss = _cli_session()
    monkeypatch.setenv("MEMNET_MAX_SESSION_BYTES", "1")
    r = runner.invoke(app, ["delete", "--id", _EID, "--session", sid])
    assert r.exit_code == 0
    assert ss.store.get(_EID) is None


def test_cli_prune_never_refused_by_session_budget(memnet_temp, monkeypatch):
    sid, ss = _cli_session()
    MutateGate(ss).apply(["CREATE (:SYM {id: 'LONE', kind: 'k', refdes: 'r'})"], mode="add")
    monkeypatch.setenv("MEMNET_MAX_SESSION_BYTES", "1")
    r = runner.invoke(app, ["housekeep", "prune", "orphans", "--apply", "--session", sid])
    assert r.exit_code == 0
    assert ss.store.get("LONE") is None


def test_prune_rows_refusal_rolls_back_whole_batch(memnet_temp, monkeypatch):
    sid, ss = _cli_session()
    MutateGate(ss).apply(
        [
            "CREATE (:SYM {id: 'L1', kind: 'k', refdes: 'r'})",
            "CREATE (:SYM {id: 'L2', kind: 'k', refdes: 'r'})",
        ],
        mode="add",
    )
    rows = [ss.store.get("L1"), ss.store.get("L2")]
    before = _state(ss)

    def boom(*_a, **_k):
        raise MemNetError("limit_exceeded", "line_bytes|9/8")

    monkeypatch.setattr("memnet.snapshot.refuse_mutate_line_cap", boom)
    with pytest.raises(MemNetError):
        prune_rows(ss, rows)
    assert _state(ss) == before
    assert ss.store.get("L1") is not None and ss.store.get("L2") is not None


def test_bypass_guard_restores_relations_and_indexes(memnet_temp):
    ss = _lead_with_seed()
    before = _state(ss)
    with pytest.raises(RuntimeError), bypass_guard(ss):
        ss.relations.add("NEWREL")
        ss.store.delete("SYM_seed")
        raise RuntimeError("x")
    assert _state(ss) == before
    assert ss.store.match_nodes(tag="SYM", props={}) != []


# --- MN-REQ-14.11: load, save, ingest and the pipe protocol ----------------


def test_delete_skips_the_budget_check(memnet_temp, monkeypatch):
    """Spy: the budget helper is never called on a CLI delete, even over budget."""
    import memnet.snapshot as snap

    sid, ss = _cli_session()
    monkeypatch.setenv("MEMNET_MAX_SESSION_BYTES", "1")  # the session is over budget
    calls: list[int] = []
    real = snap._refuse_session_bytes
    monkeypatch.setattr(
        snap, "_refuse_session_bytes", lambda *a, **k: calls.append(1) or real(*a, **k)
    )
    r = runner.invoke(app, ["delete", "--id", _EID, "--session", sid])
    assert r.exit_code == 0
    assert ss.store.get(_EID) is None
    assert calls == []


def test_save_refuses_over_budget_session_and_writes_nothing(memnet_temp, monkeypatch, tmp_path):
    from memnet.snapshot import write_snapshot

    ss = _member()
    dest = tmp_path / "over.snap"
    monkeypatch.setenv("MEMNET_MAX_SESSION_BYTES", "10")
    ss.caps.max_session_bytes = 10
    with pytest.raises(MemNetError) as ei:
        write_snapshot(ss, dest)
    assert ei.value.code == "limit_exceeded" and ei.value.message.startswith("session_bytes|")
    assert not dest.exists()


def test_save_just_fitting_ok(memnet_temp, tmp_path):
    from memnet.snapshot import write_snapshot

    ss = _member()
    total = sum(len(ln.encode()) for ln in _body_lines(ss))
    ss.caps.max_session_bytes = total
    write_snapshot(ss, tmp_path / "fit.snap")
    assert (tmp_path / "fit.snap").exists()


def test_load_refuses_over_budget_snapshot_and_registers_nothing(memnet_temp, tmp_path):
    from memnet.config import Caps
    from memnet.snapshot import load_snapshot, write_snapshot

    ss = _member()
    path = tmp_path / "s.snap"
    write_snapshot(ss, path)
    total = sum(len(ln.encode()) for ln in _body_lines(ss))
    caps = Caps()
    caps.max_session_bytes = total - 1
    with pytest.raises(MemNetError) as ei:
        load_snapshot(path, caps=caps)
    assert ei.value.code == "limit_exceeded" and ei.value.message.startswith("session_bytes|")


def test_load_just_fitting_ok(memnet_temp, tmp_path):
    from memnet.config import Caps
    from memnet.snapshot import load_snapshot, write_snapshot

    ss = _member()
    path = tmp_path / "s.snap"
    write_snapshot(ss, path)
    caps = Caps()
    caps.max_session_bytes = sum(len(ln.encode()) for ln in _body_lines(ss))
    assert load_snapshot(path, caps=caps) is not None


def test_ingest_commit_over_budget_refused_and_session_unchanged(
    memnet_temp, monkeypatch, tmp_path
):
    from memnet.pin_map_ingest import PinMapIngest_Sysml

    ss = open_session(
        map_lines=["SCHEMA PKG ; fields=id name qname", "SCHEMA PRT ; fields=id name qname"]
    )
    model = tmp_path / "m.sysml"
    model.write_text("package P { part def A; part def B; }\n", encoding="utf-8")
    ss.caps.max_session_bytes = 10
    before = _state(ss)
    ing = PinMapIngest_Sysml()
    with pytest.raises(MemNetError) as ei:
        ing.ingest(ss, model)
    assert ei.value.code == "limit_exceeded" and "session_bytes" in ei.value.message
    assert _state(ss) == before


def test_pipe_mutate_session_bytes_refusal(memnet_temp, schema_file, monkeypatch):
    from memnet.in_process_engine import run_argv

    monkeypatch.setenv("MEMNET_MAX_SESSION_BYTES", "400")
    ss = open_session(map_file=str(schema_file))
    before = _state(ss)
    big = "CREATE (:TSK {id: 'TSK_big', goal: '" + "x" * 600 + "', status: 'open'})\n"
    r = run_argv(["mutate", "--stdin", "--session", ss.session_id], stdin=big)
    assert r["exit_code"] != 0
    assert "limit_exceeded" in r["stderr"] and "session_bytes" in r["stderr"]
    assert _state(ss) == before
    assert ss.store.get("TSK_big") is None
