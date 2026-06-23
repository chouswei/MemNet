"""Tests for memnet_mcp client and MCP tools."""

from __future__ import annotations

import asyncio
import json

import pytest

from memnet_mcp.client import MemNetResponse, run_memnet
from memnet_mcp.seed import supplement_seed_lines


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


def test_memnet_response_merge():
    open_resp = MemNetResponse(
        exit_code=0,
        stdout="@SESSION: mn_abcd|…\n",
        stderr="MEMNET_SESSION=mn_abcd\n",
        session_id="mn_abcd",
        errors=[],
    )
    seed_resp = MemNetResponse(
        exit_code=0,
        stdout="@CFG: CFG01|test|CFG01|1|ok\n",
        stderr="",
        session_id="mn_abcd",
        errors=[],
    )
    merged = MemNetResponse.merge(open_resp, seed_resp)
    assert merged.exit_code == 0
    assert merged.session_id == "mn_abcd"
    assert "CFG01" in merged.stdout
    assert "@SESSION:" in merged.stdout

    failed_seed = MemNetResponse(
        exit_code=1,
        stdout="",
        stderr="@ERR: id_exists|CFG01\n",
        session_id="mn_abcd",
        errors=["@ERR: id_exists|CFG01"],
    )
    bad = MemNetResponse.merge(open_resp, failed_seed)
    assert bad.exit_code == 1
    assert bad.errors

    open_fail = MemNetResponse(exit_code=1, stdout="", stderr="@ERR: no_map", session_id=None, errors=["x"])
    assert MemNetResponse.merge(open_fail, seed_resp) is open_fail


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


def test_supplement_seed_lines():
    out = supplement_seed_lines(None)
    assert len(out) == 5
    assert all(line.startswith("@LAW:") for line in out)
    custom = [
        "@LAW: LAW01|custom|on_add|x|y",
        "@CFG: CFG01|a|CFG01|1|b|c",
    ]
    out2 = supplement_seed_lines(custom)
    assert out2[0].startswith("@LAW: LAW02")
    assert any("LAW01|custom" in line for line in out2)
    assert any("CFG01" in line for line in out2)


def test_session_open_default_law(memnet_temp, schema_file, monkeypatch):
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import query_warm, session_open

    open_raw = asyncio.run(
        session_open(map_lines=schema_file.read_text(encoding="utf-8").strip().splitlines())
    )
    payload = json.loads(open_raw)
    assert payload["exit_code"] == 0, payload
    sid = payload["session_id"]
    assert "LAW01" in payload["stdout"]
    assert "LAW05" in payload["stdout"]

    warm_raw = asyncio.run(query_warm(anchor="PLR01", depth=1, session=sid))
    warm_payload = json.loads(warm_raw)
    # anchor missing — still get all LAW rows (goldfish invariants)
    assert "LAW01" in warm_payload["stdout"]
    assert "LAW05" in warm_payload["stdout"]


def test_session_open_seed_lines_unknown_relation_aborts(memnet_temp, schema_file, monkeypatch):
    """Seed batch with a novel @EDG relation must surface the error and roll back."""
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import housekeep_stats, session_open

    seed = [
        "@CFG: CFG01|x|CFG01|1|x|x",
        "@PLR: PLR01|Hero|1|0|0|0|x",
        "@PLR: PLR02|Friend|1|0|0|0|x",
        "@EDG: E1|PLR01|owns|PLR02|tie|persistent",
    ]
    open_raw = asyncio.run(
        session_open(
            map_lines=schema_file.read_text(encoding="utf-8").strip().splitlines(),
            seed_lines=seed,
        )
    )
    payload = json.loads(open_raw)
    assert payload["exit_code"] != 0, "seed batch with unknown relation must fail closed"
    assert any("unknown_relation" in e for e in payload["errors"]), payload["errors"]
    sid = payload["session_id"]
    stats_raw = asyncio.run(housekeep_stats(session=sid))
    stats_payload = json.loads(stats_raw)
    assert "rows|0" in stats_payload["stdout"], stats_payload["stdout"]


def test_session_open_seed_lines_allow_new_relation(memnet_temp, schema_file, monkeypatch):
    """Same seed batch succeeds when allow_new_relation=True is passed through."""
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import housekeep_stats, session_open

    seed = [
        "@CFG: CFG01|x|CFG01|1|x|x",
        "@PLR: PLR01|Hero|1|0|0|0|x",
        "@PLR: PLR02|Friend|1|0|0|0|x",
        "@EDG: E1|PLR01|owns|PLR02|tie|persistent",
    ]
    open_raw = asyncio.run(
        session_open(
            map_lines=schema_file.read_text(encoding="utf-8").strip().splitlines(),
            seed_lines=seed,
            allow_new_relation=True,
        )
    )
    payload = json.loads(open_raw)
    assert payload["exit_code"] == 0, payload
    sid = payload["session_id"]
    stats_raw = asyncio.run(housekeep_stats(session=sid))
    stats_payload = json.loads(stats_raw)
    assert "rows|4" in stats_payload["stdout"], stats_payload["stdout"]


def test_session_open_seed_lines(memnet_temp, schema_file, monkeypatch):
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import query_warm, session_open

    seed = [
        "@CFG: CFG01|daily_news|CFG01|3|digest|notes",
        "@LAW: LAW01|atomise|on_add|tokens_only|no_sentences_in_fields",
        "@LAW: LAW02|graph|on_add|use_edg|relations_via_EDG_not_field_lists",
    ]
    open_raw = asyncio.run(
        session_open(
            map_lines=schema_file.read_text(encoding="utf-8").strip().splitlines(),
            seed_lines=seed,
        )
    )
    payload = json.loads(open_raw)
    assert payload["exit_code"] == 0, payload
    sid = payload["session_id"]
    assert sid
    assert "CFG01" in payload["stdout"]
    assert "LAW01" in payload["stdout"]

    warm_raw = asyncio.run(query_warm(anchor="CFG01", depth=1, session=sid))
    warm_payload = json.loads(warm_raw)
    assert warm_payload["exit_code"] == 0
    assert "CFG01" in warm_payload["stdout"]
    assert "LAW01" in warm_payload["stdout"]
