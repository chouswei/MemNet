"""``memnet admin upgrade-verify``: the health and data check after an upgrade (MN-REQ-06.14).

The check runs in the client. It asks the running serve for a checkpoint into a scratch
dir and compares it with a saved manifest: the same session ids, and per session the
same rows and relations. Any mismatch exits 3; no serve or an unreadable file exits 2.
"""

from __future__ import annotations

import json
import shutil
import signal
from pathlib import Path

import pytest

from old_build_lib import Serve, new_build, read_json, seed


@pytest.fixture
def serve(memnet_temp, tmp_path, schema_file):
    handle = Serve(tmp_path, schema_file)
    yield handle
    handle.kill_any()


@pytest.fixture
def started(serve, tmp_path):
    build = new_build(tmp_path)
    serve.start(build)
    sids = seed(serve, sessions=2)
    got = serve.cmd(["admin", "checkpoint", "--state-dir", str(tmp_path / "before")], admin=True)
    assert got["exit_code"] == 0, got
    return serve, build, sids, tmp_path / "before" / "checkpoint" / "checkpoint-manifest.json"


def _verify(serve: Serve, build, before: Path, *extra: str):
    return serve.client(build, ["admin", "upgrade-verify", "--before", str(before), *extra])


def test_compare_counts_names_each_mismatch():
    from memnet.upgrade import compare_counts

    before = [
        {"session_id": "a", "rows": 3, "edges": 1},
        {"session_id": "b", "rows": 2, "edges": 0},
        {"session_id": "c", "rows": 1, "edges": 0},
    ]
    after = [
        {"session_id": "a", "rows": 3, "edges": 2},
        {"session_id": "b", "rows": 5, "edges": 0},
        {"session_id": "d", "rows": 1, "edges": 0},
    ]
    got = {(m["kind"], m["session_id"]) for m in compare_counts(before, after)}
    assert got == {("edges", "a"), ("rows", "b"), ("missing", "c"), ("extra", "d")}
    assert compare_counts(before, before) == []


def test_pass_on_an_unchanged_serve(started):
    serve, build, sids, before = started
    got = _verify(serve, build, before)
    assert got.returncode == 0, got.stderr
    assert "@STAT: upgrade_verify|ok|2" in got.stderr
    report = json.loads(got.stdout)
    assert report["ok"] is True and report["mismatches"] == []
    assert report["sessions"] == {"before": 2, "after": 2}


def test_scratch_checkpoint_is_not_left_behind(started, tmp_path):
    serve, build, _sids, before = started
    scratch = tmp_path / "scratch"
    got = _verify(serve, build, before, "--scratch", str(scratch))
    assert got.returncode == 0, got.stderr
    assert not scratch.exists()
    assert not (serve.state / "checkpoint").exists(), "the live checkpoint set is untouched"


def test_fail_on_rows_relations_and_session_count(started, tmp_path):
    serve, build, sids, before = started
    serve.mutate(sids[0], "CREATE (:TSK {id: 'TSK_x', goal: 'extra', status: 'open'})\n")
    got = _verify(serve, build, before)
    assert got.returncode == 3, got.stderr
    assert f"@WARN: upgrade_verify_mismatch|rows|{sids[0]}|" in got.stderr
    assert "@ERR: upgrade_verify_mismatch|1" in got.stderr

    tampered = tmp_path / "tampered.json"
    data = read_json(before)
    data["sessions"][1]["edges"] += 1
    tampered.write_text(json.dumps(data), encoding="utf-8")
    got = _verify(serve, build, tampered)
    assert got.returncode == 3
    assert f"upgrade_verify_mismatch|edges|{sids[1]}|" in got.stderr

    closed = serve.cmd(["session", "close", sids[1]])
    assert closed["exit_code"] == 0, closed
    got = _verify(serve, build, before)
    assert got.returncode == 3
    assert f"upgrade_verify_mismatch|missing|{sids[1]}|" in got.stderr
    assert json.loads(got.stdout)["sessions"] == {"before": 2, "after": 1}


def test_fail_on_bad_before_file_or_no_serve(started, tmp_path):
    serve, build, _sids, before = started
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    got = _verify(serve, build, bad)
    assert got.returncode == 2 and "@ERR: upgrade_verify_before|" in got.stderr
    got = _verify(serve, build, tmp_path / "absent.json")
    assert got.returncode == 2 and "@ERR: upgrade_verify_before|" in got.stderr

    kept = tmp_path / "kept.json"
    shutil.copy(before, kept)
    serve.stop(signal.SIGTERM)
    got = _verify(serve, build, kept)
    assert got.returncode == 2, got.stderr
    assert "@ERR: serve_unreachable|" in got.stderr


def test_wrong_token_is_refused(started):
    serve, build, _sids, before = started
    serve.env["MEMNET_ADMIN_TOKEN"] = "test-wrong-token"
    got = _verify(serve, build, before)
    assert got.returncode == 2
    assert "@ERR: admin_denied|" in got.stderr
