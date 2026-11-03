"""PR #241b model follow-up (symphony pr241b-model-n1n3, node P1).

Red-first text/regex tests pinning N1 (behaviour.sysml byte-budget wording and
MN-REQ-14 section header) and N2 (requirements.sysml MN_REQ_05_3 defaults).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"


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


def _reach_doc() -> str:
    t = _text("behaviour.sysml")
    return _flat(_block(t, t.index("attribute def EvBytesReachBudget")))


def _states() -> str:
    t = _text("behaviour.sysml")
    return _flat(_block(t, t.index("state def SessionByteBudgetStates")))


def _header() -> str:
    t = _text("behaviour.sysml")
    return next(ln for ln in t.splitlines() if "Atelier-board asks" in ln and "-----" in ln)


# ---- N1 (a): EvBytesReachBudget doc ----


def test_n1a_reach_doc_drops_at_or_over_it():
    assert "at or over it" not in _reach_doc()


def test_n1a_reach_doc_says_over_budget_load_hydrate_refused():
    d = _reach_doc()
    assert re.search(r"(?i)(load|hydrate)[^.]*over (the )?budget[^.]*refused", d), d


def test_n1a_reach_doc_fires_only_exactly_at_budget_or_lowered_setting():
    d = _reach_doc()
    assert re.search(r"(?i)exactly (at|on) the budget", d), d
    assert "MEMNET_MAX_SESSION_BYTES" in d and re.search(r"(?i)lowered", d)


# ---- N1 (b): SessionByteBudget rule text ----


def test_n1b_no_unconditional_delete_claims():
    s = _states()
    assert "only deletes pass" not in s.lower()
    assert "deletes always pass" not in s.lower()


def test_n1b_delete_skips_only_budget_check():
    s = _states()
    assert re.search(r"(?i)delete[^.]*skips? only the budget check", s), s
    assert re.search(r"(?i)field[^.]*line caps[^.]*(still )?(run|apply)", s), s


# ---- N1 (c): section header ----


def test_n1c_header_not_proposal_target_only():
    assert "(PROPOSAL; MN-REQ-14; target only)" not in _header()


def test_n1c_header_names_implemented_items():
    h = _header()
    assert re.search(r"(?i)implemented", h), h
    for n in ("14.9", "14.10", "14.11"):
        assert n in h, h


def test_n1c_other_items_stay_proposal():
    h = _header()
    assert "PROPOSAL" in h and re.search(r"(?i)implemented", h), h


# ---- N2: MN_REQ_05_3_ConsistentValueByteCap ----


def _req53() -> str:
    t = _text("requirements.sysml")
    return _flat(_block(t, t.index("requirement def MN_REQ_05_3_ConsistentValueByteCap")))


def test_n2_value_default_32768():
    d = _req53()
    assert re.search(r"(?i)MEMNET_MAX_VALUE_BYTES[^.]*32768|32768[^.]*MEMNET_MAX_VALUE_BYTES", d), d
    assert "Default 4096" not in d


def test_n2_line_default_135168():
    d = _req53()
    assert "135168" in d, d
    assert re.search(r"4 ?[x×*] ?32768 ?\+ ?4096", d), d
    assert "MAX_LINE_BYTES, default 32768" not in d


def test_n2_matches_config_py():
    cfg = (ROOT / "parts/common/memnet/memnet/config.py").read_text(encoding="utf-8")
    assert '"MEMNET_MAX_VALUE_BYTES", 32768' in cfg
    assert '"MEMNET_MAX_LINE_BYTES", 135168' in cfg
    d = _req53()
    assert "32768" in d and "135168" in d
    assert "Default 4096" not in d
