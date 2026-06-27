"""Player profile read/validate/commit for god-realm setup."""

from __future__ import annotations

from typing import Any

from novel_mcp.setup_constants import PROFILE_GENDERS, PROFILE_NAME_RE, SENTINEL
from novel_mcp.setup_graph import (
    first_plr_id,
    graph_update,
    merge_plr_gender,
    read_usr_by_key,
    read_get_body,
    setup_commit_errors,
)


def validate_profile(name: str, gender: str) -> list[str]:
    errors: list[str] = []
    if not PROFILE_NAME_RE.match(name.strip()):
        errors.append("name: must be 2-4 CJK characters")
    if gender not in PROFILE_GENDERS:
        errors.append("gender: must be 男 or 女")
    return errors


def read_profile(session: str | None) -> dict[str, Any]:
    name = read_usr_by_key(session, "pc_name") or SENTINEL
    gender = read_usr_by_key(session, "pc_gender") or SENTINEL
    errors = validate_profile(name, gender) if name != SENTINEL and gender != SENTINEL else []
    complete = name != SENTINEL and gender != SENTINEL and not errors
    return {
        "exit_code": 0,
        "name": name,
        "gender": gender,
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

    errors = validate_profile(name, gender)
    if errors:
        return {
            "exit_code": 2,
            "errors": errors,
            "name": None,
            "gender": None,
            "complete": False,
        }

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

    parts = plr_body.split("|")
    if len(parts) < 7:
        return {
            "exit_code": 2,
            "errors": [f"PLR {pid} has fewer than 7 fields"],
            "name": None,
            "gender": None,
            "complete": False,
        }

    merged_body = merge_plr_gender(parts[6], gender)
    lines = [
        f"@USR: USR03|pc_name|{name}|persistent",
        f"@USR: USR53|pc_gender|{gender}|persistent",
        f"@PLR: {parts[0]}|{parts[1]}|{parts[2]}|{parts[3]}|{parts[4]}|{parts[5]}|{merged_body}",
    ]
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
