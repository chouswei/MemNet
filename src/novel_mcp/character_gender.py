"""PLR/NPC field indices and legacy wire normalisation."""

from __future__ import annotations

import re
from typing import Any

from novel_mcp.setup_constants import SENTINEL

PLR_IDX_IDENTITY = 1
PLR_IDX_BIRTH = 2
PLR_IDX_GENDER = 3
PLR_IDX_WEALTH = 4
PLR_IDX_CASHFLOW = 5
PLR_IDX_CORE = 6
PLR_IDX_BODY = 7
PLR_FIELD_COUNT = 8

NPC_IDX_NAME = 1
NPC_IDX_BIRTH = 2
NPC_IDX_GENDER = 3
NPC_IDX_APPEARANCE = 4
NPC_IDX_PERSONALITY = 5
NPC_IDX_VOICE = 6
NPC_IDX_TRAITS = 7
NPC_IDX_CORRUPTION = 8
NPC_IDX_CRAFT = 9
NPC_IDX_SKILLS = 10
NPC_IDX_ITEMS = 11
NPC_IDX_FUNDING = 12
NPC_IDX_STATUS = 13
NPC_IDX_RECYCLE = 14
NPC_FIELD_COUNT = 15

_GENDER_PREFIX_RE = re.compile(r"^(男|女)[、,，]")
_BODY_GENDER_RE = re.compile(r"性別:[^；;]+")
_KNOWN_GENDERS = frozenset({"男", "女", "未定"})
_TRAIT_SEP_RE = re.compile(r"[、,，;；]")

_APPEARANCE_TOKENS = frozenset(
    {"美貌", "滿臉炭灰", "清秀", "彪壯", "瘦削", "高大", "矮小", "疤臉", "虯髯"}
)
_PERSONALITY_TOKENS = frozenset(
    {
        "聰慧",
        "堅韌",
        "溫柔",
        "慾念",
        "狡黠",
        "大膽",
        "開放",
        "沉穩",
        "急躁",
        "內向",
        "豪爽",
        "陰狠",
    }
)
_VOICE_TOKENS = frozenset(
    {"沉穩簡約", "潑辣帶笑", "伶牙俐齒", "寡言", "文绉绉", "粗豪直率", "軟語", "尖刻"}
)


def strip_gender_from_body(body_state: str) -> str:
    if not body_state:
        return body_state
    cleaned = _BODY_GENDER_RE.sub("", body_state)
    cleaned = re.sub(r"[；;]{2,}", "；", cleaned)
    return cleaned.strip("；; ")


def gender_from_body(body_state: str) -> str | None:
    if not body_state:
        return None
    m = re.search(r"性別:([^；;]+)", body_state)
    if not m:
        return None
    val = m.group(1).strip()
    return val if val in _KNOWN_GENDERS else val or None


def split_traits_gender(traits: str) -> tuple[str, str]:
    if not traits:
        return "未定", traits
    m = _GENDER_PREFIX_RE.match(traits)
    if m:
        rest = traits[m.end() :].lstrip("、,， ")
        return m.group(1), rest
    return "未定", traits


def _join_tokens(tokens: list[str]) -> str:
    return "、".join(t for t in tokens if t)


def split_npc_trait_blob(blob: str) -> tuple[str, str, str, str]:
    """Split legacy single NPC trait column into appearance/personality/voice/identity."""
    if not blob or blob in (SENTINEL, "-", "_"):
        return "", "", "", ""
    tokens = [t.strip() for t in _TRAIT_SEP_RE.split(blob) if t.strip()]
    appearance: list[str] = []
    personality: list[str] = []
    voice: list[str] = []
    identity: list[str] = []
    for token in tokens:
        if token in _VOICE_TOKENS:
            voice.append(token)
        elif token in _APPEARANCE_TOKENS:
            appearance.append(token)
        elif token in _PERSONALITY_TOKENS:
            personality.append(token)
        else:
            identity.append(token)
    return (
        _join_tokens(appearance),
        _join_tokens(personality),
        _join_tokens(voice),
        _join_tokens(identity),
    )


def normalise_plr_parts(parts: list[str]) -> list[str]:
    if len(parts) >= PLR_FIELD_COUNT:
        out = list(parts[:PLR_FIELD_COUNT])
        orig_body = out[PLR_IDX_BODY]
        out[PLR_IDX_BODY] = strip_gender_from_body(orig_body)
        if not out[PLR_IDX_GENDER] or out[PLR_IDX_GENDER] in (SENTINEL, "-"):
            out[PLR_IDX_GENDER] = gender_from_body(orig_body) or "未定"
        return out
    if len(parts) == 7:
        body = strip_gender_from_body(parts[6])
        gender = gender_from_body(parts[6]) or "未定"
        return [
            parts[0],
            parts[1],
            parts[2],
            gender,
            parts[3],
            parts[4],
            parts[5],
            body,
        ]
    return parts


