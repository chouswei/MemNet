"""Session lifecycle — in-memory registry only."""

from __future__ import annotations

import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NoReturn

from memnet.acl import SessionAcl, WorkerWriteScope, acl_globally_enabled, parse_write_scope
from memnet.config import (
    Caps,
    default_ttl_minutes,
    examples_dir,
    expire_snapshot_dir,
    save_on_expire,
)
from memnet.exceptions import MemNetError
from memnet.mem_store import MemStore
from memnet.models import SessionMeta
from memnet.neighbourhood_reserve import NeighbourhoodReserveTable
from memnet.output import emit_wrn
from memnet.registry import (
    SessionEntry,
    clear_all,
    count,
    get_entry,
    list_entries,
    list_expired_ids,
    register,
    remove_entry,
)
from memnet.tag_map import TagMap, load_map_from_file, load_map_from_lines

_now_override: datetime | None = None
# Session id is a capability secret. Filename stem only; no path separators.
_EXPIRE_SID_SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")


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
        entry = get_entry(session_id)
        if entry is None:
            raise MemNetError("session_not_found", "unknown session", exit_code=2)
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

    @property
    def acl(self) -> SessionAcl:
        if self._entry.acl is None:
            self._entry.acl = SessionAcl()
        return self._entry.acl

    @property
    def reserves(self) -> NeighbourhoodReserveTable:
        return self._entry.ensure_reserves()

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

    def enable_acl(self) -> None:
        self.acl.enable()
        self.meta.acl_enabled = True

    def grant_caller(
        self,
        caller: str,
        *,
        can_pin_map: bool = True,
        can_mutate: bool = True,
        write_scope: WorkerWriteScope | str | None = None,
    ) -> None:
        scope = parse_write_scope(write_scope) if isinstance(write_scope, str) else write_scope
        self.acl.grant(
            caller,
            can_pin_map=can_pin_map,
            can_mutate=can_mutate,
            write_scope=scope,
        )
        self.meta.acl_enabled = True

    def set_bind(self, mission_id: str, lease: str) -> None:
        self.acl.set_bind(mission_id, lease)
        self.meta.acl_enabled = True


def _session_is_expired(entry: SessionEntry) -> bool:
    expires = datetime.fromisoformat(entry.meta.expires_at.replace("Z", "+00:00"))
    return expires < utc_now()


def expire_snap_filename(session_id: str) -> str | None:
    """Return ``{sid}.snap`` when *session_id* is a safe filename stem.

    MUST NOT echo the sid. Reject path separators / ``..``.
    """
    if not session_id or not _EXPIRE_SID_SAFE.fullmatch(session_id):
        return None
    if session_id != Path(session_id).name or ".." in session_id:
        return None
    return f"{session_id}.snap"


def expire_snap_path(session_id: str, caps: Caps | None = None) -> Path | None:
    """Expire-dir path for a known sid, or None if dir unset / sid unsafe."""
    name = expire_snap_filename(session_id)
    if name is None:
        return None
    dest_dir = getattr(caps, "expire_snapshot_dir", None) if caps is not None else None
    dest_dir = dest_dir if dest_dir is not None else expire_snapshot_dir()
    if dest_dir is None:
        return None
    return dest_dir / name


def expire_snap_exists(session_id: str, caps: Caps | None = None) -> bool:
    path = expire_snap_path(session_id, caps)
    return bool(path is not None and path.is_file())


def raise_session_miss(
    session_id: str,
    caps: Caps | None = None,
    *,
    saw_expire: bool = False,
) -> NoReturn:
    """Honest miss for a sid the caller already passed. MUST NOT echo the sid.

    ``session_expired|snap_available`` / ``session_expired|snap_missing`` /
    ``session_not_found|unknown session``.
    """
    if expire_snap_exists(session_id, caps):
        raise MemNetError("session_expired", "snap_available", exit_code=2)
    if saw_expire:
        raise MemNetError("session_expired", "snap_missing", exit_code=2)
    raise MemNetError("session_not_found", "unknown session", exit_code=2)


def resolve_expire_load_path(session_id: str, caps: Caps | None = None) -> Path:
    """Resolve ``MEMNET_EXPIRE_SNAPSHOT_DIR/{sid}.snap`` for load-by-sid.

    File present → path. Save-on-expire armed + dir set + no file →
    ``snapshot_not_found|expire_snap``. Else ``session_expired|snap_missing``.
    MUST NOT echo the sid or dump the directory.
    """
    caps = caps or Caps()
    if expire_snap_filename(session_id) is None:
        raise MemNetError("session_not_found", "unknown session", exit_code=2)
    path = expire_snap_path(session_id, caps)
    if path is not None and path.is_file():
        return path
    enabled = bool(getattr(caps, "save_on_expire", False))
    dest = getattr(caps, "expire_snapshot_dir", None)
    dest = dest if dest is not None else expire_snapshot_dir()
    if enabled and dest is not None:
        raise MemNetError("snapshot_not_found", "expire_snap", exit_code=2)
    raise MemNetError("session_expired", "snap_missing", exit_code=2)


