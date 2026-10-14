"""MN-REQ-06.16 — the session ACL persists in snapshots and restores on load."""

from __future__ import annotations

import stat

import pytest

from memnet.acl import acl_from_dict, acl_to_dict, check_bind, lease_digest
from memnet.exceptions import MemNetError
from memnet.in_process_engine import run_argv
from memnet.registry import get_entry, remove_entry
from memnet.session import open_session
from memnet.snapshot import load_snapshot, write_snapshot

_TSK = "CREATE (:TSK {id: 'TSK_acl', goal: 'bound', status: 'open'})\n"
_TSK2 = "CREATE (:TSK {id: 'TSK_two', goal: 'refused', status: 'open'})\n"


def _acl_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.startswith("#@ACL:")]


def _without_acl(text: str) -> str:
    """The same snapshot with the ACL line removed (format unchanged)."""
    return "".join(ln + "\n" for ln in text.splitlines() if not ln.startswith("#@ACL:"))


def _as_format_1(text: str) -> str:
    """The same snapshot as a format 1 writer produced it: @SNAP version 1, no ACL line."""
    return _without_acl(text).replace("\n@SNAP: 2|", "\n@SNAP: 1|", 1)


def _grants(ss) -> None:
    ss.grant_caller("owner", can_pin_map=True, can_mutate=True)
    ss.grant_caller("writer", can_pin_map=True, can_mutate=True, write_scope="labels=TSK")
    ss.grant_caller("reader", can_pin_map=True, can_mutate=False)
    ss.set_bind("mission-demo", "lease-demo")


def test_round_trip_keeps_enable_flag_grants_and_bind(memnet_temp, schema_file, tmp_path):
    ss = open_session(map_file=str(schema_file))
    _grants(ss)
    before = acl_to_dict(ss.acl)
    path = tmp_path / "acl.snap"
    write_snapshot(ss, path)

    text = path.read_text(encoding="utf-8")
    assert "\n@SNAP: 2|" in text  # format 2 carries the ACL line
    lines = _acl_lines(text)
    assert len(lines) == 1
    assert lines[0].startswith("#")  # a comment line: readers that predate it skip it

    remove_entry(ss.session_id)
    load_snapshot(path, keep_id=True)
    entry = get_entry(ss.session_id)
    assert entry is not None and entry.acl is not None
    assert entry.acl.enabled is True
    assert entry.meta.acl_enabled is True
    assert acl_to_dict(entry.acl) == before
    assert entry.acl.callers["writer"].write_scope.labels == frozenset({"TSK"})
    assert entry.acl.callers["reader"].can_mutate is False


@pytest.mark.parametrize("enable", [False, True], ids=["off", "on-no-grants"])
def test_enable_flag_round_trips_without_grants(memnet_temp, schema_file, tmp_path, enable):
    ss = open_session(map_file=str(schema_file))
    if enable:
        ss.enable_acl()
    path = tmp_path / "flag.snap"
    write_snapshot(ss, path)
    remove_entry(ss.session_id)
    load_snapshot(path, keep_id=True)
    entry = get_entry(ss.session_id)
    assert entry is not None and entry.acl is not None
    assert entry.acl.enabled is enable
    assert entry.acl.callers == {}


def test_cli_save_and_load_report_restored_acl(memnet_temp, schema_file, tmp_path):
    ss = open_session(map_file=str(schema_file))
    _grants(ss)
    path = tmp_path / "cli.snap"
    saved = run_argv(
        ["session", "save", "--file", str(path), "--session", ss.session_id, "--caller", "owner"]
    )
    assert saved["exit_code"] == 0, saved["stderr"]
    remove_entry(ss.session_id)
    loaded = run_argv(["session", "load", "--file", str(path), "--keep-id"])
    assert loaded["exit_code"] == 0, loaded["stderr"]
    assert "@ACL: loaded|enabled=1|callers=3|bind=1" in loaded["stdout"]
    assert "mission-demo" not in loaded["stdout"]  # the bind lease is never printed


def test_format_1_snapshot_loads_with_acl_off(memnet_temp, schema_file, tmp_path):
    ss = open_session(map_file=str(schema_file))
    assert run_argv(["mutate", "--stdin", "--session", ss.session_id], stdin=_TSK)["exit_code"] == 0
    path = tmp_path / "old.snap"
    write_snapshot(ss, path)
    old = _as_format_1(path.read_text(encoding="utf-8"))
    assert "#@ACL:" not in old
    assert "\n@SNAP: 1|" in old
    path.write_text(old, encoding="utf-8")

    remove_entry(ss.session_id)
    loaded = run_argv(["session", "load", "--file", str(path), "--keep-id"])
    assert loaded["exit_code"] == 0, loaded["stderr"]
    assert "@ACL: absent|off" in loaded["stdout"]
    assert "@ACL: loaded" not in loaded["stdout"]
    entry = get_entry(ss.session_id)
    assert entry is not None
    assert entry.acl is None
    assert entry.meta.acl_enabled is False
    # ACL off: a mutate with no caller is allowed, as it was before MN-REQ-06.16.
    assert (
        run_argv(["mutate", "--stdin", "--session", ss.session_id], stdin=_TSK2)["exit_code"] == 0
    )


def test_format_2_missing_acl_line_fails_bad_snapshot(memnet_temp, schema_file, tmp_path):
    ss = open_session(map_file=str(schema_file))
    _grants(ss)
    path = tmp_path / "v2-no-acl.snap"
    write_snapshot(ss, path)
    text = _without_acl(path.read_text(encoding="utf-8"))
    assert "\n@SNAP: 2|" in text
    path.write_text(text, encoding="utf-8")

    remove_entry(ss.session_id)
    with pytest.raises(MemNetError) as exc:
        load_snapshot(path, keep_id=True)
    assert exc.value.code == "bad_snapshot"
    assert get_entry(ss.session_id) is None  # never loaded with ACL silently off

    loaded = run_argv(["session", "load", "--file", str(path), "--keep-id"])
    assert loaded["exit_code"] != 0
    assert "bad_snapshot" in loaded["stdout"] + loaded["stderr"]
    assert "@ACL: absent|off" not in loaded["stdout"]
    assert get_entry(ss.session_id) is None


