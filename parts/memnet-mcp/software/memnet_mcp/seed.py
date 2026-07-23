"""Default @LAW rows injected on MCP session_open when not already in seed_lines."""

from __future__ import annotations

# Compact engine invariants — prepended on every query warm once seeded.
DEFAULT_LAW_LINES: tuple[str, ...] = (
    "@LAW: LAW01|EDG|on_context|hide|settled_edg_unless_anchor",
    "@LAW: LAW02|*|on_add|unique|one_id_add_then_update",
    "@LAW: LAW03|EDG|on_add|validate|src_dist_exist_first",
    "@LAW: LAW04|*|on_add|use_backslash|backslash_pipe_not_bare",
    "@LAW: LAW05|*|on_turn|read_warm|warm_before_add_or_update",
)


def _law_id_from_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.upper().startswith("@LAW:"):
        return None
    payload = stripped.split(":", 1)[1].strip()
    first = payload.split("|", 1)[0].strip()
    return first or None


def supplement_seed_lines(seed_lines: list[str] | None) -> list[str]:
    """Prepend default LAW rows whose ids are not already in seed_lines."""
    seed = list(seed_lines or [])
    present = {_law_id_from_line(line) for line in seed}
    present.discard(None)
    prefix = [line for line in DEFAULT_LAW_LINES if _law_id_from_line(line) not in present]
    return prefix + seed
