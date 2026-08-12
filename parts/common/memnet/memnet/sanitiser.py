"""Input sanitiser for add/update batches (GQL + legacy @TAG pipe)."""

from __future__ import annotations

import re

from memnet.exceptions import MemNetError
from memnet.gql import looks_like_gql, looks_like_legacy_layer_or_tier_a

_THINK_RE = re.compile(
    r"^<think>.*?</think>\s*",
    re.DOTALL | re.IGNORECASE,
)


def sanitise_line(line: str) -> str | None:
    line = line.strip()
    if not line or line.lstrip().startswith("#") and not line.startswith("##"):
        return None
    line = _THINK_RE.sub("", line).strip()
    line = line.strip("`").strip()
    if not line:
        return None
    if line[0] in "{[" and not line.startswith("[:"):
        # Allow Cypher list/map only inside statements; bare JSON rejected
        if line[0] == "{" or (line[0] == "[" and not line.upper().startswith("[NEW")):
            raise MemNetError(
                "json_not_supported",
                "MemNet uses GQL wire format not JSON objects",
                example="CREATE (:PLR {id: 'P01', identity: 'Alice'})",
            )
    if looks_like_legacy_layer_or_tier_a(line):
        raise MemNetError(
            "legacy_dialect_retired",
            "Layer / Tier A agent wire is retired (ADR-001 M2). "
            "Use gated openCypher-shaped GQL — see docs/grammar/gql-wire-profile.md",
            example="CREATE (:TSK {id: 'NEW', goal: '…', status: 'in_progress'})",
        )
    if line.startswith("@") or looks_like_gql(line):
        return line
    raise MemNetError(
        "invalid_line",
        "line must be gated GQL (CREATE/MATCH/MERGE/…) or @TAG pipe",
        example="CREATE (:PLR {id: 'NEW', identity: 'Hero'})",
    )


def _to_text(raw: str | bytes) -> str:
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MemNetError("encoding", "input must be UTF-8") from exc
    return raw


def sanitise_batch(raw_lines: list[str | bytes], *, strip_fences: bool = True) -> list[str]:
    lines = [_to_text(r) for r in raw_lines]
    if strip_fences and lines:
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
    out: list[str] = []
    for text in lines:
        cleaned = sanitise_line(text)
        if cleaned:
            out.append(cleaned)
    return out
