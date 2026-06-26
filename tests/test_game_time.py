"""Tests for novel_mcp.game_time (seed-agnostic axis only)."""

from __future__ import annotations

import pytest

from novel_mcp.game_time import (
    GameTime,
    advance_sys_time,
    check_sys_time_update,
    parse_game_time,
    year_from_sys_time,
)


def test_parse_iso_canonical():
    gt = parse_game_time("1637-09-15T05")
    assert gt == GameTime(1637, 9, 15, 5)
    assert gt.to_canonical() == "1637-09-15T05"


def test_parse_legacy_paren_year():
    gt = parse_game_time("崇禎十年(1637)秋·寅")
    assert gt is not None
    assert gt.year == 1637
    assert gt.month == 1  # neutral legacy fallback


def test_advance_crosses_midnight():
    out = advance_sys_time("1637-09-15T23", hours=2)
    assert out == "1637-09-16T01"


def test_year_from_sys_time():
    assert year_from_sys_time("1637-09-15T05") == 1637
    assert year_from_sys_time("崇禎十年(1637)秋") == 1637


def test_advance_legacy_raises():
    with pytest.raises(ValueError):
        advance_sys_time("完全無法解析", hours=1)


def test_check_sys_time_update_iso_regress():
    assert check_sys_time_update("1637-09-16T04", "1637-09-15T04") is not None


def test_check_sys_time_update_legacy_to_iso_ok():
    assert check_sys_time_update("崇禎十年(1637)秋·寅", "1637-09-16T04") is None


def test_check_sys_time_update_bad_format():
    err = check_sys_time_update("1637-09-16T04", "秋·卯")
    assert err is not None
    assert "time_format" in err
