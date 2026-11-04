"""Paging cursor (#247 item 4): find and typed-walk across engine, CLI and MCP.

Contract: a cursor is an opaque token (``c_`` + base32) from ``memnet.paging``.
It carries a position, the store change counter and a query fingerprint under
an HMAC keyed by the session id, so it shows no id and no ordering to compare.
Refusals: ``bad_cursor`` (malformed, forged, foreign session), ``cursor_mismatch``
(query params changed; ``limit`` may change), ``stale_cursor`` (the session was
changed since the page was made). Paging replies are opt-in: a request with
neither ``--cursor`` nor an asked limit (walk) / ``--paged`` (find) is
byte-for-byte what it was before.
"""

from __future__ import annotations

import asyncio
import json
import re

import pytest

from memnet.in_process_engine import run_argv
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_MAP = ["SCHEMA T ; fields=id name", "SCHEMA U ; fields=id name"]
_NICKS = [f"Q{c}" for c in "ABCDEFG"]


def _apply(ss, *stmts):
    return MutateGate(ss).apply(list(stmts), mode="mutate", allow_new_relation=True)


@pytest.fixture
def chain(memnet_temp):
    """QA -LINKS-> QB -> ... -> QG (7 T nodes, 6 edges)."""
    ss = open_session(map_lines=list(_MAP))
    _apply(ss, *[f"CREATE (:T {{id: '{n}', name: 'n{i}'}})" for i, n in enumerate(_NICKS)])
    for a, b in zip(_NICKS, _NICKS[1:], strict=False):
        _apply(ss, f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) CREATE (a)-[:LINKS]->(b)")
    return ss


def _cli(ss, *args: str) -> dict:
    return run_argv(["query", *args, "--session", ss.session_id])


def _walk(ss, *args: str) -> dict:
    return _cli(ss, "typed-walk", "--from", "QA", "--type", "LINKS", "--max-hops", "6", *args)


def _stat(out: str, name: str) -> str:
    m = re.search(rf"^@STAT: {name}\|([^|]*)\|", out, re.M)
    assert m, out
    return m.group(1)


def _paths(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith("@PATH:")]


def _code(r: dict) -> str:
    assert r["exit_code"] != 0, r
    m = re.search(r"@ERR: (\w+)\|", r["stderr"])
    assert m, r
    return m.group(1)


# ----- the token -------------------------------------------------------------------


def test_cursor_is_opaque_and_carries_no_id(chain):
    r = _walk(chain, "--limit", "2")
    tok = _stat(r["stdout"], "walk_cursor")
    assert re.fullmatch(r"c_[a-z2-7]+", tok), tok
    for nick in _NICKS:
        assert nick.lower() not in tok.lower()
    for rec in chain.store._by_hid.values():
        assert rec.hid not in tok


def test_cursor_roundtrip_in_paging_module(chain):
    from memnet import paging

    fp = paging.fingerprint("find", kind="T")
    tok = paging.encode_cursor(chain.session_id, "find", fp, chain.store.change_count, 5)
    assert paging.decode_cursor(chain.session_id, tok, "find", fp, chain.store) == 5


@pytest.mark.parametrize("bad", ["", "nonsense", "c_", "c_!!!", "c_aaaa", "h_abc"])
def test_malformed_cursor_is_bad_cursor(chain, bad):
    r = _walk(chain, "--cursor", bad)
    assert _code(r) == "bad_cursor"
    r = _cli(chain, "find", "--kind", "T", "--limit", "2", "--cursor", bad)
    assert _code(r) == "bad_cursor"


def test_forged_cursor_is_bad_cursor(chain):
    tok = _stat(_walk(chain, "--limit", "2")["stdout"], "walk_cursor")
    flipped = tok[:-1] + ("a" if tok[-1] != "a" else "b")
    assert _code(_walk(chain, "--cursor", flipped)) == "bad_cursor"


def test_cursor_from_another_session_is_bad_cursor(chain):
    tok = _stat(_walk(chain, "--limit", "2")["stdout"], "walk_cursor")
    other = open_session(map_lines=list(_MAP))
    _apply(other, *[f"CREATE (:T {{id: '{n}'}})" for n in _NICKS])
    r = run_argv(
        ["query", "typed-walk", "--from", "QA", "--type", "LINKS", "--cursor", tok]
        + ["--session", other.session_id]
    )
    assert _code(r) == "bad_cursor"


