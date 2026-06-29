"""Player profile read/validate/commit for god-realm setup."""

from __future__ import annotations

from typing import Any

from novel_mcp.setup_constants import SENTINEL
from novel_mcp.character_gender import (
    PLR_FIELD_COUNT,
    PLR_IDX_BODY,
    PLR_IDX_GENDER,
    format_plr_wire,
    normalise_plr_parts,
    strip_gender_from_body,
)
from novel_mcp.setup_graph import (
    first_plr_id,
    graph_update,
    read_usr_by_key,
    read_get_body,
    setup_commit_errors,
    usr_id_for_key,
)
from novel_mcp.setup_profile_rules import validate_profile_fields


def _is_set(value: str | None) -> bool:
    return bool(value) and value != SENTINEL


def read_pc_display_name(session: str | None) -> str | None:
    """Player-chosen name from USR pc_name; None when unset."""
    name = read_usr_by_key(session, "pc_name")
    if not _is_set(name):
        return None
    return str(name).strip()


def validate_profile(
    session: str | None,
    name: str,
    gender: str,
    *,
    require_name: bool = True,
    require_gender: bool = True,
) -> list[str]:
    return validate_profile_fields(
        session,
        name,
        gender,
        require_name=require_name,
        require_gender=require_gender,
    )


def read_profile(session: str | None) -> dict[str, Any]:
    name = read_usr_by_key(session, "pc_name") or SENTINEL
    gender = read_usr_by_key(session, "pc_gender") or SENTINEL
    name_set = _is_set(name)
    gender_set = _is_set(gender)
    errors: list[str] = []
    if name_set:
        errors.extend(
            validate_profile(session, name, gender, require_name=True, require_gender=False)
        )
    if gender_set:
        errors.extend(
            validate_profile(session, name, gender, require_name=False, require_gender=True)
        )
    complete = name_set and gender_set and not errors
    return {
        "exit_code": 0,
        "name": name,
        "gender": gender,
        "name_set": name_set,
        "gender_set": gender_set,
        "complete": complete,
        "errors": errors,
    }


def commit_profile(
    session: str | None,
    name: str,
    gender: str,
    *,
    plr_id: str | None = None,
    setup_complete: bool = False,
) -> dict[str, Any]:
    block = setup_commit_errors(session, setup_complete=setup_complete)
    if block:
        return {
            "exit_code": 2,
            "errors": block,
            "name": None,
            "gender": None,
            "complete": False,
        }

    current = read_profile(session)
    new_name = name.strip() if name and name.strip() else ""
    new_gender = gender.strip() if gender and gender.strip() else ""
    final_name = new_name if new_name else (current["name"] if current["name_set"] else SENTINEL)
    final_gender = (
        new_gender if new_gender else (current["gender"] if current["gender_set"] else SENTINEL)
    )

    if not new_name and not new_gender:
        return {
            "exit_code": 2,
            "errors": ["provide name and/or gender"],
            "name": None,
            "gender": None,
            "complete": False,
        }

    require_name = bool(new_name) or final_name != SENTINEL
    require_gender = bool(new_gender) or final_gender != SENTINEL
    errors = validate_profile(
        session,
        final_name,
        final_gender,
        require_name=require_name and _is_set(final_name),
        require_gender=require_gender and _is_set(final_gender),
    )
    if errors:
        return {
            "exit_code": 2,
            "errors": errors,
            "name": None,
            "gender": None,
            "complete": False,
        }

    lines: list[str] = []
    if new_name:
        uid = usr_id_for_key(session, "pc_name")
        if not uid:
            return {
                "exit_code": 2,
                "errors": ["missing USR row for pc_name"],
                "name": None,
                "gender": None,
                "complete": False,
            }
        lines.append(f"@USR: {uid}|pc_name|{final_name}|persistent")

    if new_gender:
        uid = usr_id_for_key(session, "pc_gender")
        if not uid:
            return {
                "exit_code": 2,
                "errors": ["missing USR row for pc_gender"],
                "name": None,
                "gender": None,
                "complete": False,
            }
        lines.append(f"@USR: {uid}|pc_gender|{final_gender}|persistent")

    if new_gender:
        pid = plr_id or first_plr_id(session)
        if not pid:
            return {
                "exit_code": 2,
                "errors": ["no PLR row in graph"],
                "name": None,
                "gender": None,
                "complete": False,
            }
        plr_body = read_get_body(session, pid)
        if not plr_body:
            return {
                "exit_code": 2,
                "errors": [f"PLR {pid} not found"],
                "name": None,
                "gender": None,
                "complete": False,
            }
        parts = normalise_plr_parts(plr_body.split("|"))
        if len(parts) < PLR_FIELD_COUNT:
            return {
                "exit_code": 2,
                "errors": [f"PLR {pid} has fewer than {PLR_FIELD_COUNT} fields"],
                "name": None,
                "gender": None,
                "complete": False,
            }
        parts[PLR_IDX_GENDER] = final_gender
        parts[PLR_IDX_BODY] = strip_gender_from_body(parts[PLR_IDX_BODY])
        lines.append(format_plr_wire(parts))

    if not lines:
        return {
            "exit_code": 2,
            "errors": ["nothing to commit"],
            "name": None,
            "gender": None,
            "complete": False,
        }

    code, upd_err = graph_update(session, lines)
    if code != 0:
        return {
            "exit_code": 2,
            "errors": upd_err or ["update failed"],
            "name": None,
            "gender": None,
            "complete": False,
        }

    out = read_profile(session)
    out["exit_code"] = 0
    return out
