"""0.12 SameThingAbsorb: agent-gated Commit after CueConflict; not ImportAbsorb."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import examples_dir
from memnet.exceptions import MemNetError
from memnet.gql import parse
from memnet.import_absorb import import_slice
from memnet.mutate_gate import MutateGate
from memnet.session import get_session, open_session
from memnet.tier_a import NodeRec

runner = CliRunner()
_CODING_MAP = examples_dir() / "schema.coding.example.txt"

_MAP = [
    "SCHEMA MOD ; fields=id path note",
    "SCHEMA SYM ; fields=id kind refdes",
    "SCHEMA TSK ; fields=id goal status recycle",
]


def _open() -> str:
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def test_parse_same_thing_set_is_commit_not_verb():
    doc = parse("MATCH (a:TSK {goal: 'alpha'}), (b:TSK {goal: 'beta'})\nSET a += b")
    assert len(doc.items) == 1
    n = doc.items[0]
    assert isinstance(n, NodeRec)
    assert n.same_thing is True
    assert n.kind == "TSK"
    assert n.match_props.get("goal") == "alpha"
    assert n.absorb_kind == "TSK"
    assert n.absorb_match_props.get("goal") == "beta"


def test_two_same_name_stay_two_after_find(memnet_temp):
    del memnet_temp
    sid = _open()
    line = "CREATE (:TSK {id: 'trump', goal: 'same-name', status: 'in_progress'})\n"
    assert runner.invoke(app, ["add", "--stdin", "--session", sid], input=line).exit_code == 0
    assert runner.invoke(app, ["add", "--stdin", "--session", sid], input=line).exit_code == 0
    found = runner.invoke(
        app,
        [
            "query",
            "find",
            "--kind",
            "TSK",
            "--locator",
            "id=trump",
            "--limit",
            "8",
            "--session",
            sid,
        ],
    )
    assert found.exit_code == 0, found.stderr
    assert "CueConflict" in found.stdout
    assert "|Q|=" in found.stdout
    ss = get_session(sid)
    assert len(ss.store.match_nickname("trump")) == 2


def test_cue_conflict_before_absorb_then_one_pattern(memnet_temp):
    del memnet_temp
    sid = _open()
    batch = "\n".join(
        [
            "CREATE (:TSK {id: 'trump', goal: 'alpha', status: 'in_progress'})",
            "CREATE (:TSK {id: 'trump', goal: 'beta', status: 'in_progress'})",
        ]
    )
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input=batch + "\n")
    assert add.exit_code == 0, add.stderr
    before = runner.invoke(
        app,
        [
            "query",
            "find",
            "--kind",
            "TSK",
            "--locator",
            "id=trump",
            "--limit",
            "8",
            "--session",
            sid,
        ],
    )
    assert before.exit_code == 0, before.stderr
    assert "CueConflict" in before.stdout
    assert "alpha" in before.stdout
    assert "beta" in before.stdout
    absorb = runner.invoke(
        app,
        ["update", "--stdin", "--session", sid],
        input="MATCH (a:TSK {goal: 'alpha'}), (b:TSK {goal: 'beta'})\nSET a += b\n",
    )
    assert absorb.exit_code == 0, absorb.stderr
    assert "_el" not in absorb.stdout
    assert "_memnet_hid" not in absorb.stdout
    ss = get_session(sid)
    hits = ss.store.match_nodes(tag="TSK", props={"id": "trump"})
    assert len(hits) == 1
    survivor = hits[0]
    assert survivor.fields.get("goal") == "alpha"
    aka = survivor.fields.get("aka") or survivor.fields.get("AKA") or ""
    assert "beta" in aka
    assert survivor.hid not in absorb.stdout
    after = runner.invoke(
        app,
        [
            "query",
            "find",
            "--kind",
            "TSK",
            "--locator",
            "id=trump",
            "--limit",
            "8",
            "--session",
            sid,
        ],
    )
    assert after.exit_code == 0, after.stderr
    assert "CueConflict" not in after.stdout
    warm = runner.invoke(
        app,
        ["query", "pin-map", "--kind", "TSK", "--locator", "goal=alpha", "--session", sid],
    )
    assert warm.exit_code == 0, warm.stderr
    assert survivor.hid not in warm.stdout
    assert "_memnet_hid" not in warm.stdout


def test_merge_same_name_does_not_absorb(memnet_temp):
    del memnet_temp
    sid = _open()
    line = "CREATE (:TSK {id: 'trump', goal: 'same-name', status: 'in_progress'})\n"
    assert runner.invoke(app, ["add", "--stdin", "--session", sid], input=line).exit_code == 0
    assert runner.invoke(app, ["add", "--stdin", "--session", sid], input=line).exit_code == 0
    merged = runner.invoke(
        app,
        ["update", "--stdin", "--session", sid],
        input="MERGE (:TSK {id: 'trump'})\n",
    )
    assert merged.exit_code != 0
    assert "cue_conflict" in (merged.stderr + merged.stdout).lower() or "CueConflict" in (
        merged.stderr + merged.stdout
    )
    ss = get_session(sid)
    assert len(ss.store.match_nickname("trump")) == 2


def test_same_name_name_only_patterns_stay_two(memnet_temp):
    del memnet_temp
    ss = open_session(map_file=str(_CODING_MAP))
    gate = MutateGate(ss)
    gate.apply(
        [
            "CREATE (:TSK {id: 'trump', goal: 'alpha', status: 'in_progress'})",
            "CREATE (:TSK {id: 'trump', goal: 'beta', status: 'in_progress'})",
        ],
        mode="add",
    )
    with pytest.raises(MemNetError) as ei:
        gate.apply(
            ["MATCH (a:TSK {id: 'trump'}), (b:TSK {id: 'trump'})\nSET a += b"],
            mode="update",
        )
    assert ei.value.code == "cue_conflict"
    assert len(ss.store.match_nickname("trump")) == 2


def test_import_absorb_does_not_entity_resolve(memnet_temp):
    del memnet_temp
    member = open_session(map_lines=_MAP)
    lead = open_session(map_lines=_MAP)
    MutateGate(lead).apply(
        ["CREATE (:MOD {id: 'MOD_amp', path: 'old.md', note: 'stale'})"],
        mode="add",
    )
    MutateGate(member).apply(
        ["CREATE (:MOD {id: 'MOD_amp', path: 'docs/note.md', note: 'amp'})"],
        mode="add",
    )
    import_slice(
        lead_session_id=lead.session_id,
        source_session_id=member.session_id,
        anchors=["MOD_amp"],
        id_policy="keep",
        enable_guard=False,
    )
    mods = lead.store.match_nickname("MOD_amp")
    assert len(mods) == 2
    paths = {r.fields.get("path") for r in mods}
    assert "docs/note.md" in paths
    assert "old.md" in paths
