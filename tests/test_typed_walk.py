"""MN-REQ-14.3 / issue #247 items 1-3: typed directed walks (CLI verb + engine).

Red-first for symphony typed-walks (node P-walk). Contract: /tmp/s247/score.md
section 1, D1-D9. Pinned interface (lands in M2):

- ``memnet.typed_walk.typed_walk(store, *, start, relation, direction="out",
  min_hops=1, max_hops=1, where=None, limit=50) -> WalkResult`` and
  ``emit_walk(result, *, max_bytes=None) -> list[str]``; module constants
  ``WALK_MAX_HOPS``, ``WALK_MAX_LIMIT``, ``WALK_MAX_EXAMINED`` and
  ``WALK_MAX_REPLY_BYTES`` are read at call time.
- CLI ``memnet query typed-walk --from <id> --type <T> [--dir out|in|both]
  [--min-hops N] [--max-hops N] [--where P] [--limit N] [--session S]``.
- Start by nickname through the id index (EDG rows excluded); hids are never
  accepted or emitted. BFS, each node reached once, the start never a row.
- Order: hop order, then parents' BFS order, then the edge first-insert
  sequence. Never id value, hid or property value.
- Reply (D9): ``@WALK`` header, one ``@PATH: <row>|<hops>|<shaped path>`` per
  row, then ``walk_rows``, ``walk_truncated`` and ``walk_cursor`` stats.

Path-line spacing: the END node must be exactly ``gql.emit_node_shaped(tag,
nick, fields)``; start, intermediate and edge segments are compared with
whitespace removed (the score writes them as ``{id:'A1'}``).

New names are looked up inside test bodies so collection never fails on 4b8ed16.
"""

from __future__ import annotations

import asyncio
import importlib
import re
from pathlib import Path

import pytest

from memnet.exceptions import MemNetError
from memnet.gql import emit_node_shaped
from memnet.in_process_engine import run_argv
from memnet.mutate_gate import MutateGate
from memnet.session import close_session, open_session

_MAP = [
    "SCHEMA ASK ; fields=id title",
    "SCHEMA ROW ; fields=id toBot rowRev note",
    "SCHEMA T ; fields=id name rank",
]
_HID_RE = re.compile(r"_el\d+")


def _tw():
    try:
        return importlib.import_module("memnet.typed_walk")
    except ModuleNotFoundError as exc:  # red on 4b8ed16: the feature is missing
        pytest.fail(f"missing feature: memnet.typed_walk ({exc})")


def _apply(ss, *stmts, mode="mutate"):
    return MutateGate(ss).apply(list(stmts), mode=mode, allow_new_relation=True)


def _node(ss, nick: str):
    hits = [r for r in ss.store.match_nickname(nick) if r.tag != "EDG"]
    assert len(hits) == 1, nick
    return hits[0]


def _edge(ss, a: str, rel: str, b: str, eid: str | None = None) -> None:
    props = f" {{id: '{eid}'}}" if eid else ""
    _apply(ss, f"MATCH (a {{id: '{a}'}}), (b {{id: '{b}'}}) CREATE (a)-[:{rel}{props}]->(b)")


def _nodes(ss, *nicks: str, tag: str = "T") -> None:
    _apply(ss, *(f"CREATE (:{tag} {{id: '{n}', name: 'n_{n}'}})" for n in nicks))


def _walk(ss, *args: str) -> dict:
    return run_argv(["query", "typed-walk", *args, "--session", ss.session_id])


def _ok(ss, *args: str) -> list[str]:
    out = _walk(ss, *args)
    assert out["exit_code"] == 0, out["stderr"]
    assert "No such command" not in out["stderr"]
    return out["stdout"].splitlines()


def _paths(lines: list[str]) -> list[list[str]]:
    return [ln[len("@PATH: ") :].split("|", 2) for ln in lines if ln.startswith("@PATH: ")]


def _end_ids(lines: list[str]) -> list[str]:
    """Nickname of each row's end node, in reply order ('' when it has none)."""
    out = []
    for _row, _hops, path in _paths(lines):
        end = path[path.rfind("(") :]
        m = re.search(r"id: ?'([^']*)'", end)
        out.append(m.group(1) if m else "")
    return out


def _stat(lines: list[str], name: str) -> list[str]:
    hits = [ln for ln in lines if ln.startswith(f"@STAT: {name}|")]
    assert len(hits) == 1, (name, lines)
    return hits[0][len("@STAT: ") :].split("|")


