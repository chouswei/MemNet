"""Honesty: MN-REQ-01.9 / 01.10 / 03.4 / 05.3 live in the SysML SSOT."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
REQ = MODELS / "requirements.sysml"
DEPLOY = MODELS / "deploy.sysml"
VERIFY = MODELS / "verify.sysml"


def test_requirements_ids_present():
    text = REQ.read_text(encoding="utf-8")
    for nid in ("MN-REQ-01.9", "MN-REQ-01.10", "MN-REQ-03.4", "MN-REQ-05.3"):
        assert nid in text
    assert "snapshot_unsaveable" in text
    assert "expire_snapshot_failed" in text
    assert "SHALL NOT drop RAM" in text
    assert "unsupported_predicate" in text
    assert "MEMNET_MAX_VALUE_BYTES" in text
    assert "str.splitlines()" in text
    assert "widening the" in text
    assert "escaped/raw leftover-pipe" in text
    assert "snapshotLosslessRoundTripReq" in text
    assert "sessionLifecycleAclWhoReq" in text
    assert "honourWherePredicateReq" in text
    assert "consistentValueByteCapReq" in text


def test_deploy_and_verify_trail_model():
    deploy = DEPLOY.read_text(encoding="utf-8")
    assert "losslessPropertyRoundTrip" in deploy
    assert "failClosedUnsaveable" in deploy
    assert "honourWhereOrRefuse" in deploy
    assert 'envMaxValueBytes : String = "MEMNET_MAX_VALUE_BYTES"' in deploy
    assert "sessionSaveLoadCloseAclWho" in deploy
    assert "acceptsCaller" in deploy
    assert "persistUndeclaredProperties" in deploy
    assert "splitlinesSeparatorsEscaped" in deploy
    assert "recordSplitLfOnly" in deploy
    assert "lineBytesOnEmittedLine" in deploy
    assert "expireSaveFailureKeepsRam" in deploy
    ver = VERIFY.read_text(encoding="utf-8")
    assert "MN-VER-01-S04" in ver
    assert "MN-VER-01-S05" in ver
    assert "MN-VER-03-S01" in ver
    assert "MN-VER-05-S01" in ver
    assert "persistUndeclaredProperties" in ver
    assert "splitlinesSeparatorsEscaped" in ver
    assert "lineBytesOnEmittedLine" in ver
