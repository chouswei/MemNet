"""0.19 pin-map export: cue pin_map (or empty-q outline) written out."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import OUTLINE_EXEMPLAR_LIMIT, examples_dir
from memnet.exceptions import MemNetError
from memnet.import_absorb import export_working_memory_slice
from memnet.pin_map_composer import PinMapComposer
from memnet.pin_map_export import export_pin_map
from memnet.session import get_session, open_session
from memnet.snapshot import SNAPSHOT_MAGIC, snapshot_text

runner = CliRunner()
_CODING_MAP = examples_dir() / "schema.coding.example.txt"


def _open() -> str:
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def _seed_two_kinds(sid: str) -> None:
    add = runner.invoke(
        app,
        ["add", "--stdin", "--session", sid],
        input=(
            "CREATE (:TSK {id: 'TSK_live', goal: 'export-cut', status: 'open'})\n"
            "CREATE (:MOD {id: 'MOD_x', path: 'src/x.py', summary: 'mod', status: 'active'})\n"
            "MATCH (t {id: 'TSK_live'}), (m {id: 'MOD_x'})\n"
            "CREATE (t)-[:owns {id: 'E_link'}]->(m)\n"
        ),
    )
    assert add.exit_code == 0, add.stderr


def test_export_cue_is_shaped_pin_map_not_dump(memnet_temp):
    sid = _open()
    _seed_two_kinds(sid)
    r = runner.invoke(app, ["export", "pin-map", "--kind", "TSK", "--session", sid])
    assert r.exit_code == 0, r.stderr
    out = r.stdout
    assert out.startswith("@EXPORT: pin-map|cue=kind:TSK")
    assert "(:TSK" in out
    assert "TSK_live" in out
    assert "CREATE" not in out
    assert "MERGE" not in out
    assert "_el" not in out
    assert "_memnet_hid" not in out
    mapped = runner.invoke(app, ["query", "pin-map", "--kind", "TSK", "--session", sid])
    assert mapped.exit_code == 0, mapped.stderr
    export_body = "\n".join(ln for ln in out.splitlines() if not ln.startswith("@EXPORT:"))
    assert mapped.stdout.strip() == export_body.strip()


def test_export_empty_cue_is_outline_not_dump_s(memnet_temp):
    sid = _open()
    lines = [
        f"CREATE (:TSK {{id: 'TSK_{i}', goal: 'g{i}', status: 'in_progress'}})" for i in range(8)
    ]
    lines.append("CREATE (:MOD {id: 'MOD_only', path: 'a.py', status: 'active'})")
    lines.append(
        "MATCH (t {id: 'TSK_0'}), (m {id: 'MOD_only'})\nCREATE (t)-[:owns {id: 'E_own'}]->(m)"
    )
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input="\n".join(lines) + "\n")
    assert add.exit_code == 0, add.stderr
    r = runner.invoke(app, ["export", "pin-map", "--session", sid])
    assert r.exit_code == 0, r.stderr
    assert "@EXPORT: pin-map|cue=outline" in r.stdout
    assert "## outline" in r.stdout
    shown = [ln for ln in r.stdout.splitlines() if ln.startswith("(:TSK")]
    assert len(shown) == OUTLINE_EXEMPLAR_LIMIT
    assert "-[:" not in r.stdout
    assert "owns" not in r.stdout
    assert "memnet-snapshot-v1" not in r.stdout
    assert "_el" not in r.stdout
    assert "_memnet_hid" not in r.stdout


def test_export_cue_conflict_when_q_gt_one(memnet_temp):
    sid = _open()
    line = "CREATE (:TSK {goal: 'same-goal', status: 'open'})\n"
    a = runner.invoke(app, ["add", "--stdin", "--session", sid], input=line)
    b = runner.invoke(app, ["add", "--stdin", "--session", sid], input=line)
    assert a.exit_code == 0, a.stderr
    assert b.exit_code == 0, b.stderr
    r = runner.invoke(app, ["export", "pin-map", "--kind", "TSK", "--session", sid])
    assert r.exit_code == 0, r.stderr
    assert "CueConflict" in r.stdout
    assert "conflict=1" in r.stdout
    assert "_el" not in r.stdout
    assert "_memnet_hid" not in r.stdout


def test_export_out_file_is_not_snapshot_or_absorb(memnet_temp, tmp_path: Path):
    sid = _open()
    _seed_two_kinds(sid)
    dest = tmp_path / "slice.gql"
    r = runner.invoke(
        app,
        ["export", "pin-map", "--kind", "TSK", "--out", str(dest), "--session", sid],
    )
    assert r.exit_code == 0, r.stderr
    assert dest.is_file()
    text = dest.read_text(encoding="utf-8")
    assert SNAPSHOT_MAGIC not in text
    assert "@SNAP:" not in text
    assert "@EXPORT:" not in text
    assert "(:TSK" in text
    assert "_el" not in text
    assert "_memnet_hid" not in text
    ss = get_session(sid)
    snap = snapshot_text(ss)
    assert SNAPSHOT_MAGIC in snap
    assert text != snap
    # WorkingMemorySlice export is Absorb payload (anchors required) — not this command.
    try:
        export_working_memory_slice(ss, anchors=[])
        raise AssertionError("Absorb slice must still require anchors")
    except MemNetError as exc:
        assert exc.code == "no_anchor"


def test_export_engine_matches_composer_and_hides_hid(memnet_temp):
    ss = open_session(map_file=str(_CODING_MAP))
    from memnet.mutate_gate import MutateGate

    MutateGate(ss).apply(
        ["CREATE (:TSK {goal: 'solo', status: 'in_progress'})"],
        mode="add",
    )
    rows, mapped = PinMapComposer(ss).compose(anchor=None, kind="TSK")
    result = export_pin_map(ss, kind="TSK")
    assert result.cue == "kind:TSK"
    assert result.body == mapped
    assert result.row_count == len(rows)
    assert "_el" not in result.body
    assert "_memnet_hid" not in result.body
    assert "hid" not in result.header
