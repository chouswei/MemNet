"""Validate, merge, and ingest LLM-generated @ART rows (schema-driven)."""

from __future__ import annotations

import re
from typing import Any, Callable

from novel_mcp.bootstrap import ingest_lines
from novel_mcp.catalog_schema import (
    CatalogSchema,
    art_to_wire,
    default_burn_for_art,
    slot_for_kind,
)
from novel_mcp.opening_loadout import (
    arts_from_session,
    catalog_slots,
    parse_catalog_md,
)
from novel_mcp.setup_graph import graph_update, read_usr_by_key

_NAME_FIELD_INDEX = 1


def _parse_coeff(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _name_field(schema: CatalogSchema) -> str:
    if len(schema.wire_columns) > _NAME_FIELD_INDEX:
        return schema.wire_columns[_NAME_FIELD_INDEX]
    return "name"


def validate_art_dict(art: dict[str, str], schema: CatalogSchema) -> list[str]:
    errors: list[str] = []
    aid = art.get("id", "")
    prefix = re.escape(schema.id_prefix)
    if not re.match(rf"^{prefix}\d+$", aid):
        errors.append(f"{aid}: id must match {schema.id_prefix}<number>")
    name_key = _name_field(schema)
    name = art.get(name_key, "").strip()
    if not name or len(name) > schema.name_max_len:
        errors.append(f"{aid}: name must be 1-{schema.name_max_len} chars")
    kind = art.get(schema.kind_field, "")
    if kind not in schema.valid_kinds:
        errors.append(f"{aid}: {schema.kind_field} not in allowed kinds")
    tier = art.get(schema.tier_field, "")
    if tier not in schema.valid_tiers:
        errors.append(f"{aid}: {schema.tier_field} not in allowed tiers")
    coeff = _parse_coeff(art.get(schema.coeff_field, ""))
    if coeff is None:
        errors.append(f"{aid}: {schema.coeff_field} must be a number")
    elif tier in schema.tier_coeff_bands:
        lo, hi = schema.tier_coeff_bands[tier]
        if not (lo <= coeff <= hi):
            errors.append(
                f"{aid}: {schema.coeff_field} {coeff} outside {tier} band {lo}-{hi}"
            )
    if slot_for_kind(kind, schema) is None:
        errors.append(f"{aid}: {schema.kind_field}={kind!r} has no opening slot")
    return errors


def merge_arts(
    base: list[dict[str, str]],
    additions: list[dict[str, str]],
    schema: CatalogSchema,
) -> tuple[list[dict[str, str]], list[str]]:
    by_id = {a["id"]: a for a in base}
    name_key = _name_field(schema)
    names = {a.get(name_key, "") for a in base}
    errors: list[str] = []
    for art in additions:
        errs = validate_art_dict(art, schema)
        if errs:
            errors.extend(errs)
            continue
        if art["id"] in by_id:
            errors.append(f"{art['id']}: duplicate id")
            continue
        nm = art.get(name_key, "")
        if nm in names:
            errors.append(f"{nm}: duplicate name")
            continue
        by_id[art["id"]] = art
        names.add(nm)
    return list(by_id.values()), errors


def slot_counts(arts: list[dict[str, str]], schema: CatalogSchema) -> dict[str, int]:
    slots = catalog_slots(arts, schema)
    return {k: len(slots[k]["arts"]) for k in ("neigong", "martial", "qinggong")}


def build_usr_burn_update(
    session: str | None,
    new_arts: list[dict[str, str]],
    schema: CatalogSchema,
) -> str | None:
    if not schema.burn_usr_key:
        return None
    raw = read_usr_by_key(session, schema.burn_usr_key)
    if raw is None:
        return None
    existing: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            existing[k.strip()] = v.strip()
    for art in new_arts:
        existing.setdefault(art["id"], default_burn_for_art(art, schema))
    pairs = [
        f"{k}:{existing[k]}"
        for k in sorted(existing, key=lambda x: int(x[len(schema.id_prefix) :]) if x[len(schema.id_prefix) :].isdigit() else x)
    ]
    return f"@USR: {schema.burn_usr_id}|{schema.burn_usr_key}|{';'.join(pairs)}|persistent"


def sync_art_neili_burn(
    session: str,
    schema: CatalogSchema,
) -> dict[str, Any]:
    """Merge all graph @ART rows into USR49 (preserves existing overrides)."""
    if not schema.burn_usr_key:
        return {"exit_code": 0, "skipped": True, "reason": "no_burn_usr_key"}
    arts = arts_from_session(session, schema)
    if not arts:
        return {"exit_code": 0, "skipped": True, "reason": "no_arts_on_graph"}
    line = build_usr_burn_update(session, arts, schema)
    if not line:
        return {"exit_code": 2, "errors": [f"missing {schema.burn_usr_key} on graph"]}
    code, errs = graph_update(session, [line])
    if code != 0 or errs:
        return {"exit_code": 2, "errors": errs or ["burn sync failed"]}
    return {"exit_code": 0, "art_count": len(arts)}


def _max_art_num(base: list[dict[str, str]], schema: CatalogSchema) -> int:
    nums: list[int] = []
    plen = len(schema.id_prefix)
    for art in base:
        aid = art.get("id", "")
        if aid.startswith(schema.id_prefix) and aid[plen:].isdigit():
            nums.append(int(aid[plen:]))
    return max(nums) if nums else 0


def _wire_example(schema: CatalogSchema) -> str:
    cols = "|".join(
        f"{schema.id_prefix}<n>" if c == "id" else f"<{c}>"
        for c in schema.wire_columns
    )
    return f"@ART: {cols}"


def build_expand_prompt(
    base: list[dict[str, str]],
    schema: CatalogSchema,
    *,
    need_count: int,
    seed: int | None = None,
) -> tuple[str, str]:
    name_key = _name_field(schema)
    existing_ids = ", ".join(a["id"] for a in base)
    existing_names = "、".join(a.get(name_key, "") for a in base[:40])
    if len(base) > 40:
        existing_names += f"…（共 {len(base)} 項）"
    mins = schema.min_slots
    kinds = "、".join(sorted(schema.valid_kinds))
    tiers = "、".join(sorted(schema.valid_tiers, key=lambda t: list(schema.valid_tiers).index(t)))
    band_lines = [
        f"{t}{schema.tier_coeff_bands[t][0]}-{schema.tier_coeff_bands[t][1]}"
        for t in schema.valid_tiers
        if t in schema.tier_coeff_bands
    ]
    slot_rules = "; ".join(
        f"{k}→{v}" for k, v in sorted(schema.kind_to_slot.items())
    )
    system = f"""你是「{schema.universe_label}」的功法／能力譜資料生成器（僅資料列，非正文）。
規則：
- 只輸出 @ART: 開頭的 wire 列，每行一項；禁 markdown、禁解釋、禁 JSON
- 格式範例：{_wire_example(schema)}
- {schema.kind_field} ∈ {{{kinds}}}；{schema.tier_field} ∈ {{{tiers}}}
- {schema.coeff_field} 須落在對應梯帶：{"；".join(band_lines)}
- {schema.content_rules}
- 槽位：{slot_rules}
- 新 id 勿與既有重複；名稱勿重複"""
    if schema.expand_extra_rules:
        system += f"\n- {schema.expand_extra_rules}"
    user = f"""既有 id：{existing_ids}
既有名稱（部分）：{existing_names}

請再生成 **{need_count}** 項**不重複**的 @ART 列。
各槽至少（含既有）：{mins}
新 id 建議從 {schema.id_prefix}{_max_art_num(base, schema) + 1} 起連號。
"""
    if seed is not None:
        user += f"\n隨機種子（可重現）：{seed}\n"
    return system, user


def expand_martial_catalog(
    session: str,
    schema: CatalogSchema,
    *,
    target_count: int = 80,
    llm_complete: Callable[[str, str], str],
    seed: int | None = None,
) -> dict[str, Any]:
    """Call LLM to grow @ART on session graph until target_count."""
    base = arts_from_session(session, schema)
    if len(base) >= target_count:
        return {
            "exit_code": 0,
            "skipped": True,
            "reason": "already_at_target",
            "art_count": len(base),
            "added": 0,
        }

    need = target_count - len(base)
    mins = schema.min_slots
    system, user = build_expand_prompt(base, schema, need_count=need, seed=seed)
    raw = llm_complete(system, user)
    candidates = parse_catalog_md(raw, schema)
    merged, val_errors = merge_arts(base, candidates, schema)
    new_arts = [a for a in merged if a["id"] not in {b["id"] for b in base}]

    counts = slot_counts(merged, schema)
    shortfall = {k: max(0, mins.get(k, 0) - counts.get(k, 0)) for k in mins}
    if shortfall and any(shortfall.values()) and len(new_arts) < need:
        extra_need = sum(shortfall.values())
        sys2, user2 = build_expand_prompt(merged, schema, need_count=extra_need, seed=seed)
        user2 += f"\n各槽仍缺：{shortfall}。請優先補缺槽。\n"
        raw2 = llm_complete(sys2, user2)
        merged2, val_errors2 = merge_arts(merged, parse_llm_catalog_text(raw2, schema), schema)
        val_errors.extend(val_errors2)
        new_arts = [a for a in merged2 if a["id"] not in {b["id"] for b in base}]
        merged = merged2

    if not new_arts:
        return {
            "exit_code": 2,
            "errors": val_errors or ["LLM returned no valid new @ART rows"],
            "art_count": len(base),
            "added": 0,
            "llm_sample": raw[:500],
        }

    lines = [art_to_wire(a, schema) for a in new_arts]
    ing = ingest_lines(session, lines)
    if ing.get("exit_code", 1) != 0:
        return {
            "exit_code": 2,
            "errors": ing.get("errors", ["ingest failed"]),
            "added": 0,
        }

    burn_line = build_usr_burn_update(session, new_arts, schema)
    if burn_line:
        graph_update(session, [burn_line])

    final = arts_from_session(session, schema)
    return {
        "exit_code": 0,
        "added": len(new_arts),
        "art_count": len(final),
        "slot_counts": slot_counts(final, schema),
        "validation_warnings": val_errors[:20],
        "skipped": False,
    }


def parse_llm_catalog_text(text: str, schema: CatalogSchema) -> list[dict[str, str]]:
    return parse_catalog_md(text, schema)
