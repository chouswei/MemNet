"""Honesty-c: storageRole strings, cabinet wiring, cousin fence rename."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
VERIFY = MODELS / "verify.sysml"
COUSINS = MODELS / "cousins.sysml"
ARCHIVE = MODELS / "archive.sysml"
CONNECTIONS = MODELS / "connections.sysml"
BEHAVIOUR = MODELS / "behaviour.sysml"
REQ = MODELS / "requirements.sysml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_storage_role_strings_on_parts():
    text = _read(DEPLOY)
    for role in (
        '"working_memory"',
        '"mission_handle"',
        '"file_snapshot"',
        '"cabinet_ego"',
        '"ci_seam"',
        '"library_locators"',
        '"row_hide_mark"',
        '"row_prune"',
        '"retired_shelf"',
        '"process_host"',
        '"recall_window"',
    ):
        assert role in text
    assert "attribute unconfiguredIsFakeSeam : Boolean = true;" in text
    assert "attribute bindsExactlyOneAdapter : Boolean = true;" in text
    assert 'attribute bindsExactlyOneOf : String = "agensgraph|neo4j";' in text
    assert "attribute explicitSaveAndExpireSaveOneBlob : Boolean = true;" in text
    assert "attribute hydrateByHidLiveProven : Boolean = false;" in text
    assert "attribute serverVendored : Boolean = false;" in text
    assert "attribute runsOnCommit : Boolean = false;" in text
    assert "attribute runsOnTtl : Boolean = false;" in text
    assert "attribute mcpCliCaller : Boolean = false;" in text


def test_durable_flow_uses_buffer_ports():
    text = _read(DEPLOY)
    assert "end port source ::> durable.hydrateOut;" in text
    assert "end port sink ::> durable.flushIn;" in text
    assert "durable.agens.hydrateOut" not in text
    assert "durable.agens.flushIn" not in text


def test_verify_pins_roles_and_known_sid():
    text = _read(VERIFY)
    assert "verification def MN_VER_06_S06_StorageRoles" in text
    assert 'attribute verificationId : String = "MN-VER-06-S06";' in text
    assert "storageRolesVerify : MN_VER_06_S06_StorageRoles" in text
    assert '.storageRole == "working_memory"' in text
    assert '.storageRole == "cabinet_ego"' in text
    assert '.fakeSeamStorageRole == "ci_seam"' in text
    assert ".loadByKnownSid == true" in text
    assert "contrast.cousinNestOwnsLiveNeo4jClaim == false" in text
    assert "contrast.liveNeo4jClaimed" not in text


def test_cousin_fence_renamed():
    text = _read(COUSINS)
    assert "attribute cousinNestOwnsLiveNeo4jClaim : Boolean = false;" in text
    assert "attribute liveNeo4jClaimed : Boolean = false;" not in text


def test_archive_shelf_role_off_load_wording():
    text = _read(ARCHIVE)
    assert 'attribute storageRole : String = "retired_shelf";' in text


def test_landed_client_ports_and_one_blob():
    connections = _read(CONNECTIONS)
    assert "ROADMAP M2.5" not in connections
    assert "Landed client:" in connections
    behaviour = _read(BEHAVIOUR)
    assert "ROADMAP M2.5" not in behaviour
    assert "Landed client:" in behaviour
    req = _read(REQ)
    assert "working-memory" in req
    assert "Explicit session_save and expire-save write that" in req
    assert "one\n          SessionSnapshotBlob" in req
