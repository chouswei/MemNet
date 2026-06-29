"""Opening catalog loadout: per-slot picks and schema-driven graph wiring."""

from __future__ import annotations

import hashlib
import random
import re
from pathlib import Path
from typing import Any

from novel_mcp.catalog_schema import (
    CatalogSchema,
    art_from_parts,
    opening_offer_roll_usr_key,
    opening_offer_usr_key,
    opening_rank,
    read_catalog_schema,
    setup_scene_usr_key,
    slot_for_kind,
    slot_label,
    slot_order,
)
from novel_mcp.setup_constants import (
    DEFAULT_PICK_OFFER_MAX,
    DEFAULT_PICK_OFFER_MIN,
    OPENING_CATALOG_MD_KEY,
    OPENING_OFFER_EMPTY,
    SENTINEL,
    SETUP_PICK_OFFER_COUNT_KEY,
    SETUP_PICK_OFFER_SEED_KEY,
)
from novel_mcp.setup_graph import (
    first_plr_id,
    ensure_usr_row,
    graph_apply_setup_lines,
    graph_update,
    list_tag_data_rows,
    read_get_body,
    read_usr_by_key,
    resolve_catalog_path,
    setup_commit_errors,
    usr_id_for_key,
)

_ART_LINE_RE = re.compile(r"^@ART:\s*(.+)$", re.MULTILINE)
_FENCE_RE = re.compile(r"```text\s*\n(.*?)```", re.DOTALL)


def _require_schema(
    session: str | None,
    *,
    workspace_root_path: str | None = None,
) -> tuple[CatalogSchema | None, list[str]]:
    schema = read_catalog_schema(session, workspace_root_path=workspace_root_path)
    if schema is None:
        return None, ["missing catalog_schema on graph (bootstrap with instance catalog_schema)"]
    return schema, []


def parse_catalog_md(text: str, schema: CatalogSchema) -> list[dict[str, str]]:
    arts: list[dict[str, str]] = []
    seen: set[str] = set()
    blocks = [_ART_LINE_RE.findall(text)]
    for fence in _FENCE_RE.findall(text):
        blocks.append(_ART_LINE_RE.findall(fence))
    prefix = schema.id_prefix
    for group in blocks:
        for body in group:
            parts = [p.strip() for p in body.strip().split("|")]
            if not parts or not parts[0].startswith(prefix):
                continue
            if parts[0] in seen:
                continue
            seen.add(parts[0])
            arts.append(art_from_parts(parts, schema))
    return arts


def load_catalog_from_path(path: Path, schema: CatalogSchema) -> list[dict[str, str]]:
    return parse_catalog_md(path.read_text(encoding="utf-8"), schema)


def arts_from_session(
    session: str | None,
    schema: CatalogSchema,
) -> list[dict[str, str]]:
    if not session:
        return []
    rows = list_tag_data_rows(session, "ART")
    arts: list[dict[str, str]] = []
    for parts in rows:
        if not parts or not parts[0].startswith(schema.id_prefix):
            continue
        arts.append(art_from_parts(parts, schema))
    return arts


def _load_catalog_arts(
    session: str | None,
    schema: CatalogSchema,
    *,
    workspace_root_path: str | None = None,
) -> tuple[list[dict[str, str]], str | None, list[str]]:
    rel = read_usr_by_key(session, OPENING_CATALOG_MD_KEY) if session else None
    graph_arts = arts_from_session(session, schema)
    if graph_arts:
        return graph_arts, rel, []
    try:
        path = resolve_catalog_path(session, workspace_root_path)
    except ValueError as exc:
        return [], None, [str(exc)]
    if not path.is_file():
        return [], rel, [f"catalog not found: {path}"]
    return load_catalog_from_path(path, schema), rel, []


def slot_for_art(art: dict[str, str], schema: CatalogSchema) -> str | None:
    return slot_for_kind(art.get(schema.kind_field, ""), schema)