def normalise_npc_parts(parts: list[str]) -> list[str]:
    if len(parts) >= NPC_FIELD_COUNT:
        out = list(parts[:NPC_FIELD_COUNT])
        while len(out) < NPC_FIELD_COUNT:
            out.append("")
        if not out[NPC_IDX_GENDER] or out[NPC_IDX_GENDER] in (SENTINEL, "-"):
            gender, blob = split_traits_gender(out[NPC_IDX_APPEARANCE])
            if gender != "未定":
                out[NPC_IDX_GENDER] = gender
                app, pers, voice, traits = split_npc_trait_blob(blob)
                if not out[NPC_IDX_PERSONALITY]:
                    out[NPC_IDX_PERSONALITY] = pers
                if not out[NPC_IDX_VOICE]:
                    out[NPC_IDX_VOICE] = voice
                if not out[NPC_IDX_TRAITS]:
                    out[NPC_IDX_TRAITS] = traits
                out[NPC_IDX_APPEARANCE] = app or blob
        return out
    if len(parts) >= 12:
        gender = parts[3] if len(parts) > 3 else "未定"
        blob = parts[4] if len(parts) > 4 else ""
        if gender in ("", SENTINEL, "-") or gender in _PERSONALITY_TOKENS | _APPEARANCE_TOKENS:
            gender, blob = split_traits_gender(blob if gender in _KNOWN_GENDERS else parts[3])
        app, pers, voice, traits = split_npc_trait_blob(blob)
        tail = parts[5:12] if len(parts) >= 12 else parts[5:]
        while len(tail) < 7:
            tail.append("")
        return [
            parts[0],
            parts[1],
            parts[2],
            gender,
            app,
            pers,
            voice,
            traits,
            *tail[:7],
        ]
    if len(parts) >= 11:
        gender, blob = split_traits_gender(parts[3])
        app, pers, voice, traits = split_npc_trait_blob(blob)
        tail = parts[4:11]
        while len(tail) < 7:
            tail.append("")
        return [parts[0], parts[1], parts[2], gender, app, pers, voice, traits, *tail[:7]]
    return parts


def plr_body_index(parts: list[str]) -> int:
    return PLR_IDX_BODY if len(parts) >= PLR_FIELD_COUNT else 6


def plr_gender(parts: list[str], *, usr_gender: str | None = None) -> str:
    norm = normalise_plr_parts(parts)
    if len(norm) > PLR_IDX_GENDER and norm[PLR_IDX_GENDER] not in ("", SENTINEL, "-"):
        return norm[PLR_IDX_GENDER]
    if usr_gender and usr_gender not in ("", SENTINEL, "-"):
        return usr_gender
    return "未定"


def npc_gender(parts: list[str]) -> str:
    norm = normalise_npc_parts(parts)
    if len(norm) > NPC_IDX_GENDER and norm[NPC_IDX_GENDER] not in ("", SENTINEL, "-"):
        return norm[NPC_IDX_GENDER]
    return "未定"


def _npc_field(parts: list[str], index: int) -> str:
    norm = normalise_npc_parts(parts)
    if len(norm) > index:
        return norm[index] or ""
    return ""


def npc_appearance(parts: list[str]) -> str:
    return _npc_field(parts, NPC_IDX_APPEARANCE)


def npc_personality(parts: list[str]) -> str:
    return _npc_field(parts, NPC_IDX_PERSONALITY)


def npc_voice(parts: list[str]) -> str:
    return _npc_field(parts, NPC_IDX_VOICE)


def npc_traits(parts: list[str]) -> str:
    return _npc_field(parts, NPC_IDX_TRAITS)


def npc_profile(parts: list[str]) -> dict[str, str]:
    return {
        "gender": npc_gender(parts),
        "appearance": npc_appearance(parts),
        "personality": npc_personality(parts),
        "voice": npc_voice(parts),
        "traits": npc_traits(parts),
    }


def npc_presentation_entry(parts: list[str]) -> dict[str, Any]:
    profile = npc_profile(parts)
    entry: dict[str, Any] = {
        "id": parts[0] if parts else "",
        "name": parts[NPC_IDX_NAME] if len(parts) > NPC_IDX_NAME else "",
    }
    for key, val in profile.items():
        if val and val != "未定":
            entry[key] = val
    return entry


def format_plr_wire(parts: list[str]) -> str:
    norm = normalise_plr_parts(parts)
    if len(norm) < PLR_FIELD_COUNT:
        raise ValueError(f"PLR needs {PLR_FIELD_COUNT} fields, got {len(norm)}")
    return "@PLR: " + "|".join(norm[:PLR_FIELD_COUNT])
