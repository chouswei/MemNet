"""0.13 goldfish caller contract — one live pin_map in the prompt (or skip).

The engine emits Shape. The outer harness packs the next generate. Shape saves
tokens only if that pack **drops** prior ``pin_map`` rows. Stuffing MCP JSON into
a growing ``messages`` list is a fail (``stuffed_maps``).

Env blobs (pytest logs, screenshots) stay on the harness channel. Sparse Δ is a
Commit rule: do not echo the fetched map. Empty cue still skips (0.11 owns
outline). ``view=shell`` is grain on a seed, not a session outline.

This module is the in-repo fail surface. A sibling user-pack may absorb the
caller playbook later; the stuffed-maps test stays here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from memnet.exceptions import MemNetError

PromptChannel = Literal["pin_map", "env_blob", "other"]

# At most one live Recall Shape in the generate prompt.
MAX_PIN_MAPS_IN_PROMPT = 1


@dataclass(frozen=True)
class PromptPart:
    """One packed prompt fragment. The harness tags the channel."""

    channel: PromptChannel
    text: str = ""


def pin_map_bodies(parts: Sequence[PromptPart]) -> list[str]:
    """Non-empty pin_map emits in pack order. Empty skip rows do not count."""
    return [p.text for p in parts if p.channel == "pin_map" and str(p.text).strip()]


def drop_prior_pin_maps(parts: Sequence[PromptPart]) -> list[PromptPart]:
    """Keep env blobs and other turns; retain only the last non-empty pin_map."""
    last_i: int | None = None
    for i, part in enumerate(parts):
        if part.channel == "pin_map" and str(part.text).strip():
            last_i = i
    out: list[PromptPart] = []
    for i, part in enumerate(parts):
        if part.channel == "pin_map":
            if last_i is None or i != last_i:
                continue
        out.append(part)
    return out


def judge_goldfish_prompt(parts: Sequence[PromptPart]) -> None:
    """Fail if the prompt stuffed more than one pin_map emit.

    Empty (skip) is valid. Env blobs do not count as maps.
    """
    bodies = pin_map_bodies(parts)
    if len(bodies) > MAX_PIN_MAPS_IN_PROMPT:
        raise MemNetError(
            "stuffed_maps",
            "goldfish caller stuffed prior pin_map rows; drop them before the next generate",
        )


def judge_sparse_commit(*, pin_map_text: str, mutate_text: str) -> None:
    """Fail if Commit echoes the fetched pin_map body (not a sparse Δ)."""
    body = str(pin_map_text).strip()
    delta = str(mutate_text).strip()
    if body and delta and body in delta:
        raise MemNetError(
            "echo_map",
            "Commit Δ must not echo the fetched pin_map; write only what changed",
        )
