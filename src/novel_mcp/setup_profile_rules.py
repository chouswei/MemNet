"""Profile validation rules from seed USR keys (instance-specific)."""

from __future__ import annotations

import re
from typing import Any

from novel_mcp.setup_constants import (
    PROFILE_GENDERS,
    PROFILE_NAME_RE,
    SETUP_PROFILE_GENDERS_KEY,
    SETUP_PROFILE_NAME_RULE_KEY,
    SENTINEL,
)
from novel_mcp.setup_graph import read_usr_by_key

_NAME_RULE_ALIASES: dict[str, re.Pattern[str]] = {
    "cjk_2_4": PROFILE_NAME_RE,
}


def read_profile_rules(session: str | None) -> dict[str, Any]:
    """Load name/gender validation from seed; fall back to generic defaults."""
    name_raw = read_usr_by_key(session, SETUP_PROFILE_NAME_RULE_KEY) if session else None
    gender_raw = read_usr_by_key(session, SETUP_PROFILE_GENDERS_KEY) if session else None

    name_re = PROFILE_NAME_RE
    if name_raw and name_raw not in (SENTINEL, "-"):
        if name_raw.startswith("regex:"):
            name_re = re.compile(name_raw[6:])
        else:
            name_re = _NAME_RULE_ALIASES.get(name_raw.strip(), PROFILE_NAME_RE)

    genders = set(PROFILE_GENDERS)
    if gender_raw and gender_raw not in (SENTINEL, "-"):
        genders = {g.strip() for g in gender_raw.split(";") if g.strip()}

    return {"name_re": name_re, "genders": genders}


def validate_profile_fields(
    session: str | None,
    name: str,
    gender: str,
    *,
    require_name: bool = True,
    require_gender: bool = True,
) -> list[str]:
    rules = read_profile_rules(session)
    errors: list[str] = []
    if require_name:
        if not name or name == SENTINEL:
            errors.append("name: required")
        elif not rules["name_re"].match(name.strip()):
            errors.append("name: does not match setup_profile_name_rule")
    if require_gender:
        if not gender or gender == SENTINEL:
            errors.append("gender: required")
        elif gender not in rules["genders"]:
            allowed = " or ".join(sorted(rules["genders"]))
            errors.append(f"gender: must be {allowed}")
    return errors
