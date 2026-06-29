"""Tests for novel beat pipeline (parse warm + atomic finish)."""

from __future__ import annotations

from pathlib import Path

from novel_mcp.beat_pipeline import beat_turn_begin, beat_turn_finish, parse_warm_stdout, pipeline_next_action
from novel_mcp.constants import NOVEL_WARM_DEPTH, NOVEL_WARM_MAX_ROWS


WARM_SAMPLE = """\
@LAW: LAW-PIPE21|STEP|on_turn|beat_turn|begin_finish_only
@STEP: STEP01|4|OLN06|persistent
@USR: USR05|scene_length|650_950_zh|persistent
@USR: USR21|prose_draft|800_zh|persistent
@USR: USR23|beat_stage|oln|persistent
@USR: USR06|chapter_out|novel-output/shenjia_caifa/chapters|persistent
@CHP: CHP01|1|3925|1|0|open
@OLN: OLN06|6|心算夜賬|躺著心算欠債炭價|芯：…|明日寅時|delete_on_settle
"""

OLN_WIRE = ["@OLN: OLN99|1|test|要点|对白|钩子|persistent"]
SBD_WIRE = ["@SBD: SBD99|1|1|画面|感官|氛围|persistent"]
SCR_WIRE = ["@SCR: SCR99|1|动作|对白|内心|音效|persistent"]


def _pipeline_kwargs(**overrides):
    base = {
        "oln_lines": OLN_WIRE,
        "sbd_lines": SBD_WIRE,
        "scr_lines": SCR_WIRE,
    }
    base.update(overrides)
    return base


def test_parse_warm_stdout_character_ages():
    warm = """\
@SYS: SYS01|1|崇禎十年(1637)秋|0|0|25|1兩=825文銅
@PLR: P01|流民|1627|未定|0|0|技能|狀態
@NPC: N01|沈芯|1625|女|聰慧|0|土法|技能|物品|0|需小工|常駐
@NPC: N02|沈蘭|1627|女|活潑|0|土法|技能|物品|0|需小工|常駐
"""
    p = parse_warm_stdout(warm)
    assert p["sys_year"] == 1637
    assert p["character_ages"] == {"P01": 10, "N01": 12, "N02": 10}
    assert "P01:10歲" in p["age_hint"]


def test_parse_warm_stdout_iso_game_time():
    warm = """\
@SYS: SYS01|10|1637-09-15T05|0|0|25|1兩=825文銅
@USR: USR43|game_time|axis=iso;display=chongzhen_shichen;era_base=1628;era_name=崇禎|persistent
@PLR: P01|鐵坊小工|1627|男|0|0|技能|狀態
"""
    p = parse_warm_stdout(warm)
    assert p["game_time"] == "1637-09-15T05"
    assert "崇禎十年九月15日・卯時" in p["time_display"]
    assert p["sys_year"] == 1637


def test_parse_warm_stdout():
    p = parse_warm_stdout(WARM_SAMPLE)
    assert p["step_n"] == 4
    assert p["step_focus"] == "OLN06"
    assert p["usr05_band"] == "650_950_zh"
    assert p["min_chars"] == 650
    assert p["max_chars"] == 950
    assert p["target_chars"] == 800
    assert p["draft_target_chars"] == 800
    assert p["chapter_dir"] == "novel-output/shenjia_caifa/chapters"
    assert p["chp_num"] == 1
    assert p["oln_row"].startswith("OLN06|")


