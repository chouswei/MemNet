"""Honesty c: clipped pin_map / ShapeWalk MUST highlight Truncation."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import examples_dir
from memnet.mutate_gate import MutateGate
from memnet.pin_map_composer import PinMapComposer, emit_truncation
from memnet.session import open_session

runner = CliRunner()
_CST_MAP = ["SCHEMA CST ; fields=id name role ports law recycle"]
_CODING_MAP = examples_dir() / "schema.coding.example.txt"


def _star_lines(n_leaves: int) -> list[str]:
    lines = ["CREATE (:CST {id: 'CST_Hub', name: 'hub', role: 'person'})"]
    for i in range(n_leaves):
        lid = f"CST_L{i:02d}"
        lines.append(f"CREATE (:CST {{id: '{lid}', name: 'leaf{i}', role: 'person'}})")
        lines.append(
            f"MATCH (a {{id: '{lid}'}}), (b {{id: 'CST_Hub'}})\n"
            f"CREATE (a)-[:member_of {{id: 'E_m{i:02d}'}}]->(b)"
        )
    return lines


def test_emit_truncation_mark_shape():
    line = emit_truncation(
        [{"reason": "max_rows", "offered": 10, "kept": 3}],
        max_rows=3,
    )
    assert line.startswith("## Truncation ")
    assert "truncated=true" in line
    assert "M=3" in line
    assert "omitted=7" in line
    assert "reason=max_rows" in line
    assert emit_truncation([], max_rows=50) == ""


def test_max_rows_clip_emits_truncation(memnet_temp):
    del memnet_temp
    ss = open_session(map_lines=list(_CST_MAP))
    MutateGate(ss).apply(_star_lines(10), mode="add", allow_new_relation=True)
    composer = PinMapComposer(ss)

    _fit_rows, fit_text = composer.compose(anchor="CST_Hub", depth=1, max_rows=50)
    assert "## Truncation" not in fit_text
    assert "truncated=true" not in fit_text
    assert "name: 'hub'" in fit_text

    clip_rows, clip_text = composer.compose(anchor="CST_Hub", depth=1, max_rows=4)
    assert "## Truncation" in clip_text
    assert "truncated=true" in clip_text
    assert "M=4" in clip_text
    assert "reason=max_rows" in clip_text
    assert "omitted=" in clip_text
    assert "_el" not in clip_text
    assert "_memnet_hid" not in clip_text
    payload = [r for r in clip_rows if r.tag != "LAW"]
    assert len(payload) <= 4


def test_cli_pin_map_truncation_when_m_clips(memnet_temp):
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    sid = r.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    lines = ["CREATE (:TSK {id: 'TSK_hub', goal: 'clip-me', status: 'open'})"]
    for i in range(8):
        lines.append(
            f"CREATE (:MOD {{id: 'MOD_{i}', path: 'p/{i}.py', summary: 'm{i}', status: 'active'}})"
        )
        lines.append(
            f"MATCH (t {{id: 'TSK_hub'}}), (m {{id: 'MOD_{i}'}})\n"
            f"CREATE (t)-[:owns {{id: 'E{i}'}}]->(m)"
        )
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input="\n".join(lines) + "\n")
    assert add.exit_code == 0, add.stderr

    fits = runner.invoke(
        app,
        [
            "query",
            "pin-map",
            "--kind",
            "TSK",
            "--locator",
            "goal=clip-me",
            "--depth",
            "1",
            "--max-rows",
            "50",
            "--session",
            sid,
        ],
    )
    assert fits.exit_code == 0, fits.stderr
    assert "## Truncation" not in fits.stdout

    clipped = runner.invoke(
        app,
        [
            "query",
            "pin-map",
            "--kind",
            "TSK",
            "--locator",
            "goal=clip-me",
            "--depth",
            "1",
            "--max-rows",
            "3",
            "--session",
            sid,
        ],
    )
    assert clipped.exit_code == 0, clipped.stderr
    assert "## Truncation" in clipped.stdout
    assert "truncated=true" in clipped.stdout
    assert "M=3" in clipped.stdout
    assert "reason=max_rows" in clipped.stdout


def test_shell_soft_cap_emits_truncation(memnet_temp):
    del memnet_temp
    ss = open_session(map_lines=list(_CST_MAP))
    MutateGate(ss).apply(_star_lines(12), mode="add", allow_new_relation=True)
    composer = PinMapComposer(ss)
    _rows, text = composer.compose(anchor="CST_Hub", depth=2, max_rows=50, view="shell")
    assert "## Truncation" in text
    assert "reason=shell" in text
    interior_rows, interior = composer.compose(
        anchor="CST_Hub", depth=2, max_rows=50, view="interior"
    )
    assert "## Truncation" not in interior
    assert len([r for r in interior_rows if r.tag == "CST"]) > 8


def test_outline_m_clip_emits_truncation(memnet_temp):
    del memnet_temp
    ss = open_session(map_file=str(_CODING_MAP))
    lines = [f"CREATE (:TSK {{id: 'TSK_{i}', goal: 'g{i}', status: 'open'}})" for i in range(4)]
    lines.extend(
        f"CREATE (:MOD {{id: 'MOD_{i}', path: 'm/{i}.py', status: 'active'}})" for i in range(4)
    )
    MutateGate(ss).apply(lines, mode="add")
    _rows, text = PinMapComposer(ss).compose(anchor=None, max_rows=2)
    assert "## outline" in text
    assert "## Truncation" in text
    assert "M=2" in text
    assert "reason=max_rows" in text
    wide, wide_text = PinMapComposer(ss).compose(anchor=None, max_rows=50)
    assert "## outline" in wide_text
    assert "## Truncation" not in wide_text
    assert len(wide) >= 2


def test_depth_cap_emits_truncation(memnet_temp):
    del memnet_temp
    ss = open_session(map_lines=list(_CST_MAP))
    MutateGate(ss).apply(_star_lines(3), mode="add", allow_new_relation=True)
    ss.store.caps.max_depth = 1
    _rows, text = PinMapComposer(ss).compose(anchor="CST_Hub", depth=3, max_rows=50)
    assert "## Truncation" in text
    assert "reason=depth" in text
    assert "_el" not in text
