"""MN-REQ-14.3 model pins for symphony typed-walks (node P-model).

Red-first text tests: the SysML model must record typed directed walks
(MN-REQ-14.3, owner issue #247 items 1-3) as implemented, with a TypedWalk
behaviour, a TypedWalk implementation part that satisfies 14.3 and an S03
verify case naming the runtime tests. Also pins the folded-in LATER fixes:
L-250b-1 (non-finite is a source of UNKNOWN), L-250b-2 (gql.py:384 -> :388)
and L-247-1 (rowRev compares with a number literal, not by string order).
"""

from __future__ import annotations

import re
from pathlib import Path

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


def _flat(text: str) -> str:
    return " ".join(text.split())


def _req(name: str) -> str:
    return _def("requirements.sysml", "requirement", name)


def _ver(name: str) -> str:
    return _def("verify.sysml", "verification", name)


def _req_14_3() -> str:
    return _flat(_req("MN_REQ_14_3_TypedDirectedWalks"))


def _req_14_1() -> str:
    return _flat(_req("MN_REQ_14_1_WhereRangeComparison"))


def _range_where_compare() -> str:
    return _flat(_def("behaviour.sysml", "action", "RangeWhereCompare"))


def _sentences(text: str) -> list[str]:
    return re.split(r"\.\s+", text)


# ----- requirements.sysml: MN-REQ-14.3 rewritten as implemented -----


def test_14_3_status_implemented_not_parked():
    doc = _req_14_3()
    assert "Status: implemented" in doc, "14.3 must say Status: implemented"
    assert "PARKED" not in doc, "14.3 still says PARKED"
    assert 'requirementId : String = "MN-REQ-14.3"' in doc


def test_14_3_names_verb_fold_directions_and_bounds():
    doc = _req_14_3()
    assert "query typed-walk" in doc, "14.3 must name the query typed-walk verb"
    assert "partOf" in doc
    assert re.search(r"PART_OF\s*(->|→|to|folds to)\s*partOf", doc), (
        "14.3 must state the fold rule PART_OF -> partOf"
    )
    assert re.search(r"\bout\b.{0,12}\bin\b.{0,12}\bboth\b", doc), "14.3 must name out/in/both"
    assert re.search(r"\b10\b", doc) and "hops" in doc, "14.3 must state max hops 10"
    assert re.search(r"\b500\b", doc), "14.3 must state limit ceiling 500"
    assert re.search(r"\b20,?000\b", doc), "14.3 must state the 20,000 edge-read budget"
    assert re.search(r"\b1,?048,?576\b", doc), "14.3 must state the 1,048,576 reply-byte cap"


def test_14_3_names_refusal_codes_truncation_and_cursor():
    doc = _req_14_3()
    for code in (
        "hops_out_of_range",
        "invalid_direction",
        "limit_out_of_range",
        "walk_cursor",
    ):
        assert code in doc, f"14.3 must name {code}"
    assert "truncated" in doc, "14.3 must name the truncated / walk_truncated flag"


def test_14_3_order_is_first_insert_not_id():
    doc = _req_14_3()
    assert "first-insert" in doc, "14.3 must state the first-insert edge order"
    assert re.search(
        r"\bno id (value|order)|\bnot (by )?(the )?id\b|\bnever (by )?(the )?id\b|"
        r"id order is not used|not id order",
        doc,
        re.I,
    ), "14.3 must say id order is not used"


def test_14_3_names_index_surface_and_gate():
    doc = _req_14_3()
    assert "RecordTable" in doc, "14.3 must place the adjacency index in RecordTable"
    assert "MCP" in doc and "14.7" in doc, "14.3 must say no MCP until 14.7"
    assert "product_gate" in doc or "gql_parse_front.py:34" in doc, (
        "14.3 must say agent MATCH ... RETURN stays product-gated"
    )


def test_14_3_names_runtime_tests():
    doc = _req_14_3()
    for path in ("tests/test_typed_walk.py", "tests/test_walk_index.py"):
        assert path in doc, f"14.3 must cite {path}"


def test_14_3_index_line_not_parked():
    req = _text("requirements.sysml")
    line = next(ln for ln in req.splitlines() if re.match(r"\s*MN-REQ-14\.3\s", ln))
    assert "PARKED" not in line, f"14.3 index line still PARKED: {line.strip()}"


def test_14_group_doc_does_not_list_14_3_parked():
    group = _req("MN_REQ_14_AtelierBoardAsks")
    head = _flat(group[: group.index("requirement def MN_REQ_14_1_")])
    parked = [s for s in _sentences(head) if "PARKED" in s]
    assert not any("14.3" in s for s in parked), f"14 group doc lists 14.3 PARKED: {parked}"


# ----- behaviour / implementation / verify -----


def test_behaviour_typed_walk_cites_14_3():
    body = _def("behaviour.sysml", "action", "TypedWalk")
    assert "MN-REQ-14.3" in body


def test_implementation_typed_walk_part_satisfies_14_3():
    body = _def("implementation.sysml", "part", "TypedWalk")
    assert re.search(r"attribute implemented : Boolean = true;", body)
    assert re.search(r"satisfy\s+[\w:]*MN_REQ_14_3_TypedDirectedWalks\b", body)


def test_atelier_board_plan_parks_only_14_2():
    body = _def("implementation.sysml", "part", "AtelierBoardAskPlan")
    m = re.search(r'attribute parkedItems : String = "([^"]*)";', body)
    assert m, "AtelierBoardAskPlan.parkedItems missing"
    assert m.group(1) == "MN-REQ-14.2", f"parkedItems is {m.group(1)!r}"


def test_verify_s03_names_runtime_tests():
    body = _flat(_ver("MN_VER_14_S03_TypedDirectedWalks"))
    for path in (
        "tests/test_typed_walk.py",
        "tests/test_typed_walk_where.py",
        "tests/test_walk_index.py",
        "tests/test_typed_walk_perf.py",
    ):
        assert path in body, f"MN-VER-14-S03 must cite {path}"
    assert "no runtime test" not in body


# ----- folded-in LATER fixes -----


def test_l_250b_1_non_finite_is_unknown_source():
    doc = _req_14_1()
    m = re.search(r"\(6\)(.*?)\(7\)", doc)
    assert m, "14.1 rule (6) missing"
    assert "non-finite" in m.group(1), "14.1 rule (6) must name non-finite as UNKNOWN"
    rwc = _range_where_compare()
    assert any("non-finite" in s and "UNKNOWN" in s for s in _sentences(rwc)), (
        "RangeWhereCompare must name non-finite as a source of UNKNOWN"
    )


def test_l_250b_2_gql_line_ref_moved_to_388():
    hits = [p.name for p in sorted(MODELS.glob("*.sysml")) if "gql.py:384" in _text(p.name)]
    assert not hits, f"gql.py:384 still cited in {hits}"
    assert any("gql.py:388" in _text(p.name) for p in MODELS.glob("*.sysml"))


def test_l_247_1_rowrev_compares_as_number():
    doc = _req_14_1()
    rwc = _range_where_compare()
    for where, body in (("14.1", doc), ("RangeWhereCompare", rwc)):
        assert not re.search(r"string order equals rev order", body), where
        assert not re.search(r"bounded at 999,?999", body), where
    assert re.search(r"rowRev\s*>\s*\d+", doc), "14.1 must show rowRev compared with a number"
    assert "number literal" in doc
