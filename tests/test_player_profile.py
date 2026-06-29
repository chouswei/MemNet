"""Tests for player_profile validation and commit."""

from __future__ import annotations

from unittest.mock import patch

from novel_mcp.player_profile import commit_profile, read_profile, validate_profile


def test_validate_profile_ok() -> None:
    assert validate_profile(None, "北見硝", "男") == []


def test_validate_profile_bad_name() -> None:
    errs = validate_profile(None, "A", "男")
    assert any("name" in e for e in errs)


def test_validate_profile_bad_gender() -> None:
    errs = validate_profile(None, "北見硝", "M")
    assert any("gender" in e for e in errs)


def test_read_profile_unset() -> None:
    with patch("novel_mcp.player_profile.read_usr_by_key", side_effect=lambda _s, k: "未定"):
        out = read_profile("mn_x")
    assert out["complete"] is False
    assert out["name_set"] is False


def test_commit_profile_updates_plr_gender() -> None:
    plr_body = "P01|流民|1627|未定|0|0|靈魂圖書館登峰造極|氣血:6/6"

    def fake_read_get(session, record_id):
        if record_id == "P01":
            return plr_body
        return None

    with patch("novel_mcp.player_profile.read_usr_by_key", return_value="未定"), patch(
        "novel_mcp.player_profile.first_plr_id", return_value="P01"
    ), patch("novel_mcp.player_profile.usr_id_for_key", side_effect=lambda _s, k: {"pc_name": "USR03", "pc_gender": "USR53"}.get(k)), patch(
        "novel_mcp.player_profile.read_get_body", side_effect=fake_read_get
    ), patch(
        "novel_mcp.player_profile.graph_update", return_value=(0, [])
    ), patch(
        "novel_mcp.player_profile.read_profile",
        return_value={
            "exit_code": 0,
            "name": "北見硝",
            "gender": "男",
            "complete": True,
            "errors": [],
        },
    ):
        out = commit_profile("mn_x", "北見硝", "男")
    assert out["exit_code"] == 0
    assert out["complete"] is True
