"""LAW budget smoke test against reference instance seed fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from novel_mcp.bootstrap import fence_lines
from novel_mcp.warm_index import index_warm, laws_for_stage

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "application-notes" / "novel-shenjia-initial-state.md"


@pytest.fixture
def engine_law_warm() -> str:
    text = SEED.read_text(encoding="utf-8")
    lines = fence_lines(text, "Opening seed — Engine")
    law_lines = [ln for ln in lines if ln.startswith("@LAW:")]
    return "\n".join(law_lines)


def test_engine_law_count_at_most_40() -> None:
    text = SEED.read_text(encoding="utf-8")
    engine = fence_lines(text, "Opening seed — Engine")
    law_lines = [ln for ln in engine if ln.startswith("@LAW:")]
    assert len(law_lines) <= 40, f"expected <=40 LAW rows, got {len(law_lines)}"


def test_no_absorbed_law_ids_in_engine_fence() -> None:
    text = SEED.read_text(encoding="utf-8")
    engine = "\n".join(fence_lines(text, "Opening seed — Engine"))
    for banned in ("LAW-WX01", "LAW-PROSE16", "LAW-OPT01", "LAW-NPC01", "LAW-HUD01"):
        assert banned not in engine


def test_laws_for_stage_oln_under_28(engine_law_warm: str) -> None:
    idx = index_warm(engine_law_warm)
    oln_laws = laws_for_stage(idx, "oln")
    # 40 LAW budget − WX/PROSE/OPT/LIB merged rows (4) ⇒ 36 script-stage laws
    assert len(oln_laws) <= 36


def test_prose_warm_index_has_npc_sys_from_fixture() -> None:
    warm = """@STEP: STEP01|1|SCN01|persistent
@USR: USR23|beat_stage|prose|persistent
@NPC: N01|沈芯|1625|女|traits|sk|it|0|常駐|常駐
@SYS: SYS01|1|1637-09-01T06|0|0|25|1兩=825文銅
"""
    idx = index_warm(warm)
    assert idx.npc_rows
    assert idx.sys_rows
