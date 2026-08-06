"""MutateGate + PinMapComposer integration (Tier A path)."""

from __future__ import annotations

from typer.testing import CliRunner

from memnet.cli import app
from memnet.mutate_gate import MutateGate, classify_batch
from memnet.pin_map_composer import PinMapComposer
from memnet.session import get_session, open_session

runner = CliRunner()


def test_classify_rejects_mixed():
    import pytest
    from memnet.exceptions import MemNetError

    with pytest.raises(MemNetError, match="mix"):
        classify_batch(["@PLR: A|x", "+ PLR [NEW] ; identity=y"])


def test_tier_a_add_mints_new(memnet_temp, schema_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")
    batch = "+ PLR [NEW] ; identity=Hero ; wealth=1 ; cashflow=0 ; monopoly=0 ; reputation=0 ; inventory=bag\n"
    add = runner.invoke(app, ["add", "--stdin", "--session", sid], input=batch)
    assert add.exit_code == 0, add.stderr
    assert "+ PLR [" in add.stdout
    assert "[NEW]" not in add.stdout
    assert "@ID:" in add.stderr
    warm = runner.invoke(app, ["query", "warm", "--anchor", "PLR1", "--session", sid])
    # minted id may be PLR1
    sid2 = sid
    ss = get_session(sid2)
    plrs = [r for r in ss.store.list_records("PLR") if r.fields.get("identity") == "Hero"]
    assert len(plrs) == 1
    warm = runner.invoke(
        app, ["query", "warm", "--anchor", plrs[0].id, "--session", sid]
    )
    assert warm.exit_code == 0
    assert plrs[0].id in warm.stdout
    assert f"PLR [{plrs[0].id}]" in warm.stdout
    assert f"+ PLR [{plrs[0].id}]" not in warm.stdout
    assert "@PLR:" not in warm.stdout


def test_pin_map_composer_unit(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    gate = MutateGate(ss)
    gate.apply(
        ["@PLR: PLR01|Hero|1|0|0|0|bag"],
        mode="add",
    )
    text = PinMapComposer(ss).compose(anchor="PLR01", depth=1)[1]
    assert "## Nodes" in text
    assert "PLR [PLR01]" in text
    assert "+ PLR [PLR01]" not in text


def test_rename_free_retargets_edges(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    gate = MutateGate(ss)
    gate.apply(
        [
            "+ PLR [PLR_BAD] ; identity=Hero ; wealth=1 ; cashflow=0 ; monopoly=0 ; reputation=0 ; inventory=bag",
            "+ NPC [N01] ; name=Guide ; traits=kind ; corruption=0 ; craft=none ; funding_gap=0 ; status=active ; recycle=persistent",
            "+ NEW [N01] --(seeks_help)--> [PLR_BAD] ; recycle=persistent",
        ],
        mode="add",
        allow_new_relation=False,
    )
    result = gate.apply(["~ [PLR_BAD] ; id=PLR01"], mode="update")
    assert ss.store.get("PLR_BAD") is None
    assert ss.store.get("PLR01") is not None
    assert ss.store.get("PLR01").fields["identity"] == "Hero"
    edges = [r for r in ss.store.list_records("EDG") if r.fields.get("dist") == "PLR01"]
    assert len(edges) == 1
    assert edges[0].fields.get("src") == "N01"
    assert "PLR01" in result.ack_lines[0]


def test_rename_occupied_rejects(memnet_temp, schema_file):
    import pytest
    from memnet.exceptions import MemNetError

    ss = open_session(map_file=str(schema_file))
    gate = MutateGate(ss)
    gate.apply(
        [
            "+ PLR [PLR_BAD] ; identity=Wrong ; wealth=1 ; cashflow=0 ; monopoly=0 ; reputation=0 ; inventory=bag",
            "+ PLR [PLR01] ; identity=Hero ; wealth=2 ; cashflow=0 ; monopoly=0 ; reputation=0 ; inventory=bag",
        ],
        mode="add",
    )
    with pytest.raises(MemNetError) as ei:
        gate.apply(["~ [PLR_BAD] ; id=PLR01"], mode="update")
    assert ei.value.code == "id_occupied"
    assert ss.store.get("PLR_BAD") is not None
    assert ss.store.get("PLR01").fields["identity"] == "Hero"


def test_rename_occupied_merge_retargets(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    gate = MutateGate(ss)
    gate.apply(
        [
            "+ PLR [PLR_BAD] ; identity=Wrong ; wealth=1 ; cashflow=0 ; monopoly=0 ; reputation=0 ; inventory=bag",
            "+ PLR [PLR01] ; identity=Hero ; wealth=2 ; cashflow=0 ; monopoly=0 ; reputation=0 ; inventory=bag",
            "+ NPC [N01] ; name=Guide ; traits=kind ; corruption=0 ; craft=none ; funding_gap=0 ; status=active ; recycle=persistent",
            "+ NEW [N01] --(seeks_help)--> [PLR_BAD] ; recycle=persistent",
        ],
        mode="add",
    )
    result = gate.apply(["~ [PLR_BAD] ; id=PLR01 ; merge=true"], mode="update")
    assert ss.store.get("PLR_BAD") is None
    assert ss.store.get("PLR01").fields["identity"] == "Hero"
    edges = [r for r in ss.store.list_records("EDG") if r.fields.get("dist") == "PLR01"]
    assert len(edges) == 1
    assert any("merged|PLR_BAD->PLR01" == w for w in result.warnings)


def test_rename_self_noop(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    gate = MutateGate(ss)
    gate.apply(
        [
            "+ PLR [PLR01] ; identity=Hero ; wealth=1 ; cashflow=0 ; monopoly=0 ; reputation=0 ; inventory=bag",
        ],
        mode="add",
    )
    gate.apply(["~ [PLR01] ; id=PLR01 ; wealth=9"], mode="update")
    assert ss.store.get("PLR01").fields["wealth"] == "9"


def test_numeric_increment_on_update(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    gate = MutateGate(ss)
    gate.apply(
        [
            "+ PLR [PLR01] ; identity=Hero ; wealth=1 ; cashflow=100 ; monopoly=0 ; reputation=0 ; inventory=bag",
        ],
        mode="add",
    )
    gate.apply(["~ [PLR01] ; wealth+=2 ; cashflow-=25"], mode="update")
    row = ss.store.get("PLR01")
    assert row.fields["wealth"] == "3"
    assert row.fields["cashflow"] == "75"


def test_numeric_op_non_numeric_field_rejects(memnet_temp, schema_file):
    import pytest
    from memnet.exceptions import MemNetError

    ss = open_session(map_file=str(schema_file))
    gate = MutateGate(ss)
    gate.apply(
        [
            "+ TSK [T01] ; goal=Test ; deadline=1 ; status=in_progress ; recycle=persistent",
        ],
        mode="add",
    )
    with pytest.raises(MemNetError) as ei:
        gate.apply(["~ [T01] ; status+=1"], mode="update")
    assert ei.value.code == "bad_numeric"


def test_numeric_op_on_create_rejects(memnet_temp, schema_file):
    import pytest
    from memnet.exceptions import MemNetError

    ss = open_session(map_file=str(schema_file))
    gate = MutateGate(ss)
    with pytest.raises(MemNetError) as ei:
        gate.apply(
            [
                "+ PLR [NEW] ; identity=Hero ; wealth+=1 ; cashflow=0 ; monopoly=0 ; reputation=0 ; inventory=bag",
            ],
            mode="add",
        )
    assert ei.value.code == "invalid_field"


def test_pin_map_shows_absolute_after_numeric_op(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    gate = MutateGate(ss)
    gate.apply(
        [
            "+ PLR [PLR01] ; identity=Hero ; wealth=1 ; cashflow=0 ; monopoly=0 ; reputation=0 ; inventory=bag",
        ],
        mode="add",
    )
    gate.apply(["~ [PLR01] ; wealth+=4"], mode="update")
    text = PinMapComposer(ss).compose(anchor="PLR01", depth=1)[1]
    assert "wealth=5" in text
    assert "+=" not in text