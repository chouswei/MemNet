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
from memnet.checkpoint import checkpoint_dir, run_checkpoint, verify_checkpoint
from memnet.cli import app
from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.neighbourhood_reserve import reserve
from memnet.registry import contains, count, get_entry
from memnet.session import (
    SessionStore,
    get_session,
    open_session,
    reset_registry,
    set_now_override,
)
from memnet.snapshot import load_snapshot

pytestmark = pytest.mark.xfail(reason="MN-REQ-05.5 not shipped; engine pending", strict=False)

runner = CliRunner()

ENV_MAX = "MEMNET_MAX_SESSIONS"
ENV_DIR = "MEMNET_EXPIRE_SNAPSHOT_DIR"  # reused; no second eviction knob
ENV_ALIAS = "MEMNET_SNAPSHOT_DIR"  # optional neutral alias; conflicting paths refuse start
ENV_ADMIN = "MEMNET_ADMIN_TOKEN"
ADMIN_TOKEN = "test-admin-token"  # dummy value for the in-process admin read
BASE = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
_MN_ID = re.compile(r"mn_[0-9a-fA-F]+")
_PLR = (
    "CREATE (:PLR {id: 'PLR01', identity: 'Hero', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)


# Surface lists. The MN-REQ-05.5 READ-SURFACES and ADMIN-READS blocks in
# sysml-models/models/requirements.sysml name the same entries;
# tests/test_sysml_session_evict.py asserts the two stay equal. READ_SURFACES
# is the MCP read tools plus the CLI-only reads (CLI_READ_ARGV) plus get_session.
READ_SURFACES = (
    "get_session",
    "pin_map",
    "query_warm",
    "find",
    "query_walk",
    "read_list",
    "export_pin_map",
    "housekeep_stats",
    "session_current",
    "session_resume",
    "tagmap_show",
    "relations_list",
    "query_neighbors",
    "query_path",
    "query_context",
    "housekeep_stale",
    "housekeep_orphans",
    "housekeep_dangling",
    "housekeep_recyclable",
)
ADMIN_READS = (
    "serve_status",
    "session_list",
    "admin_usage_report",
    "admin_checkpoint",
    "admin_checkpoint_verify",
)
# Arguments beyond the session for the MCP caller reads that need them.
_READ_ARGS = {
    "find": {"limit": 5, "kind": "PLR"},
    "query_walk": {"cue": "PLR01"},
    "read_list": {"tag": "PLR"},
}
# CLI-only caller reads (no MCP tool). "{sid}" is the session id; each argv
# names ids that workflow.example.txt seeds (PLR01, TEC01, E02).
CLI_READ_ARGV = {
    "session_resume": ("session", "resume", "{sid}"),
    "tagmap_show": ("tagmap", "show", "--session", "{sid}"),
    "relations_list": ("relations", "list", "--session", "{sid}"),
    "query_neighbors": ("query", "neighbors", "PLR01", "--session", "{sid}"),
    "query_path": ("query", "path", "PLR01", "TEC01", "--session", "{sid}"),
    "query_context": ("query", "context", "--session", "{sid}"),
    "housekeep_stale": ("housekeep", "stale", "--session", "{sid}"),
    "housekeep_orphans": ("housekeep", "orphans", "--session", "{sid}"),
    "housekeep_dangling": ("housekeep", "dangling", "--session", "{sid}"),
    "housekeep_recyclable": ("housekeep", "recyclable", "--session", "{sid}"),
}


def _at(minute: float) -> datetime:
    return BASE + timedelta(minutes=minute)


@pytest.fixture
def evict(memnet_temp, monkeypatch, tmp_path):
    """Cap 3, snapshot dir set, no touch window (LATER). Clock fixed to BASE."""
    snap_dir = tmp_path / "evict-snaps"
    snap_dir.mkdir()
    monkeypatch.setenv(ENV_MAX, "3")
    monkeypatch.setenv(ENV_DIR, str(snap_dir))
    monkeypatch.delenv(ENV_ALIAS, raising=False)
    set_now_override(BASE)
    return snap_dir


@pytest.fixture
def evict_pair(memnet_temp, monkeypatch, tmp_path):
    """Cap 2, snapshot dir set, clock frozen at BASE: every touch ties on modified_at."""
    snap_dir = tmp_path / "pair-snaps"
    snap_dir.mkdir()
    monkeypatch.setenv(ENV_MAX, "2")
    monkeypatch.setenv(ENV_DIR, str(snap_dir))
    monkeypatch.delenv(ENV_ALIAS, raising=False)
    set_now_override(BASE)
    return snap_dir


def _open(schema, minute: float, ttl: int = 600) -> SessionStore:
    set_now_override(_at(minute))
    return open_session(map_file=str(schema), ttl_minutes=ttl)


def _touch(sid: str, minute: float) -> SessionStore:
    set_now_override(_at(minute))
    return get_session(sid)


def _last_touch(sid: str):
    """Last touch is SessionMeta.modified_at, the field SessionStore.touch sets."""
    return get_entry(sid).meta.modified_at


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


def _instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _advanced(before: str | None, after: str | None) -> bool:
    if after is None:
        return False
    return before is None or _instant(after) > _instant(before)


def caller_read(surface: str, sid: str) -> int:
    """One session-scoped caller read through the surface named in READ_SURFACES.

    Returns the exit code. The text of a failure is not returned: it can name ids.
    get_session() raises on failure, so its exit code is 0 or the call raises.
    """
    if surface == "get_session":
        get_session(sid)
        return 0
    if surface in CLI_READ_ARGV:
        argv = [a.format(sid=sid) for a in CLI_READ_ARGV[surface]]
        return runner.invoke(app, argv).exit_code
    from memnet_mcp import server as mcp_server

    call = getattr(mcp_server, surface)
    resp = json.loads(asyncio.run(call(session=sid, **_READ_ARGS.get(surface, {}))))
    return resp["exit_code"]


def _admin_read(surface: str, ckpt_dir) -> None:
    """One admin or session-less read through the surface named in ADMIN_READS."""
    if surface == "serve_status":
        _serve_status_payload()
    elif surface == "session_list":
        from memnet_mcp import server as mcp_server

        asyncio.run(mcp_server.session_list())
    elif surface == "admin_usage_report":
        build_report(ADMIN_TOKEN)
    elif surface == "admin_checkpoint":
        run_checkpoint(ADMIN_TOKEN, directory=ckpt_dir)
    elif surface == "admin_checkpoint_verify":
        run_checkpoint(ADMIN_TOKEN, directory=ckpt_dir)
        verify_checkpoint(checkpoint_dir(ckpt_dir), ADMIN_TOKEN)
    else:
        raise AssertionError(f"no admin call for {surface}")


def _open_frozen(schema) -> SessionStore:
    """Open at the current (frozen) clock; does not move it."""
    return open_session(map_file=str(schema), ttl_minutes=600)


# Keys match by word or prefix: a segment starting with one of these names.
_CAP_KEY = re.compile(r"(^|_)(cap|limit|max_sessions|sessions_count|evict)")
# Raw text matches only these exact tokens, so ordinary words like "capacity" pass.
_CAP_TOKEN = re.compile(r"\b(max_sessions|sessions_count|evicted)\b")


def _keys_of(node) -> set[str]:
    if isinstance(node, dict):
        keys = set(node)
        for value in node.values():
            keys |= _keys_of(value)
        return keys
    if isinstance(node, list):
        keys: set[str] = set()
        for item in node:
            keys |= _keys_of(item)
        return keys
    return set()


def _assert_no_cap_text(text: str) -> None:
    assert not _CAP_TOKEN.search(text.lower()), "open/load output must not name a cap or eviction"


def _assert_no_cap_fields(payload: dict) -> None:
    bad = sorted(k for k in _keys_of(payload) if _CAP_KEY.search(k.lower()))
    assert not bad, f"open/load result carries cap-like keys: {bad}"
    _assert_no_cap_text(json.dumps(payload))


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


@pytest.mark.parametrize("surface", READ_SURFACES)
def test_caller_read_is_a_touch_and_moves_lru_pick(evict, schema_file, workflow_file, surface):
    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)  # valid ids for the reads; the write is at minute 0
    b = _open(schema_file, 1)
    c = _open(schema_file, 2)
    before = _last_touch(a.session_id)
    set_now_override(_at(3))
    assert caller_read(surface, a.session_id) == 0, f"{surface} read must succeed"
    assert _advanced(before, _last_touch(a.session_id)), f"{surface} must set modified_at"
    _open(schema_file, 4)
    assert not contains(b.session_id), f"after {surface} on a, b must be the victim"
    assert contains(a.session_id) and contains(c.session_id)


