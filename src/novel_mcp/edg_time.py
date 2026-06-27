"""Plot @EDG.at — in-world time when a story edge became true (novel application)."""

from __future__ import annotations

from memnet.wire import emit_record_line, split_payload

from novel_mcp.game_time import is_canonical_time
from novel_mcp.warm_index import index_warm

# Structural / beat wiring — no in-world event timestamp.
WIRING_RELATIONS = frozenset(
    {
        "governs",
        "features",
        "constrains",
        "applies_to",
        "set_in",
        "focus",
    }
)


def edg_requires_at(relation: str) -> bool:
    return relation not in WIRING_RELATIONS


def normalize_edg_parts(parts: list[str]) -> list[str]:
    if len(parts) == 6:
        return parts[:4] + [""] + parts[4:]
    if len(parts) == 7:
        return parts
    raise ValueError(f"expected 6 or 7 EDG fields, got {len(parts)}")


def parse_edg_parts(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("@EDG:"):
        return None
    return split_payload(stripped.removeprefix("@EDG:").strip())


def format_edg_line(parts: list[str]) -> str:
    return emit_record_line("EDG", normalize_edg_parts(parts))


def law_requires_edg_at(warm_stdout: str) -> bool:
    idx = index_warm(warm_stdout)
    law = idx.laws.get("LAW-EDG01")
    if law:
        return "plot_at" in law.tokens or "cite_SYS_time" in law.tokens
    for row in idx.laws.values():
        if row.name == "EDG" and ("plot_at" in row.tokens or "cite_SYS_time" in row.tokens):
            return True
    return False


def stamp_edg_parts(parts: list[str], sys_time: str) -> list[str]:
    normed = normalize_edg_parts(parts)
    if not edg_requires_at(normed[2]):
        return normed
    if normed[4].strip():
        return normed
    normed[4] = sys_time
    return normed


def prepare_edg_add_lines(
    add_lines: list[str],
    *,
    sys_time: str | None,
    warm_stdout: str,
) -> list[str]:
    if not add_lines or not law_requires_edg_at(warm_stdout):
        return add_lines
    out: list[str] = []
    for line in add_lines:
        parts = parse_edg_parts(line)
        if parts is None:
            out.append(line)
            continue
        if sys_time:
            parts = stamp_edg_parts(parts, sys_time)
        else:
            parts = normalize_edg_parts(parts)
        out.append(format_edg_line(parts))
    return out


def validate_edg_at_add_lines(
    add_lines: list[str],
    *,
    warm_stdout: str,
) -> list[str]:
    if not add_lines or not law_requires_edg_at(warm_stdout):
        return []
    errors: list[str] = []
    for line in add_lines:
        parts = parse_edg_parts(line)
        if parts is None:
            continue
        try:
            normed = normalize_edg_parts(parts)
        except ValueError:
            errors.append(f"@ERR: edg_field_count|{line[:40]}")
            continue
        rel = normed[2]
        if not edg_requires_at(rel):
            continue
        at_val = normed[4].strip()
        if not at_val:
            errors.append(f"@ERR: edg_at_missing|{normed[0]}|plot edge needs @EDG.at")
            continue
        if not is_canonical_time(at_val):
            errors.append(f"@ERR: edg_at_format|{normed[0]}|need YYYY-MM-DDTHH got {at_val!r}")
    return errors
