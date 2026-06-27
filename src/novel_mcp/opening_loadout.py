"""Opening martial loadout: catalog, per-slot picks, wire on 3rd pick."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from novel_mcp.catalog_schema import (
    CatalogSchema,
    art_from_parts,
    art_to_wire,
    read_catalog_schema,
    slot_for_kind,
)
from novel_mcp.setup_constants import (
    MWU_RANK,
    SENTINEL,
    SLOT_LABELS,
    SLOT_ORDER,
    SLOT_SCENE_USR,
    WUX_RANK_MARTIAL,
    WUX_RANK_NEIGONG,
    WUX_RANK_QINGGONG,
)
from novel_mcp.setup_graph import (
    first_plr_id,
    graph_apply_setup_lines,
    graph_update,
    list_tag_data_rows,
    read_get_body,
    read_usr_by_key,
    read_usr_record,
    resolve_catalog_path,
    setup_commit_errors,
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
    rel = read_usr_by_key(session, "martial_catalog_md") if session else None
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


def catalog_slots(arts: list[dict[str, str]], schema: CatalogSchema) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, str]]] = {
        "neigong": [],
        "martial": [],
        "qinggong": [],
    }
    for art in arts:
        slot = slot_for_art(art, schema)
        if slot:
            buckets[slot].append(art)
    return {
        "neigong": {"label": SLOT_LABELS["neigong"], "arts": buckets["neigong"]},
        "martial": {"label": SLOT_LABELS["martial"], "arts": buckets["martial"]},
        "qinggong": {
            "label": SLOT_LABELS["qinggong"],
            "aliases": [schema.qinggong_wire_kind],
            "wire_kind": schema.qinggong_wire_kind,
            "arts": buckets["qinggong"],
        },
    }


def read_martial_catalog(
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
    return {
        "exit_code": 0,
        "catalog_path": rel,
        "slots": catalog_slots(arts, schema),
        "art_count": len(arts),
        "source": "graph" if on_graph else "md",
        "errors": [],
    }


def _parse_opening_arts(raw: str | None) -> list[str]:
    if not raw or raw == SENTINEL:
        return [SENTINEL, SENTINEL, SENTINEL]
    parts = [p.strip() for p in raw.split(";")]
    while len(parts) < 3:
        parts.append(SENTINEL)
    return parts[:3]


def _next_slot(picks: list[str]) -> str | None:
    for slot, pick in zip(SLOT_ORDER, picks, strict=True):
        if pick == SENTINEL:
            return slot
    return None


def _scene_for_slot(session: str | None, slot: str) -> dict[str, str]:
    uid = SLOT_SCENE_USR.get(slot, "")
    rec = read_usr_record(session, uid) if uid else None
    if rec and len(rec) >= 3:
        value = rec[2]
        if ";" in value:
            title, hint = value.split(";", 1)
            return {"title": title, "hint": hint}
        return {"title": value, "hint": ""}
    return {"title": "", "hint": ""}


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
        return [f"slot_{slot}: {art_id} is {kind}, not {SLOT_LABELS.get(slot, slot)}"]
    return []


def validate_opening_picks(
    art_ids: list[str],
    catalog: list[dict[str, str]],
    schema: CatalogSchema,
) -> list[str]:
    if len(art_ids) != 3:
        return ["opening_arts: must have exactly 3 ids"]
    if len(set(art_ids)) != 3:
        return ["opening_arts: ids must be distinct"]
    errors: list[str] = []
    for slot, art_id in zip(SLOT_ORDER, art_ids, strict=True):
        errors.extend(validate_slot_pick(slot, art_id, catalog, schema))
    return errors


def read_opening_loadout(
    session: str | None,
    *,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    raw = read_usr_by_key(session, "opening_arts")
    picks = _parse_opening_arts(raw)
    slots_out: dict[str, Any] = {}
    for slot, pick in zip(SLOT_ORDER, picks, strict=True):
        slots_out[slot] = {
            "label": SLOT_LABELS[slot],
            "pick": None if pick == SENTINEL else pick,
            "scene": _scene_for_slot(session, slot),
        }
    next_slot = _next_slot(picks)
    complete = next_slot is None
    errors: list[str] = []
    if complete:
        cat_resp = read_martial_catalog(session, workspace_root_path=workspace_root_path)
        if cat_resp.get("exit_code") == 0:
            schema, _ = _require_schema(session, workspace_root_path=workspace_root_path)
            all_arts: list[dict[str, str]] = []
            for bucket in cat_resp.get("slots", {}).values():
                all_arts.extend(bucket.get("arts", []))
            if schema:
                errors = validate_opening_picks(
                    [p for p in picks if p != SENTINEL],
                    all_arts,
                    schema,
                )
    return {
        "exit_code": 0,
        "soul_library": {
            "name": "靈魂圖書館",
            "rank": "登峰造極",
            "selectable": False,
        },
        "slots": slots_out,
        "next_slot": next_slot,
        "complete": complete and not errors,
        "errors": errors,
    }


def _mwu_id(plr_id: str, index: int) -> str:
    suffix = plr_id.replace("P", "")
    return f"MWU{suffix}0{index}"


def _wire_opening_loadout(
    session: str | None,
    plr_id: str,
    art_ids: tuple[str, str, str],
    catalog: list[dict[str, str]],
    schema: CatalogSchema,
) -> list[str]:
    arts = _art_by_id(catalog)
    name_key = schema.wire_columns[1] if len(schema.wire_columns) > 1 else "name"
    names = [arts[aid][name_key] for aid in art_ids]
    lines: list[str] = []

    for i, art_id in enumerate(art_ids, start=1):
        ea_id = f"EA{plr_id}{i}"
        mwu_id = _mwu_id(plr_id, i)
        lines.append(f"@EDG: {ea_id}|{plr_id}|soul_knows|{art_id}||persistent")
        lines.append(
            f"@MWU: {mwu_id}|{plr_id}|{art_id}|{MWU_RANK}|1|常駐"
        )
        lines.append(f"@EDG: EM{plr_id}{i}|{plr_id}|has_mwu|{mwu_id}||persistent")
        lines.append(f"@EDG: EM{plr_id}{i}a|{mwu_id}|for_art|{art_id}||persistent")

    lines.append(
        f"@WUX: WUX01|{plr_id}|{schema.body_stat_labels['neigong']}|{WUX_RANK_NEIGONG}|0|常駐"
    )
    lines.append(
        f"@WUX: WUX02|{plr_id}|{schema.body_stat_labels['martial']}|{WUX_RANK_MARTIAL}|1|常駐"
    )
    lines.append(f"@WUX: WUX03|{plr_id}|{schema.qinggong_wire_kind}|{WUX_RANK_QINGGONG}|1|常駐")

    neigong_art = art_ids[0]
    lines.append(f"@USR: USR48|primary_neigong|{plr_id}={neigong_art}|persistent")
    lines.append(
        f"@EDG: EP50|{plr_id}|primary_neigong|{neigong_art}|{names[0]}主修|persistent"
    )

    mwu_nei = _mwu_id(plr_id, 1)
    lines.append(
        f"@USR: USR46|neigong_recover|{neigong_art};{mwu_nei};WUX01;半時辰一輪|persistent"
    )

    skills = (
        f"靈魂圖書館登峰造極、{names[0]}{MWU_RANK}、"
        f"{names[1]}{WUX_RANK_MARTIAL}、{names[2]}{WUX_RANK_QINGGONG}"
    )
    lines.append(f"@USR: USR04|skills|{skills}|persistent")

    plr_body = read_get_body(session, plr_id)
    if plr_body:
        parts = plr_body.split("|")
        if len(parts) >= 7:
            body = parts[6]
            labels = schema.body_stat_labels
            for slot_key, rank in (
                ("neigong", WUX_RANK_NEIGONG),
                ("martial", WUX_RANK_MARTIAL),
                ("qinggong", WUX_RANK_QINGGONG),
            ):
                label = labels.get(slot_key, slot_key)
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

    if slot not in SLOT_ORDER:
        return {"exit_code": 2, "errors": [f"invalid slot: {slot}"]}

    cat_resp = read_martial_catalog(session, workspace_root_path=workspace_root_path)
    if cat_resp.get("exit_code") != 0:
        return {"exit_code": 2, "errors": cat_resp.get("errors", ["catalog error"])}

    schema, schema_err = _require_schema(session, workspace_root_path=workspace_root_path)
    if schema_err or schema is None:
        return {"exit_code": 2, "errors": schema_err or ["missing catalog_schema"]}

    all_arts: list[dict[str, str]] = []
    for bucket in cat_resp.get("slots", {}).values():
        all_arts.extend(bucket.get("arts", []))

    val_err = validate_slot_pick(slot, art_id, all_arts, schema)
    if val_err:
        return {"exit_code": 2, "errors": val_err}

    raw = read_usr_by_key(session, "opening_arts")
    picks = _parse_opening_arts(raw)
    expected = _next_slot(picks)
    if expected != slot:
        return {
            "exit_code": 2,
            "errors": [f"expected slot {expected}, got {slot}"],
        }

    idx = SLOT_ORDER.index(slot)
    picks[idx] = art_id
    lines = [_set_usr58(picks)]

    if _next_slot(picks) is None:
        pid = plr_id or first_plr_id(session)
        if not pid:
            return {"exit_code": 2, "errors": ["no PLR row in graph"]}
        pick_err = validate_opening_picks(picks, all_arts, schema)
        if pick_err:
            return {"exit_code": 2, "errors": pick_err}
        lines.extend(
            _wire_opening_loadout(session, pid, tuple(picks), all_arts, schema)
        )

    apply_fn = graph_apply_setup_lines if _next_slot(picks) is None else graph_update
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

    if len(art_ids) != 3:
        return {"exit_code": 2, "errors": ["art_ids must have length 3"]}

    for slot, art_id in zip(SLOT_ORDER, art_ids, strict=True):
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


def has_mwu_edges(session: str | None, plr_id: str | None = None) -> bool:
    pid = plr_id or first_plr_id(session)
    if not pid or not session:
        return False
    for row in list_tag_data_rows(session, "EDG"):
        if len(row) >= 4 and row[1] == pid and row[2] == "has_mwu":
            return True
    return False