def _refused(ss, code: str, *args: str) -> str:
    out = _walk(ss, *args)
    assert "No such command" not in out["stderr"], "missing feature: query typed-walk"
    assert out["exit_code"] != 0, (args, out)
    assert f"@ERR: {code}|" in out["stderr"], (args, out["stderr"])
    assert "@PATH" not in out["stdout"]
    return out["stderr"]


def _engine_refused(store, code: str, **kw) -> MemNetError:
    tw = _tw()
    with pytest.raises(MemNetError) as ei:
        tw.typed_walk(store, **kw)
    assert ei.value.code == code, (kw, ei.value.code, ei.value.message)
    return ei.value


def _end_nicks(result) -> list[str]:
    return [p.end.fields.get("id", "") for p in result.paths]


def _squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


@pytest.fixture
def board(memnet_temp):
    """A1 (ASK); R1, R2 point at A1 by PART_OF; R3 has no nickname; A1 -IN_SESSION-> S1."""
    ss = open_session(map_lines=list(_MAP))
    _apply(
        ss,
        "CREATE (:ASK {id: 'A1', title: 'claim'})",
        "CREATE (:ASK {id: 'S1', title: 'session'})",
        "CREATE (:ROW {id: 'R1', toBot: 'x', rowRev: '000124', note: 'first'})",
        "CREATE (:ROW {id: 'R2', toBot: 'y', rowRev: '000125', note: 'second'})",
        "CREATE (:ROW {toBot: 'z', rowRev: '000126', note: 'anon'})",
    )
    _edge(ss, "R1", "PART_OF", "A1", "E_r1")
    _edge(ss, "R2", "PART_OF", "A1", "E_r2")
    _apply(
        ss,
        "MATCH (a {note: 'anon'}), (b {id: 'A1'}) CREATE (a)-[:PART_OF {id: 'E_r3'}]->(b)",
    )
    _edge(ss, "A1", "IN_SESSION", "S1", "E_s1")
    return ss


# ----- one hop out / in / both -----------------------------------------------


def test_one_hop_in_far_nodes_with_id_and_every_property(board):
    lines = _ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "in")
    assert _end_ids(lines) == ["R1", "R2", ""]
    anon = next(r for r in board.store.list_records("ROW") if not r.fields.get("id"))
    for (_row, hops, path), nick in zip(_paths(lines), ("R1", "R2", ""), strict=True):
        assert hops == "1"
        rec = anon if not nick else _node(board, nick)
        assert path.endswith(emit_node_shaped(rec.tag, nick, dict(rec.fields))), path
        # every stored property of the end node is on the row
        for key, val in rec.fields.items():
            if key not in ("recycle",) and val:
                assert f"{key}:" in path, (key, path)
    assert "A1" not in _end_ids(lines)


def test_one_hop_out_and_engine_result(board):
    tw = _tw()
    lines = _ok(board, "--from", "R1", "--type", "PART_OF")
    assert _end_ids(lines) == ["A1"]
    res = tw.typed_walk(board.store, start="R1", relation="PART_OF")
    assert res.relation == "partOf"
    assert res.direction == "out"
    assert (res.min_hops, res.max_hops, res.limit) == (1, 1, 50)
    assert _end_nicks(res) == ["A1"]
    (path,) = res.paths
    assert path.start.fields["id"] == "R1"
    assert len(path.steps) == 1
    step = path.steps[0]
    assert step.forward is True
    assert step.edge.fields["id"] == "E_r1"
    assert step.node is path.end
    assert path.end.fields["title"] == "claim"
    assert res.truncated is None
    assert res.cursor is None


def test_one_hop_in_backward_step_flag(board):
    tw = _tw()
    res = tw.typed_walk(board.store, start="A1", relation="PART_OF", direction="in")
    assert _end_nicks(res) == ["R1", "R2", ""]
    assert all(p.steps[0].forward is False for p in res.paths)
    assert [p.steps[0].edge.fields["id"] for p in res.paths] == ["E_r1", "E_r2", "E_r3"]


