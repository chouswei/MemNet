"""Tests for seed-driven HUD time formatters."""

from __future__ import annotations

from novel_mcp.game_time import GameTime
from novel_mcp.time_display import format_time_display, parse_time_spec


def test_parse_time_spec():
    spec = parse_time_spec(
        "axis=iso;display=chongzhen_shichen;era_base=1628;era_name=崇禎"
    )
    assert spec["display"] == "chongzhen_shichen"
    assert spec["era_base"] == "1628"


def test_format_iso_only_without_usr43():
    gt = GameTime(1637, 9, 15, 5)
    assert format_time_display(gt, None) == "1637-09-15T05"


def test_format_chongzhen_from_seed_spec():
    gt = GameTime(1637, 9, 15, 5)
    label = format_time_display(
        gt,
        "axis=iso;display=chongzhen_shichen;era_base=1628;era_name=崇禎",
    )
    assert label.startswith("1637-09-15T05（")
    assert "崇禎十年九月15日・卯時" in label


def test_unknown_display_falls_back_to_iso():
    gt = GameTime(2000, 1, 1, 0)
    assert format_time_display(gt, "display=stardate_fiction") == "2000-01-01T00"
