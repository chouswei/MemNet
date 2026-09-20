"""Honesty-c: ops fleet — device MemNet services, one MCP at the droplet."""

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
    assert "fleetSingleton : Boolean = true" in text
    assert 'defaultHostKind : String = "droplet"' in text
    assert "deviceHostLegal : Boolean = true" in text
    assert "part memnet : MemNetSystem" in text
    assert "part service : MemNetCoreLibrary" in text
    assert "part devices : MemNetDeviceHost[1..*]" in text
    assert "MemNetOpsFleet MUST NOT nest here" in text


def test_ops_fleet_requirement_and_verify():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "MN-REQ-06.6" in req
    assert "requirement def MN_REQ_06_6_DeviceServicesOneDropletMcp" in req
    assert "deviceServicesOneDropletMcpReq" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S03_DeviceFleetOneDropletMcp" in ver
    assert "verify deviceServicesOneDropletMcpReq" in ver
    conn = CONNECTIONS.read_text(encoding="utf-8")
    assert "item def DeviceMemNetFleet" in conn


def test_ops_fleet_outputs_and_not_nserver():
    nest = NEST.read_text(encoding="utf-8")
    assert "MemNetOpsFleet" in nest
    assert "one MCP at droplet" in nest
    assert "nServerFederation=false" in nest
    study = STUDY.read_text(encoding="utf-8")
    assert "MN-REQ-06.6" in study
    assert "MN-VER-06-S03" in study
    assert "nServerFederation=false" in study
    assert "mcpNested=false" in study
