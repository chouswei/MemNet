"""Honesty-c: ops fleet — one MemNet MCP at droplet (tip≠face); sysmledge is product."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
CONNECTIONS = MODELS / "connections.sysml"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
STUDY = ROOT / "sysml-models" / "outputs" / "device-fleet-one-mcp-case-study.md"

# Prescriptions that sold MemNet MCP as the product LLM face.
# Kill rows may quote the bad teach; those quotes keep "MemNet" in the
# droplet-bind phrase and wrap the device-MCP ban as a named kill.
_TIP_AS_FACE_TEACH = (
    "LLM tool face",
    "bind the droplet MCP only",
    "Cursor/cloud agents bind the droplet MCP only",
)


def test_ops_fleet_parts_and_flags():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "part def DropletHost" in text
    assert "part def MemNetDeviceHost" in text
    assert "part def MemNetOpsFleet" in text
    assert "part opsFleet : MemNetOpsFleet" in text
    assert "opsFleetInsideSystem : Boolean = false" in text
    assert "mcpCount : Integer = 1" in text
    assert 'fleetMcpHost : String = "droplet"' in text
    assert "nServerFederation : Boolean = false" in text
    assert "mcpNested : Boolean = false" in text
    assert "productMcpNested : Boolean = false" in text
    assert "tipMcpLegal : Boolean = true" in text
    assert "fleetSingleton : Boolean = true" in text
    assert 'defaultHostKind : String = "droplet"' in text
    assert "deviceHostLegal : Boolean = true" in text
    assert 'productInventFace : String = "sysmledge"' in text
    assert "mustNotInventUploadBind : Boolean = true" in text
    assert "part memnet : MemNetSystem" in text
    assert "part service : MemNetCoreLibrary" in text
    assert "part devices : MemNetDeviceHost[1..*]" in text
    assert "MemNetOpsFleet MUST NOT nest here" in text
    assert "MemNet tip/ops" in text
    assert "tip≠face" in text
    assert "sysmledge" in text
    # MemNetMcpServer (not the dashboard) records tip≠face.
    assert "attribute tipIsFace : Boolean = false;" in text
    mcp_block = text.split("part def MemNetMcpServer", 1)[1].split("part def ", 1)[0]
    assert "attribute tipIsFace : Boolean = false;" in mcp_block
    assert "NOT the product invent face" in mcp_block


def test_ops_fleet_requirement_and_verify():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "MN-REQ-06.6" in req
    assert "requirement def MN_REQ_06_6_DeviceServicesOneDropletMcp" in req
    assert "deviceServicesOneDropletMcpReq" in req
    assert "sysmledge" in req
    assert "tip≠face" in req
    assert "mustNotInventUploadBind" in req
    assert "tip MemNet MCP on a" in req
    assert "MUST NOT answer" in req and "product questions" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S03_DeviceFleetOneDropletMcp" in ver
    assert "verify deviceServicesOneDropletMcpReq" in ver
    assert 'fleet.productInventFace == "sysmledge"' in ver
    assert "fleet.mustNotInventUploadBind == true" in ver
    assert "fleet.devices.productMcpNested == false" in ver
    assert "fleet.devices.tipMcpLegal == true" in ver
    assert "mcp.tipIsFace == false" in ver
    conn = CONNECTIONS.read_text(encoding="utf-8")
    assert "item def DeviceMemNetFleet" in conn
    assert "sysmledge" in conn
    assert "tip≠face" in conn


def test_ops_fleet_outputs_and_not_nserver():
    nest = NEST.read_text(encoding="utf-8")
    assert "MemNetOpsFleet" in nest
    assert "one MemNet MCP at droplet" in nest
    assert "nServerFederation=false" in nest
    assert "sysmledge" in nest
    assert "tip≠face" in nest
    assert "mustNotInventUploadBind" in nest
    assert "tipMcpLegal=true" in nest
    study = STUDY.read_text(encoding="utf-8")
    assert "MN-REQ-06.6" in study
    assert "MN-VER-06-S03" in study
    assert "nServerFederation=false" in study
    assert "mcpNested=false" in study
    assert "sysmledge" in study
    assert "tip≠face" in study
    assert "mustNotInventUploadBind" in study
    assert "productInventFace" in study
    assert "tipMcpLegal=true" in study
    assert "Product agents bind **sysmledge**" in study
    assert "MUST NOT answer product questions on the MemNet tip path" in study


def test_ops_fleet_no_tip_as_face_teach():
    blobs = [
        DEPLOY.read_text(encoding="utf-8"),
        REQUIREMENTS.read_text(encoding="utf-8"),
        VERIFY.read_text(encoding="utf-8"),
        CONNECTIONS.read_text(encoding="utf-8"),
        NEST.read_text(encoding="utf-8"),
        STUDY.read_text(encoding="utf-8"),
    ]
    joined = "\n".join(blobs)
    for needle in _TIP_AS_FACE_TEACH:
        assert needle not in joined, f"tip-as-face teach string still present: {needle!r}"
    # Soft-pass kill rows must name the forbidden teach, not prescribe it.
    assert "Tip path answering a product question" in STUDY.read_text(encoding="utf-8")
    assert "device must never run any MCP" in NEST.read_text(encoding="utf-8")
    assert "as a ban on ops tip" in NEST.read_text(encoding="utf-8")