@pytest.mark.parametrize("surface", ADMIN_READS)
def test_admin_and_serve_status_reads_are_not_touches(
    evict, schema_file, monkeypatch, tmp_path, surface
):
    monkeypatch.setenv(ENV_ADMIN, ADMIN_TOKEN)
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    c = _open(schema_file, 2)
    before = _last_touch(a.session_id)
    set_now_override(_at(3))
    _admin_read(surface, tmp_path / "ckpt")
    assert _last_touch(a.session_id) == before, f"admin read {surface} must not move modified_at"
    _open(schema_file, 4)
    assert not contains(a.session_id), f"admin read {surface} must not change the victim pick"
    assert contains(b.session_id) and contains(c.session_id)


def test_tie_touch_order_a_then_b_evicts_a(evict_pair, schema_file):
    # Open order is B then A, so opening order alone would evict B. The final
    # touches are A, B, A, B: A's last touch is the earlier one, so A is the victim.
    b = _open_frozen(schema_file)
    a = _open_frozen(schema_file)
    for sid in (a.session_id, b.session_id, a.session_id, b.session_id):
        get_session(sid)  # frozen clock: every modified_at ties; touch_seq decides
    _open_frozen(schema_file)
    assert not contains(a.session_id), "the session touched first must be the victim"
    assert contains(b.session_id)


