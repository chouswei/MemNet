"""Tests for dual-loop play context."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from novel_mcp.chapter_io import last_committed_paragraph
from novel_mcp.play_context import (
    player_beat_prepare,
    prose_beat_prepare,
    script_beat_prepare,
)


def test_last_committed_paragraph(tmp_path: Path) -> None:
    ch = tmp_path / "第001回.md"
    ch.write_text(
        "# 第一回\n\n第一段。\n\n第二段結尾。",
        encoding="utf-8",
    )
    assert last_committed_paragraph(ch) == "第二段結尾。"


def test_player_beat_prepare_bad_choice() -> None:
    out = player_beat_prepare(session="mn_test", choice=9)
    assert out["exit_code"] == 2


def test_script_beat_prepare_phase() -> None:
    with patch("novel_mcp.play_context.read_beat_stage", return_value="oln"), patch(
        "novel_mcp.play_context.beat_turn_begin",
        return_value={"pipeline": {}, "finish_params": {}},
    ):
        out = script_beat_prepare(session="mn_test", choice=6)
    assert out["exit_code"] == 0
    assert out["phase"] == "script"
    assert out["player"]["lib_query"] is True
    assert out["fsm"]["stages"] == ["oln", "sbd", "scr"]


def test_prose_beat_prepare_gate() -> None:
    with patch("novel_mcp.play_context.read_beat_stage", return_value="oln"):
        out = prose_beat_prepare(session="mn_test")
    assert out["exit_code"] == 2
    assert "prose" in out["errors"][0]


def test_prose_beat_prepare_ok() -> None:
    with patch("novel_mcp.play_context.read_beat_stage", return_value="prose"), patch(
        "novel_mcp.play_context.beat_turn_begin",
        return_value={
            "pipeline": {"scr_row": "@SCR: …", "oln_row": "@OLN: …"},
            "finish_params": {},
        },
    ):
        out = prose_beat_prepare(session="mn_test")
    assert out["exit_code"] == 0
    assert out["phase"] == "prose"
    assert out["scr_row"] == "@SCR: …"
