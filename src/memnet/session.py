"""Session lifecycle — in-memory registry only."""

from __future__ import annotations

import secrets
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Iterator

from memnet.config import Caps, default_ttl_minutes, examples_dir
from memnet.exceptions import MemNetError
from memnet.mem_store import MemStore
from memnet.models import SessionMeta
from memnet.registry import SessionEntry, clear_all, count, get, list_entries, purge_before, register, remove
from memnet.tag_map import TagMap, load_map_from_file, load_map_from_lines

_now_override: datetime | None = None


def set_now_override(dt: datetime | None) -> None:
    global _now_override
    _now_override = dt


def utc_now() -> datetime:
    return _now_override or datetime.now(UTC)


def iso_timestamp(dt: datetime | None = None) -> str:
    when = dt or utc_now()
    return when.isoformat().replace("+00:00", "Z")


def _seed_relations() -> list[str]:
    seed_file = examples_dir() / "relations.seed.txt"
    if not seed_file.exists():
        return ["seeks_help", "binds", "produces", "links"]
    lines = []
    for line in seed_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


class SessionStore:
    def __init__(self, session_id: str, caps: Caps | None = None) -> None:
        self.session_id = session_id
        self.caps = caps or Caps()
        entry = get(session_id)
        if entry is None:
            raise MemNetError("session_not_found", self.session_id, exit_code=2)
        self._entry = entry

    @property
    def meta(self) -> SessionMeta:
        return self._entry.meta

    @property
    def tag_map(self) -> TagMap:
        return self._entry.tag_map

    @property
    def relations(self) -> set[str]:
        return self._entry.relations

    @relations.setter
    def relations(self, value: set[str]) -> None:
        self._entry.relations = value

    @property
    def store(self) -> MemStore:
        return self._entry.store

    def touch(self) -> None:
        """Record last activity time (reads and writes)."""
        self.meta.modified_at = iso_timestamp()

    def mark_written(self) -> None:
        self.meta.has_writes = True
        self.touch()

    @contextmanager
    def lock(self, exclusive: bool) -> Iterator[None]:
        with self._entry.lock:
            yield


def purge_expired(caps: Caps | None = None) -> None:
    del caps  # registry-wide purge; caps reserved for API compatibility
    purge_before(utc_now())


def count_sessions() -> int:
    purge_expired()
    return count()


def open_session(
    map_lines: list[str] | None = None,
    map_file: str | None = None,
    ttl_minutes: int | None = None,
    caps: Caps | None = None,
) -> SessionStore:
    caps = caps or Caps()
    purge_expired(caps)
    if count_sessions() >= caps.max_sessions:
        raise MemNetError(
            "limit_exceeded",
            f"sessions|{count_sessions() + 1}/{caps.max_sessions}",
        )
    if ttl_minutes is None:
        ttl_minutes = default_ttl_minutes()
    if ttl_minutes < 1 or ttl_minutes > 1440:
        raise MemNetError("bad_ttl", "ttl must be 1..1440")
    if map_file:
        tag_map = load_map_from_file(map_file, caps)
    elif map_lines:
        tag_map = load_map_from_lines(map_lines, caps)
    else:
        raise MemNetError("no_map", "provide --map-file or --map")
    session_id = f"mn_{secrets.token_hex(4)}"
    now = utc_now()
    expires = now + timedelta(minutes=ttl_minutes)
    meta = SessionMeta(
        session_id=session_id,
        created_at=now.isoformat().replace("+00:00", "Z"),
        expires_at=expires.isoformat().replace("+00:00", "Z"),
        ttl_minutes=ttl_minutes,
    )
    entry = SessionEntry(
        meta=meta,
        tag_map=tag_map,
        store=MemStore(tag_map, caps),
        relations=set(_seed_relations()),
    )
    register(session_id, entry)
    return SessionStore(session_id, caps)


def get_session(session_id: str, caps: Caps | None = None) -> SessionStore:
    caps = caps or Caps()
    entry = get(session_id)
    if entry is None:
        purge_expired(caps)
        raise MemNetError("session_not_found", session_id, exit_code=2)
    expires = datetime.fromisoformat(entry.meta.expires_at.replace("Z", "+00:00"))
    if expires < utc_now():
        remove(session_id)
        purge_expired(caps)
        raise MemNetError("session_expired", session_id, exit_code=2)
    purge_expired(caps)
    return SessionStore(session_id, caps)


def list_sessions(caps: Caps | None = None) -> list[tuple[str, str, int, str]]:
    caps = caps or Caps()
    purge_expired(caps)
    now = utc_now()
    out: list[tuple[str, str, int, str]] = []
    for entry in list_entries():
        expires = datetime.fromisoformat(entry.meta.expires_at.replace("Z", "+00:00"))
        if expires < now:
            continue
        ttl_left = max(0, int((expires - now).total_seconds() // 60))
        modified = entry.meta.modified_at or "-"
        out.append((entry.meta.session_id, entry.meta.expires_at, ttl_left, modified))
    out.sort(key=lambda row: row[0])
    return out


def close_session(session_id: str, caps: Caps | None = None) -> None:
    caps = caps or Caps()
    ss = get_session(session_id, caps)
    with ss.lock(exclusive=True):
        if not remove(session_id):
            raise MemNetError("session_not_found", session_id, exit_code=2)


def resolve_session_id(cli_session: str | None) -> str:
    import os

    if cli_session:
        return cli_session
    env = os.environ.get("MEMNET_SESSION")
    if env:
        return env
    raise MemNetError("no_session", "set --session or MEMNET_SESSION", exit_code=2)


def reset_registry() -> None:
    """Test helper — drop all in-memory sessions."""
    clear_all()