def test_tie_touch_order_b_then_a_evicts_b(evict_pair, schema_file):
    # Open order is A then B, so opening order alone would evict A. The final
    # touches are B, A, B, A: B's last touch is the earlier one, so B is the victim.
    a = _open_frozen(schema_file)
    b = _open_frozen(schema_file)
    for sid in (b.session_id, a.session_id, b.session_id, a.session_id):
        get_session(sid)  # frozen clock: every modified_at ties; touch_seq decides
    _open_frozen(schema_file)
    assert not contains(b.session_id), "the session touched first must be the victim"
    assert contains(a.session_id)


def test_open_assigns_touch_seq(evict, schema_file):
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    seq_a = get_entry(a.session_id).touch_seq
    seq_b = get_entry(b.session_id).touch_seq
    assert isinstance(seq_a, int) and isinstance(seq_b, int), "open must take a touch_seq"
    assert seq_b > seq_a, "a later open must take a later touch_seq"


def test_victim_order_compares_modified_at_as_instant(evict_pair, schema_file):
    # Whole-second stamp "...00Z" and fractional stamp "...00.500000Z": as strings
    # the fractional one sorts first ('.' < 'Z'), but as instants it is 0.5 s later.
    set_now_override(BASE)
    whole = open_session(map_file=str(schema_file), ttl_minutes=600)
    set_now_override(BASE + timedelta(milliseconds=500))
    fractional = open_session(map_file=str(schema_file), ttl_minutes=600)
    set_now_override(_at(1))
    open_session(map_file=str(schema_file), ttl_minutes=600)  # cap 2: one victim
    assert not contains(whole.session_id), "the oldest instant must be the victim"
    assert contains(fractional.session_id)


