"""Tests for novel-writer MCP tools."""

from __future__ import annotations

import asyncio
import json


def test_beat_turn_begin_tool(monkeypatch):
    def fake_begin(**kwargs):
        return {"exit_code": 0, "tool": "beat_turn_begin", "pipeline": {}, "finish_params": {}}

    import novel_mcp.server as srv

    monkeypatch.setattr(srv, "do_beat_turn_begin", fake_begin)
    raw = asyncio.run(srv.beat_turn_begin(session="mn_test"))
    payload = json.loads(raw)
    assert payload["tool"] == "beat_turn_begin"


def test_memnet_mcp_has_no_beat_turn_tools():
    import asyncio
    import memnet_mcp.server as mem_srv

    names = {t.name for t in asyncio.run(mem_srv.mcp.list_tools())}
    assert "beat_turn_begin" not in names
    assert "beat_turn_finish" not in names


def test_novel_mcp_has_beat_turn_tools():
    import asyncio
    import novel_mcp.server as novel_srv

    names = {t.name for t in asyncio.run(novel_srv.mcp.list_tools())}
    assert "beat_turn_begin" in names
    assert "beat_turn_finish" in names
    assert "bootstrap_from_seed" in names


def test_prose_metrics_tool_mcp_forbidden():
    from novel_mcp.server import prose_metrics

    raw = asyncio.run(prose_metrics("字" * 150))
    payload = json.loads(raw)
    assert payload["exit_code"] == 1
    assert payload["mcp_forbidden"] is True
    assert payload["count"] == 150
    assert payload["status"] == "no_gate"
    assert "prose_count.py" in payload["errors"][0]


def test_prose_metrics_tool_with_gate_mcp_forbidden():
    from novel_mcp.server import prose_metrics

    short = json.loads(asyncio.run(prose_metrics("字" * 150, min_chars=300, max_chars=600)))
    assert short["exit_code"] == 1
    assert short["mcp_forbidden"] is True
    assert short["ok"] is False
    assert short["gate_ready"] is False
    assert short["short_by"] == 150

    ok_payload = json.loads(
        asyncio.run(prose_metrics("字" * 350, min_chars=300, max_chars=600))
    )
    assert ok_payload["exit_code"] == 1
    assert ok_payload["mcp_forbidden"] is True
    assert ok_payload["ok"] is True
    assert ok_payload["gate_ready"] is True


def test_chapter_prose_gate_tool_valid_without_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMNET_WORKSPACE_ROOT", str(tmp_path))
    from novel_mcp.server import chapter_prose_gate

    raw = asyncio.run(
        chapter_prose_gate(
            prose="字" * 150,
            chapter_dir="chapters",
            chp_num=1,
            workspace_root=str(tmp_path),
        )
    )
    payload = json.loads(raw)
    assert payload["exit_code"] == 0
    assert payload["ok"] is True
    assert payload["status"] == "no_gate"
    assert payload["file_char_total"] == 150
    assert (tmp_path / "chapters" / "第001回.md").exists()


def test_chapter_prose_gate_tool_valid_with_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMNET_WORKSPACE_ROOT", str(tmp_path))
    from novel_mcp.server import chapter_prose_gate

    raw = asyncio.run(
        chapter_prose_gate(
            prose="字" * 350,
            chapter_dir="chapters",
            chp_num=1,
            min_chars=300,
            max_chars=600,
            workspace_root=str(tmp_path),
        )
    )
    payload = json.loads(raw)
    assert payload["exit_code"] == 0
    assert payload["ok"] is True
    assert payload["file_char_total"] == 350
    assert (tmp_path / "chapters" / "第001回.md").exists()


def test_chapter_prose_gate_tool_short_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMNET_WORKSPACE_ROOT", str(tmp_path))
    from novel_mcp.server import chapter_prose_gate

    raw = asyncio.run(
        chapter_prose_gate(
            prose="字" * 150,
            chapter_dir="chapters",
            chp_num=1,
            min_chars=300,
            max_chars=600,
            workspace_root=str(tmp_path),
        )
    )
    payload = json.loads(raw)
    assert payload["exit_code"] == 1
    assert payload["ok"] is False
    assert payload["gate_blocked"] is True
    assert payload["gate_ready"] is False
    assert "beat_prose_finalize" in payload["forbidden_until_gate_ready"]
    assert payload.get("mcp_retry_forbidden") is True
    assert not (tmp_path / "chapters" / "第001回.md").exists()


def test_beat_prose_finalize_tool_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMNET_WORKSPACE_ROOT", str(tmp_path))
    from novel_mcp.server import beat_prose_finalize

    raw = asyncio.run(
        beat_prose_finalize(
            prose="字" * 350,
            chapter_dir="chapters",
            chp_num=1,
            min_chars=300,
            max_chars=600,
            workspace_root=str(tmp_path),
        )
    )
    payload = json.loads(raw)
    assert payload["exit_code"] == 0
    assert payload["tool"] == "beat_prose_finalize"
    assert payload["mcp_budget_per_beat"] == 1
    assert (tmp_path / "chapters" / "第001回.md").exists()


def test_chapter_prose_append_tool_short_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMNET_WORKSPACE_ROOT", str(tmp_path))
    from novel_mcp.server import chapter_prose_append

    raw = asyncio.run(
        chapter_prose_append(
            prose="字" * 150,
            chapter_dir="chapters",
            chp_num=1,
            min_chars=300,
            max_chars=600,
            workspace_root=str(tmp_path),
        )
    )
    payload = json.loads(raw)
    assert payload["exit_code"] == 1
    assert not (tmp_path / "chapters" / "第001回.md").exists()


def test_chapter_prose_append_tool_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMNET_WORKSPACE_ROOT", str(tmp_path))
    from novel_mcp.server import chapter_prose_append

    raw = asyncio.run(
        chapter_prose_append(
            prose="字" * 300,
            chapter_dir="chapters",
            chp_num=1,
            min_chars=300,
            max_chars=600,
            workspace_root=str(tmp_path),
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
            min_chars=300,
            max_chars=600,
            workspace_root=str(tmp_path),
        )
    )
    payload2 = json.loads(raw2)
    assert payload2["file_char_total"] == 800
    assert payload2["paragraph_count"] == 2
