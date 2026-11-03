"""MN-REQ-14 (Atelier board, PR #237) structure: parts, behaviour and states traced.

Red-first tests for node B-perf of symphony cap135k-model: the model must carry
part defs, actions and state machines for the MN-REQ-14 leaves, wired to the
existing 14.x requirements and verify cases, with the fixed line-cap interface
(MEMNET_MAX_LINE_BYTES default 4 x 32768 + 4096 = 135168, mutate-time
escaped-size line_bytes refusal). 14.2 and 14.3 stay PARKED.

Red-first tests for node D-probe of symphony linecap-n1n6 (Elon review of
PR #237 at ffe9324, owner decisions 2026-11-03): item 20 (targetTrace
dependencies, no satisfy on implemented=false parts), N1 whole-line cap, N2
14.10 floor, N3 foreign handles, N4 no pin-ingest carve-out, N5 dedicated
session_bytes event, N6 over-cap load refused, and the D02 test citation.
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
#
# Item 20 (Elon review of PR #237 at ffe9324): a target part with
# implemented=false must not `satisfy` anything. Each former satisfy is a plain
# dependency targetTrace_<Part>_<Req> from the part def to the requirement.

TARGET_TRACE_DOC = "PROPOSAL target trace; not a satisfy; tracker does not count it"


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


def _target_traces(part_name: str, req_tokens: tuple[str, ...]) -> list[str]:
    """`dependency targetTrace_<Part>_... from <Part> to <req>` statements (with their body)."""
    text = _all_model_text()
    found = []
    for m in re.finditer(rf"\bdependency\s+targetTrace_{part_name}_\w+", text):
        end = text.index(";", m.start())
        brace = text.find("{", m.start())
        stmt = _block(text, m.start()) if 0 <= brace < end else text[m.start() : end + 1]
        head = stmt.split("{", 1)[0]
        if re.search(rf"\bfrom\s+[\w:]*\b{part_name}\b", head) and any(
            re.search(rf"\bto\s+[\w:]*\b{t}\b", head) for t in req_tokens
        ):
            found.append(stmt)
    return found


def _assert_target_trace(part_name: str, req_tokens: tuple[str, ...]) -> None:
    traces = _target_traces(part_name, req_tokens)
    assert traces, (
        f"no dependency targetTrace_{part_name}_<Req> from {part_name} to {req_tokens[1]}"
    )
    assert any(TARGET_TRACE_DOC in " ".join(t.split()) for t in traces), (
        f"targetTrace for {part_name} -> {req_tokens[1]} lacks doc {TARGET_TRACE_DOC!r}"
    )


def _target_part_defs() -> dict[str, str]:
    """implemented=false part defs in implementation.sysml (the MN-REQ-14 target parts)."""
    text = (MODELS / "implementation.sysml").read_text(encoding="utf-8")
    found = {m.group(1): _block(text, m.start()) for m in re.finditer(r"\bpart def (\w+)", text)}
    return {
        n: b for n, b in found.items() if re.search(r"\bimplemented\s*:\s*Boolean\s*=\s*false", b)
    }


def test_no_satisfy_on_any_implemented_false_part():
    parts = _target_part_defs()
    assert parts, "no part def with implemented=false"
    bad = [n for n, b in parts.items() if re.search(r"\bsatisfy\b", _strip_comments(b))]
    assert not bad, f"satisfy inside implemented=false part defs: {bad}"
    text = _strip_comments(_all_model_text())
    for m in re.finditer(r"\bsatisfy\b[^;]*\bby\s+([\w:]+)\s*;", text):
        target = m.group(1).split("::")[-1]
        assert target not in parts, f"satisfy ... by {target} on an implemented=false part"


def test_id_index_part_satisfies_14_4_and_has_target_trace_to_14_6():
    name, body = _one_def("part", r"IdIndex")
    code = _strip_comments(body)
    text = _strip_comments(_all_model_text())
    req = "|".join(REQ_14_4)
    in_body = re.search(rf"\bsatisfy\b[^;]*\b(?:{req})\s*;", code)
    by_part = re.search(rf"\bsatisfy\b[^;]*\b(?:{req})\b[^;]*\bby\s+[\w:]*\b{name}\s*;", text)
    assert in_body or by_part, f"{name} must satisfy {REQ_14_4[1]}"
    assert not _target_traces(name, REQ_14_4), f"{name} still has a targetTrace to 14.4"
    _assert_target_trace(name, REQ_14_6)


def test_tombstone_store_part_has_target_trace_to_14_6():
    _one_def("part", r"TombstoneStore")
    _assert_target_trace("TombstoneStore", REQ_14_6)


def test_handle_table_part_has_target_trace_to_14_7():
    _one_def("part", r"HandleTable")
    _assert_target_trace("HandleTable", REQ_14_7)


def test_developer_credential_is_a_port_def():
    _one_def("port", DEV_CREDENTIAL)


def test_developer_listener_has_credential_port_and_target_trace_14_8():
    name, body = _one_def("part", r"DeveloperListener")
    port_defs = _defs("port", DEV_CREDENTIAL)
    assert port_defs, "no credential port def"
    assert any(re.search(rf"\bport\s+\w+\s*:\s*~?{pd}\b", body) for pd in port_defs), (
        f"{name} has no port typed by a credential port def"
    )
    _assert_target_trace(name, REQ_14_8)


def test_session_byte_budget_part_is_implemented_and_satisfies_14_10():
    name, body = _one_def("part", r"Byte(s)?Budget")
    code = _strip_comments(body)
    assert re.search(r"\bimplemented\s*:\s*Boolean\s*=\s*true", code), (
        f"{name} must be implemented=true"
    )
    assert re.search(rf"\bsatisfy\b[^;]*\b{REQ_14_10[1]}\s*;", code), (
        f"{name} must satisfy {REQ_14_10[1]}"
    )
    assert not _target_traces(name, REQ_14_10), f"{name} still has a targetTrace"


# ----- behaviour -----


def test_range_where_action_is_traced():
    name, _ = _one_def("action", r"Range")
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


# ----- Elon review of PR #237 at ffe9324: N1-N6 and D02 (symphony linecap-n1n6) -----

PER_VALUE_WORST = re.compile(r"64\s*x\s*32,?768|10,?485,?760,?000")
WHOLE_LINE_REFUSAL = re.compile(r"line_bytes\|\{n\}/\{max\}")
OLD_FLOOR = re.compile(r"20,?480,?000")
NEW_FLOOR = re.compile(r"5,?000\s*x\s*32,?768\s*=\s*163,?840,?000")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_n1_line_cap_checks_whole_record_line_at_mutate():
    doc = _flat(_requirement_doc("MN_REQ_14_9_ValueCap32k"))
    _, enforce = _one_def("action", r"ValueLineCapEnforce")
    enforce = _flat(enforce)
    for where, body in (("14.9", doc), ("ValueLineCapEnforce", enforce)):
        low = body.lower()
        assert re.search(r"whole (record )?line", low), (
            f"{where}: line cap must cover the whole record line"
        )
        assert "all fields" in low, f"{where}: whole line means all fields"
        assert WHOLE_LINE_REFUSAL.search(body), (
            f"{where}: refusal must be limit_exceeded|line_bytes|{{n}}/{{max}}"
        )
        assert "a value whose escaped wire size" not in low, f"{where}: still checks one value only"
        assert not PER_VALUE_WORST.search(body), f"{where}: 5,000 x 64 x 32,768 framed as reachable"
    assert re.search(r"per-record bound[^.]*line cap", doc, re.IGNORECASE), (
        "14.9 must say the per-record bound is the line cap"
    )
    s09 = _flat(_verify_case("MN_VER_14_S09_ValueCap32k"))
    assert "fix/line-cap-whole-line" in s09, (
        "S09 multi-field case must cite code PR fix/line-cap-whole-line"
    )
    assert re.search(r"fields? each fits?", s09) and re.search(r"whole (escaped )?line", s09), (
        "S09 needs a multi-field case: each field fits, whole escaped line over the cap"
    )
    assert LINE_CAP.search(s09)
    assert not PER_VALUE_WORST.search(s09)


def test_n2_session_bytes_default_is_163840000_a_cap_not_a_floor():
    doc = _flat(_requirement_doc("MN_REQ_14_10_SessionTotalBytesCap"))
    s10 = _flat(_verify_case("MN_VER_14_S10_SessionTotalBytesCap"))
    _, part = _one_def("part", r"SessionByteBudget")
    _, states = _one_def("state", r"SessionByteBudgetStates")
    assert NEW_FLOOR.search(doc), "14.10 default must be 5,000 x 32,768 = 163,840,000"
    for where, body in (("14.10", doc), ("S10", s10)):
        assert "refuses nothing that loads" not in body, f"{where} floor claim is false"
        assert "nothing that loads today" not in body, f"{where} floor claim is false"
        assert "tombstone" not in body.lower().replace("no tombstones", ""), (
            f"{where} counts tombstones, which do not exist"
        )
    assert "escaped" in doc.lower(), "14.10 floor counts escaped line bytes"
    assert re.search(r"163,?840,?000", s10), "S10 default must be 163,840,000"
    for where, body in (
        ("14.10", doc),
        ("S10", s10),
        ("SessionByteBudget", part),
        ("SessionByteBudgetStates", states),
    ):
        assert not OLD_FLOOR.search(body), f"{where} still uses 20,480,000 as floor"
    assert "MEMNET_MAX_SESSION_BYTES" in doc, "14.10 must name the setting MEMNET_MAX_SESSION_BYTES"
    assert "MEMNET_MAX_SESSION_BYTES" in part, (
        "SessionByteBudget must name MEMNET_MAX_SESSION_BYTES"
    )


HANDLE_UNIQUE = re.compile(
    r"process-unique|unique (across|within|in) the process|carr(y|ies) (its|their|the) session",
    re.IGNORECASE,
)


def test_n3_foreign_session_handle_is_refused():
    doc = _flat(_requirement_doc("MN_REQ_14_7_AgentHandlesNotIds"))
    _, table = _one_def("part", r"HandleTable")
    table = _flat(table)
    for where, body in (("14.7", doc), ("HandleTable", table)):
        assert HANDLE_UNIQUE.search(body), (
            f"{where}: handles must be process-unique or carry their session"
        )
        assert "foreign" in body.lower(), (
            f"{where}: a handle from another session is foreign and refused"
        )
    assert "never reused in that session" not in doc, "14.7 still scopes uniqueness to one session"
    s07 = _flat(_verify_case("MN_VER_14_S07_AgentHandlesNotIds"))
    assert re.search(r"session A[^.;]*session B[^.;]*refused", s07), (
        "S07 needs a case: session A handle presented to session B is refused"
    )


def test_n4_no_pin_ingest_deterministic_id_carve_out():
    doc = _flat(_requirement_doc("MN_REQ_14_6_IdDesign"))
    s06 = _flat(_verify_case("MN_VER_14_S06_IdDesign"))
    for where, body in (("14.6", doc), ("S06", s06)):
        low = body.lower()
        assert "carve-out" not in low, f"{where}: pin-ingest carve-out still present"
        assert "keeps its deterministic ids" not in low, (
            f"{where}: pin ingest still keeps deterministic ids"
        )
        assert re.search(r"pin[- ]ingest\w*[^.;]*(commit|minted)", low), (
            f"{where}: pin-ingested elements are created by Commit and get a minted UUIDv7"
        )
        assert "locator" in low, f"{where}: locators stay properties (11.16)"
    g = re.search(r"\(g\)(.*?)(\(h\)|Behaviour:)", s06)
    assert g and "UUIDv7" in g.group(1), "S06(g) must say pin-ingested elements get a minted UUIDv7"


def test_n5_at_budget_means_total_at_or_over_budget():
    events = _defs("attribute", r"^EvSessionBytes\w*Refus")
    assert events, "no attribute def EvSessionBytes...Refused for a session_bytes refusal"
    _, states = _one_def("state", r"SessionByteBudgetStates")
    code = _strip_comments(states)
    assert not re.search(r"\baccept\s+EvError\b", code), (
        "generic EvError must not move underBudget -> atBudget"
    )
    moves = re.findall(
        r"\btransition\s+\w+\s+first\s+underBudget\s+accept\s+(\w+)\s+then\s+atBudget", code
    )
    assert moves and all(e not in events for e in moves), (
        f"a refusal event must not move underBudget -> atBudget (atBudget is a total), got {moves}"
    )
    assert "at or over the budget" in _flat(states), "atBudget must mean total at or over budget"


def test_n6_over_cap_load_refused_value_bytes_no_open_question():
    s09 = _flat(_verify_case("MN_VER_14_S09_ValueCap32k"))
    assert "loads anyway" not in s09, "S09(g) still says the snapshot may load anyway"
    assert "open for Elon" not in s09, "S09(g) still open"
    g = re.search(r"\(g\)(.*?)\(h\)", s09)
    assert g and "value_bytes" in g.group(1) and "refused" in g.group(1), (
        "S09(g): over-cap load is refused with value_bytes"
    )
    _, enforce = _one_def("action", r"ValueLineCapEnforce")
    enforce = _flat(enforce)
    assert re.search(r"On load:[^.]*refused[^.]*value_bytes", enforce), (
        "load refusal (value_bytes) must stay"
    )


def test_d02_verify_case_cites_real_test():
    d02 = _verify_case("MN_VER_14_D02_WhereRelationSetRefusedAsDelete")
    cite = "tests/test_d02_where_set_refusal.py"
    assert (ROOT / cite).is_file(), f"{cite} missing"
    assert cite in d02, f"MN-VER-14-D02 must cite {cite}"