def test_one_hop_both_merges_by_edge_insert_order(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _nodes(ss, "X", "I1", "O1", "I2", "O2")
    _edge(ss, "X", "LINKS", "O1", "e4")
    _edge(ss, "I1", "LINKS", "X", "e3")
    _edge(ss, "X", "LINKS", "O2", "e2")
    _edge(ss, "I2", "LINKS", "X", "e1")
    assert _end_ids(_ok(ss, "--from", "X", "--type", "LINKS", "--dir", "both")) == [
        "O1",
        "I1",
        "O2",
        "I2",
    ]
    assert _end_ids(_ok(ss, "--from", "X", "--type", "LINKS", "--dir", "out")) == ["O1", "O2"]
    assert _end_ids(_ok(ss, "--from", "X", "--type", "LINKS", "--dir", "in")) == ["I1", "I2"]
    tw = _tw()
    res = tw.typed_walk(ss.store, start="X", relation="links", direction="both")
    assert [p.steps[0].forward for p in res.paths] == [True, False, True, False]


def test_default_direction_is_out(board):
    assert _ok(board, "--from", "A1", "--type", "PART_OF") == _ok(
        board, "--from", "A1", "--type", "PART_OF", "--dir", "out"
    )
    assert _end_ids(_ok(board, "--from", "A1", "--type", "PART_OF")) == []


def test_other_types_not_followed(board):
    assert _end_ids(_ok(board, "--from", "A1", "--type", "IN_SESSION")) == ["S1"]
    assert _end_ids(_ok(board, "--from", "A1", "--type", "IN_SESSION", "--dir", "both")) == ["S1"]
    assert _end_ids(_ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "both")) == [
        "R1",
        "R2",
        "",
    ]


@pytest.mark.parametrize("direction", ["out", "in", "both"])
def test_self_loop_gives_no_row(memnet_temp, direction):
    ss = open_session(map_lines=list(_MAP))
    _nodes(ss, "X", "Y")
    _edge(ss, "X", "LINKS", "X", "loop")
    _edge(ss, "X", "LINKS", "Y", "xy")
    _edge(ss, "Y", "LINKS", "X", "yx")
    lines = _ok(ss, "--from", "X", "--type", "LINKS", "--dir", direction, "--max-hops", "3")
    assert "X" not in _end_ids(lines)
    assert _end_ids(lines) == ["Y"]


def test_parallel_edges_one_row_first_edge(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _nodes(ss, "X", "P")
    _edge(ss, "X", "LINKS", "P", "first")
    _edge(ss, "X", "LINKS", "P", "second")
    _edge(ss, "P", "LINKS", "X", "back")
    for direction in ("out", "both"):
        lines = _ok(ss, "--from", "X", "--type", "LINKS", "--dir", direction)
        assert _end_ids(lines) == ["P"], direction
        assert "first" in lines[1] and "second" not in lines[1] and "back" not in lines[1]
    tw = _tw()
    res = tw.typed_walk(ss.store, start="X", relation="LINKS", direction="both")
    assert [p.steps[0].edge.fields["id"] for p in res.paths] == ["first"]


def test_edge_to_missing_endpoint_is_skipped(board):
    tw = _tw()
    r2 = _node(board, "R2")
    board.store.delete(r2.hid)  # raw delete: E_r2 now dangles
    res = tw.typed_walk(board.store, start="A1", relation="PART_OF", direction="in")
    assert _end_nicks(res) == ["R1", ""]
    assert res.examined >= 3


# ----- start lookup -----------------------------------------------------------


def test_start_not_found(board):
    err = _refused(board, "not_found", "--from", "NOPE", "--type", "PART_OF")
    assert "@ERR: not_found|walk start NOPE not found" in err
    _engine_refused(board.store, "not_found", start="NOPE", relation="PART_OF")


def test_start_cue_conflict(board):
    _apply(board, "CREATE (:T {id: 'R1', name: 'twin'})")
    err = _refused(board, "cue_conflict", "--from", "R1", "--type", "PART_OF")
    assert "@ERR: cue_conflict|walk start R1 matches 2 nodes" in err
    _engine_refused(board.store, "cue_conflict", start="R1", relation="PART_OF")


def test_start_no_anchor(board):
    err = _refused(board, "no_anchor", "--from", "", "--type", "PART_OF")
    assert "@ERR: no_anchor|query typed-walk requires --from" in err
    _engine_refused(board.store, "no_anchor", start="", relation="PART_OF")


def test_start_edge_nickname_is_not_a_start(board):
    _refused(board, "not_found", "--from", "E_r1", "--type", "PART_OF")


def test_start_hid_is_not_accepted(board):
    anon = next(r for r in board.store.list_records("ROW") if not r.fields.get("id"))
    _refused(board, "not_found", "--from", anon.hid, "--type", "PART_OF")
    _engine_refused(board.store, "not_found", start=anon.hid, relation="PART_OF")


def test_start_uses_id_index(board, monkeypatch):
    tw = _tw()
    store = board.store
    seen: list[str] = []
    real = store.match_nickname

    def spy(nick, *a, **kw):
        seen.append(nick)
        return real(nick, *a, **kw)

    monkeypatch.setattr(store, "match_nickname", spy)
    tw.typed_walk(store, start="A1", relation="PART_OF", direction="in")
    assert "A1" in seen


def test_no_hid_in_output_and_anon_node_shows_no_id(board):
    _edge(board, "S1", "PART_OF", "R1", "E_x")
    lines = _ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "both", "--max-hops", "3")
    text = "\n".join(lines)
    assert not _HID_RE.search(text), text
    for rec in [*board.store.list_records("ROW"), *board.store.list_records("ASK")]:
        assert rec.hid not in text
    anon_rows = [p for p in _paths(lines) if "anon" in p[2]]
    assert len(anon_rows) == 1
    end = anon_rows[0][2][anon_rows[0][2].rfind("(") :]
    assert "id:" not in end.replace(" ", ""), end


