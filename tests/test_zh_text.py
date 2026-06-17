"""Tests for zh_text prose metrics."""

from __future__ import annotations

from memnet_mcp.zh_text import count_zh_chars, prose_status


def test_count_zh_chars_empty():
    assert count_zh_chars("") == 0


def test_count_zh_chars_punctuation_only():
    assert count_zh_chars("，。！？…") == 0


def test_count_zh_chars_mixed():
    assert count_zh_chars("Hello 你好 world 世界") == 4


def test_prose_status_short():
    text = "深" * 150
    s = prose_status(text, min_chars=300, max_chars=600)
    assert s["count"] == 150
    assert s["ok"] is False
    assert s["status"] == "short"
    assert s["short_by"] == 150
    assert s["long_by"] == 0
    assert "expand" in s["hint"]


def test_prose_status_long():
    text = "秋" * 650
    s = prose_status(text, min_chars=300, max_chars=600)
    assert s["ok"] is False
    assert s["status"] == "long"
    assert s["long_by"] == 50
    assert "trim" in s["hint"]


def test_prose_status_ok_at_bounds():
    assert prose_status("字" * 300)["ok"] is True
    assert prose_status("字" * 600)["ok"] is True


def test_prose_status_ok_mid():
    s = prose_status("風" * 500)
    assert s["ok"] is True
    assert s["status"] == "ok"
    assert s["hint"] == ""
