"""Honesty-c: product gateway on memnet-mcp (MN-REQ-06.12; parent stays inventOnly)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
IMPL = MODELS / "implementation.sysml"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
CONTRACT = ROOT / "docs" / "operations" / "product-gateway-contract.md"
CODE = ROOT / "parts" / "memnet-mcp" / "software" / "memnet_mcp" / "product_gateway.py"
PROJECT = ROOT / "project.toml"


def test_gateway_part_and_parent_still_invent():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "part def MemNetProductGateway" in text
    assert "part productGateway : MemNetProductGateway" in text
    assert "attribute implemented : Boolean = true" in text
    assert "attribute reusesTipBearer : Boolean = false" in text
    assert "attribute inventOnly : Boolean = true" in text
    assert "attribute implemented : Boolean = false" in text
    assert "attribute codeApproved : Boolean = false" in text
    assert "attribute singleBackendUnchanged : Boolean = true" in text
    assert "attribute publicBindDefault : Boolean = false" in text
    assert "MN_REQ_06_12_ProductGateway" in text


def test_requirement_verify_and_allocate():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "MN-REQ-06.12" in req
    assert "requirement def MN_REQ_06_12_ProductGateway" in req
    assert "productGatewayReq" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S10_ProductGateway" in ver
    assert 'attribute verificationId : String = "MN-VER-06-S10"' in ver
    assert "verify productGatewayReq" in ver
    assert "gateway.implemented == true" in ver
    assert "gateway.reusesTipBearer == false" in ver
    assert "gateway.singleBackendUnchanged == true" in ver
    impl = IMPL.read_text(encoding="utf-8")
    assert "part def ProductGatewayMod" in impl
    assert "product_gateway.py" in impl
    assert "memnet_mcp.product_gateway" in impl
    assert "allocation productGatewayToMod" in impl
    assert CODE.is_file()


def test_contract_is_not_draft_and_no_semver_bump():
    contract = CONTRACT.read_text(encoding="utf-8")
    assert "MN-REQ-06.12" in contract
    assert "implemented for the behaviours" in contract
    lowered = contract.lower()
    assert "draft" not in lowered
    assert "100.118.79.40" in contract
    assert "18795" in contract
    nest = NEST.read_text(encoding="utf-8")
    assert "inventOnly" in nest
    assert "MemNetLanMcpFront" in nest
    assert "worthBuildingVisible=true" in nest
    assert "MemNetProductGateway" in nest
    project = PROJECT.read_text(encoding="utf-8")
    assert 'version = "0.19.20"' in project
    assert "0.19.21" not in project
