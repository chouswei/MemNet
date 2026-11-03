"""PR #241 model status (symphony pr241-model-b1b2, nodes N1-N4).

Red-first text/regex tests: the byte-budget state machine guards, the
MN-REQ-14 status wording (14.9-14.11 implemented), the implementation block
comment and the verify S09/S11 wording.
"""

from __future__ import annotations

import re
from pathlib import Path

MODELS = Path(__file__).resolve().parents[1] / "sysml-models" / "models"


def _text(name: str) -> str:
    return (MODELS / name).read_text(encoding="utf-8")


def _block(text: str, start: int) -> str:
    open_at = text.index("{", start)
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise AssertionError("unbalanced braces")


def _flat(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def _states() -> str:
    t = _text("behaviour.sysml")
    return _block(t, t.index("state def SessionByteBudgetStates"))


def _transitions(src: str, name: str) -> list[str]:
    return [m.group(0) for m in re.finditer(rf"transition {name}\b[^;]*;", src)]


def _req(name: str) -> str:
    t = _text("requirements.sysml")
    return _block(t, t.index(f"requirement def {name}"))


# ---- N1: behaviour.sysml SessionByteBudgetStates ----


def test_n1_free_bytes_out_of_at_budget_is_guarded():
    ts = [
        x
        for x in _transitions(_states(), "free_bytes")
        if "first atBudget" in x and "then underBudget" in x
    ]
    assert ts, "free_bytes atBudget -> underBudget missing"
    for x in ts:
        assert re.search(r"\bif\b", x), x


def test_n1_write_fits_out_of_at_budget_is_guarded():
    ts = [
        x
        for x in _transitions(_states(), "write_fits")
        if "first atBudget" in x and "then underBudget" in x
    ]
    assert ts, "write_fits atBudget -> underBudget missing"
    for x in ts:
        assert re.search(r"\bif\b", x), x


def test_n1_guards_name_new_total_under_budget():
    s = _states()
    for n in ("free_bytes", "write_fits"):
        x = " ".join(_transitions(s, n))
        assert re.search(r"(?i)(total|new\w*).*budget|budget.*(total|new)", x), n


def test_n1_at_budget_has_stay_transition():
    s = _states()
    stays = [
        m.group(0) for m in re.finditer(r"transition \w+\s+first atBudget[^;]*then atBudget\s*;", s)
    ]
    assert stays, "no atBudget -> atBudget stay transition"
    assert any(re.search(r"\bif\b", x) for x in stays)


def test_n1_no_shrinking_write_accepted_claim():
    assert not re.search(r"(?i)shrinking write is\s+accepted", _flat(_states()))


def test_n1_doc_delete_skips_only_budget_write_total_rule():
    f = _flat(_states())
    assert not re.search(r"(?i)deletes always pass", f)
    assert re.search(
        r"(?i)a delete skips only the budget check; the field and line caps still run", f
    )
    assert re.search(r"(?i)write is accepted only if the new total ends at or under the budget", f)
    assert re.search(r"(?i)otherwise it is refused session_bytes", f)


def test_n1_declares_new_total_and_budget():
    s = _states()
    assert re.search(r"attribute newTotal\s*:", s)
    assert re.search(r"attribute budget\s*:", s)


def test_n1_at_budget_guards_split_on_budget():
    s = _states()
    for n in ("free_bytes", "write_fits"):
        assert any("newTotal < budget" in x for x in _transitions(s, n)), n
    for n in ("stay_at_budget", "write_stays_at_budget"):
        assert any("newTotal >= budget" in x for x in _transitions(s, n)), n


def test_n1_bytes_write_covers_every_accepted_write():
    f = _flat(_text("behaviour.sysml"))
    m = re.search(r"attribute def EvBytesWrite \{.*?\*/", f)
    assert m
    d = m.group(0)
    assert re.search(r"(?i)any write whose new total", d)
    assert re.search(r"newTotal <= budget", d)
    assert not re.search(r"(?i)not overlap|disjoint", d)


# ---- N2: requirements.sysml ----


def _group() -> str:
    return _req("MN_REQ_14_AtelierBoardAsks").split("requirement def MN_REQ_14_1_")[0]


def test_n2_group_no_engine_untouched_claims():
    g = _flat(_group())
    assert "no engine code changes in this cut" not in g
    assert not re.search(r"(?i)every MN-VER-14 case is model-level", g)
    assert not re.search(r"(?i)no runtime test, and a tracker", g)


def test_n2_group_names_implemented():
    g = _flat(_group())
    assert re.search(r"(?i)implemented", g)
    for n in ("14.9", "14.10", "14.11"):
        assert n in g
    assert re.search(r"(?i)runtime tests?", g)


def test_n2_index_14_9_not_proposal():
    line = next(
        ln for ln in _text("requirements.sysml").splitlines() if re.match(r"\s*MN-REQ-14\.9\s", ln)
    )
    assert "PROPOSAL" not in line


def test_n2_14_9_doc_not_proposal():
    assert "PROPOSAL" not in _req("MN_REQ_14_9_ValueCap32k")[:400]
    assert re.search(r"Status: implemented", _req("MN_REQ_14_9_ValueCap32k"))


def test_n2_14_11_mentions_field_cap():
    assert re.search(
        r"(?i)field cap|per-field|field count|fields? (is|are) capped",
        _req("MN_REQ_14_11_BypassPathCaps")
        if "MN_REQ_14_11_BypassPathCaps" in _text("requirements.sysml")
        else _text("requirements.sysml").split('"MN-REQ-14.11"')[0][-3000:],
    )


def test_n2_proposal_kept_on_others():
    t = _text("requirements.sysml")
    idx = {}
    for ln in t.splitlines():
        m = re.match(r"\s*MN-REQ-(14\.\d+)\s", ln)
        if m:
            idx[m.group(1)] = ln
    for k in ("14.6", "14.7", "14.8"):
        assert "PROPOSAL" in idx[k], k
    assert "PARKED" in idx["14.2"] and "PARKED" in idx["14.3"]
    for name in (
        "MN_REQ_14_5_",
        "MN_REQ_14_6_",
        "MN_REQ_14_7_",
        "MN_REQ_14_8_",
    ):
        i = t.index(f"requirement def {name}")
        assert "PROPOSAL" in _block(t, i)[:600], name


# ---- N3: implementation.sysml ----


def test_n3_board_comment_qualified():
    t = _text("implementation.sysml")
    i = t.index("Atelier-board asks (PROPOSAL; MN-REQ-14")
    head = _flat(t[i : t.index("part def AtelierBoardAskPlan", i)])
    assert not re.search(r"nothing is shipped\.?\s*$", head.strip())
    assert re.search(r"(?i)implemented", head)
    # 14.12 (incremental ledger) widened the range to 14.9-14.12.
    if not re.search(r"14\.9 to 14\.1[12]", head):
        for n in ("14.9", "14.10", "14.11"):
            assert n in head


# ---- N4: verify.sysml ----


def test_n4_s09_objective_not_no_runtime_test():
    t = _text("verify.sysml")
    i = t.index("objective atelierBoardS09")
    assert "no runtime test" not in _block(t, i)


def test_n4_s11_cases_a_c_limited_to_import_hydrate():
    t = _text("verify.sysml")
    d = _flat(_block(t, t.index("verification def MN_VER_14_S11_BypassPathCaps")))
    assert not re.search(
        r"For each of snapshot import, durable hydrate and CLI delete/prune: \(a\)", d
    )
    assert re.search(
        r"(?i)\(a\)[^;]*(import|hydrate)[^;]*(only|not CLI|CLI delete and prune are not)", d
    ) or re.search(r"(?i)(a) and \(c\)[^.]*import and hydrate|import and hydrate[^.]*\(a\)", d)


def test_n4_summary_consistent():
    t = _text("verify.sysml")[:6000]
    assert re.search(r"S09 to S1[12] implemented", t) or re.search(r"S09.{0,4}S1[12]", t)
    assert re.search(r"(?i)14\.11 bypass-path caps: import, hydrate", t)
    assert not re.search(r"14\.11 bypass-path caps: import, hydrate, CLI delete/prune \(S11\)", t)
