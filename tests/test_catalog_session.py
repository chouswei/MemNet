"""Tests for martial catalog background MemNet session."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from novel_mcp.catalog_session import (
    catalog_schema_key,
    catalog_session_id_file,
    catalog_snapshot_file,
    catalog_store_dir,
    catalog_tag_map_lines,
    link_skill_catalog_session,
    resolve_catalog_session_id,
)
from novel_mcp.skill_catalog_keys import read_skill_catalog_md_rel, read_skill_catalog_session_from_story


def test_catalog_store_paths(wuxia_schema, tmp_path: Path) -> None:
    schema_path = tmp_path / "catalog_specs" / "wuxia_jinyong.json"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_text("{}", encoding="utf-8")
    root = tmp_path / "repo"
    store = catalog_store_dir(schema_path, workspace_root_path=root)
    assert store == root / "novel-output" / "catalogs" / "wuxia_jinyong"
    assert catalog_session_id_file(schema_path, workspace_root_path=root).name == "catalog_session_id.txt"
    assert catalog_snapshot_file(schema_path, workspace_root_path=root).name == "catalog_snap.json"
    assert catalog_schema_key(schema_path) == "wuxia_jinyong"


def test_catalog_tag_map_lines(wuxia_schema) -> None:
    lines = catalog_tag_map_lines(wuxia_schema)
    assert lines[0].startswith("@ART:")
    assert "名稱" in lines[0]
    assert lines[1].startswith("@CFG:")


def test_resolve_catalog_session_id_from_story_usr(wuxia_schema) -> None:
    with patch("novel_mcp.skill_catalog_keys.read_usr_by_key", return_value="mn_cat01"):
        sid = resolve_catalog_session_id("mn_story", wuxia_schema)
    assert sid == "mn_cat01"


def test_resolve_catalog_session_id_from_store_file(wuxia_schema, tmp_path: Path) -> None:
    schema_path = tmp_path / "wuxia_jinyong.json"
    schema_path.write_text("{}", encoding="utf-8")
    id_file = catalog_session_id_file(schema_path, workspace_root_path=tmp_path)
    id_file.parent.mkdir(parents=True, exist_ok=True)
    id_file.write_text("mn_file99\n", encoding="utf-8")
    with patch("novel_mcp.skill_catalog_keys.read_usr_by_key", return_value=None):
        sid = resolve_catalog_session_id(
            None,
            wuxia_schema,
            schema_path=schema_path,
            workspace_root_path=tmp_path,
        )
    assert sid == "mn_file99"


def test_resolve_catalog_session_id_legacy_martial_key(wuxia_schema) -> None:
    with patch(
        "novel_mcp.skill_catalog_keys.read_usr_by_key",
        side_effect=lambda _s, key: "mn_legacy" if key == "martial_catalog_session" else None,
    ):
        sid = read_skill_catalog_session_from_story("mn_story")
    assert sid == "mn_legacy"


def test_read_skill_catalog_md_legacy_key() -> None:
    with patch(
        "novel_mcp.skill_catalog_keys.read_usr_by_key",
        side_effect=lambda _s, key: "catalog.md" if key == "martial_catalog_md" else None,
    ):
        rel = read_skill_catalog_md_rel("mn_story")
    assert rel == "catalog.md"


def test_link_skill_catalog_session() -> None:
    with patch(
        "novel_mcp.catalog_session.ensure_usr_row",
        return_value="USR80",
    ), patch(
        "novel_mcp.catalog_session.graph_update",
        return_value=(0, []),
    ):
        out = link_skill_catalog_session("mn_story", "mn_cat")
    assert out["exit_code"] == 0
    assert out["catalog_session"] == "mn_cat"
