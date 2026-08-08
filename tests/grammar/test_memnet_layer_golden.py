"""Golden harness for MemNetLayer (proposed 1.x) fixtures + soft-validate."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "docs" / "grammar" / "tools"
EXAMPLES = ROOT / "docs" / "grammar" / "examples"
LAYER_EXAMPLES = EXAMPLES / "layer"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

pytest.importorskip("antlr4")

from layer_soft_validate import (  # noqa: E402
    ParseError,
    expect_from_text,
    iter_layer_fixtures,
    lint,
    parse,
    soft_validate,
)


def _fixtures() -> list[Path]:
    return list(iter_layer_fixtures(EXAMPLES))


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
def test_layer_fixture(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    expect = _resolve_expect(path, text)

    if expect == "parse-reject":
        with pytest.raises(ParseError):
            parse(text)
        return

    if expect == "lint-reject":
        doc = parse(text)
        errors = [i for i in soft_validate(doc) if i.severity == "error"]
        assert errors, f"{path.name}: expected soft-validate errors, got none"
        return

    if expect == "auto-bad":
        try:
            doc = parse(text)
        except ParseError:
            return
        errors = [i for i in soft_validate(doc) if i.severity == "error"]
        assert errors, f"{path.name}: bad fixture parsed but no soft-validate errors"
        return

    assert expect == "parse-ok"
    doc = parse(text)
    errors = [i for i in lint(doc) if i.severity == "error"]
    assert not errors, f"{path.name}: unexpected lint errors {[e.message for e in errors]}"


def test_orphan_law_alias_soft_reject() -> None:
    text = (
        "CST [CST_X] ; ports=a: {direc=in, V=@va} ; law=$@va=@missing$\n"
    )
    doc = parse(text)
    codes = {i.code for i in soft_validate(doc) if i.severity == "error"}
    assert "orphan_law_alias" in codes


def test_fixtures_directory_populated() -> None:
    names = {p.name for p in _fixtures()}
    required = {
        "layer_01_bind_good.txt",
        "layer_02_relation_good.txt",
        "layer_03_ports_law_alias_good.txt",
        "layer_04_named_fn_A_good.txt",
        "layer_05_bad_mixed_endpoints.txt",
        "layer_06_bad_law_on_edge.txt",
        "layer_07_bad_bag_on_law.txt",
        "layer_08_bad_brace_depth3.txt",
        "layer_09_inv_amp_good.txt",
    }
    assert required <= names, f"missing fixtures: {required - names}"
    assert LAYER_EXAMPLES.is_dir()
