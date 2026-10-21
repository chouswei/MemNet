"""MN-REQ-05.5 expire race — expiry never drops a session whose lock another thread holds."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

import memnet.session as session_mod
from memnet.cli import app
from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.registry import contains, get_entry
from memnet.session import (
    SessionStore,
    _expire_drop_if_overdue,
    expire_hold_count,
    get_session,
    open_session,
    purge_expired,
    set_now_override,
)
from memnet.snapshot import load_snapshot

_PLR = (
    "CREATE (:PLR {id: 'PLR01', identity: 'Hero', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)
_READ_BOUND_S = 1.0


@pytest.fixture(autouse=True)
def _reset_clock():
    yield
    set_now_override(None)


def _arm_expire(monkeypatch, tmp_path: Path) -> Caps:
    monkeypatch.setenv("MEMNET_SAVE_ON_EXPIRE", "1")
    monkeypatch.setenv("MEMNET_EXPIRE_SNAPSHOT_DIR", str(tmp_path))
    return Caps()


def _expire_now(minutes: int = 5) -> None:
    set_now_override(datetime.now(UTC) + timedelta(minutes=minutes))


def _make_unsaveable(ss) -> None:
    """Oversize a field so the expire-save refuses (snapshot_unsaveable)."""
    MutateGate(ss).apply([_PLR], mode="add")
    ss.store.get("PLR01").fields["identity"] = "x" * 9000


def _hold_lock_in_thread(sid: str, action=None):
    """Hold ``sid``'s entry lock on a worker thread until ``release`` is set."""
    held = threading.Event()
    release = threading.Event()
    holder = SessionStore(sid)

    def run():
        with holder.lock(exclusive=True):
            held.set()
            release.wait(5)
            if action is not None:
                action()

    thread = threading.Thread(target=run)
    thread.start()
    assert held.wait(5)
    return thread, release


def test_expiry_skips_session_held_by_another_thread(
    memnet_temp, schema_file, tmp_path, monkeypatch
):
    caps = _arm_expire(monkeypatch, tmp_path)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps).session_id

    def write_under_hold():
        MutateGate(SessionStore(sid)).apply([_PLR], mode="add")

    thread, release = _hold_lock_in_thread(sid, action=write_under_hold)
    try:
        _expire_now()
        purge_expired(caps)
        assert contains(sid), "a session locked by another thread is skipped, not dropped"
        assert list(tmp_path.glob("*.snap")) == []
    finally:
        release.set()
        thread.join(5)

    purge_expired(caps)
    assert not contains(sid), "the next sweep expire-saves and drops it"
    snaps = list(tmp_path.glob("*.snap"))
    assert len(snaps) == 1, "the expire-save includes the write made under the hold"
    reloaded = load_snapshot(snaps[0], caps=caps, keep_id=True)
    assert reloaded.store.get("PLR01") is not None


def test_read_during_held_lock_does_not_block(memnet_temp, schema_file, monkeypatch):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    expiring = open_session(map_file=str(schema_file), ttl_minutes=1).session_id
    live = open_session(map_file=str(schema_file), ttl_minutes=1440).session_id
    _expire_now()
    thread, release = _hold_lock_in_thread(expiring)
    try:
        started = time.monotonic()
        ss = get_session(live)
        assert ss.session_id == live
        assert time.monotonic() - started < _READ_BOUND_S

        started = time.monotonic()
        with pytest.raises(MemNetError) as exc:
            get_session(expiring)
        assert exc.value.code == "session_expired"
        assert exc.value.message == "overdue"
        assert time.monotonic() - started < _READ_BOUND_S
        assert contains(expiring), "the held expiring session is kept for a later sweep"
    finally:
        release.set()
        thread.join(5)


