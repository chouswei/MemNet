"""Path B ImportAbsorb / ImportGuard (MN-REQ-12.9–12.11)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from memnet.cli import app
from memnet.exceptions import MemNetError
from memnet.import_absorb import (
    ImportGuardDecision,
    WorkingMemorySlice,
    absorb_working_memory_slice,
    export_working_memory_slice,
    import_slice,
    reset_import_guard_for_tests,
    set_import_guard,
)
from memnet.mutate_gate import MutateGate
from memnet.session import get_session, open_session

runner = CliRunner()

_SEED = [
    "CREATE (:MOD {id: 'MOD_amp', path: 'docs/note.md', note: 'amp'})",
    "CREATE (:SYM {id: 'SYM_Rin', kind: 'resistor', refdes: 'Rin'})",
    "CREATE (:SYM {id: 'SYM_scratch', kind: 'noise', refdes: 'X'})",
    "MATCH (a {id: 'MOD_amp'}), (b {id: 'SYM_Rin'})\n"
    "CREATE (a)-[:mentions {id: 'EDG_amp_rin', recycle: 'persistent'}]->(b)",
    "MATCH (a {id: 'MOD_amp'}), (b {id: 'SYM_scratch'})\n"
    "CREATE (a)-[:mentions {id: 'EDG_amp_scratch', recycle: 'persistent'}]->(b)",
]

_MAP = [
    "SCHEMA MOD ; fields=id path note",
    "SCHEMA SYM ; fields=id kind refdes",
    "SCHEMA TSK ; fields=id goal status recycle",
]


@pytest.fixture(autouse=True)
def _reset_guard():
    reset_import_guard_for_tests()
    yield
    reset_import_guard_for_tests()


def _open_pair(schema_file):
    # Use schema_file for PLR maps from conftest; also seed custom via map lines.
    member = open_session(map_lines=_MAP)
    lead = open_session(map_lines=_MAP)
    gate = MutateGate(member)
    gate.apply(_SEED, mode="add", allow_new_relation=True)
    return member, lead


def test_import_keep_accepts_and_upserts(memnet_temp, schema_file):
    member, lead = _open_pair(schema_file)
    # Pre-seed conflicting MOD on lead — keep/MERGE should upsert.
    MutateGate(lead).apply(
        ["CREATE (:MOD {id: 'MOD_amp', path: 'old.md', note: 'stale'})"],
        mode="add",
        allow_new_relation=True,
    )
    result = import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        id_policy="keep",
        enable_guard=False,
    )
    assert "MOD_amp" in result.imported_ids
    assert "SYM_Rin" in result.imported_ids
    assert lead.store.get("MOD_amp").fields.get("path") == "docs/note.md"
    assert lead.store.get("EDG_amp_rin") is not None
    assert result.guard_skipped is True


def test_import_reject_on_conflict(memnet_temp, schema_file):
    member, lead = _open_pair(schema_file)
    MutateGate(lead).apply(
        ["CREATE (:MOD {id: 'MOD_amp', path: 'old.md', note: 'stale'})"],
        mode="add",
        allow_new_relation=True,
    )
    with pytest.raises(MemNetError) as ei:
        import_slice(
            lead_session_id=lead.session_id,
            source_session_id=member.session_id,
            anchors=["MOD_amp"],
            id_policy="reject",
            enable_guard=False,
        )
    assert ei.value.code == "id_conflict"
    # Lead unchanged beyond the pre-seed.
    assert lead.store.get("SYM_Rin") is None


def test_import_remint_conflicts(memnet_temp, schema_file):
    member, lead = _open_pair(schema_file)
    MutateGate(lead).apply(
        [
            "CREATE (:MOD {id: 'MOD_amp', path: 'old.md', note: 'stale'})",
            "CREATE (:SYM {id: 'SYM_Rin', kind: 'other', refdes: 'R0'})",
        ],
        mode="add",
        allow_new_relation=True,
    )
    result = import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        id_policy="remint",
        enable_guard=False,
    )
    assert "MOD_amp" in result.reminted
    assert "SYM_Rin" in result.reminted
    new_mod = result.reminted["MOD_amp"]
    new_rin = result.reminted["SYM_Rin"]
    assert lead.store.get(new_mod) is not None
    assert lead.store.get(new_rin) is not None
    # Original lead rows preserved.
    assert lead.store.get("MOD_amp").fields.get("path") == "old.md"
    # Reminted edge endpoints retargeted.
    edge_ids = [i for i in result.imported_ids if i.startswith("EDG") or "EDG" in i]
    assert edge_ids
    for eid in result.imported_ids:
        rec = lead.store.get(eid)
        if rec and rec.tag == "EDG":
            assert rec.fields.get("src") in {new_mod, "MOD_amp"} or rec.fields.get(
                "src"
            ) in result.reminted.values()


def test_guard_skip_when_disabled(memnet_temp, schema_file):
    member, lead = _open_pair(schema_file)

    def boom(_slice: WorkingMemorySlice) -> ImportGuardDecision:
        return ImportGuardDecision(outcome="reject", reason="should not run")

    set_import_guard(boom)
    result = import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        id_policy="keep",
        enable_guard=False,
    )
    assert result.guard_skipped is True
    assert lead.store.get("MOD_amp") is not None


def test_guard_fail_rejects_without_mutate(memnet_temp, schema_file):
    member, lead = _open_pair(schema_file)

    def deny(_slice: WorkingMemorySlice) -> ImportGuardDecision:
        return ImportGuardDecision(
            outcome="reject",
            reason="invented ids not on member pin_map",
        )

    set_import_guard(deny)
    with pytest.raises(MemNetError) as ei:
        import_slice(
            lead_session_id=lead.session_id,
            source_session_id=member.session_id,
            anchors=["MOD_amp"],
            id_policy="keep",
            enable_guard=True,
        )
    assert ei.value.code == "import_guard_reject"
    assert lead.store.get("MOD_amp") is None


def test_guard_trim_then_absorb(memnet_temp, schema_file):
    member, lead = _open_pair(schema_file)

    def trim(slice_: WorkingMemorySlice) -> ImportGuardDecision:
        keep = {
            r.id
            for r in slice_.records
            if r.id in {"MOD_amp", "SYM_Rin", "EDG_amp_rin"}
        }
        return ImportGuardDecision(
            outcome="trim",
            reason="drop off-mission SYM_scratch_* settle noise",
            keep_ids=keep,
        )

    set_import_guard(trim)
    result = import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        id_policy="keep",
        enable_guard=True,
    )
    assert result.guard_skipped is False
    assert result.decision is not None
    assert result.decision.outcome == "trim"
    assert lead.store.get("MOD_amp") is not None
    assert lead.store.get("SYM_Rin") is not None
    assert lead.store.get("SYM_scratch") is None
    assert lead.store.get("EDG_amp_scratch") is None


def test_same_session_refused(memnet_temp, schema_file):
    member, _lead = _open_pair(schema_file)
    with pytest.raises(MemNetError) as ei:
        import_slice(
            lead_session_id=member.session_id,
            source_session_id=member.session_id,
            anchors=["MOD_amp"],
            enable_guard=False,
        )
    assert ei.value.code == "same_session_import"


def test_cli_import_slice(memnet_temp, schema_file):
    member, lead = _open_pair(schema_file)
    # Ignore schema_file; sessions already open.
    del schema_file
    r = runner.invoke(
        app,
        [
            "import-slice",
            "--from-session",
            member.session_id,
            "--anchor",
            "MOD_amp",
            "--id-policy",
            "keep",
            "--no-guard",
            "--session",
            lead.session_id,
        ],
    )
    assert r.exit_code == 0, r.stderr + r.stdout
    assert "@IMPORT: ok|" in r.stdout
    assert get_session(lead.session_id).store.get("MOD_amp") is not None


def test_export_requires_anchor(memnet_temp, schema_file):
    member, _ = _open_pair(schema_file)
    with pytest.raises(MemNetError) as ei:
        export_working_memory_slice(member, anchors=[])
    assert ei.value.code == "no_anchor"


def test_absorb_unit_reject_policy(memnet_temp, schema_file):
    member, lead = _open_pair(schema_file)
    slice_ = export_working_memory_slice(member, anchors=["MOD_amp"])
    MutateGate(lead).apply(
        ["CREATE (:SYM {id: 'SYM_Rin', kind: 'x', refdes: 'R'})"],
        mode="add",
    )
    with pytest.raises(MemNetError) as ei:
        absorb_working_memory_slice(
            lead, slice_, id_policy="reject", enable_guard=False
        )
    assert ei.value.code == "id_conflict"
