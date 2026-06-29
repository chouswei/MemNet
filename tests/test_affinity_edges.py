"""Tests for aff_to edge parsing and read."""

from __future__ import annotations

from novel_mcp.affinity_edges import (
    format_affinity_attrs,
    parse_affinity_attrs,
    read_directed_affinity,
)


def test_format_and_parse_affinity_attrs():
    attrs = format_affinity_attrs(
        {"親密度": "35", "信任度": "60", "敬重": "50"},
        note="姐弟日久",
    )
    assert attrs == "親密度:35;信任度:60;敬重:50;備註:姐弟日久"
    scores, note = parse_affinity_attrs(attrs)
    assert scores["信任度"] == "60"
    assert note == "姐弟日久"


def test_parse_negative_and_zero():
    scores, note = parse_affinity_attrs("親密度:-40;信任度:-80;敬重:0;備註:世仇")
    assert scores["親密度"] == "-40"
    assert scores["敬重"] == "0"
    assert note == "世仇"


def test_read_directed_affinity_from_edg(monkeypatch):
    monkeypatch.setattr(
        "novel_mcp.affinity_edges.list_tag_data_rows",
        lambda session, tag: {
            "EDG": [
                [
                    "EAFF01",
                    "P01",
                    "aff_to",
                    "N01",
                    "",
                    "親密度:35;信任度:60;敬重:50;備註:姐弟日久",
                    "常駐",
                ]
            ]
        }.get(tag, []),
    )
    row = read_directed_affinity("mn_test", "P01", "N01")
    assert row is not None
    assert row["dims"][0]["value"] == "35"
    assert row["note"] == "姐弟日久"
    assert row["edge_id"] == "EAFF01"


def test_read_directed_affinity_asymmetric_edges(monkeypatch):
    monkeypatch.setattr(
        "novel_mcp.affinity_edges.list_tag_data_rows",
        lambda session, tag: {
            "EDG": [
                ["EAFF10", "P01", "aff_to", "N03", "", "親密度:-40;信任度:-80;敬重:-60;備註:世仇", "常駐"],
                ["EAFF11", "N03", "aff_to", "P01", "", "親密度:15;信任度:25;敬重:0;備註:不識此人", "常駐"],
            ]
        }.get(tag, []),
    )
    a = read_directed_affinity("mn_test", "P01", "N03")
    b = read_directed_affinity("mn_test", "N03", "P01")
    assert a["dims"][0]["value"] == "-40"
    assert b["dims"][0]["value"] == "15"
