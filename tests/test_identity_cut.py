"""0.10 identity cut: GraphElement, CREATE (), CueConflict, two same-name stay two."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import examples_dir
from memnet.gql import parse
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.tier_a import NodeRec, Op

runner = CliRunner()
_CODING_MAP = examples_dir() / "schema.coding.example.txt"


def _open() -> str:
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def test_create_empty_node_legal():
    doc = parse("CREATE ()")
    assert len(doc.items) == 1
    n = doc.items[0]
    assert isinstance(n, NodeRec)
    assert n.op == Op.CREATE
    assert n.kind == ""
    assert n.id == ""


def test_two_same_nickname_stay_two(memnet_temp):
    del memnet_temp
    sid = _open()
    line = "CREATE (:TSK {id: 'trump', goal: 'same-name', status: 'in_progress'})\n"
    a = runner.invoke(app, ["add", "--stdin", "--session", sid], input=line)
    b = runner.invoke(app, ["add", "--stdin", "--session", sid], input=line)
    assert a.exit_code == 0, a.stderr
    assert b.exit_code == 0, b.stderr
    from memnet.session import get_session

    ss = get_session(sid)
    hits = ss.store.match_nickname("trump")
    assert len(hits) == 2
    assert hits[0].hid != hits[1].hid


def test_find_cue_conflict_when_q_gt_1(memnet_temp):
    del memnet_temp
    sid = _open()
    batch = "\n".join(
        [
            "CREATE (:TSK {id: 'TSK_a', goal: 'alpha', status: 'in_progress'})",
            "CREATE (:TSK {id: 'TSK_b', goal: 'beta', status: 'in_progress'})",
            "CREATE (:TSK {id: 'TSK_c', goal: 'gamma', status: 'in_progress'})",
        ]
    )
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input=batch + "\n")
    assert add.exit_code == 0, add.stderr
    r = runner.invoke(app, ["query", "find", "--kind", "TSK", "--limit", "2", "--session", sid])
    assert r.exit_code == 0, r.stderr
    assert "CueConflict" in r.stdout
    assert "|Q|=" in r.stdout
    assert "RETURN" not in r.stdout


def test_pin_map_empty_cue_skips(memnet_temp):
    del memnet_temp
    sid = _open()
    missing = runner.invoke(app, ["query", "pin-map", "--session", sid])
    assert missing.exit_code == 0, missing.stderr
    assert "no_anchor" not in missing.stderr
    assert missing.stdout.strip() == ""


def test_pin_map_from_cue_kind(memnet_temp):
    del memnet_temp
    sid = _open()
    add = runner.invoke(
        app,
        ["add", "--stdin", "--session", sid],
        input="CREATE (:TSK {goal: 'solo', status: 'in_progress'})\n",
    )
    assert add.exit_code == 0, add.stderr
    r = runner.invoke(
        app,
        ["query", "pin-map", "--kind", "TSK", "--locator", "goal=solo", "--session", sid],
    )
    assert r.exit_code == 0, r.stderr
    assert "(:TSK" in r.stdout
    assert "CueConflict" not in r.stdout


def test_pin_map_cue_conflict_when_kind_matches_many(memnet_temp):
    del memnet_temp
    sid = _open()
    batch = "\n".join(
        [
            "CREATE (:TSK {goal: 'alpha', status: 'in_progress'})",
            "CREATE (:TSK {goal: 'beta', status: 'in_progress'})",
        ]
    )
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input=batch + "\n")
    assert add.exit_code == 0, add.stderr
    r = runner.invoke(app, ["query", "pin-map", "--kind", "TSK", "--session", sid])
    assert r.exit_code == 0, r.stderr
    assert "CueConflict" in r.stdout
    assert "|Q|=" in r.stdout
    assert "(:TSK" in r.stdout or "TSK" in r.stdout


def test_create_unlabeled_commits(memnet_temp):
    del memnet_temp
    ss = open_session(map_file=str(_CODING_MAP))
    result = MutateGate(ss).apply(["CREATE ()"], mode="add")
    assert result.dialect == "gql"
    blanks = [r for r in ss.store.list_records() if r.tag == ""]
    assert len(blanks) == 1
    assert blanks[0].id == ""


def test_hid_off_cli_pin_map_and_merge_ack(memnet_temp):
    sid = _open()
    create = runner.invoke(
        app,
        ["add", "--stdin", "--session", sid],
        input="CREATE (:TSK {id: 'TSK_wire', goal: 'hid-off', status: 'in_progress'})\n",
    )
    assert create.exit_code == 0, create.stderr
    assert "_el" not in create.stdout

    merge = runner.invoke(
        app,
        ["update", "--stdin", "--session", sid],
        input="MERGE (n:TSK {id: 'TSK_wire'}) SET n.status = 'settled'\n",
    )
    assert merge.exit_code == 0, merge.stderr
    assert "_el" not in merge.stdout
    assert "{id: '_el" not in merge.stdout.replace(" ", "")

    pin = runner.invoke(
        app,
        ["query", "pin-map", "--kind", "TSK", "--locator", "id=TSK_wire", "--session", sid],
    )
    assert pin.exit_code == 0, pin.stderr
    assert "_el" not in pin.stdout

    from memnet.session import get_session

    ss = get_session(sid)
    rows = ss.store.to_jsonl_rows()
    assert all("hid" not in row for row in rows)
    dump = ss.store.list_records("TSK")[0].model_dump()
    assert "hid" not in dump


def test_leftover_cli_read_get_nickname_only(memnet_temp):
    sid = _open()
    add = runner.invoke(
        app,
        ["add", "--stdin", "--session", sid],
        input="CREATE (:TSK {id: 'TSK_nick', goal: 'leftover-get', status: 'in_progress'})\n",
    )
    assert add.exit_code == 0, add.stderr
    from memnet.session import get_session

    hid = get_session(sid).store.match_nickname("TSK_nick")[0].hid
    by_nick = runner.invoke(app, ["read", "get", "--id", "TSK_nick", "--session", sid])
    assert by_nick.exit_code == 0, by_nick.stderr
    assert "TSK_nick" in by_nick.stdout
    assert hid not in by_nick.stdout
    by_hid = runner.invoke(app, ["read", "get", "--id", hid, "--session", sid])
    assert by_hid.exit_code != 0
