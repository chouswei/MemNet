"""Tests for script-stage wire validation (mechanical bundle only)."""

from __future__ import annotations

from novel_mcp.stage_wire_validate import (
    validate_script_draft_bundle,
    validate_stage_wires,
)


def test_n01_in_scr_content_not_blocked() -> None:
    line = "@SCR: SCR01|1|1|動作|N01說了話|內心|音效|delete_on_settle"
    result = validate_stage_wires([line], presentation={})
    assert not result["violations"]


def test_canonical_name_in_scr_not_blocked() -> None:
    line = "@SCR: SCR02|1|1|動作|沈芯轉身|內心|音效|delete_on_settle"
    pres = {
        "scene": {
            "npcs": [
                {
                    "id": "N01",
                    "name": "匠戶孤女",
                    "name_visible": False,
                    "canonical_name": "沈芯",
                }
            ]
        }
    }
    result = validate_stage_wires([line], presentation=pres)
    assert not result["violations"]


def test_bundle_requires_matching_shots() -> None:
    oln = ["@OLN: OLN01|1|a|b|c|d|delete"]
    sbd = ["@SBD: SBD01|1|1|a|b|c|d|delete", "@SBD: SBD02|1|2|a|b|c|d|delete"]
    scr = ["@SCR: SCR01|1|1|a|b|c|d|delete"]
    errors = validate_script_draft_bundle(oln, sbd, scr)
    assert errors
    assert any("SBD shots" in e or "SCR" in e for e in errors)
