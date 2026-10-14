"""Admin checkpoint of loaded sessions without draining (MN-REQ-06.15)."""

from __future__ import annotations

import json
import stat
import threading
from pathlib import Path

import pytest
from typer.testing import CliRunner

from memnet.checkpoint import (
    MANIFEST_NAME,
    atomic_write_bytes,
    run_checkpoint,
    verify_checkpoint,
)
from memnet.cli import app
from memnet.in_process_engine import run_argv
from memnet.registry import count, get_entry
from memnet.serve import _handle_request
from memnet.session import close_session, open_session
from memnet.snapshot import SNAPSHOT_MAGIC, materialise_snapshot_text
from memnet.upgrade import drain_gate

TOKEN = "test-admin-token"
runner = CliRunner()


def _mutate(sid: str, text: str) -> None:
    raw = run_argv(["mutate", "--stdin", "--session", sid], stdin=text)
    assert raw["exit_code"] == 0, raw["stderr"]


def _edge_poison(sid: str) -> None:
    entry = get_entry(sid)
    assert entry is not None
    for hid in entry.store.write_order:
        rec = entry.store._by_hid.get(hid)
        if rec is not None and rec.tag == "EDG":
            rec.fields["not_a_field"] = "x"
            return
    raise AssertionError("expected an edge to poison")


def _edge_endpoints_resolve(entry) -> None:
    for hid in entry.store.write_order:
        rec = entry.store._by_hid.get(hid)
        if rec is None or rec.tag != "EDG":
            continue
        assert rec.fields.get("src") in entry.store._by_hid
        assert rec.fields.get("dist") in entry.store._by_hid


