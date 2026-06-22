"""Tests for novel-writer MCP tools."""

from __future__ import annotations

import asyncio
import json

import pytest


def test_prose_metrics_tool():
    from novel_mcp.server import prose_metrics

    raw = asyncio.run(prose_metrics("字" * 150))
    payload = json.loads(raw)
    assert payload["exit_code"] == 0
    assert payload["count"] == 150
    assert payload["ok"] is False
    assert payload["short_by"] == 150

    ok_raw = asyncio.run(prose_metrics("字" * 350))
    ok_payload = json.loads(ok_raw)
    assert ok_payload["ok"] is True


def test_chapter_prose_gate_tool_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from novel_mcp.server import chapter_prose_gate

    raw = asyncio.run(
        chapter_prose_gate(
            prose="字" * 350,
            chapter_dir="chapters",
            chp_num=1,
        )
    )
    payload = json.loads(raw)
    assert payload["exit_code"] == 0
    assert payload["ok"] is True
    assert payload["file_char_total"] == 350
    assert (tmp_path / "chapters" / "第001回.md").exists()


def test_chapter_prose_gate_tool_short_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from novel_mcp.server import chapter_prose_gate

    raw = asyncio.run(
        chapter_prose_gate(
            prose="字" * 150,
            chapter_dir="chapters",
            chp_num=1,
        )
    )
    payload = json.loads(raw)
    assert payload["exit_code"] == 1
    assert payload["ok"] is False
    assert not (tmp_path / "chapters" / "第001回.md").exists()


def test_chapter_prose_append_tool_short_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from novel_mcp.server import chapter_prose_append

    raw = asyncio.run(
        chapter_prose_append(
            prose="字" * 150,
            chapter_dir="chapters",
            chp_num=1,
        )
    )
    payload = json.loads(raw)
    assert payload["exit_code"] == 1
    assert not (tmp_path / "chapters" / "第001回.md").exists()


def test_chapter_prose_append_tool_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from novel_mcp.server import chapter_prose_append

    raw = asyncio.run(
        chapter_prose_append(
            prose="字" * 300,
            chapter_dir="chapters",
            chp_num=1,
        )
    )
    payload = json.loads(raw)
    assert payload["exit_code"] == 0
    assert payload["file_char_total"] == 300
    assert (tmp_path / "chapters" / "第001回.md").exists()

    raw2 = asyncio.run(
        chapter_prose_append(
            prose="風" * 500,
            chapter_dir="chapters",
            chp_num=1,
        )
    )
    payload2 = json.loads(raw2)
    assert payload2["file_char_total"] == 800
    assert payload2["paragraph_count"] == 2
