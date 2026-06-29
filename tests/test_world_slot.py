"""Tests for per-world game slots."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))
sys.path.insert(0, str(ROOT / "applications"))

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


def test_delete_world_record(tmp_path: Path) -> None:
    from novel_mobile.world_registry import delete_world_record, list_worlds_for_owner, read_meta

    base = _base(tmp_path)
    create_world_record(base, "user-aaaa1111", world_id="world-aaaa1111", title="甲")
    wdir = world_root(base, "world-aaaa1111").output_dir
    assert wdir.is_dir()
    delete_world_record(base, "world-aaaa1111", "user-aaaa1111")
    assert not wdir.is_dir()
    assert read_meta(base, "world-aaaa1111") is None
    assert list_worlds_for_owner(base, "user-aaaa1111") == []


def test_world_meta_records_app_id(tmp_path: Path) -> None:
    from novel_mobile.world_registry import read_meta

    base = _base(tmp_path)
    meta = create_world_record(base, "user-aaaa1111", world_id="world-aaaa1111", title="甲")
    assert meta.app_id == base.app_id
    loaded = read_meta(base, "world-aaaa1111")
    assert loaded is not None
    assert loaded.app_id == base.app_id


def test_locate_world_across_app_dirs(tmp_path: Path, monkeypatch) -> None:
    from app_config import NovelAppConfig
    from novel_mobile.world_registry import create_world_record, locate_world, read_meta

    root = tmp_path / "repo"
    shenjia_out = root / "novel-output" / "shenjia_caifa"
    shenjia_out.mkdir(parents=True)
    monkeypatch.setattr("novel_mobile.world_registry.repo_root", lambda: root)
    default = NovelAppConfig(
        app_id="other_app",
        seed_md=root / "seed.md",
        title="Other",
        output_dir=root / "novel-output" / "other_app",
        chapter_dir=shenjia_out / "chapters",
        snapshot_file=shenjia_out / "session_snap.json",
        session_id_file=shenjia_out / "session_id.txt",
        last_beat_file=shenjia_out / "last_beat.json",
        agents_dir=shenjia_out / "agents",
    )
    default.output_dir.mkdir(parents=True, exist_ok=True)
    shenjia = NovelAppConfig(
        app_id="shenjia_caifa",
        seed_md=root / "seed.md",
        title="Shenjia",
        output_dir=shenjia_out,
        chapter_dir=shenjia_out / "chapters",
        snapshot_file=shenjia_out / "session_snap.json",
        session_id_file=shenjia_out / "session_id.txt",
        last_beat_file=shenjia_out / "last_beat.json",
        agents_dir=shenjia_out / "agents",
    )
    create_world_record(shenjia, "user-aaaa1111", world_id="world-aaaa1111", title="甲")

    def fake_load_config(*, app_id=None, seed_md=None):
        if app_id == "shenjia_caifa":
            return shenjia
        raise FileNotFoundError(app_id)

    monkeypatch.setattr("novel_mobile.world_registry.load_config", fake_load_config)
    app_cfg, meta = locate_world(default, "world-aaaa1111")
    assert app_cfg.app_id == "shenjia_caifa"
    assert meta.world_id == "world-aaaa1111"
    assert read_meta(default, "world-aaaa1111") is None


def test_normalise_world_id_rejects_short() -> None:
    try:
        normalise_world_id("abc")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
