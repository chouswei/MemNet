"""Tests for writing_contract compiler (compat shim)."""

from __future__ import annotations

from novel_mcp.writing_contract import compile_writing_contract


def test_compile_writing_contract_compat():
    warm = """\
@LAW: LAW-A|x|1|demo|ban_telegraphic
@USR: U1|beat_stage|oln|persistent
@USR: U2|stage_hint_oln|Write outline|persistent
"""
    bullets = compile_writing_contract(warm, {"beat_stage": "oln"})
    assert any("outline" in b.lower() for b in bullets)
