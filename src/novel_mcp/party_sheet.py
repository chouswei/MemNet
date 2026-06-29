"""Party roster panel — member items/skills/attrs; display controlled by USR (author/script)."""

from __future__ import annotations

from typing import Any

from novel_mcp.affinity_edges import read_directed_affinity
from novel_mcp.character_gender import (
    NPC_IDX_CRAFT,
    NPC_IDX_GENDER,
    NPC_IDX_ITEMS,
    NPC_IDX_SKILLS,
    NPC_IDX_STATUS,
    normalise_npc_parts,
    normalise_plr_parts,
    npc_appearance,
    npc_personality,
    npc_traits,
    npc_voice,
    PLR_IDX_BODY,
    PLR_IDX_GENDER,
)
from novel_mcp.catalog_schema import read_catalog_schema, resolve_martial_actions
from novel_mcp.entity_knowledge import (
    knowledge_meta,
    merge_knowledge_index,
    resolve_npc_display_name,
)
from novel_mcp.player_profile import read_pc_display_name
from novel_mcp.player_sheet import read_items_for_owner, read_skills_for_owner
from novel_mcp.setup_constants import (
    PARTY_ROSTER_KEY,
    PARTY_UI_KEY,
    PARTY_UI_NOTE_KEY,
    SENTINEL,
)
from novel_mcp.setup_graph import first_plr_id, list_tag_data_rows, read_usr_by_key

_PARTY_RELATIONS = frozenset({"party", "in_party", "companions", "member", "隊伍"})
_VALID_UI_SECTIONS = frozenset({"items", "skills", "attrs", "summary", "relations"})
_DEFAULT_UI = ("items", "skills", "attrs")


def _is_empty_usr(raw: str | None) -> bool:
    return not raw or raw.strip() in (SENTINEL, "_", "-", "")


def _parse_roster(raw: str | None) -> list[str]:
    if _is_empty_usr(raw):
        return []
    text = raw.replace("，", ";").replace(",", ";")
    return [part.strip() for part in text.split(";") if part.strip()]


def _parse_ui_sections(raw: str | None) -> list[str]:
    if _is_empty_usr(raw):
        return list(_DEFAULT_UI)
    text = raw.replace("，", ",")
    parts = [p.strip().lower() for p in text.split(",") if p.strip()]
    out = [p for p in parts if p in _VALID_UI_SECTIONS]
    return out or list(_DEFAULT_UI)


def _roster_from_edges(session: str, plr_id: str) -> list[str]:
    found: list[str] = []
    for parts in list_tag_data_rows(session, "EDG"):
        if len(parts) < 4:
            continue
        rel = parts[2]
        if rel not in _PARTY_RELATIONS:
            continue
        src, dst = parts[1], parts[3]
        if src == plr_id and dst not in found:
            found.append(dst)
        elif dst == plr_id and src not in found:
            found.append(src)
    return found


def _resolve_roster(session: str, plr_id: str) -> list[str]:
    explicit = _parse_roster(read_usr_by_key(session, PARTY_ROSTER_KEY))
    if explicit:
        return explicit
    edge_ids = _roster_from_edges(session, plr_id)
    if edge_ids:
        return [plr_id] + [mid for mid in edge_ids if mid != plr_id]
    return [plr_id]


