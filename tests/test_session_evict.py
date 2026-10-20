"""MN-REQ-05.5 session cap LRU evict — runtime checks on the in-process engine.

Proposed, not shipped. Every test here is xfail until the engine ships the
eviction path (module-level mark below). Test names are cited by the
MN-VER-05-S03..S09 verify defs in sysml-models/models/verify.sysml; the
presence check in tests/test_sysml_session_evict.py keeps the two in sync.

Never print session ids here: assertion messages name the rule, not the id.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import stat
import threading
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import memnet.registry as registry_mod
import memnet.session as session_mod
import memnet.snapshot as snapshot_mod
from memnet.acl import acl_to_dict
from memnet.admin_usage import build_report  # noqa: F401  (admin read surface)
from memnet.cli import app
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.neighbourhood_reserve import reserve
from memnet.registry import contains, count, get_entry
from memnet.session import (
    SessionStore,
    get_session,
    list_sessions,
    open_session,
    reset_registry,
    set_now_override,
)
from memnet.snapshot import load_snapshot

pytestmark = pytest.mark.xfail(reason="MN-REQ-05.5 not shipped; engine pending", strict=False)

runner = CliRunner()

ENV_MAX = "MEMNET_MAX_SESSIONS"
ENV_DIR = "MEMNET_EVICT_SNAPSHOT_DIR"
ENV_ADMIN = "MEMNET_ADMIN_TOKEN"
ADMIN_TOKEN = "test-admin-token"  # dummy value for the in-process admin read
BASE = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
_MN_ID = re.compile(r"mn_[0-9a-fA-F]+")
_PLR = (
    "CREATE (:PLR {id: 'PLR01', identity: 'Hero', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)


def _at(minute: float) -> datetime:
    return BASE + timedelta(minutes=minute)


@pytest.fixture
def evict(memnet_temp, monkeypatch, tmp_path):
    """Cap 3, snapshot dir set, no touch window (LATER). Clock fixed to BASE."""
    snap_dir = tmp_path / "evict-snaps"
    snap_dir.mkdir()
    monkeypatch.setenv(ENV_MAX, "3")
    monkeypatch.setenv(ENV_DIR, str(snap_dir))
    set_now_override(BASE)
    return snap_dir


def _open(schema, minute: float, ttl: int = 600) -> SessionStore:
    set_now_override(_at(minute))
    return open_session(map_file=str(schema), ttl_minutes=ttl)


def _touch(sid: str, minute: float) -> SessionStore:
    set_now_override(_at(minute))
    return get_session(sid)


def _seed(sid: str, workflow) -> None:
    """Write rows and edges through the CLI add path (a real write)."""
    r = runner.invoke(app, ["add", "--file", str(workflow), "--session", sid])
    assert r.exit_code == 0, "seed write failed"


def _snapshot_of(snap_dir, sid: str):
    hits = [p for p in snap_dir.iterdir() if p.is_file() and sid in p.read_text(encoding="utf-8")]
    assert len(hits) == 1, "expected exactly one snapshot for the evicted session"
    return hits[0]


def _make_unsaveable(ss: SessionStore) -> None:
    MutateGate(ss).apply([_PLR], mode="add")
    ss.store.get("PLR01").fields["identity"] = "x" * 9000


def _serve_status_payload() -> dict:
    from memnet_mcp.server import serve_status

    return json.loads(asyncio.run(serve_status()))


# --- S03: oldest-touch order and touch semantics ----------------------------


def test_evicts_oldest_touched_first(evict, schema_file):
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    c = _open(schema_file, 2)
    _touch(a.session_id, 3)  # a is now the newest touch
    d = _open(schema_file, 4)
    assert not contains(b.session_id), "oldest-touched session must be the victim"
    assert contains(a.session_id) and contains(c.session_id) and contains(d.session_id)


def test_reads_and_writes_are_touches(evict, schema_file, workflow_file):
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    c = _open(schema_file, 2)
    set_now_override(_at(3))
    _seed(a.session_id, workflow_file)  # write touches a
    _touch(b.session_id, 4)  # read touches b
    _open(schema_file, 5)
    assert not contains(c.session_id), "untouched session must be the victim"
    assert contains(a.session_id) and contains(b.session_id)


def test_admin_and_serve_status_reads_are_not_touches(evict, schema_file, monkeypatch):
    monkeypatch.setenv(ENV_ADMIN, ADMIN_TOKEN)
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    c = _open(schema_file, 2)
    set_now_override(_at(3))
    list_sessions()
    build_report(ADMIN_TOKEN)
    _serve_status_payload()
    d = _open(schema_file, 4)
    assert not contains(a.session_id), "admin/serve_status reads must not refresh the touch"
    assert contains(b.session_id) and contains(c.session_id) and contains(d.session_id)


# --- S04: save first, atomic write, victim lock, crash safety ---------------


def test_victim_saved_before_drop_atomic_fsync(evict, schema_file, workflow_file, monkeypatch):
    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    _open(schema_file, 1)
    _open(schema_file, 2)
    victim = a.session_id
    fsynced: list[int] = []
    real_fsync = os.fsync

    def counting_fsync(fd):
        fsynced.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", counting_fsync)
    _open(schema_file, 4)
    assert not contains(victim)
    assert len(fsynced) >= 2, "file and directory must both be fsynced"
    snap = _snapshot_of(evict, victim)
    assert stat.S_IMODE(snap.stat().st_mode) == 0o600
    leftovers = [p.name for p in evict.iterdir() if p != snap]
    assert not leftovers, "no temp files may be left in the snapshot dir"


def test_victim_lock_held_from_pick_through_drop(evict, schema_file, monkeypatch):
    a = _open(schema_file, 0)
    _open(schema_file, 1)
    _open(schema_file, 2)
    victim = a.session_id
    real_write = snapshot_mod.write_snapshot
    writing = threading.Event()
    release = threading.Event()

    def slow_write(ss, path, **kwargs):
        if ss.session_id == victim:
            writing.set()
            release.wait(5)
        return real_write(ss, path, **kwargs)

    monkeypatch.setattr(snapshot_mod, "write_snapshot", slow_write)
    opener = threading.Thread(target=lambda: _open(schema_file, 4))
    opener.start()
    try:
        assert writing.wait(5), "eviction never reached the save"
        entry = get_entry(victim)
        assert entry is not None
        acquired = entry.lock.acquire(timeout=0.2)
        if acquired:
            entry.lock.release()
        assert not acquired, "victim lock must be held during save"
    finally:
        release.set()
        opener.join(5)
    assert not opener.is_alive()
    assert not contains(victim)


def test_crash_after_fsync_before_drop_is_restorable(evict, schema_file, workflow_file):
    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    _open(schema_file, 1)
    _open(schema_file, 2)
    victim = a.session_id
    crash = RuntimeError("simulated crash")
    with (
        patch.object(registry_mod, "remove_entry", side_effect=crash) as reg_drop,
        patch.object(session_mod, "remove_entry", side_effect=crash) as ses_drop,
    ):
        try:
            _open(schema_file, 4)
        except RuntimeError:
            pass
    assert reg_drop.called or ses_drop.called, "crash hook never ran"
    snap = _snapshot_of(evict, victim)  # complete snapshot exists
    reset_registry()  # restart: RAM is lost
    assert not contains(victim)
    restored = load_snapshot(snap)  # restorable after restart, never torn
    assert restored.store.get("PLR01") is not None, "rows from before the crash must be intact"


def test_failed_save_never_drops_ram(evict, schema_file, monkeypatch):
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    _open(schema_file, 2)
    victim = a.session_id
    real_write = snapshot_mod.write_snapshot

    def failing_write(ss, path, **kwargs):
        if ss.session_id == victim:
            raise OSError("simulated disk full")
        return real_write(ss, path, **kwargs)

    monkeypatch.setattr(snapshot_mod, "write_snapshot", failing_write)
    _open(schema_file, 4)
    assert contains(victim), "a failed save must keep the victim live"
    assert not contains(b.session_id), "the next-oldest candidate must be tried"


# --- S05: skip unsaveable, count them -----------------------------------------


def test_unsaveable_victim_skipped_next_oldest_tried(evict, schema_file):
    a = _open(schema_file, 0)
    _make_unsaveable(a)
    b = _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)
    assert contains(a.session_id), "unsaveable session stays live"
    assert not contains(b.session_id), "next-oldest saveable session is the victim"


def test_unsaveable_held_counted_on_serve_status(evict, schema_file):
    a = _open(schema_file, 0)
    _make_unsaveable(a)
    _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)
    payload = _serve_status_payload()
    assert payload.get("sessions_unsaveable_held") == 1, "held unsaveable sessions must be counted"


# --- S06: refusal, no snapshot dir, concurrency -------------------------------


def test_all_in_use_refusal_drops_nothing(evict, schema_file):
    ids = [_open(schema_file, m).session_id for m in (0, 1, 2)]
    for sid in ids:  # every session is in use: open bind, so none is evictable
        SessionStore(sid).set_bind(f"mission-{sid[:4]}", "lease-x")
    with pytest.raises(MemNetError) as exc:
        _open(schema_file, 1)
    assert exc.value.code == "limit_exceeded"
    assert "all sessions are in use" in exc.value.message
    assert all(contains(sid) for sid in ids), "nothing may be dropped on refusal"
    assert not any(evict.iterdir()), "no snapshot may be written on refusal"


def test_no_snapshot_dir_refuses_without_eviction(evict, schema_file, monkeypatch):
    monkeypatch.delenv(ENV_DIR, raising=False)
    ids = [_open(schema_file, m).session_id for m in (0, 1, 2)]
    with pytest.raises(MemNetError) as exc:
        _open(schema_file, 4)
    assert exc.value.code == "limit_exceeded"
    assert all(contains(sid) for sid in ids), "no eviction without a snapshot dir"


def test_cap_two_concurrent_opens_one_victim_per_slot(evict, schema_file, monkeypatch):
    monkeypatch.setenv(ENV_MAX, "2")
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    seeded = {a.session_id, b.session_id}
    set_now_override(_at(30))
    barrier = threading.Barrier(4)
    opened: list[SessionStore] = []
    refused: list[MemNetError] = []
    errors: list[Exception] = []
    samples: list[int] = []
    stop = threading.Event()

    def worker():
        barrier.wait(5)
        try:
            opened.append(open_session(map_file=str(schema_file), ttl_minutes=600))
        except MemNetError as exc:
            refused.append(exc)
        except Exception as exc:  # any other error is a failure
            errors.append(exc)

    def sampler():
        while not stop.is_set():
            samples.append(count())

    mon = threading.Thread(target=sampler)
    threads = [threading.Thread(target=worker) for _ in range(4)]
    mon.start()
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    stop.set()
    mon.join(5)

    assert not errors, "only limit_exceeded refusals are allowed"
    assert len(opened) + len(refused) == 4
    # Two victims exist and the cap lock serialises picks, so the first two opens always
    # succeed. Later opens may be refused while both victims are mid-save (race-dependent).
    assert len(opened) >= 2, "the first two opens each free one slot"
    assert all(e.code == "limit_exceeded" for e in refused)
    assert samples and max(samples) <= 2, "count must never exceed the cap"
    assert count() == 2
    created = seeded | {s.session_id for s in opened}
    evicted = {sid for sid in created if not contains(sid)}
    assert len(evicted) == len(opened), "each successful open consumes exactly one victim"
    assert len(list(evict.iterdir())) == len(evicted), "one snapshot per victim"


# --- S07: exemptions ----------------------------------------------------------


def test_session_being_loaded_is_not_evicted(evict, schema_file):
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    c = _open(schema_file, 2)
    d = _open(schema_file, 4)  # evicts a
    snap = _snapshot_of(evict, a.session_id)
    set_now_override(_at(5))
    loaded = load_snapshot(snap)  # cap full: victim is oldest of b, c, d
    assert contains(loaded.session_id), "the session being loaded is never its own victim"
    assert not contains(b.session_id)
    assert contains(c.session_id) and contains(d.session_id)


def test_write_locked_session_exempt(evict, schema_file):
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    _open(schema_file, 2)
    held = threading.Event()
    release = threading.Event()
    holder_ss = SessionStore(a.session_id)

    def hold():
        with holder_ss.lock(exclusive=True):
            held.set()
            release.wait(5)

    t = threading.Thread(target=hold)
    t.start()
    try:
        assert held.wait(5)
        _open(schema_file, 4)
    finally:
        release.set()
        t.join(5)
    assert contains(a.session_id), "write-locked session is exempt"
    assert not contains(b.session_id), "next-oldest candidate is the victim"


def test_open_bind_exempt(evict, schema_file):
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    _open(schema_file, 2)
    SessionStore(a.session_id).set_bind("mission-x", "lease-x")
    _open(schema_file, 4)
    assert contains(a.session_id), "session with an open bind is exempt"
    assert not contains(b.session_id)


def test_reserve_lease_is_not_an_exemption(evict, schema_file, workflow_file):
    # Only open bind and live writes are exempt. A reserve lease does not protect
    # its session, and the lease does not survive the eviction.
    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    b = _open(schema_file, 1)
    _open(schema_file, 2)
    holder = SessionStore(a.session_id)
    reserve(holder.reserves, holder.store, anchor="PLR01", llm_id="llm-1", ttl_s=600, now=_at(3))
    _open(schema_file, 4)
    assert not contains(a.session_id), "a reserve lease alone does not exempt a session"
    assert contains(b.session_id)
    loaded = load_snapshot(_snapshot_of(evict, a.session_id))
    assert loaded.reserves.leases == {}, "reserve leases do not survive eviction"


# --- S08: caller silence, admin naming ---------------------------------------


def test_caller_result_has_no_eviction_field(evict, schema_file):
    for minute in (0, 1, 2):
        set_now_override(_at(minute))
        runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    set_now_override(_at(4))
    res = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    assert res.exit_code == 0
    text = (res.stdout + res.stderr).lower()
    assert "evict" not in text, "caller output must not mention eviction"


def test_admin_report_names_victim_never_mn_id(evict, schema_file):
    a = _open(schema_file, 0)
    _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)  # evicts a
    payload = _serve_status_payload()
    dumped = json.dumps(payload, default=str)
    assert payload.get("sessions_evicted") == 1, "admin status counts the eviction"
    assert not _MN_ID.search(dumped), "admin status must not carry a real session id"
    assert not contains(a.session_id)


# --- S09: restore fidelity, no lease, restored flag, fresh TTL ---------------


def test_restore_keeps_rows_edges_and_acl(evict, schema_file, workflow_file):
    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    victim = a.session_id
    ss = SessionStore(victim)
    ss.enable_acl()
    ss.grant_caller("worker-1", can_mutate=False)
    rows_before = ss.store.row_count_non_law()
    _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)  # evicts a
    snap = _snapshot_of(evict, victim)
    set_now_override(_at(5))
    loaded = load_snapshot(snap)
    assert loaded.store.row_count_non_law() == rows_before, "row count must survive"
    assert loaded.store.get("PLR01") is not None, "node rows must survive"
    assert loaded.store.get("E02") is not None, "edges must survive"
    assert loaded.acl.enabled and "worker-1" in loaded.acl.callers
    assert loaded.acl.callers["worker-1"].can_mutate is False


def test_restore_carries_no_lease(evict, schema_file, workflow_file):
    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    victim = a.session_id
    SessionStore(victim).grant_caller("worker-1")
    holder = SessionStore(victim)
    reserve(holder.reserves, holder.store, anchor="PLR01", llm_id="llm-1", ttl_s=600, now=_at(0.5))
    _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)  # evicts a; a reserve lease alone does not exempt it
    snap = _snapshot_of(evict, victim)
    set_now_override(_at(5))
    loaded = load_snapshot(snap)
    assert loaded.reserves.leases == {}, "restored session must carry no reserve leases"
    assert not (acl_to_dict(loaded.acl) or {}).get("bind"), "no bind may survive the restore"
    assert "worker-1" in loaded.acl.callers, "the ACL itself is kept"


def test_reopen_restored_true_no_alerts(evict, schema_file, capsys):
    a = _open(schema_file, 0)
    victim = a.session_id
    _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)  # evicts a
    snap = _snapshot_of(evict, victim)
    set_now_override(_at(5))
    capsys.readouterr()
    loaded = load_snapshot(snap)
    err = capsys.readouterr().err
    assert getattr(loaded, "restored", None) is True, "reopen must report restored=true"
    assert "WRN" not in err, "reopen of an evicted session emits no alerts"


def test_load_is_touch_with_fresh_ttl(evict, schema_file):
    a = _open(schema_file, 0, ttl=60)
    victim = a.session_id
    _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)  # evicts a
    snap = _snapshot_of(evict, victim)
    set_now_override(_at(30))
    loaded = load_snapshot(snap)
    expires = datetime.fromisoformat(loaded.meta.expires_at.replace("Z", "+00:00"))
    assert expires == _at(30 + 60), "a load starts a fresh TTL from load time"
