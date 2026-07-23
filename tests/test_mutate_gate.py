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
