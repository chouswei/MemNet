"""Honesty-c: SSOT parts allocate to live code; one Hatch wheel; sysmledge not in wheel."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
IMPLEMENTATION = MODELS / "implementation.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
CONFIG = ROOT / "sysml-models" / "config.yaml"
ROOT_SYSML = MODELS / "root.sysml"
PYPROJECT = ROOT / "pyproject.toml"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
STUDY = ROOT / "sysml-models" / "outputs" / "ssot-to-code-allocate-case-study.md"

_PATH_RE = re.compile(r'attribute path : String = "([^"]+)"')
_CODE_END_RE = re.compile(r"end code ::> ([A-Za-z0-9_.]+);")
_TIP_AS_FACE_TEACH = (
    "LLM tool face",
    "bind the droplet MCP only",
    "Cursor/cloud agents bind the droplet MCP only",
)


def _impl_text() -> str:
    return IMPLEMENTATION.read_text(encoding="utf-8")


def test_ssot_to_code_paths_exist():
    text = _impl_text()
    paths = _PATH_RE.findall(text)
    assert paths, "implementation.sysml must declare module paths"
    missing = []
    for rel in paths:
        target = ROOT / rel
        if not target.exists():
            missing.append(rel)
        assert "sysmledge" not in rel
        assert "sysml-edge" not in rel.lower()
    assert missing == [], f"allocated paths missing on disk: {missing}"


def test_ssot_to_code_wheel_and_absence():
    text = _impl_text()
    assert "package MemNetImplementation" in text
    assert "allocation def SoftwareAllocate" in text
    assert "part def MemNetLlmWheel" in text
    assert "oneWheelManyHosts : Boolean = true" in text
    assert "sysmlEdgeInWheel : Boolean = false" in text
    assert 'hatchPackage : String = "memnet-llm"' in text
    assert 'consoleMemnet : String = "memnet.cli:main"' in text
    assert 'consoleMemnetMcp : String = "memnet_mcp.server:main"' in text
    assert "part def CousinSysMLEdgeNotInRepo" in text
    assert "inThisRepo : Boolean = false" in text
    assert "mustNotInventUploadBind : Boolean = true" in text
    assert "attribute tipIsFace : Boolean = false;" in text
    mcp_block = text.split("part def McpServerMod", 1)[1].split("part def ", 1)[0]
    assert "attribute tipIsFace : Boolean = false;" in mcp_block
    assert "end code ::> sysmlEdgeAbsent" not in text
    assert "end logical ::> sysmlEdgeAbsent" not in text
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    assert 'name = "memnet-llm"' in pyproject
    assert 'memnet = "memnet.cli:main"' in pyproject
    assert 'memnet-mcp = "memnet_mcp.server:main"' in pyproject
    assert '"parts/common/memnet/memnet"' in pyproject
    assert '"parts/memnet-mcp/software/memnet_mcp"' in pyproject
    assert 'hatchCorePackage : String = "parts/common/memnet/memnet"' in text
    assert 'hatchMcpPackage : String = "parts/memnet-mcp/software/memnet_mcp"' in text


def test_ssot_to_code_requirement_verify_load():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "MN-REQ-06.7" in req
    assert "requirement def MN_REQ_06_7_SsotToCodeAllocate" in req
    assert "ssotToCodeAllocateReq" in req
    assert "oneWheelManyHosts" in req
    assert "sysmlEdgeInWheel" in req
    assert "mustNotInventUploadBind" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S04_SsotToCodeAllocate" in ver
    assert "verify ssotToCodeAllocateReq" in ver
    assert "wheel.oneWheelManyHosts == true" in ver
    assert "wheel.sysmlEdgeInWheel == false" in ver
    assert "mcpMod.tipIsFace == false" in ver
    assert "absent.inThisRepo == false" in ver
    assert "private import MemNetImplementation::*;" in ver
    cfg = CONFIG.read_text(encoding="utf-8")
    files = [
        line.split("#", 1)[0].strip().lstrip("- ").strip()
        for line in cfg.splitlines()
        if line.strip().startswith("- ") and line.strip().endswith(".sysml")
    ]
    assert "implementation.sysml" in files
    assert files.index("deploy.sysml") < files.index("implementation.sysml")
    assert files.index("implementation.sysml") < files.index("verify.sysml")
    root = ROOT_SYSML.read_text(encoding="utf-8")
    assert "private import MemNetImplementation::*;" in root
    assert "private import MemNetArchive" not in root


def test_ssot_to_code_allocate_targets_exist():
    text = _impl_text()
    code_ends = _CODE_END_RE.findall(text)
    assert code_ends, "SoftwareAllocate must name code ends"
    usages = set(re.findall(r"^  part ([A-Za-z0-9_]+) :", text, re.M))
    usages.add("wheel.core")
    usages.add("wheel.mcp")
    usages.add("wheel")
    missing = [end for end in code_ends if end not in usages]
    assert missing == [], f"code ends without usages: {missing}"


def test_ssot_to_code_outputs_and_not_nserver():
    nest = NEST.read_text(encoding="utf-8")
    assert "IMPLEMENTATION" in nest
    assert "MemNetImplementation" in nest
    assert "oneWheelManyHosts=true" in nest
    assert "sysmlEdgeInWheel=false" in nest
    study = STUDY.read_text(encoding="utf-8")
    assert "MN-REQ-06.7" in study
    assert "MN-VER-06-S04" in study
    assert "oneWheelManyHosts" in study
    assert "sysmlEdgeInWheel=false" in study
    assert "mustNotInventUploadBind" in study
    assert "tipIsFace=false" in study
    assert "nServerFederation=false" in study
    assert "Hatch stays **0.19.11**" in study
    blobs = [nest, study, _impl_text(), REQUIREMENTS.read_text(encoding="utf-8"), VERIFY.read_text(encoding="utf-8")]
    joined = "\n".join(blobs)
    for needle in _TIP_AS_FACE_TEACH:
        assert needle not in joined, f"tip-as-face teach string still present: {needle!r}"
