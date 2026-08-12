"""Golden harness for Tier A MemNet grammar fixtures."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from memnet.tier_a import (
    ParseError,
    emit,
    expect_from_text,
    lint,
    parse,
    round_trip_ok,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "docs" / "grammar" / "examples"

SKIP_NAMES = {"10_compile_down_sketch.txt"}


def _fixtures() -> list[Path]:
    return sorted(p for p in EXAMPLES.glob("*.txt") if p.name not in SKIP_NAMES)


def _resolve_expect(path: Path, text: str) -> str:
    marked = expect_from_text(text)
    if marked:
        return marked
    if path.name.endswith("_good.txt"):
        return "parse-ok"
    if "_bad_" in path.name or path.name.endswith("_bad.txt"):
        return "auto-bad"
    return "parse-ok"


@pytest.mark.parametrize("path", _fixtures(), ids=lambda p: p.name)
def test_example_fixture(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    expect = _resolve_expect(path, text)

    if expect == "parse-reject":
        with pytest.raises(ParseError):
            parse(text)
        return

    if expect == "lint-reject":
        doc = parse(text)
        errors = [i for i in lint(doc) if i.severity == "error"]
        assert errors, f"{path.name}: expected lint errors, got none"
        return

    if expect == "auto-bad":
        try:
            doc = parse(text)
        except ParseError:
            return
        errors = [i for i in lint(doc) if i.severity == "error"]
        assert errors, f"{path.name}: bad fixture parsed but no lint errors"
        return

    # parse-ok
    assert expect == "parse-ok"
    doc = parse(text)
    errors = [i for i in lint(doc) if i.severity == "error"]
    assert not errors, f"{path.name}: unexpected lint errors {[e.message for e in errors]}"


@pytest.mark.parametrize(
    "name",
    [
        "01_warm_slice_good.txt",
        "04_pin_map_sysml_code_good.txt",
        "22_inverting_amp_nodal_good.txt",
        "23_formula_derives_good.txt",
    ],
)
def test_round_trip_emit(name: str) -> None:
    text = (EXAMPLES / name).read_text(encoding="utf-8")
    assert round_trip_ok(text)
    doc = parse(text)
    emitted = emit(doc)
    assert "## Nodes" in emitted or "## Pins" in emitted or "## Edges" in emitted
    assert re.search(r"\bE[A-Za-z0-9_]+\b", emitted), f"{name}: expected an edge id in emit"


def test_law_first_field_no_leading_semi() -> None:
    doc = parse("LAW01 kind=engine ; text=one_row_per_id_tag ; recycle=persistent\n")
    node = doc.items[0]
    assert node.id == "LAW01"
    assert [f.key for f in node.fields] == ["kind", "text", "recycle"]


def test_new_create_and_reject_on_patch() -> None:
    doc = parse("+ CLM [NEW] ; type=fact ; code=x ; recycle=persistent\n")
    assert doc.items[0].id == "NEW"
    with pytest.raises(ParseError):
        parse("~ [NEW] ; status=settled ; recycle=delete_on_settle\n")


def test_edge_id_warm_form() -> None:
    doc = parse("+ E77 [N03] --(helps)--> [T42] ; note=labour ; recycle=persistent\n")
    edge = doc.items[0]
    assert edge.edge_id == "E77"
    assert edge.frm == "N03"
    assert edge.to == "T42"


def test_numeric_ops_parse_and_emit() -> None:
    doc = parse("~ [T42] ; phase+=1 ; risk-=0.5 ; recycle=persistent\n")
    node = doc.items[0]
    assert [(f.key, f.op, f.value) for f in node.fields] == [
        ("phase", "+=", "1"),
        ("risk", "-=", "0.5"),
        ("recycle", "=", "persistent"),
    ]
    emitted = emit(doc)
    assert "phase+=1" in emitted
    assert "risk-=0.5" in emitted


def test_pin_map_bare_present() -> None:
    from memnet.tier_a import Op

    doc = parse(
        "CLM [C12] ; type=decision ; recycle=persistent\n"
        "E77 [N03] --(helps)--> [T42] ; note=labour ; recycle=persistent\n"
    )
    assert doc.items[0].op == Op.PRESENT
    assert doc.items[1].op == Op.PRESENT
    emitted = emit(doc)
    assert emitted.startswith("CLM [C12]")
    assert "+ CLM" not in emitted
    assert "E77 [N03]" in emitted
    assert "+ E77" not in emitted
