"""Beat FSM stage names and legacy normalisation."""

from __future__ import annotations

PIPELINE_STAGES = ("script_draft", "script_review", "prose")

STAGE_NEXT: dict[str, str] = {
    "script_draft": "script_review",
    "script_review": "prose",
    "prose": "script_draft",
}

_LEGACY_STAGE_MAP: dict[str, str] = {
    "oln": "script_draft",
    "sbd": "script_draft",
    "scr": "script_review",
    "script_draft": "script_draft",
    "script_review": "script_review",
    "prose": "prose",
}

SCRIPT_STAGES = frozenset({"script_draft", "script_review"})

STAGE_HINT_USR: dict[str, str] = {
    "script_draft": "USR55",
    "script_review": "USR56",
    "prose": "USR57",
}


def normalize_beat_stage(stage: str | None) -> str:
    """Map legacy oln/sbd/scr and unknown values to current FSM stages."""
    key = (stage or "").strip()
    return _LEGACY_STAGE_MAP.get(key, "script_draft")


def is_script_law_stage(stage: str) -> bool:
    return normalize_beat_stage(stage) in SCRIPT_STAGES
