"""Internal Pydantic types — not exposed on CLI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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

    @property
    def id(self) -> str:
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