def _character_meta(
    session: str,
    char_id: str,
    *,
    know_idx: dict | None = None,
    viewer_id: str | None = None,
) -> dict[str, Any]:
    viewer = viewer_id or first_plr_id(session)
    for parts in list_tag_data_rows(session, "PLR"):
        if parts[0] != char_id:
            continue
        norm = normalise_plr_parts(parts)
        attrs: list[dict[str, str]] = []
        if len(norm) > 1 and norm[1]:
            attrs.append({"label": "身份", "value": norm[1]})
        if len(norm) > 2 and norm[2]:
            attrs.append({"label": "出生年", "value": norm[2]})
        if len(norm) > PLR_IDX_GENDER and norm[PLR_IDX_GENDER]:
            attrs.append({"label": "性別", "value": norm[PLR_IDX_GENDER]})
        if len(norm) > PLR_IDX_BODY and norm[PLR_IDX_BODY]:
            attrs.append({"label": "身體", "value": norm[PLR_IDX_BODY]})
        display_name = read_pc_display_name(session)
        if not display_name:
            display_name = parts[1] if len(parts) > 1 else char_id
        return {
            "id": char_id,
            "name": display_name,
            "role": "plr",
            "attrs": attrs,
            "summary": {},
        }
    for parts in list_tag_data_rows(session, "NPC"):
        if parts[0] != char_id:
            continue
        norm = normalise_npc_parts(parts)
        attrs: list[dict[str, str]] = []
        if len(norm) > 2 and norm[2]:
            attrs.append({"label": "出生年", "value": norm[2]})
        if len(norm) > NPC_IDX_GENDER and norm[NPC_IDX_GENDER]:
            attrs.append({"label": "性別", "value": norm[NPC_IDX_GENDER]})
        if npc_appearance(parts):
            attrs.append({"label": "外觀", "value": npc_appearance(parts)})
        if npc_personality(parts):
            attrs.append({"label": "性格", "value": npc_personality(parts)})
        if npc_voice(parts):
            attrs.append({"label": "語氣", "value": npc_voice(parts)})
        if npc_traits(parts):
            attrs.append({"label": "特徵", "value": npc_traits(parts)})
        if len(norm) > NPC_IDX_CRAFT and norm[NPC_IDX_CRAFT]:
            attrs.append({"label": "工藝", "value": norm[NPC_IDX_CRAFT]})
        if len(norm) > NPC_IDX_STATUS and norm[NPC_IDX_STATUS]:
            attrs.append({"label": "狀態", "value": norm[NPC_IDX_STATUS]})
        summary: dict[str, str] = {}
        if len(norm) > NPC_IDX_SKILLS and norm[NPC_IDX_SKILLS]:
            summary["skills"] = norm[NPC_IDX_SKILLS]
        if len(norm) > NPC_IDX_ITEMS and norm[NPC_IDX_ITEMS]:
            summary["items"] = norm[NPC_IDX_ITEMS]
        meta = knowledge_meta(session, viewer, char_id, index=know_idx)
        return {
            "id": char_id,
            "name": resolve_npc_display_name(session, viewer, parts, index=know_idx),
            "role": "npc",
            "attrs": attrs,
            "summary": summary,
            **meta,
        }
    return {
        "id": char_id,
        "name": char_id,
        "role": "unknown",
        "attrs": [],
        "summary": {},
    }


def _strip_actions(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in entries:
        copy = {k: v for k, v in row.items() if k != "actions"}
        out.append(copy)
    return out


def read_party_panel(
    session: str | None,
    *,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    if not session:
        return {"exit_code": 2, "errors": ["missing session"], "members": []}

    plr_id = first_plr_id(session)
    if not plr_id:
        return {"exit_code": 2, "errors": ["no PLR row"], "members": []}

    schema = read_catalog_schema(session, workspace_root_path=workspace_root_path)
    ui_sections = _parse_ui_sections(read_usr_by_key(session, PARTY_UI_KEY))
    ui_note = read_usr_by_key(session, PARTY_UI_NOTE_KEY) or ""
    if _is_empty_usr(ui_note):
        ui_note = ""

    plr_id = first_plr_id(session)
    know_idx = merge_knowledge_index(session) if session else {}

    members: list[dict[str, Any]] = []
    plr_meta = _character_meta(session, plr_id, know_idx=know_idx)
    plr_name = plr_meta["name"]
    for char_id in _resolve_roster(session, plr_id):
        meta = _character_meta(session, char_id, know_idx=know_idx, viewer_id=plr_id)
        entry: dict[str, Any] = {
            "id": meta["id"],
            "name": meta["name"],
            "role": meta["role"],
            "sections": list(ui_sections),
        }

        if "attrs" in ui_sections:
            entry["attrs"] = meta["attrs"]

        if "summary" in ui_sections and meta.get("summary"):
            entry["summary"] = meta["summary"]

        if "items" in ui_sections:
            items = read_items_for_owner(
                session, char_id, schema, workspace_root_path=workspace_root_path
            )
            entry["items"] = _strip_actions(items)

        if "skills" in ui_sections:
            arts, body_stats = read_skills_for_owner(
                session, char_id, schema, workspace_root_path=workspace_root_path
            )
            entry["skills"] = _strip_actions(arts)
            entry["body_stats"] = _strip_actions(body_stats)

        if "relations" in ui_sections and char_id != plr_id:
            rel: dict[str, Any] = {"directed": True}
            plr_to_member = read_directed_affinity(session, plr_id, char_id)
            member_to_plr = read_directed_affinity(session, char_id, plr_id)
            if plr_to_member:
                rel["plr_to_member"] = plr_to_member
            if member_to_plr:
                rel["member_to_plr"] = member_to_plr
            # Legacy keys for older clients
            if plr_to_member:
                rel["to_member"] = plr_to_member
            if member_to_plr:
                rel["from_member"] = member_to_plr
            if plr_to_member or member_to_plr:
                entry["relations"] = rel

        members.append(entry)

    return {
        "exit_code": 0,
        "plr_id": plr_id,
        "plr_name": plr_name,
        "ui_sections": ui_sections,
        "ui_note": ui_note,
        "members": members,
        "errors": [],
    }
