"""Backward-compatible shim — acquaintance SSOT is ``entity_knowledge``."""

from __future__ import annotations

from novel_mcp.entity_knowledge import (
    DEPTH_RANK,
    build_knowledge_view,
    can_speak_about,
    depth_rank,
    entity_refs_missing_from_warm,
    format_knowledge_hud,
    knowledge_gate_hint,
    merge_warm_catalog_lines,
    parse_warm_knowledge,
)

# Legacy names
knw_refs_missing_from_warm = entity_refs_missing_from_warm
merge_warm_knw_lines = merge_warm_catalog_lines

__all__ = [
    "DEPTH_RANK",
    "build_knowledge_view",
    "can_speak_about",
    "depth_rank",
    "entity_refs_missing_from_warm",
    "format_knowledge_hud",
    "knw_refs_missing_from_warm",
    "knowledge_gate_hint",
    "merge_warm_catalog_lines",
    "merge_warm_knw_lines",
    "parse_warm_knowledge",
]
