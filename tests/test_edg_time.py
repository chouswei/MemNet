"""@EDG.at — plot-edge in-world timestamps."""

from __future__ import annotations

from memnet.fixed_tags import fixed_tag_map
from memnet.tag_map import parse_line

from novel_mcp.edg_time import (
    law_requires_edg_at,
    prepare_edg_add_lines,
    stamp_edg_parts,
    validate_edg_at_add_lines,
)

_WARM_WITH_LAW = "\n".join(
    [
        "@LAW: LAW-EDG01|EDG|on_add|plot_at|cite_SYS_time;skip_wiring",
        "@SYS: SYS01|1|1637-09-01T08|0|0|0|1:1",
    ]
)


def test_legacy_six_field_edg_parses():
    tm = fixed_tag_map()
    rec = parse_line("@EDG: E01|N01|seeks_help|PLR01|unlock|persistent", tm)
    assert rec.fields["at"] == ""
    assert rec.fields["attrs"] == "unlock"
    assert rec.fields["recycle"] == "persistent"


def test_seven_field_edg_at_roundtrip():
    tm = fixed_tag_map()
    line = "@EDG: E02|N01|speaks|PLR01|1637-09-01T08|greeting|persistent"
    rec = parse_line(line, tm)
    assert rec.fields["at"] == "1637-09-01T08"
    assert rec.fields["attrs"] == "greeting"


def test_stamp_skips_wiring_relations():
    parts = stamp_edg_parts(
        ["E03", "SCN01", "features", "N01", "", "", "delete_on_settle"],
        "1637-09-01T09",
    )
    assert parts[4] == ""


def test_stamp_fills_plot_relation():
    parts = stamp_edg_parts(
        ["E04", "N01", "speaks", "PLR01", "", "hello", "persistent"],
        "1637-09-01T09",
    )
    assert parts[4] == "1637-09-01T09"


def test_prepare_edg_add_lines_expands_legacy_and_stamps():
    lines = [
        "@EDG: E05|N01|unknows|TEC01||delete_on_settle",
        "@EDG: E06|SCN02|features|P01||delete_on_settle",
    ]
    out = prepare_edg_add_lines(
        lines,
        sys_time="1637-09-01T10",
        warm_stdout=_WARM_WITH_LAW,
    )
    assert len(out) == 2
    assert "1637-09-01T10" in out[0]
    assert "1637-09-01T10" not in out[1]


def test_validate_edg_at_missing_plot_edge():
    lines = ["@EDG: E07|N01|qiuzhu|PLR01||persistent"]
    errs = validate_edg_at_add_lines(lines, warm_stdout=_WARM_WITH_LAW)
    assert any("edg_at_missing" in e for e in errs)


def test_law_requires_edg_at_from_seed_token():
    assert law_requires_edg_at(_WARM_WITH_LAW)
    assert not law_requires_edg_at("@LAW: LAW01|EDG|on_context|hide|x")