def _opening_gift_from_session(
    session: str | None,
    usr_key: str | None,
) -> dict[str, Any] | None:
    """Parse optional instance gift USR (`name;rank;no_pick` shape)."""
    if not usr_key or not session:
        return None
    raw = read_usr_by_key(session, usr_key)
    if not raw or raw == SENTINEL:
        return None
    parts = [p.strip() for p in raw.split(";")]
    name = parts[0] if parts else ""
    rank = parts[1] if len(parts) > 1 else ""
    selectable = True
    if len(parts) > 2:
        selectable = parts[2].lower() not in ("no_pick", "false", "0", "不可選")
    return {"name": name, "rank": rank, "selectable": selectable}


def catalog_slots(arts: list[dict[str, str]], schema: CatalogSchema) -> dict[str, Any]:
    order = slot_order(schema)
    buckets: dict[str, list[dict[str, str]]] = {s: [] for s in order}
    for art in arts:
        slot = slot_for_art(art, schema)
        if slot and slot in buckets:
            buckets[slot].append(art)
    out: dict[str, Any] = {}
    for s in order:
        entry: dict[str, Any] = {
            "label": slot_label(schema, s),
            "arts": buckets[s],
        }
        if s == schema.loadout.mobility_stat_slot:
            entry["wire_kind"] = schema.qinggong_wire_kind
        out[s] = entry
    return out


_PICK_OFFER_COUNT_RE = re.compile(r"^(\d+)\s*-\s*(\d+)$")


def parse_pick_offer_count(raw: str | None) -> tuple[int, int]:
    """Parse seed USR `setup_pick_offer_count` (e.g. `5-9`)."""
    if not raw or raw in (SENTINEL, OPENING_OFFER_EMPTY):
        return DEFAULT_PICK_OFFER_MIN, DEFAULT_PICK_OFFER_MAX
    m = _PICK_OFFER_COUNT_RE.match(raw.strip())
    if not m:
        return DEFAULT_PICK_OFFER_MIN, DEFAULT_PICK_OFFER_MAX
    lo, hi = int(m.group(1)), int(m.group(2))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def _rng_for_slot(session: str | None, slot: str) -> random.Random:
    extra = read_usr_by_key(session, SETUP_PICK_OFFER_SEED_KEY) or ""
    roll_n = read_usr_by_key(session, opening_offer_roll_usr_key(slot)) or "0"
    base = f"{session or 'local'}:{slot}:{extra}:{roll_n}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _read_stored_offer_ids(session: str | None, slot: str) -> list[str] | None:
    key = opening_offer_usr_key(slot)
    if not session:
        return None
    raw = read_usr_by_key(session, key)
    if not raw or raw in (SENTINEL, OPENING_OFFER_EMPTY, "-"):
        return None
    ids = [p.strip() for p in raw.split(";") if p.strip()]
    return ids or None


def _preferred_offer_usr_id(key: str) -> str | None:
    return {
        "opening_offer_neigong": "USR74",
        "opening_offer_martial": "USR75",
        "opening_offer_qinggong": "USR76",
    }.get(key)


def _persist_offer_ids(session: str | None, slot: str, ids: list[str]) -> list[str]:
    key = opening_offer_usr_key(slot)
    if not session:
        return ["missing session for offer persist"]
    pref = _preferred_offer_usr_id(key)
    preferred = (pref,) if pref else ()
    uid = ensure_usr_row(
        session, key, initial=OPENING_OFFER_EMPTY, preferred_ids=preferred
    )
    if not uid:
        return [f"missing USR row for key {key} (seed opening_offer_* rows)"]
    value = ";".join(ids) if ids else OPENING_OFFER_EMPTY
    code, errs = graph_update(
        session, [f"@USR: {uid}|{key}|{value}|persistent"]
    )
    if code != 0 or errs:
        return errs or ["offer persist failed"]
    return []


def _bump_offer_roll(session: str | None, slot: str) -> list[str]:
    if not session:
        return ["missing session for offer reroll"]
    roll_key = opening_offer_roll_usr_key(slot)
    raw = read_usr_by_key(session, roll_key) or "0"
    try:
        n = int(raw.strip()) + 1
    except ValueError:
        n = 1
    uid = ensure_usr_row(session, roll_key, initial="0")
    if not uid:
        return [f"missing USR row for key {roll_key}"]
    code, errs = graph_update(
        session, [f"@USR: {uid}|{roll_key}|{n}|persistent"]
    )
    if code != 0 or errs:
        return errs or ["offer roll bump failed"]
    return []


