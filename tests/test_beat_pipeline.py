"""Tests for novel beat pipeline (parse warm + atomic finish)."""

from __future__ import annotations

from pathlib import Path

from novel_mcp.beat_pipeline import beat_turn_finish, parse_warm_stdout, pipeline_next_action


WARM_SAMPLE = """\
@LAW: LAW-PIPE21|STEP|on_turn|beat_turn|begin_finish_only
@STEP: STEP01|4|OLN06|persistent
@USR: USR05|scene_length|650_950_zh|persistent
@USR: USR06|chapter_out|novel-output/shenjia_caifa/chapters|persistent
@CHP: CHP01|1|3925|1|0|open
@OLN: OLN06|6|心算夜賬|躺著心算欠債炭價|芯：…|明日寅時|delete_on_settle
"""


def test_parse_warm_stdout():
    p = parse_warm_stdout(WARM_SAMPLE)
    assert p["step_n"] == 4
    assert p["step_focus"] == "OLN06"
    assert p["usr05_band"] == "650_950_zh"
    assert p["min_chars"] == 650
    assert p["max_chars"] == 950
    assert p["target_chars"] == 800
    assert p["chapter_dir"] == "novel-output/shenjia_caifa/chapters"
    assert p["chp_num"] == 1
    assert p["oln_row"].startswith("OLN06|")


def test_pipeline_next_action():
    assert "beat_turn_finish" in pipeline_next_action(4)


def test_beat_turn_finish_gate_blocked(tmp_path: Path):
    result = beat_turn_finish(
        session=None,
        prose="字" * 200,
        chapter_dir="chapters",
        chp_num=1,
        min_chars=650,
        max_chars=950,
        workspace_root=tmp_path,
    )
    assert result["exit_code"] == 1
    assert result["gate_blocked"] is True
    assert not (tmp_path / "chapters" / "第001回.md").exists()


def test_beat_turn_finish_chapter_only(tmp_path: Path):
    result = beat_turn_finish(
        session=None,
        prose="字" * 800,
        chapter_dir="chapters",
        chp_num=1,
        min_chars=650,
        max_chars=950,
        workspace_root=tmp_path,
    )
    assert result["exit_code"] == 0
    assert (tmp_path / "chapters" / "第001回.md").exists()
    assert result["chapter"]["file_char_total"] == 800
