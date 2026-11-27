"""MN-REQ-05.6 live session limits: the SysML SSOT and the code stay aligned."""

from __future__ import annotations

import re
from pathlib import Path

from memnet.config import Caps
from memnet.serve_retry import _READ_VERBS
from memnet.snapshot import _LIM_PREFIX

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
DEPLOY = MODELS / "deploy.sysml"
IMPLEMENTATION = MODELS / "implementation.sysml"
BEHAVIOUR = MODELS / "behaviour.sysml"
RUNTIME = ROOT / "tests" / "test_session_live_limits.py"
SATISFY = "satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_6_LiveSessionLimits;"


def _attr(text: str, name: str) -> str:
    m = re.search(rf"attribute {name} : \w+ = ([^;]+);", text)
    assert m, f"{name} missing"
    return m.group(1).strip().strip('"')


def test_requirement_def_index_usage_and_derivation():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "requirement def MN_REQ_05_6_LiveSessionLimits" in req
    assert 'attribute requirementId : String = "MN-REQ-05.6"' in req
    assert "    MN-REQ-05.6        Live session TTL and size-cap change" in req
    assert "requirement liveSessionLimitsReq" in req
    assert "end #derive ::> liveSessionLimitsReq;" in req
    assert "MN-VER-05-S10" in req


def test_deploy_flags_match_the_code():
    text = DEPLOY.read_text(encoding="utf-8")
    assert SATISFY in text
    assert _attr(text, "liveLimitsShipped") == "true"
    assert _attr(text, "liveLimitsDropsRows") == "false"
    assert _attr(text, "liveLimitsAboveProcessCapAllowed") == "false"
    assert _attr(text, "liveLimitsSetPermission") == "mutate"
    assert _attr(text, "liveLimitsReadPermission") == "pin_map"
    assert _attr(text, "liveLimitsSnapshotLinePrefix") == _LIM_PREFIX.strip()
    # The process caps the model names are the code defaults.
    caps = Caps()
    assert int(_attr(text, "maxRows")) == caps.max_rows
    assert int(_attr(text, "maxSessionBytesDefault")) == caps.max_session_bytes


def test_each_deploy_flag_cites_a_runtime_test_that_exists():
    text = DEPLOY.read_text(encoding="utf-8")
    src = RUNTIME.read_text(encoding="utf-8")
    cited = re.findall(r"attribute liveLimits\w+ : Boolean = \w+;\s+// (test_\w+)", text)
    assert len(cited) >= 7
    for name in cited:
        assert f"def {name}(" in src, name


def test_verify_case_names_real_tests_and_verifies_the_requirement():
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_05_S10_LiveSessionLimits" in ver
    assert 'attribute verificationId : String = "MN-VER-05-S10"' in ver
    assert "verify liveSessionLimitsReq;" in ver
    assert "verification liveSessionLimitsVerify" in ver
    block = ver.split("verification def MN_VER_05_S10_LiveSessionLimits", 1)[1]
    block = block.split("verification def ", 1)[0]
    names = re.findall(r"::(test_\w+)", block)
    assert len(names) >= 10
    src = RUNTIME.read_text(encoding="utf-8")
    for name in names:
        assert f"def {name}(" in src, name
    for flag in re.findall(r"\.(liveLimits\w+) ==", block):
        assert f"attribute {flag} " in DEPLOY.read_text(encoding="utf-8"), flag


def test_implementation_and_behaviour():
    impl = IMPLEMENTATION.read_text(encoding="utf-8")
    mod = impl.split("part def SessionLifecycleMod", 1)[1].split("part def ", 1)[0]
    assert SATISFY in mod
    assert "attribute def EvSetLimits" in BEHAVIOUR.read_text(encoding="utf-8")


def test_retry_classes_match_the_model():
    assert ("session", "limits") in _READ_VERBS
    assert ("session", "set-limits") not in _READ_VERBS