# ----- spelling (D2) ------------------------------------------------------------


def test_spelling_folds(board):
    want = _ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "in")
    assert _end_ids(want) == ["R1", "R2", ""]
    for spelling in ("partOf", "PartOf"):
        got = _ok(board, "--from", "A1", "--type", spelling, "--dir", "in")
        assert _paths(got) == _paths(want), spelling
        assert got[0].startswith("@WALK: type=partOf|"), got[0]


def test_in_session_stored_folded_and_walked(board):
    rels = {e.fields["id"]: e.fields["relation"] for e in board.store.list_records("EDG")}
    assert rels["E_s1"] == "inSession"
    for spelling in ("IN_SESSION", "inSession", "InSession"):
        assert _end_ids(_ok(board, "--from", "A1", "--type", spelling)) == ["S1"], spelling


def test_snake_lower_is_not_folded(board):
    # part_of keeps its spelling, so no edge has it (MN-REQ-14.7: refused, not empty)
    err = _refused(board, "unknown_relation", "--from", "A1", "--type", "part_of", "--dir", "in")
    assert "part_of" in err


def test_unknown_valid_type_refused(board):
    _refused(board, "unknown_relation", "--from", "A1", "--type", "NEVER_USED", "--dir", "both")


def test_invalid_relation_refused(board):
    _refused(board, "invalid_relation", "--from", "A1", "--type", "PART-OF")
    _engine_refused(board.store, "invalid_relation", start="A1", relation="PART-OF")


# ----- 1..k hops ------------------------------------------------------------------


def _chain(ss, n: int, rel: str = "REPLACES") -> list[str]:
    nicks = [f"c{i:02d}" for i in range(n)]
    _nodes(ss, *nicks)
    for a, b in zip(nicks, nicks[1:], strict=False):
        _edge(ss, a, rel, b, f"e_{a}")
    return nicks