def test_find_cursor_not_valid_for_walk(chain):
    r = _cli(chain, "find", "--kind", "T", "--limit", "2", "--paged")
    tok = _stat(r["stdout"], "find_cursor")
    assert _code(_walk(chain, "--cursor", tok)) == "bad_cursor"


# ----- typed-walk paging -----------------------------------------------------------


def test_walk_pages_cover_all_rows_once_in_order(chain):
    full = _paths(_walk(chain)["stdout"])
    assert len(full) == 6
    got: list[str] = []
    cursor = None
    pages = 0
    while True:
        args = ["--limit", "2"] + (["--cursor", cursor] if cursor else [])
        out = _walk(chain, *args)["stdout"]
        got += _paths(out)
        pages += 1
        cursor = _stat(out, "walk_cursor")
        if cursor == "-":
            assert _stat(out, "walk_truncated") == "none"
            break
        assert _stat(out, "walk_truncated") == "limit"
    assert pages == 3
    assert got == full  # row numbers continue across pages


def test_walk_exact_fit_last_page_has_no_cursor(chain):
    out = _walk(chain, "--limit", "6")["stdout"]
    assert _stat(out, "walk_cursor") == "-"
    assert _stat(out, "walk_truncated") == "none"


def test_walk_limit_may_change_between_pages(chain):
    tok = _stat(_walk(chain, "--limit", "2")["stdout"], "walk_cursor")
    out = _walk(chain, "--limit", "3", "--cursor", tok)["stdout"]
    assert [p.split("|")[0] for p in _paths(out)] == ["@PATH: 3", "@PATH: 4", "@PATH: 5"]


@pytest.mark.parametrize(
    "changed",
    [
        ["--type", "OTHER"],
        ["--dir", "in"],
        ["--max-hops", "5"],
        ["--min-hops", "2"],
        ["--where", "n.name = 'n3'"],
        ["--from", "QB"],
    ],
)
def test_walk_changed_params_with_cursor_is_cursor_mismatch(chain, changed):
    tok = _stat(_walk(chain, "--limit", "2")["stdout"], "walk_cursor")
    base = {
        "--from": "QA",
        "--type": "LINKS",
        "--max-hops": "6",
    }
    base.update(dict(zip(changed[::2], changed[1::2], strict=True)))
    argv = [x for kv in base.items() for x in kv]
    r = run_argv(["query", "typed-walk", *argv, "--cursor", tok, "--session", chain.session_id])
    assert _code(r) == "cursor_mismatch"


def test_walk_cursor_stale_after_change(chain):
    tok = _stat(_walk(chain, "--limit", "2")["stdout"], "walk_cursor")
    _apply(chain, "CREATE (:U {id: 'QZ', name: 'late'})")
    r = _walk(chain, "--cursor", tok)
    assert _code(r) == "stale_cursor"


def test_reads_do_not_stale_a_cursor(chain):
    tok = _stat(_walk(chain, "--limit", "2")["stdout"], "walk_cursor")
    _walk(chain)
    _cli(chain, "find", "--kind", "T", "--limit", "2")
    _cli(chain, "pin-map", "--cue", "QA")
    out = _walk(chain, "--cursor", tok)["stdout"]
    assert _stat(out, "walk_rows") == "4"


def test_walk_cursor_after_byte_truncation_resumes(chain, monkeypatch):
    from memnet import typed_walk as tw

    full = _paths(_walk(chain)["stdout"])
    monkeypatch.setattr(tw, "WALK_MAX_REPLY_BYTES", 520)
    got: list[str] = []
    cursor = None
    for _ in range(10):
        args = ["--limit", "6"] + (["--cursor", cursor] if cursor else [])
        out = _walk(chain, *args)["stdout"]
        got += _paths(out)
        cursor = _stat(out, "walk_cursor")
        if cursor == "-":
            break
        assert _stat(out, "walk_truncated") == "bytes"
    assert cursor == "-"
    assert got == full


