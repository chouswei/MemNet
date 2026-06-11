"""Tests for memnet_mcp client and MCP tools."""

from __future__ import annotations

import asyncio
import json

import pytest

from memnet_mcp.client import MemNetResponse, run_memnet


def _session_from_stdout(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("@SESSION:"):
            return line.split("|", 1)[0].replace("@SESSION:", "").strip()
    raise AssertionError(f"no @SESSION in {stdout!r}")


def test_run_memnet_session_open(memnet_temp, schema_file):
    resp = run_memnet(["session", "open", "--map-file", str(schema_file)])
    assert resp.exit_code == 0, resp.stderr
    assert resp.session_id
    assert resp.session_id.startswith("mn_")


def test_run_memnet_add_and_warm(memnet_temp, schema_file):
    open_resp = run_memnet(["session", "open", "--map-file", str(schema_file)])
    sid = _session_from_stdout(open_resp.stdout)
    add_resp = run_memnet(
        ["add", "--stdin"],
        stdin="@PLR: PLR77|Test|1|0|0|0|bag",
        session=sid,
    )
    assert add_resp.exit_code == 0, add_resp.stderr
    warm_resp = run_memnet(
        ["query", "warm", "--anchor", "PLR77", "--depth", "1"],
        session=sid,
    )
    assert warm_resp.exit_code == 0
    assert "PLR77" in warm_resp.stdout


def test_serve_required_without_inline(monkeypatch):
    monkeypatch.delenv("MEMNET_TEST_INLINE", raising=False)
    monkeypatch.delenv("MEMNET_SERVE_INTERNAL", raising=False)
    monkeypatch.setenv("MEMNET_SERVE_PORT", "59999")
    resp = run_memnet(["session", "current"])
    assert resp.exit_code == 2
    assert resp.errors
    assert "serve_required" in resp.errors[0]


def test_memnet_response_to_json():
    resp = MemNetResponse(
        exit_code=0,
        stdout="@PLR: X|a|1|0|0|0|x",
        stderr="",
        session_id="mn_abcd",
        errors=[],
    )
    payload = json.loads(resp.to_json())
    assert payload["exit_code"] == 0
    assert payload["session_id"] == "mn_abcd"


mcp = pytest.importorskip("mcp")


def test_serve_status_tool(monkeypatch):
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import serve_status

    raw = asyncio.run(serve_status())
    payload = json.loads(raw)
    assert "running" in payload
    assert "host" in payload
    assert "port" in payload


def test_query_warm_tool_envelope(memnet_temp, schema_file, monkeypatch):
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import query_warm, session_open

    open_raw = asyncio.run(
        session_open(map_lines=schema_file.read_text(encoding="utf-8").strip().splitlines())
    )
    open_payload = json.loads(open_raw)
    assert open_payload["exit_code"] == 0
    sid = open_payload["session_id"]
    assert sid

    monkeypatch.setenv("MEMNET_SESSION", sid)
    add_resp = run_memnet(
        ["add", "--stdin"],
        stdin="@PLR: PLR55|Warm|1|0|0|0|ok",
        session=sid,
    )
    assert add_resp.exit_code == 0

    warm_raw = asyncio.run(query_warm(anchor="PLR55", depth=1, session=sid))
    warm_payload = json.loads(warm_raw)
    assert warm_payload["exit_code"] == 0
    assert "PLR55" in warm_payload["stdout"]
    assert warm_payload["errors"] == []
