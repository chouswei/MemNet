"""Tests for seed-driven profile validation rules."""

from __future__ import annotations

from unittest.mock import patch

from novel_mcp.player_profile import commit_profile, read_profile, validate_profile
from novel_mcp.setup_profile_rules import read_profile_rules


def test_read_profile_rules_defaults() -> None:
    rules = read_profile_rules(None)
    assert rules["name_re"].match("北見硝")
    assert "男" in rules["genders"]


def test_read_profile_rules_from_seed() -> None:
    def read_usr(_s, key):
        return {
            "setup_profile_name_rule": "cjk_2_4",
            "setup_profile_genders": "男;女",
        }.get(key)

    with patch("novel_mcp.setup_profile_rules.read_usr_by_key", side_effect=read_usr):
        rules = read_profile_rules("mn_x")
    assert rules["name_re"].match("沈芯")
    assert rules["genders"] == {"男", "女"}


def test_validate_profile_partial_name_only() -> None:
    assert validate_profile(None, "北見硝", "未定", require_name=True, require_gender=False) == []


def test_commit_profile_name_then_gender() -> None:
    state = {"pc_name": "未定", "pc_gender": "未定"}

    def read_usr(_s, key):
        return state.get(key, "未定")

    def uid_for_key(_s, key):
        return {"pc_name": "USR03", "pc_gender": "USR53"}.get(key)

    updates: list[list[str]] = []

    def fake_update(session, lines):
        updates.append(lines)
        for ln in lines:
            if ln.startswith("@USR:"):
                parts = ln.split(":", 1)[1].strip().split("|")
                if len(parts) >= 3:
                    state[parts[1]] = parts[2]
        return 0, []

    plr_body = "P01|流民|1627|未定|0|0|靈魂圖書館登峰造極|氣血:6/6"

    with (
        patch("novel_mcp.player_profile.read_usr_by_key", side_effect=read_usr),
        patch("novel_mcp.player_profile.usr_id_for_key", side_effect=uid_for_key),
        patch("novel_mcp.player_profile.graph_update", side_effect=fake_update),
        patch("novel_mcp.player_profile.read_get_body", return_value=plr_body),
        patch("novel_mcp.player_profile.first_plr_id", return_value="P01"),
        patch("novel_mcp.setup_profile_rules.read_usr_by_key", side_effect=read_usr),
    ):
        out1 = commit_profile("mn_x", "北見硝", "")
        out2 = commit_profile("mn_x", "", "男")
    assert out1["exit_code"] == 0
    assert out1["complete"] is False
    assert out1["name_set"] is True
    assert out2["complete"] is True
    assert out2["gender_set"] is True
    plr_updates = [ln for batch in updates for ln in batch if ln.startswith("@PLR:")]
    assert plr_updates
    assert "|男|" in plr_updates[-1]
