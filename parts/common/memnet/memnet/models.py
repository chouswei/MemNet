"""Internal Pydantic types — not exposed on CLI."""

from __future__ import annotations

import itertools
from typing import Literal

from pydantic import BaseModel, Field

# Hidden store handle (elementId-style). Off the agent wire. Not a nickname.
_HID_SEQ = itertools.count(1)

# Keys that MUST NOT appear on product GQL / jsonl emit. Cabinet MERGE may
# keep ``_memnet_hid`` in-process. Nickname ``id`` is dropped on pin_map only.
SHAPE_DROP_KEYS = frozenset({"hid", "_memnet_hid", "elementId"})


def new_hid() -> str:
    return f"_el{next(_HID_SEQ)}"


class TagDef(BaseModel):
    tag: str
    fields: list[str]
    kind: Literal["node", "edge"] = "node"


class TagMap(BaseModel):
    tags: dict[str, TagDef] = Field(default_factory=dict)

    def get(self, tag: str) -> TagDef | None:
        return self.tags.get(tag.upper())

    def tag_names(self) -> list[str]:
        return sorted(self.tags.keys())


class Record(BaseModel):
    tag: str
    fields: dict[str, str]
    agent: str | None = None
    written_at: float | None = None
    # GraphElement identity in-process. MUST NOT appear on GQL emit / jsonl.
    hid: str = Field(default_factory=new_hid, exclude=True)

    @property
    def id(self) -> str:
        """Optional nickname property — not identity, not a store key."""
        return self.fields.get("id", "")

    @property
    def kind(self) -> Literal["node", "edge"]:
        return "edge" if self.tag == "EDG" else "node"

    def recycle_value(self) -> str | None:
        return self.fields.get("recycle")

    def is_recyclable(self) -> bool:
        val = self.recycle_value()
        return val in ("delete_on_settle", "delete_on_expire")


class SessionMeta(BaseModel):
    session_id: str
    created_at: str
    expires_at: str
    ttl_minutes: int
    has_writes: bool = False
    modified_at: str | None = None
    # CapsPolicy ACL presence flag (detail lives on SessionEntry.acl)
    acl_enabled: bool = False
