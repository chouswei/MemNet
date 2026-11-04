"""Upgrade a running 0.20.4 serve with live sessions to this build, check, and roll back.

Real processes only: the old serve runs from a 0.20.4 build out of git history
(tests/old_build_lib.py), the new one from this checkout, on one port and one state dir.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from old_build_lib import REPO, Serve, new_build, read_json, seed

ROLLBACK = REPO / "scripts" / "upgrade-rollback.sh"


@pytest.fixture
def serve(memnet_temp, tmp_path, schema_file):
    handle = Serve(tmp_path, schema_file)
    yield handle
    handle.kill_any()


def _shape(serve: Serve, sids: list[str]) -> dict[str, list[str]]:
    return {sid: serve.find(sid) for sid in sids}


def _verify(serve: Serve, client, before: Path) -> subprocess.CompletedProcess[str]:
    return serve.client(client, ["admin", "upgrade-verify", "--before", str(before)])


def _wait_down_cmd(port: int) -> str:
    probe = (
        "import socket, time\n"
        "for _ in range(200):\n"
        "    try:\n"
        f"        socket.create_connection(('127.0.0.1', {port}), 0.2).close()\n"
        "    except OSError:\n"
        "        break\n"
        "    time.sleep(0.05)\n"
    )
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(probe)}"


def test_old_serve_upgrades_to_new_and_rolls_back(serve, old_build, tmp_path):
    new = new_build(tmp_path)
    live = tmp_path / "venv"
    live.symlink_to(old_build.venv)

    # 0.20.4 serve with live sessions.
    serve.start(old_build)
    sids = seed(serve)
    before = _shape(serve, sids)
    manifest = serve.prepare()
    assert {row["session_id"] for row in manifest["sessions"]} == set(sids)
    assert all(row["rows"] > 0 and row["edges"] > 0 for row in manifest["sessions"])
    serve.stop()
    saved = tmp_path / "state.pre-upgrade"
    shutil.copytree(serve.state, saved, symlinks=True)

    # Switch the live link to the new build and start it on the same state dir.
    live.unlink()
    live.symlink_to(new.venv)
    serve.start(new)
    report = read_json(serve.state / "upgrade-restore.json")
    assert report["source"] == "upgrade" and report["ok"] == 3 and report["failed"] == 0
    assert serve.session_ids() == set(sids)
    assert _shape(serve, sids) == before

    # The health and data check passes on the restored serve ...
    got = _verify(serve, new, saved / "upgrade-manifest.json")
    assert got.returncode == 0, got.stderr
    assert "@STAT: upgrade_verify|ok|3" in got.stderr

    # ... and fails once a session differs from the saved set.
    serve.mutate(sids[0], "CREATE (:TSK {id: 'TSK_late', goal: 'after-upgrade', status: 'open'})\n")
    got = _verify(serve, new, saved / "upgrade-manifest.json")
    assert got.returncode == 3, got.stderr
    assert f"upgrade_verify_mismatch|rows|{sids[0]}|" in got.stderr

    # One-step rollback: old venv back on the live link, saved sessions back, old serve up.
    serve_cmd = " ".join(shlex.quote(part) for part in serve.serve_argv(live / "bin" / "python"))
    pidfile = shlex.quote(str(serve.pidfile))
    start = f"{serve_cmd} >> {shlex.quote(str(serve.log))} 2>&1 & echo $! > {pidfile}"
    stop = f"kill -TERM $(cat {pidfile}) && {_wait_down_cmd(serve.port)}"
    new_proc, serve.proc = serve.proc, None  # the script's stop command ends it
    rolled = subprocess.run(
        [
            "bash",
            str(ROLLBACK),
            "--live-venv",
            str(live),
            "--old-venv",
            str(old_build.venv),
            "--state-dir",
            str(serve.state),
            "--saved",
            str(saved),
            "--stop",
            stop,
            "--start",
            start,
            "--wait-s",
            "30",
        ],
        env=serve.env,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert new_proc is not None and new_proc.wait(timeout=10) is not None
    assert rolled.returncode == 0, rolled.stdout + rolled.stderr + serve.log_text()[-2000:]
    assert "@STAT: upgrade_rollback|ok|3" in rolled.stdout
    assert os.readlink(live) == str(old_build.venv)
    serve.wait_up()
    assert serve.session_ids() == set(sids)
    assert _shape(serve, sids) == before, "rollback must bring back the pre-upgrade rows"
    # The new build's writes are set aside, not deleted.
    assert list(tmp_path.glob("state.rolled-back-*"))
