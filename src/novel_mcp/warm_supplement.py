"""Enrich truncated ``query warm`` for the generic novel RPG pipeline.

MemNet core stays application-agnostic; beat wires (OLN/SBD/SCR) and scene
cast (PLR/NPC/SYS) are merged here via ``read list`` when absent from warm.
"""

from __future__ import annotations

from memnet_mcp.client import run_memnet
from novel_mcp.setup_constants import AFF_EDG_RELATION

from novel_mcp.beat_stage import normalize_beat_stage

# Novel RPG stage wires + scene cast — not MemNet engine concepts.
_STAGE_SUPPLEMENT_TAGS: dict[str, tuple[str, ...]] = {
    "script_draft": ("PLR", "NPC", "SYS", "BIZ", "SCN"),
    "script_review": ("OLN", "SBD", "SCR", "PLR", "NPC", "SYS"),
    "prose": ("OLN", "SBD", "SCR", "PLR", "NPC", "SYS"),
}
_DEFAULT_STAGE = "prose"

# Opening cast + industry wiring (instance-specific ids; safe when graph lacks them).
_OPENING_EDG_IDS = frozenset(
    {
        "E06",
        "E09",
        "E10",
        "E11",
        "E20",
        "E21",
        "E22",
        "E23",
        "EG287",
        "EG288",
        "EG289",
        "EG290",
        "EG291",
        "EG292",
        "EG293",
        "EG294",
    }
)

_CAST_TAGS = frozenset({"PLR", "NPC"})


def _tags_for_stage(beat_stage: str) -> tuple[str, ...]:
    stage = normalize_beat_stage(beat_stage)
    return _STAGE_SUPPLEMENT_TAGS.get(stage, _STAGE_SUPPLEMENT_TAGS[_DEFAULT_STAGE])


def _is_tag_map_def_line(line: str) -> bool:
    s = line.strip()
    if not s.startswith("@") or ":" not in s:
        return False
    body = s.split(":", 1)[1].strip()
    return body.startswith("id|")


def _has_tag_rows(stdout: str, tag: str) -> bool:
    prefix = f"@{tag}:"
    for line in stdout.splitlines():
        s = line.strip()
        if s.startswith(prefix) and not _is_tag_map_def_line(s):
            return True
    return False


def _parse_wire_row(line: str) -> tuple[str, list[str]] | None:
    s = line.strip()
    if not s.startswith("@") or ":" not in s:
        return None
    if _is_tag_map_def_line(s):
        return None
    tag, body = s[1:].split(":", 1)
    parts = [p.strip() for p in body.strip().split("|")]
    if not parts or not parts[0]:
        return None
    return tag, parts


def _character_ids_from_text(text: str) -> set[str]:
    ids: set[str] = set()
    for line in text.splitlines():
        parsed = _parse_wire_row(line)
        if not parsed:
            continue
        tag, parts = parsed
        if tag in _CAST_TAGS:
            ids.add(parts[0])
    return ids


def _supplement_tag_rows(
    session: str,
    warm_stdout: str,
    *,
    beat_stage: str,
    existing: set[str],
) -> list[str]:
    extras: list[str] = []
    for tag in _tags_for_stage(beat_stage):
        if _has_tag_rows(warm_stdout, tag):
            continue
        resp = run_memnet(["read", "list", "--tag", tag], session=session)
        if resp.exit_code != 0 or not resp.stdout:
            continue
        for raw in resp.stdout.splitlines():
            ln = raw.strip()
            if not ln or ln in existing:
                continue
            if not ln.startswith(f"@{tag}:"):
                continue
            extras.append(ln)
            existing.add(ln)
    return extras


def _supplement_opening_plot_edges(session: str, existing: set[str]) -> list[str]:
    extras: list[str] = []
    resp = run_memnet(["read", "list", "--tag", "EDG"], session=session)
    if resp.exit_code != 0 or not resp.stdout:
        return extras
    for raw in resp.stdout.splitlines():
        ln = raw.strip()
        if not ln or ln in existing or not ln.startswith("@EDG:"):
            continue
        parsed = _parse_wire_row(ln)
        if not parsed:
            continue
        _, parts = parsed
        if not parts or parts[0] not in _OPENING_EDG_IDS:
            continue
        extras.append(ln)
        existing.add(ln)
    return extras


def _supplement_aff_to_edges(session: str, character_ids: set[str], existing: set[str]) -> list[str]:
    if not character_ids:
        return []
    extras: list[str] = []
    resp = run_memnet(["read", "list", "--tag", "EDG"], session=session)
    if resp.exit_code != 0 or not resp.stdout:
        return extras
    for raw in resp.stdout.splitlines():
        ln = raw.strip()
        if not ln or ln in existing or not ln.startswith("@EDG:"):
            continue
        parsed = _parse_wire_row(ln)
        if not parsed:
            continue
        _, parts = parsed
        if len(parts) < 4 or parts[2] != AFF_EDG_RELATION:
            continue
        src, dst = parts[1], parts[3]
        if src not in character_ids and dst not in character_ids:
            continue
        extras.append(ln)
        existing.add(ln)
    return extras


def enrich_warm_stdout(
    session: str | None,
    warm_stdout: str,
    *,
    beat_stage: str = "prose",
) -> str:
    """Append missing novel RPG rows when warm was truncated (e.g. by LAW flood)."""
    if not session or not warm_stdout:
        return warm_stdout

    existing = {ln.strip() for ln in warm_stdout.splitlines() if ln.strip()}
    extras: list[str] = []
    stage = normalize_beat_stage(beat_stage)
    extras.extend(_supplement_tag_rows(session, warm_stdout, beat_stage=stage, existing=existing))

    if stage in ("script_draft", "script_review"):
        extras.extend(_supplement_opening_plot_edges(session, existing))

    merged_text = warm_stdout.rstrip()
    if extras:
        merged_text = merged_text + "\n" + "\n".join(extras)

    character_ids = _character_ids_from_text(merged_text)
    aff_extras = _supplement_aff_to_edges(session, character_ids, existing)
    extras.extend(aff_extras)

    if not extras:
        return warm_stdout
    base = warm_stdout.rstrip()
    return base + "\n" + "\n".join(extras) + "\n"
