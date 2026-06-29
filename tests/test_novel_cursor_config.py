"""Tests for generic novel_cursor app config."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOVEL_CURSOR = ROOT / "applications" / "novel_cursor"
sys.path.insert(0, str(NOVEL_CURSOR))

from app_config import RESULT_MARKER, load_config, repo_root  # noqa: E402


def test_result_marker_is_generic() -> None:
    assert RESULT_MARKER == "NOVEL_BEAT_RESULT"


def test_load_instance_config() -> None:
    cfg = load_config(app_id="shenjia_caifa")
    assert cfg.app_id == "shenjia_caifa"
    assert cfg.title == "工匠傳奇"
    assert cfg.seed_md == repo_root() / "application-notes/novel-shenjia-initial-state.md"
    assert cfg.output_dir == repo_root() / "novel-output/shenjia_caifa"
    assert cfg.snapshot_file == repo_root() / "novel-output/shenjia_caifa/session_snap.json"
    assert cfg.chapter_dir == repo_root() / "novel-output/shenjia_caifa/chapters"
    assert cfg.session_id_file == repo_root() / "novel-output/shenjia_caifa/session_id.txt"
    assert cfg.last_beat_file == repo_root() / "novel-output/shenjia_caifa/last_beat.json"
    assert cfg.agents_dir == repo_root() / "novel-output/shenjia_caifa/agents"
    assert cfg.script_agent_id_file.name == "script_agent_id.txt"
    assert cfg.catalog_store_dir == repo_root() / "novel-output/catalogs/wuxia_jinyong"
    assert cfg.catalog_session_id_file == cfg.catalog_store_dir / "catalog_session_id.txt"


def test_list_story_instances_includes_shenjia() -> None:
    from app_config import list_story_instances

    seeds = list_story_instances()
    ids = {s["app_id"] for s in seeds}
    assert "shenjia_caifa" in ids
    shenjia = next(s for s in seeds if s["app_id"] == "shenjia_caifa")
    assert shenjia["title"] == "工匠傳奇"
    assert shenjia["seed_md"].endswith("novel-shenjia-initial-state.md")


def test_load_from_seed_path() -> None:
    seed = "application-notes/novel-shenjia-initial-state.md"
    cfg = load_config(seed_md=seed)
    assert cfg.app_id == "shenjia_caifa"
    assert str(cfg.seed_md).endswith("novel-shenjia-initial-state.md")


def test_app_and_seed_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="only one"):
        load_config(app_id="x", seed_md="y.md")
