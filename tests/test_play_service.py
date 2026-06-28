"""Tests for play_service shared beat helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys

_cursor = Path(__file__).resolve().parents[1] / "applications" / "novel_cursor"
sys.path.insert(0, str(_cursor))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app_config import NovelAppConfig
from play_service import probe_serve, read_last_beat, write_last_beat


def _tmp_config(tmp_path: Path) -> NovelAppConfig:
    out = tmp_path / "novel-output" / "test_app"
    out.mkdir(parents=True)
    return NovelAppConfig(
        app_id="test_app",
        seed_md=tmp_path / "seed.md",
        title="測試",
        output_dir=out,
        chapter_dir=out / "chapters",
        snapshot_file=out / "session_snap.json",
        session_id_file=out / "session_id.txt",
        last_beat_file=out / "last_beat.json",
        agents_dir=out / "agents",
    )


def test_write_and_read_last_beat_round_trip(tmp_path):
    config = _tmp_config(tmp_path)
    payload = {
        "exit_code": 0,
        "session": "mn_test",
        "prose": "一段劇情",
        "options": ["a", "b", "", "", "", ""],
        "hud": "氣血:6/6",
    }
    write_last_beat(config, payload)
    loaded = read_last_beat(config)
    assert loaded == payload


def test_read_last_beat_missing_returns_none(tmp_path):
    config = _tmp_config(tmp_path)
    assert read_last_beat(config) is None


def test_probe_serve_mock(monkeypatch):
    class FakeSock:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "play_service.socket.create_connection",
        lambda *a, **k: FakeSock(),
    )
    assert probe_serve() is True

    def boom(*a, **k):
        raise OSError("nope")

    monkeypatch.setattr("play_service.socket.create_connection", boom)
    assert probe_serve() is False