def test_beat_turn_begin_uses_enrich_for_scr(monkeypatch):
    from novel_mcp.beat_pipeline import beat_turn_begin, parse_warm_stdout
    from memnet_mcp.client import MemNetResponse

    warm_truncated = """\
@STEP: STEP01|1|SCN01|persistent
@USR: USR23|beat_stage|prose|persistent
"""

    def fake_run(argv, stdin=None, session=None):
        if argv[:2] == ["query", "warm"]:
            return MemNetResponse(0, warm_truncated, "", session, [])
        if argv[:3] == ["read", "list", "--tag"]:
            tag = argv[3]
            if tag == "OLN":
                body = "@OLN: OLN01|1|魂穿|匠坊|对白|钩|delete_on_settle"
            elif tag == "SCR":
                body = (
                    "@SCR: SCR01|1|1|动作|对白|内心|音效|delete_on_settle\n"
                    "@SCR: SCR02|1|2|动作2|对白2|内心2|音效2|delete_on_settle"
                )
            else:
                body = ""
            return MemNetResponse(0, body, "", session, [])
        if argv[:2] == ["read", "get"]:
            return MemNetResponse(0, "@USR: USR23|beat_stage|prose|persistent", "", session, [])
        return MemNetResponse(0, "", "", session, [])

    monkeypatch.setattr("memnet_mcp.client.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.warm_supplement.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.play_context.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_warm_walk", lambda **kw: [])
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_session_modified", lambda s: None)

    out = beat_turn_begin(session="mn_x")
    pipeline = out["pipeline"]
    assert pipeline["oln_row"].startswith("OLN01|1|")
    assert "@SCR: SCR01|1|1|" in pipeline["scr_row"]
    assert "@SCR: SCR02|1|2|" in pipeline["scr_row"]


def test_parse_warm_stdout_prose_stage_attaches_scr_rows():
    warm = """\
@STEP: STEP01|1|SCN01|persistent
@USR: USR23|beat_stage|prose|persistent
@OLN: OLN01|1|魂穿驚愕|匠坊門口炭煙|芯問名|尾鉤|delete_on_settle
@SCR: SCR01|1|1|蜷身撐地|（無語）|這身體……|風箱低鳴|delete_on_settle
@SCR: SCR02|1|2|沈芯蹲下|芯：「你叫什麼？」|怎麼脫口而出？|炭火啪響|delete_on_settle
"""
    p = parse_warm_stdout(warm)
    assert p["beat_stage"] == "prose"
    assert p["step_focus"] == "SCN01"
    assert p["oln_row"].startswith("OLN01|1|")
    assert "@SCR: SCR01|1|1|" in p["scr_row"]
    assert "@SCR: SCR02|1|2|" in p["scr_row"]


def test_pipeline_next_action():
    assert "beat_turn_finish" in pipeline_next_action(4)
    assert "OLN" in pipeline_next_action(4, "oln", pipeline_no_bundle=True)
    assert "SBD" in pipeline_next_action(4, "sbd", pipeline_no_bundle=True)