# --- S04: save first, atomic write, victim lock, crash safety ---------------


def test_victim_saved_before_drop_atomic_fsync(evict, schema_file, workflow_file, monkeypatch):
    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    _open(schema_file, 1)
    _open(schema_file, 2)
    victim = a.session_id
    snap_dir_stat = os.stat(evict)
    snap_dir_real = os.path.realpath(evict)
    events: list[str] = []  # kinds only; never a session id or path
    real_fsync, real_replace, real_rename = os.fsync, os.replace, os.rename
    real_drop, real_session_drop = registry_mod.remove_entry, session_mod.remove_entry

    def recording_fsync(fd):
        st = os.fstat(fd)
        if stat.S_ISDIR(st.st_mode):
            same = st.st_ino == snap_dir_stat.st_ino and st.st_dev == snap_dir_stat.st_dev
            events.append("dir_fsync_snap" if same else "dir_fsync_other")
        elif stat.S_ISREG(st.st_mode):
            events.append("file_fsync")
        return real_fsync(fd)

    def wrap_rename(real):
        def rename(src, dst, *args, **kwargs):
            if os.path.realpath(os.path.dirname(os.fspath(dst))) == snap_dir_real:
                events.append("rename_snap")
            return real(src, dst, *args, **kwargs)

        return rename

    def wrap_drop(real):
        def drop(*args, **kwargs):
            events.append("drop")
            return real(*args, **kwargs)

        return drop

    monkeypatch.setattr(os, "fsync", recording_fsync)
    monkeypatch.setattr(os, "replace", wrap_rename(real_replace))
    monkeypatch.setattr(os, "rename", wrap_rename(real_rename))
    monkeypatch.setattr(registry_mod, "remove_entry", wrap_drop(real_drop))
    monkeypatch.setattr(session_mod, "remove_entry", wrap_drop(real_session_drop))
    _open(schema_file, 4)
    assert not contains(victim)

    def step(kind: str, after: int) -> int:
        idx = next((i for i in range(after, len(events)) if events[i] == kind), None)
        assert idx is not None, f"no {kind} after step {after}: {events}"
        return idx

    file_sync = step("file_fsync", 0)
    renamed = step("rename_snap", file_sync)
    dir_sync = step("dir_fsync_snap", renamed)
    step("drop", dir_sync)  # RAM drop only after the snapshot dir is fsynced
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


def test_cap_full_with_snapshot_dir_evicts_oldest(evict, schema_file):
    # Positive control for the refusal test below: with the dir set, the same full cap evicts.
    a = _open(schema_file, 0)
    _open(schema_file, 1)
    _open(schema_file, 2)
    fresh = _open(schema_file, 4)
    assert not contains(a.session_id), "oldest session must be evicted when the dir is set"
    assert contains(fresh.session_id), "the fresh open must be live"
    _snapshot_of(evict, a.session_id)  # the victim's complete snapshot exists


def test_no_snapshot_dir_refuses_without_eviction(evict, schema_file, monkeypatch):
    monkeypatch.delenv(ENV_DIR, raising=False)
    monkeypatch.delenv(ENV_ALIAS, raising=False)
    ids = [_open(schema_file, m).session_id for m in (0, 1, 2)]
    with pytest.raises(MemNetError) as exc:
        _open(schema_file, 4)
    assert exc.value.code == "limit_exceeded"
    assert "all sessions are in use" in exc.value.message
    assert all(contains(sid) for sid in ids), "no eviction without a snapshot dir"
    for sid in ids:
        assert get_session(sid).session_id == sid, "every existing session must stay live"
    assert not any(evict.iterdir()), "no snapshot may be written without a dir"


