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
    enrich_warm_stdout("mn_x", warm, beat_stage="oln")
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
