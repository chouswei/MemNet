"""Honesty-c: LAN MCP front invent (#191; tip≠face; not #47 peer pipe)."""

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
STUDY = ROOT / "sysml-models" / "outputs" / "lan-mcp-front-case-study.md"
TEACH = ROOT / "docs" / "operations" / "memnet-lan-mcp-front.md"

_PROJECT = ROOT / "project.toml"


def test_lan_front_parts_outside_system():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "part def MemNetLanMcpFront" in text
    assert "part lanMcpFront : MemNetLanMcpFront" in text
    assert "part def ServeBackend" in text
    assert "part def SessionOwnerRegistry" in text
    assert "part def FrontBackendAuth" in text
    assert "part def ClusterRoute" in text
    assert "part clusterRoute : ClusterRoute" in text
    assert "part def SessionOpenRoute" in text
    assert "part def SessionListUnion" in text
    assert "part def SessionCurrentBind" in text
    assert "part def SnapshotHandCarry" in text
    assert "lanMcpFrontInsideSystem : Boolean = false" in text
    assert "MemNetLanMcpFront MUST NOT nest here" in text
    assert "attribute inventOnly : Boolean = true" in text
    assert "attribute implemented : Boolean = false" in text
    assert "attribute codeApproved : Boolean = false" in text
    assert "attribute noSemVerBump : Boolean = true" in text
    assert "attribute nServerPeerHandoff : Boolean = false" in text
    assert "attribute pinMapSpansBackends : Boolean = false" in text
    assert "attribute findSpansBackends : Boolean = false" in text
    assert "attribute silentHashRouting : Boolean = false" in text
    assert "attribute registryPreferred : Boolean = true" in text
    assert "attribute explicitPinAllowed : Boolean = true" in text
    assert "attribute oneOwnerPerSession : Boolean = true" in text
    assert "attribute importSliceFromUrl : Boolean = false" in text
    assert "attribute cousinIssue47 : Boolean = true" in text
    assert "attribute unauthenticatedPublicMcp : Boolean = false" in text
    assert "attribute snapshotDirPerBackend : Boolean = true" in text
    assert "attribute silentMigrate : Boolean = false" in text
    assert "end port source ::> pinOut" in text
    assert "end port sink ::> registry.pinIn" in text
    assert "end port source ::> backends.statusOut" in text
    assert "end port sink ::> backends.mcpIn" in text


def test_requirement_verify_and_load():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "MN-REQ-06.9" in req
    assert "requirement def MN_REQ_06_9_LanMcpFrontSeveralServes" in req
    assert "lanMcpFrontSeveralServesReq" in req
    assert "tip≠face" in req
    assert "SessionOwnerRegistry" in req
    assert "import_slice(from_url)" in req
    assert "#47" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S07_LanMcpFrontSeveralServes" in ver
    assert "verify lanMcpFrontSeveralServesReq" in ver
    assert "front.inventOnly == true" in ver
    assert "front.nServerPeerHandoff == false" in ver
    assert "front.pinMapSpansBackends == false" in ver
    assert "front.registry.silentHashRouting == false" in ver
    assert "front.importSliceFromUrl == false" in ver
    assert "front.clusterRoute.openRoute.writesRegistry == true" in ver
    conn = CONNECTIONS.read_text(encoding="utf-8")
    assert "item def MemNetLanMcpCluster" in conn
    assert "item def SessionOwnerRecord" in conn
    assert "connection def RoutedMcpCallFlow" in conn
    assert "import_slice(from_url)" in conn
    root = ROOT_SYSML.read_text(encoding="utf-8")
    assert "MemNetLanMcpFront" in root
    assert "private import MemNet::" in root
    cfg = CONFIG.read_text(encoding="utf-8")
    assert "deploy.sysml" in cfg
    assert "MemNetLanMcpFront nests in deploy.sysml" in cfg


def test_teach_contrasts_47_and_worth_building():
    study = STUDY.read_text(encoding="utf-8")
    teach = TEACH.read_text(encoding="utf-8")
    nest = NEST.read_text(encoding="utf-8")
    for blob in (study, teach, nest):
        assert "tip≠face" in blob
        assert "#191" in blob or blob is nest
        assert "inventOnly" in blob
    assert "session_open" in teach
    assert "session_list" in teach
    assert "session_current" in teach
    assert "pin_map" in teach
    assert "SessionOwnerRegistry" in teach
    assert "silent hash" in teach.lower() or "Silent hash" in teach
    assert "per-backend" in teach
    assert "CEO lock" in teach
    assert "single serve already hosts many sessions" in teach.lower()
    assert "no SemVer" in teach or "no SemVer" in study
    assert "cousin" in teach.lower()
    assert "#47" in teach
    assert "import_slice(from_url" in teach
    assert "nServerPeerHandoff=false" in study
    assert "MN-REQ-06.9" in study
    assert "MN-VER-06-S07" in study
    assert "worthBuildingVisible=true" in nest
    assert "MemNetLanMcpFront" in nest
    assert "InkMirage" in teach
    assert "Szu-Wei" not in teach
    assert "Szu-Wei" not in study


def test_no_semver_bump_in_this_invent():
    text = _PROJECT.read_text(encoding="utf-8")
    assert 'version = "0.19.16"' in text
    assert "0.19.17" not in text
