"""Optional session save/load snapshots."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from memnet.cli import app
from memnet.registry import contains
from memnet.snapshot import load_snapshot, snapshot_text, write_snapshot
from memnet.session import get_session, open_session

runner = CliRunner()


def test_snapshot_roundtrip(memnet_temp, schema_file, workflow_file, tmp_path: Path):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])

    snap_path = tmp_path / "game.snap"
    ss = get_session(sid)
    rows = write_snapshot(ss, snap_path)
    assert rows > 0
    assert "@SNAP:" in snap_path.read_text(encoding="utf-8")
    assert "@PLR:" in snap_path.read_text(encoding="utf-8")

    loaded = load_snapshot(snap_path)
    assert loaded.session_id != sid
    assert loaded.store.get("PLR01") is not None
    assert loaded.store.row_count_non_law() == rows


def test_cli_session_save_load(memnet_temp, schema_file, workflow_file, tmp_path: Path):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])

    snap_path = tmp_path / "roundtrip.snap"
    save = runner.invoke(app, ["session", "save", "--file", str(snap_path), "--session", sid])
    assert save.exit_code == 0
    assert "@STAT: saved|" in save.stdout

    runner.invoke(app, ["session", "close", sid])
    assert not contains(sid)

    load = runner.invoke(app, ["session", "load", "--file", str(snap_path)])
    assert load.exit_code == 0
    new_sid = load.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    assert new_sid.startswith("mn_")
    warm = runner.invoke(app, ["query", "warm", "--anchor", "PLR01", "--session", new_sid])
    assert warm.exit_code == 0
    assert "@PLR:" in warm.stdout


def test_snapshot_text_matches_file(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    text = snapshot_text(ss)
    assert text.startswith("# memnet-snapshot-v1\n")


def test_snapshot_preserves_modified_at(memnet_temp, schema_file, workflow_file, tmp_path: Path):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])
    ss = get_session(sid)
    assert ss.meta.modified_at is not None

    snap_path = tmp_path / "mod.snap"
    write_snapshot(ss, snap_path)
    assert f"|{ss.meta.modified_at}" in snap_path.read_text(encoding="utf-8")

    loaded = load_snapshot(snap_path)
    assert loaded.meta.modified_at == ss.meta.modified_at
