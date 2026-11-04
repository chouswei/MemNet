"""scripts/upgrade-rollback.sh against temp dirs: no systemd, no serve (fake stop/start).

The real-serve rollback (0.20.4 back on the live link) is in test_upgrade_cross_version.py.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from old_build_lib import REPO

SCRIPT = REPO / "scripts" / "upgrade-rollback.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash not installed")


def _venv(path: Path) -> Path:
    (path / "bin").mkdir(parents=True)
    py = path / "bin" / "python"
    py.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n', encoding="utf-8")
    py.chmod(0o755)
    return path


def _manifest(sessions: int) -> dict:
    return {
        "manifest_format": 1,
        "snapshot_format": 2,
        "ready_to_stop": True,
        "retired": False,
        "sessions": [
            {"session_id": f"s{i}", "file": f"upgrade-snapshots/s{i}.snap", "rows": 1, "edges": 0}
            for i in range(sessions)
        ],
        "unsaved": [],
    }


@pytest.fixture
def host(tmp_path):
    old = _venv(tmp_path / "venv-old")
    new = _venv(tmp_path / "venv-new")
    live = tmp_path / "venv"
    live.symlink_to(new)
    saved = tmp_path / "state.pre-upgrade"
    (saved / "upgrade-snapshots").mkdir(parents=True)
    for i in range(2):
        (saved / "upgrade-snapshots" / f"s{i}.snap").write_text(f"old-{i}\n", encoding="utf-8")
    (saved / "upgrade-manifest.json").write_text(json.dumps(_manifest(2)), encoding="utf-8")
    state = tmp_path / "state"
    shutil.copytree(saved, state)
    manifest = json.loads((state / "upgrade-manifest.json").read_text())
    manifest.update({"retired": True, "retired_at": "2026-11-04T00:00:00Z"})
    (state / "upgrade-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (state / "upgrade-restore.json").write_text('{"ok": 2, "failed": 0}', encoding="utf-8")
    (state / "checkpoint").mkdir()
    (state / "checkpoint" / "new-write.snap").write_text("new\n", encoding="utf-8")
    return {"tmp": tmp_path, "old": old, "new": new, "live": live, "saved": saved, "state": state}


def _run(host: dict, *, start: str, stop: str = "true", saved: Path | None = None):
    log = host["tmp"] / "calls.log"
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--live-venv",
            str(host["live"]),
            "--old-venv",
            str(host["old"]),
            "--state-dir",
            str(host["state"]),
            "--saved",
            str(saved or host["saved"]),
            "--stop",
            f"echo stop >> {shlex.quote(str(log))}; {stop}",
            "--start",
            f"echo start >> {shlex.quote(str(log))}; {start}",
            "--wait-s",
            "5",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _fake_restore(host: dict, ok: int, failed: int) -> str:
    report = json.dumps({"ok": ok, "failed": failed})
    return (
        f"echo {shlex.quote(report)} > {shlex.quote(str(host['state'] / 'upgrade-restore.json'))}"
    )


def test_rollback_swaps_venv_and_restores_saved_sessions(host):
    got = _run(host, start=_fake_restore(host, 2, 0))
    assert got.returncode == 0, got.stdout + got.stderr
    assert "@STAT: upgrade_rollback|ok|2" in got.stdout
    assert (host["tmp"] / "calls.log").read_text().split() == ["stop", "start"]
    assert os.readlink(host["live"]) == str(host["old"])
    state = host["state"]
    manifest = json.loads((state / "upgrade-manifest.json").read_text())
    assert manifest["retired"] is False and "retired_at" not in manifest
    assert (state / "upgrade-snapshots" / "s1.snap").read_text() == "old-1\n"
    assert not (state / "checkpoint").exists()
    moved = list(host["tmp"].glob("state.rolled-back-*"))
    assert len(moved) == 1 and (moved[0] / "checkpoint" / "new-write.snap").is_file()
    # The saved copy is left as it was, so the rollback can be run again.
    assert json.loads((host["saved"] / "upgrade-manifest.json").read_text())["retired"] is False


def test_rollback_fails_when_the_old_serve_does_not_restore_every_session(host):
    got = _run(host, start=_fake_restore(host, 1, 1))
    assert got.returncode == 3, got.stdout + got.stderr
    assert "@ERR: upgrade_rollback|restore|" in got.stderr


def test_rollback_fails_when_the_old_serve_writes_no_restore_report(host):
    got = _run(host, start="true")
    assert got.returncode == 3
    assert "@ERR: upgrade_rollback|timeout|" in got.stderr


def test_rollback_refuses_a_bad_saved_copy_and_changes_nothing(host):
    empty = host["tmp"] / "empty"
    empty.mkdir()
    got = _run(host, start="true", saved=empty)
    assert got.returncode == 2
    assert "@ERR: upgrade_rollback|saved|" in got.stderr
    assert not (host["tmp"] / "calls.log").exists(), "nothing stopped"
    assert os.readlink(host["live"]) == str(host["new"])
    assert (host["state"] / "checkpoint" / "new-write.snap").is_file()


def test_rollback_refuses_when_the_live_venv_is_not_a_link(host):
    host["live"].unlink()
    host["live"].mkdir()
    got = _run(host, start="true")
    assert got.returncode == 2
    assert "@ERR: upgrade_rollback|live_venv|" in got.stderr


def test_failed_stop_leaves_state_and_link(host):
    got = _run(host, start="true", stop="false")
    assert got.returncode == 2
    assert "@ERR: upgrade_rollback|stop|" in got.stderr
    assert os.readlink(host["live"]) == str(host["new"])
    assert (host["state"] / "checkpoint" / "new-write.snap").is_file()
