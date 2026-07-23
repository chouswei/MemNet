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


def test_user_map_requires_id_first():
    with pytest.raises(MemNetError) as exc:
        load_map_from_lines(["@FOO: name|id"])
    assert exc.value.code == "id_first"


def test_field_count_mismatch():
    tm = load_map_from_lines(["@NPC: id|name|traits|corruption|craft|funding_gap|status|recycle"])
    with pytest.raises(MemNetError) as exc:
        parse_line("@NPC: N01|only|two", tm)
    assert exc.value.code == "FIELD_COUNT"


def test_id_conflict_cross_tag(memnet_temp):
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
    with pytest.raises(MemNetError) as exc:
        bad = parse_line("@BIZ: N01|x|t|l|0|0|0|persistent", ss.tag_map)
        ss.store.upsert(bad, relations=ss.relations)
    assert exc.value.code == "id_conflict"


def test_techdocs_schema_and_workflow_parse():
    """RTO remote-mode example map + seed lines parse without field errors."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    schema_path = root / "parts" / "common" / "memnet" / "memnet" / "examples" / "schema.techdocs.example.txt"
    workflow_path = root / "parts" / "common" / "memnet" / "memnet" / "examples" / "workflow.rto-remote.example.txt"
    tm = load_map_from_lines(schema_path.read_text(encoding="utf-8").splitlines())
    for line in workflow_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parse_line(stripped, tm)


def test_coding_schema_and_workflow_parse():
    """Coding example map + seed lines parse without field errors."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    schema_path = root / "parts" / "common" / "memnet" / "memnet" / "examples" / "schema.coding.example.txt"
    workflow_path = root / "parts" / "common" / "memnet" / "memnet" / "examples" / "workflow.coding.example.txt"
    tm = load_map_from_lines(schema_path.read_text(encoding="utf-8").splitlines())
    for line in workflow_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parse_line(stripped, tm)
