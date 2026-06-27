"""Tests for Phase C library_contracts compiler."""

from __future__ import annotations

from novel_mcp.library_contracts import compile_library_contracts, match_lib_rows
from novel_mcp.presentation import compile_presentation
from novel_mcp.warm_index import index_warm

SHENJIA_LIB_WARM = """\
@LAW: LAW-LIB01|LIB|on_turn|lib_cite|cite_usr31;cite_glo_vocab_on_overlap
@LAW: LAW-LIB03|LIB|on_pick|lib_context|anchor_last_oln;match_LIB;no_tech_tree_only
@USR: USR31|lib_anchor|last_oln_match_LIB;fallback_LIB01|persistent
@USR: USR31b|lib_match_keys|風箱;皮墊;漏風;聽聲;塊子;炭|persistent
@USR: USR31c|lib_glo_ids|GLO09|persistent
@USR: USR52|stage_hint_lib|【靈魂圖書館檢閱】須對準本拍OLN|persistent
@GLO: GLO09|匠話|土法炭火|堅炭;燒透;塊子;成料;聽聲|persistent
@LIB: LIB01|T01|升級作坊|upgrade_route|可查|常駐
@LIB: LIB02|TEC01|焦炭製作|coke_step1|鎖定|常駐
@LIB: LIB04|smithy_ops|風箱皮墊|bellows_leather|可查|常駐
@TEC: TEC01|焦炭製作|熱力冶金|鎖定|產量+300%
@OLN: OLN05|5|風箱漏風|硝指出皮垫問題；芯意外|「待會開爐前來扶」|灶房|delete_on_settle
@OLN: OLN04|4|求首肯|硝問芯|芯：算穩|歇半刻|delete_on_settle
"""

GENERIC_RPG_WARM = """\
@LAW: LAW-LIB01|LIB|on_turn|lib_cite|cite_usr31;cite_glo_vocab_on_overlap
@LAW: LAW-LIB03|LIB|on_pick|lib_context|no_tech_tree_only
@USR: U31|lib_anchor|last_oln_match_LIB;fallback_L01|persistent
@USR: U31b|lib_match_keys|gate;ward;patrol|persistent
@USR: U31c|lib_glo_ids|G01|persistent
@GLO: G01|watch|fortress|beacon;patrol;gate|persistent
@LIB: L01|Q01|main quest|route|open|persistent
@LIB: L02|TEC01|alchemy|brew_step|locked|persistent
@LIB: L03|fortress|gate ward|warding|open|persistent
@TEC: TEC01|alchemy|craft|locked|effect
@OLN: OLN02|2|gate alarm|patrol the ward|npc warns|hook|persistent
"""


def test_match_lib_rows_bellows_from_latest_oln():
    idx = index_warm(SHENJIA_LIB_WARM)
    matched = match_lib_rows(idx, "風箱漏風 皮垫 待會開爐")
    ids = [row[0] for row in matched]
    assert "LIB04" in ids
    assert "LIB02" not in ids


def test_compile_library_contracts_lib_query_bellows():
    idx = index_warm(SHENJIA_LIB_WARM)
    bullets, meta = compile_library_contracts(idx, lib_query=True)
    text = "\n".join(bullets)
    assert "【靈魂圖書館檢閱】" in text
    assert "LIB04" in text
    assert "GLO09" in text
    assert "no_tech_tree_only" in text
    assert meta["oln_anchor"] == "OLN05"


def test_presentation_injects_library_contracts_on_lib_query():
    pres = compile_presentation(
        SHENJIA_LIB_WARM,
        {"beat_stage": "oln", "lib_query": True},
    )
    assert pres["library_contracts"]
    assert any("LIB04" in c for c in pres["library_contracts"])
    assert any("LIB04" in c for c in pres["contracts"])


def test_generic_seed_glo_vocab_from_glo_row_not_hardcoded():
    idx = index_warm(GENERIC_RPG_WARM)
    bullets, meta = compile_library_contracts(idx, lib_query=True)
    text = "\n".join(bullets)
    assert "L03" in meta["matched_libs"]
    assert "G01" in text
    assert "patrol" in text
    assert "no_tech_tree_only" in text
    assert "LIB02" not in text and "L02" not in meta["matched_libs"]
