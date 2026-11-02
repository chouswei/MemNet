"""MN-REQ-14 (Atelier board, PR #237) structure: parts, behaviour and states traced.

Red-first tests for node B-perf of symphony cap135k-model: the model must carry
part defs, actions and state machines for the MN-REQ-14 leaves, wired to the
existing 14.x requirements and verify cases, with the fixed line-cap interface
(MEMNET_MAX_LINE_BYTES default 4 x 32768 + 4096 = 135168, mutate-time
escaped-size line_bytes refusal). 14.2 and 14.3 stay PARKED.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"

LINE_CAP = re.compile(r"135,?168")
OLD_LINE_CAP = re.compile(r"69,?632")
DEV_CREDENTIAL = r"Developer\w*Credential|Credential\w*Developer"


def _all_model_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(MODELS.glob("*.sysml")))


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


def _defs(kind: str, name_pattern: str) -> dict[str, str]:
    """All `<kind> def <Name>` blocks whose name matches name_pattern (case-insensitive)."""
    text = _all_model_text()
    found: dict[str, str] = {}
    for m in re.finditer(rf"\b{kind} def (\w+)", text):
        if re.search(name_pattern, m.group(1), re.IGNORECASE):
            found[m.group(1)] = _block(text, m.start())
    return found


def _one_def(kind: str, name_pattern: str) -> tuple[str, str]:
    found = _defs(kind, name_pattern)
    assert found, f"no `{kind} def` matching /{name_pattern}/ in sysml-models/models"
    return next(iter(found.items()))


def _satisfies(part_name: str, body: str, req_tokens: tuple[str, ...]) -> bool:
    """True when the part def (or a `satisfy ... by` line naming it) satisfies one of req_tokens."""
    for line in body.splitlines():
        if re.search(r"\bsatisfy\b", line) and any(t in line for t in req_tokens):
            return True
    text = _all_model_text()
    for m in re.finditer(r"\bsatisfy\b[^;]*;", text):
        stmt = m.group(0)
        if " by " in stmt and part_name_ref(part_name, stmt) and any(t in stmt for t in req_tokens):
            return True
    return False


def part_name_ref(part_name: str, stmt: str) -> bool:
    lower = part_name[0].lower() + part_name[1:]
    return part_name in stmt or lower in stmt


def _requirement_doc(def_name: str) -> str:
    text = REQUIREMENTS.read_text(encoding="utf-8")
    m = re.search(rf"requirement def {def_name}\b", text)
    assert m, f"requirement def {def_name} missing"
    return _block(text, m.start())


def _verify_case(def_name: str) -> str:
    text = VERIFY.read_text(encoding="utf-8")
    m = re.search(rf"verification def {def_name}\b", text)
    assert m, f"verification def {def_name} missing"
    return _block(text, m.start())


def _performed(action_name: str) -> bool:
    text = _all_model_text()
    return re.search(rf"\bperform\b[^;{{]*\b{action_name}\b", text) is not None


def _exhibited(state_name: str) -> bool:
    text = _all_model_text()
    return re.search(rf"\bexhibit\b[^;{{]*\b{state_name}\b", text) is not None


# Requirement tokens: usage name or the def name of the leaf.
REQ_14_1 = ("whereRangeComparisonReq", "MN_REQ_14_1_WhereRangeComparison")
REQ_14_4 = ("idIndexAndLinearLoadReq", "MN_REQ_14_4_IdIndexAndLinearLoad")
REQ_14_6 = ("idDesignReq", "MN_REQ_14_6_IdDesign")
REQ_14_7 = ("agentHandlesNotIdsReq", "MN_REQ_14_7_AgentHandlesNotIds")
REQ_14_8 = ("developerSurfaceRealIdsReq", "MN_REQ_14_8_DeveloperSurfaceRealIds")
REQ_14_9 = ("valueCap32kReq", "MN_REQ_14_9_ValueCap32k")
REQ_14_10 = ("sessionTotalBytesCapReq", "MN_REQ_14_10_SessionTotalBytesCap")


# ----- part defs -----


def test_id_index_part_satisfies_14_4_and_14_6():
    name, body = _one_def("part", r"IdIndex")
    assert _satisfies(name, body, REQ_14_4), f"{name} does not satisfy MN-REQ-14.4"
    assert _satisfies(name, body, REQ_14_6), f"{name} does not satisfy MN-REQ-14.6"


def test_tombstone_store_part_satisfies_14_6():
    name, body = _one_def("part", r"Tombstone")
    assert _satisfies(name, body, REQ_14_6), f"{name} does not satisfy MN-REQ-14.6"


def test_handle_table_part_satisfies_14_7():
    name, body = _one_def("part", r"HandleTable")
    assert _satisfies(name, body, REQ_14_7), f"{name} does not satisfy MN-REQ-14.7"


def test_developer_credential_is_a_port_def():
    _one_def("port", DEV_CREDENTIAL)


def test_developer_listener_has_credential_port_and_satisfies_14_8():
    name, body = _one_def("part", r"DeveloperListener")
    port_defs = _defs("port", DEV_CREDENTIAL)
    assert port_defs, "no credential port def"
    assert any(re.search(rf"\bport\s+\w+\s*:\s*~?{pd}\b", body) for pd in port_defs), (
        f"{name} has no port typed by a credential port def"
    )
    assert _satisfies(name, body, REQ_14_8), f"{name} does not satisfy MN-REQ-14.8"


def test_session_byte_budget_part_satisfies_14_10():
    name, body = _one_def("part", r"Byte(s)?Budget")
    assert _satisfies(name, body, REQ_14_10), f"{name} does not satisfy MN-REQ-14.10"


# ----- behaviour -----


def test_range_where_action_refuses_type_mismatch_and_is_traced():
    name, body = _one_def("action", r"Range")
    assert "type_mismatch" in body
    assert _performed(name), f"action {name} is never performed"
    assert name in _verify_case("MN_VER_14_S01_WhereRangeComparison") or name in _requirement_doc(
        "MN_REQ_14_1_WhereRangeComparison"
    )


def test_cap_enforcement_action_on_write_and_load_with_line_cap():
    found = {
        n: b for n, b in _defs("action", r"Cap").items() if LINE_CAP.search(b) and "line_bytes" in b
    }
    assert found, "no cap-enforcement action naming 135168 and line_bytes"
    name, body = next(iter(found.items()))
    low = body.lower()
    assert "escaped" in low, "line_bytes refusal must be on the escaped wire size"
    assert "mutate" in low or "write" in low
    assert "load" in low
    assert "limit_exceeded" in body
    assert "value_bytes" in body
    assert not OLD_LINE_CAP.search(body)
    assert _performed(name), f"action {name} is never performed"
    assert name in _verify_case("MN_VER_14_S09_ValueCap32k")


def test_d02_where_set_fix_action_is_traced():
    found = {n: b for n, b in _defs("action", r"\w").items() if "D02" in b and "SET" in b}
    assert found, "no action def for the D02 WHERE+SET refusal fix"
    name, _ = next(iter(found.items()))
    assert _performed(name), f"action {name} is never performed"
    assert name in _verify_case("MN_VER_14_D02_WhereRelationSetRefusedAsDelete")


# ----- state machines -----


def test_id_lifecycle_state_machine():
    name, body = _one_def("state", r"IdLifecycle")
    low = body.lower()
    assert re.search(r"\bstate\s+live\b", low)
    assert re.search(r"\bstate\s+(deleted|tombstone\w*)\b", low)
    assert re.search(r"\bstate\s+retired\b", low)
    assert "never reused" in low
    assert _exhibited(name), f"state {name} is never exhibited"
    assert name in _verify_case("MN_VER_14_S06_IdDesign")


def test_session_byte_budget_state_machine():
    name, _ = _one_def("state", r"Byte(s)?Budget")
    assert _exhibited(name), f"state {name} is never exhibited"
    assert name in _verify_case("MN_VER_14_S10_SessionTotalBytesCap")


# ----- 14.9 line cap and parked leaves -----


def test_14_9_line_cap_is_135168_not_69632():
    doc = _requirement_doc("MN_REQ_14_9_ValueCap32k")
    assert LINE_CAP.search(doc), "14.9 must state line cap 135168"
    assert re.search(r"4\s*x\s*32,?768\s*\+\s*4,?096", doc), "14.9 must show 4 x 32768 + 4096"
    assert not OLD_LINE_CAP.search(doc), "14.9 still says 69632"
    s09 = _verify_case("MN_VER_14_S09_ValueCap32k")
    assert LINE_CAP.search(s09)
    assert not OLD_LINE_CAP.search(s09)
    req = REQUIREMENTS.read_text(encoding="utf-8")
    index_line = next(line for line in req.splitlines() if "MN-REQ-14.9 " in line)
    assert not OLD_LINE_CAP.search(index_line)


def test_14_2_and_14_3_stay_parked():
    assert "PARKED" in _requirement_doc("MN_REQ_14_2_PagedReadsPastCap")
    assert "PARKED" in _requirement_doc("MN_REQ_14_3_TypedDirectedWalks")
