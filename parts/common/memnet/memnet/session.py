"""Session lifecycle — in-memory registry only."""

from __future__ import annotations

import itertools
import re
import secrets
import threading
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
    count_expire_snapshot_failed,
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
# MN-REQ-05.5 cap state. _cap_lock covers the count, the victim pick and the slot claim.
# _pending_slots counts opens that hold a claimed slot and are not yet registered. A
# victim stays in the registry until it is dropped, so its picking open holds a pending slot.
_cap_lock = threading.Lock()
_pending_slots = 0
_evicted_total = 0
_last_evicted_product: str | None = None
_touch_seq_counter = itertools.count(1)
_touch_seq_lock = threading.Lock()


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
    # True when this handle came from a snapshot load (MN-REQ-05.5 reopen).
    restored: bool = False

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
        """Record a touch: last activity time and a fresh touch_seq (MN-REQ-05.5)."""
        self.meta.modified_at = iso_timestamp()
        self._entry.touch_seq = _next_touch_seq()

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


def _mark_expire_save_failed(session_id: str, code: str) -> None:
    entry = get_entry(session_id)
    if entry is None:
        return
    entry.expire_save_failed = code
    emit_wrn("expire_snapshot_failed", code, force=True)


def _clear_expire_save_failed(session_id: str) -> None:
    entry = get_entry(session_id)
    if entry is not None:
        entry.expire_save_failed = None


def expire_save_enabled(caps: Caps | None = None) -> bool:
    if caps is not None:
        return bool(getattr(caps, "save_on_expire", False))
    return save_on_expire()


def snapshot_expired_session(session_id: str, caps: Caps | None = None) -> str | None:
    """Configurable expire ``session_save``. Off unless ``MEMNET_SAVE_ON_EXPIRE``.

    Auto path also needs ``MEMNET_EXPIRE_SNAPSHOT_DIR``. Entry must remain.
    On write failure the session stays live and ``expire_save_failed`` is set.
    """
    enabled = expire_save_enabled(caps)
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
        _mark_expire_save_failed(session_id, "unsafe_sid")
        return None
    from memnet.snapshot import write_snapshot

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _mark_expire_save_failed(session_id, type(exc).__name__)
        return None
    path = dest_dir / name
    ss = SessionStore(session_id, caps)
    try:
        write_snapshot(ss, path)
    except OSError as exc:
        _mark_expire_save_failed(session_id, type(exc).__name__)
        return None
    except MemNetError as exc:
        _mark_expire_save_failed(session_id, exc.code)
        return None
    _clear_expire_save_failed(session_id)
    emit_wrn("expire_snapshot", "written")
    return str(path)


def expire_save_should_drop(session_id: str, caps: Caps | None = None) -> bool:
    """Try expire-save. True means drop RAM; False means keep live after a write failure."""
    if not expire_save_enabled(caps):
        return True
    path = snapshot_expired_session(session_id, caps)
    if path is not None:
        return True
    entry = get_entry(session_id)
    return not (entry is not None and entry.expire_save_failed)


def purge_expired(caps: Caps | None = None, *, keep: str | None = None) -> None:
    now = utc_now()
    for sid in list_expired_ids(now):
        if keep is not None and sid == keep:
            continue
        if expire_save_should_drop(sid, caps):
            remove_entry(sid)


def count_sessions(caps: Caps | None = None) -> int:
    purge_expired(caps)
    return count()


def expire_hold_count() -> int:
    """Sessions kept in RAM because expire-save failed. Peek; does not purge."""
    return count_expire_snapshot_failed()


def _next_touch_seq() -> int:
    with _touch_seq_lock:
        return next(_touch_seq_counter)


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _victim_key(entry: SessionEntry) -> tuple[datetime, int]:
    """LRU order: last touch as a parsed instant, then touch_seq (oldest first)."""
    return (_instant(entry.meta.modified_at or entry.meta.created_at), entry.touch_seq)


def _exempt_from_eviction(entry: SessionEntry) -> bool:
    """An open bind exempts its session. A reserve lease alone does not."""
    return entry.evicting or (entry.acl is not None and entry.acl.bind is not None)


def _pick_victim_locked(skipped: set[str]) -> SessionEntry | None:
    """Oldest-touched evictable session, with its victim lock taken. Caller holds _cap_lock.

    A session whose lock is held by live writes is exempt: another thread's hold fails
    the try-lock, and a hold by the calling thread is refused by _is_owned (RLock re-entry).
    """
    candidates = [
        entry
        for entry in list_entries()
        if entry.meta.session_id not in skipped and not _exempt_from_eviction(entry)
    ]
    candidates.sort(key=_victim_key)
    for entry in candidates:
        if not entry.lock._is_owned() and entry.lock.acquire(blocking=False):
            entry.evicting = True
            return entry
    return None


def save_evict_victim(session_id: str, caps: Caps) -> None:
    """MAINTENANCE-SAVES evict_save: write the victim's snapshot. Not a touch."""
    from memnet.snapshot import write_snapshot

    dest = expire_snap_path(session_id, caps)
    if dest is None:
        raise MemNetError("snapshot_unsaveable", "evict dir")
    write_snapshot(SessionStore(session_id, caps), dest)


def _evict_victim(entry: SessionEntry, caps: Caps) -> bool:
    """Save, then drop, one victim. Caller holds its victim lock. True when dropped."""
    global _evicted_total, _last_evicted_product
    sid = entry.meta.session_id
    try:
        save_evict_victim(sid, caps)
    except (MemNetError, OSError):
        entry.evict_unsaveable = True
        return False
    remove_entry(sid)
    with _cap_lock:
        _evicted_total += 1
        _last_evicted_product = entry.meta.product
    return True


