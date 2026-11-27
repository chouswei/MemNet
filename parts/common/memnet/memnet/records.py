"""Mutate record data classes shared by the GQL parser, MutateGate and IdAllocator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from memnet.config import standard_relation


class Op(str, Enum):  # noqa: UP042
    CREATE = "+"
    PATCH = "~"
    DROP = "-"
    LAW = "LAW"
    PRESENT = ""  # pin-map display: bare atom (no mutate op)


@dataclass
class Field:
    key: str
    op: str  # "=", "+=", "-="
    value: str


@dataclass
class NodeRec:
    op: Op
    kind: str
    id: str  # optional nickname; empty when omitted
    fields: list[Field] = field(default_factory=list)
    raw: str = ""
    match_props: dict[str, str] = field(default_factory=dict)
    # SameThingAbsorb Commit (MATCH (a),(b) SET a += b). Not a product verb.
    same_thing: bool = False
    absorb_kind: str = ""
    absorb_match_props: dict[str, str] = field(default_factory=dict)
    where: object | None = None


@dataclass
class EdgeRec:
    op: Op
    edge_id: str | None  # optional nickname; empty/None when omitted
    frm: str
    rel: str
    to: str
    fields: list[Field] = field(default_factory=list)
    raw: str = ""
    frm_label: str = ""
    to_label: str = ""
    frm_props: dict[str, str] = field(default_factory=dict)
    to_props: dict[str, str] = field(default_factory=dict)
    # Spelling as written when it differs from the standard ``rel`` (echoed back).
    rel_written: str = ""

    def __post_init__(self) -> None:
        std = standard_relation(self.rel)
        if std != self.rel:
            self.rel_written, self.rel = self.rel, std


@dataclass
class Section:
    name: str
    raw: str = ""


@dataclass
class Document:
    items: list[Section | NodeRec | EdgeRec] = field(default_factory=list)