def test_walk_budget_truncation_gives_no_cursor(chain, monkeypatch):
    from memnet import typed_walk as tw

    monkeypatch.setattr(tw, "WALK_MAX_EXAMINED", 3)
    out = _walk(chain, "--limit", "6")["stdout"]
    assert _stat(out, "walk_truncated") == "budget"
    assert _stat(out, "walk_cursor") == "-"


def test_walk_json_handles_carries_cursor(chain):
    r = _walk(chain, "--limit", "2", "--json-handles")
    line = next(ln for ln in r["stdout"].splitlines() if ln.startswith("@WALKJSON: "))
    got = json.loads(line[len("@WALKJSON: ") :])
    tok = got["stats"]["cursor"]
    assert re.fullmatch(r"c_[a-z2-7]+", tok)
    nxt = _walk(chain, "--limit", "2", "--json-handles", "--cursor", tok)
    line2 = next(ln for ln in nxt["stdout"].splitlines() if ln.startswith("@WALKJSON: "))
    got2 = json.loads(line2[len("@WALKJSON: ") :])
    assert [r["row"] for r in got2["rows"]] == [3, 4]


# ----- find paging -----------------------------------------------------------------


def _find(ss, *args: str) -> dict:
    return _cli(ss, "find", "--kind", "T", *args)


def _rows(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith("(:")]


def test_find_pages_cover_all_hits_once_in_order(chain):
    full = _rows(_find(chain, "--limit", "7")["stdout"])
    assert len(full) == 7
    got: list[str] = []
    cursor = None
    pages = 0
    while True:
        args = ["--limit", "3", "--paged"] + (["--cursor", cursor] if cursor else [])
        out = _find(chain, *args)["stdout"]
        assert "## CueConflict |Q|=7" in out
        got += _rows(out)
        pages += 1
        cursor = _stat(out, "find_cursor")
        if cursor == "-":
            break
    assert pages == 3
    assert got == full


def test_find_cursor_implies_paged_and_limit_may_change(chain):
    tok = _stat(_find(chain, "--limit", "3", "--paged")["stdout"], "find_cursor")
    out = _find(chain, "--limit", "2", "--cursor", tok)["stdout"]
    assert len(_rows(out)) == 2
    assert _stat(out, "find_cursor") != "-"


@pytest.mark.parametrize(
    "extra",
    [["--kind", "U"], ["--locator", "name=n1"], ["--keyword", "n1"]],
)
def test_find_changed_params_with_cursor_is_cursor_mismatch(chain, extra):
    tok = _stat(_find(chain, "--limit", "3", "--paged")["stdout"], "find_cursor")
    argv = ["find", "--limit", "3", "--cursor", tok] + extra
    if "--kind" not in extra:
        argv += ["--kind", "T"]
    assert _code(_cli(chain, *argv)) == "cursor_mismatch"


def test_find_cursor_stale_after_change(chain):
    tok = _stat(_find(chain, "--limit", "3", "--paged")["stdout"], "find_cursor")
    _apply(chain, "CREATE (:T {id: 'QZ', name: 'late'})")
    assert _code(_find(chain, "--limit", "3", "--cursor", tok)) == "stale_cursor"


def test_find_single_hit_has_no_cursor_line(chain):
    r = _cli(chain, "find", "--locator", "id=QC", "--limit", "3", "--paged")
    assert _stat(r["stdout"], "find_cursor") == "-"
    assert _rows(r["stdout"]) == ["(:T {name: 'n2'})"]


# ----- back-compat: bytes unchanged when paging is not asked -----------------------


def test_backcompat_find_bytes_unchanged(chain):
    r = _cli(chain, "find", "--kind", "T", "--limit", "3")
    assert r["stdout"] == (
        "## CueConflict |Q|=7\n(:T {name: 'n0'})\n(:T {name: 'n1'})\n(:T {name: 'n2'})\n"
    )
    r = _cli(chain, "find", "--locator", "id=QC", "--limit", "3")
    assert r["stdout"] == "(:T {name: 'n2'})\n"


