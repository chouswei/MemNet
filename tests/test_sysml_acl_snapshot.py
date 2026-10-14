"""MN-REQ-06.16 session ACL in snapshots is modelled in SysML before and beside the code."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
IMPLEMENTATION = MODELS / "implementation.sysml"
MAP = ROOT / "sysml-models" / "outputs" / "ssot-to-code-allocate-map.md"


def test_requirement_and_index():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "requirement def MN_REQ_06_16_SnapshotAcl" in req
    assert 'attribute requirementId : String = "MN-REQ-06.16"' in req
    assert "MN-REQ-06.16       Session snapshot carries the ACL" in req
    assert "requirement snapshotAclReq" in req
    assert "MN_REQ_06_16_SnapshotAcl;" in req


def test_deploy_attributes():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "part def SnapshotAcl" in text
    assert "part snapshotAcl : SnapshotAcl" in text
    assert 'attribute aclLineCommentPrefix : String = "#@ACL:"' in text
    assert "attribute snapshotFormatVersion : Integer = 2" in text
    assert "attribute v2MissingAclFailsBadSnapshot : Boolean = true" in text
    assert "attribute bindStoresLeaseDigestOnly : Boolean = true" in text
    assert 'attribute snapshotFileMode : String = "0600"' in text
    assert "oldReaderSkipsAclLine" not in text
    assert 'attribute aclAbsentStat : String = "@ACL: absent|off"' in text


def test_verify_case_names_real_tests():
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S14_SnapshotAcl" in ver
    assert 'attribute verificationId : String = "MN-VER-06-S14"' in ver
    assert "verify snapshotAclReq" in ver
    assert "snap.snapshotAcl.aclMalformedFailsClosed == true" in ver
    assert "snap.snapshotAcl.v2MissingAclFailsBadSnapshot == true" in ver
    assert 'snap.snapshotAcl.snapshotFileMode == "0600"' in ver
    assert "verification snapshotAclVerify" in ver
    assert "tests/test_acl_snapshot.py" in ver
    assert "::test_format_2_missing_acl_line_fails_bad_snapshot" in ver
    assert "::test_snapshot_files_are_mode_0600_and_replace_loose_modes" in ver


def test_implementation_satisfy_and_allocation():
    impl = IMPLEMENTATION.read_text(encoding="utf-8")
    assert "part def SnapshotAclMod" in impl
    assert (
        "satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_16_SnapshotAcl;"
        in impl
    )
    assert "allocation snapshotAclToMod" in impl
    assert "memnet.snapshot" in impl
    ledger = MAP.read_text(encoding="utf-8")
    assert "| snapshotAclToMod |" in ledger
