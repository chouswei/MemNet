"""Compile soul-library cite lines from seed USR31 / LIB rows + latest @OLN (Phase C)."""

from __future__ import annotations

import re
from typing import Any

from novel_mcp.warm_index import WarmIndex, usr_value

_GLO_CITE_RE = re.compile(r"cite_glo(\d+)", re.I)


def latest_oln_body(index: WarmIndex) -> str | None:
    best_n = -1
    best: str | None = None
    for body in index.rows_by_tag.get("OLN", []):
        parts = body.split("|")
        if len(parts) < 2:
            continue
        try:
            n = int(parts[1])
        except ValueError:
            continue
        if n >= best_n:
            best_n = n
            best = body
    return best


def oln_context_text(oln_body: str) -> str:
    parts = oln_body.split("|")
    if len(parts) >= 6:
        return "".join(parts[2:6])
    return oln_body


def _split_vocab(text: str) -> list[str]:
    sep = ";" if ";" in text else ","
    return [t.strip() for t in text.split(sep) if t.strip()]


def lib_match_keys(index: WarmIndex) -> list[str]:
    val = usr_value(index, "lib_match_keys")
    if not val:
        return []
    return _split_vocab(val.replace(",", ";"))


def parse_lib_rows(index: WarmIndex) -> list[list[str]]:
    return [body.split("|") for body in index.rows_by_tag.get("LIB", []) if body.strip()]


def match_lib_rows(index: WarmIndex, context: str) -> list[list[str]]:
    keys = lib_match_keys(index)
    matched: list[list[str]] = []
    seen: set[str] = set()
    for lib in parse_lib_rows(index):
        if not lib:
            continue
        lid = lib[0]
        searchable = "|".join(lib[1:4]) if len(lib) >= 4 else lid
        hit = False
        for key in keys:
            if key not in context:
                continue
            if key in searchable or (len(lib) >= 3 and key in lib[2]):
                hit = True
                break
        if not hit and len(lib) >= 3 and lib[2] and lib[2] in context:
            hit = True
        if hit and lid not in seen:
            seen.add(lid)
            matched.append(lib)
    return matched


def _lib_fallback_id(index: WarmIndex) -> str:
    val = usr_value(index, "lib_anchor") or ""
    for part in _split_vocab(val.replace(",", ";")):
        if part.startswith("fallback_"):
            return part.removeprefix("fallback_")
    libs = parse_lib_rows(index)
    return libs[0][0] if libs else "LIB01"


def _tec_anchor_ids(index: WarmIndex) -> set[str]:
    return {body.split("|", 1)[0] for body in index.rows_by_tag.get("TEC", []) if body.strip()}


def _tec_linked_libs(index: WarmIndex) -> list[list[str]]:
    tec = _tec_anchor_ids(index)
    return [lib for lib in parse_lib_rows(index) if len(lib) >= 2 and lib[1] in tec]


def _law_constraint_blob(index: WarmIndex, law_id: str) -> str:
    law = index.laws.get(law_id)
    if not law:
        return ""
    return f"{law.constraint} {' '.join(law.tokens)}"


def _law_requests_glo_vocab(index: WarmIndex) -> bool:
    blob = _law_constraint_blob(index, "LAW-LIB01").lower()
    return "cite_glo_vocab" in blob or bool(_GLO_CITE_RE.search(blob))


def _law_no_tech_tree_only(index: WarmIndex) -> bool:
    blob = _law_constraint_blob(index, "LAW-LIB03").lower()
    return "no_tech_tree_only" in blob


def _text_overlaps_vocab(text: str, vocab: list[str]) -> bool:
    return any(tok and tok in text for tok in vocab)


def _lib_glo_ids(index: WarmIndex) -> list[str]:
    val = usr_value(index, "lib_glo_ids")
    if not val:
        return []
    return _split_vocab(val.replace(",", ";"))


def _glo_row(index: WarmIndex, glo_id: str) -> list[str] | None:
    for body in index.rows_by_tag.get("GLO", []):
        parts = body.split("|")
        if parts and parts[0] == glo_id:
            return parts
    return None