def test_beat_stage_authoritative_over_stale_warm(monkeypatch):
    stale_warm = (
        "@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|no_bundle|persistent\n"
        "@USR: USR23|beat_stage|oln|persistent\n"
        "@STEP: STEP01|4|OLN03|persistent\n"
    )

    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[:2] == ["read", "get"]:
            rid = argv[argv.index("--id") + 1] if "--id" in argv else ""
            if rid == "USR23":
                return MemNetResponse(
                    exit_code=0,
                    stdout="@USR: USR23|beat_stage|sbd|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            if rid == "LAW-PIPE20":
                return MemNetResponse(
                    exit_code=0,
                    stdout="@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|no_bundle|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            if rid == "USR55":
                return MemNetResponse(
                    exit_code=0,
                    stdout="@USR: USR55|stage_hint_sbd|draft SBD|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])
        if argv[0] == "query":
            return MemNetResponse(
                exit_code=0,
                stdout=stale_warm,
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_warm_walk", lambda **kwargs: "")
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_session_modified", lambda s: "m1")
    out = beat_turn_begin(session="test")
    assert out["pipeline"]["beat_stage"] == "sbd"
    assert out["pipeline"]["pipeline_no_bundle"] is True
    assert "SBD" in out["pipeline"]["next_action"]
    assert out["presentation"]["stage"] == "sbd"


def test_pipeline_oln_then_sbd_without_bypass(monkeypatch):
    """OLN finish advances stage; SBD finish accepts when warm still shows oln."""
    stage = {"beat_stage": "oln"}

    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[:2] == ["read", "get"]:
            rid = argv[argv.index("--id") + 1] if "--id" in argv else ""
            if rid == "USR23":
                return MemNetResponse(
                    exit_code=0,
                    stdout=f"@USR: USR23|beat_stage|{stage['beat_stage']}|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            if rid == "LAW-PIPE20":
                return MemNetResponse(
                    exit_code=0,
                    stdout="@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|no_bundle|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])
        if argv[0] == "query":
            return MemNetResponse(
                exit_code=0,
                stdout="@USR: USR23|beat_stage|oln|persistent\n",
                stderr="",
                session_id=session,
                errors=[],
            )
        if argv[0] == "update" and stdin and "beat_stage|sbd" in stdin:
            stage["beat_stage"] = "sbd"
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_session_modified", lambda s: "m1")

    r1 = beat_turn_finish(session="test", oln_lines=OLN_WIRE)
    assert r1["exit_code"] == 0
    assert r1["beat_stage"] == "sbd"
    stage["beat_stage"] = "sbd"

    r2 = beat_turn_finish(session="test", sbd_lines=SBD_WIRE)
    assert r2["exit_code"] == 0
    assert r2["beat_stage"] == "scr"
    assert not r2.get("pipeline_blocked")


def test_parse_warm_stdout_qi_zero_auto_beat():
    warm = """\
@PLR: P01|鐵坊小工|1627|男|0|0|技能|氣血:0/7；內力:1/6；昏厥:是；疲勞:8
@STEP: STEP01|1|SCN01|persistent
"""
    p = parse_warm_stdout(warm)
    assert p["auto_beat"] is True
    assert p["no_options"] is True


def test_beat_turn_begin_auto_beat_next_action(monkeypatch):
    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[0] == "query" and "walk" in argv:
            return MemNetResponse(
                exit_code=0,
                stdout="",
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(
            exit_code=0,
            stdout=(
                "@PLR: P01|鐵坊小工|1627|男|0|0|技能|"
                "氣血:0/7；昏厥:是\n@STEP: STEP01|1|SCN01|persistent\n"
            ),
            stderr="",
            session_id=session,
            errors=[],
        )

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_warm_walk", lambda **kwargs: "")
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_session_modified", lambda s: None)
    out = beat_turn_begin(session="test")
    assert out["pipeline"]["auto_beat"] is True
    assert "auto_beat" in out["pipeline"]["next_action"]
    assert "no options" in out["pipeline"]["next_action"]


def test_beat_turn_begin_advisory_draft_note(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        calls.append(argv)
        if argv[0] == "query" and "walk" in argv:
            return MemNetResponse(
                exit_code=0,
                stdout="@WALK: STEP01 -[governs]-> USR21\n",
                stderr="",
                session_id=session,
                errors=[],
            )
        if argv[0] == "query" and "USR21" in argv:
            return MemNetResponse(
                exit_code=0,
                stdout="@USR: USR21|prose_target|800_zh_advisory|persistent\n",
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(
            exit_code=0,
            stdout=(
                "@USR: USR21|prose_target|800_zh_advisory|persistent\n"
                "@USR: USR05|scene_length|no_gate|persistent\n"
                "@USR: USR23|beat_stage|oln|persistent\n"
                "@STEP: STEP01|1|SCN01|persistent\n"
            ),
            stderr="",
            session_id=session,
            errors=[],
        )

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr(
        "novel_mcp.beat_pipeline.fetch_warm_walk",
        lambda **kwargs: "@WALK: STEP01 -[governs]-> USR21\n",
    )
    monkeypatch.setattr(
        "novel_mcp.beat_pipeline.fetch_session_modified",
        lambda session: "2020-01-01T00:00:00",
    )
    out = beat_turn_begin(session="test")
    assert out["pipeline"]["draft_target_chars"] == 800
    assert out["prose_advisory_zh"] == 800
    assert out.get("presentation")
    assert out.get("session_contract")
    assert out["warm_stdout"] is None
    assert isinstance(out.get("writing_contract"), list)


def test_beat_turn_begin_uses_novel_warm_max_rows(monkeypatch):
    warm_calls: list[list[str]] = []

    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[0] == "query" and argv[1] == "warm":
            warm_calls.append(list(argv))
            return MemNetResponse(
                exit_code=0,
                stdout="@STEP: STEP01|1|SCN01|persistent\n",
                stderr="",
                session_id=session,
                errors=[],
            )
        if argv[0] == "query" and "walk" in argv:
            return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_warm_walk", lambda **kwargs: "")
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_session_modified", lambda s: None)
    beat_turn_begin(session="test")
    assert warm_calls
    main_warm = warm_calls[0]
    assert "--max-rows" in main_warm
    assert main_warm[main_warm.index("--max-rows") + 1] == str(NOVEL_WARM_MAX_ROWS)
    assert main_warm[main_warm.index("--depth") + 1] == str(NOVEL_WARM_DEPTH)
    assert NOVEL_WARM_MAX_ROWS == 150
    assert NOVEL_WARM_DEPTH == 3


def test_beat_turn_begin_no_gate_local_draft(monkeypatch):
    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[0] == "query" and "walk" in argv:
            return MemNetResponse(
                exit_code=0,
                stdout="",
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(
            exit_code=0,
            stdout="@USR: USR05|scene_length|no_gate|persistent\n@STEP: STEP01|1|SCN01|persistent\n",
            stderr="",
            session_id=session,
            errors=[],
        )

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_warm_walk", lambda **kwargs: "")
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_session_modified", lambda s: None)
    out = beat_turn_begin(session="test")
    assert out["pipeline"]["prose_gate"] is False
    assert out["local_draft"] is None
    assert out.get("presentation")


def test_beat_turn_finish_gate_blocked(tmp_path: Path, monkeypatch):
    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_session_modified", lambda s: None)
    result = beat_turn_finish(
        session=None,
        prose="字" * 200,
        chapter_dir="chapters",
        chp_num=1,
        min_chars=650,
        max_chars=950,
        workspace_root=tmp_path,
        pipeline_bypass=True,
        **_pipeline_kwargs(),
    )
    assert result["exit_code"] == 1
    assert result["gate_blocked"] is True
    assert not (tmp_path / "chapters" / "第001回.md").exists()


def test_beat_turn_begin_finish_params():
    p = parse_warm_stdout(WARM_SAMPLE)
    from novel_mcp.beat_pipeline import _finish_params_from_pipeline

    fp = _finish_params_from_pipeline(p)
    assert fp["chapter_dir"] == "novel-output/shenjia_caifa/chapters"
    assert fp["chp_num"] == 1
    assert fp["workspace_root"]


def test_beat_turn_finish_auto_chapter_from_warm(tmp_path: Path, monkeypatch):
    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[0] == "query":
            return MemNetResponse(
                exit_code=0,
                stdout=WARM_SAMPLE,
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setenv("MEMNET_WORKSPACE_ROOT", str(tmp_path))

    result = beat_turn_finish(
        session="test",
        prose="字" * 800,
        **_pipeline_kwargs(),
    )
    assert result["exit_code"] == 0
    assert result["auto_resolved"]["chapter_dir"] == "novel-output/shenjia_caifa/chapters"
    assert result["auto_resolved"]["chp_num"] == 1
    ch_path = tmp_path / "novel-output/shenjia_caifa/chapters/第001回.md"
    assert ch_path.exists()
    assert any(p.get("phase") == "chapter" for p in result["phases"])


def test_beat_turn_finish_time_regress_blocked(tmp_path: Path, monkeypatch):
    warm = """\
@SYS: SYS01|10|1637-09-16T04|0|0|25|1兩=825文銅
@USR: USR05|scene_length|no_gate|persistent
@USR: USR23|beat_stage|oln|persistent
@CHP: CHP01|1|100|1|0|open
@USR: USR14|chapter_out|chapters|persistent
"""

    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[0] == "query":
            return MemNetResponse(
                exit_code=0,
                stdout=warm,
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setenv("MEMNET_WORKSPACE_ROOT", str(tmp_path))

    result = beat_turn_finish(
        session="test",
        prose="字" * 100,
        update_lines=["@SYS: SYS01|11|1637-09-15T04|0|0|25|1兩=825文銅"],
        **_pipeline_kwargs(),
    )
    assert result["exit_code"] == 1
    assert result.get("time_blocked") is True
    assert any("time_regress" in e for e in result["errors"])


def test_beat_turn_finish_chapter_only(tmp_path: Path, monkeypatch):
    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_session_modified", lambda s: None)
    result = beat_turn_finish(
        session=None,
        prose="字" * 800,
        chapter_dir="chapters",
        chp_num=1,
        min_chars=650,
        max_chars=950,
        workspace_root=tmp_path,
        pipeline_bypass=True,
        **_pipeline_kwargs(),
    )
    assert result["exit_code"] == 0
    assert (tmp_path / "chapters" / "第001回.md").exists()
    assert result["chapter"]["file_char_total"] == 800


def test_pipeline_blocks_prose_only(tmp_path: Path):
    result = beat_turn_finish(
        session=None,
        prose="字" * 800,
        chapter_dir="chapters",
        chp_num=1,
        workspace_root=tmp_path,
    )
    assert result["exit_code"] == 1
    assert result.get("pipeline_blocked") is True
    assert any("pipeline_stage_mismatch" in e for e in result["errors"])
    assert not (tmp_path / "chapters" / "第001回.md").exists()


def test_pipeline_full_bundle_advances_stage(tmp_path: Path, monkeypatch):
    warm = "@USR: USR23|beat_stage|oln|persistent\n"

    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[0] == "query":
            return MemNetResponse(
                exit_code=0,
                stdout=warm,
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    result = beat_turn_finish(
        session="test",
        prose="字" * 100,
        chapter_dir="chapters",
        chp_num=1,
        workspace_root=tmp_path,
        pipeline_bypass=False,
        **_pipeline_kwargs(),
    )
    assert result["exit_code"] == 0
    assert result["beat_stage"] == "oln"
    phases = [p["phase"] for p in result["phases"]]
    assert phases.count("oln") == 1
    assert phases.count("sbd") == 1
    assert phases.count("scr") == 1


def test_pipeline_single_oln_advances_to_sbd(monkeypatch):
    warm = "@USR: USR23|beat_stage|oln|persistent\n"

    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[0] == "query":
            return MemNetResponse(
                exit_code=0,
                stdout=warm,
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    result = beat_turn_finish(session="test", oln_lines=OLN_WIRE)
    assert result["exit_code"] == 0
    assert result["beat_stage"] == "sbd"
    assert any(p["phase"] == "update" for p in result["phases"])


def test_pipeline_no_bundle_blocks_multi_wire(monkeypatch):
    warm = (
        "@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|no_bundle|persistent\n"
        "@USR: USR23|beat_stage|oln|persistent\n"
    )

    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[0] == "query":
            return MemNetResponse(
                exit_code=0,
                stdout=warm,
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    result = beat_turn_finish(
        session="test",
        prose="字" * 100,
        pipeline_bypass=False,
        **_pipeline_kwargs(),
    )
    assert result["exit_code"] == 1
    assert result.get("pipeline_blocked") is True
    assert any("pipeline_no_bundle" in e for e in result["errors"])


def test_parse_warm_stdout_pipeline_no_bundle():
    warm = "@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|no_bundle|persistent\n"
    p = parse_warm_stdout(warm)
    assert p["pipeline_no_bundle"] is True
    p2 = parse_warm_stdout(WARM_SAMPLE)
    assert p2.get("pipeline_no_bundle") is False


def test_parse_warm_stdout_beat_stage():
    p = parse_warm_stdout("@USR: USR23|beat_stage|scr|persistent\n")
    assert p["beat_stage"] == "scr"


def test_ensure_beat_stage_update_replaces_same_usr_id():
    from novel_mcp.beat_pipeline import _ensure_beat_stage_update

    out = _ensure_beat_stage_update(
        ["@USR: USR23|beat_stage|prose|persistent", "@STEP: STEP01|5|OLN07|persistent"],
        "oln",
        beat_stage_usr_id="USR23",
    )
    usr_rows = [ln for ln in out if "USR23|beat_stage" in ln]
    assert len(usr_rows) == 1
    assert usr_rows[0] == "@USR: USR23|beat_stage|oln|persistent"
    assert any("STEP01" in ln for ln in out)


def test_prose_finish_advances_usr23_to_oln(tmp_path: Path, monkeypatch):
    """Prose finish must persist beat_stage|oln (not leave USR23 at prose)."""
    stage = {"beat_stage": "prose"}
    updates: list[str] = []

    warm = (
        "@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|no_bundle|persistent\n"
        "@USR: USR23|beat_stage|prose|persistent\n"
        "@USR: USR05|scene_length|650_950_zh|persistent\n"
        "@USR: USR06|chapter_out|novel-output/shenjia_caifa/chapters|persistent\n"
        "@CHP: CHP01|1|0|1|0|open\n"
    )

    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[:2] == ["read", "get"]:
            rid = argv[argv.index("--id") + 1] if "--id" in argv else ""
            if rid == "USR23":
                return MemNetResponse(
                    exit_code=0,
                    stdout=f"@USR: USR23|beat_stage|{stage['beat_stage']}|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            if rid == "LAW-PIPE20":
                return MemNetResponse(
                    exit_code=0,
                    stdout="@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|no_bundle|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])
        if argv[0] == "query":
            return MemNetResponse(
                exit_code=0,
                stdout=warm,
                stderr="",
                session_id=session,
                errors=[],
            )
        if argv[0] == "update" and stdin:
            updates.append(stdin)
            if "beat_stage|oln" in stdin:
                stage["beat_stage"] = "oln"
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setenv("MEMNET_WORKSPACE_ROOT", str(tmp_path))

    result = beat_turn_finish(
        session="test",
        prose="字" * 800,
        option_lines=["一", "二", "三", "四", "五", "六"],
    )
    assert result["exit_code"] == 0
    assert result["beat_stage"] == "oln"
    assert stage["beat_stage"] == "oln"
    assert any("beat_stage|oln" in u for u in updates)


def test_beat_turn_begin_next_action_prose_stage_no_bundle(monkeypatch):
    def fake_run(argv, stdin=None, session=None):
        from memnet_mcp.client import MemNetResponse

        if argv[:2] == ["read", "get"]:
            rid = argv[argv.index("--id") + 1] if "--id" in argv else ""
            if rid == "USR23":
                return MemNetResponse(
                    exit_code=0,
                    stdout="@USR: USR23|beat_stage|prose|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            if rid == "LAW-PIPE20":
                return MemNetResponse(
                    exit_code=0,
                    stdout="@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|no_bundle|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            if rid == "USR57":
                return MemNetResponse(
                    exit_code=0,
                    stdout="@USR: USR57|stage_hint_prose|draft prose|persistent\n",
                    stderr="",
                    session_id=session,
                    errors=[],
                )
            return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])
        if argv[0] == "query":
            return MemNetResponse(
                exit_code=0,
                stdout="@USR: USR23|beat_stage|oln|persistent\n@STEP: STEP01|4|OLN06|persistent\n",
                stderr="",
                session_id=session,
                errors=[],
            )
        return MemNetResponse(exit_code=0, stdout="", stderr="", session_id=session, errors=[])

    monkeypatch.setattr("novel_mcp.beat_pipeline.run_memnet", fake_run)
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_warm_walk", lambda **kwargs: "")
    monkeypatch.setattr("novel_mcp.beat_pipeline.fetch_session_modified", lambda s: "m1")
    out = beat_turn_begin(session="test")
    assert out["pipeline"]["beat_stage"] == "prose"
    assert "prose" in out["pipeline"]["next_action"].lower()
    assert "beat_turn_finish" in out["pipeline"]["next_action"]
