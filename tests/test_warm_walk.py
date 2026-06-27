"""Tests for warm_walk fallback from neighbors wire."""

from __future__ import annotations

from novel_mcp.warm_walk import hops_from_wire, walk_stdout_from_wire


def test_hops_from_wire_edg_lines():
    wire = """\
@EDG: EG01|STEP01|governs|USR51||persistent
@EDG: EG02|USR51|governs|LAW-PROSE00||persistent
@STEP: STEP01|1|SCN01|persistent
"""
    hops = hops_from_wire(wire)
    assert ("STEP01", "governs", "USR51") in hops
    assert ("USR51", "governs", "LAW-PROSE00") in hops


def test_walk_stdout_from_wire():
    wire = "@EDG: EG01|STEP01|governs|USR51||persistent\n"
    out = walk_stdout_from_wire(wire)
    assert out == "@WALK: STEP01 -[governs]-> USR51\n"
