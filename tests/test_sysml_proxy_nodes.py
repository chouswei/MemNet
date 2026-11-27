"""MN-REQ-15 model pins: one-hop PROXY nodes recorded as implemented.

The requirement, the WriteProxy / FollowProxy behaviours, the ProxyNode /
FollowProxy parts that satisfy it, the MN-VER-15 cases and the allocate rows.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
MAP = ROOT / "sysml-models" / "outputs" / "ssot-to-code-allocate-map.md"


def _text(name: str) -> str:
    return (MODELS / name).read_text(encoding="utf-8")


def _block(text: str, marker: str) -> str:
    start = text.index(marker)
    open_at = text.index("{", start)
    depth = 0
    for i in range(open_at, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return " ".join(text[start : i + 1].split())
    raise AssertionError(marker)


def _req() -> str:
    return _block(_text("requirements.sysml"), "requirement def MN_REQ_15_ProxyNodes")


def test_15_is_its_own_implemented_nest_not_under_14():
    req = _text("requirements.sysml")
    group_14 = _block(req, "requirement def MN_REQ_14_AtelierBoardAsks")
    assert "MN_REQ_15" not in group_14
    mission = _block(req, "requirement def MN_REQ_00_MissionBridge")
    assert "requirement def MN_REQ_15_ProxyNodes" in mission
    doc = _req()
    assert "Status: implemented" in doc and 'requirementId : String = "MN-REQ-15"' in doc
    line = next(ln for ln in req.splitlines() if re.match(r"\s*MN-REQ-15\s", ln))
    assert "implemented" in line
    assert "proxyNodesReq" in req and "deriveProxyNodesFromMission" in req


def test_15_states_shape_and_write_rules():
    doc = _req()
    assert "id, target_session, target, target_backend" in doc
    assert "fixed node tag" in doc and "not a reserved tag" in doc
    assert "proxy_shape" in doc and "ID_PATTERN" in doc
    assert "does not require the target to exist" in doc
    assert "nothing routes by it" in doc


def test_15_states_reads_follow_and_reasons():
    doc = _req()
    assert "do not auto-follow" in doc
    assert "query follow" in doc and "follow_proxy" in doc
    assert "one hop only" in doc and "not followed again" in doc
    for word in ("dangling", "target_missing", "not_reachable", "not_proxy", "@FOLLOW"):
        assert word in doc, word
    assert "never read as a confirmed delete" in doc


def test_15_states_acl_gateway_housekeep_and_upgrade():
    doc = _req()
    assert "pin_map on the source session and on the target session" in doc
    assert "does not say whether the target exists" in doc
    assert "owners map only" in doc and "target_backend is never a route" in doc
    assert "no forbidden_session leak" in doc
    assert "dangling_proxies" in doc and "prune does not delete a PROXY" in doc
    assert "byte-identical to 0.20.8" in doc and "unknown_tag" in doc
    for path in ("tests/test_proxy_nodes.py", "tests/test_product_gateway.py"):
        assert path in doc, path


def test_read_surfaces_block_lists_follow_reads():
    req = _text("requirements.sysml")
    block = req.split("READ-SURFACES-BEGIN", 1)[1].split("READ-SURFACES-END", 1)[0].split()
    assert block[-2:] == ["follow_proxy", "query_follow"]


def test_behaviours_parts_and_satisfy():
    beh = _text("behaviour.sysml")
    for name in ("WriteProxy", "FollowProxy"):
        assert "MN-REQ-15" in _block(beh, f"action def {name}"), name
    follow = _block(beh, "action def FollowProxy")
    assert "owners map" in follow and "--resolved-id" in follow
    imp = _text("implementation.sysml")
    for name, action in (("ProxyNode", "WriteProxy"), ("FollowProxy", "FollowProxy")):
        body = _block(imp, f"part def {name} ")
        assert "attribute implemented : Boolean = true;" in body
        assert re.search(r"satisfy\s+[\w:]*MN_REQ_15_ProxyNodes\b", body), name
        assert f"MemNetBehaviour::{action}" in body
    follow_part = _block(imp, "part def FollowProxy ")
    assert "attribute maxHops : Integer = 1;" in follow_part
    assert "attribute autoFollowOnPinMap : Boolean = false;" in follow_part
    assert "attribute pruneDeletesProxy : Boolean = false;" in follow_part
    assert "attribute routesByTargetBackend : Boolean = false;" in follow_part


def test_allocations_name_live_paths_and_map_rows():
    imp = _text("implementation.sysml")
    assert 'attribute path : String = "parts/common/memnet/memnet/proxy.py";' in imp
    assert "part proxyMod : ProxyNodeMod;" in imp
    ledger = MAP.read_text(encoding="utf-8")
    for alloc in ("proxyNodeToMod", "followProxyToMod"):
        assert f"allocation {alloc} : SoftwareAllocate" in imp, alloc
        assert f"| {alloc} |" in ledger, alloc
    for rel in re.findall(r'attribute \w*[pP]ath : String = "([^"]+)"', imp):
        assert (ROOT / rel).exists(), rel


def test_verify_cases_name_runtime_tests():
    ver = _text("verify.sysml")
    cases = {
        "MN_VER_15_S01_ProxyWriteShape": ("tests/test_proxy_nodes.py",),
        "MN_VER_15_S02_FollowOneHop": ("tests/test_proxy_nodes.py", "tests/test_proxy_mcp.py"),
        "MN_VER_15_S03_GatewayHopAndHousekeep": ("tests/test_product_gateway.py",),
        "MN_VER_15_S04_ProxyUpgradeSafety": ("tests/test_mixed_version_clients.py",),
    }
    for name, paths in cases.items():
        body = _block(ver, f"verification def {name}")
        assert "verify proxyNodesReq;" in body, name
        for path in paths:
            assert path in body and (ROOT / path).exists(), (name, path)
        assert re.search(rf"verification \w+\s*:\s*{name};", ver), f"{name} has no usage"
