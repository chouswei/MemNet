"""0.13 goldfish caller: stuffed history of maps is a fail."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import examples_dir
from memnet.exceptions import MemNetError
from memnet.goldfish_caller import (
    PromptPart,
    drop_prior_pin_maps,
    judge_goldfish_prompt,
    judge_sparse_commit,
    pin_map_bodies,
)
from memnet.mutate_gate import MutateGate
from memnet.pin_map_composer import PinMapComposer
from memnet.session import open_session

runner = CliRunner()
_CODING_MAP = examples_dir() / "schema.coding.example.txt"

_MAP_T1 = "(:TSK {goal: 'turn1', status: 'in_progress'})\n"
_MAP_T2 = "(:TSK {goal: 'turn2', status: 'in_progress'})\n"
_MAP_T3 = "(:TSK {goal: 'turn3', status: 'in_progress'})\n"
_ENV_BLOB = "E       test_foo.py:12  AssertionError: expected 1\n"


def test_stuffed_history_of_maps_is_a_fail():
    history = [
        PromptPart("other", "user: continue"),
        PromptPart("pin_map", _MAP_T1),
        PromptPart("other", "assistant: ok"),
        PromptPart("pin_map", _MAP_T2),
        PromptPart("env_blob", _ENV_BLOB),
        PromptPart("pin_map", _MAP_T3),
    ]
    assert len(pin_map_bodies(history)) == 3
    with pytest.raises(MemNetError) as ei:
        judge_goldfish_prompt(history)
    assert ei.value.code == "stuffed_maps"


def test_drop_prior_maps_then_prompt_ok():
    history = [
        PromptPart("pin_map", _MAP_T1),
        PromptPart("env_blob", _ENV_BLOB),
        PromptPart("pin_map", _MAP_T2),
        PromptPart("pin_map", _MAP_T3),
        PromptPart("other", "user: next"),
    ]
    packed = drop_prior_pin_maps(history)
    judge_goldfish_prompt(packed)
    bodies = pin_map_bodies(packed)
    assert bodies == [_MAP_T3]
    assert any(p.channel == "env_blob" for p in packed)


def test_skip_and_env_blob_without_map_ok():
    judge_goldfish_prompt(
        [
            PromptPart("other", "user: hello"),
            PromptPart("pin_map", ""),
            PromptPart("env_blob", _ENV_BLOB),
        ]
    )


def test_echo_fetched_map_is_not_sparse_delta():
    with pytest.raises(MemNetError) as ei:
        judge_sparse_commit(
            pin_map_text=_MAP_T1,
            mutate_text="CREATE " + _MAP_T1.strip() + "\n",
        )
    assert ei.value.code == "echo_map"
    judge_sparse_commit(
        pin_map_text=_MAP_T1,
        mutate_text="MATCH (t:TSK {goal: 'turn1'}) SET t.status = 'settled'\n",
    )


def _open_coding(memnet_temp) -> str:
    del memnet_temp
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def test_empty_cue_is_outline_regardless_of_view(memnet_temp):
    sid = _open_coding(memnet_temp)
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
    plain = runner.invoke(app, ["query", "pin-map", "--session", sid])
    assert plain.exit_code == 0, plain.stderr
    assert "## outline" in plain.stdout
    with_shell = runner.invoke(
        app,
        ["query", "pin-map", "--view", "shell", "--session", sid],
    )
    assert with_shell.exit_code == 0, with_shell.stderr
    assert "## outline" in with_shell.stdout
    assert "no_anchor" not in with_shell.stderr
    assert "goal: 'work'" in with_shell.stdout
    assert "path: 'src/x.py'" in with_shell.stdout
    assert "-[:" not in with_shell.stdout
    assert "owns" not in with_shell.stdout
    # view=shell is not the outline operator; empty q is.
    help_r = runner.invoke(app, ["query", "pin-map", "--help"])
    assert (
        "grain on a seed" in help_r.stdout
        or "not the outline" in help_r.stdout.lower()
        or "not session outline" in help_r.stdout
    )


def test_view_shell_is_grain_on_a_seed_not_session_outline(memnet_temp):
    ss = open_session(map_file=str(_CODING_MAP))
    MutateGate(ss).apply(
        [
            "CREATE (:TSK {id: 'TSK_live', goal: 'work', status: 'in_progress'})",
            "CREATE (:MOD {id: 'MOD_unlinked', path: 'src/y.py', "
            "summary: 'other', status: 'active'})",
            "CREATE (:USR {id: 'USR_one', topic: 'size', "
            "content: 'keep it small', status: 'active'})",
        ],
        mode="add",
    )
    census, census_text = PinMapComposer(ss).compose(
        anchor=None, view="shell", kind=None, locators=None, keyword=None
    )
    assert "## outline" in census_text
    assert "goal: 'work'" in census_text
    assert "path: 'src/y.py'" in census_text
    assert "topic: 'size'" in census_text
    assert "-[:" not in census_text
    assert all(r.tag != "EDG" for r in census)

    rows, text = PinMapComposer(ss).compose(
        anchor=None,
        view="shell",
        kind="TSK",
        locators=[("goal", "work")],
    )
    assert "goal: 'work'" in text
    assert "path: 'src/y.py'" not in text
    assert "topic: 'size'" not in text
    kinds = {r.tag for r in rows if r.tag not in {"LAW", "EDG"}}
    assert kinds <= {"TSK"}