def reroll_opening_offers(
    session: str | None,
    slot: str,
    *,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    """Re-roll offered ART ids for the current pick slot (before commit)."""
    from novel_mcp.player_setup import read_player_setup

    block = setup_commit_errors(session, setup_complete=False)
    if block:
        return {"exit_code": 2, "errors": block}

    schema, schema_err = _require_schema(session, workspace_root_path=workspace_root_path)
    if schema_err or schema is None:
        return {"exit_code": 2, "errors": schema_err or ["missing catalog_schema"]}

    order = slot_order(schema)
    if slot not in order:
        return {"exit_code": 2, "errors": [f"invalid slot: {slot}"]}

    raw = read_usr_by_key(session, "opening_arts")
    picks = _parse_opening_arts(raw, len(order))
    expected = _next_slot(picks, order)
    if expected != slot:
        return {
            "exit_code": 2,
            "errors": [f"expected slot {expected}, got {slot}"],
        }

    setup = read_player_setup(session, workspace_root_path=workspace_root_path)
    next_action = (setup.get("setup_guidance") or {}).get("next_action", "")
    if next_action != f"pick_{slot}":
        return {
            "exit_code": 2,
            "errors": [f"next_action is {next_action!r}, not pick_{slot}"],
        }

    arts_full, _, load_err = _load_catalog_arts(
        session, schema, workspace_root_path=workspace_root_path
    )
    if load_err:
        return {"exit_code": 2, "errors": load_err}

    pool = [a for a in arts_full if slot_for_art(a, schema) == slot]
    if not pool:
        return {"exit_code": 2, "errors": [f"empty pool for slot {slot}"]}

    bump_errs = _bump_offer_roll(session, slot)
    if bump_errs:
        return {"exit_code": 2, "errors": bump_errs}

    lo, hi = parse_pick_offer_count(read_usr_by_key(session, SETUP_PICK_OFFER_COUNT_KEY))
    ids = roll_slot_offers(session, slot, pool, lo=lo, hi=hi)
    persist_errs = _persist_offer_ids(session, slot, ids)
    if persist_errs:
        return {"exit_code": 2, "errors": persist_errs}

    cat = read_opening_catalog(session, workspace_root_path=workspace_root_path)
    slot_data = (cat.get("slots") or {}).get(slot) or {}
    return {
        "exit_code": cat.get("exit_code", 0),
        "slot": slot,
        "offer_ids": slot_data.get("offer_ids") or ids,
        "offer_count": len(ids),
        "slots": cat.get("slots") or {},
        "errors": cat.get("errors") or [],
    }


def roll_slot_offers(
    session: str | None,
    slot: str,
    pool: list[dict[str, str]],
    *,
    lo: int,
    hi: int,
    rng: random.Random | None = None,
) -> list[str]:
    """Sample `lo`–`hi` distinct ART ids from `pool` (capped by pool size)."""
    if not pool:
        return []
    cap = len(pool)
    n_lo = max(1, min(lo, cap))
    n_hi = max(n_lo, min(hi, cap))
    rng = rng or _rng_for_slot(session, slot)
    count = rng.randint(n_lo, n_hi)
    picked = rng.sample(pool, count)
    return [a["id"] for a in picked]


def ensure_slot_offers(
    session: str | None,
    slot: str,
    pool: list[dict[str, str]],
    *,
    roll: bool = True,
) -> tuple[list[str], list[str]]:
    """Return offered ART ids for slot; roll and persist on first access when `roll`."""
    stored = _read_stored_offer_ids(session, slot)
    if stored is not None:
        return stored, []
    if not roll or not session:
        return [a["id"] for a in pool], []
    lo, hi = parse_pick_offer_count(read_usr_by_key(session, SETUP_PICK_OFFER_COUNT_KEY))
    ids = roll_slot_offers(session, slot, pool, lo=lo, hi=hi)
    errs = _persist_offer_ids(session, slot, ids)
    return ids, errs


def _arts_by_id(arts: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {a["id"]: a for a in arts}


def _parse_opening_arts(raw: str | None, n_slots: int) -> list[str]:
    if not raw or raw == SENTINEL:
        return [SENTINEL] * n_slots
    parts = [p.strip() for p in raw.split(";")]
    while len(parts) < n_slots:
        parts.append(SENTINEL)
    return parts[:n_slots]


def _next_slot(picks: list[str], order: tuple[str, ...]) -> str | None:
    for slot, pick in zip(order, picks, strict=True):
        if pick == SENTINEL:
            return slot
    return None


def _apply_offers_to_slots(
    session: str | None,
    slots: dict[str, Any],
    schema: CatalogSchema,
    *,
    roll_slot: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Replace each slot's `arts` with offered subset; roll current pick slot if needed."""
    errors: list[str] = []
    order = slot_order(schema)
    next_slot = roll_slot
    if next_slot is None and session:
        n = len(order)
        raw = read_usr_by_key(session, "opening_arts")
        next_slot = _next_slot(_parse_opening_arts(raw, n), order)

    out: dict[str, Any] = {}
    for slot in order:
        bucket = dict(slots.get(slot, {}))
        pool = list(bucket.get("arts") or [])
        should_roll = slot == next_slot
        offer_ids, errs = ensure_slot_offers(
            session, slot, pool, roll=should_roll
        )
        errors.extend(errs)
        by_id = _arts_by_id(pool)
        offered = [by_id[aid] for aid in offer_ids if aid in by_id]
        bucket["arts"] = offered
        bucket["offer_ids"] = offer_ids
        bucket["offer_count"] = len(offer_ids)
        bucket["pool_count"] = len(pool)
        out[slot] = bucket
    return out, errors


def read_opening_catalog(
    session: str | None,
    *,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    schema, schema_err = _require_schema(session, workspace_root_path=workspace_root_path)
    if schema_err:
        return {
            "exit_code": 2,
            "errors": schema_err,
            "catalog_path": None,
            "slots": {},
            "source": "none",
        }
    assert schema is not None
    arts, rel, errors = _load_catalog_arts(
        session, schema, workspace_root_path=workspace_root_path
    )
    if errors:
        return {
            "exit_code": 2,
            "errors": errors,
            "catalog_path": rel,
            "slots": {},
            "source": "none",
        }
    on_graph = bool(session and arts_from_session(session, schema))
    raw_slots = catalog_slots(arts, schema)
    slots, offer_errs = _apply_offers_to_slots(session, raw_slots, schema)
    lo, hi = parse_pick_offer_count(
        read_usr_by_key(session, SETUP_PICK_OFFER_COUNT_KEY) if session else None
    )
    if offer_errs:
        return {
            "exit_code": 2,
            "errors": offer_errs,
            "catalog_path": rel,
            "slots": slots,
            "source": "graph" if on_graph else "md",
        }
    return {
        "exit_code": 0,
        "catalog_path": rel,
        "slots": slots,
        "art_count": len(arts),
        "pick_offer_count": {"min": lo, "max": hi},
        "source": "graph" if on_graph else "md",
        "errors": [],
    }


read_martial_catalog = read_opening_catalog


def _scene_for_slot(session: str | None, slot: str) -> dict[str, str]:
    raw = read_usr_by_key(session, setup_scene_usr_key(slot)) if session else None
    if not raw or raw == SENTINEL:
        return {"title": "", "hint": ""}
    if ";" in raw:
        title, hint = raw.split(";", 1)
        return {"title": title, "hint": hint}
    return {"title": raw, "hint": ""}


def _art_by_id(catalog: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {a["id"]: a for a in catalog}


def validate_slot_pick(
    slot: str,
    art_id: str,
    catalog: list[dict[str, str]],
    schema: CatalogSchema,
) -> list[str]:
    arts = _art_by_id(catalog)
    if art_id not in arts:
        return [f"unknown art_id: {art_id}"]
    actual = slot_for_art(arts[art_id], schema)
    if actual != slot:
        kind = arts[art_id].get(schema.kind_field, "")
        return [f"slot_{slot}: {art_id} is {kind}, not {slot_label(schema, slot)}"]
    return []


def validate_opening_picks(
    art_ids: list[str],
    catalog: list[dict[str, str]],
    schema: CatalogSchema,
) -> list[str]:
    order = slot_order(schema)
    n = len(order)
    if len(art_ids) != n:
        return [f"opening_arts: must have exactly {n} ids"]
    if len(set(art_ids)) != n:
        return ["opening_arts: ids must be distinct"]
    errors: list[str] = []
    for slot, art_id in zip(order, art_ids, strict=True):
        errors.extend(validate_slot_pick(slot, art_id, catalog, schema))
    return errors


def read_opening_loadout(
    session: str | None,
    *,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    schema, schema_err = _require_schema(session, workspace_root_path=workspace_root_path)
    if not schema:
        return {
            "exit_code": 0,
            "slots": {},
            "next_slot": None,
            "complete": False,
            "errors": list(schema_err or []),
        }
    order = slot_order(schema)
    n = len(order)
    raw = read_usr_by_key(session, "opening_arts")
    picks = _parse_opening_arts(raw, n)
    slots_out: dict[str, Any] = {}
    for slot, pick in zip(order, picks, strict=True):
        slots_out[slot] = {
            "label": slot_label(schema, slot) if schema else slot,
            "pick": None if pick == SENTINEL else pick,
            "scene": _scene_for_slot(session, slot),
        }
    next_slot = _next_slot(picks, order)
    complete = next_slot is None
    errors: list[str] = list(schema_err or [])
    if next_slot and session and schema:
        arts_full, _, load_err = _load_catalog_arts(
            session, schema, workspace_root_path=workspace_root_path
        )
        if load_err:
            errors.extend(load_err)
        else:
            pool = [a for a in arts_full if slot_for_art(a, schema) == next_slot]
            offer_ids, offer_errs = ensure_slot_offers(
                session, next_slot, pool, roll=True
            )
            errors.extend(offer_errs)
            by_id = _arts_by_id(pool)
            slots_out[next_slot]["offers"] = [
                by_id[aid] for aid in offer_ids if aid in by_id
            ]
            slots_out[next_slot]["offer_count"] = len(offer_ids)
    if complete and schema:
        arts_full, _, load_err = _load_catalog_arts(
            session, schema, workspace_root_path=workspace_root_path
        )
        if load_err:
            errors.extend(load_err)
        elif arts_full:
            errors = validate_opening_picks(
                [p for p in picks if p != SENTINEL],
                arts_full,
                schema,
            )
    return {
        "exit_code": 0,
        "slots": slots_out,
        "next_slot": next_slot,
        "complete": complete and not errors,
        "errors": errors,
        **(
            {
                "opening_gift": _opening_gift_from_session(
                    session,
                    schema.loadout.opening_gift_usr_key if schema else None,
                )
            }
            if schema and schema.loadout.opening_gift_usr_key
            else {}
        ),
    }


def _proficiency_id(plr_id: str, index: int, schema: CatalogSchema) -> str:
    lc = schema.loadout
    tpl = lc.proficiency_id_template or f"PROF{plr_id}{index}"
    suffix = plr_id.replace("P", "")
    return tpl.replace("{plr_suffix}", suffix).replace("{index}", str(index))


def _wire_template_context(
    plr_id: str,
    art_ids: tuple[str, ...],
    names: list[str],
    schema: CatalogSchema,
) -> dict[str, str]:
    ctx: dict[str, str] = {"plr": plr_id}
    for i, aid in enumerate(art_ids):
        ctx[f"art{i}"] = aid
        ctx[f"name{i}"] = names[i]
        ctx[f"prof{i + 1}"] = _proficiency_id(plr_id, i + 1, schema)
    return ctx


def _format_wire_line(template: str, ctx: dict[str, str]) -> str:
    line = template
    for key, val in ctx.items():
        line = line.replace("{" + key + "}", val)
    return line


def _build_skills_line(
    session: str | None,
    names: list[str],
    ranks: list[str],
    schema: CatalogSchema,
) -> str:
    lc = schema.loadout
    parts: list[str] = []
    gift_key = lc.opening_gift_usr_key
    if gift_key:
        gift = _opening_gift_from_session(session, gift_key)
        if gift and gift.get("name"):
            rank = gift.get("rank") or ""
            label = gift["name"]
            parts.append(f"{label}{rank}" if rank else label)
    existing = read_usr_by_key(session, "skills") if session else None
    if existing and existing != SENTINEL and existing not in parts:
        parts.append(existing)
    for name, rank in zip(names, ranks, strict=True):
        parts.append(f"{name}{rank}")
    return lc.skills_separator.join(parts)


def _wire_opening_loadout(
    session: str | None,
    plr_id: str,
    art_ids: tuple[str, ...],
    catalog: list[dict[str, str]],
    schema: CatalogSchema,
) -> list[str]:
    lc = schema.loadout
    order = slot_order(schema)
    arts = _art_by_id(catalog)
    name_key = schema.wire_columns[1] if len(schema.wire_columns) > 1 else "name"
    names = [arts[aid][name_key] for aid in art_ids]
    ranks = [opening_rank(schema, slot) for slot in order]
    lines: list[str] = []

    if lc.proficiency_tag:
        for i, art_id in enumerate(art_ids, start=1):
            ea_id = f"EA{plr_id}{i}"
            prof_id = _proficiency_id(plr_id, i, schema)
            lines.append(
                f"@EDG: {ea_id}|{plr_id}|{lc.knows_relation}|{art_id}||persistent"
            )
            lines.append(
                f"@{lc.proficiency_tag}: {prof_id}|{plr_id}|{art_id}|"
                f"{lc.proficiency_rank}|{lc.proficiency_mastery}|常駐"
            )
            lines.append(
                f"@EDG: EM{plr_id}{i}|{plr_id}|{lc.has_proficiency_relation}|"
                f"{prof_id}||persistent"
            )
            lines.append(
                f"@EDG: EM{plr_id}{i}a|{prof_id}|{lc.for_art_relation}|"
                f"{art_id}||persistent"
            )

    if lc.body_stat_tag:
        for i, slot in enumerate(order):
            stat_id = (
                lc.body_stat_ids[i]
                if i < len(lc.body_stat_ids)
                else f"{lc.body_stat_tag}{i + 1:02d}"
            )
            label = schema.body_stat_labels.get(slot, slot)
            if slot == lc.mobility_stat_slot:
                label = schema.qinggong_wire_kind
            rank = opening_rank(schema, slot)
            mastery = lc.body_stat_mastery.get(slot, lc.proficiency_mastery)
            lines.append(
                f"@{lc.body_stat_tag}: {stat_id}|{plr_id}|{label}|{rank}|{mastery}|常駐"
            )

    ctx = _wire_template_context(plr_id, art_ids, names, schema)
    for template in lc.extra_wire_lines:
        lines.append(_format_wire_line(template, ctx))

    skills = _build_skills_line(session, names, ranks, schema)
    skills_uid = usr_id_for_key(session, "skills") if session else None
    if skills_uid:
        lines.append(f"@USR: {skills_uid}|skills|{skills}|persistent")

    plr_body = read_get_body(session, plr_id)
    if plr_body:
        parts = plr_body.split("|")
        if len(parts) >= 7:
            body = parts[6]
            for slot_key, rank in zip(order, ranks, strict=True):
                label = schema.body_stat_labels.get(slot_key, slot_key)
                token = f"{label}:{rank}"
                if f"{label}:" in body:
                    body = re.sub(rf"{label}:[^；;]+", token, body, count=1)
            parts[6] = body
            lines.append(
                f"@PLR: {parts[0]}|{parts[1]}|{parts[2]}|{parts[3]}|"
                f"{parts[4]}|{skills}|{parts[6]}"
            )

    return lines


def _set_usr58(picks: list[str]) -> str:
    return f"@USR: USR58|opening_arts|{';'.join(picks)}|persistent"


def commit_opening_pick(
    session: str | None,
    slot: str,
    art_id: str,
    *,
    plr_id: str | None = None,
    workspace_root_path: str | None = None,
    setup_complete: bool = False,
) -> dict[str, Any]:
    from novel_mcp.player_setup import read_player_setup

    block = setup_commit_errors(session, setup_complete=setup_complete)
    if block:
        return {"exit_code": 2, "errors": block}

    schema, schema_err = _require_schema(session, workspace_root_path=workspace_root_path)
    if schema_err or schema is None:
        return {"exit_code": 2, "errors": schema_err or ["missing catalog_schema"]}

    order = slot_order(schema)
    if slot not in order:
        return {"exit_code": 2, "errors": [f"invalid slot: {slot}"]}

    cat_resp = read_opening_catalog(session, workspace_root_path=workspace_root_path)
    if cat_resp.get("exit_code") != 0:
        return {"exit_code": 2, "errors": cat_resp.get("errors", ["catalog error"])}

    arts_full, _, load_err = _load_catalog_arts(
        session, schema, workspace_root_path=workspace_root_path
    )
    if load_err:
        return {"exit_code": 2, "errors": load_err}

    val_err = validate_slot_pick(slot, art_id, arts_full, schema)
    if val_err:
        return {"exit_code": 2, "errors": val_err}

    offer_ids = (cat_resp.get("slots", {}).get(slot) or {}).get("offer_ids") or []
    if offer_ids and art_id not in offer_ids:
        return {
            "exit_code": 2,
            "errors": [f"{art_id} not in offered picks for {slot}"],
        }

    raw = read_usr_by_key(session, "opening_arts")
    picks = _parse_opening_arts(raw, len(order))
    expected = _next_slot(picks, order)
    if expected != slot:
        return {
            "exit_code": 2,
            "errors": [f"expected slot {expected}, got {slot}"],
        }

    idx = order.index(slot)
    picks[idx] = art_id
    lines = [_set_usr58(picks)]

    if _next_slot(picks, order) is None:
        pid = plr_id or first_plr_id(session)
        if not pid:
            return {"exit_code": 2, "errors": ["no PLR row in graph"]}
        pick_err = validate_opening_picks(picks, arts_full, schema)
        if pick_err:
            return {"exit_code": 2, "errors": pick_err}
        lines.extend(
            _wire_opening_loadout(session, pid, tuple(picks), arts_full, schema)
        )

    apply_fn = graph_apply_setup_lines if _next_slot(picks, order) is None else graph_update
    code, upd_err = apply_fn(session, lines)
    if code != 0:
        return {"exit_code": 2, "errors": upd_err or ["update failed"]}

    return read_player_setup(session, workspace_root_path=workspace_root_path)


def commit_opening_loadout(
    session: str | None,
    art_ids: list[str],
    *,
    plr_id: str | None = None,
    workspace_root_path: str | None = None,
    setup_complete: bool = False,
) -> dict[str, Any]:
    from novel_mcp.player_setup import read_player_setup

    schema, schema_err = _require_schema(session, workspace_root_path=workspace_root_path)
    if schema_err or schema is None:
        return {"exit_code": 2, "errors": schema_err or ["missing catalog_schema"]}

    order = slot_order(schema)
    if len(art_ids) != len(order):
        return {
            "exit_code": 2,
            "errors": [f"art_ids must have length {len(order)}"],
        }

    for slot, art_id in zip(order, art_ids, strict=True):
        result = commit_opening_pick(
            session,
            slot,
            art_id,
            plr_id=plr_id,
            workspace_root_path=workspace_root_path,
            setup_complete=setup_complete,
        )
        if result.get("exit_code") != 0:
            return result
        setup_complete = bool(result.get("setup_complete"))

    return read_player_setup(session, workspace_root_path=workspace_root_path)


def has_proficiency_edges(
    session: str | None,
    plr_id: str | None = None,
    *,
    workspace_root_path: str | None = None,
) -> bool:
    pid = plr_id or first_plr_id(session)
    if not pid or not session:
        return False
    schema = read_catalog_schema(session, workspace_root_path=workspace_root_path)
    relation = (
        schema.loadout.has_proficiency_relation
        if schema
        else "has_proficiency"
    )
    for row in list_tag_data_rows(session, "EDG"):
        if len(row) >= 4 and row[1] == pid and row[2] == relation:
            return True
    return False


has_mwu_edges = has_proficiency_edges
