"""Honesty-c: MN-REQ-06.11 admin serve usage report on memnet-serve."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
CONNECTIONS = MODELS / "connections.sysml"
IMPLEMENTATION = MODELS / "implementation.sysml"
STUDY = ROOT / "sysml-models" / "outputs" / "admin-usage-report-case-study.md"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
TEACH = ROOT / "docs" / "operations" / "admin-usage-report.md"


def test_admin_usage_parts_on_serve():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "part def AdminUsageReport" in text
    assert "part def AdminCredentialGate" in text
    assert "part def CapPressureTally" in text
    assert "part def CmdAdminUsageReport" in text
    assert "part adminUsage : AdminUsageReport" in text
    assert "port adminReportOut : AdminUsageReportOutPort" in text
    assert "port adminCmdIn : AdminUsageCommandInPort" in text
    assert "attribute onAgentMcp : Boolean = false" in text
    assert "attribute emitsRealSessionId : Boolean = false" in text
    assert "attribute peekOnly : Boolean = true" in text
    assert "attribute mcpProductLabelOpen : Boolean = true" in text
    assert "attribute productLabelOnMcpSessionOpen : Boolean = false" in text
    assert "attribute adminUsageToolNested : Boolean = false" in text
    assert 'attribute envName : String = "MEMNET_ADMIN_TOKEN"' in text
    assert 'attribute errUnconfigured : String = "admin_unconfigured"' in text
    assert "part adminUsageReport : CmdAdminUsageReport" in text
    mcp_block = text.split("part def McpFacade", 1)[1].split("part def ", 1)[0]
    assert "part adminUsageReport" not in mcp_block


def test_requirement_verify_and_load():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "MN-REQ-06.11" in req
    assert "requirement def MN_REQ_06_11_AdminServeUsageReport" in req
    assert "adminServeUsageReportReq" in req
    assert "admin_unconfigured" in req
    assert "mcpProductLabelOpen" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S09_AdminServeUsageReport" in ver
    assert "verify adminServeUsageReportReq" in ver
    assert "tcp.adminUsage.emitsRealSessionId == false" in ver
    assert "mcp.adminUsageToolNested == false" in ver
    conn = CONNECTIONS.read_text(encoding="utf-8")
    assert "item def AdminUsageReportSnapshot" in conn
    assert "port def AdminUsageReportOutPort" in conn
    impl = IMPLEMENTATION.read_text(encoding="utf-8")
    assert "part def AdminUsageReportMod" in impl
    assert "allocation adminUsageToMod" in impl
    assert "memnet.admin_usage" in impl


def test_outputs_and_docs():
    study = STUDY.read_text(encoding="utf-8")
    assert "MN-REQ-06.11" in study
    assert "MN-VER-06-S09" in study
    assert "emitsRealSessionId=false" in study
    nest = NEST.read_text(encoding="utf-8")
    assert "AdminUsageReport" in nest
    teach = TEACH.read_text(encoding="utf-8")
    assert "memnet admin usage-report" in teach
    assert "MEMNET_ADMIN_TOKEN" in teach
    assert "admin_unconfigured" in teach
    assert "mn_" in teach
