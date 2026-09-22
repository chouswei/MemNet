"""Honesty-c: tip MemNet access portal invent (keyed Bearer; tip≠face)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
CONNECTIONS = MODELS / "connections.sysml"
ROOT_SYSML = MODELS / "root.sysml"
CONFIG = ROOT / "sysml-models" / "config.yaml"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
STUDY = ROOT / "sysml-models" / "outputs" / "tip-memnet-access-portal-case-study.md"
TEACH = ROOT / "docs" / "operations" / "tip-memnet-access-portal.md"

WWW = "https://memnet.139-59-255-181.nip.io/mcp"


def test_portal_parts_outside_system():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "part def TipMemNetAccessPortal" in text
    assert "part tipAccessPortal : TipMemNetAccessPortal" in text
    assert "part def PortalWeb" in text
    assert "part def GoogleIdP" in text
    assert "part def InviteStore" in text
    assert "part def KeyStore" in text
    assert "part def TipMcpGate" in text
    assert "part def PiTipMemNetMcp" in text
    assert "part def TipAccessAdmin" in text
    assert 'attribute displayName : String = "Szu-Wei"' in text
    assert "tipAccessPortalInsideSystem : Boolean = false" in text
    assert "attribute insideMemNetSystem : Boolean = false" in text
    assert "attribute tipIsFace : Boolean = false" in text
    assert "attribute isSysmlEdgeProduct : Boolean = false" in text
    assert "attribute openProjectKeyPage : Boolean = false" in text
    assert "attribute grantsOpenMemNet : Boolean = false" in text
    assert "attribute unauthenticatedWwwMcp : Boolean = false" in text
    assert "attribute keyedWwwMcp : Boolean = true" in text
    assert "attribute inventOnly : Boolean = false" in text
    assert "attribute portalWebImplemented : Boolean = true" in text
    assert "attribute sellsInvent2Green : Boolean = false" in text
    assert "attribute serviceLookImplemented : Boolean = true" in text
    assert "attribute clientLookImplemented : Boolean = true" in text
    assert "attribute statusLookOnly : Boolean = true" in text
    assert "attribute unparksUsageDashboard : Boolean = false" in text
    assert "attribute lastUsedTracked : Boolean = true" in text
    assert "attribute useCountTracked : Boolean = true" in text
    assert "attribute httpImplemented : Boolean = false" in text
    assert "attribute gatesTipMcpOnly : Boolean = true" in text
    assert "attribute gatesSysmlEdge : Boolean = false" in text
    assert "attribute unauthenticatedAllowed : Boolean = false" in text
    assert 'attribute forwardHost : String = "pi-tip"' in text
    assert f'attribute wwwUrl : String = "{WWW}"' in text
    assert "TipMemNetAccessPortal MUST NOT nest here" in text
    # Admin → Invite; User → Google → Portal → Key; Key → gate → Pi tip.
    assert "end port source ::> admin.mintOut" in text
    assert "end port sink ::> invites.mintIn" in text
    assert "end port source ::> user.loginOut" in text
    assert "end port sink ::> google.loginIn" in text
    assert "end port source ::> google.assertOut" in text
    assert "end port sink ::> portal.googleIn" in text
    assert "end port source ::> portal.keyFetchOut" in text
    assert "end port sink ::> keys.issueIn" in text
    assert "end port source ::> keys.bearerOut" in text
    assert "end port sink ::> gate.bearerIn" in text
    assert "end port source ::> gate.forwardOut" in text
    assert "end port sink ::> piTip.mcpIn" in text


def test_requirement_verify_and_load():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "MN-REQ-06.8" in req
    assert "requirement def MN_REQ_06_8_TipMemNetAccessPortal" in req
    assert "tipMemNetAccessPortalReq" in req
    assert "Szu-Wei" in req
    assert "tip≠face" in req
    assert "invent_2_green" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S05_TipMemNetAccessPortal" in ver
    assert "verify tipMemNetAccessPortalReq" in ver
    assert 'portal.admin.displayName == "Szu-Wei"' in ver
    assert "portal.isSysmlEdgeProduct == false" in ver
    assert "portal.unauthenticatedWwwMcp == false" in ver
    assert "portal.gate.gatesSysmlEdge == false" in ver
    assert f'portal.gate.wwwUrl == "{WWW}"' in ver
    assert "portal.sellsInvent2Green == false" in ver
    assert "portal.statusLookOnly == true" in ver
    assert "portal.unparksUsageDashboard == false" in ver
    assert "portal.keys.lastUsedTracked == true" in ver
    assert "dashboard.httpImplemented == false" in ver
    conn = CONNECTIONS.read_text(encoding="utf-8")
    assert "item def TipMemNetAccess" in conn
    assert "connection def TipBearerFlow" in conn
    assert "connection def TipForwardFlow" in conn
    assert "Authorization: Bearer" in conn
    root = ROOT_SYSML.read_text(encoding="utf-8")
    assert "TipMemNetAccessPortal" in root
    assert "private import MemNet::" in root
    cfg = CONFIG.read_text(encoding="utf-8")
    assert "deploy.sysml" in cfg
    assert "TipMemNetAccessPortal nests in deploy.sysml" in cfg


def test_teach_and_soft_pass_kills():
    study = STUDY.read_text(encoding="utf-8")
    teach = TEACH.read_text(encoding="utf-8")
    nest = NEST.read_text(encoding="utf-8")
    for blob in (study, teach, nest):
        assert "tip≠face" in blob
        assert "Szu-Wei" in blob or blob is nest
        assert WWW in blob or blob is nest
        assert "invent_2_green" in blob
        assert "sysmledge" in blob
    assert "Authorization: Bearer" in study
    assert "Authorization: Bearer" in teach
    assert "openProject" in study
    assert "Unauthenticated MemNet MCP on droplet WWW" in nest
    assert "portalWebImplemented=true" in nest
    assert "inventOnly=false" in nest
    assert "isSysmlEdgeProduct=false" in nest
    assert "statusLookOnly=true" in nest
    assert "unparksUsageDashboard=false" in nest
    assert "httpImplemented=false" in nest
    assert "last-used" in teach
    assert "MEMNET_STATUS_PROBES" in teach
    assert "MEMNET_TIP_MCP_PROBE" in teach
    assert "statusLookOnly" in study
