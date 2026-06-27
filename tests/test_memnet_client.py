"""Tests for warm_walk fetch fallback."""

from __future__ import annotations

from memnet_mcp.client import MemNetResponse
from novel_mcp.warm_walk import fetch_warm_walk


def test_fetch_warm_walk_neighbors_fallback(monkeypatch):
    def fake_run(argv, stdin=None, session=None):
        if argv[0] == "query" and "walk" in argv:
            return MemNetResponse(
                exit_code=1,
                stdout="",
                stderr="@ERR: internal|UsageError: No such command 'walk'.\n",
                session_id=session,
                errors=[],
            )
        if argv[0] == "query" and argv[1] == "neighbors":
            return MemNetResponse(
                exit_code=0,
                stdout="@EDG: EG01|STEP01|governs|USR51||persistent\n",
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.warm_walk.run_memnet", fake_run)
    out = fetch_warm_walk(session="mn_x", anchor="STEP01", depth=2, max_rows=10)
    assert out == "@WALK: STEP01 -[governs]-> USR51\n"
