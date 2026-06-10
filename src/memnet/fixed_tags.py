"""Built-in EDG + LAW field definitions."""

from __future__ import annotations

from memnet.models import TagDef, TagMap

EDG_FIELDS = ["id", "src", "relation", "dist", "attrs", "recycle"]
LAW_FIELDS = ["id", "name", "cycle", "mechanism", "constraint"]

FIXED_TAGS: dict[str, TagDef] = {
    "EDG": TagDef(tag="EDG", fields=EDG_FIELDS, kind="edge"),
    "LAW": TagDef(tag="LAW", fields=LAW_FIELDS, kind="node"),
}


def fixed_tag_map() -> TagMap:
    return TagMap(tags=dict(FIXED_TAGS))
