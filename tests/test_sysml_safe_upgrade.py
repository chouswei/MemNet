"""Honesty-c: MN-REQ-06.14 safe serve upgrade is modelled before the code."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
IMPLEMENTATION = MODELS / "implementation.sysml"
STUDY = ROOT / "sysml-models" / "outputs" / "safe-upgrade-case-study.md"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
TEACH = ROOT / "docs" / "operations" / "safe-upgrade.md"
MAP = ROOT / "sysml-models" / "outputs" / "ssot-to-code-allocate-map.md"


def test_safe_upgrade_parts():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "part def SafeServeUpgrade" in text
    assert "part def CmdAdminUpgradePrepare" in text
    assert "part safeUpgrade : SafeServeUpgrade" in text
    assert "attribute silentSessionLoss : Boolean = false" in text
    assert 'attribute errDraining : String = "serve_draining"' in text
    assert "attribute retryDefaultS : Integer = 30" in text
    assert "attribute clientsBeforeServe : Boolean = true" in text
    mcp = text.split("part def McpFacade", 1)[1].split("part def ", 1)[0]
    assert "part upgradePrepare" not in mcp
    assert "attribute upgradeRetry : Boolean = true" in mcp
    gateway = text.split("part def MemNetProductGateway", 1)[1].split("part def ", 1)[0]
    assert "attribute retryConnectionRefusal : Boolean = true" in gateway


def test_requirement_verify_allocate():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "requirement def MN_REQ_06_14_SafeServeUpgrade" in req
    assert 'attribute requirementId : String = "MN-REQ-06.14"' in req
    assert "safeServeUpgradeReq" in req
    assert "serve_draining" in req
    assert "allow-unsaved" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S12_SafeServeUpgrade" in ver
    assert "verify safeServeUpgradeReq" in ver
    assert "tcp.safeUpgrade.corruptDeletesSnapshots == false" in ver
    impl = IMPLEMENTATION.read_text(encoding="utf-8")
    assert "part def SafeUpgradeMod" in impl
    assert "allocation safeUpgradeToMod" in impl
    assert "memnet.upgrade" in impl
    assert "memnet.upgrade_retry" in impl
    assert "memnet.upgrade_run" in impl
    ledger = MAP.read_text(encoding="utf-8")
    assert "| safeUpgradeToMod |" in ledger
    assert "| upgradeHelperToMod |" in ledger


def test_outputs_and_docs():
    study = STUDY.read_text(encoding="utf-8")
    assert "MN-REQ-06.14" in study
    assert "MN-VER-06-S12" in study
    nest = NEST.read_text(encoding="utf-8")
    assert "SafeServeUpgrade" in nest
    teach = TEACH.read_text(encoding="utf-8")
    assert "memnet-upgrade" in teach
    assert "MEMNET_ADMIN_TOKEN" in teach
    assert "18765" in teach
    assert "18766" in teach
    assert "mn_" not in teach
    assert "mn_" not in study
