"""Serve restart restores the newest valid snapshot set, every time (MN-REQ-06.14, 06.15).

Candidates are the admin checkpoint and the upgrade-prepare manifest. Newest wins, a tie
goes to upgrade, a retired manifest stays a candidate, a broken newer set falls back
loudly, and no valid set at all exits 3.
"""

from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

import pytest

import memnet.upgrade as upgrade_mod
from memnet.checkpoint import run_checkpoint
from memnet.in_process_engine import run_argv
from memnet.registry import count, get_entry
from memnet.serve import probe, send_command
from memnet.session import open_session, reset_registry, utc_now
from memnet.upgrade import (
    BLOCKED_NAME,
    MANIFEST_NAME,
    RESTORE_NAME,
    prepare_upgrade,
    reset_drain_gate,
    startup_restore_or_exit,
)

TOKEN = "test-admin-token"
CKPT_MANIFEST = Path("checkpoint") / "checkpoint-manifest.json"
_RECORD = re.compile(r"^@([A-Z]+): ([^|]*)\|")


# --- in-process helpers ---------------------------------------------------------------


def _mutate(sid: str, text: str) -> None:
    raw = run_argv(["mutate", "--stdin", "--session", sid], stdin=text)
    assert raw["exit_code"] == 0, raw["stderr"]


def _find(sid: str) -> str:
    raw = run_argv(["query", "find", "--kind", "TSK", "--limit", "20", "--session", sid])
    assert raw["exit_code"] == 0, raw["stderr"]
    return raw["stdout"]


