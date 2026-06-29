"""Tests for PLR body state HUD and LAW-VIT01 checks."""

from __future__ import annotations

from novel_mcp.body_state import (
    effective_plr_body,
    format_beat_hud,
    hud_keys_from_body_plot,
    parse_body_fields,
    plr_update_downgrade_satiety,
    resolve_beat_hud,
    vitality_satiety_conflict,
)


def test_hud_keys_from_body_plot() -> None:
    raw = "氣血;內力;疲勞;飽食;oln;prose;opt;delta"
    assert hud_keys_from_body_plot(raw) == ["氣血", "內力", "疲勞", "飽食"]


def test_parse_body_fields() -> None:
    body = "氣血:6/6；內力:0/4；飽食:略飽；疲勞:0"
    f = parse_body_fields(body)
    assert f["飽食"] == "略飽"
    assert f["氣血"] == "6/6"


def test_format_beat_hud_seed_keys() -> None:
    body = "氣血:6/6；內力:0/4；飽食:略飽；疲勞:0；內功:未入門"
    keys = ["氣血", "內力", "飽食", "疲勞"]
    hud = format_beat_hud(
        body,
        hud_keys=keys,
        hud_pipe="qi_neili_wux_datetime",
        time_display="丑時三刻",
    )
    assert "飽食:略飽" in hud
    assert "內功" not in hud
    assert "丑時三刻" in hud


def test_format_beat_hud_llm_fallback() -> None:
    hud = format_beat_hud("", llm_fallback="HP:12｜MP:3")
    assert hud == "HP:12｜MP:3"


def test_format_beat_hud_generic_world() -> None:
    body = "HP:12/20；MP:3/8；魂穿:現代工程師"
    hud = format_beat_hud(body, hud_keys=[])
    assert "HP:12/20" in hud
    assert "魂穿" not in hud


def test_resolve_beat_hud_after_plr_update() -> None:
    begin = "氣血:6/6；飽食:略飽；疲勞:0"
    updates = [
        "@PLR: P01|流民|1627|男|0|0|技能|氣血:5/6；飽食:略餓；疲勞:1"
    ]
    hud = resolve_beat_hud(
        plr_body=begin,
        update_lines=updates,
        hud_keys=["氣血", "飽食", "疲勞"],
    )
    assert "飽食:略餓" in hud
    assert "略飽" not in hud


def test_vitality_satiety_skipped_without_body_plot() -> None:
    body = "氣血:6/6；飽食:略飽；疲勞:0"
    err = vitality_satiety_conflict(
        "你肚子很餓，腹中空鳴不止。",
        body,
        body_plot_keys=["HP", "MP"],
    )
    assert err is None


def test_vitality_satiety_conflict_slightly_full() -> None:
    body = "氣血:6/6；飽食:略飽；疲勞:0"
    err = vitality_satiety_conflict(
        "你肚子很餓，腹中空鳴不止。",
        body,
        body_plot_keys=["飽食"],
    )
    assert err is not None
    assert "略飽" in err


def test_vitality_satiety_conflict_ok_hungry() -> None:
    body = "氣血:6/6；飽食:飢餓；疲勞:0"
    err = vitality_satiety_conflict(
        "腹中空鳴，你餓得發慌。",
        body,
        body_plot_keys=["飽食"],
    )
    assert err is None


def test_effective_plr_body_from_update() -> None:
    begin = "氣血:6/6；飽食:略飽；疲勞:0"
    updates = ["@PLR: P01|流民|1627|男|0|0|技能|氣血:5/6；飽食:略餓；疲勞:1"]
    assert "略餓" in effective_plr_body(begin, updates)


def test_vitality_ok_when_update_lowers_satiety() -> None:
    body = "氣血:6/6；飽食:略飽；疲勞:0"
    updates = ["@PLR: P01|流民|1627|男|0|0|技能|氣血:5/6；飽食:略餓；疲勞:1"]
    err = vitality_satiety_conflict(
        "腹中微微空鳴，你略覺餓意。",
        body,
        body_plot_keys=["飽食"],
        update_lines=updates,
    )
    assert err is None


def test_plr_update_downgrade_satiety() -> None:
    parts = [
        "P01",
        "流民",
        "1627",
        "男",
        "0",
        "0",
        "靈魂圖書館登峰造極",
        "氣血:6/6；飽食:略飽；疲勞:0",
    ]
    wire = plr_update_downgrade_satiety(parts)
    assert wire is not None
    assert "飽食:略餓" in wire
    assert wire.startswith("@PLR:")