def snapshot_expired_session(session_id: str, caps: Caps | None = None) -> str | None:
    """Configurable expire ``session_save``. Off unless ``MEMNET_SAVE_ON_EXPIRE``.

    Auto path also needs ``MEMNET_EXPIRE_SNAPSHOT_DIR``. Entry must remain.
    """
    enabled = bool(getattr(caps, "save_on_expire", False)) if caps is not None else save_on_expire()
    if not enabled:
        return None
    dest_dir = getattr(caps, "expire_snapshot_dir", None) if caps is not None else None
    dest_dir = dest_dir if dest_dir is not None else expire_snapshot_dir()
    if dest_dir is None:
        emit_wrn("save_on_expire_no_dir", "dir unset")
        return None
    entry = get_entry(session_id)
    if entry is None:
        return None
    name = expire_snap_filename(session_id)
    if name is None:
        emit_wrn("expire_snapshot_failed", "unsafe_sid")
        return None
    from memnet.snapshot import write_snapshot

    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / name
    ss = SessionStore(session_id, caps)
    try:
        write_snapshot(ss, path)
    except OSError as exc:
        emit_wrn("expire_snapshot_failed", type(exc).__name__)
        return None
    emit_wrn("expire_snapshot", "written")
    return str(path)


def purge_expired(caps: Caps | None = None, *, keep: str | None = None) -> None:
    now = utc_now()
    for sid in list_expired_ids(now):
        if keep is not None and sid == keep:
            continue
        snapshot_expired_session(sid, caps)
        remove_entry(sid)


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
    acl_default = bool(getattr(caps, "acl_default_enabled", False) or acl_globally_enabled())
    acl = SessionAcl(enabled=acl_default)
    meta = SessionMeta(
        session_id=session_id,
        created_at=now.isoformat().replace("+00:00", "Z"),
        expires_at=expires.isoformat().replace("+00:00", "Z"),
        ttl_minutes=ttl_minutes,
        acl_enabled=acl.enabled,
    )
    entry = SessionEntry(
        meta=meta,
        tag_map=tag_map,
        store=MemStore(tag_map, caps),
        relations=set(_seed_relations()),
        acl=acl,
        reserves=NeighbourhoodReserveTable(),
    )
    register(session_id, entry)
    return SessionStore(session_id, caps)


def get_session(session_id: str, caps: Caps | None = None) -> SessionStore:
    caps = caps or Caps()
    entry = get_entry(session_id)
    if entry is None:
        purge_expired(caps)
        # session id is a capability secret — do not echo it in errors
        raise_session_miss(session_id, caps, saw_expire=False)
    expires = datetime.fromisoformat(entry.meta.expires_at.replace("Z", "+00:00"))
    if expires < utc_now():
        snapshot_expired_session(session_id, caps)
        remove_entry(session_id)
        purge_expired(caps)
        raise_session_miss(session_id, caps, saw_expire=True)
    # Sliding TTL: extend on access (avoids silent expiry for long sessions)
    original_ttl = entry.meta.ttl_minutes
    new_expires = utc_now() + timedelta(minutes=original_ttl)
    entry.meta.expires_at = new_expires.isoformat().replace("+00:00", "Z")
    purge_expired(caps)
    return SessionStore(session_id, caps)


def get_session_for_save(session_id: str, caps: Caps | None = None) -> tuple[SessionStore, bool]:
    """Load a session for ``session_save``.

    Expired save is off unless ``MEMNET_SAVE_ON_EXPIRE`` (Caps.save_on_expire).
    Live sessions slide TTL. Other expired ids still purge.
    """
    caps = caps or Caps()
    entry = get_entry(session_id)
    if entry is None:
        purge_expired(caps)
        raise_session_miss(session_id, caps, saw_expire=False)
    expired = _session_is_expired(entry)
    if expired and not bool(getattr(caps, "save_on_expire", False)):
        snapshot_expired_session(session_id, caps)
        remove_entry(session_id)
        purge_expired(caps)
        raise_session_miss(session_id, caps, saw_expire=True)
    if not expired:
        original_ttl = entry.meta.ttl_minutes
        new_expires = utc_now() + timedelta(minutes=original_ttl)
        entry.meta.expires_at = new_expires.isoformat().replace("+00:00", "Z")
        purge_expired(caps)
    else:
        purge_expired(caps, keep=session_id)
    return SessionStore(session_id, caps), expired


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
        if not remove_entry(session_id):
            raise MemNetError("session_not_found", "unknown session", exit_code=2)


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
