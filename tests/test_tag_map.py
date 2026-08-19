"""tagMap tests."""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.fixed_tags import fixed_tag_map
from memnet.tag_map import load_map_from_lines, parse_line
from memnet.wire import join_payload, split_payload


def test_split_join_roundtrip():
    assert split_payload("a|b\\|c|d") == ["a", "b|c", "d"]
    assert join_payload(["a", "b|c"]) == "a|b\\|c"


def test_fixed_tags_present():
    tm = fixed_tag_map()
    assert "EDG" in tm.tags
    assert "LAW" in tm.tags
    assert tm.tags["EDG"].fields == [
        "id",
        "src",
        "relation",
        "dist",
        "at",
        "attrs",
        "recycle",
    ]


def test_cannot_redefine_edg():
    with pytest.raises(MemNetError) as exc:
        load_map_from_lines(["@EDG: id|src|relation|dist|attrs|recycle"])
    assert exc.value.code == "fixed_tag"


def test_user_map_allows_fields_without_id_first():
    tm = load_map_from_lines(["@FOO: name|id"])
    assert tm.tags["FOO"].fields[0] == "name"
    assert "id" in tm.tags["FOO"].fields


def test_schema_shared_dialect_load():
    tm = load_map_from_lines(
        [
            "SCHEMA NPC ; fields=id name traits corruption craft funding_gap status recycle",
            "SCHEMA BIZ ; fields=id name type location profit cashflow employees recycle",
        ]
    )
    assert tm.tags["NPC"].fields[0] == "id"
    assert "name" in tm.tags["BIZ"].fields


def test_schema_shared_not_id_first():
    tm = load_map_from_lines(["SCHEMA FOO ; fields=name id"])
    assert tm.tags["FOO"].fields[0] == "name"


def test_schema_emit_roundtrip():
    from memnet.tag_map import emit_schema_line, load_persisted_map_from_lines, tag_map_to_lines

    tm = load_map_from_lines(["SCHEMA MOD ; fields=id path summary status recycle"])
    lines = tag_map_to_lines(tm)
    assert any(line.startswith("SCHEMA MOD ;") for line in lines)
    assert emit_schema_line("MOD", ["id", "path"]) == "SCHEMA MOD ; fields=id path"
    # Snapshots emit fixed LAW/EDG too; persisted load skips them.
    tm2 = load_persisted_map_from_lines(lines)
    assert tm2.tags["MOD"].fields == tm.tags["MOD"].fields


def test_field_count_mismatch():
    tm = load_map_from_lines(["@NPC: id|name|traits|corruption|craft|funding_gap|status|recycle"])
    with pytest.raises(MemNetError) as exc:
        parse_line("@NPC: N01|only|two", tm)
    assert exc.value.code == "FIELD_COUNT"


def test_same_nickname_cross_tag_stay_two(memnet_temp):
    from memnet.session import open_session

    ss = open_session(
        map_lines=[
            "@NPC: id|name|traits|corruption|craft|funding_gap|status|recycle",
            "@BIZ: id|name|type|location|profit|cashflow|employees|recycle",
        ]
    )
    rec = parse_line(
        "@NPC: N01|Alice|t|0|c|0|active|persistent",
        ss.tag_map,
    )
    ss.store.upsert(rec, relations=ss.relations)
    other = parse_line("@BIZ: N01|x|t|l|0|0|0|persistent", ss.tag_map)
    ss.store.upsert(other, relations=ss.relations)
    hits = ss.store.match_nickname("N01")
    assert len(hits) == 2
    assert {r.tag for r in hits} == {"NPC", "BIZ"}
    assert hits[0].hid != hits[1].hid


def test_techdocs_schema_and_workflow_parse():
    """RTO remote-mode example map + seed lines parse without field errors."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    examples = root / "parts" / "common" / "memnet" / "memnet" / "examples"
    schema_path = examples / "schema.techdocs.example.txt"
    workflow_path = examples / "workflow.rto-remote.example.txt"
    tm = load_map_from_lines(schema_path.read_text(encoding="utf-8").splitlines())
    for line in workflow_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parse_line(stripped, tm)


def test_coding_schema_and_workflow_parse(memnet_temp):
    """Coding TagMap + GQL workflow ingest without field errors."""
    from pathlib import Path

    from memnet.mutate_gate import MutateGate
    from memnet.session import open_session

    root = Path(__file__).resolve().parents[1]
    examples = root / "parts" / "common" / "memnet" / "memnet" / "examples"
    schema_path = examples / "schema.coding.example.txt"
    workflow_path = examples / "workflow.coding.example.txt"
    tm = load_map_from_lines(schema_path.read_text(encoding="utf-8").splitlines())
    assert "MOD" in tm.tags and "SYM" in tm.tags
    ss = open_session(map_file=str(schema_path))
    result = MutateGate(ss).apply(
        workflow_path.read_text(encoding="utf-8").splitlines(),
        mode="add",
    )
    assert result.dialect == "gql"
    assert ss.store.get("CFG01") is not None
    assert ss.store.get("MOD_cli") is not None
    assert ss.store.get("E_cfg_root") is not None