def test_checkpoint_during_other_session_mutates(memnet_temp, monkeypatch, tmp_path, schema_file):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    held = open_session(map_file=str(schema_file), ttl_minutes=2)
    other = open_session(map_file=str(schema_file), ttl_minutes=2)
    _mutate(held.session_id, "CREATE (:TSK {id: 'TSK_held', goal: 'quiet', status: 'open'})\n")
    _mutate(
        other.session_id,
        "CREATE (:TSK {id: 'TSK_a', goal: 'kept', status: 'open'})\n"
        "CREATE (:TSK {id: 'TSK_b', goal: 'kept', status: 'open'})\n"
        "MATCH (a {id: 'TSK_a'}), (b {id: 'TSK_b'}) "
        "CREATE (a)-[:owns {id: 'E_keep'}]->(b)\n",
    )
    held.enable_acl()
    held.grant_caller("caller-demo", can_pin_map=True, can_mutate=False)
    held_entry = get_entry(held.session_id)
    assert held_entry is not None
    expires = held_entry.meta.expires_at
    created = held_entry.meta.created_at
    before_rows = get_entry(other.session_id).store.row_count_non_law()
    release = threading.Event()
    holding = threading.Event()

    def _hold() -> None:
        with held_entry.lock:
            holding.set()
            assert release.wait(timeout=5)

    holder = threading.Thread(target=_hold)
    holder.start()
    assert holding.wait(timeout=2)
    box: dict = {}

    def _run() -> None:
        box["result"] = run_checkpoint(TOKEN, directory=tmp_path)

    worker = threading.Thread(target=_run)
    worker.start()
    assert worker.is_alive()
    _mutate(other.session_id, "CREATE (:TSK {id: 'TSK_during', goal: 'live', status: 'open'})\n")
    other_expires = get_entry(other.session_id).meta.expires_at
    assert worker.is_alive()
    fresh = open_session(map_file=str(schema_file))
    assert fresh.session_id
    assert worker.is_alive()
    counted, refuse = drain_gate.begin(["session", "open"])
    assert refuse is None
    drain_gate.end(counted)
    assert drain_gate.phase == "open"
    release.set()
    worker.join(timeout=5)
    holder.join(timeout=2)
    assert not worker.is_alive()
    result = box["result"]
    assert result.exit_code == 0
    assert result.skipped == []
    assert result.stat == f"@STAT: checkpoint|ok|{result.saved}|skipped|0|bytes|{result.nbytes}"
    assert result.saved >= 2
    back = get_entry(held.session_id)
    assert back is not None
    assert back.meta.session_id == held.session_id
    assert back.meta.expires_at == expires
    assert back.meta.created_at == created
    assert back.acl is not None and back.acl.enabled is True
    assert back.acl.callers["caller-demo"].can_mutate is False
    assert get_entry(other.session_id).meta.expires_at == other_expires
    manifest = json.loads((tmp_path / "checkpoint" / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["manifest_format"] == 1
    assert manifest["snapshot_format"] == 2
    assert stat.S_IMODE((tmp_path / "checkpoint" / MANIFEST_NAME).stat().st_mode) == 0o600
    for row in manifest["sessions"]:
        assert stat.S_IMODE((tmp_path / "checkpoint" / row["file"]).stat().st_mode) == 0o600
    assert manifest["serve_version"]
    assert manifest["timestamp"].endswith("Z")
    assert manifest["unsaved"] == []
    other_row = next(row for row in manifest["sessions"] if row["session_id"] == other.session_id)
    snap = materialise_snapshot_text(
        (tmp_path / "checkpoint" / other_row["file"]).read_text(encoding="utf-8")
    )
    assert snap.store.row_count_non_law() == other_row["rows"]
    assert other_row["rows"] >= before_rows
    _edge_endpoints_resolve(snap)
    held_row = next(row for row in manifest["sessions"] if row["session_id"] == held.session_id)
    held_snap = materialise_snapshot_text(
        (tmp_path / "checkpoint" / held_row["file"]).read_text(encoding="utf-8")
    )
    assert held_snap.store.row_count_non_law() == held_entry.store.row_count_non_law()
    assert count() >= 3


def test_unsaveable_session_is_skipped(memnet_temp, monkeypatch, tmp_path, schema_file):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    good = open_session(map_file=str(schema_file))
    bad = open_session(map_file=str(schema_file))
    _mutate(good.session_id, "CREATE (:TSK {id: 'TSK_good', goal: 'kept', status: 'open'})\n")
    _mutate(
        bad.session_id,
        "CREATE (:TSK {id: 'TSK_a', goal: 'a', status: 'open'})\n"
        "CREATE (:TSK {id: 'TSK_b', goal: 'b', status: 'open'})\n"
        "MATCH (a {id: 'TSK_a'}), (b {id: 'TSK_b'}) "
        "CREATE (a)-[:owns {id: 'E_bad'}]->(b)\n",
    )
    first = run_checkpoint(TOKEN, directory=tmp_path)
    assert first.exit_code == 0
    assert first.saved == 2
    manifest_text = (tmp_path / "checkpoint" / MANIFEST_NAME).read_text(encoding="utf-8")
    first_manifest = json.loads(manifest_text)
    bad_name = next(
        row["file"] for row in first_manifest["sessions"] if row["session_id"] == bad.session_id
    )
    assert (tmp_path / "checkpoint" / bad_name).is_file()
    expires = get_entry(bad.session_id).meta.expires_at
    _edge_poison(bad.session_id)
    result = run_checkpoint(TOKEN, directory=tmp_path)
    assert result.exit_code == 2
    assert result.saved == 1
    assert len(result.skipped) == 1
    assert result.skipped[0]["code"] == "snapshot_unsaveable"
    assert result.skipped[0]["session_id"] == bad.session_id
    assert result.skipped[0]["detail"]
    assert result.stat.startswith("@STAT: checkpoint|ok|1|skipped|1|bytes|")
    assert not (tmp_path / "checkpoint" / bad_name).exists()
    manifest = json.loads((tmp_path / "checkpoint" / MANIFEST_NAME).read_text(encoding="utf-8"))
    saved_ids = {row["session_id"] for row in manifest["sessions"]}
    assert good.session_id in saved_ids
    assert bad.session_id not in saved_ids
    assert manifest["unsaved"][0]["code"] == "snapshot_unsaveable"
    assert get_entry(bad.session_id) is not None
    assert get_entry(bad.session_id).meta.expires_at == expires
    assert get_entry(good.session_id).meta.expires_at


def test_atomic_write_never_leaves_a_partial_file(tmp_path, monkeypatch):
    dest = tmp_path / "session.snap"
    original = (SNAPSHOT_MAGIC + "\nCOMPLETE-OLD\n").encode("utf-8")
    dest.write_bytes(original)

    def _boom(_fd: int) -> None:
        raise OSError("fsync failed")

    monkeypatch.setattr("memnet.atomic_file._fsync_fd", _boom)
    with pytest.raises(OSError):
        atomic_write_bytes(dest, b"PARTIAL-NEW-BYTES")
    assert dest.read_bytes() == original
    assert b"PARTIAL" not in dest.read_bytes()
    assert list(tmp_path.glob("*.tmp")) == []


def test_stale_checkpoint_removed_after_close(memnet_temp, monkeypatch, tmp_path, schema_file):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    keep = open_session(map_file=str(schema_file))
    gone = open_session(map_file=str(schema_file))
    _mutate(keep.session_id, "CREATE (:TSK {id: 'TSK_keep', goal: 'stay', status: 'open'})\n")
    _mutate(gone.session_id, "CREATE (:TSK {id: 'TSK_gone', goal: 'drop', status: 'open'})\n")
    first = run_checkpoint(TOKEN, directory=tmp_path)
    assert first.saved == 2
    dest = tmp_path / "checkpoint"
    manifest = json.loads((dest / MANIFEST_NAME).read_text(encoding="utf-8"))
    gone_name = next(
        row["file"] for row in manifest["sessions"] if row["session_id"] == gone.session_id
    )
    assert (dest / gone_name).is_file()
    close_session(gone.session_id)
    second = run_checkpoint(TOKEN, directory=tmp_path)
    assert second.exit_code == 0
    assert second.saved == 1
    assert not (dest / gone_name).exists()
    again = json.loads((dest / MANIFEST_NAME).read_text(encoding="utf-8"))
    ids = {row["session_id"] for row in again["sessions"]}
    assert ids == {keep.session_id}
    assert list(dest.glob("*.snap")) == [dest / again["sessions"][0]["file"]]


def test_checkpoint_verify_good_corrupt_and_missing(
    memnet_temp, monkeypatch, tmp_path, schema_file
):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    ss = open_session(map_file=str(schema_file))
    _mutate(ss.session_id, "CREATE (:TSK {id: 'TSK_v', goal: 'verify', status: 'open'})\n")
    result = run_checkpoint(TOKEN, directory=tmp_path)
    assert result.exit_code == 0
    dest = tmp_path / "checkpoint"
    live = count()
    good = verify_checkpoint(dest, TOKEN)
    assert good.exit_code == 0
    assert good.ok == 1
    assert good.failed == []
    assert good.stat == "@STAT: checkpoint_verify|ok|1|failed|0"
    assert count() == live
    snap = next(dest.glob("*.snap"))
    original = snap.read_bytes()
    snap.write_bytes(original[:40] + b"XXXX" + original[44:])
    corrupt = verify_checkpoint(dest, TOKEN)
    assert corrupt.exit_code != 0
    assert corrupt.ok == 0
    assert corrupt.failed
    assert corrupt.failed[0]["code"] == "checkpoint_checksum"
    assert corrupt.stat == "@STAT: checkpoint_verify|ok|0|failed|1"
    assert snap.read_bytes() != original
    assert count() == live
    snap.write_bytes(original)
    snap.unlink()
    missing = verify_checkpoint(dest, TOKEN)
    assert missing.exit_code != 0
    assert any(row["code"] == "checkpoint_missing" for row in missing.failed)
    assert missing.stat.startswith("@STAT: checkpoint_verify|ok|0|failed|")
    assert count() == live


def test_admin_token_required(memnet_temp, monkeypatch, tmp_path, schema_file):
    ss = open_session(map_file=str(schema_file))
    _mutate(ss.session_id, "CREATE (:TSK {id: 'TSK_tok', goal: 'gate', status: 'open'})\n")
    monkeypatch.delenv("MEMNET_ADMIN_TOKEN", raising=False)
    denied = _handle_request({"checkpoint": True, "admin_token": "anything"})
    assert denied["exit_code"] == 2
    assert "admin_unconfigured" in denied["stderr"]
    assert denied["stdout"] == ""
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    monkeypatch.setenv("MEMNET_STATE_DIR", str(tmp_path / "wire"))
    wrong = _handle_request({"checkpoint": True, "admin_token": "wrong"})
    assert wrong["exit_code"] == 2
    assert "admin_denied" in wrong["stderr"]
    missing = _handle_request({"checkpoint": True})
    assert missing["exit_code"] == 2
    assert "admin_denied" in missing["stderr"]
    cli_missing = runner.invoke(app, ["admin", "checkpoint", "--state-dir", str(tmp_path)])
    assert cli_missing.exit_code == 2
    assert "admin_denied" in cli_missing.stderr
    verify_missing = runner.invoke(app, ["admin", "checkpoint-verify", str(tmp_path)])
    assert verify_missing.exit_code == 2
    assert "admin_denied" in verify_missing.stderr
    ok = _handle_request({"checkpoint": True, "admin_token": TOKEN})
    assert ok["exit_code"] == 0, ok
    assert ok["stdout"].startswith("@STAT: checkpoint|ok|")
    assert "skipped|0|" in ok["stdout"]
    cli = runner.invoke(
        app,
        ["admin", "checkpoint", "--token", TOKEN, "--state-dir", str(tmp_path / "cli")],
    )
    assert cli.exit_code == 0, cli.stderr
    assert cli.stdout.startswith("@STAT: checkpoint|ok|")
    checked = runner.invoke(
        app,
        [
            "admin",
            "checkpoint-verify",
            "--token",
            TOKEN,
            str(tmp_path / "cli" / "checkpoint"),
        ],
    )
    assert checked.exit_code == 0, checked.stderr
    assert checked.stdout.startswith("@STAT: checkpoint_verify|ok|")


def test_backup_doc_has_no_session_id_or_secret():
    text = (Path(__file__).resolve().parents[1] / "docs/operations/backup.md").read_text(
        encoding="utf-8"
    )
    assert "mn_" not in text
    assert "memnet admin checkpoint" in text
    assert "checkpoint-verify" in text
    assert "MEMNET_ADMIN_TOKEN" in text
    assert "restic" in text
    assert "R2" in text
    assert "test-admin-token" not in text
