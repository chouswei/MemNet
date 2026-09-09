"""Optional session save/load snapshots."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from memnet.cli import app
from memnet.registry import contains
from memnet.session import get_session, open_session
from memnet.snapshot import load_snapshot, snapshot_text, write_snapshot

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
    assert "identity:" in warm.stdout
    assert "@PLR:" not in warm.stdout
    assert "(:PLR" in warm.stdout
    assert "id: 'PLR01'" not in warm.stdout


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


_MISSION_MAP = [
    "SCHEMA PRT ; fields=id name qname path sysml_kind recycle",
    "SCHEMA MOD ; fields=id path summary status recycle",
    "SCHEMA SYM ; fields=id name kind path line signature status recycle",
    "SCHEMA TSK ; fields=id goal anchor status recycle",
]


def _mission_graph(ss) -> None:
    from memnet.mutate_gate import MutateGate

    MutateGate(ss).apply(
        [
            "CREATE (:TSK {goal: 'TSK_model_vfdl2', status: 'open'})",
            "CREATE (:PRT {name: 'Valve', qname: 'Pkg::Valve', path: 'models/deploy-vfdl2.sysml'})",
            "CREATE (:SYM {name: 'edgePc', kind: 'port', path: 'models/deploy-vfdl2.sysml'})",
            "CREATE (:MOD {path: 'models/deploy-vfdl2.sysml', "
            "summary: 'interior', status: 'active'})",
            "MATCH (a:SYM {name: 'edgePc'}), (b:MOD {path: 'models/deploy-vfdl2.sysml'})",
            "CREATE (a)-[:inFile]->(b)",
            "MATCH (a:PRT {name: 'Valve'}), (b:SYM {name: 'edgePc'})",
            "CREATE (a)-[:declaredIn]->(b)",
        ],
        mode="add",
        allow_new_relation=True,
    )


def test_mission_empty_nick_infile_save_load(memnet_temp, tmp_path: Path):
    """CREATE without nickname + camelCase :inFile round-trips session_save/load."""
    del memnet_temp
    ss = open_session(map_lines=_MISSION_MAP)
    _mission_graph(ss)
    text = snapshot_text(ss)
    rec_lines = [
        ln for ln in text.splitlines() if ln.startswith("@") and not ln.startswith("@SNAP:")
    ]
    rec_lines = [
        ln for ln in rec_lines if ln.startswith(("@TSK:", "@PRT:", "@SYM:", "@MOD:", "@EDG:"))
    ]
    assert rec_lines
    for line in rec_lines:
        nick = line.split(":", 1)[1].strip().split("|", 1)[0]
        assert nick, line
        from memnet.tag_map import validate_id

        validate_id(nick)
        assert not nick.startswith("TSK_model_"), line
    assert "inFile" in text
    assert "declaredIn" in text
    assert "@REL: inFile" in text

    snap_path = tmp_path / "mission.snap"
    write_snapshot(ss, snap_path)
    loaded = load_snapshot(snap_path)
    tsks = [
        r for r in loaded.store.list_records("TSK") if r.fields.get("goal") == "TSK_model_vfdl2"
    ]
    assert len(tsks) == 1
    assert tsks[0].id
    rels = {r.fields.get("relation") for r in loaded.store.list_records("EDG")}
    assert "inFile" in rels
    assert "declaredIn" in rels
    from memnet.pin_map_composer import PinMapComposer

    look = PinMapComposer(loaded).compose(
        anchor=None, kind="SYM", locators=[("name", "edgePc")], depth=1
    )[1]
    assert "edgePc" in look
    assert ":inFile" in look or "inFile" in look
    assert tsks[0].hid not in look
    assert "id: '" not in look

    save = runner.invoke(
        app,
        ["session", "save", "--file", str(snap_path), "--session", ss.session_id],
    )
    assert save.exit_code == 0, save.stderr
    load = runner.invoke(app, ["session", "load", "--file", str(snap_path)])
    assert load.exit_code == 0, load.stderr
    assert "@ERR:" not in load.stdout
    assert "invalid_id" not in load.stderr
    assert "invalid_relation" not in load.stderr


def test_parse_line_mints_empty_id_and_accepts_infile(memnet_temp):
    del memnet_temp
    from memnet.tag_map import leftover_wire_nick, parse_line, validate_id

    ss = open_session(map_lines=_MISSION_MAP)
    used: set[str] = set()
    tsk = parse_line(
        "@TSK: |TSK_model_vfdl2||open|persistent",
        ss.tag_map,
        used_nicks=used,
    )
    assert tsk.id
    validate_id(tsk.id)
    assert tsk.id.startswith("sn_")
    assert tsk.fields["goal"] == "TSK_model_vfdl2"
    mod = parse_line(
        "@MOD: |models/deploy-vfdl2.sysml|interior|active|persistent",
        ss.tag_map,
        used_nicks=used,
    )
    edg = parse_line(
        f"@EDG: |{tsk.id}|inFile|{mod.id}|||persistent",
        ss.tag_map,
        used_nicks=used,
    )
    assert edg.fields["relation"] == "inFile"
    a = leftover_wire_nick("_el9", kind="TSK", used=set())
    b = leftover_wire_nick("_el9", kind="TSK", used=set())
    assert a == b
    validate_id(a)