def test_chain_of_12_at_max_10(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    nicks = _chain(ss, 12)
    lines = _ok(ss, "--from", "c00", "--type", "REPLACES", "--max-hops", "10")
    rows = _paths(lines)
    assert len(rows) == 10
    assert _end_ids(lines) == nicks[1:11]
    for i, (row, hops, path) in enumerate(rows, start=1):
        assert row == str(i)
        assert hops == str(i)
        # each path lists start .. end in walk order
        pos = [path.index(f"'{n}'") for n in nicks[: i + 1]]
        assert pos == sorted(pos), path
        assert f"'{nicks[i + 1]}'" not in path if i + 1 < 12 else True
        assert path.count("-[:replaces") == i, path
    assert _stat(lines, "walk_truncated") == ["walk_truncated", "none", "-"]
    tw = _tw()
    res = tw.typed_walk(ss.store, start="c00", relation="REPLACES", max_hops=10)
    for i, p in enumerate(res.paths, start=1):
        assert [s.node.fields["id"] for s in p.steps] == nicks[1 : i + 1]
        assert [s.edge.fields["id"] for s in p.steps] == [f"e_{n}" for n in nicks[:i]]
        assert all(s.forward for s in p.steps)


def test_chain_walked_backwards(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    nicks = _chain(ss, 5)
    lines = _ok(ss, "--from", "c04", "--type", "REPLACES", "--dir", "in", "--max-hops", "10")
    assert _end_ids(lines) == ["c03", "c02", "c01", "c00"]
    assert all("<-[:replaces" in p[2] for p in _paths(lines))
    assert nicks[0] == "c00"


def test_cycle_ends(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _nodes(ss, "a", "b", "c")
    _edge(ss, "a", "CITES", "b", "ab")
    _edge(ss, "b", "CITES", "c", "bc")
    _edge(ss, "c", "CITES", "a", "ca")
    lines = _ok(ss, "--from", "a", "--type", "CITES", "--max-hops", "10")
    assert _end_ids(lines) == ["b", "c"]
    assert [h for _r, h, _p in _paths(lines)] == ["1", "2"]
    both = _ok(ss, "--from", "a", "--type", "CITES", "--dir", "both", "--max-hops", "10")
    assert sorted(_end_ids(both)) == ["b", "c"]
    assert [h for _r, h, _p in _paths(both)] == ["1", "1"]


def test_min_hops_skips_rows_but_expands(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    nicks = _chain(ss, 8)
    lines = _ok(ss, "--from", "c00", "--type", "REPLACES", "--min-hops", "3", "--max-hops", "5")
    assert _end_ids(lines) == nicks[3:6]
    assert [(r, h) for r, h, _p in _paths(lines)] == [("1", "3"), ("2", "4"), ("3", "5")]
    assert lines[0] == "@WALK: type=replaces|dir=out|hops=3..5|limit=50"
    # the hop-3 row still shows the full path through c01, c02
    first = _paths(lines)[0][2]
    for n in nicks[:4]:
        assert f"'{n}'" in first


def test_shortest_path_wins_bfs(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _nodes(ss, "s", "a", "b", "t")
    _edge(ss, "s", "DEP", "a", "sa")
    _edge(ss, "a", "DEP", "b", "ab")
    _edge(ss, "b", "DEP", "t", "bt")
    _edge(ss, "s", "DEP", "t", "st")
    lines = _ok(ss, "--from", "s", "--type", "DEP", "--max-hops", "5")
    assert _end_ids(lines) == ["a", "t", "b"]
    assert [h for _r, h, _p in _paths(lines)] == ["1", "1", "2"]


# ----- order (D6) ---------------------------------------------------------------


def _fan(ss) -> None:
    _apply(ss, "CREATE (:T {id: 'S', name: 'start'})")
    _apply(
        ss,
        "CREATE (:T {id: 'zz', name: 'z', rank: '1'})",
        "CREATE (:T {id: 'mm', name: 'm', rank: '3'})",
        "CREATE (:T {id: 'aa', name: 'a', rank: '2'})",
    )
    # edge nicknames sort the other way round
    _edge(ss, "S", "LINKS", "zz", "e9")
    _edge(ss, "S", "LINKS", "mm", "e5")
    _edge(ss, "S", "LINKS", "aa", "e1")


def test_order_is_insertion_not_id(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _fan(ss)
    assert _end_ids(_ok(ss, "--from", "S", "--type", "LINKS")) == ["zz", "mm", "aa"]


def test_order_follows_edge_insert_not_node_insert(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _nodes(ss, "S", "n1", "n2", "n3")
    _edge(ss, "S", "LINKS", "n3", "x1")
    _edge(ss, "S", "LINKS", "n1", "x2")
    _edge(ss, "S", "LINKS", "n2", "x3")
    assert _end_ids(_ok(ss, "--from", "S", "--type", "LINKS")) == ["n3", "n1", "n2"]


def test_order_survives_rename(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _fan(ss)
    _apply(ss, "MATCH (n {id: 'mm'}) SET n.id = 'a0'", mode="update")
    _apply(ss, "MATCH (n {id: 'zz'}) SET n.id = 'zzz'", mode="update")
    assert _end_ids(_ok(ss, "--from", "S", "--type", "LINKS")) == ["zzz", "a0", "aa"]


def test_order_ignores_property_values(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _fan(ss)
    before = _end_ids(_ok(ss, "--from", "S", "--type", "LINKS"))
    _apply(ss, "MATCH (n {id: 'zz'}) SET n.rank = '9'")
    _apply(ss, "MATCH (n {id: 'aa'}) SET n.name = '0'")
    assert _end_ids(_ok(ss, "--from", "S", "--type", "LINKS")) == before == ["zz", "mm", "aa"]


def test_order_hop_major_then_parent_order(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _nodes(ss, "S", "p1", "p2", "q1", "q2", "q3")
    _edge(ss, "S", "LINKS", "p2", "a")
    _edge(ss, "S", "LINKS", "p1", "b")
    _edge(ss, "p1", "LINKS", "q1", "c")
    _edge(ss, "p2", "LINKS", "q2", "d")
    _edge(ss, "p1", "LINKS", "q3", "e")
    lines = _ok(ss, "--from", "S", "--type", "LINKS", "--max-hops", "2")
    # p2 is dequeued before p1, so q2 comes before q1, q3
    assert _end_ids(lines) == ["p2", "p1", "q2", "q1", "q3"]


def test_save_load_keeps_output(memnet_temp, tmp_path: Path):
    from memnet.snapshot import load_snapshot, write_snapshot

    tw = _tw()
    ss = open_session(map_lines=list(_MAP))
    _fan(ss)
    _nodes(ss, "deep")
    _edge(ss, "aa", "LINKS", "deep", "e0")
    _edge(ss, "zz", "LINKS", "S", "back")
    _apply(ss, "MATCH (n {id: 'mm'}) SET n.id = 'm2'", mode="update")
    want = tw.emit_walk(
        tw.typed_walk(ss.store, start="S", relation="LINKS", direction="both", max_hops=3)
    )
    path = tmp_path / "walk.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path)
    got = tw.emit_walk(
        tw.typed_walk(loaded.store, start="S", relation="LINKS", direction="both", max_hops=3)
    )
    assert got == want
    assert _end_ids(got) == ["zz", "m2", "aa", "deep"]


def test_cli_session_save_load_keeps_output(memnet_temp, tmp_path: Path):
    ss = open_session(map_lines=list(_MAP))
    _fan(ss)
    _edge(ss, "aa", "LINKS", "mm", "e0")
    sid = ss.session_id
    args = ("--from", "S", "--type", "LINKS", "--dir", "both", "--max-hops", "2")
    want = _ok(ss, *args)
    path = tmp_path / "cli.snap"
    saved = run_argv(["session", "save", "--file", str(path), "--session", sid])
    assert saved["exit_code"] == 0, saved["stderr"]
    close_session(sid)
    loaded = run_argv(["session", "load", "--file", str(path), "--keep-id"])
    assert loaded["exit_code"] == 0, loaded["stderr"]
    got = run_argv(["query", "typed-walk", *args, "--session", sid])
    assert got["exit_code"] == 0, got["stderr"]
    assert got["stdout"].splitlines() == want


# ----- bounds (D7) ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("lo", "hi"),
    [("0", "1"), ("1", "11"), ("3", "2"), ("0", "0"), ("-1", "2")],
)
def test_hops_out_of_range(board, lo, hi):
    err = _refused(
        board,
        "hops_out_of_range",
        "--from",
        "A1",
        "--type",
        "PART_OF",
        "--min-hops",
        lo,
        "--max-hops",
        hi,
    )
    assert f"hops {lo}..{hi} must satisfy 1 <= min <= max <= 10" in err
    _engine_refused(
        board.store,
        "hops_out_of_range",
        start="A1",
        relation="PART_OF",
        min_hops=int(lo),
        max_hops=int(hi),
    )


def test_max_hops_ten_is_allowed(board):
    lines = _ok(board, "--from", "A1", "--type", "PART_OF", "--min-hops", "10", "--max-hops", "10")
    assert lines[0] == "@WALK: type=partOf|dir=out|hops=10..10|limit=50"


def test_invalid_direction(board):
    err = _refused(board, "invalid_direction", "--from", "A1", "--type", "PART_OF", "--dir", "up")
    assert "direction 'up' must be out, in or both" in err
    _engine_refused(
        board.store, "invalid_direction", start="A1", relation="PART_OF", direction="up"
    )


@pytest.mark.parametrize("limit", ["0", "501", "-3"])
def test_limit_out_of_range(board, limit):
    err = _refused(
        board, "limit_out_of_range", "--from", "A1", "--type", "PART_OF", "--limit", limit
    )
    assert f"limit {limit} must be 1..500" in err
    _engine_refused(
        board.store, "limit_out_of_range", start="A1", relation="PART_OF", limit=int(limit)
    )


def test_limit_500_is_allowed(board):
    lines = _ok(board, "--from", "A1", "--type", "PART_OF", "--limit", "500")
    assert lines[0].endswith("|limit=500")


def test_limit_exact_is_not_truncated(board):
    lines = _ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "in", "--limit", "3")
    assert _end_ids(lines) == ["R1", "R2", ""]
    assert _stat(lines, "walk_rows") == ["walk_rows", "3", "3"]
    assert _stat(lines, "walk_truncated") == ["walk_truncated", "none", "-"]


def test_limit_one_short_is_truncated_prefix(board):
    full = _ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "in")
    lines = _ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "in", "--limit", "2")
    assert _end_ids(lines) == ["R1", "R2"]
    assert _paths(lines) == _paths(full)[:2]
    assert _stat(lines, "walk_rows") == ["walk_rows", "2", "2"]
    assert _stat(lines, "walk_truncated") == ["walk_truncated", "limit", "-"]
    tw = _tw()
    res = tw.typed_walk(board.store, start="A1", relation="PART_OF", direction="in", limit=2)
    assert res.truncated == "limit"
    assert len(res.paths) == 2


def _star(ss, n: int) -> list[str]:
    leaves = [f"L{i:02d}" for i in range(n)]
    _nodes(ss, "hub", *leaves)
    for leaf in leaves:
        _edge(ss, "hub", "LINKS", leaf, f"h_{leaf}")
    for a, b in zip(leaves, leaves[1:], strict=False):
        _edge(ss, a, "LINKS", b, f"s_{a}")
    return leaves


def test_examined_budget_truncates_to_prefix(memnet_temp, monkeypatch):
    tw = _tw()
    ss = open_session(map_lines=list(_MAP))
    _star(ss, 12)
    full = tw.typed_walk(ss.store, start="hub", relation="LINKS", direction="both", max_hops=3)
    assert full.truncated is None
    assert full.examined > 5
    assert full.visited == len(full.paths) + 1
    monkeypatch.setattr(tw, "WALK_MAX_EXAMINED", 5)
    cut = tw.typed_walk(ss.store, start="hub", relation="LINKS", direction="both", max_hops=3)
    assert cut.truncated == "budget"
    assert cut.examined <= 5
    assert cut.visited <= cut.examined + 1
    assert len(cut.paths) < len(full.paths)
    assert _end_nicks(cut) == _end_nicks(full)[: len(cut.paths)]
    lines = _ok(ss, "--from", "hub", "--type", "LINKS", "--dir", "both", "--max-hops", "3")
    assert _stat(lines, "walk_truncated") == ["walk_truncated", "budget", "-"]
    assert _end_ids(lines) == _end_nicks(cut)


def test_examined_reads_only_typed_edges(memnet_temp):
    tw = _tw()
    ss = open_session(map_lines=list(_MAP))
    _nodes(ss, "hub", "t1", "o1", "o2", "o3")
    _edge(ss, "hub", "LINKS", "t1", "t")
    for leaf in ("o1", "o2", "o3"):
        _edge(ss, "hub", "OTHER", leaf, f"x_{leaf}")
    res = tw.typed_walk(ss.store, start="hub", relation="LINKS")
    assert _end_nicks(res) == ["t1"]
    assert res.examined == 1


def _byte_len(lines: list[str]) -> int:
    return sum(len(ln.encode("utf-8")) + 1 for ln in lines)


def test_reply_bytes_truncates(memnet_temp, monkeypatch):
    tw = _tw()
    ss = open_session(map_lines=list(_MAP))
    _star(ss, 8)
    res = tw.typed_walk(ss.store, start="hub", relation="LINKS")
    full = tw.emit_walk(res, max_bytes=10**9)
    assert _stat(full, "walk_truncated") == ["walk_truncated", "none", "-"]
    cap = _byte_len(full) - 1
    cut = tw.emit_walk(res, max_bytes=cap)
    assert _byte_len(cut) <= cap
    assert _stat(cut, "walk_truncated") == ["walk_truncated", "bytes", "-"]
    n = len(_paths(cut))
    assert 0 < n < len(_paths(full))
    assert _paths(cut) == _paths(full)[:n]
    assert _stat(cut, "walk_rows") == ["walk_rows", str(n), "50"]
    # the module constant is read at call time, on the CLI path too
    monkeypatch.setattr(tw, "WALK_MAX_REPLY_BYTES", cap)
    assert tw.emit_walk(res) == cut
    assert _ok(ss, "--from", "hub", "--type", "LINKS") == cut


# ----- reply shape (D9) -------------------------------------------------------------


def test_reply_lines_exact(board):
    lines = _ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "in")
    assert lines[0] == "@WALK: type=partOf|dir=in|hops=1..1|limit=50"
    assert lines[-3:] == [
        "@STAT: walk_rows|3|50",
        "@STAT: walk_truncated|none|-",
        "@STAT: walk_cursor|-|-",
    ]
    assert len(lines) == 1 + 3 + 3
    r1 = _node(board, "R1")
    want_end = emit_node_shaped(r1.tag, "R1", dict(r1.fields))
    row, hops, path = _paths(lines)[0]
    assert (row, hops) == ("1", "1")
    assert path.endswith(want_end)
    assert _squash(path[: -len(want_end)]) == _squash("(:ASK {id:'A1'})<-[:partOf {id:'E_r1'}]-")
    assert lines[1] == f"@PATH: 1|1|{path}"


def test_reply_forward_two_hops_shape(board):
    lines = _ok(board, "--from", "R1", "--type", "PART_OF", "--max-hops", "2")
    assert lines[0] == "@WALK: type=partOf|dir=out|hops=1..2|limit=50"
    (row,) = _paths(lines)
    a1 = _node(board, "A1")
    want_end = emit_node_shaped(a1.tag, "A1", dict(a1.fields))
    assert row[2].endswith(want_end)
    assert _squash(row[2][: -len(want_end)]) == _squash("(:ROW {id:'R1'})-[:partOf {id:'E_r1'}]->")


def test_intermediate_nodes_are_kind_and_id_only(memnet_temp):
    ss = open_session(map_lines=list(_MAP))
    _apply(
        ss,
        "CREATE (:T {id: 's', name: 'start', rank: '5'})",
        "CREATE (:T {id: 'm', name: 'middle', rank: '6'})",
        "CREATE (:T {id: 'e', name: 'end', rank: '7'})",
    )
    _edge(ss, "s", "DEP", "m", "sm")
    _edge(ss, "m", "DEP", "e", "me")
    lines = _ok(ss, "--from", "s", "--type", "DEP", "--min-hops", "2", "--max-hops", "2")
    (row,) = _paths(lines)
    e = _node(ss, "e")
    want_end = emit_node_shaped(e.tag, "e", dict(e.fields))
    assert row[2].endswith(want_end)
    head = row[2][: -len(want_end)]
    assert _squash(head) == _squash(
        "(:T {id:'s'})-[:dep {id:'sm'}]->(:T {id:'m'})-[:dep {id:'me'}]->"
    )
    assert "start" not in head and "middle" not in head


def test_result_cursor_is_none(board):
    tw = _tw()
    for limit in (1, 50):
        res = tw.typed_walk(
            board.store, start="A1", relation="PART_OF", direction="in", limit=limit
        )
        assert res.cursor is None
        assert tw.emit_walk(res)[-1] == "@STAT: walk_cursor|-|-"


def test_empty_walk_reply(board):
    lines = _ok(board, "--from", "S1", "--type", "PART_OF")
    assert lines == [
        "@WALK: type=partOf|dir=out|hops=1..1|limit=50",
        "@STAT: walk_rows|0|50",
        "@STAT: walk_truncated|none|-",
        "@STAT: walk_cursor|-|-",
    ]


# ----- surface (D1) ----------------------------------------------------------------


def test_return_still_product_gated_beside_the_verb(board):
    assert _end_ids(_ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "in")) == [
        "R1",
        "R2",
        "",
    ]
    out = run_argv(
        ["mutate", "--stdin", "--session", board.session_id],
        stdin="MATCH (a {id:'A1'})<-[:PART_OF]-(r) RETURN r\n",
    )
    assert out["exit_code"] != 0
    assert "@ERR: product_gate|" in out["stderr"]


def test_one_mcp_typed_walk_tool(board, monkeypatch):
    _tw()
    assert _end_ids(_ok(board, "--from", "R1", "--type", "PART_OF")) == ["A1"]
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    from memnet_mcp.server import mcp

    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "query_walk" in names
    # MN-REQ-14.7 slice: the handle-only typed_walk tool (tests/test_typed_walk_mcp.py)
    assert [n for n in names if "typed" in n.lower()] == ["typed_walk"], names


def test_leftover_query_walk_unchanged(board):
    typed = _ok(board, "--from", "A1", "--type", "PART_OF", "--dir", "in")
    assert typed[0].startswith("@WALK: type=")
    a1, s1, r1, r2 = (_node(board, n) for n in ("A1", "S1", "R1", "R2"))
    anon = next(r for r in board.store.list_records("ROW") if not r.fields.get("id"))
    out = run_argv(["query", "walk", "--anchor", "R1", "--session", board.session_id])
    assert out["exit_code"] == 0, out["stderr"]
    lines = out["stdout"].splitlines()
    # 4b8ed16 output, byte for byte (hids and all: it is leftover hop debug)
    assert lines == [
        f"@WALK: {a1.hid} -[inSession]-> {s1.hid}",
        f"@WALK: {anon.hid} -[partOf]-> {a1.hid}",
        f"@WALK: {r1.hid} -[partOf]-> {a1.hid}",
        f"@WALK: {r2.hid} -[partOf]-> {a1.hid}",
    ]
    assert not any(ln.startswith(("@PATH", "@STAT: walk_")) for ln in lines)
