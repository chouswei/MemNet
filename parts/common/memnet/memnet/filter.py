"""Field filters for read list."""

from __future__ import annotations

import fnmatch

from memnet.exceptions import MemNetError
from memnet.models import Record


def parse_where(clause: str) -> tuple[str, str]:
    clause = clause.strip()
    if not clause:
        raise MemNetError("bad_where", "empty --where")
    if "=" not in clause:
        raise MemNetError("bad_where", f"expected field=value got {clause!r}")
    field, _, pattern = clause.partition("=")
    field = field.strip()
    if not field:
        raise MemNetError("bad_where", f"missing field name in {clause!r}")
    return field, pattern


def parse_wheres(clauses: list[str]) -> list[tuple[str, str]]:
    return [parse_where(c) for c in clauses]


def field_matches(value: str, pattern: str) -> bool:
    if "*" in pattern or "?" in pattern:
        return fnmatch.fnmatch(value, pattern)
    return value == pattern


def record_matches(record: Record, wheres: list[tuple[str, str]]) -> bool:
    for field, pattern in wheres:
        if not field_matches(record.fields.get(field, ""), pattern):
            return False
    return True
