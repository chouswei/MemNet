"""Mechanical script-stage checks (bundle shape). Content quality is LLM-reviewed."""

from __future__ import annotations

import re

_ROW_RE = re.compile(r"^@(\w+):\s*(.+)$")


def _parse_wire(line: str) -> tuple[str, list[str]] | None:
    text = line.strip()
    m = _ROW_RE.match(text)
    if m:
        tag, body = m.group(1).upper(), m.group(2)
    elif ":" in text and text.startswith("@"):
        tag, body = text[1:].split(":", 1)
        tag = tag.upper()
    else:
        return None
    parts = [p.strip() for p in body.split("|")]
    if not parts or not parts[0]:
        return None
    return tag, parts


def validate_stage_wires(
    lines: list[str],
    *,
    presentation: dict | None = None,
    warm_stdout: str = "",
) -> dict[str, list[str]]:
    """No programmatic content scan — script_review LLM handles ID/name checks."""
    _ = lines, presentation, warm_stdout
    return {"violations": [], "warnings": []}


def validate_script_draft_bundle(
    oln_lines: list[str] | None,
    sbd_lines: list[str] | None,
    scr_lines: list[str] | None,
) -> list[str]:
    """Mechanical bundle checks for script_draft finish."""
    errors: list[str] = []
    oln = list(oln_lines or [])
    sbd = list(sbd_lines or [])
    scr = list(scr_lines or [])

    if len(oln) < 1:
        errors.append("@ERR: script_draft_bundle|need >=1 @OLN line")
    if len(sbd) < 2:
        errors.append("@ERR: script_draft_bundle|need >=2 @SBD lines")
    if len(scr) < 2:
        errors.append("@ERR: script_draft_bundle|need >=2 @SCR lines")
    if errors:
        return errors

    oln_parsed = _parse_wire(oln[0])
    if not oln_parsed:
        errors.append("@ERR: script_draft_bundle|invalid @OLN line")
        return errors
    _, oln_parts = oln_parsed
    if len(oln_parts) < 2:
        errors.append("@ERR: script_draft_bundle|@OLN missing round field")
        return errors
    beat_round = oln_parts[1]

    def _round_and_shot(line: str) -> tuple[str | None, str | None]:
        p = _parse_wire(line)
        if not p or len(p[1]) < 3:
            return None, None
        return p[1][1], p[1][2]

    sbd_shots: set[int] = set()
    for line in sbd:
        rnd, shot = _round_and_shot(line)
        if rnd != beat_round:
            errors.append(f"@ERR: script_draft_bundle|SBD round {rnd} != OLN round {beat_round}")
        if shot and shot.isdigit():
            sbd_shots.add(int(shot))

    scr_shots: set[int] = set()
    for line in scr:
        rnd, shot = _round_and_shot(line)
        if rnd != beat_round:
            errors.append(f"@ERR: script_draft_bundle|SCR round {rnd} != OLN round {beat_round}")
        if shot and shot.isdigit():
            scr_shots.add(int(shot))

    if sbd_shots != scr_shots:
        errors.append(
            f"@ERR: script_draft_bundle|SBD shots {sorted(sbd_shots)} != SCR shots {sorted(scr_shots)}"
        )
    elif len(sbd_shots) < 2:
        errors.append("@ERR: script_draft_bundle|need >=2 matching shot numbers")
    else:
        expected = set(range(1, len(sbd_shots) + 1))
        if sbd_shots != expected:
            errors.append(
                f"@ERR: script_draft_bundle|shots must be 1..{len(sbd_shots)}, got {sorted(sbd_shots)}"
            )
    return errors


def collect_audit_findings(
    warm_stdout: str,
    *,
    presentation: dict | None = None,
) -> list[str]:
    """Script review is LLM-driven; no programmatic audit list."""
    _ = warm_stdout, presentation
    return []
