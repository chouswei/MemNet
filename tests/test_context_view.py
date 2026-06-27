"""Tests for context walk presentation."""

from __future__ import annotations

from memnet.context_view import format_walk_hop


def test_format_walk_hop():
    line = format_walk_hop("STEP01", "governs", "USR51")
    assert line == "@WALK: STEP01 -[governs]-> USR51"