def claim_slot(caps: Caps) -> None:
    """Claim one slot for an open or load; at cap, evict the oldest saveable session.

    Returns with the slot claimed. The caller registers it with register_claimed.
    Raises limit_exceeded "all sessions are in use" when nothing can be evicted;
    nothing is dropped and nothing is written then.
    """
    global _pending_slots
    skipped: set[str] = set()
    while True:
        with _cap_lock:
            if count() + _pending_slots < caps.max_sessions:
                _pending_slots += 1
                return
            victim = None
            if caps.expire_snapshot_dir is not None:
                victim = _pick_victim_locked(skipped)
            if victim is None:
                raise MemNetError("limit_exceeded", "all sessions are in use")
            _pending_slots += 1
        dropped = False
        try:
            dropped = _evict_victim(victim, caps)
        finally:
            victim.evicting = False
            victim.lock.release()
            if not dropped:
                with _cap_lock:
                    _pending_slots -= 1
        if dropped:
            return  # the victim's slot is ours; the caller registers it
        skipped.add(victim.meta.session_id)


def register_claimed(session_id: str, entry: SessionEntry) -> None:
    """Register an entry whose slot came from claim_slot, and release that claim."""
    global _pending_slots
    with _cap_lock:
        _pending_slots -= 1
        register(session_id, entry)


def eviction_status() -> dict[str, int | str | None]:
    """Admin counters for serve_status. Names only: never a session id."""
    with _cap_lock:
        evicted = _evicted_total
        last_product = _last_evicted_product
    held = sum(1 for entry in list_entries() if entry.evict_unsaveable)
    return {
        "sessions_evicted": evicted,
        "sessions_unsaveable_held": held,
        "last_evicted_product": last_product,
    }


def open_session(
    map_lines: list[str] | None = None,
    map_file: str | None = None,
    ttl_minutes: int | None = None,
    caps: Caps | None = None,
    product: str | None = None,
) -> SessionStore:
    from memnet.upgrade import refuse_new_session

    refuse_new_session()
    caps = caps or Caps()
    purge_expired(caps)
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
    from memnet.admin_usage import validate_product_label

    product_label = validate_product_label(product)
    session_id = f"mn_{secrets.token_hex(4)}"
    now = utc_now()
    expires = now + timedelta(minutes=ttl_minutes)
    acl_default = bool(getattr(caps, "acl_default_enabled", False) or acl_globally_enabled())
    acl = SessionAcl(enabled=acl_default)
    created = now.isoformat().replace("+00:00", "Z")
    meta = SessionMeta(
        session_id=session_id,
        created_at=created,
        expires_at=expires.isoformat().replace("+00:00", "Z"),
        ttl_minutes=ttl_minutes,
        acl_enabled=acl.enabled,
        product=product_label,
        # Open is the first touch: a never-read session has a defined last touch.
        modified_at=created,
    )
    entry = SessionEntry(
        meta=meta,
        tag_map=tag_map,
        store=MemStore(tag_map, caps),
        relations=set(_seed_relations()),
        acl=acl,
        reserves=NeighbourhoodReserveTable(),
        touch_seq=_next_touch_seq(),
    )
    claim_slot(caps)
    register_claimed(session_id, entry)
    return SessionStore(session_id, caps)


def get_session(session_id: str, caps: Caps | None = None, *, touch: bool = True) -> SessionStore:
    """Live session by id. A read is a touch unless ``touch`` is False (a refused write)."""
    caps = caps or Caps()
    entry = get_entry(session_id)
    if entry is None:
        purge_expired(caps)
        # session id is a capability secret — do not echo it in errors
        raise_session_miss(session_id, caps, saw_expire=False)
    expires = datetime.fromisoformat(entry.meta.expires_at.replace("Z", "+00:00"))
    if expires < utc_now():
        if expire_save_should_drop(session_id, caps):
            remove_entry(session_id)
            purge_expired(caps)
            raise_session_miss(session_id, caps, saw_expire=True)
        purge_expired(caps, keep=session_id)
        raise MemNetError("session_expired", "overdue", exit_code=2)
    # Sliding TTL: extend on access (avoids silent expiry for long sessions)
    original_ttl = entry.meta.ttl_minutes
    new_expires = utc_now() + timedelta(minutes=original_ttl)
    entry.meta.expires_at = new_expires.isoformat().replace("+00:00", "Z")
    purge_expired(caps)
    ss = SessionStore(session_id, caps)
    if touch:
        ss.touch()
    return ss


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
        overdue = expires < now
        if overdue and not entry.expire_save_failed:
            continue
        ttl_left = 0 if overdue else max(0, int((expires - now).total_seconds() // 60))
        modified = entry.meta.modified_at or "-"
        out.append((entry.meta.session_id, entry.meta.expires_at, ttl_left, modified))
    out.sort(key=lambda row: row[0])
    return out


def get_session_for_close(session_id: str, caps: Caps | None = None) -> SessionStore:
    """Load a session for ``session_close``, including overdue expire-save holds."""
    caps = caps or Caps()
    entry = get_entry(session_id)
    if entry is None:
        purge_expired(caps)
        raise_session_miss(session_id, caps, saw_expire=False)
    purge_expired(caps, keep=session_id)
    return SessionStore(session_id, caps)


def close_session(session_id: str, caps: Caps | None = None) -> None:
    caps = caps or Caps()
    ss = get_session_for_close(session_id, caps)
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
    """Test helper — drop all in-memory sessions and the eviction counters."""
    global _pending_slots, _evicted_total, _last_evicted_product
    with _cap_lock:
        _pending_slots = 0
        _evicted_total = 0
        _last_evicted_product = None
    clear_all()
