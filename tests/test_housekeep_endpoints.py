"""MN-REQ-04.12 — edge endpoints are hid or nickname, not nickname alone."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from memnet.cli import app
from memnet.exceptions import MemNetError
from memnet.housekeep import orphan_rows, prune_rows, prune_stale, stats
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.snapshot import load_snapshot, write_snapshot

runner = CliRunner()
_MAP = ["SCHEMA PRT ; fields=id name role"]


def _gql_chain(ss, n: int = 4) -> None:
    creates = [f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: 'r'}})" for i in range(n)]
    edges = []
    for i in range(n - 1):
        edges.append(
            "MATCH (a {id: 'P"
            + str(i)
            + "'}), (b {id: 'P"
            + str(i + 1)
            + "'}) CREATE (a)-[:links {id: 'E"
            + str(i)
            + "'}]->(b)"
        )
    MutateGate(ss).apply(creates + edges, mode="mutate", allow_new_relation=True)


def _ids(ss) -> set[str]:
    return {rec.fields.get("id", "") for rec in ss.store._by_hid.values() if rec.tag == "PRT"}


def test_gql_graph_has_no_orphans_and_survives_reload(memnet_temp, tmp_path: Path):
    ss = open_session(map_lines=_MAP)
    _gql_chain(ss, 4)
    got = stats(ss)
    assert got["edges"] == 3
    assert got["dangling"] == 0
    assert got["orphans"] == 0
    assert orphan_rows(ss) == []
    edge = next(rec for rec in ss.store._by_hid.values() if rec.tag == "EDG")
    assert edge.fields["src"].startswith("_el")
    assert edge.fields["dist"].startswith("_el")
    path = tmp_path / "gql.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path)
    again = stats(loaded)
    assert again["edges"] == 3
    assert again["dangling"] == 0
    assert again["orphans"] == 0


def test_pipe_graph_keeps_nickname_endpoints_and_true_orphans(memnet_temp):
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        [
            "@PRT: P1|a|r",
            "@PRT: P2|b|r",
            "@PRT: P3|alone|r",
            "@EDG: E1|P1|links|P2|||",
        ],
        mode="add",
        allow_new_relation=True,
    )
    got = stats(ss)
    assert got["edges"] == 1
    assert got["dangling"] == 0
    assert got["orphans"] == 1
    assert [rec.fields["id"] for rec in orphan_rows(ss)] == ["P3"]
    edge = next(rec for rec in ss.store._by_hid.values() if rec.tag == "EDG")
    edge.fields["src"] = "P1"
    edge.fields["dist"] = "P2"
    again = stats(ss)
    assert again["dangling"] == 0
    assert again["orphans"] == 1
    assert [rec.fields["id"] for rec in orphan_rows(ss)] == ["P3"]


def test_half_missing_end_is_dangling_and_the_live_end_is_not_an_orphan(memnet_temp):
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        ["CREATE (:PRT {id: 'P1', name: 'a', role: 'r'})"],
        mode="add",
    )
    p1 = ss.store.get("P1")
    assert p1 is not None
    MutateGate(ss).apply(
        [f"@EDG: E_d|{p1.hid}|links|_el_missing|||"],
        mode="add",
        allow_new_relation=True,
    )
    got = stats(ss)
    assert got["dangling"] == 1
    assert got["orphans"] == 0


def test_prune_apply_on_gql_graph_deletes_nothing_referenced(memnet_temp):
    ss = open_session(map_lines=_MAP)
    _gql_chain(ss, 4)
    sid = ss.session_id
    dry = runner.invoke(app, ["housekeep", "prune", "orphans", "--session", sid])
    assert dry.exit_code == 0, dry.stderr
    assert "would-delete 0" in dry.stderr
    assert "prune orphans --apply" not in dry.stderr
    applied = runner.invoke(
        app,
        ["housekeep", "prune", "orphans", "--apply", "--session", sid],
    )
    assert applied.exit_code == 0, applied.stderr
    assert "deleted 0" in applied.stderr
    assert _ids(ss) == {"P0", "P1", "P2", "P3"}
    nodes = [rec for rec in ss.store._by_hid.values() if rec.tag == "PRT"]
    try:
        prune_rows(ss, nodes)
        raise AssertionError("expected prune_referenced")
    except MemNetError as exc:
        assert exc.code == "prune_referenced"
    assert _ids(ss) == {"P0", "P1", "P2", "P3"}
    p0 = ss.store.get("P0")
    assert p0 is not None
    p0.fields["recycle"] = "delete_on_settle"
    refused = runner.invoke(
        app,
        ["housekeep", "prune", "stale", "--apply", "--session", sid],
    )
    assert refused.exit_code != 0
    assert "prune_referenced" in refused.stderr
    assert ss.store.get("P0") is not None
    try:
        prune_stale(ss)
        raise AssertionError("expected prune_stale to refuse")
    except MemNetError as exc:
        assert exc.code == "prune_referenced"
    assert _ids(ss) == {"P0", "P1", "P2", "P3"}


def test_true_orphan_still_prunes_and_unreferenced_only(memnet_temp):
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        [
            "CREATE (:PRT {id: 'P1', name: 'a', role: 'r'})",
            "CREATE (:PRT {id: 'P2', name: 'b', role: 'r'})",
            "CREATE (:PRT {id: 'LONE', name: 'z', role: 'r'})",
        ],
        mode="add",
    )
    MutateGate(ss).apply(
        ["MATCH (a {id: 'P1'}), (b {id: 'P2'}) CREATE (a)-[:links {id: 'E1'}]->(b)"],
        mode="mutate",
        allow_new_relation=True,
    )
    assert [rec.fields["id"] for rec in orphan_rows(ss)] == ["LONE"]
    deleted = prune_rows(ss, orphan_rows(ss))
    assert [rec.fields["id"] for rec in deleted] == ["LONE"]
    assert ss.store.get("P1") is not None
    assert ss.store.get("LONE") is None