def test_snapshot_dir_alias_conflict_refuses(tmp_path, monkeypatch):
    same = tmp_path / "snaps"
    same.mkdir()
    other = tmp_path / "other"
    monkeypatch.setenv(ENV_DIR, str(same))
    monkeypatch.setenv(ENV_ALIAS, str(same))
    Caps()  # the same path under both names is accepted
    monkeypatch.setenv(ENV_ALIAS, str(other))
    with pytest.raises(MemNetError) as exc:
        Caps()
    assert exc.value.code == "config_conflict", "two different snapshot dirs must refuse start"
    assert str(same) not in exc.value.message and str(other) not in exc.value.message, (
        "the refusal must not name either path"
    )


def test_cap_two_concurrent_opens_one_victim_per_slot(evict, schema_file, monkeypatch):
    monkeypatch.setenv(ENV_MAX, "2")
    a = _open(schema_file, 0)
    b = _open(schema_file, 1)
    victims = {a.session_id, b.session_id}
    set_now_override(_at(30))
    real_write = snapshot_mod.write_snapshot
    picked: set[str] = set()
    picked_lock = threading.Lock()
    both_picked = threading.Event()
    release = threading.Event()

    def held_write(ss, path, **kwargs):
        # Each victim stays mid-save (slot still held) until the late opens have run.
        if ss.session_id in victims:
            with picked_lock:
                picked.add(ss.session_id)
                if len(picked) == len(victims):
                    both_picked.set()
            release.wait(5)
        return real_write(ss, path, **kwargs)

    monkeypatch.setattr(snapshot_mod, "write_snapshot", held_write)
    opened: list[SessionStore] = []
    refused: list[MemNetError] = []
    errors: list[Exception] = []
    samples: list[int] = []
    stop = threading.Event()

    def worker():
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
    mon.start()
    pickers = [threading.Thread(target=worker) for _ in range(2)]
    for t in pickers:
        t.start()
    try:
        assert both_picked.wait(5), "both victims must be picked and mid-save"
        # Release window: victims are still live and mid-save, so the picking opens
        # must not have returned a session yet, and the cap is still full.
        assert count() == 2, "victims stay registered until their save and drop"
        assert not opened, "a picking open must not return before its victim is dropped"
        late = [threading.Thread(target=worker) for _ in range(2)]
        for t in late:
            t.start()
        for t in late:
            t.join(5)
        # Late opens see no evictable session (both victims are evicting) and are refused
        # at once, without queuing behind the victims' saves.
        assert len(refused) == 2, "late opens must be refused while the victims are mid-save"
        assert count() == 2 and not opened, "cap stays full and no open returns during the window"
    finally:
        release.set()
        for t in pickers:
            t.join(5)
        stop.set()
        mon.join(5)

    assert not errors, "only limit_exceeded refusals are allowed"
    assert len(opened) == 2, "exactly the two opens that picked a victim succeed"
    assert all(contains(s.session_id) for s in opened), (
        "each successful open is live after its drop"
    )
    assert all(e.code == "limit_exceeded" for e in refused)
    assert all("all sessions are in use" in e.message for e in refused)
    assert samples and max(samples) <= 2, "count must never exceed the cap"
    assert count() == 2
    assert not any(contains(sid) for sid in victims), "each victim is dropped after its save"
    assert len(list(evict.iterdir())) == 2, "one snapshot per victim"


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
    live = get_session(a.session_id)
    lease = reserve(
        live.reserves, live.store, anchor="PLR01", llm_id="llm-1", ttl_s=600, now=_at(3)
    )
    assert lease.rid in live.reserves.leases, "the lease must be held before eviction"
    _open(schema_file, 4)
    assert not contains(a.session_id), "a reserve lease alone does not exempt a session"
    assert contains(b.session_id)
    loaded = load_snapshot(_snapshot_of(evict, a.session_id))
    assert lease.rid not in loaded.reserves.leases, "the lease must be absent after load"
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


