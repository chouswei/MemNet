"""Generic skill-catalog USR keys (武學／魔法／異能等 — instance defines sub-types via catalog_schema)."""

from __future__ import annotations

from novel_mcp.setup_constants import SENTINEL
from novel_mcp.setup_graph import read_usr_by_key

# Canonical keys for new seeds; martial_* kept for 沈家 and other legacy instances.
SKILL_CATALOG_MD_KEY = "skill_catalog_md"
SKILL_CATALOG_SESSION_KEY = "skill_catalog_session"
LEGACY_CATALOG_MD_KEY = "martial_catalog_md"
LEGACY_CATALOG_SESSION_KEY = "martial_catalog_session"

CATALOG_MD_USR_KEYS: tuple[str, ...] = (
    SKILL_CATALOG_MD_KEY,
    LEGACY_CATALOG_MD_KEY,
)
CATALOG_SESSION_USR_KEYS: tuple[str, ...] = (
    SKILL_CATALOG_SESSION_KEY,
    LEGACY_CATALOG_SESSION_KEY,
)


def read_skill_catalog_md_rel(session: str | None) -> str | None:
    """Return repo-relative path to skill catalog seed md, if wired on story graph."""
    if not session:
        return None
    for key in CATALOG_MD_USR_KEYS:
        raw = read_usr_by_key(session, key)
        if raw and raw not in (SENTINEL, "_", "-"):
            return raw.strip()
    return None


def read_skill_catalog_session_from_story(session: str | None) -> str | None:
    """Return mn_… id of background catalog session linked from story USR."""
    if not session:
        return None
    for key in CATALOG_SESSION_USR_KEYS:
        raw = read_usr_by_key(session, key)
        if raw and raw not in (SENTINEL, "_", "-") and raw.startswith("mn_"):
            return raw.strip()
    return None
