"""Per-world game slot — MemNet session, threads, chapters under novel-output/<app>/worlds/."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from app_config import NovelAppConfig

WORLD_ID_HEADER = "X-Novel-World-Id"
USER_ID_HEADER = "X-Novel-User-Id"
# Legacy alias (tests / old clients)
PLAYER_ID_HEADER = WORLD_ID_HEADER

_SLOT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{7,63}$")


def normalise_world_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    wid = raw.strip()
    if not wid:
        return None
    if not _SLOT_ID_RE.match(wid):
        raise ValueError("invalid world id")
    return wid


def normalise_user_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    uid = raw.strip()
    if not uid:
        return None
    if not _SLOT_ID_RE.match(uid):
        raise ValueError("invalid user id")
    return uid


def worlds_base_dir(base: NovelAppConfig) -> Path:
    return base.output_dir / "worlds"


def world_root(base: NovelAppConfig, world_id: str) -> NovelAppConfig:
    """Paths for one player-created world (MemNet session + agent threads)."""
    wroot = base.output_dir / "worlds" / world_id
    return replace(
        base,
        output_dir=wroot,
        chapter_dir=wroot / "chapters",
        snapshot_file=wroot / "session_snap.json",
        session_id_file=wroot / "session_id.txt",
        last_beat_file=wroot / "last_beat.json",
        agents_dir=wroot / "agents",
    )


def resolve_config(base: NovelAppConfig, world_id: str | None) -> NovelAppConfig:
    if world_id:
        return world_root(base, world_id)
    return base