def _two_nodes(sid: str, tag: str) -> None:
    _mutate(
        sid,
        f"CREATE (:TSK {{id: 'TSK_{tag}1', goal: '{tag}-one', status: 'open'}})\n"
        f"CREATE (:TSK {{id: 'TSK_{tag}2', goal: '{tag}-two', status: 'open'}})\n"
        f"MATCH (a {{id: 'TSK_{tag}1'}}), (b {{id: 'TSK_{tag}2'}}) "
        f"CREATE (a)-[:owns {{id: 'E_{tag}'}}]->(b)\n",
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _set_timestamp(path: Path, stamp: str) -> None:
    data = _read_json(path)
    data["timestamp"] = stamp
    _write_json(path, data)


def _corrupt(path: Path) -> bytes:
    data = path.read_bytes()
    path.write_bytes(data[:40] + b"XXXX" + data[44:])
    return path.read_bytes()


def _cold_start() -> None:
    reset_registry()
    reset_drain_gate()


@pytest.fixture
def state(memnet_temp, monkeypatch, tmp_path):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    monkeypatch.setenv("MEMNET_STATE_DIR", str(tmp_path))
    return tmp_path


# --- in-process: precedence, fallback, failure ----------------------------------------


def test_field_case_retired_legacy_prepare_and_newer_checkpoint_restores_checkpoint(
    state, schema_file, capsys
):
    plain = open_session(map_file=str(schema_file), ttl_minutes=30, product="gateapp")
    _two_nodes(plain.session_id, "p")
    guarded = open_session(map_file=str(schema_file), ttl_minutes=30)
    _two_nodes(guarded.session_id, "g")
    soon = (utc_now() + timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    guarded.meta.expires_at = soon
    guarded.enable_acl()
    guarded.grant_caller("caller-demo", can_pin_map=True, can_mutate=False)
    assert prepare_upgrade(TOKEN, directory=state).ready_to_stop is True
    # The field's 11-03 manifest: no timestamp, already retired, mtime a day old.
    legacy = state / MANIFEST_NAME
    data = _read_json(legacy)
    data.pop("timestamp", None)
    data["retired"] = True
    _write_json(legacy, data)
    old = time.time() - 86400
    os.utime(legacy, (old, old))
    reset_drain_gate()
    _mutate(plain.session_id, "CREATE (:TSK {id: 'TSK_late', goal: 'late-fact', status: 'open'})\n")
    assert run_checkpoint(TOKEN, directory=state).saved == 2
    want = {
        plain.session_id: get_entry(plain.session_id).meta.expires_at,
        guarded.session_id: soon,
    }
    ckpt_stamp = _read_json(state / CKPT_MANIFEST)["timestamp"]
    _cold_start()
    capsys.readouterr()

    report = startup_restore_or_exit(state)

    out = capsys.readouterr()
    assert report.ok == 2, "the newer checkpoint must be restored (today: 0 sessions)"
    assert report.failed == 0
    assert set(report.session_ids) == set(want)
    assert getattr(report, "source", None) == "checkpoint"
    assert getattr(report, "timestamp", None) == ckpt_stamp
    assert getattr(report, "rejected", None) == []
    for sid, expires in want.items():
        entry = get_entry(sid)
        assert entry is not None
        assert entry.meta.session_id == sid
        assert entry.meta.expires_at == expires
    assert get_entry(plain.session_id).meta.product == "gateapp"
    back = get_entry(guarded.session_id)
    assert back.acl is not None and back.acl.enabled is True
    assert back.acl.callers["caller-demo"].can_pin_map is True
    assert "late-fact" in _find(plain.session_id)
    assert f"@STAT: restore_source|checkpoint|{ckpt_stamp}" in out.out
    assert f"@STAT: restore_source|checkpoint|{ckpt_stamp}" in out.err
    written = _read_json(state / RESTORE_NAME)
    assert written.get("source") == "checkpoint"
    assert written.get("timestamp") == ckpt_stamp
    assert written.get("timestamp_source") == "manifest"
    assert written.get("manifest") == str(CKPT_MANIFEST)
    assert written.get("rejected") == []
    assert _read_json(legacy)["retired"] is True


def test_legacy_prepare_alone_restores_by_mtime_and_again_when_retired(state, schema_file):
    ss = open_session(map_file=str(schema_file), ttl_minutes=30)
    _two_nodes(ss.session_id, "m")
    assert prepare_upgrade(TOKEN, directory=state).ready_to_stop is True
    legacy = state / MANIFEST_NAME
    data = _read_json(legacy)
    data.pop("timestamp", None)
    data["retired"] = True
    _write_json(legacy, data)
    _cold_start()

    report = startup_restore_or_exit(state)

    assert report.ok == 1, "a retired manifest must stay a candidate (today: skipped)"
    assert get_entry(ss.session_id) is not None
    assert getattr(report, "source", None) == "upgrade"
    written = _read_json(state / RESTORE_NAME)
    assert written.get("timestamp_source") == "mtime"
    assert written.get("manifest") == MANIFEST_NAME


def test_tie_goes_to_upgrade(state, schema_file):
    ss = open_session(map_file=str(schema_file), ttl_minutes=30)
    sid = ss.session_id
    _two_nodes(sid, "t")
    assert prepare_upgrade(TOKEN, directory=state).ready_to_stop is True
    reset_drain_gate()
    _mutate(sid, "CREATE (:TSK {id: 'TSK_ck', goal: 'checkpoint-only', status: 'open'})\n")
    assert run_checkpoint(TOKEN, directory=state).saved == 1
    stamp = "2026-01-02T03:04:05Z"
    _set_timestamp(state / MANIFEST_NAME, stamp)
    _set_timestamp(state / CKPT_MANIFEST, stamp)
    _cold_start()

    report = startup_restore_or_exit(state)

    assert report.ok == 1
    assert getattr(report, "source", None) == "upgrade"
    assert getattr(report, "timestamp", None) == stamp
    assert "t-one" in _find(sid)
    assert "checkpoint-only" not in _find(sid)


def test_corrupt_newest_checkpoint_falls_back_to_upgrade_loudly(state, schema_file, capsys):
    ss = open_session(map_file=str(schema_file), ttl_minutes=30)
    sid = ss.session_id
    _two_nodes(sid, "c")
    expires = get_entry(sid).meta.expires_at
    assert prepare_upgrade(TOKEN, directory=state).ready_to_stop is True
    reset_drain_gate()
    _mutate(sid, "CREATE (:TSK {id: 'TSK_ck', goal: 'checkpoint-only', status: 'open'})\n")
    assert run_checkpoint(TOKEN, directory=state).saved == 1
    snap = next((state / "checkpoint").glob("*.snap"))
    broken = _corrupt(snap)
    _cold_start()
    capsys.readouterr()

    restore_candidates = getattr(upgrade_mod, "restore_candidates", None)
    assert restore_candidates is not None, "upgrade.restore_candidates is missing"
    cands = restore_candidates(state)
    assert [c.source for c in cands] == ["checkpoint", "upgrade"]
    assert cands[0].error_code == "upgrade_checksum"
    assert cands[0].manifest_path == state / CKPT_MANIFEST
    assert cands[0].timestamp_source == "manifest"
    assert cands[1].error_code is None
    assert cands[1].snap_root == state
    assert count() == 0  # candidates only read

    report = startup_restore_or_exit(state)

    out = capsys.readouterr()
    assert report.ok == 1
    assert report.failed == 0
    assert getattr(report, "source", None) == "upgrade"
    rejected = getattr(report, "rejected", None)
    assert rejected and rejected[0]["source"] == "checkpoint"
    assert rejected[0]["code"] == "upgrade_checksum"
    assert "@WARN: restore_fallback|checkpoint|upgrade_checksum|" in out.out
    assert "@WARN: restore_fallback|checkpoint|upgrade_checksum|" in out.err
    assert "@STAT: restore_source|upgrade|" in out.out
    assert get_entry(sid).meta.expires_at == expires
    assert "c-one" in _find(sid)
    assert "checkpoint-only" not in _find(sid)
    written = _read_json(state / RESTORE_NAME)
    assert written.get("source") == "upgrade"
    assert [r["code"] for r in written.get("rejected") or []] == ["upgrade_checksum"]
    assert snap.read_bytes() == broken


def test_no_valid_set_exits_3_with_the_newest_code(state, schema_file, capsys):
    ss = open_session(map_file=str(schema_file), ttl_minutes=30)
    _two_nodes(ss.session_id, "x")
    assert prepare_upgrade(TOKEN, directory=state).ready_to_stop is True
    reset_drain_gate()
    assert run_checkpoint(TOKEN, directory=state).saved == 1
    next((state / "upgrade-snapshots").glob("*.snap")).unlink()
    snap = next((state / "checkpoint").glob("*.snap"))
    broken = _corrupt(snap)
    _cold_start()
    capsys.readouterr()

    with pytest.raises(SystemExit) as exc:
        startup_restore_or_exit(state)

    out = capsys.readouterr()
    assert exc.value.code == 3
    assert "@ERR: upgrade_checksum|" in out.out, "the newest candidate's own code"
    assert "@ERR: upgrade_checksum|" in out.err
    assert count() == 0
    assert snap.read_bytes() == broken


def test_no_candidate_files_is_skipped(state):
    _write_json(state / BLOCKED_NAME, {"ready_to_stop": False, "saved": [], "unsaved": []})
    _cold_start()

    report = startup_restore_or_exit(state)

    assert report.skipped is True
    assert count() == 0
    assert getattr(report, "source", "missing") is None
    assert getattr(report, "rejected", None) == []


# --- real process ---------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _Serve:
    """One state dir, one port, many serve processes in turn."""

    def __init__(self, tmp_path: Path, schema_file: Path) -> None:
        self.port = _free_port()
        self.state = tmp_path / "state"
        self.state.mkdir()
        self.tmp = tmp_path
        self.schema = schema_file
        self.log = tmp_path / "serve.log"
        self.proc: subprocess.Popen[bytes] | None = None
        env = os.environ.copy()
        env.update(
            {
                "MEMNET_ADMIN_TOKEN": TOKEN,
                "MEMNET_STATE_DIR": str(self.state),
                "MEMNET_SERVE_HOST": "127.0.0.1",
                "MEMNET_SERVE_PORT": str(self.port),
            }
        )
        env.pop("MEMNET_TEST_INLINE", None)
        env.pop("MEMNET_SESSION", None)
        self.env = env

    def _log_text(self) -> str:
        return self.log.read_text(encoding="utf-8") if self.log.is_file() else ""

    def start(self, timeout_s: float = 15.0) -> None:
        handle = self.log.open("a", encoding="utf-8")
        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "memnet",
                "serve",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            env=self.env,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
        handle.close()
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if probe(host="127.0.0.1", port=self.port):
                return
            if self.proc.poll() is not None:
                break
            time.sleep(0.05)
        raise AssertionError(f"serve did not come up: {self._log_text()[-2000:]}")

    def stop(self, sig: int = signal.SIGTERM) -> None:
        proc = self.proc
        if proc is None:
            return
        self.proc = None
        if proc.poll() is None:
            proc.send_signal(sig)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and probe(host="127.0.0.1", port=self.port):
            time.sleep(0.05)
        assert not probe(host="127.0.0.1", port=self.port), "port still open after stop"

    def cmd(self, args: list[str], *, stdin: str | None = None, admin: bool = False) -> dict:
        return send_command(
            args,
            stdin=stdin,
            host="127.0.0.1",
            port=self.port,
            admin_token=TOKEN if admin else None,
            timeout=30,
        )

    def open(self, *, product: str | None = None) -> str:
        args = ["session", "open", "--map-file", str(self.schema), "--ttl", "30"]
        if product:
            args += ["--product", product]
        got = self.cmd(args)
        assert got["exit_code"] == 0, got
        return got["stdout"].split("|", 1)[0].replace("@SESSION: ", "").strip()

    def mutate(self, sid: str, text: str) -> None:
        got = self.cmd(["mutate", "--stdin", "--session", sid], stdin=text)
        assert got["exit_code"] == 0, got

    def checkpoint(self, directory: Path) -> dict:
        got = self.cmd(["admin", "checkpoint", "--state-dir", str(directory)], admin=True)
        assert got["exit_code"] == 0, got
        assert "@STAT: checkpoint|ok|" in got["stdout"], got
        return _read_json(directory / CKPT_MANIFEST)

    def prepare(self) -> None:
        got = self.cmd(["admin", "upgrade-prepare", "--state-dir", str(self.state)], admin=True)
        assert got["exit_code"] == 0, got
        assert "upgrade_prepare|ready|" in got["stderr"], got

    def session_ids(self) -> set[str]:
        got = self.cmd(["session", "list"])
        assert got["exit_code"] == 0, got
        return {
            line.split("|", 1)[0].replace("@SESSION: ", "").strip()
            for line in got["stdout"].splitlines()
            if line.startswith("@SESSION: ")
        }

    def find(self, sid: str) -> dict:
        return self.cmd(["query", "find", "--kind", "TSK", "--limit", "20", "--session", sid])

    def restore_report(self) -> dict:
        return _read_json(self.state / RESTORE_NAME)


def _shape(serve: _Serve, probe_dir: Path) -> dict[str, dict]:
    """Per session: rows, edges, node ids (from a fresh checkpoint) and the find listing."""
    probe_dir.mkdir()
    manifest = serve.checkpoint(probe_dir)
    shape: dict[str, dict] = {}
    for row in manifest["sessions"]:
        snap = probe_dir / "checkpoint" / row["file"]
        ids = set()
        for line in snap.read_text(encoding="utf-8").splitlines():
            hit = _RECORD.match(line)
            if hit and hit.group(1) not in {"SNAP", "REL"}:
                ids.add((hit.group(1), hit.group(2)))
        found = serve.find(row["session_id"])
        assert found["exit_code"] == 0, found
        shape[row["session_id"]] = {
            "rows": row["rows"],
            "edges": row["edges"],
            "ids": ids,
            "find": sorted(found["stdout"].splitlines()),
        }
    return shape


@pytest.fixture
def serve(memnet_temp, tmp_path, schema_file):
    handle = _Serve(tmp_path, schema_file)
    yield handle
    handle.stop(signal.SIGKILL)


def _seed_three(serve: _Serve) -> tuple[list[str], str]:
    sids = [serve.open(product="gateapp"), serve.open(), serve.open()]
    for idx in range(len(sids)):
        nodes = 3 + idx
        lines = [
            f"CREATE (:TSK {{id: 'TSK_{idx}_{n}', goal: 's{idx}-n{n}', status: 'open'}})"
            for n in range(nodes)
        ]
        for n in range(2 + idx):
            src, dst = n % nodes, (n + 1) % nodes
            lines.append(
                f"MATCH (a {{id: 'TSK_{idx}_{src}'}}), (b {{id: 'TSK_{idx}_{dst}'}}) "
                f"CREATE (a)-[:owns {{id: 'E_{idx}_{n}'}}]->(b)"
            )
        serve.mutate(sids[idx], "\n".join(lines) + "\n")
    guarded = sids[2]
    got = serve.cmd(["session", "acl-enable", "--session", guarded])
    assert got["exit_code"] == 0, got
    return sids, guarded


@pytest.mark.parametrize("sig", [signal.SIGKILL, signal.SIGTERM], ids=["sigkill", "sigterm"])
def test_real_restart_restores_checkpoint_and_again_on_the_next_restart(serve, tmp_path, sig):
    serve.start()
    sids, guarded = _seed_three(serve)
    saved = serve.checkpoint(serve.state)
    assert len(saved["sessions"]) == 3
    before = _shape(serve, tmp_path / "probe0")
    assert set(before) == set(sids)
    assert all(v["rows"] >= 3 and v["edges"] >= 2 for v in before.values())
    serve.stop(sig)

    for turn in (1, 2):
        serve.start()
        assert serve.session_ids() == set(sids), (
            f"restart {turn}: the checkpoint set must be restored"
        )
        report = serve.restore_report()
        assert report.get("source") == "checkpoint", report
        assert report["ok"] == 3 and report["failed"] == 0
        details = {d["session_id"]: d for d in report["details"]}
        assert details[guarded]["acl_enabled"] is True
        assert details[sids[0]]["product"] == "gateapp"
        after = _shape(serve, tmp_path / f"probe{turn}")
        assert after == before, f"restart {turn}: rows, edges or node ids changed"
        serve.stop(signal.SIGKILL)


def test_real_restart_newer_checkpoint_beats_older_prepare(serve, tmp_path):
    serve.start()
    sid = serve.open()
    serve.mutate(sid, "CREATE (:TSK {id: 'TSK_a', goal: 'early-fact', status: 'open'})\n")
    serve.prepare()
    serve.stop(signal.SIGTERM)

    serve.start()
    first = serve.restore_report()
    assert first["ok"] == 1
    assert first.get("source") == "upgrade", first
    serve.mutate(sid, "CREATE (:TSK {id: 'TSK_b', goal: 'late-fact', status: 'open'})\n")
    serve.checkpoint(serve.state)
    serve.stop(signal.SIGKILL)

    serve.start()
    found = serve.find(sid)
    assert found["exit_code"] == 0, f"session gone after restart: {found}"
    assert "late-fact" in found["stdout"]
    assert "early-fact" in found["stdout"]
    assert serve.restore_report().get("source") == "checkpoint"


def test_real_restart_newer_prepare_beats_older_checkpoint(serve, tmp_path):
    serve.start()
    sid = serve.open()
    serve.mutate(sid, "CREATE (:TSK {id: 'TSK_a', goal: 'early-fact', status: 'open'})\n")
    serve.checkpoint(serve.state)
    serve.mutate(sid, "CREATE (:TSK {id: 'TSK_b', goal: 'late-fact', status: 'open'})\n")
    serve.prepare()
    serve.stop(signal.SIGTERM)

    serve.start()
    found = serve.find(sid)
    assert found["exit_code"] == 0, found
    assert "late-fact" in found["stdout"]
    report = serve.restore_report()
    assert report.get("source") == "upgrade", report
    assert report.get("manifest") == MANIFEST_NAME