def test_backcompat_walk_bytes_unchanged_without_limit(chain):
    out = _cli(chain, "typed-walk", "--from", "QA", "--type", "LINKS", "--max-hops", "3")["stdout"]
    assert out == (
        "@WALK: type=links|dir=out|hops=1..3|limit=50\n"
        "@PATH: 1|1|(:T {id: 'QA'})-[:links {id: 'E1'}]->(:T {id: 'QB', name: 'n1'})\n"
        "@PATH: 2|2|(:T {id: 'QA'})-[:links {id: 'E1'}]->(:T {id: 'QB'})"
        "-[:links {id: 'E2'}]->(:T {id: 'QC', name: 'n2'})\n"
        "@PATH: 3|3|(:T {id: 'QA'})-[:links {id: 'E1'}]->(:T {id: 'QB'})"
        "-[:links {id: 'E2'}]->(:T {id: 'QC'})-[:links {id: 'E3'}]->(:T {id: 'QD', name: 'n3'})\n"
        "@STAT: walk_rows|3|50\n@STAT: walk_truncated|none|-\n@STAT: walk_cursor|-|-\n"
    )


def test_backcompat_walk_json_has_no_cursor_without_limit(chain):
    r = _cli(chain, "typed-walk", "--from", "QA", "--type", "LINKS", "--json-handles")
    assert r["stdout"].rstrip().endswith('"stats":{"rows":1,"truncated":"none","cursor":null}}')


# ----- MCP -------------------------------------------------------------------------


def _mcp_walk(ss, **kw) -> dict:
    from memnet_mcp.server import typed_walk

    raw = asyncio.run(typed_walk(session=ss.session_id, **kw))
    for nick in _NICKS:
        assert nick not in raw
    return json.loads(raw)


def test_mcp_typed_walk_pages_with_next_cursor(chain):
    kw = {"start": "QA", "edge_type": "LINKS", "max_hops": 6}
    rows: list[int] = []
    got = _mcp_walk(chain, limit=4, **kw)
    assert got["ok"] is True
    pages = 1
    rows += [r["row"] for r in got["rows"]]
    assert got["next_cursor"] == got["stats"]["cursor"]
    while got.get("next_cursor"):
        got = _mcp_walk(chain, limit=4, cursor=got["next_cursor"], **kw)
        pages += 1
        rows += [r["row"] for r in got["rows"]]
    assert rows == [1, 2, 3, 4, 5, 6]
    assert pages == 2
    assert got.get("next_cursor") is None


def test_mcp_typed_walk_without_limit_or_cursor_is_unchanged(chain):
    got = _mcp_walk(chain, start="QA", edge_type="LINKS", max_hops=3)
    assert "next_cursor" not in got
    assert got["stats"] == {"rows": 3, "truncated": "none", "cursor": None}
    assert list(got) == ["ok", "exit_code", "session_id", "errors", "walk", "rows", "stats"]


def test_mcp_typed_walk_errors_use_codes(chain):
    first = _mcp_walk(chain, start="QA", edge_type="LINKS", max_hops=6, limit=2)
    bad = _mcp_walk(chain, start="QA", edge_type="LINKS", max_hops=6, cursor="junk")
    assert bad["ok"] is False and bad["error"]["code"] == "bad_cursor"
    mism = _mcp_walk(chain, start="QA", edge_type="LINKS", max_hops=5, cursor=first["next_cursor"])
    assert mism["error"]["code"] == "cursor_mismatch"
    _apply(chain, "CREATE (:U {id: 'QZ'})")
    stale = _mcp_walk(chain, start="QA", edge_type="LINKS", max_hops=6, cursor=first["next_cursor"])
    assert stale["error"]["code"] == "stale_cursor"


def test_mcp_find_pages(chain):
    from memnet_mcp.server import find

    def call(**kw) -> dict:
        return json.loads(asyncio.run(find(session=chain.session_id, kind="T", **kw)))

    first = call(limit=3, paged=True)
    out = first["stdout"] if "stdout" in first else json.dumps(first)
    tok = re.search(r"@STAT: find_cursor\|(c_[a-z2-7]+)\|", out).group(1)
    second = call(limit=3, cursor=tok)
    assert "find_cursor" in json.dumps(second)
    plain = call(limit=3)
    assert "find_cursor" not in json.dumps(plain)
