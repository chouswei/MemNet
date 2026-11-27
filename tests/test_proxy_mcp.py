"""MCP follow_proxy (MN-REQ-15): one new tool; the 30 0.20.8 tools keep their names."""

from __future__ import annotations

import asyncio
import json

import pytest

pytest.importorskip("mcp")

BASE_TOOLS = frozenset(
    {
        "serve_status",
        "session_open",
        "session_list",
        "session_close",
        "snap_model",
        "session_current",
        "session_load",
        "session_save",
        "pin_map",
        "query_warm",
        "find",
        "query_walk",
        "typed_walk",
        "mutate",
        "add",
        "update",
        "import_slice",
        "session_acl_grant",
        "session_acl_bind",
        "session_acl_enable",
        "reserve",
        "extend",
        "release",
        "export_pin_map",
        "ingest_sysml",
        "ingest_codebase",
        "ingest_pcba",
        "ingest_skills",
        "read_list",
        "housekeep_stats",
    }
)


def test_follow_proxy_is_the_one_new_tool(monkeypatch):
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import mcp

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert len(BASE_TOOLS) == 30
    assert names == BASE_TOOLS | {"follow_proxy"}
    tool = next(t for t in tools if t.name == "follow_proxy")
    props = (tool.inputSchema or {}).get("properties") or {}
    assert set(props) == {"id", "session", "caller"}
    assert (tool.inputSchema or {}).get("required") == ["id"]
    doc = " ".join((tool.description or "").split())
    assert "one hop" in doc and "never follow" in doc


def test_follow_proxy_tool_end_to_end(memnet_temp):
    from memnet.session import close_session, open_session
    from memnet_mcp.server import follow_proxy, mutate

    a = open_session(map_lines=["SCHEMA TSK ; fields=id goal status"], ttl_minutes=60)
    b = open_session(map_lines=["SCHEMA TSK ; fields=id goal status"], ttl_minutes=60)
    try:
        asyncio.run(
            mutate(
                wire_lines=["CREATE (:TSK {id: 'T1', goal: 'via mcp', status: 'open'})"],
                session=b.session_id,
            )
        )
        asyncio.run(
            mutate(
                wire_lines=[
                    f"CREATE (:PROXY {{id: 'P1', target_session: '{b.session_id}', target: 'T1'}})"
                ],
                session=a.session_id,
            )
        )
        got = json.loads(asyncio.run(follow_proxy(id="P1", session=a.session_id)))
        assert got["exit_code"] == 0, got
        assert "@STAT: follow|ok" in got["stdout"] and "via mcp" in got["stdout"]
        miss = json.loads(asyncio.run(follow_proxy(id="T1", session=b.session_id)))
        assert miss["exit_code"] != 0 and "not_proxy" in json.dumps(miss)
    finally:
        close_session(a.session_id)
        close_session(b.session_id)
