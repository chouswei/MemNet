"""Enrich truncated ``query warm`` for the generic novel RPG pipeline.

MemNet core stays application-agnostic; beat wires (OLN/SBD/SCR) and scene
cast (PLR/NPC/SYS) are merged here via ``read list`` when absent from warm.
"""

from __future__ import annotations

from memnet_mcp.client import run_memnet

# Novel RPG stage wires + scene cast — not MemNet engine concepts.
_STAGE_SUPPLEMENT_TAGS: dict[str, tuple[str, ...]] = {
    "oln": ("PLR", "NPC", "SYS", "BIZ", "SCN"),
    "sbd": ("OLN", "PLR", "NPC", "SYS"),
    "scr": ("OLN", "SBD", "PLR", "NPC", "SYS"),
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


def _tags_for_stage(beat_stage: str) -> tuple[str, ...]:
    return _STAGE_SUPPLEMENT_TAGS.get(beat_stage, _STAGE_SUPPLEMENT_TAGS[_DEFAULT_STAGE])


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

    if beat_stage in ("oln", "sbd", "scr"):
        resp = run_memnet(["read", "list", "--tag", "EDG"], session=session)
        if resp.exit_code == 0 and resp.stdout:
            for raw in resp.stdout.splitlines():
                ln = raw.strip()
                if not ln or ln in existing or not ln.startswith("@EDG:"):
                    continue
                parts = ln.split(":", 1)[1].strip().split("|")
                if not parts or parts[0] not in _OPENING_EDG_IDS:
                    continue
                extras.append(ln)
                existing.add(ln)

    if not extras:
        return warm_stdout
    base = warm_stdout.rstrip()
    return base + "\n" + "\n".join(extras) + "\n"
