"""MN-REQ-09.2 / MN-VER-09-S02: bare $name refused parameter_unsupported.

Text pins: the SysML model records the refusal (index line, requirement
leaf, verify case, ProductGqlGate), and cites the runtime tests.
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


def test_req_09_2_index_line_names_parameter_unsupported():
    req = _text("requirements.sysml")
    line = next(ln for ln in req.splitlines() if re.match(r"\s*MN-REQ-09\.2\s", ln))
    assert "parameter_unsupported" in line, line.strip()


def test_req_09_2_refuses_bare_parameter_and_cites_tests():
    body = _def("requirements.sysml", "requirement", "MN_REQ_09_2_RejectInvalidWire")
    assert "parameter_unsupported" in body
    assert "SHALL apply nothing" in body
    assert "tests/test_gql_codec.py" in body
    assert "tests/test_typed_walk_where.py::test_parameter_in_where_is_refused" in body
    assert "MN-VER-09-S02" in body


def test_ver_09_s02_cites_runtime_tests():
    body = _def("verify.sysml", "verification", "MN_VER_09_S02_ParameterUnsupported")
    assert "parameter_unsupported" in body
    assert "tests/test_gql_codec.py::test_parameters_are_refused" in body
    assert "tests/test_typed_walk_where.py::test_parameter_in_where_is_refused" in body
    assert "verify rejectInvalidWireReq;" in body


def test_product_gql_gate_rejects_parameter():
    body = _def("deploy.sysml", "part", "ProductGqlGate")
    assert "attribute rejectParameter : Boolean = true;" in body
    assert "parameter_unsupported" in body
