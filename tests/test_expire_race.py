"""MN-REQ-05.5 expire race — expiry never drops a session whose lock another thread holds."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

import memnet.cli as cli_mod
import memnet.session as session_mod
from memnet.cli import app
from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.registry import contains, get_entry
from memnet.session import (
    ExpireOutcome,
    SessionStore,
    _expire_drop_if_overdue,
    expire_hold_count,
    get_session,
    get_session_for_save,
    open_session,
    purge_expired,
    set_now_override,
)
from memnet.snapshot import load_snapshot, write_snapshot

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


def _renew_before_recheck(monkeypatch, sid: str, modules=(session_mod, cli_mod)) -> list[bool]:
    """Probe: the first overdue check on ``sid`` renews its TTL, after the caller's overdue
    check and before the locked re-check inside _expire_drop_if_overdue."""
    real = session_mod._expire_drop_if_overdue
    fired: list[bool] = []

    def probe(session_id, caps=None):
        if session_id == sid and not fired:
            fired.append(True)
            renewed = session_mod.utc_now() + timedelta(minutes=30)
            get_entry(sid).meta.expires_at = renewed.isoformat().replace("+00:00", "Z")
        return real(session_id, caps)

    for module in modules:
        monkeypatch.setattr(module, "_expire_drop_if_overdue", probe)
    return fired


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


def test_renewed_ttl_between_scan_and_acquire_is_not_dropped(memnet_temp, schema_file, monkeypatch):
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
    assert _expire_drop_if_overdue(sid, caps) is ExpireOutcome.UNSAVEABLE
    assert contains(sid), "a direct overdue drop also keeps it while the save fails"
    assert expire_hold_count() == 1
    assert list(tmp_path.glob("*.snap")) == []


def test_get_session_ttl_renewed_before_lock_returns_live_session(
    memnet_temp, schema_file, monkeypatch
):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1).session_id
    fired = _renew_before_recheck(monkeypatch, sid)
    _expire_now()
    ss = get_session(sid)
    assert fired == [True], "the probe ran between the overdue check and the locked re-check"
    assert ss.session_id == sid
    assert contains(sid)


def test_renewed_before_lock_outcome_is_renewed(memnet_temp, schema_file, monkeypatch):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1).session_id
    _expire_now()
    get_entry(sid).meta.expires_at = (
        (session_mod.utc_now() + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
    )
    assert _expire_drop_if_overdue(sid) is ExpireOutcome.RENEWED
    assert contains(sid)


def test_get_session_for_save_ttl_renewed_before_lock_saves_live_session(
    memnet_temp, schema_file, tmp_path, monkeypatch
):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    caps = Caps()
    sid = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps).session_id
    MutateGate(SessionStore(sid, caps)).apply([_PLR], mode="add")
    fired = _renew_before_recheck(monkeypatch, sid)
    _expire_now()
    ss, expired = get_session_for_save(sid, caps)
    assert fired == [True]
    assert expired is False, "a renewed session is saved as live, not as expired"
    assert contains(sid)
    dest = tmp_path / "live.snap"
    write_snapshot(ss, dest)
    assert load_snapshot(dest, caps=caps, keep_id=True).store.get("PLR01") is not None


def test_cli_save_ttl_renewed_before_lock_saves_live_session(
    memnet_temp, schema_file, tmp_path, monkeypatch
):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    caps = Caps()
    sid = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps).session_id
    MutateGate(SessionStore(sid, caps)).apply([_PLR], mode="add")
    fired = _renew_before_recheck(monkeypatch, sid)
    _expire_now()
    dest = tmp_path / "cli_live.snap"
    saved = runner.invoke(app, ["session", "save", "--file", str(dest), "--session", sid])
    assert fired == [True]
    assert saved.exit_code == 0, saved.stderr
    assert "session_expired" not in saved.stderr
    assert contains(sid)
    assert load_snapshot(dest, caps=caps, keep_id=True).store.get("PLR01") is not None


def test_cli_session_load_ttl_renewed_before_lock_returns_ok(
    memnet_temp, schema_file, tmp_path, monkeypatch
):
    caps = _arm_expire(monkeypatch, tmp_path)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps).session_id
    # Skip the sweep so the load's own overdue check is the one that meets the probe.
    monkeypatch.setattr(cli_mod, "purge_expired", lambda *a, **k: None)
    fired = _renew_before_recheck(monkeypatch, sid, modules=(cli_mod,))
    _expire_now()
    loaded = runner.invoke(app, ["session", "load", "--session", sid])
    assert fired == [True]
    assert loaded.exit_code == 0, loaded.stderr
    assert "session_expired" not in loaded.stderr
    assert contains(sid)
    assert list(tmp_path.glob("*.snap")) == [], "a renewed session is not expire-saved"


def test_busy_outcome_and_refusals_while_other_thread_holds(memnet_temp, schema_file, monkeypatch):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1).session_id
    _expire_now()
    thread, release = _hold_lock_in_thread(sid)
    try:
        assert _expire_drop_if_overdue(sid) is ExpireOutcome.BUSY
        with pytest.raises(MemNetError) as exc:
            get_session(sid)
        assert exc.value.code == "session_expired"
        assert exc.value.message == "overdue"
        with pytest.raises(MemNetError) as exc:
            get_session_for_save(sid)
        assert exc.value.code == "session_expired"
        assert exc.value.message == "overdue"
        assert contains(sid)
    finally:
        release.set()
        thread.join(5)
    assert _expire_drop_if_overdue(sid) is ExpireOutcome.DROPPED


def test_busy_outcome_when_calling_thread_holds_lock(memnet_temp, schema_file, monkeypatch):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    sid = open_session(map_file=str(schema_file), ttl_minutes=1).session_id
    _expire_now()
    with SessionStore(sid).lock(exclusive=True):
        assert _expire_drop_if_overdue(sid) is ExpireOutcome.BUSY
    assert _expire_drop_if_overdue(sid) is ExpireOutcome.DROPPED


def test_unsaveable_outcome_keeps_get_session_refusal(
    memnet_temp, schema_file, tmp_path, monkeypatch
):
    caps = _arm_expire(monkeypatch, tmp_path)
    ss = open_session(map_file=str(schema_file), ttl_minutes=1, caps=caps)
    sid = ss.session_id
    _make_unsaveable(ss)
    _expire_now()
    assert _expire_drop_if_overdue(sid, caps) is ExpireOutcome.UNSAVEABLE
    with pytest.raises(MemNetError) as exc:
        get_session(sid, caps)
    assert exc.value.code == "session_expired"
    assert exc.value.message == "overdue"
    assert contains(sid)
