"""Persistent script / prose chat threads (conversation memory only)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from app_config import NovelAppConfig

Role = Literal["script", "prose"]

_MAX_MESSAGES = int(os.environ.get("THREAD_MAX_MESSAGES", "80"))


def thread_path(config: NovelAppConfig, role: Role) -> Path:
    return config.agents_dir.parent / "threads" / f"{role}.json"


def reset_threads(config: NovelAppConfig) -> None:
    root = config.agents_dir.parent / "threads"
    if root.is_dir():
        for path in root.glob("*.json"):
            path.unlink()
    root.mkdir(parents=True, exist_ok=True)


def reset_role_thread(config: NovelAppConfig, role: Role) -> None:
    path = thread_path(config, role)
    if path.is_file():
        path.unlink()


class ChatThread:
    """OpenAI-style message list persisted per role."""

    def __init__(self, role: Role, path: Path, *, model: str) -> None:
        self.role = role
        self.path = path
        self.model = model
        self.messages: list[dict[str, str]] = []

    @classmethod
    def load(cls, config: NovelAppConfig, role: Role, *, model: str) -> ChatThread:
        path = thread_path(config, role)
        thread = cls(role, path, model=model)
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data.get("messages"), list):
                    thread.messages = [
                        {"role": str(m["role"]), "content": str(m["content"])}
                        for m in data["messages"]
                        if isinstance(m, dict) and "role" in m and "content" in m
                    ]
                if data.get("model"):
                    thread.model = str(data["model"])
            except (json.JSONDecodeError, OSError):
                thread.messages = []
        return thread

    def ensure_system(self, system: str) -> None:
        if self.messages and self.messages[0].get("role") == "system":
            if self.messages[0]["content"] != system:
                self.messages[0] = {"role": "system", "content": system}
            return
        self.messages.insert(0, {"role": "system", "content": system})

    def append_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        self._trim()

    def append_assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})
        self._trim()

    def drop_last_user(self) -> None:
        if self.messages and self.messages[-1].get("role") == "user":
            self.messages.pop()

    def _trim(self) -> None:
        if _MAX_MESSAGES <= 0:
            return
        system = [m for m in self.messages if m.get("role") == "system"]
        rest = [m for m in self.messages if m.get("role") != "system"]
        if len(rest) > _MAX_MESSAGES:
            rest = rest[-_MAX_MESSAGES :]
        self.messages = (system[:1] if system else []) + rest

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "role": self.role,
            "model": self.model,
            "messages": self.messages,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
