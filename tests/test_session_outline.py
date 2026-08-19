"""0.11 session outline: empty cue is Recall census of S."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import OUTLINE_EXEMPLAR_LIMIT, examples_dir
from memnet.mutate_gate import MutateGate
from memnet.pin_map_composer import PinMapComposer
from memnet.session import open_session

runner = CliRunner()
_CODING_MAP = examples_dir() / "schema.coding.example.txt"


def _open(memnet_temp) -> str:
    del memnet_temp
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def test_empty_cue_outline_is_census_of_s(memnet_temp):
    sid = _open(memnet_temp)
    add = runner.invoke(
        app,
        ["add", "--stdin", "--session", sid],
        input=(
            "CREATE (:TSK {id: 'TSK_model_memnet', goal: 'model', status: 'open'})\n"
            "CREATE (:MOD {id: 'MOD_deploy', path: 'models/deploy.sysml', "
            "summary: 'deploy', status: 'active'})\n"
            "CREATE (:SYM {id: 'SYM_Recall', name: 'Recall', status: 'active'})\n"
            "MATCH (t {id: 'TSK_model_memnet'}), (m {id: 'MOD_deploy'})\n"
            "CREATE (t)-[:owns {id: 'E_own'}]->(m)\n"
        ),
    )
    assert add.exit_code == 0, add.stderr
    r = runner.invoke(app, ["query", "pin-map", "--session", sid])
    assert r.exit_code == 0, r.stderr
    out = r.stdout
    assert out.strip()
    assert "## outline" in out
    assert "kinds=" in out
    assert "TSK" in out
    assert "MOD" in out
    assert "SYM" in out
    assert "TSK_model_memnet" in out
    assert "status: 'open'" in out
    assert "MOD_deploy" in out
    assert "path: 'models/deploy.sysml'" in out
    assert "SYM_Recall" in out
    assert "name: 'Recall'" in out
    assert "-[:" not in out
    assert "owns" not in out
    assert "_el" not in out
    assert "_memnet_hid" not in out
    assert "no_anchor" not in r.stderr
    assert "RETURN" not in out


def test_empty_cue_with_view_shell_is_still_outline_not_shell_hop(memnet_temp):
    sid = _open(memnet_temp)
    add = runner.invoke(
        app,
        ["add", "--stdin", "--session", sid],
        input=(
            "CREATE (:TSK {id: 'TSK_live', goal: 'work', status: 'in_progress'})\n"
            "CREATE (:MOD {id: 'MOD_x', path: 'src/x.py', summary: 'mod', status: 'active'})\n"
            "MATCH (t {id: 'TSK_live'}), (m {id: 'MOD_x'})\n"
            "CREATE (t)-[:owns {id: 'E_link'}]->(m)\n"
        ),
    )
    assert add.exit_code == 0, add.stderr
    r = runner.invoke(
        app,
        ["query", "pin-map", "--view", "shell", "--session", sid],
    )
    assert r.exit_code == 0, r.stderr
    assert "## outline" in r.stdout
    assert "TSK_live" in r.stdout
    assert "MOD_x" in r.stdout
    assert "-[:" not in r.stdout
    assert "owns" not in r.stdout
    assert "_el" not in r.stdout
    assert "_memnet_hid" not in r.stdout


def test_outline_hard_limit_exemplars_not_dump_s(memnet_temp):
    sid = _open(memnet_temp)
    lines = [
        f"CREATE (:TSK {{id: 'TSK_{i}', goal: 'g{i}', status: 'in_progress'}})" for i in range(8)
    ]
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input="\n".join(lines) + "\n")
    assert add.exit_code == 0, add.stderr
    r = runner.invoke(app, ["query", "pin-map", "--session", sid])
    assert r.exit_code == 0, r.stderr
    shown = [ln for ln in r.stdout.splitlines() if ln.startswith("(:TSK")]
    assert len(shown) == OUTLINE_EXEMPLAR_LIMIT
    assert "kinds=" in r.stdout and "TSK" in r.stdout
    assert "-[:" not in r.stdout


def test_outline_cue_conflict_if_exemplar_name_collides(memnet_temp):
    sid = _open(memnet_temp)
    line = "CREATE (:TSK {id: 'trump', goal: 'same-name', status: 'in_progress'})\n"
    a = runner.invoke(app, ["add", "--stdin", "--session", sid], input=line)
    b = runner.invoke(app, ["add", "--stdin", "--session", sid], input=line)
    assert a.exit_code == 0, a.stderr
    assert b.exit_code == 0, b.stderr
    r = runner.invoke(app, ["query", "pin-map", "--session", sid])
    assert r.exit_code == 0, r.stderr
    assert "## outline" in r.stdout
    assert "CueConflict" in r.stdout
    assert r.stdout.count("trump") >= 2
    assert "-[:" not in r.stdout
    assert "_el" not in r.stdout


def test_outline_does_not_require_anchor_or_match_seed(memnet_temp):
    ss = open_session(map_file=str(_CODING_MAP))
    MutateGate(ss).apply(
        ["CREATE (:TSK {goal: 'solo', status: 'in_progress'})"],
        mode="add",
    )
    rows, text = PinMapComposer(ss).compose(
        anchor=None, view=None, kind=None, locators=None, keyword=None
    )
    assert "## outline" in text
    assert "(:TSK" in text
    assert "solo" in text
    assert rows
    assert all(r.tag != "EDG" for r in rows)
    assert "_el" not in text
    assert "_memnet_hid" not in text
