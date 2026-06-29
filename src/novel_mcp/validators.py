"""Finish-time validators driven by seed LAW constraint tokens."""

from __future__ import annotations

import re
from typing import Any

from novel_mcp.warm_index import WarmIndex, index_warm, laws_for_stage, usr_value

_ACTION_CHAIN_RE = re.compile(
    r"^(?:[^，。！？；：、]+[，、]){2,}|"
    r"[^。！？；]{0,8}(?:然後|接著|隨即|便|再|又).*(?:然後|接著|隨即|便|再|又)"
)

_TOKEN_RULES: dict[str, str] = {
    "full_sentence": "option must be a complete readable sentence",
    "no_action_chain": "option must not be a verb chain / outline style",
    "opt_readable_baihua": "option must be readable vernacular",
}


def _option_length_bounds(index: WarmIndex) -> tuple[int | None, int | None]:
    lo: int | None = None
    hi: int | None = None
    for law in index.laws.values():
        for tok in law.tokens:
            if tok.startswith("min_chars:"):
                try:
                    lo = int(tok.split(":", 1)[1])
                except ValueError:
                    pass
            if tok.startswith("max_chars:"):
                try:
                    hi = int(tok.split(":", 1)[1])
                except ValueError:
                    pass
    style = usr_value(index, "option_style") or usr_value(index, "opt_copy") or ""
    for part in style.replace(";", ",").split(","):
        part = part.strip()
        if part.endswith("字") and part[:-1].isdigit():
            hi = int(part[:-1])
        if "-" in part and part.endswith("字"):
            seg = part.replace("字", "")
            if "-" in seg:
                a, b = seg.split("-", 1)
                if a.isdigit() and b.isdigit():
                    lo, hi = int(a), int(b)
    return lo, hi


def _law_requires(index: WarmIndex, token: str) -> bool:
    for law in laws_for_stage(index, "prose", for_options=True):
        if token in law.tokens or token in law.mechanism:
            return True
    for law in index.laws.values():
        if token in law.tokens or token in law.mechanism:
            return True
    return False


def validate_option_lines(
    option_lines: list[str],
    *,
    warm_stdout: str,
    auto_beat: bool = False,
) -> dict[str, Any]:
    """Return {violations, warnings} from seed-linked LAW tokens."""
    violations: list[str] = []
    warnings: list[str] = []
    if not option_lines:
        return {"violations": violations, "warnings": warnings}

    if auto_beat:
        violations.append("@ERR: auto_beat_options|昏厥拍禁六選項")
        return {"violations": violations, "warnings": warnings}

    index = index_warm(warm_stdout)
    lo, hi = _option_length_bounds(index)
    lib_copy = (usr_value(index, "lib_opt_copy") or "").strip()
    need_full = _law_requires(index, "full_sentence") or _law_requires(index, "opt_readable_baihua")
    need_no_chain = _law_requires(index, "no_action_chain")

    for i, text in enumerate(option_lines, start=1):
        t = text.strip()
        if not t:
            violations.append(f"@ERR: option_empty|slot {i}")
            continue
        n = len(t)
        slot_lo = lo
        if i == 6 and lib_copy and lo is not None and len(lib_copy) < lo:
            slot_lo = len(lib_copy)
        if slot_lo is not None and n < slot_lo:
            violations.append(f"@ERR: option_short|slot {i}|{n}<{slot_lo}")
        if hi is not None and n > hi:
            warnings.append(f"option_long: slot {i} ({n}>{hi})")
        if need_no_chain and _ACTION_CHAIN_RE.search(t):
            violations.append(f"@ERR: option_action_chain|slot {i}")
        if need_full and not re.search(r"[。！？；…]$", t) and n < 8:
            warnings.append(f"option_incomplete: slot {i}")

    return {"violations": violations, "warnings": warnings}
