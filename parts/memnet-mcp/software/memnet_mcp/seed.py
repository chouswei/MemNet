"""LawSeedHelper — engine LAW01–LAW05 injected on MCP session_open.

These rows are **engine invariants** (prepended on every warm / pin map), not
agent I/O. Agents must not hand-author LAW01–LAW05 in chat.

Default emit is gated GQL CREATE. When the caller passes legacy ``@TAG``
pipe ``seed_lines``, missing defaults are emitted as pipe so the whole seed
batch stays one dialect (MutateGate rejects mixed batches).
"""

from __future__ import annotations

import re

from memnet.gql import looks_like_gql
from memnet.legacy_pipe_import import looks_like_pipe

# id, name, cycle, mechanism, constraint (fixed LAW schema)
_DEFAULT_LAW_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("LAW01", "EDG", "on_context", "hide", "settled_edg_unless_anchor"),
    ("LAW02", "*", "on_add", "unique", "one_id_add_then_update"),
    ("LAW03", "EDG", "on_add", "validate", "src_dist_exist_first"),
    ("LAW04", "*", "on_add", "use_backslash", "backslash_pipe_not_bare"),
    ("LAW05", "*", "on_turn", "read_warm", "warm_before_add_or_update"),
)

_LAW_ID_TIER_A = re.compile(r"^(LAW[A-Za-z0-9_.-]+)\b")
_LAW_ID_GQL = re.compile(
    r"id:\s*['\"]?(LAW[A-Za-z0-9_.-]+)['\"]?",
    re.IGNORECASE,
)


def _gql_line(row: tuple[str, str, str, str, str]) -> str:
    law_id, name, cycle, mechanism, constraint = row
    return (
        f"CREATE (:LAW {{id: '{law_id}', name: '{name}', cycle: '{cycle}', "
        f"mechanism: '{mechanism}', constraint: '{constraint}'}})"
    )


def _pipe_line(row: tuple[str, str, str, str, str]) -> str:
    law_id, name, cycle, mechanism, constraint = row
    return f"@LAW: {law_id}|{name}|{cycle}|{mechanism}|{constraint}"


DEFAULT_LAW_LINES: tuple[str, ...] = tuple(_gql_line(r) for r in _DEFAULT_LAW_ROWS)


def _law_id_from_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.upper().startswith("@LAW:"):
        payload = stripped.split(":", 1)[1].strip()
        first = payload.split("|", 1)[0].strip()
        return first or None
    mg = _LAW_ID_GQL.search(stripped)
    if mg:
        return mg.group(1)
    m = _LAW_ID_TIER_A.match(stripped)
    return m.group(1) if m else None


def _seed_dialect(seed_lines: list[str] | None) -> str:
    """Return 'gql', 'pipe', or 'mixed' for non-empty content lines."""
    saw_pipe = False
    saw_gql = False
    for line in seed_lines or []:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if looks_like_pipe(s):
            saw_pipe = True
        elif looks_like_gql(s):
            saw_gql = True
    if saw_pipe and saw_gql:
        return "mixed"
    if saw_pipe:
        return "pipe"
    return "gql"


def supplement_seed_lines(seed_lines: list[str] | None) -> list[str]:
    """Prepend default LAW rows whose ids are not already in seed_lines."""
    seed = list(seed_lines or [])
    present = {_law_id_from_line(line) for line in seed}
    present.discard(None)
    dialect = _seed_dialect(seed)
    fmt = _pipe_line if dialect == "pipe" else _gql_line
    prefix = [fmt(row) for row in _DEFAULT_LAW_ROWS if row[0] not in present]
    return prefix + seed
