"""Tests for slot graph path sync in play_service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app_config import NovelAppConfig, repo_root
from play_service import ensure_slot_graph_paths


def _world_config(tmp_path: Path) -> NovelAppConfig:
    root = repo_root()
    wroot = root / "novel-output" / "shenjia_caifa" / "worlds" / "w_test1234"
    return NovelAppConfig(
        app_id="shenjia_caifa",
        seed_md=root / "application-notes" / "novel-shenjia-initial-state.md",
        title="test",
        output_dir=wroot,
        chapter_dir=wroot / "chapters",
        snapshot_file=wroot / "session_snap.json",
        session_id_file=wroot / "session_id.txt",
        last_beat_file=wroot / "last_beat.json",
        agents_dir=wroot / "agents",
    )


def test_ensure_slot_graph_paths_updates_mismatch(tmp_path: Path) -> None:
    cfg = _world_config(tmp_path)
    root = repo_root()
    ch_rel = str(cfg.chapter_dir.relative_to(root)).replace("\\", "/")
    with patch("play_service.read_usr_by_key", side_effect=["legacy/chapters", "legacy/snap.json"]), patch(
        "play_service.graph_sync_output_paths", return_value=(0, [])
    ) as sync:
        ensure_slot_graph_paths(cfg, "mn_test")
    sync.assert_called_once()
    assert sync.call_args.kwargs["chapter_out"] == ch_rel


def test_ensure_slot_graph_paths_skips_legacy_app(tmp_path: Path) -> None:
    root = repo_root()
    cfg = NovelAppConfig(
        app_id="shenjia_caifa",
        seed_md=root / "application-notes" / "novel-shenjia-initial-state.md",
        title="test",
        output_dir=root / "novel-output" / "shenjia_caifa",
        chapter_dir=root / "novel-output" / "shenjia_caifa" / "chapters",
        snapshot_file=root / "novel-output" / "shenjia_caifa" / "session_snap.json",
        session_id_file=root / "novel-output" / "shenjia_caifa" / "session_id.txt",
        last_beat_file=root / "novel-output" / "shenjia_caifa" / "last_beat.json",
        agents_dir=root / "novel-output" / "shenjia_caifa" / "agents",
    )
    with patch("play_service.graph_sync_output_paths") as sync:
        ensure_slot_graph_paths(cfg, "mn_test")
    sync.assert_not_called()
