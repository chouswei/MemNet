"""Honesty-c: MN-REQ-06.15 serve checkpoint is modelled before the code."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
IMPLEMENTATION = MODELS / "implementation.sysml"
STUDY = ROOT / "sysml-models" / "outputs" / "checkpoint-case-study.md"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
TEACH = ROOT / "docs" / "operations" / "backup.md"
MAP = ROOT / "sysml-models" / "outputs" / "ssot-to-code-allocate-map.md"


def test_checkpoint_parts():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "part def ServeCheckpoint" in text
    assert "part def CmdAdminCheckpoint" in text
    assert "part def CmdAdminCheckpointVerify" in text
    assert "part serveCheckpoint : ServeCheckpoint" in text
    assert "attribute drainsServe : Boolean = false" in text
    assert "attribute retiresOrLoads : Boolean = false" in text
    assert "attribute refusesNewSessionOpen : Boolean = false" in text
    mcp = text.split("part def McpFacade", 1)[1].split("part def ", 1)[0]
    assert "part checkpoint" not in mcp
    gateway = text.split("part def MemNetProductGateway", 1)[1].split("part def ", 1)[0]
    assert "MN_REQ_06_15_ServeCheckpoint" not in gateway


def test_requirement_verify_allocate():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "requirement def MN_REQ_06_15_ServeCheckpoint" in req
    assert 'attribute requirementId : String = "MN-REQ-06.15"' in req
    assert "serveCheckpointReq" in req
    assert "checkpoint|ok|n|skipped|m|bytes|b" in req
    assert "snapshot_unsaveable" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S13_ServeCheckpoint" in ver
    assert "verify serveCheckpointReq" in ver
    assert "tcp.serveCheckpoint.drainsServe == false" in ver
    assert "tcp.serveCheckpoint.retiresOrLoads == false" in ver
    impl = IMPLEMENTATION.read_text(encoding="utf-8")
    assert "part def ServeCheckpointMod" in impl
    assert "allocation serveCheckpointToMod" in impl
    assert "memnet.checkpoint" in impl
    ledger = MAP.read_text(encoding="utf-8")
    assert "| serveCheckpointToMod |" in ledger


def test_outputs_and_docs():
    study = STUDY.read_text(encoding="utf-8")
    assert "MN-REQ-06.15" in study
    assert "MN-VER-06-S13" in study
    nest = NEST.read_text(encoding="utf-8")
    assert "ServeCheckpoint" in nest
    teach = TEACH.read_text(encoding="utf-8")
    assert "memnet admin checkpoint" in teach
    assert "checkpoint-verify" in teach
    assert "MEMNET_ADMIN_TOKEN" in teach
    assert "restic" in teach
    assert "mn_" not in teach
    assert "mn_" not in study
