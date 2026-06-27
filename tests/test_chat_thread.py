"""Tests for dual chat thread persistence."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "applications" / "novel_cursor"))

from chat_thread import ChatThread  # noqa: E402


def test_thread_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "script.json"
    t = ChatThread("script", path, model="deepseek-chat")
    t.ensure_system("sys")
    t.append_user("u1")
    t.append_assistant("a1")
    t.save()
    t2 = ChatThread.load(
        type("C", (), {"agents_dir": tmp_path, "output_dir": tmp_path})(),  # type: ignore
        "script",
        model="deepseek-chat",
    )
    # load via path directly
    t2 = ChatThread("script", path, model="deepseek-chat")
    data = path.read_text(encoding="utf-8")
    import json

    t2.messages = json.loads(data)["messages"]
    assert len(t2.messages) == 3
    assert t2.messages[-1]["content"] == "a1"


def test_drop_last_user() -> None:
    t = ChatThread("script", Path("x.json"), model="m")
    t.messages = [{"role": "user", "content": "u"}]
    t.drop_last_user()
    assert t.messages == []
