"""MN-REQ-14.1 / 14.4 model pins for symphony range-where-id-index (node P-range).

Red-first text tests: the SysML model must mark range WHERE (14.1) and the id
index with linear load (14.4) implemented, cite their runtime tests, drop the
deploy.sysml reserved-keyword names (actor, interface), and cite the B3 tests
in the MN-VER-14-D02 case.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"


def _text(name: str) -> str:
    return (MODELS / name).read_text(encoding="utf-8")


def _block(text: str, start: int) -> str:
    """Return the text from start through the brace that closes the first '{'."""
    open_at = text.index("{", start)
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise AssertionError(f"unbalanced braces after offset {start}")


def _def(file: str, kind: str, name: str) -> str:
    text = _text(file)
    m = re.search(rf"\b{kind} def {name}\b", text)
    assert m, f"{kind} def {name} missing in {file}"
    return _block(text, m.start())


def _req(name: str) -> str:
    return _def("requirements.sysml", "requirement", name)


def _ver(name: str) -> str:
    return _def("verify.sysml", "verification", name)


# ----- deploy.sysml: no reserved keywords as names -----


def test_deploy_has_no_attribute_named_actor():
    bad = re.findall(r"(?m)^\s*attribute actor\b.*$", _text("deploy.sysml"))
    assert not bad, f"deploy.sysml still names an attribute 'actor': {bad[:3]}"


def test_deploy_has_no_part_named_interface():
    bad = re.findall(r"(?m)^\s*part interface\b.*$", _text("deploy.sysml"))
    assert not bad, f"deploy.sysml still names a part 'interface': {bad}"


def test_deploy_quotes_interface_part_name():
    assert "part 'interface' : PinMapIngestBase;" in _text("deploy.sysml")


# ----- verify.sysml: MN-VER-14-D02 cites the B3 tests -----


@pytest.mark.parametrize(
    "test_ref",
    [
        "::test_b3_set_with_only_end_node_id_is_refused",
        "::test_b3_refusal_names_relationship_id_pattern",
    ],
)
def test_ver_14_d02_cites_b3_tests(test_ref):
    assert test_ref in _ver("MN_VER_14_D02_WhereRelationSetRefusedAsDelete")


# ----- requirements.sysml: 14.1 and 14.4 implemented -----


@pytest.mark.parametrize(
    "name", ["MN_REQ_14_1_WhereRangeComparison", "MN_REQ_14_4_IdIndexAndLinearLoad"]
)
def test_req_no_longer_proposal(name):
    assert "Status: PROPOSAL" not in _req(name), name


def test_req_14_1_cites_test_and_no_match_rule():
    body = _req("MN_REQ_14_1_WhereRangeComparison")
    assert "tests/test_range_where.py" in body
    assert "does not match" in body


def test_req_14_4_cites_id_index_test():
    assert "tests/test_id_index.py" in _req("MN_REQ_14_4_IdIndexAndLinearLoad")


# ----- verify.sysml: S01 / S04 runnable -----


def test_ver_14_s01_cites_range_where_test():
    body = _ver("MN_VER_14_S01_WhereRangeComparison")
    assert "tests/test_range_where.py" in body
    assert "PROPOSAL: no runtime test yet" not in body


def test_ver_14_s04_cites_id_index_tests():
    body = _ver("MN_VER_14_S04_IdIndexAndLinearLoad")
    assert "tests/test_id_index.py" in body
    assert "tests/test_id_index_perf.py" in body
    assert "PROPOSAL: no runtime test yet" not in body


# ----- behaviour / implementation -----


@pytest.mark.parametrize("name", ["RangeWhereCompare", "SessionLoadLinear"])
def test_behaviour_action_doc_says_implemented(name):
    assert "Implemented" in _def("behaviour.sysml", "action", name), name


def test_id_index_part_is_implemented():
    body = _def("implementation.sysml", "part", "IdIndex")
    assert "attribute implemented : Boolean = true;" in body
