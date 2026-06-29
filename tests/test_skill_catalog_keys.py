"""Tests for generic skill-catalog USR key resolution."""

from __future__ import annotations

from unittest.mock import patch

from novel_mcp.skill_catalog_keys import (
    read_skill_catalog_md_rel,
    read_skill_catalog_session_from_story,
)


def test_read_skill_catalog_md_prefers_canonical_key() -> None:
    def fake_read(_session: str, key: str) -> str | None:
        return {
            "skill_catalog_md": "skill.md",
            "martial_catalog_md": "martial.md",
        }.get(key)

    with patch("novel_mcp.skill_catalog_keys.read_usr_by_key", side_effect=fake_read):
        assert read_skill_catalog_md_rel("mn_x") == "skill.md"


def test_read_skill_catalog_session_prefers_canonical_key() -> None:
    def fake_read(_session: str, key: str) -> str | None:
        return {
            "skill_catalog_session": "mn_skill",
            "martial_catalog_session": "mn_martial",
        }.get(key)

    with patch("novel_mcp.skill_catalog_keys.read_usr_by_key", side_effect=fake_read):
        assert read_skill_catalog_session_from_story("mn_x") == "mn_skill"
