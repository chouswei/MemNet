"""0.18 Peak_L last-resort residual cue — never default goldfish."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app
from memnet.config import examples_dir
from memnet.peak_l import residual_degree
from memnet.session import get_session

runner = CliRunner()
_SYSML_MAP = examples_dir() / "schema.sysml.example.txt"
_CODING_MAP = examples_dir() / "schema.coding.example.txt"


def _open(memnet_temp, map_file=_SYSML_MAP) -> str:
    del memnet_temp
    r = runner.invoke(app, ["session", "open", "--map-file", str(map_file)])
    assert r.exit_code == 0, r.stderr
    return r.stdout.strip().split("|")[0].replace("@SESSION: ", "")


def _add(sid: str, gql: str) -> None:
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input=gql)
    assert add.exit_code == 0, add.stderr


def _ingest_tree(sid: str) -> None:
    """PKG/MOD contains-tree (raw-degree trap) plus a residual TSK star."""
    _add(
        sid,
        "CREATE (:PKG {id: 'PKG_root', name: 'root', qname: 'Root', path: 'models', "
        "sysml_kind: 'package', grain: 'catalog', kind_band: 'pkg'})\n"
        "CREATE (:PRT {id: 'PRT_a', name: 'A', qname: 'Root::A', path: 'a.sysml', "
        "sysml_kind: 'part'})\n"
        "CREATE (:PRT {id: 'PRT_b', name: 'B', qname: 'Root::B', path: 'b.sysml', "
        "sysml_kind: 'part'})\n"
        "CREATE (:PRT {id: 'PRT_c', name: 'C', qname: 'Root::C', path: 'c.sysml', "
        "sysml_kind: 'part'})\n"
        "CREATE (:PRT {id: 'PRT_d', name: 'D', qname: 'Root::D', path: 'd.sysml', "
        "sysml_kind: 'part'})\n"
        "MATCH (p {id: 'PKG_root'}), (a {id: 'PRT_a'})\n"
        "CREATE (p)-[:contains {id: 'E_ca'}]->(a)\n"
        "MATCH (p {id: 'PKG_root'}), (b {id: 'PRT_b'})\n"
        "CREATE (p)-[:contains {id: 'E_cb'}]->(b)\n"
        "MATCH (p {id: 'PKG_root'}), (c {id: 'PRT_c'})\n"
        "CREATE (p)-[:contains {id: 'E_cc'}]->(c)\n"
        "MATCH (p {id: 'PKG_root'}), (d {id: 'PRT_d'})\n"
        "CREATE (p)-[:contains {id: 'E_cd'}]->(d)\n"
        "CREATE (:TSK {id: 'TSK_live', goal: 'work', status: 'in_progress'})\n"
        "CREATE (:USR {id: 'USR_scope', topic: 'scope', content: 'bound', status: 'open'})\n"
        "MATCH (t {id: 'TSK_live'}), (a {id: 'PRT_a'})\n"
        "CREATE (t)-[:owns {id: 'E_oa'}]->(a)\n"
        "MATCH (t {id: 'TSK_live'}), (u {id: 'USR_scope'})\n"
        "CREATE (t)-[:next {id: 'E_nu'}]->(u)\n",
    )


def test_v9_contains_parent_is_not_rho_star_peak(memnet_temp):
    """V9: raw degree peaks on PKG; ρ* last-resort seeds the residual TSK."""
    sid = _open(memnet_temp)
    _ingest_tree(sid)
    store = get_session(sid).store
    pkg = store.match_nickname("PKG_root")[0]
    tsk = store.match_nickname("TSK_live")[0]
    assert residual_degree(store, pkg.hid) == 0
    assert residual_degree(store, tsk.hid) >= 2
    miss = runner.invoke(
        app,
        [
            "query",
            "pin-map",
            "--keyword",
            "zzznosuchcue018",
            "--depth",
            "1",
            "--session",
            sid,
        ],
    )
    assert miss.exit_code == 0, miss.stderr
    assert "## outline" not in miss.stdout
    assert "goal: 'work'" in miss.stdout
    assert "owns" in miss.stdout
    assert "contains" not in miss.stdout
    assert "CueConflict" not in miss.stdout
    assert "_el" not in miss.stdout
    assert "_memnet_hid" not in miss.stdout


def test_peak_not_used_when_codebook_hits(memnet_temp):
    sid = _open(memnet_temp)
    _ingest_tree(sid)
    hit = runner.invoke(
        app,
        [
            "query",
            "pin-map",
            "--kind",
            "PKG",
            "--locator",
            "name=root",
            "--depth",
            "1",
            "--session",
            sid,
        ],
    )
    assert hit.exit_code == 0, hit.stderr
    assert "name: 'root'" in hit.stdout
    assert "contains" in hit.stdout
    assert "goal: 'work'" not in hit.stdout
    assert "## CueConflict" not in hit.stdout


def test_peak_not_used_for_empty_q_outline(memnet_temp):
    sid = _open(memnet_temp)
    _ingest_tree(sid)
    outlined = runner.invoke(app, ["query", "pin-map", "--session", sid])
    assert outlined.exit_code == 0, outlined.stderr
    assert "## outline" in outlined.stdout
    assert "-[:" not in outlined.stdout
    assert "owns" not in outlined.stdout
    assert "CueConflict" not in outlined.stdout


def test_peak_not_default_pin_map(memnet_temp):
    sid = _open(memnet_temp, _CODING_MAP)
    _add(
        sid,
        "CREATE (:TSK {id: 'TSK_hub', goal: 'hub', status: 'in_progress'})\n"
        "CREATE (:MOD {id: 'MOD_a', path: 'a.py', summary: 'a', status: 'active'})\n"
        "MATCH (t {id: 'TSK_hub'}), (m {id: 'MOD_a'})\n"
        "CREATE (t)-[:owns {id: 'NEW'}]->(m)\n",
    )
    empty = runner.invoke(app, ["query", "pin-map", "--session", sid])
    assert empty.exit_code == 0, empty.stderr
    assert "## outline" in empty.stdout
    assert "owns" not in empty.stdout


def test_two_peaks_cue_conflict(memnet_temp):
    sid = _open(memnet_temp, _CODING_MAP)
    _add(
        sid,
        "CREATE (:TSK {id: 'TSK_a', goal: 'star-a', status: 'in_progress'})\n"
        "CREATE (:TSK {id: 'TSK_b', goal: 'star-b', status: 'in_progress'})\n"
        "CREATE (:MOD {id: 'MOD_a0', path: 'a0.py', summary: 'a0', status: 'active'})\n"
        "CREATE (:MOD {id: 'MOD_a1', path: 'a1.py', summary: 'a1', status: 'active'})\n"
        "CREATE (:MOD {id: 'MOD_b0', path: 'b0.py', summary: 'b0', status: 'active'})\n"
        "CREATE (:MOD {id: 'MOD_b1', path: 'b1.py', summary: 'b1', status: 'active'})\n"
        "MATCH (t {id: 'TSK_a'}), (m {id: 'MOD_a0'})\n"
        "CREATE (t)-[:owns {id: 'NEW'}]->(m)\n"
        "MATCH (t {id: 'TSK_a'}), (m {id: 'MOD_a1'})\n"
        "CREATE (t)-[:owns {id: 'NEW'}]->(m)\n"
        "MATCH (t {id: 'TSK_b'}), (m {id: 'MOD_b0'})\n"
        "CREATE (t)-[:owns {id: 'NEW'}]->(m)\n"
        "MATCH (t {id: 'TSK_b'}), (m {id: 'MOD_b1'})\n"
        "CREATE (t)-[:owns {id: 'NEW'}]->(m)\n",
    )
    miss = runner.invoke(
        app,
        ["query", "pin-map", "--keyword", "zzznosuchcue018", "--session", sid],
    )
    assert miss.exit_code == 0, miss.stderr
    assert "CueConflict" in miss.stdout
    assert "|Q|=2" in miss.stdout
    assert "goal: 'star-a'" in miss.stdout
    assert "goal: 'star-b'" in miss.stdout
    assert "-[:" not in miss.stdout
    assert "_el" not in miss.stdout


def test_find_codebook_miss_does_not_peak(memnet_temp):
    sid = _open(memnet_temp, _CODING_MAP)
    _add(
        sid,
        "CREATE (:TSK {id: 'TSK_hub', goal: 'hub', status: 'in_progress'})\n"
        "CREATE (:MOD {id: 'MOD_a', path: 'a.py', summary: 'a', status: 'active'})\n"
        "MATCH (t {id: 'TSK_hub'}), (m {id: 'MOD_a'})\n"
        "CREATE (t)-[:owns {id: 'NEW'}]->(m)\n",
    )
    found = runner.invoke(
        app,
        [
            "query",
            "find",
            "--kind",
            "TSK",
            "--keyword",
            "zzznosuchcue018",
            "--limit",
            "5",
            "--session",
            sid,
        ],
    )
    assert found.exit_code == 0, found.stderr
    assert found.stdout.strip() == ""
