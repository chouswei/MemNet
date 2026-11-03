"""Per-command cost: click command built once per process; one stale-scan pass.

Red-first for symphony range-where-id-index M1 (node P-cmd). The pinned
interface lands in M2: ``memnet.in_process_engine.cli_command`` /
``reset_cli_command`` / ``invoke_cli`` and ``memnet.housekeep.stale_counts``.
New names are imported inside test bodies so the rest of the file still runs
on the old code.
"""

from __future__ import annotations

import typer.main

from memnet.mutate_gate import MutateGate
from memnet.output import capture_request_stdio, format_wrn, reset_warn_budget
from memnet.session import open_session

_MAP = ["SCHEMA PRT ; fields=id name role recycle"]


def _count_get_command(monkeypatch) -> list[int]:
    """Wrap ``typer.main.get_command`` (module attribute) with a call counter."""
    calls = [0]
    real = typer.main.get_command

    def counting(typer_instance):
        calls[0] += 1
        return real(typer_instance)

    monkeypatch.setattr(typer.main, "get_command", counting)
    return calls


def _spy_categorise(monkeypatch) -> list[int]:
    from memnet import housekeep

    calls = [0]
    real = housekeep._categorise

    def spy(*args, **kwargs):
        calls[0] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(housekeep, "_categorise", spy)
    return calls


def _stale_session():
    """Session with recyclable, dangling and orphan rows."""
    ss = open_session(map_lines=_MAP)
    MutateGate(ss).apply(
        [
            "@PRT: P1|a|r|persistent",
            "@PRT: P2|b|r|persistent",
            "@PRT: P3|alone|r|persistent",
            "@PRT: P4|gone1|r|delete_on_settle",
            "@PRT: P5|gone2|r|delete_on_expire",
            "@EDG: E1|P1|links|P2|||",
            "@EDG: E2|P1|links|P2|||",
        ],
        mode="add",
        allow_new_relation=True,
    )
    e2 = next(
        rec
        for rec in ss.store._by_hid.values()
        if rec.tag == "EDG" and rec.fields.get("id") == "E2"
    )
    e2.fields["dist"] = "NO_SUCH_NODE"
    return ss


def _run_triple(run_argv) -> list[tuple[int, str]]:
    return [
        (r["exit_code"], r["stdout"])
        for r in (
            run_argv(["--help"]),
            run_argv(["session", "list"]),
            run_argv(["version"]),
        )
    ]


# 1 — CLI in-process path builds the click command at most once.
def test_run_argv_builds_click_command_once(memnet_temp, monkeypatch):
    from memnet.in_process_engine import reset_cli_command, run_argv

    before = _run_triple(run_argv)
    reset_cli_command()
    calls = _count_get_command(monkeypatch)
    after = _run_triple(run_argv)
    assert calls[0] <= 1, f"get_command called {calls[0]} times for 3 commands"
    assert after == before


# 2 — serve request path and MCP in-process path share the one command.
def test_serve_and_mcp_build_click_command_once(memnet_temp, monkeypatch):
    from memnet import serve
    from memnet.in_process_engine import reset_cli_command
    from memnet_mcp.client import run_memnet

    monkeypatch.delenv("MEMNET_MCP_TRANSPORT", raising=False)
    reset_cli_command()
    calls = _count_get_command(monkeypatch)
    r1 = serve._handle_request({"args": ["version"]})
    r2 = serve._handle_request({"args": ["session", "list"]})
    m1 = run_memnet(["version"])
    m2 = run_memnet(["session", "list"])
    assert calls[0] <= 1, f"get_command called {calls[0]} times for 4 commands"
    assert r1["exit_code"] == 0 and r1["stdout"].strip()
    assert r2["exit_code"] == 0
    assert m1.exit_code == 0 and m1.stdout == r1["stdout"]
    assert m2.exit_code == 0


# 3 — error parity on every path (green before and after the change).
def test_serve_usage_error_stays_exit_2(memnet_temp):
    from memnet import serve

    resp = serve._handle_request({"args": ["version", "--no-such-option"]})
    assert resp["exit_code"] == 2
    assert "@ERR: usage|" in resp["stderr"]


def test_raising_command_is_internal_error(memnet_temp, monkeypatch):
    from memnet import cli
    from memnet.in_process_engine import run_argv

    def boom(json_out: bool) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "_emit_version", boom)
    resp = run_argv(["version"])
    assert resp["exit_code"] == 1
    assert "@ERR: internal|RuntimeError: boom" in resp["stderr"]


def test_system_exit_codes_kept(memnet_temp, monkeypatch):
    from memnet import cli, serve
    from memnet.in_process_engine import run_argv
    from memnet_mcp.client import run_memnet

    monkeypatch.delenv("MEMNET_MCP_TRANSPORT", raising=False)

    def leave(json_out: bool) -> None:
        raise SystemExit(3)

    monkeypatch.setattr(cli, "_emit_version", leave)
    assert run_argv(["version"])["exit_code"] == 3
    assert serve._handle_request({"args": ["version"]})["exit_code"] == 3
    assert run_memnet(["version"]).exit_code == 3


# 4 — emit_stale_warnings: one categorising pass, same @WRN lines.
def test_stale_warnings_one_pass_same_lines(memnet_temp, monkeypatch):
    from memnet.housekeep import dangling_rows, orphan_rows, recyclable_rows
    from memnet.warnings import emit_stale_warnings

    ss = _stale_session()
    r = len(recyclable_rows(ss))
    d = len(dangling_rows(ss))
    o = len(orphan_rows(ss))
    assert r and d and o, (r, d, o)
    expected = [
        format_wrn(
            "stale_in_store", f"{r}|query warm or housekeep prune recyclable --apply", force=True
        ),
        format_wrn(
            "stale_dangling", f"{d}|housekeep dangling or prune dangling --apply", force=True
        ),
        format_wrn("stale_orphans", f"{o}|housekeep orphans or prune orphans --apply", force=True),
        format_wrn("stale_graph", f"{r}|{d}|{o}|housekeep stale", force=True),
    ]

    calls = _spy_categorise(monkeypatch)
    reset_warn_budget()
    with capture_request_stdio(None) as (_out, err):
        emit_stale_warnings(ss)
        got = [line for line in err.getvalue().splitlines() if line.startswith("@WRN:")]
    assert calls[0] == 1, f"_categorise called {calls[0]} times"
    assert got == expected

    from memnet.housekeep import stale_counts

    assert stale_counts(ss) == (r, d, o)


# 5 — one session-loading CLI command categorises once.
def test_query_find_categorises_once(memnet_temp, monkeypatch):
    from memnet.in_process_engine import run_argv

    ss = _stale_session()
    sid = ss.meta.session_id
    calls = _spy_categorise(monkeypatch)
    resp = run_argv(["query", "find", "--kind", "PRT", "--limit", "5", "--session", sid])
    assert resp["exit_code"] == 0, resp["stderr"]
    assert calls[0] == 1, f"_categorise called {calls[0]} times"
