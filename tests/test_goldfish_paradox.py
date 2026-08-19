"""Goldfish paradox V1/V3/V4/V6 + V5 — coding map + GQL."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import examples_dir

runner = CliRunner()

_CODING_MAP = examples_dir() / "schema.coding.example.txt"


def _open_coding(memnet_temp) -> str:
    del memnet_temp
    r = runner.invoke(app, ["session", "open", "--map-file", str(_CODING_MAP)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def _add(sid: str, gql: str) -> None:
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input=gql)
    assert add.exit_code == 0, add.stderr


def _pin(sid: str, *anchors: str, max_rows: int | None = None) -> object:
    argv = ["query", "pin-map", "--session", sid]
    for a in anchors:
        argv.extend(["--anchor", a])
    if max_rows is not None:
        argv.extend(["--max-rows", str(max_rows)])
    return runner.invoke(app, argv)


def test_v1_isolated_tsk_hides_unlinked_mod(memnet_temp):
    sid = _open_coding(memnet_temp)
    _add(
        sid,
        "CREATE (:TSK {id: 'TSK_x', goal: 'solo', status: 'in_progress'})\n"
        "CREATE (:MOD {id: 'MOD_y', path: 'src/y.py', summary: 'unlinked', status: 'active'})\n",
    )
    first = _pin(sid, "TSK_x")
    assert first.exit_code == 0, first.stderr
    assert "TSK_x" in first.stdout
    assert "MOD_y" not in first.stdout
    _add(
        sid,
        "MATCH (t {id: 'TSK_x'}), (m {id: 'MOD_y'})\nCREATE (t)-[:owns {id: 'NEW'}]->(m)\n",
    )
    second = _pin(sid, "TSK_x")
    assert second.exit_code == 0, second.stderr
    assert "MOD_y" in second.stdout


def test_v3_empty_read_list_then_empty_cue_skips(memnet_temp):
    sid = _open_coding(memnet_temp)
    listed = runner.invoke(app, ["read", "list", "--tag", "TSK", "--active-only", "--session", sid])
    assert listed.exit_code == 0, listed.stderr
    assert "TSK" not in listed.stdout or "(:TSK" not in listed.stdout
    assert "TSK_" not in listed.stdout
    missing = runner.invoke(app, ["query", "pin-map", "--session", sid])
    assert missing.exit_code == 0, missing.stderr
    assert "no_anchor" not in missing.stderr
    assert missing.stdout.strip() == ""


def test_v4_sparse_owns_edge(memnet_temp):
    sid = _open_coding(memnet_temp)
    _add(
        sid,
        "CREATE (:TSK {id: 'TSK_a', goal: 'sparse', status: 'in_progress'})\n"
        "CREATE (:MOD {id: 'MOD_a', path: 'src/a.py', summary: 'mod', status: 'active'})\n",
    )
    before = _pin(sid, "TSK_a")
    assert before.exit_code == 0, before.stderr
    assert "owns" not in before.stdout
    _add(
        sid,
        "MATCH (t {id: 'TSK_a'}), (m {id: 'MOD_a'})\nCREATE (t)-[:owns {id: 'NEW'}]->(m)\n",
    )
    after = _pin(sid, "TSK_a")
    assert after.exit_code == 0, after.stderr
    assert "owns" in after.stdout
    assert "MOD_a" in after.stdout


def test_v6_two_same_nickname_stay_two(memnet_temp):
    sid = _open_coding(memnet_temp)
    line = "CREATE (:TSK {id: 'TSK_dup', goal: 'once', status: 'in_progress'})\n"
    _add(sid, line)
    dup = runner.invoke(app, ["add", "--stdin", "--session", sid], input=line)
    assert dup.exit_code == 0, dup.stderr
    from memnet.session import get_session

    ss = get_session(sid)
    assert len(ss.store.match_nickname("TSK_dup")) == 2


def test_v2_union_under_one_m(memnet_temp):
    sid = _open_coding(memnet_temp)
    batch = [
        "CREATE (:TSK {id: 'TSK_a', goal: 'star-a', status: 'in_progress'})",
        "CREATE (:TSK {id: 'TSK_b', goal: 'star-b', status: 'in_progress'})",
    ]
    for i in range(3):
        batch.append(
            f"CREATE (:MOD {{id: 'MOD_a{i}', path: 'a/{i}.py', summary: 'a{i}', status: 'active'}})"
        )
        batch.append(
            f"MATCH (t {{id: 'TSK_a'}}), (m {{id: 'MOD_a{i}'}})\n"
            f"CREATE (t)-[:owns {{id: 'NEW'}}]->(m)"
        )
        batch.append(
            f"CREATE (:MOD {{id: 'MOD_b{i}', path: 'b/{i}.py', summary: 'b{i}', status: 'active'}})"
        )
        batch.append(
            f"MATCH (t {{id: 'TSK_b'}}), (m {{id: 'MOD_b{i}'}})\n"
            f"CREATE (t)-[:owns {{id: 'NEW'}}]->(m)"
        )
    _add(sid, "\n".join(batch) + "\n")
    _add(
        sid,
        "CREATE (:LAW {id: 'LAW01', name: 'EDG', cycle: 'on_context', "
        "mechanism: 'hide', constraint: 'settled_edg_unless_anchor'})\n",
    )
    both = _pin(sid, "TSK_a", "TSK_b", max_rows=5)
    assert both.exit_code == 0, both.stderr
    payload = [ln for ln in both.stdout.splitlines() if ln.startswith("(:")]
    law_lines = [ln for ln in payload if ln.startswith("(:LAW")]
    body = [ln for ln in payload if not ln.startswith("(:LAW")]
    assert law_lines, both.stdout
    assert both.stdout.count("(:LAW {id: 'LAW01'") == 1
    assert payload[: len(law_lines)] == law_lines
    assert len(body) <= 5
    mods = {ln for ln in body if "MOD_" in ln}
    assert len(mods) < 6, "both stars must not fully expand under one M"


def test_v5_n_pin_maps_repeat_law(memnet_temp):
    sid = _open_coding(memnet_temp)
    _add(
        sid,
        "CREATE (:LAW {id: 'LAW01', name: 'EDG', cycle: 'on_context', "
        "mechanism: 'hide', constraint: 'settled_edg_unless_anchor'})\n"
        "CREATE (:TSK {id: 'TSK_v5', goal: 'one-task', status: 'in_progress'})\n"
        "CREATE (:MOD {id: 'MOD_v5a', path: 'a.py', summary: 'a', status: 'active'})\n"
        "CREATE (:MOD {id: 'MOD_v5b', path: 'b.py', summary: 'b', status: 'active'})\n"
        "MATCH (t {id: 'TSK_v5'}), (a {id: 'MOD_v5a'})\n"
        "CREATE (t)-[:owns {id: 'NEW'}]->(a)\n"
        "MATCH (t {id: 'TSK_v5'}), (b {id: 'MOD_v5b'})\n"
        "CREATE (t)-[:owns {id: 'NEW'}]->(b)\n",
    )
    anchors = ("TSK_v5", "MOD_v5a", "TSK_v5", "MOD_v5b", "TSK_v5")
    law_hits = 0
    first_out = ""
    for i, aid in enumerate(anchors):
        r = _pin(sid, aid)
        assert r.exit_code == 0, r.stderr
        n = r.stdout.count("(:LAW {id: 'LAW01'")
        assert n == 1, r.stdout
        law_hits += n
        if i == 0:
            first_out = r.stdout
    assert law_hits == 5
    assert "TSK_v5" in first_out
