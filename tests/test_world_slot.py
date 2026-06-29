"""Tests for per-world game slots."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from app_config import NovelAppConfig
from chat_thread import ChatThread, reset_threads, thread_path
from novel_mobile.world_registry import create_world_record
from novel_mobile.world_slot import normalise_world_id, world_root


def _base(tmp_path: Path) -> NovelAppConfig:
    out = tmp_path / "out"
    out.mkdir()
    return NovelAppConfig(
        app_id="shenjia_caifa",
        seed_md=tmp_path / "seed.md",
        title="工匠傳奇",
        output_dir=out,
        chapter_dir=out / "chapters",
        snapshot_file=out / "session_snap.json",
        session_id_file=out / "session_id.txt",
        last_beat_file=out / "last_beat.json",
        agents_dir=out / "agents",
    )


def test_world_root_isolated_paths(tmp_path: Path) -> None:
    base = _base(tmp_path)
    a = world_root(base, "world-aaaa1111")
    b = world_root(base, "world-bbbb2222")
    assert a.session_id_file != b.session_id_file
    assert "worlds/world-aaaa1111" in str(a.session_id_file).replace("\\", "/")
    assert a.output_dir.name == "world-aaaa1111"


def test_world_thread_paths_isolated(tmp_path: Path) -> None:
    base = _base(tmp_path)
    a = world_root(base, "world-aaaa1111")
    b = world_root(base, "world-bbbb2222")
    script_a = thread_path(a, "script")
    script_b = thread_path(b, "script")
    assert script_a != script_b
    assert "worlds/world-aaaa1111/threads/script.json" in str(script_a).replace("\\", "/")


def test_reset_threads_only_affects_one_world(tmp_path: Path) -> None:
    base = _base(tmp_path)
    a = world_root(base, "world-aaaa1111")
    b = world_root(base, "world-bbbb2222")
    for cfg, marker in ((a, "world-a"), (b, "world-b")):
        thread = ChatThread.load(cfg, "prose", model="deepseek-v4-flash")
        thread.append_user(marker)
        thread.save()
    reset_threads(a)
    assert not thread_path(a, "prose").is_file()
    assert thread_path(b, "prose").is_file()


def test_list_worlds_for_owner(tmp_path: Path) -> None:
    from novel_mobile.world_registry import list_worlds_for_owner

    base = _base(tmp_path)
    create_world_record(base, "user-aaaa1111", world_id="world-aaaa1111", title="甲")
    create_world_record(base, "user-bbbb2222", world_id="world-bbbb2222", title="乙")
    worlds = list_worlds_for_owner(base, "user-aaaa1111")
    assert len(worlds) == 1
    assert worlds[0]["world_id"] == "world-aaaa1111"


def test_normalise_world_id_rejects_short() -> None:
    try:
        normalise_world_id("abc")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
