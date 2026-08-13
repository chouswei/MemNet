"""In-memory session registry — pure RAM graph store."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from memnet.mem_store import MemStore
from memnet.models import SessionMeta, TagMap

if TYPE_CHECKING:
    from memnet.acl import SessionAcl

_registry_lock = threading.RLock()
_sessions: dict[str, SessionEntry] = {}


@dataclass
class SessionEntry:
    meta: SessionMeta
    tag_map: TagMap
    store: MemStore
    relations: set[str]
    lock: threading.RLock = field(default_factory=threading.RLock)
    acl: SessionAcl | None = None


def register(session_id: str, entry: SessionEntry) -> None:
    with _registry_lock:
        _sessions[session_id] = entry


def get_entry(session_id: str) -> SessionEntry | None:
    with _registry_lock:
        return _sessions.get(session_id)


def remove_entry(session_id: str) -> bool:
    with _registry_lock:
        return _sessions.pop(session_id, None) is not None


def contains(session_id: str) -> bool:
    with _registry_lock:
        return session_id in _sessions


def count() -> int:
    with _registry_lock:
        return len(_sessions)


def list_entries() -> list[SessionEntry]:
    with _registry_lock:
        return list(_sessions.values())


def clear_all() -> None:
    with _registry_lock:
        _sessions.clear()


def purge_before(now: datetime) -> list[str]:
    expired: list[str] = []
    with _registry_lock:
        for sid, entry in list(_sessions.items()):
            expires = datetime.fromisoformat(entry.meta.expires_at.replace("Z", "+00:00"))
            if expires < now:
                _sessions.pop(sid, None)
                expired.append(sid)
    return expired
