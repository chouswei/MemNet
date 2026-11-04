"""MN-REQ-14.7 slice: typed walks over MCP, handles only.

The ``typed_walk`` MCP tool routes ``query typed-walk --json-handles`` and
returns parsed walk JSON. No real id (nickname, hid, edge id) may appear in the
reply string, error text included. Handles are session-keyed: a foreign or
deleted node's handle is refused ``stale_handle``. An edge type no edge in the
session has is refused ``unknown_relation`` (engine, so CLI and MCP agree).
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest

from memnet.in_process_engine import run_argv
from memnet.mutate_gate import MutateGate
from memnet.session import close_session, open_session

_MAP = ["SCHEMA T ; fields=id name ref"]
_NICKS = ("QxAlpha", "QxBravo", "QxCharlie", "QxDelta")
_EDGE_IDS = ("QxEdge1", "QxEdge2", "QxEdge3")


def _apply(ss, *stmts):
    return MutateGate(ss).apply(list(stmts), mode="mutate", allow_new_relation=True)


def _chain(ss) -> None:
    """QxAlpha -LINKS-> QxBravo -LINKS-> QxCharlie -LINKS-> QxDelta (edge ids set).

    QxCharlie's ``ref`` holds QxAlpha's nickname and QxDelta's ``ref`` mentions
    it in text: both are kept out of props defensively.
    """
    _apply(
        ss,
        "CREATE (:T {id: 'QxAlpha', name: 'first'})",
        "CREATE (:T {id: 'QxBravo', name: 'second'})",
        "CREATE (:T {id: 'QxCharlie', name: 'third', ref: 'QxAlpha'})",
        "CREATE (:T {id: 'QxDelta', name: 'fourth', ref: 'after QxAlpha'})",
    )
    for (a, b), eid in zip(zip(_NICKS, _NICKS[1:], strict=False), _EDGE_IDS, strict=True):
        _apply(
            ss,
            f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) CREATE (a)-[:LINKS {{id: '{eid}'}}]->(b)",
        )


@pytest.fixture
def chain(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _chain(ss)
    return ss


def _real_ids(ss) -> tuple[set[str], set[str]]:
    recs = list(ss.store._by_hid.values())
    nicks = {r.fields["id"] for r in recs if r.fields.get("id")}
    return nicks, {r.hid for r in recs}


def _assert_no_ids(ss, reply: str) -> None:
    nicks, hids = _real_ids(ss)
    for nick in nicks:
        assert nick not in reply, (nick, reply)
    for hid in hids:
        # a handle is "h_" + base32, so "h_el12..." is not a hid
        assert not re.search(rf"(?<!h){re.escape(hid)}(?!\d)", reply), (hid, reply)


def _tool(**kw) -> str:
    from memnet_mcp.server import typed_walk

    return asyncio.run(typed_walk(**kw))


def _call(ss, **kw) -> dict:
    raw = _tool(session=ss.session_id, **kw)
    _assert_no_ids(ss, raw)
    return json.loads(raw)


def _ok(ss, **kw) -> dict:
    got = _call(ss, **kw)
    assert got["ok"] is True, got
    return got


def _refused(ss, code: str, **kw) -> dict:
    got = _call(ss, **kw)
    assert got["ok"] is False, got
    assert got["error"]["code"] == code, got
    assert "rows" not in got
    return got


def _end(row: dict) -> dict:
    return row["steps"][-1]["node"]


def _cli(ss, *args: str) -> dict:
    return run_argv(["query", "typed-walk", *args, "--session", ss.session_id])


# ----- surface ------------------------------------------------------------------


def test_tool_listed_and_callable_through_fastmcp(chain):
    from memnet_mcp.server import mcp

    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "typed_walk" in names
    out = asyncio.run(
        mcp.call_tool(
            "typed_walk",
            {"start": "QxAlpha", "edge_type": "LINKS", "session": chain.session_id},
        )
    )
    content = out[0] if isinstance(out, tuple) else out
    raw = content[0].text
    _assert_no_ids(chain, raw)
    got = json.loads(raw)
    assert got["ok"] is True
    assert got["stats"] == {"rows": 1, "truncated": "none", "cursor": None}


def test_rows_carry_handles_and_no_real_id(chain):
    got = _ok(chain, start="QxAlpha", edge_type="LINKS", max_hops=3)
    assert got["walk"] == {"type": "links", "dir": "out", "hops": [1, 3], "limit": 50}
    assert [r["row"] for r in got["rows"]] == [1, 2, 3]
    assert [r["hops"] for r in got["rows"]] == [1, 2, 3]
    assert [_end(r)["props"]["name"] for r in got["rows"]] == ["second", "third", "fourth"]
    for row in got["rows"]:
        assert row["start"]["kind"] == "T"
        assert row["start"]["handle"].startswith("h_")
        assert "props" not in row["start"]
        for step in row["steps"][:-1]:
            assert "props" not in step["node"]
        for step in row["steps"]:
            assert step["edge"]["type"] == "links"
            assert step["edge"]["dir"] == "out"
            assert re.fullmatch(r"h_[a-z2-7]{26}", step["edge"]["handle"])
            assert re.fullmatch(r"h_[a-z2-7]{26}", step["node"]["handle"])
    # the same start in every row; distinct nodes and edges get distinct handles
    assert len({r["start"]["handle"] for r in got["rows"]}) == 1
    deep = got["rows"][2]["steps"]
    assert len({s["node"]["handle"] for s in deep} | {s["edge"]["handle"] for s in deep}) == 6
    # a value that is a real id is dropped; an id inside text is masked
    assert _end(got["rows"][1])["props"] == {"name": "third"}
    assert _end(got["rows"][2])["props"] == {"name": "fourth", "ref": "after <id>"}


def test_direction_in_reports_step_dir(chain):
    got = _ok(chain, start="QxDelta", edge_type="LINKS", direction="in", max_hops=2)
    assert [_end(r)["props"]["name"] for r in got["rows"]] == ["third", "second"]
    assert {s["edge"]["dir"] for r in got["rows"] for s in r["steps"]} == {"in"}


def test_end_handle_continues_the_walk(chain):
    first = _ok(chain, start="QxAlpha", edge_type="LINKS")
    hop1 = _end(first["rows"][0])["handle"]
    second = _ok(chain, start=hop1, edge_type="LINKS")
    assert second["rows"][0]["start"]["handle"] == hop1
    assert _end(second["rows"][0])["props"] == {"name": "third"}  # ref dropped
    third = _ok(chain, start=_end(second["rows"][0])["handle"], edge_type="LINKS")
    assert _end(third["rows"][0])["props"]["name"] == "fourth"
    # matches the multi-hop walk from the start
    deep = _ok(chain, start="QxAlpha", edge_type="LINKS", max_hops=3)
    assert [_end(r)["handle"] for r in deep["rows"]] == [
        hop1,
        _end(second["rows"][0])["handle"],
        _end(third["rows"][0])["handle"],
    ]


# ----- stale handles ---------------------------------------------------------------


def test_handle_from_other_session_refused(chain):
    other = open_session(map_lines=list(_MAP))
    _chain(other)  # same nicknames: a handle is keyed by session, not by name only
    hop1 = _end(_ok(chain, start="QxAlpha", edge_type="LINKS")["rows"][0])["handle"]
    got = _refused(other, "stale_handle", start=hop1, edge_type="LINKS")
    assert hop1 in got["error"]["message"]
    # and the handle still works where it was minted
    _ok(chain, start=hop1, edge_type="LINKS")


def test_deleted_node_handle_refused(chain):
    hop1 = _end(_ok(chain, start="QxAlpha", edge_type="LINKS")["rows"][0])["handle"]
    _apply(chain, "MATCH (n {id: 'QxBravo'}) DETACH DELETE n")
    _refused(chain, "stale_handle", start=hop1, edge_type="LINKS")
    nicks, _ = _real_ids(chain)
    assert "QxBravo" not in nicks


def test_garbage_handle_refused(chain):
    _refused(chain, "stale_handle", start="h_notahandle", edge_type="LINKS")


def test_handle_stable_across_save_and_load(chain, tmp_path: Path):
    sid = chain.session_id
    before = _ok(chain, start="QxAlpha", edge_type="LINKS", max_hops=3)
    hop1 = _end(before["rows"][0])["handle"]
    path = tmp_path / "walk.snap"
    saved = run_argv(["session", "save", "--file", str(path), "--session", sid])
    assert saved["exit_code"] == 0, saved["stderr"]
    close_session(sid)
    loaded = run_argv(["session", "load", "--file", str(path), "--keep-id"])
    assert loaded["exit_code"] == 0, loaded["stderr"]
    from memnet.session import get_session

    ss = get_session(sid)
    after = _ok(ss, start="QxAlpha", edge_type="LINKS", max_hops=3)
    assert after["rows"] == before["rows"]
    cont = _ok(ss, start=hop1, edge_type="LINKS")
    assert _end(cont["rows"][0])["props"] == {"name": "third"}


# ----- unknown relation -----------------------------------------------------------------


def test_unknown_relation_refused_cli_and_mcp(chain):
    for args in (("--from", "QxAlpha"), ("--json-handles", "--from", "QxAlpha")):
        out = _cli(chain, *args, "--type", "NEVER_USED")
        assert out["exit_code"] != 0
        assert "@ERR: unknown_relation|" in out["stderr"], out
        assert "@PATH" not in out["stdout"] and "@WALKJSON" not in out["stdout"]
    _refused(chain, "unknown_relation", start="QxAlpha", edge_type="NEVER_USED")
    # checked after folding: every spelling of the present type still walks
    for spelling in ("LINKS", "links", "Links"):
        assert _ok(chain, start="QxAlpha", edge_type=spelling)["stats"]["rows"] == 1


def test_unknown_relation_after_last_edge_deleted(chain):
    _apply(chain, "MATCH (a {id: 'QxAlpha'})-[r:LINKS]->(b {id: 'QxBravo'}) DELETE r")
    assert _ok(chain, start="QxBravo", edge_type="LINKS")["stats"]["rows"] == 1
    for a, b in (("QxBravo", "QxCharlie"), ("QxCharlie", "QxDelta")):
        _apply(chain, f"MATCH (a {{id: '{a}'}})-[r:LINKS]->(b {{id: '{b}'}}) DELETE r")
    _refused(chain, "unknown_relation", start="QxAlpha", edge_type="LINKS")


# ----- errors never echo ids ---------------------------------------------------------------


def test_error_text_scrubbed(chain):
    _apply(
        chain, "CREATE (:T {id: 'QxTwin', name: 'one'})", "CREATE (:T {id: 'QxTwin', name: 'two'})"
    )
    cli = _cli(chain, "--from", "QxTwin", "--type", "LINKS")
    assert "@ERR: cue_conflict|" in cli["stderr"] and "QxTwin" in cli["stderr"]
    cli = _cli(chain, "--json-handles", "--from", "QxTwin", "--type", "LINKS")
    assert "@ERR: cue_conflict|" in cli["stderr"] and "QxTwin" not in cli["stderr"]
    _refused(chain, "cue_conflict", start="QxTwin", edge_type="LINKS")
    got = _refused(chain, "not_found", start="QxNobody", edge_type="LINKS")
    assert "QxNobody" not in json.dumps(got)


# ----- limits (same as the CLI) -----------------------------------------------------------------


@pytest.fixture
def star(memnet_temp):
    """Hub -LINKS-> 60 leaves."""
    ss = open_session(map_lines=list(_MAP))
    _apply(ss, "CREATE (:T {id: 'QxHub', name: 'hub'})")
    _apply(ss, *(f"CREATE (:T {{id: 'QxLeaf{i:02d}', name: 'leaf{i}'}})" for i in range(60)))
    _apply(
        ss,
        *(
            f"MATCH (a {{id: 'QxHub'}}), (b {{id: 'QxLeaf{i:02d}'}}) CREATE (a)-[:LINKS]->(b)"
            for i in range(60)
        ),
    )
    return ss


def test_default_limit_50(star):
    got = _ok(star, start="QxHub", edge_type="LINKS")
    assert got["walk"]["limit"] == 50
    assert got["stats"] == {"rows": 50, "truncated": "limit", "cursor": None}
    assert len(got["rows"]) == 50


@pytest.mark.parametrize("limit", [0, 501])
def test_limit_out_of_range_refused_like_cli(star, limit):
    cli = _cli(star, "--json-handles", "--from", "QxHub", "--type", "LINKS", "--limit", str(limit))
    assert "@ERR: limit_out_of_range|" in cli["stderr"]
    _refused(star, "limit_out_of_range", start="QxHub", edge_type="LINKS", limit=limit)


def test_limit_500_accepted(star):
    got = _ok(star, start="QxHub", edge_type="LINKS", limit=500)
    assert got["stats"] == {"rows": 60, "truncated": "none", "cursor": None}


def test_budget_truncation_in_stats(star, monkeypatch):
    from memnet import typed_walk as tw

    monkeypatch.setattr(tw, "WALK_MAX_EXAMINED", 7)
    got = _ok(star, start="QxHub", edge_type="LINKS")
    assert got["stats"] == {"rows": 7, "truncated": "budget", "cursor": None}


def test_bytes_truncation_in_stats(star, monkeypatch):
    from memnet import typed_walk as tw

    full = _ok(star, start="QxHub", edge_type="LINKS", limit=60)
    cap = 2_000
    monkeypatch.setattr(tw, "WALK_MAX_REPLY_BYTES", cap)
    cli = _cli(star, "--json-handles", "--from", "QxHub", "--type", "LINKS", "--limit", "60")
    line = cli["stdout"].splitlines()[0]
    assert len(line.encode("utf-8")) + 1 <= cap
    got = _ok(star, start="QxHub", edge_type="LINKS", limit=60)
    n = got["stats"]["rows"]
    assert 0 < n < 60
    assert got["stats"]["truncated"] == "bytes"
    # trailing rows dropped, the kept ones unchanged
    assert got["rows"] == full["rows"][:n]


def test_default_text_output_unchanged_without_flag(chain):
    out = _cli(chain, "--from", "QxAlpha", "--type", "LINKS")
    assert out["exit_code"] == 0, out["stderr"]
    lines = out["stdout"].splitlines()
    assert lines[0].startswith("@WALK: type=links|")
    assert lines[1].startswith("@PATH: 1|1|") and "QxBravo" in lines[1]
    assert not any(ln.startswith("@WALKJSON") for ln in lines)
