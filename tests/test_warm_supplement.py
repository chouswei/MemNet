"""Tests for novel RPG warm enrichment (not memnet core)."""

from __future__ import annotations

from memnet_mcp.client import MemNetResponse
from novel_mcp.warm_supplement import enrich_warm_stdout


def test_enrich_oln_stage_skips_sbd_scr(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run(argv, stdin=None, session=None):
        if argv[:3] == ["read", "list", "--tag"]:
            calls.append(argv[3])
        return MemNetResponse(0, "", "", session, [])

    monkeypatch.setattr("novel_mcp.warm_supplement.run_memnet", fake_run)
    warm = "@STEP: STEP01|1|SCN01|persistent\n"
    enrich_warm_stdout("mn_x", warm, beat_stage="script_draft")
    assert "SBD" not in calls
    assert "SCR" not in calls


def test_enrich_passthrough_without_session() -> None:
    warm = "@STEP: STEP01|1|SCN01|persistent\n"
    assert enrich_warm_stdout(None, warm) == warm


def test_enrich_adds_missing_tags(monkeypatch) -> None:
    def fake_run(argv, stdin=None, session=None):
        if argv[:3] == ["read", "list", "--tag"]:
            tag = argv[3]
            bodies = {
                "OLN": "@OLN: OLN01|1|魂穿|匠坊|对白|钩|delete_on_settle",
                "SCR": (
                    "@SCR: SCR01|1|1|动作|对白|内心|音效|delete_on_settle\n"
                    "@SCR: SCR02|1|2|动作2|对白2|内心2|音效2|delete_on_settle"
                ),
                "NPC": "@NPC: N01|小美|1625|女|0|土法|sk|it|0|常駐|常駐",
            }
            return MemNetResponse(0, bodies.get(tag, ""), "", session, [])
        return MemNetResponse(2, "", "", session, [])

    monkeypatch.setattr("novel_mcp.warm_supplement.run_memnet", fake_run)
    warm = "@STEP: STEP01|1|SCN01|persistent\n@USR: USR23|beat_stage|prose|persistent\n"
    out = enrich_warm_stdout("mn_x", warm)
    assert "@OLN: OLN01|1|" in out
    assert "@SCR: SCR01|1|1|" in out
    assert "@SCR: SCR02|1|2|" in out
    assert "@NPC: N01|小美|" in out


def test_enrich_skips_tags_already_in_warm(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run(argv, stdin=None, session=None):
        if argv[:3] == ["read", "list", "--tag"]:
            calls.append(argv[3])
        return MemNetResponse(0, "", "", session, [])

    monkeypatch.setattr("novel_mcp.warm_supplement.run_memnet", fake_run)
    warm = "@OLN: OLN01|1|已有|匠坊|对白|钩|delete_on_settle\n"
    enrich_warm_stdout("mn_x", warm)
    assert "OLN" not in calls


def test_enrich_fetches_when_only_tag_map_def_present(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run(argv, stdin=None, session=None):
        if argv[:3] == ["read", "list", "--tag"]:
            tag = argv[3]
            calls.append(tag)
            if tag == "OLN":
                return MemNetResponse(
                    0,
                    "@OLN: OLN01|1|魂穿|匠坊|对白|钩|delete_on_settle",
                    "",
                    session,
                    [],
                )
        return MemNetResponse(0, "", "", session, [])

    monkeypatch.setattr("novel_mcp.warm_supplement.run_memnet", fake_run)
    warm = "@OLN: id|回合|情緒錨|情節要點|對白骨架|尾鉤|回收\n"
    out = enrich_warm_stdout("mn_x", warm)
    assert "OLN" in calls
    assert "@OLN: OLN01|1|" in out


def test_enrich_adds_aff_to_for_cast_in_warm(monkeypatch) -> None:
    aff_line = "@EDG: EAFF01|P01|aff_to|N01||親密度:35;信任度:60;敬重:50;備註:姐弟|常駐"
    other_edg = "@EDG: E99|B01|hiring|P01|待聘|失效刪"

    def fake_run(argv, stdin=None, session=None):
        if argv[:3] == ["read", "list", "--tag"]:
            tag = argv[3]
            if tag == "EDG":
                return MemNetResponse(0, aff_line + "\n" + other_edg, "", session, [])
            return MemNetResponse(0, "", "", session, [])
        return MemNetResponse(2, "", "", session, [])

    monkeypatch.setattr("novel_mcp.warm_supplement.run_memnet", fake_run)
    warm = "@PLR: P01|流民|1627|0|0||\n@NPC: N01|沈芯|1625|聰慧|0||||0|常駐\n"
    out = enrich_warm_stdout("mn_x", warm, beat_stage="prose")
    assert aff_line in out
    assert other_edg not in out


def test_enrich_supplements_hud_usr_config(monkeypatch) -> None:
    def fake_run(argv, stdin=None, session=None):
        if argv[:3] == ["read", "list", "--tag"]:
            tag = argv[3]
            if tag == "USR":
                return MemNetResponse(
                    0,
                    "@USR: USR45|body_plot|氣血;內力;飽食;oln;prose|persistent\n"
                    "@USR: USR02|hud_pipe|qi_neili_wux_datetime|persistent\n"
                    "@USR: USR43|game_time|axis=iso;display=chongzhen_shichen|persistent\n",
                    "",
                    session,
                    [],
                )
            if tag == "PLR":
                return MemNetResponse(
                    0,
                    "@PLR: P01|流民|1627|未定|0|0|bag|氣血:6/6|內力:6/6|飽食:略飽",
                    "",
                    session,
                    [],
                )
            if tag == "SYS":
                return MemNetResponse(
                    0,
                    "@SYS: SYS01|1|1628-01-01T06|0|0|25|fx",
                    "",
                    session,
                    [],
                )
        return MemNetResponse(0, "", "", session, [])

    monkeypatch.setattr("novel_mcp.warm_supplement.run_memnet", fake_run)
    warm = "@STEP: STEP01|1|SCN01|persistent\n@USR: USR23|beat_stage|prose|persistent\n"
    out = enrich_warm_stdout("mn_x", warm, beat_stage="prose")
    assert "body_plot|氣血" in out
    assert "hud_pipe|qi_neili" in out
    assert "game_time|axis=iso" in out

    from novel_mcp.beat_pipeline import parse_warm_stdout
    from novel_mcp.presentation import compile_presentation

    pipeline = parse_warm_stdout(out)
    pres = compile_presentation(out, pipeline, session="mn_x")
    assert pres["body_plot_keys"] == ["氣血", "內力", "飽食"]
    assert pres["hud_pipe"]
    assert pres["scene"].get("plr_body")
    assert pipeline.get("time_display")


def test_enrich_skips_aff_to_when_no_cast_ids(monkeypatch) -> None:
    edg_calls = 0

    def fake_run(argv, stdin=None, session=None):
        nonlocal edg_calls
        if argv[:3] == ["read", "list", "--tag"] and argv[3] == "EDG":
            edg_calls += 1
            return MemNetResponse(
                0,
                "@EDG: EAFF01|P01|aff_to|N01||親密度:35|常駐",
                "",
                session,
                [],
            )
        return MemNetResponse(0, "", "", session, [])

    monkeypatch.setattr("novel_mcp.warm_supplement.run_memnet", fake_run)
    warm = "@STEP: STEP01|1|SCN01|persistent\n"
    out = enrich_warm_stdout("mn_x", warm)
    assert edg_calls == 0
    assert "aff_to" not in out