def _glo_link_bullets(
    index: WarmIndex,
    context: str,
    matched: list[list[str]],
    *,
    lib_query: bool,
) -> list[str]:
    if not _law_requests_glo_vocab(index):
        return []
    topic_blob = "|".join(lib[2] for lib in matched if len(lib) > 2)
    searchable = context + topic_blob
    configured = _lib_glo_ids(index)
    bullets: list[str] = []

    def _maybe_add(parts: list[str]) -> None:
        glo_id = parts[0]
        label = parts[1] if len(parts) > 1 else glo_id
        vocab = _split_vocab(parts[3]) if len(parts) > 3 else []
        vocab_hit = _text_overlaps_vocab(searchable, vocab)
        forced = bool(configured and glo_id in configured and matched and lib_query)
        if vocab_hit or forced:
            sem = parts[3] if len(parts) > 3 else ""
            bullets.append(f"Link {glo_id} ({label}) in library table: {sem}")

    if configured:
        for glo_id in configured:
            row = _glo_row(index, glo_id)
            if row:
                _maybe_add(row)
        return bullets

    for body in index.rows_by_tag.get("GLO", []):
        parts = body.split("|")
        if len(parts) >= 4:
            _maybe_add(parts)
    return bullets


def _tec_lib_bullets(
    index: WarmIndex,
    matched: list[list[str]],
    *,
    lib_query: bool,
) -> list[str]:
    tec_libs = _tec_linked_libs(index)
    if not tec_libs:
        return []
    matched_ids = {row[0] for row in matched}
    tec_ids = {row[0] for row in tec_libs}
    hit = matched_ids & tec_ids
    bullets: list[str] = []
    if hit:
        for lib in tec_libs:
            if lib[0] not in hit:
                continue
            anchor = lib[1] if len(lib) > 1 else ""
            topic = lib[2] if len(lib) > 2 else ""
            bullets.append(f"Related TEC route: cite {lib[0]} → {anchor} ({topic})")
    elif lib_query and _law_no_tech_tree_only(index):
        bullets.append(
            f"Ban no_tech_tree_only: omit {', '.join(sorted(tec_ids))} unless OLN matches per USR31b"
        )
    return bullets


def compile_library_contracts(
    index: WarmIndex,
    *,
    lib_query: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    """Return (bullet contracts, meta) for presentation.library_contracts."""
    meta: dict[str, Any] = {}
    hint = usr_value(index, "stage_hint_lib")
    bullets: list[str] = []
    fallback = _lib_fallback_id(index)

    oln = latest_oln_body(index)
    if not oln:
        if lib_query and hint:
            bullets.append(hint)
        if lib_query:
            bullets.append(f"Cite {fallback} — no @OLN in warm yet")
        return bullets, meta

    ctx = oln_context_text(oln)
    oln_id = oln.split("|", 1)[0]
    meta["oln_anchor"] = oln_id
    meta["oln_context"] = ctx

    matched = match_lib_rows(index, ctx)
    meta["matched_libs"] = [row[0] for row in matched]

    if lib_query and hint:
        bullets.append(hint)

    if lib_query:
        preview = ctx if len(ctx) <= 96 else ctx[:96] + "…"
        bullets.append(f"Library anchor (LAW-LIB03): latest {oln_id} — {preview}")

    if matched:
        for lib in matched:
            lid = lib[0]
            topic = lib[2] if len(lib) > 2 else ""
            short = lib[3] if len(lib) > 3 else ""
            status = lib[4] if len(lib) > 4 else ""
            bullets.append(f"Cite {lid} ({topic}, {short}) [{status}] — required")
    else:
        bullets.append(f"Cite {fallback} — fallback per USR31 lib_anchor")

    bullets.extend(_glo_link_bullets(index, ctx, matched, lib_query=lib_query))
    bullets.extend(_tec_lib_bullets(index, matched, lib_query=lib_query))

    if lib_query:
        bullets.append(
            "LAW-OPT03: no time advance; consciousness_frame + plain_route_table; reoffer 1–6"
        )

    return bullets, meta
