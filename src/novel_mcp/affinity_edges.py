"""Directed character affinity — `@EDG` relation `aff_to` with scored `attrs`."""

from __future__ import annotations

from typing import Any

from novel_mcp.setup_constants import AFF_DIMENSION_LABELS, AFF_EDG_RELATION
from novel_mcp.setup_graph import list_tag_data_rows

_AFF_NOTE_KEY = "備註"


def format_affinity_attrs(
    scores: dict[str, str],
    *,
    note: str = "",
    labels: tuple[str, ...] = AFF_DIMENSION_LABELS,
) -> str:
    parts = [f"{label}:{scores[label]}" for label in labels if label in scores and scores[label] != ""]
    if note:
        parts.append(f"{_AFF_NOTE_KEY}:{note}")
    return ";".join(parts)


def parse_affinity_attrs(
    attrs: str,
    *,
    labels: tuple[str, ...] = AFF_DIMENSION_LABELS,
) -> tuple[dict[str, str], str]:
    raw: dict[str, str] = {}
    note = ""
    for token in attrs.split(";"):
        piece = token.strip()
        if not piece or ":" not in piece:
            continue
        key, value = piece.split(":", 1)
        key, value = key.strip(), value.strip()
        if key == _AFF_NOTE_KEY:
            note = value
        else:
            raw[key] = value
    return raw, note


def _dims_from_scores(scores: dict[str, str], labels: tuple[str, ...]) -> list[dict[str, str]]:
    return [{"label": label, "value": scores[label]} for label in labels if label in scores and scores[label] != ""]


def read_directed_affinity(session: str, from_id: str, to_id: str) -> dict[str, Any] | None:
    labels = AFF_DIMENSION_LABELS
    for parts in list_tag_data_rows(session, "EDG"):
        if len(parts) < 4:
            continue
        if parts[2] != AFF_EDG_RELATION or parts[1] != from_id or parts[3] != to_id:
            continue
        attrs = parts[5] if len(parts) > 5 else ""
        scores, note = parse_affinity_attrs(attrs, labels=labels)
        dims = _dims_from_scores(scores, labels)
        if not dims and not note:
            return None
        return {"from": from_id, "to": to_id, "dims": dims, "note": note, "edge_id": parts[0]}

    # Legacy `@AFF` node rows (pre-EDG migration); remove once all sessions re-bootstrap.
    for parts in list_tag_data_rows(session, "AFF"):
        if len(parts) < 5 or parts[1] != from_id or parts[2] != to_id:
            continue
        scores = {
            labels[i]: parts[3 + i]
            for i in range(len(labels))
            if len(parts) > 3 + i and parts[3 + i] != ""
        }
        note_idx = 3 + len(labels)
        note = parts[note_idx] if len(parts) > note_idx else ""
        return {
            "from": from_id,
            "to": to_id,
            "dims": _dims_from_scores(scores, labels),
            "note": note,
            "edge_id": parts[0],
        }
    return None
