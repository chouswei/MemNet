"""Built-in EDG + LAW + PROXY field definitions."""

from __future__ import annotations

from memnet.models import TagDef, TagMap

EDG_FIELDS = ["id", "src", "relation", "dist", "at", "attrs", "recycle"]
LAW_FIELDS = ["id", "name", "cycle", "mechanism", "constraint"]
# One-hop pointer to a node in a session (memnet.proxy). Not a reserved tag: it is written.
PROXY_FIELDS = ["id", "target_session", "target", "target_backend"]

FIXED_TAGS: dict[str, TagDef] = {
    "EDG": TagDef(tag="EDG", fields=EDG_FIELDS, kind="edge"),
    "LAW": TagDef(tag="LAW", fields=LAW_FIELDS, kind="node"),
    "PROXY": TagDef(tag="PROXY", fields=PROXY_FIELDS, kind="node"),
}

# Fixed tags whose SCHEMA line a snapshot does not carry (the loader merges every
# fixed tag back in). A snapshot with no PROXY row stays byte-identical to 0.20.8,
# and a build without the PROXY tag refuses a PROXY row unknown_tag.
SNAPSHOT_OMIT_SCHEMA = frozenset({"PROXY"})


def fixed_tag_map() -> TagMap:
    return TagMap(tags=dict(FIXED_TAGS))
