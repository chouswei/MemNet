"""Tests for warm_index."""

from __future__ import annotations

from novel_mcp.warm_index import index_warm, laws_for_stage, pipeline_no_bundle, usr_value

WARM = """\
@USR: U1|prose_warm|voice a|persistent
@USR: U2|beat_stage|oln|persistent
@LAW: L1|x|1|warm_prose|ban_telegraphic
@LAW: L2|x|1|opt_readable|full_sentence
@LAW: L3|x|1|vit_embed|prose_embed
"""


def test_usr_by_key():
    idx = index_warm(WARM)
    assert usr_value(idx, "prose_warm") == "voice a"
    assert len(laws_for_stage(idx, "oln")) == 1
    assert laws_for_stage(idx, "oln")[0].id == "L3"
    assert len(laws_for_stage(idx, "prose", for_options=True)) >= 1


def test_pipeline_no_bundle_from_law():
    warm = "@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|no_bundle;one_wire|persistent\n"
    assert pipeline_no_bundle(index_warm(warm)) is True
    assert pipeline_no_bundle(index_warm(WARM)) is False
