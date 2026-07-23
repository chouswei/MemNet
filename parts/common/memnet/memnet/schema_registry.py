"""SchemaRegistry — session schema (tag/kind + fields); TagMap is legacy surface."""

from __future__ import annotations

from memnet.models import TagDef, TagMap
from memnet.tag_map import (
    example_ingest_line,
    load_map_from_file,
    load_map_from_lines,
    load_persisted_map_from_lines,
    load_user_map,
    merge_fixed,
    parse_line,
    parse_map_line,
    tag_map_to_lines,
    validate_id,
    validate_values,
)

SchemaRegistry = TagMap

__all__ = [
    "SchemaRegistry",
    "TagDef",
    "TagMap",
    "example_ingest_line",
    "load_map_from_file",
    "load_map_from_lines",
    "load_persisted_map_from_lines",
    "load_user_map",
    "merge_fixed",
    "parse_line",
    "parse_map_line",
    "tag_map_to_lines",
    "validate_id",
    "validate_values",
]
