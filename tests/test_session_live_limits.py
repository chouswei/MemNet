"""MN-REQ-05.6: change a live session's TTL and size caps (``session limits`` / ``set-limits``).

Driven through the public surfaces: the CLI argv (in-process serve handler), the MCP
tool functions, the product gateway, checkpoint and upgrade restore. The 0.20.8
rollback test runs the real 0.20.8 reader from git history on a file this build wrote.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest

from memnet.checkpoint import run_checkpoint
from memnet.in_process_engine import run_argv
from memnet.registry import get_entry
from memnet.serve import _handle_request
from memnet.serve_retry import RequestKind, argv_kind
from memnet.session import get_session, reset_registry, set_now_override
from memnet.upgrade import prepare_upgrade, reset_drain_gate, startup_restore_or_exit

BASE = datetime(2026, 11, 27, 6, 0, tzinfo=UTC)
TOKEN = "test-admin-token"
REPO = Path(__file__).resolve().parents[1]
BASE_COMMIT = "16813eb"  # MemNet 0.20.8, the build a rollback returns to


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _run(*argv: str, stdin: str | None = None) -> dict:
    return run_argv(list(argv), stdin=stdin)


def _ok(*argv: str, stdin: str | None = None) -> str:
    raw = _run(*argv, stdin=stdin)
    assert raw["exit_code"] == 0, raw["stderr"]
    return raw["stdout"]


def _open(schema_file: Path, ttl: int = 60) -> str:
    out = _ok("session", "open", "--map-file", str(schema_file), "--ttl", str(ttl))
    return out.split("@SESSION:", 1)[1].split("|", 1)[0].strip()


def _rows(sid: str, n: int, prefix: str = "r", goal: str = "g") -> None:
    gql = "".join(
        f"CREATE (:TSK {{id: 'TSK_{prefix}{i}', goal: '{goal}{i}', status: 'open'}})\n"
        for i in range(n)
    )
    _ok("mutate", "--stdin", "--session", sid, stdin=gql)


def _stats(stdout: str) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for line in stdout.splitlines():
        if line.startswith("@STAT: "):
            key, val, cap = line.removeprefix("@STAT: ").split("|", 2)
            out[key] = (val, cap)
    return out


def _limits(sid: str, *extra: str) -> dict[str, tuple[str, str]]:
    return _stats(_ok("session", "limits", "--session", sid, *extra))


def _set(sid: str, *flags: str) -> dict:
    return _run("session", "set-limits", "--session", sid, *flags)


def _row_count(sid: str) -> int:
    return get_entry(sid).store.row_count_non_law()


def _meta(sid: str) -> tuple:
    m = get_entry(sid).meta
    return (m.ttl_minutes, m.expires_at, m.max_rows, m.max_session_bytes)


@pytest.fixture
def clock(memnet_temp):
    set_now_override(BASE)
    yield BASE
    set_now_override(None)


@pytest.fixture
def state(memnet_temp, monkeypatch, tmp_path):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    monkeypatch.setenv("MEMNET_STATE_DIR", str(tmp_path))
    return tmp_path


def _cold_start() -> None:
    reset_registry()
    reset_drain_gate()


# --- TTL ---------------------------------------------------------------------------


def test_lower_ttl_restarts_clock_and_slides_by_new_ttl(clock, schema_file):
    sid = _open(schema_file, ttl=60)
    st = _stats(_set(sid, "--ttl", "5")["stdout"])
    assert st["ttl_minutes"] == ("5", "session")
    assert st["expires_at"][0] == _iso(BASE + timedelta(minutes=5))
    # A touch at +4 slides by the new TTL (5), not the old one (60).
    set_now_override(BASE + timedelta(minutes=4))
    assert _limits(sid)["expires_at"][0] == _iso(BASE + timedelta(minutes=9))
    # Past the new TTL the session expires exactly as any other session does.
    set_now_override(BASE + timedelta(minutes=15))
    gone = _run("session", "limits", "--session", sid)
    assert gone["exit_code"] != 0
    # The existing miss contract (no snapshot dir set here): the purge dropped it.
    assert gone["stderr"].startswith(("@ERR: session_expired|", "@ERR: session_not_found|"))
    assert sid not in gone["stderr"]
    assert get_entry(sid) is None


def test_lowered_ttl_never_makes_the_session_overdue_at_the_call(clock, schema_file):
    sid = _open(schema_file, ttl=60)
    # 30 minutes since the last touch, then ask for TTL 1: the clock restarts at the call.
    set_now_override(BASE + timedelta(minutes=30))
    st = _stats(_set(sid, "--ttl", "1")["stdout"])
    assert st["expires_at"][0] == _iso(BASE + timedelta(minutes=31))
    assert _row_count(sid) == 0 and get_entry(sid) is not None


def test_set_limits_on_an_already_overdue_session_is_session_expired(clock, schema_file):
    sid = _open(schema_file, ttl=5)
    set_now_override(BASE + timedelta(minutes=6))
    raw = _set(sid, "--ttl", "600")
    assert raw["exit_code"] != 0
    assert raw["stderr"].startswith(("@ERR: session_expired|", "@ERR: session_not_found|"))
    assert sid not in raw["stderr"]
    assert get_entry(sid) is None  # not revived by the larger TTL


def test_raise_ttl_survives_sliding_renew_and_save_load(clock, schema_file, tmp_path):
    sid = _open(schema_file, ttl=30)
    _rows(sid, 3)
    _set(sid, "--ttl", "600", "--max-rows", "50")
    set_now_override(BASE + timedelta(minutes=100))  # beyond the old TTL of 30
    assert _limits(sid)["ttl_minutes"] == ("600", "session")
    snap = tmp_path / "s.snap"
    _ok("session", "save", "--session", sid, "--file", str(snap))
    assert '#@LIM: {"max_rows":50}' in snap.read_text(encoding="utf-8")
    _ok("session", "close", sid)
    out = _ok("session", "load", "--file", str(snap), "--keep-id")
    assert sid in out
    st = _limits(sid)
    assert st["ttl_minutes"] == ("600", "session")
    assert st["max_rows"] == ("50", "session")
    assert st["rows"] == ("3", "50")
    # load --ttl still overrides the TTL, and keeps the cap.
    _ok("session", "close", sid)
    _ok("session", "load", "--file", str(snap), "--keep-id", "--ttl", "7")
    st = _limits(sid)
    assert st["ttl_minutes"] == ("7", "session")
    assert st["max_rows"] == ("50", "session")


# --- caps ----------------------------------------------------------------------------


def test_row_cap_raise_lower_and_enforce(memnet_temp, schema_file):
    sid = _open(schema_file)
    _rows(sid, 2)
    st = _stats(_set(sid, "--max-rows", "3")["stdout"])
    assert st["max_rows"] == ("3", "session")
    assert st["rows"] == ("2", "3")
    # A batch of 2 new rows crosses the cap: refused, rolled back.
    raw = _run(
        "mutate",
        "--stdin",
        "--session",
        sid,
        stdin="CREATE (:TSK {id: 'TSK_x1', goal: 'x', status: 'open'})\n"
        "CREATE (:TSK {id: 'TSK_x2', goal: 'x', status: 'open'})\n",
    )
    assert raw["exit_code"] != 0
    assert "@ERR: limit_exceeded|rows 4/3" in raw["stderr"]
    assert _row_count(sid) == 2
    # Updates to existing rows still apply at the cap.
    _rows(sid, 1, prefix="z")
    assert _row_count(sid) == 3
    done = "MATCH (n {id: 'TSK_r0'}) SET n.status = 'done'\n"
    _ok("mutate", "--stdin", "--session", sid, stdin=done)
    # Raise it again: new rows fit.
    _set(sid, "--max-rows", "10")
    _rows(sid, 2, prefix="y")
    assert _row_count(sid) == 5
    # default = the process cap again.
    st = _stats(_set(sid, "--max-rows", "default")["stdout"])
    assert st["max_rows"] == ("5000", "process")


def test_cap_equal_to_usage_is_allowed(memnet_temp, schema_file):
    sid = _open(schema_file)
    _rows(sid, 4)
    assert _set(sid, "--max-rows", "4")["exit_code"] == 0
    assert _limits(sid)["rows"] == ("4", "4")


def test_row_cap_below_usage_refuses_and_drops_nothing(memnet_temp, schema_file):
    sid = _open(schema_file)
    _rows(sid, 10)
    before = _meta(sid)
    raw = _set(sid, "--max-rows", "5", "--ttl", "9")
    assert raw["exit_code"] != 0
    assert "@ERR: limit_below_usage|rows 10/5\n" in raw["stderr"]
    assert _row_count(sid) == 10
    assert _meta(sid)[0] == before[0] and _meta(sid)[2:] == before[2:]


def test_byte_cap_lower_enforce_and_below_usage(memnet_temp, schema_file):
    sid = _open(schema_file)
    _rows(sid, 3)
    used = int(_limits(sid)["session_bytes"][0])
    assert _limits(sid)["max_session_bytes"] == ("163840000", "process")
    raw = _set(sid, "--max-bytes", str(used - 1))
    assert raw["exit_code"] != 0
    assert f"@ERR: limit_below_usage|session_bytes {used}/{used - 1}\n" in raw["stderr"]
    assert get_entry(sid).meta.max_session_bytes is None
    cap = used + 40
    st = _stats(_set(sid, "--max-bytes", str(cap))["stdout"])
    assert st["max_session_bytes"] == (str(cap), "session")
    assert st["session_bytes"] == (str(used), str(cap))
    long_goal = "x" * 200
    raw = _run(
        "mutate",
        "--stdin",
        "--session",
        sid,
        stdin=f"CREATE (:TSK {{id: 'TSK_big', goal: '{long_goal}', status: 'open'}})\n",
    )
    assert raw["exit_code"] != 0
    assert "@ERR: limit_exceeded|session_bytes " in raw["stderr"]
    assert f"/{cap}" in raw["stderr"]
    assert _row_count(sid) == 3


@pytest.mark.parametrize(
    ("flags", "err"),
    [
        ((), "@ERR: no_limit|give --ttl, --max-rows or --max-bytes"),
        (("--ttl", "0"), "@ERR: bad_ttl|ttl must be 1..1440"),
        (("--ttl", "1441"), "@ERR: bad_ttl|ttl must be 1..1440"),
        (("--ttl", "x"), "@ERR: bad_ttl|ttl must be 1..1440"),
        (("--max-rows", "0"), "@ERR: bad_limit|max_rows must be 1..5000"),
        (("--max-rows", "5001"), "@ERR: bad_limit|max_rows must be 1..5000"),
        (("--max-rows", "lots"), "@ERR: bad_limit|max_rows must be 1..5000"),
        (("--max-bytes", "163840001"), "@ERR: bad_limit|max_session_bytes must be 1..163840000"),
        # Mixed valid + invalid: nothing changes (the TTL is not applied either).
        (("--ttl", "9", "--max-rows", "-1"), "@ERR: bad_limit|max_rows must be 1..5000"),
        (("--max-rows", "9", "--ttl", "0"), "@ERR: bad_ttl|ttl must be 1..1440"),
    ],
)
def test_bad_values_refuse_and_change_nothing(clock, schema_file, flags, err):
    sid = _open(schema_file, ttl=60)
    before = _meta(sid)
    raw = _set(sid, *flags)
    assert raw["exit_code"] != 0
    assert raw["stderr"].splitlines()[0] == err
    assert _meta(sid) == before


# --- persistence and rollback ----------------------------------------------------------


def test_default_clears_the_lim_line_and_file_is_byte_identical(clock, schema_file, tmp_path):
    sid = _open(schema_file)
    _rows(sid, 2)
    plain = tmp_path / "plain.snap"
    _ok("session", "save", "--session", sid, "--file", str(plain))
    assert "#@LIM" not in plain.read_text(encoding="utf-8")
    _set(sid, "--max-rows", "100", "--max-bytes", "900000")
    capped = tmp_path / "capped.snap"
    _ok("session", "save", "--session", sid, "--file", str(capped))
    text = capped.read_text(encoding="utf-8")
    assert '#@LIM: {"max_rows":100,"max_session_bytes":900000}' in text
    _set(sid, "--max-rows", "default", "--max-bytes", "default")
    again = tmp_path / "again.snap"
    _ok("session", "save", "--session", sid, "--file", str(again))
    # Fixed clock: the cleared session writes the very bytes it wrote before any override.
    assert again.read_bytes() == plain.read_bytes()


def test_lim_line_dropped_loads_with_process_caps(memnet_temp, schema_file, tmp_path):
    """What 0.20.8 sees on rollback: no override, rows and TTL intact."""
    sid = _open(schema_file, ttl=45)
    _rows(sid, 4)
    _set(sid, "--max-rows", "4")
    snap = tmp_path / "s.snap"
    _ok("session", "save", "--session", sid, "--file", str(snap))
    lines = snap.read_text(encoding="utf-8").splitlines(keepends=True)
    snap.write_text("".join(x for x in lines if not x.startswith("#@LIM")), encoding="utf-8")
    _ok("session", "close", sid)
    _ok("session", "load", "--file", str(snap), "--keep-id")
    st = _limits(sid)
    assert st["rows"] == ("4", "5000")
    assert st["max_rows"] == ("5000", "process")
    assert st["ttl_minutes"] == ("45", "session")


def _old_reader(tmp_path: Path) -> Path:
    """The 0.20.8 engine source from git history, or skip when history is absent."""
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not installed")
    probe = subprocess.run(
        [git, "-C", str(REPO), "cat-file", "-e", f"{BASE_COMMIT}^{{commit}}"],
        capture_output=True,
        timeout=60,
    )
    if probe.returncode != 0:
        pytest.skip(f"commit {BASE_COMMIT} (0.20.8) is not in this clone")
    archive = subprocess.run(
        [git, "-C", str(REPO), "archive", "--format=tar", BASE_COMMIT, "parts/common/memnet"],
        capture_output=True,
        timeout=60,
    )
    assert archive.returncode == 0
    src = tmp_path / "src-0.20.8"
    with tarfile.open(fileobj=BytesIO(archive.stdout)) as tar:
        tar.extractall(src, filter="data")
    return src / "parts" / "common" / "memnet"


_OLD_LOAD = """
import json, sys
import memnet
from memnet.session import get_session
from memnet.snapshot import load_snapshot_text
text = open(sys.argv[1], encoding="utf-8").read()
ss = load_snapshot_text(text, keep_id=True)
ss = get_session(ss.session_id)
print(json.dumps({
    "file": memnet.__file__,
    "rows": ss.store.row_count_non_law(),
    "ttl": ss.meta.ttl_minutes,
    "max_rows": ss.caps.max_rows,
    "has_override": hasattr(ss.meta, "max_rows"),
}))
"""


def test_real_0_20_8_reader_loads_a_file_with_lim(memnet_temp, schema_file, tmp_path):
    sid = _open(schema_file, ttl=45)
    _rows(sid, 6)
    _set(sid, "--max-rows", "6", "--max-bytes", "500000")
    snap = tmp_path / "s.snap"
    _ok("session", "save", "--session", sid, "--file", str(snap))
    assert "#@LIM:" in snap.read_text(encoding="utf-8")
    old_src = _old_reader(tmp_path / "old")
    try:
        env = {k: v for k, v in os.environ.items() if not k.startswith("MEMNET_")}
        env["PYTHONPATH"] = str(old_src)
        env["MEMNET_TEST_INLINE"] = "1"
        proc = subprocess.run(
            [sys.executable, "-c", _OLD_LOAD, str(snap)],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        got = json.loads(proc.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp_path / "old", ignore_errors=True)
    assert got["file"].startswith(str(old_src)), got["file"]
    assert got["has_override"] is False  # really the 0.20.8 model
    assert got["rows"] == 6 and got["ttl"] == 45 and got["max_rows"] == 5000


def _saved(schema_file: Path, tmp_path: Path) -> tuple[str, Path, list[str]]:
    sid = _open(schema_file)
    _rows(sid, 2)
    _set(sid, "--max-rows", "40")
    snap = tmp_path / "s.snap"
    _ok("session", "save", "--session", sid, "--file", str(snap))
    _ok("session", "close", sid)
    return sid, snap, snap.read_text(encoding="utf-8").splitlines(keepends=True)


_BAD_LIM = [
    '#@LIM: {"max_rows":',
    '#@LIM: {"max_rows":0}',
    '#@LIM: ["x"]',
    '#@LIM: {"max_rows":"9"}',
]


@pytest.mark.parametrize("bad", _BAD_LIM)
def test_malformed_lim_line_is_bad_snapshot(memnet_temp, schema_file, tmp_path, bad):
    sid, snap, lines = _saved(schema_file, tmp_path)
    snap.write_text(
        "".join(bad + "\n" if x.startswith("#@LIM") else x for x in lines), encoding="utf-8"
    )
    raw = _run("session", "load", "--file", str(snap), "--keep-id")
    assert raw["exit_code"] != 0
    assert "@ERR: bad_snapshot|malformed LIM line" in raw["stderr"]
    assert get_entry(sid) is None


def test_unknown_lim_key_loads_and_over_cap_value_is_clamped(
    memnet_temp, schema_file, tmp_path, monkeypatch
):
    sid, snap, lines = _saved(schema_file, tmp_path)
    lim = '#@LIM: {"future_knob":3,"max_rows":40}\n'
    snap.write_text("".join(lim if x.startswith("#@LIM") else x for x in lines), encoding="utf-8")
    _ok("session", "load", "--file", str(snap), "--keep-id")
    assert _limits(sid)["max_rows"] == ("40", "session")
    _ok("session", "close", sid)
    # A process with a lower MEMNET_MAX_ROWS clamps the override, with a warning.
    monkeypatch.setenv("MEMNET_MAX_ROWS", "30")
    raw = _run("session", "load", "--file", str(snap), "--keep-id")
    assert raw["exit_code"] == 0, raw["stderr"]
    assert "@WRN: limit_clamped|max_rows 40/30" in raw["stderr"]
    assert _limits(sid)["max_rows"] == ("30", "session")


def test_checkpoint_restart_restores_ttl_and_caps(state, schema_file):
    sid = _open(schema_file, ttl=30)
    _rows(sid, 3)
    _set(sid, "--ttl", "700", "--max-rows", "8", "--max-bytes", "600000")
    want = _meta(sid)
    assert run_checkpoint(TOKEN, directory=state).saved == 1
    _cold_start()
    report = startup_restore_or_exit(state)
    assert report.ok == 1
    assert _meta(sid) == want
    assert get_entry(sid).store.row_cap == 8
    assert _row_count(sid) == 3
    verify = _run("admin", "checkpoint-verify", str(state / "checkpoint"), "--token", TOKEN)
    assert verify["exit_code"] == 0, verify["stderr"]


def test_upgrade_prepare_restore_keeps_clocks_ttl_and_caps(state, schema_file):
    sid = _open(schema_file, ttl=30)
    _rows(sid, 3)
    _set(sid, "--ttl", "900", "--max-rows", "8")
    want = _meta(sid)
    assert prepare_upgrade(TOKEN, directory=state).ready_to_stop is True
    # set-limits is a write: refused while draining, nothing changes.
    drained = _handle_request({"args": ["session", "set-limits", "--session", sid, "--ttl", "5"]})
    assert drained["exit_code"] != 0
    assert "@ERR: serve_draining|" in drained["stderr"]
    _cold_start()
    report = startup_restore_or_exit(state)
    assert report.ok == 1
    assert _meta(sid) == want  # preserve_clocks: expires_at unchanged too
    assert _limits(sid)["max_rows"] == ("8", "session")


# --- who may change limits ---------------------------------------------------------------


def test_acl_mutate_grant_needed_to_set_pin_map_to_read(memnet_temp, schema_file):
    sid = _open(schema_file)
    _ok("session", "acl-enable", "--session", sid)
    _ok("session", "acl-grant", "--caller", "reader", "--no-mutate", "--session", sid)
    _ok("session", "acl-grant", "--caller", "writer", "--session", sid)
    _ok("session", "acl-grant", "--caller", "blind", "--no-pin-map", "--session", sid)
    before = _meta(sid)
    no_who = _set(sid, "--ttl", "9")
    assert no_who["stderr"].startswith("@ERR: acl_who|")
    stranger = _set(sid, "--ttl", "9", "--caller", "nobody")
    assert stranger["stderr"].startswith("@ERR: acl_denied|")
    reader = _set(sid, "--ttl", "9", "--caller", "reader")
    assert reader["stderr"].startswith("@ERR: acl_forbidden|")
    assert _meta(sid)[0] == before[0]
    assert _limits(sid, "--caller", "reader")["ttl_minutes"] == ("60", "session")
    blind = _run("session", "limits", "--session", sid, "--caller", "blind")
    assert blind["stderr"].startswith("@ERR: acl_forbidden|")
    ok = _set(sid, "--ttl", "9", "--caller", "writer")
    assert ok["exit_code"] == 0, ok["stderr"]
    assert get_entry(sid).meta.ttl_minutes == 9


# --- concurrency ---------------------------------------------------------------------------


def test_set_limits_waits_for_the_entry_lock(clock, schema_file):
    sid = _open(schema_file, ttl=60)
    ss = get_session(sid)
    done = threading.Event()
    result: dict = {}

    def setter() -> None:
        result.update(_set(sid, "--ttl", "20"))
        done.set()

    with ss.lock(exclusive=True):
        t = threading.Thread(target=setter)
        t.start()
        assert not done.wait(0.3), "set-limits must wait for the writer holding the lock"
        assert get_entry(sid).meta.ttl_minutes == 60
    t.join(10)
    assert result["exit_code"] == 0, result.get("stderr")
    assert get_entry(sid).meta.ttl_minutes == 20


def test_sliding_renew_racing_set_limits_never_keeps_an_old_ttl_expiry(
    clock, schema_file, monkeypatch
):
    """A read slides expires_at outside the entry lock. Pause one read inside its slide,
    run set-limits --ttl 5 meanwhile, then let the read finish: the expiry must still
    follow the TTL in force (5), never the TTL the paused read saw (60)."""
    import memnet.session as session_mod

    sid = _open(schema_file, ttl=60)
    in_slide = threading.Event()
    release = threading.Event()
    reader_calls = []

    def paused_now() -> datetime:
        # get_session reads the clock twice: the overdue check, then the slide. Pause
        # in the slide, i.e. after the reader may have read the TTL.
        if threading.current_thread().name == "paused-reader":
            reader_calls.append(1)
            if len(reader_calls) == 2:
                in_slide.set()
                release.wait(10)
        return BASE

    monkeypatch.setattr(session_mod, "utc_now", paused_now)
    reader = threading.Thread(target=get_session, args=(sid,), name="paused-reader")
    reader.start()
    assert in_slide.wait(10)
    result: dict = {}
    setter = threading.Thread(target=lambda: result.update(_set(sid, "--ttl", "5")))
    setter.start()
    setter.join(0.5)  # pre-fix: done here, and the paused read then writes +60
    release.set()
    reader.join(10)
    setter.join(10)
    assert result["exit_code"] == 0, result.get("stderr")
    m = get_entry(sid).meta
    assert m.ttl_minutes == 5
    assert m.expires_at == _iso(BASE + timedelta(minutes=5))


# --- MCP, gateway, retry class -------------------------------------------------------------


def test_mcp_tools_map_args_and_pass_default(memnet_temp, schema_file):
    from memnet_mcp.server import session_limits, session_set_limits

    sid = _open(schema_file)
    _rows(sid, 2)
    resp = json.loads(asyncio.run(session_set_limits(session=sid, ttl=15, max_rows=7)))
    assert resp["exit_code"] == 0, resp
    assert "@STAT: max_rows|7|session" in resp["stdout"]
    assert "@STAT: ttl_minutes|15|session" in resp["stdout"]
    resp = json.loads(asyncio.run(session_set_limits(session=sid, max_rows="default")))
    assert "@STAT: max_rows|5000|process" in resp["stdout"]
    resp = json.loads(asyncio.run(session_set_limits(session=sid, max_rows=1)))
    assert resp["exit_code"] != 0
    assert "limit_below_usage" in resp["stderr"]
    read = json.loads(asyncio.run(session_limits(session=sid)))
    assert read["exit_code"] == 0
    assert "@STAT: rows|2|5000" in read["stdout"]


def test_existing_session_tools_are_unchanged(memnet_temp, schema_file):
    """Old callers: open and list print what they printed before; no new lines."""
    sid = _open(schema_file, ttl=60)
    listed = _ok("session", "list")
    assert "max_rows" not in listed and "ttl_minutes" not in listed
    assert sid in listed


def test_gateway_set_limits_on_a_foreign_session_is_forbidden(monkeypatch, tmp_path):
    from memnet import __version__
    from memnet_mcp.product_gateway import ProductGateway
    from test_product_gateway import ATELIER, ENDLEAF, _config

    calls: list[list[str]] = []

    def fake_send(args, stdin=None, **_kw):
        calls.append(list(args))
        if args == ["version"]:
            return {"exit_code": 0, "stdout": f"@VER: memnet|{__version__}\n", "stderr": ""}
        if args[:2] == ["session", "open"]:
            return {"exit_code": 0, "stdout": "@SESSION: mn_xxxxxxxx|soon|60\n", "stderr": ""}
        return {"exit_code": 0, "stdout": "@STAT: ttl_minutes|9|session\n", "stderr": ""}

    monkeypatch.setattr("memnet_mcp.product_gateway.send_command", fake_send)
    cfg = tmp_path / "gw.json"
    _config(cfg, tmp_path / "owners.json", 1, 2)
    gw = ProductGateway.load(str(cfg))

    def post(token: str, args: list[str]):
        return gw.handle(
            method="POST",
            path="/gateway",
            authorization=f"Bearer {token}",
            body=json.dumps({"args": args}).encode(),
        )

    assert post(ENDLEAF, ["session", "open", "--map-file", "m.txt"]).exit_code == 0
    argv = ["session", "set-limits", "--session", "mn_xxxxxxxx", "--ttl", "9"]
    foreign = post(ATELIER, argv)
    assert foreign.http_status == 403
    assert foreign.stderr.startswith("@ERR: gateway_forbidden_session|")
    assert argv not in calls  # never forwarded
    owned = post(ENDLEAF, argv)
    assert owned.exit_code == 0
    assert calls[-1] == argv  # forwarded unchanged


def test_retry_class_limits_is_read_set_limits_is_write():
    assert argv_kind(["session", "limits", "--session", "mn_xxxxxxxx"]) is RequestKind.READ
    assert argv_kind(["session", "set-limits", "--session", "mn_xxxxxxxx"]) is RequestKind.WRITE
