"""PLR body-state parsing, seed-driven beat HUD, and optional LAW-VIT01 checks."""

from __future__ import annotations

import re
from typing import Any

from novel_mcp.character_gender import PLR_IDX_BODY, normalise_plr_parts

# USR45 body_plot meta tokens — not HUD / vitals keys.
_BODY_PLOT_META = frozenset({"oln", "prose", "opt", "delta"})

_SATIETY_RANK: dict[str, int] = {
    "極餓": 0,
    "飢餓": 1,
    "略餓": 2,
    "略飽": 3,
    "飽": 4,
    "飽腹": 4,
}

_STRONG_HUNGER = re.compile(
    r"餓得發慌|餓極|非常餓|很餓|飢餓難耐|飢腸轆轆|腹中空鳴|肚子餓得|餓昏|餓到|餓得慌"
)
_MILD_HUNGER = re.compile(r"略餓|有點餓|微微餓|肚子叫|腹中空|胃裡空|空腹")

_WUX_BODY_KEYS = ("內功", "武學", "輕功")


def hud_keys_from_body_plot(usr_value: str | None) -> list[str]:
    """Vitals keys from `@USR|body_plot|氣血;內力;…;oln;prose` (seed SSOT)."""
    if not usr_value:
        return []
    return [
        part.strip()
        for part in usr_value.split(";")
        if part.strip() and part.strip() not in _BODY_PLOT_META
    ]


def parse_body_fields(body: str) -> dict[str, str]:
    """Parse `key:val` segments from @PLR body column."""
    fields: dict[str, str] = {}
    if not body:
        return fields
    for part in re.split(r"[；;]", body):
        chunk = part.strip()
        if ":" not in chunk:
            continue
        key, val = chunk.split(":", 1)
        fields[key.strip()] = val.strip()
    return fields


def satiety_guidance(satiety: str) -> str:
    """Author-facing hint when USR45 lists 飽食 (LAW-VIT01)."""
    guides = {
        "略飽": "腹中尚可；禁空鳴、很餓、飢腸轆轆等強烈飢餓描寫",
        "飽": "不餓；禁饑餓描寫",
        "略餓": "可寫輕微空腹、腹鳴",
        "飢餓": "須寫明顯飢餓感",
        "極餓": "須寫強烈飢餓、乏力、眼冒金星",
    }
    return guides.get(satiety, "")


def plr_body_from_update_lines(update_lines: list[str]) -> str | None:
    """Extract body-state column from @PLR update wires (post-finish_delta)."""
    for raw in update_lines:
        line = raw.strip()
        if not line.startswith("@PLR:"):
            continue
        body = line.split(":", 1)[1].strip()
        parts = normalise_plr_parts(body.split("|"))
        if len(parts) > PLR_IDX_BODY:
            return parts[PLR_IDX_BODY]
        if len(parts) >= 7:
            return parts[6]
    return None


def _wux_hud_bits(fields: dict[str, str], hud_pipe: str | None) -> list[str]:
    """Optional 內功/武學/輕功 when USR02 hud_pipe contains `wux`."""
    if not hud_pipe or "wux" not in hud_pipe:
        return []
    bits: list[str] = []
    for key in _WUX_BODY_KEYS:
        val = fields.get(key)
        if val and val != "未入門":
            bits.append(f"{key}:{val}")
    return bits


def _generic_hud_bits(fields: dict[str, str]) -> list[str]:
    """Fallback when seed has no body_plot keys: short scalar segments only."""
    bits: list[str] = []
    for key, val in fields.items():
        if len(val) > 40 or key.startswith("魂"):
            continue
        bits.append(f"{key}:{val}")
    return bits


def format_beat_hud(
    body: str,
    *,
    hud_keys: list[str] | None = None,
    hud_pipe: str | None = None,
    time_display: str | None = None,
    llm_fallback: str | None = None,
) -> str:
    """One-line HUD from @PLR body per seed USR45 / USR02; else LLM fallback."""
    fields = parse_body_fields(body)
    bits: list[str] = []
    keys = hud_keys or []
    if keys:
        for key in keys:
            if key in fields:
                bits.append(f"{key}:{fields[key]}")
        bits.extend(_wux_hud_bits(fields, hud_pipe))
    elif fields:
        bits = _generic_hud_bits(fields)
    if hud_pipe and "datetime" in hud_pipe and time_display:
        bits.append(time_display)
    elif time_display and not hud_pipe:
        bits.append(time_display)
    hud = "｜".join(bits)
    if not hud and llm_fallback:
        return llm_fallback.strip()
    return hud


def resolve_beat_hud(
    *,
    plr_body: str,
    update_lines: list[str] | None = None,
    hud_keys: list[str] | None = None,
    hud_pipe: str | None = None,
    time_display: str | None = None,
    llm_fallback: str | None = None,
) -> str:
    """HUD after optional finish_delta @PLR update."""
    body = plr_body_from_update_lines(update_lines or []) or plr_body
    return format_beat_hud(
        body,
        hud_keys=hud_keys,
        hud_pipe=hud_pipe,
        time_display=time_display,
        llm_fallback=llm_fallback,
    )


def vitality_satiety_conflict(
    prose: str,
    plr_body: str,
    *,
    body_plot_keys: list[str] | None = None,
) -> str | None:
    """LAW-VIT01 check — only when seed body_plot includes 飽食."""
    keys = body_plot_keys or []
    if keys and "飽食" not in keys:
        return None
    satiety = parse_body_fields(plr_body).get("飽食")
    if not satiety:
        return None
    rank = _SATIETY_RANK.get(satiety)
    if rank is None:
        return None
    if rank >= 3:
        if _STRONG_HUNGER.search(prose):
            return (
                f"LAW-VIT01: @PLR 飽食為「{satiety}」，正文禁寫強烈飢餓"
                f"（{satiety_guidance(satiety)}）。若本拍確實耗損，須在 update_lines 落盤 @PLR。"
            )
        if _MILD_HUNGER.search(prose):
            return (
                f"LAW-VIT01: @PLR 飽食為「{satiety}」，正文不宜寫空腹／腹鳴。"
                f" {satiety_guidance(satiety)}"
            )
    return None


def vitality_block(plr_body: str, *, body_plot_keys: list[str] | None = None) -> str:
    """Markdown block for prose agent when seed governs body-in-plot."""
    if not plr_body:
        return ""
    keys = body_plot_keys or []
    if keys and not any(k in keys for k in ("飽食", "氣血", "內力", "疲勞")):
        return ""
    fields = parse_body_fields(plr_body)
    satiety = fields.get("飽食", "")
    guide = satiety_guidance(satiety) if satiety and "飽食" in keys else ""
    lines = [f"Graph body (match at beat start): `{plr_body}`"]
    if guide:
        lines.append(f"飽食「{satiety}」: {guide}")
    return "## Body state\n" + "\n".join(lines) + "\n\n"


def hud_config_from_presentation(presentation: dict[str, Any]) -> tuple[list[str], str | None]:
    """(body_plot_keys, hud_pipe) from beat_turn_begin presentation envelope."""
    keys = presentation.get("body_plot_keys")
    if isinstance(keys, list):
        plot_keys = [str(k) for k in keys]
    else:
        plot_keys = hud_keys_from_body_plot(presentation.get("body_plot"))
    pipe = presentation.get("hud_pipe")
    return plot_keys, str(pipe) if pipe else None
