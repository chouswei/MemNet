"""Generic graph presentation helpers (wire vs walk views)."""

from __future__ import annotations


def format_walk_hop(src: str, relation: str, dst: str) -> str:
    rel = relation.replace("|", " ")
    return f"@WALK: {src} -[{rel}]-> {dst}"
