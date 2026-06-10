"""read list --where field filters."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from memnet.cli import app
from memnet.exceptions import MemNetError
from memnet.filter import field_matches, parse_where, record_matches
from memnet.mem_store import MemStore
from memnet.models import Record
from memnet.tag_map import load_map_from_lines, parse_line

runner = CliRunner()


def test_parse_where_exact():
    assert parse_where("status=active") == ("status", "active")
    assert parse_where("name=*Tiexin*") == ("name", "*Tiexin*")


def test_parse_where_errors():
    with pytest.raises(MemNetError) as exc:
        parse_where("")
    assert exc.value.code == "bad_where"
    with pytest.raises(MemNetError) as exc:
        parse_where("status")
    assert exc.value.code == "bad_where"


def test_field_matches():
    assert field_matches("active", "active")
    assert not field_matches("active", "settled")
    assert field_matches("Shen Tiexin", "*Tiexin*")
    assert field_matches("TEC01", "TEC*")


def test_record_matches_and():
    rec = Record(tag="NPC", fields={"id": "N01", "name": "Bob", "status": "active"})
    assert record_matches(rec, [("status", "active")])
    assert record_matches(rec, [("status", "active"), ("name", "Bob")])
    assert not record_matches(rec, [("status", "active"), ("name", "Alice")])


def test_list_records_where():
    tm = load_map_from_lines(
        [
            "@NPC: id|name|traits|corruption|craft|funding_gap|status|recycle",
            "@TSK: id|goal|deadline|status|recycle",
        ]
    )
    store = MemStore(tm)
    store.upsert(
        parse_line("@NPC: N01|Shen Tiexin|t|0|c|0|active|persistent", tm),
        relations=set(),
    )
    store.upsert(
        parse_line("@NPC: N02|Other|t|0|c|0|gone|delete_on_settle", tm),
        relations=set(),
    )
    store.upsert(
        parse_line("@TSK: T01|Work|1|urgent|persistent", tm),
        relations=set(),
    )

    by_status = store.list_records("NPC", where=[("status", "active")])
    assert [r.id for r in by_status] == ["N01"]

    by_glob = store.list_records("NPC", where=[("name", "*Tiexin*")])
    assert [r.id for r in by_glob] == ["N01"]

    combined = store.list_records(
        "NPC",
        active_only=True,
        where=[("status", "active"), ("name", "*Tiexin*")],
    )
    assert [r.id for r in combined] == ["N01"]

    none = store.list_records("TSK", where=[("status", "urgent"), ("goal", "Other")])
    assert none == []


def test_read_list_where_cli(memnet_temp, schema_file, workflow_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    runner.invoke(app, ["add", "--file", str(workflow_file), "--session", sid])

    exact = runner.invoke(
        app,
        ["read", "list", "--tag", "NPC", "--where", "status=active", "--session", sid],
    )
    assert exact.exit_code == 0
    assert "@NPC: N01|" in exact.stdout
    assert "N02" not in exact.stdout

    glob = runner.invoke(
        app,
        ["read", "list", "--tag", "NPC", "--where", "name=*Tiexin*", "--session", sid],
    )
    assert glob.exit_code == 0
    assert "N01" in glob.stdout

    bad = runner.invoke(app, ["read", "list", "--where", "status", "--session", sid])
    assert bad.exit_code == 1
    assert "@ERR: bad_where" in bad.stderr