def test_renewed_ttl_between_scan_and_acquire_is_not_dropped(
    memnet_temp, schema_file, monkeypatch
):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1).session_id
    real_list = session_mod.list_expired_ids

    def scan_then_renew(now):
        found = real_list(now)
        # A read renews the TTL after the scan and before the purge takes the lock.
        entry = get_entry(sid)
        renewed = session_mod.utc_now() + timedelta(minutes=30)
        entry.meta.expires_at = renewed.isoformat().replace("+00:00", "Z")
        return found

    monkeypatch.setattr(session_mod, "list_expired_ids", scan_then_renew)
    _expire_now()
    purge_expired()
    monkeypatch.setattr(session_mod, "list_expired_ids", real_list)
    assert contains(sid), "a TTL renewed before the lock is taken keeps the session"


def test_session_held_by_calling_thread_is_skipped(memnet_temp, schema_file, monkeypatch):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1).session_id
    _expire_now()
    with SessionStore(sid).lock(exclusive=True):
        purge_expired()
        assert contains(sid), "the caller's own session in use is skipped (RLock re-entry)"
    purge_expired()
    assert not contains(sid)


runner = CliRunner()


def test_cli_session_load_during_held_expiry_keeps_session(
    memnet_temp, schema_file, tmp_path, monkeypatch
):
    caps = _arm_expire(monkeypatch, tmp_path)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps).session_id

    def write_under_hold():
        MutateGate(SessionStore(sid)).apply([_PLR], mode="add")

    _expire_now()
    thread, release = _hold_lock_in_thread(sid, action=write_under_hold)
    try:
        loaded = runner.invoke(app, ["session", "load", "--session", sid])
        assert loaded.exit_code != 0
        assert "session_expired|overdue" in loaded.stderr
        assert contains(sid), "a CLI load does not drop a session another thread holds"
        assert list(tmp_path.glob("*.snap")) == []
    finally:
        release.set()
        thread.join(5)

    dest = tmp_path / "after.snap"
    saved = runner.invoke(app, ["session", "save", "--file", str(dest), "--session", sid])
    assert saved.exit_code == 0, saved.stderr
    reloaded = load_snapshot(dest, caps=caps, keep_id=True)
    assert reloaded.store.get("PLR01") is not None, "the write made under the hold is not lost"


def test_cli_session_save_during_held_expiry_keeps_write(
    memnet_temp, schema_file, tmp_path, monkeypatch
):
    caps = _arm_expire(monkeypatch, tmp_path)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps).session_id

    def write_under_hold():
        MutateGate(SessionStore(sid)).apply([_PLR], mode="add")

    _expire_now()
    thread, release = _hold_lock_in_thread(sid, action=write_under_hold)
    dest = tmp_path / "saved.snap"
    results = {}

    def run_save():
        results["save"] = runner.invoke(
            app, ["session", "save", "--file", str(dest), "--session", sid]
        )

    saver = threading.Thread(target=run_save)
    try:
        saver.start()
        time.sleep(0.2)
    finally:
        release.set()
        thread.join(5)
    saver.join(5)
    assert not saver.is_alive()
    assert results["save"].exit_code == 0, results["save"].stderr
    assert not contains(sid), "an expired save drops the session it wrote, under the same hold"
    reloaded = load_snapshot(dest, caps=caps, keep_id=True)
    assert reloaded.store.get("PLR01") is not None, "the save includes the hold's write"


def test_unsaveable_expiry_keeps_session_through_sweeps(
    memnet_temp, schema_file, tmp_path, monkeypatch
):
    caps = _arm_expire(monkeypatch, tmp_path)
    ss = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps)
    sid = ss.session_id
    _make_unsaveable(ss)
    _expire_now()
    purge_expired(caps)
    assert contains(sid), "an unsaveable expire-save keeps the session in RAM"
    assert _expire_drop_if_overdue(sid, caps) is False
    assert contains(sid), "a direct overdue drop also keeps it while the save fails"
    assert expire_hold_count() == 1
    assert list(tmp_path.glob("*.snap")) == []