def test_open_and_load_results_carry_no_cap_fields(evict, schema_file, workflow_file):
    from memnet_mcp.server import session_load, session_open

    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    b = _open(schema_file, 1)
    _open(schema_file, 2)
    set_now_override(_at(3))
    cli_open = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])  # evicts a
    assert cli_open.exit_code == 0
    # CLI session open/load print wire lines, not JSON (only `version --json` does),
    # so the CLI side is checked by text token; the MCP side checks keys.
    _assert_no_cap_text(cli_open.stdout + cli_open.stderr)
    set_now_override(_at(4))
    mcp_open = json.loads(asyncio.run(session_open(map_file=str(schema_file))))  # evicts b
    assert mcp_open["exit_code"] == 0, mcp_open
    _assert_no_cap_fields(mcp_open)
    set_now_override(_at(5))
    mcp_load = json.loads(asyncio.run(session_load(file=str(_snapshot_of(evict, a.session_id)))))
    assert mcp_load["exit_code"] == 0, mcp_load
    _assert_no_cap_fields(mcp_load)
    set_now_override(_at(6))
    cli_load = runner.invoke(
        app, ["session", "load", "--file", str(_snapshot_of(evict, b.session_id)), "--keep-id"]
    )
    assert cli_load.exit_code == 0
    _assert_no_cap_text(cli_load.stdout + cli_load.stderr)


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
    live = get_session(victim)
    lease = reserve(
        live.reserves, live.store, anchor="PLR01", llm_id="llm-1", ttl_s=600, now=_at(0.5)
    )
    assert lease.rid in live.reserves.leases, "the lease must be held before eviction"
    _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)  # evicts a; a reserve lease alone does not exempt it
    snap = _snapshot_of(evict, victim)
    set_now_override(_at(5))
    loaded = load_snapshot(snap)
    assert lease.rid not in loaded.reserves.leases, "the lease must be absent after load"
    assert loaded.reserves.leases == {}, "restored session must carry no reserve leases"
    assert not (acl_to_dict(loaded.acl) or {}).get("bind"), "no bind may survive the restore"
    assert "worker-1" in loaded.acl.callers, "the ACL itself is kept"


def test_restore_lease_commit_fails_cleanly(evict, schema_file, workflow_file):
    # Real write path: MCP mutate (in-process), the same call an agent makes.
    # The wire names the dropped reserve as rid= and its holder as llm_id=.
    from memnet_mcp.server import mutate

    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    victim = a.session_id
    live = get_session(victim)
    lease = reserve(
        live.reserves, live.store, anchor="PLR01", llm_id="llm-1", ttl_s=600, now=_at(0.5)
    )
    assert lease.rid in live.reserves.leases, "the lease must be held before eviction"
    _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)  # evicts a while llm-1 holds a lease on PLR01
    snap = _snapshot_of(evict, victim)
    set_now_override(_at(5))
    loaded = load_snapshot(snap, keep_id=True)  # same id back, live, no lease
    assert lease.rid not in loaded.reserves.leases, "the lease must be absent after load"
    snap_bytes = snap.read_bytes()
    snap_mtime = snap.stat().st_mtime_ns
    rows_before = loaded.store.row_count_non_law()
    fields_before = dict(loaded.store.get("PLR01").fields)
    touch_before = _last_touch(victim)

    set_now_override(_at(6))
    res = json.loads(
        asyncio.run(
            mutate(
                wire_lines=["MATCH (n {id: 'PLR01'}) SET n.wealth = 999"],
                session=victim,
                llm_id="llm-1",
                rid=lease.rid,
            )
        )
    )
    assert res["exit_code"] != 0, "a commit naming a dropped lease must be refused"
    assert "@ERR: lease_lost|" in res["stderr"], "the refusal must carry code lease_lost"
    assert loaded.store.row_count_non_law() == rows_before, "no row may be added or dropped"
    assert dict(loaded.store.get("PLR01").fields) == fields_before, "PLR01 must be unchanged"
    assert snap.read_bytes() == snap_bytes, "the snapshot file must not be rewritten"
    assert snap.stat().st_mtime_ns == snap_mtime, "the snapshot mtime must not move"
    assert _last_touch(victim) == touch_before, "a refused commit is not a touch"


