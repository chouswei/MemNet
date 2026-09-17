"""Honesty-c bundled examples grammar hygiene (teach only)."""

from __future__ import annotations

from pathlib import Path

from memnet.config import examples_dir
from memnet.mutate_gate import MutateGate
from memnet.pin_map_ingest import _CON_KIND_ENUM
from memnet.session import open_session
from memnet.tag_map import load_map_from_lines

_EXAMPLES = examples_dir()
_PIPE_BANNER = "LEFTOVER @TAG PIPE"
_NICK_BANNER = "leftover nickname"


def _schema_fields(kind: str, map_text: str) -> list[str]:
    for line in map_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"SCHEMA {kind} "):
            _, rhs = stripped.split("fields=", 1)
            return rhs.split()
    raise AssertionError(f"SCHEMA {kind} missing")


def test_sysml_map_con_matches_ingest_fields():
    """CON SCHEMA columns = Path-B ingest keys; no invented ends= property."""
    map_text = (_EXAMPLES / "schema.sysml.example.txt").read_text(encoding="utf-8")
    fields = _schema_fields("CON", map_text)
    assert "ends" not in fields
    expected = {"id", "name", "qname", "path", "sysml_kind", "kind", "recycle"}
    assert expected == set(fields)
    assert set(_CON_KIND_ENUM.values()) <= {
        "connectionDef",
        "connectionUsage",
        "linkUsage",
    }
    for kind in ("PKG", "PRT", "REQ", "POR", "CON"):
        assert f"SCHEMA {kind} " in map_text


def test_demo_gql_seed_keeps_nickname_lookup(memnet_temp):
    """CLI/MCP nickname fixtures stay: get('CFG01') after leftover-id seed."""
    header = (_EXAMPLES / "workflow.example.txt").read_text(encoding="utf-8")[:800]
    assert _NICK_BANNER in header.lower() or "leftover nickname" in header
    assert "not GraphElement identity" in header or "Not GraphElement identity" in header
    assert "leftover LAW text" in header
    ss = open_session(map_file=str(_EXAMPLES / "schema.example.txt"))
    result = MutateGate(ss).apply(
        (_EXAMPLES / "workflow.example.txt").read_text(encoding="utf-8").splitlines(),
        mode="add",
    )
    assert result.dialect == "gql"
    assert ss.store.get("CFG01") is not None
    assert ss.store.get("N01") is not None
    assert ss.store.get("E01") is not None


def test_coding_gql_seed_keeps_nickname_lookup(memnet_temp):
    header = (_EXAMPLES / "workflow.coding.example.txt").read_text(encoding="utf-8")[:900]
    assert "leftover nickname" in header
    ss = open_session(map_file=str(_EXAMPLES / "schema.coding.example.txt"))
    result = MutateGate(ss).apply(
        (_EXAMPLES / "workflow.coding.example.txt").read_text(encoding="utf-8").splitlines(),
        mode="add",
    )
    assert result.dialect == "gql"
    assert ss.store.get("CFG01") is not None
    assert ss.store.get("MOD_cli") is not None


def test_sysml_snippet_match_by_qname_not_id(memnet_temp):
    """Product teach snippet: CON node + contains/connects; no leftover id property."""
    path = _EXAMPLES / "workflow.sysml.snippet.example.txt"
    text = path.read_text(encoding="utf-8")
    assert "id:" not in text
    assert "{id" not in text
    assert ":CON" in text
    ss = open_session(map_file=str(_EXAMPLES / "schema.sysml.example.txt"))
    result = MutateGate(ss).apply(text.splitlines(), mode="add")
    assert result.dialect == "gql"
    cons = [r for r in ss.store.list_records("CON") if r.fields.get("qname") == "DemoPkg::Amp::sig"]
    assert len(cons) == 1
    assert cons[0].fields.get("kind") == "connectionUsage"
    assert not cons[0].fields.get("id")
    assert ss.store.get("sig") is None
    assert ss.store.get("DemoPkg::Amp::sig") is None
    connects = [
        r
        for r in ss.store._by_hid.values()
        if r.tag == "EDG" and r.fields.get("relation") == "connects"
    ]
    assert len(connects) == 2


def test_pipe_seeds_quarantined_not_gql_teach():
    for name in (
        "workflow.rto-remote.example.txt",
        "workflow.memnet-codebase.snap.txt",
    ):
        head = (_EXAMPLES / name).read_text(encoding="utf-8")[:600]
        assert _PIPE_BANNER in head
        assert "NOT agent GQL" in head
        assert "Do not teach this file as mutate" in head
        body_lines = [
            ln.strip()
            for ln in Path(_EXAMPLES / name).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        assert body_lines[0].startswith("@"), name
        assert not body_lines[0].startswith("CREATE"), name


def test_examples_readme_con_and_pipe_section():
    readme = (_EXAMPLES / "README.md").read_text(encoding="utf-8")
    assert "PKG/PRT/REQ/POR/**CON**" in readme or "PKG/PRT/REQ/POR/CON" in readme
    assert "leftover pipe quarantine" in readme.lower() or "leftover `@TAG` pipe" in readme
    assert "workflow.sysml.snippet.example.txt" in readme
    assert "get(\"CFG01\")" in readme
    tm = load_map_from_lines(
        (_EXAMPLES / "schema.sysml.example.txt").read_text(encoding="utf-8").splitlines()
    )
    assert "CON" in tm.tags
    assert "ends" not in tm.tags["CON"].fields
