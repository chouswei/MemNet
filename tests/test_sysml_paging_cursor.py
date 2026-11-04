"""MN-REQ-14.13 model pins: paging cursor recorded as implemented, with a PagedRead
behaviour, a PagingCursor part that satisfies it and an S13 verify case."""

from __future__ import annotations

import re
from pathlib import Path

MODELS = Path(__file__).resolve().parents[1] / "sysml-models" / "models"


def _text(name: str) -> str:
    return (MODELS / name).read_text(encoding="utf-8")


def _block(text: str, marker: str) -> str:
    start = text.index(marker)
    open_at = text.index("{", start)
    depth = 0
    for i in range(open_at, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return " ".join(text[start : i + 1].split())
    raise AssertionError(marker)


def test_models_braces_balance():
    for name in ("requirements.sysml", "verify.sysml", "behaviour.sysml", "implementation.sysml"):
        t = re.sub(r"/\*.*?\*/|//[^\n]*", "", _text(name), flags=re.S)
        assert t.count("{") == t.count("}"), name


def test_14_13_leaf_implemented_and_stated():
    d = _block(_text("requirements.sysml"), "requirement def MN_REQ_14_13_PagingCursor")
    assert "Status: implemented" in d and 'requirementId : String = "MN-REQ-14.13"' in d
    for word in ("bad_cursor", "cursor_mismatch", "stale_cursor", "next_cursor", "opt-in"):
        assert word in d, word
    assert "tests/test_paging_cursor.py" in d
    assert "MN-VER-14-S13" in d and "PagedRead" in d


def test_14_2_stays_parked_and_index_lists_14_13():
    t = _text("requirements.sysml")
    line = next(ln for ln in t.splitlines() if re.match(r"\s*MN-REQ-14\.13\s", ln))
    assert "implemented" in line and "PARKED" not in line
    line2 = next(ln for ln in t.splitlines() if re.match(r"\s*MN-REQ-14\.2\s", ln))
    assert "PARKED" in line2


def test_part_action_and_verify_case_exist():
    imp = _block(_text("implementation.sysml"), "part def PagingCursor")
    assert "MN_REQ_14_13_PagingCursor" in imp and "MemNetBehaviour::PagedRead" in imp
    assert "action def PagedRead" in _text("behaviour.sysml")
    ver = _block(_text("verify.sysml"), "verification def MN_VER_14_S13_PagingCursor")
    assert "pagingCursorReq" in ver and "tests/test_paging_cursor.py" in ver
    assert "pagingCursorReq" in _text("requirements.sysml")