def test_snapshot_files_are_mode_0600_and_replace_loose_modes(memnet_temp, schema_file, tmp_path):
    ss = open_session(map_file=str(schema_file))
    _grants(ss)
    path = tmp_path / "private.snap"
    path.write_text("stale", encoding="utf-8")
    path.chmod(0o644)
    write_snapshot(ss, path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(tmp_path.glob("*.tmp")) == []  # the temp file was renamed, not left behind

    cli_path = tmp_path / "cli-private.snap"
    saved = run_argv(
        [
            "session",
            "save",
            "--file",
            str(cli_path),
            "--session",
            ss.session_id,
            "--caller",
            "owner",
        ]
    )
    assert saved["exit_code"] == 0, saved["stderr"]
    assert stat.S_IMODE(cli_path.stat().st_mode) == 0o600


def test_bind_stores_only_a_digest_of_the_lease(memnet_temp, schema_file, tmp_path):
    ss = open_session(map_file=str(schema_file))
    _grants(ss)
    path = tmp_path / "bind.snap"
    write_snapshot(ss, path)
    text = path.read_text(encoding="utf-8")
    assert "lease-demo" not in text
    assert lease_digest("lease-demo") in text

    remove_entry(ss.session_id)
    load_snapshot(path, keep_id=True)
    acl = get_entry(ss.session_id).acl
    check_bind(acl, mission_id="mission-demo", lease="lease-demo", require=True)
    with pytest.raises(MemNetError) as exc:
        check_bind(acl, mission_id="mission-demo", lease="lease-other", require=True)
    assert exc.value.code == "acl_bind"


def test_pre_digest_raw_lease_still_binds_on_load():
    acl = acl_from_dict(
        {
            "enabled": True,
            "callers": [],
            "bind": {"mission_id": "mission-demo", "lease": "lease-demo"},
        }
    )
    assert acl.bind is not None and acl.bind.lease_sha256 == lease_digest("lease-demo")
    check_bind(acl, mission_id="mission-demo", lease="lease-demo", require=True)


def test_malformed_bind_digest_fails_closed():
    with pytest.raises(MemNetError) as exc:
        acl_from_dict(
            {"enabled": True, "callers": [], "bind": {"mission_id": "m", "lease_sha256": "nope"}}
        )
    assert exc.value.code == "bad_snapshot"


def test_reader_only_caller_is_refused_after_reload(memnet_temp, schema_file, tmp_path):
    ss = open_session(map_file=str(schema_file))
    _grants(ss)
    sid = ss.session_id
    assert (
        run_argv(["mutate", "--stdin", "--session", sid, "--caller", "owner"], stdin=_TSK)[
            "exit_code"
        ]
        == 0
    )
    path = tmp_path / "reader.snap"
    assert (
        run_argv(["session", "save", "--file", str(path), "--session", sid, "--caller", "owner"])[
            "exit_code"
        ]
        == 0
    )

    remove_entry(sid)
    assert run_argv(["session", "load", "--file", str(path), "--keep-id"])["exit_code"] == 0
    entry = get_entry(sid)
    assert entry is not None and entry.acl is not None and entry.acl.enabled is True
    rows = entry.store.row_count_non_law()

    refused = run_argv(["mutate", "--stdin", "--session", sid, "--caller", "reader"], stdin=_TSK2)
    assert refused["exit_code"] != 0
    assert "acl_forbidden" in refused["stdout"] + refused["stderr"]
    assert get_entry(sid).store.row_count_non_law() == rows  # the write did not land

    allowed = run_argv(["mutate", "--stdin", "--session", sid, "--caller", "writer"], stdin=_TSK2)
    assert allowed["exit_code"] == 0, allowed["stderr"]


def test_keep_id_reload_restores_acl_and_fresh_id_does_too(memnet_temp, schema_file, tmp_path):
    ss = open_session(map_file=str(schema_file))
    _grants(ss)
    before = acl_to_dict(ss.acl)
    sid = ss.session_id
    path = tmp_path / "keep.snap"
    write_snapshot(ss, path)

    remove_entry(sid)
    kept = run_argv(["session", "load", "--file", str(path), "--keep-id"])
    assert kept["exit_code"] == 0, kept["stderr"]
    assert f"@SESSION: {sid}" in kept["stdout"]
    kept_entry = get_entry(sid)
    assert kept_entry is not None and acl_to_dict(kept_entry.acl) == before

    fresh = load_snapshot(path)
    assert fresh.session_id != sid
    fresh_entry = get_entry(fresh.session_id)
    assert fresh_entry is not None and acl_to_dict(fresh_entry.acl) == before


def test_malformed_acl_line_fails_closed(memnet_temp, schema_file, tmp_path):
    ss = open_session(map_file=str(schema_file))
    _grants(ss)
    path = tmp_path / "bad.snap"
    write_snapshot(ss, path)
    text = path.read_text(encoding="utf-8")
    (line,) = _acl_lines(text)
    path.write_text(text.replace(line, "#@ACL: {not json"), encoding="utf-8")

    remove_entry(ss.session_id)
    with pytest.raises(MemNetError) as exc:
        load_snapshot(path, keep_id=True)
    assert exc.value.code == "bad_snapshot"
    assert get_entry(ss.session_id) is None  # never loaded with ACL silently off