def test_no_rid_commit_after_evict_and_reload_succeeds(evict, schema_file, workflow_file):
    # lease_lost fires only when a rid is named. The reload drops the lease, so a
    # commit with no rid and no live lease is a plain commit and must succeed.
    from memnet_mcp.server import mutate

    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    victim = a.session_id
    live = get_session(victim)
    reserve(live.reserves, live.store, anchor="PLR01", llm_id="llm-1", ttl_s=600, now=_at(0.5))
    _open(schema_file, 1)
    _open(schema_file, 2)
    _open(schema_file, 4)  # evicts a while llm-1 holds a lease on PLR01
    snap = _snapshot_of(evict, victim)
    set_now_override(_at(5))
    loaded = load_snapshot(snap, keep_id=True)
    assert loaded.reserves.leases == {}, "the reload must carry no lease"

    set_now_override(_at(6))
    res = json.loads(
        asyncio.run(
            mutate(
                wire_lines=["MATCH (n {id: 'PLR01'}) SET n.wealth = 999"],
                session=victim,
                llm_id="llm-1",
            )
        )
    )
    assert res["exit_code"] == 0, "a commit with no rid must succeed after eviction and reload"
    assert get_session(victim).store.get("PLR01").fields["wealth"] == "999", "the field must change"


def test_rid_held_by_other_llm_refused_reserved(evict, schema_file, workflow_file):
    # A rid naming a live lease held by another llm_id hits the existing reserve
    # refusal (code reserved, MutateGate check_mutate_ids), not lease_lost.
    from memnet_mcp.server import mutate

    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    victim = a.session_id
    live = get_session(victim)
    lease = reserve(
        live.reserves, live.store, anchor="PLR01", llm_id="llm-1", ttl_s=600, now=_at(0.5)
    )
    fields_before = dict(live.store.get("PLR01").fields)
    touch_before = _last_touch(victim)

    set_now_override(_at(1))
    res = json.loads(
        asyncio.run(
            mutate(
                wire_lines=["MATCH (n {id: 'PLR01'}) SET n.wealth = 999"],
                session=victim,
                llm_id="llm-2",
                rid=lease.rid,
            )
        )
    )
    assert res["exit_code"] != 0, "llm-2 must not commit under llm-1's live lease"
    assert "@ERR: reserved|" in res["stderr"], "the refusal must carry code reserved"
    assert dict(live.store.get("PLR01").fields) == fields_before, "PLR01 must be unchanged"
    assert _last_touch(victim) == touch_before, "a refused commit is not a touch"


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


def test_touch_seq_not_in_snapshot_fresh_on_load(evict, schema_file, workflow_file):
    # touchSeqInSnapshot=false: the counter is not persisted; a load is a touch.
    a = _open(schema_file, 0)
    _seed(a.session_id, workflow_file)
    victim = a.session_id
    b = _open(schema_file, 1)
    c = _open(schema_file, 2)
    _open(schema_file, 4)  # evicts a
    snap = _snapshot_of(evict, victim)
    assert "touch_seq" not in snap.read_text(encoding="utf-8"), "snapshot must not carry touch_seq"
    set_now_override(_at(5))
    loaded = load_snapshot(snap)
    assert loaded.store.get("PLR01") is not None, "round trip must keep the rows"
    seq_loaded = get_entry(loaded.session_id).touch_seq
    others = [get_entry(s.session_id).touch_seq for s in (b, c)]
    assert seq_loaded > max(others), "a loaded session must get a fresh touch_seq above all others"
