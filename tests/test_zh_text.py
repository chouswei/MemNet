"""Tests for zh_text prose metrics."""

from __future__ import annotations

from novel_mcp.zh_text import count_zh_chars, parse_scene_band, prose_status


def test_count_zh_chars_empty():
    assert count_zh_chars("") == 0


def test_count_zh_chars_punctuation_only():
    assert count_zh_chars("，。！？…") == 0


def test_count_zh_chars_mixed():
    assert count_zh_chars("Hello 你好 world 世界") == 4


def test_prose_status_count_only():
    text = "深" * 150
    s = prose_status(text)
    assert s["count"] == 150
    assert s["ok"] is True
    assert s["gate_ready"] is True
    assert s["status"] == "no_gate"
    assert s["min"] is None
    assert s["max"] is None
    assert s["forbidden_until_gate_ready"] == ""
    assert "beat_turn_finish" in s["next_action"]


def test_prose_status_short():
    text = "深" * 150
    s = prose_status(text, min_chars=300, max_chars=600)
    assert s["count"] == 150
    assert s["ok"] is False
    assert s["gate_ready"] is False
    assert s["status"] == "short"
    assert s["short_by"] == 150
    assert s["target_chars"] == 450
    assert "chapter_prose_gate" in s["forbidden_until_gate_ready"]


def test_prose_status_long():
    text = "秋" * 650
    s = prose_status(text, min_chars=300, max_chars=600)
    assert s["ok"] is False
    assert s["status"] == "long"
    assert s["long_by"] == 50
    assert "trim" in s["hint"]


def test_prose_status_ok_at_bounds():
    assert prose_status("字" * 300, min_chars=300, max_chars=600)["ok"] is True
    assert prose_status("字" * 600, min_chars=300, max_chars=600)["ok"] is True


def test_parse_scene_band():
    assert parse_scene_band("650_950_zh") == (650, 950)
    assert parse_scene_band("300_600") == (300, 600)


def test_prose_status_ok_mid():
    s = prose_status("風" * 500, min_chars=300, max_chars=600)
    assert s["ok"] is True
    assert s["gate_ready"] is True
    assert s["status"] == "ok"
    assert s["hint"] == ""
    assert s["next_action"] == "beat_prose_finalize once (same min_chars/max_chars)"


def test_prose_status_short_advisory():
    text = "字" * 300
    s = prose_status(text, advisory_target=800)
    assert s["count"] == 300
    assert s["status"] == "short_advisory"
    assert s["target_chars"] == 800
    assert s["draft_vs_target"] == -500
    assert "expand ~500" in s["hint"]
    assert s["ok"] is True
