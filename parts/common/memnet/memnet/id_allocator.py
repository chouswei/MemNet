"""IdAllocator — mint NEW for goldfish mutate; pin-key path for ingest.

Goldfish: LLM writes [NEW] / NEW; engine allocates session-scoped ids.
Pin-map ingest: use allocate_from_locator (deterministic); never client NEW.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from memnet.records import Document, EdgeRec, NodeRec, Op

_NUM_SUFFIX = re.compile(r"^([A-Za-z_]+)(\d+)$")


@dataclass
class AssignedIdMap:
    """Maps mint placeholders to ground ids (order-preserving)."""

    mapping: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.mapping.get(key, default)


class IdAllocator:
    """Allocate session ids for NEW tokens; optional deterministic pin keys."""

    def __init__(self, existing_ids: set[str] | None = None) -> None:
        self._used: set[str] = set(existing_ids or ())
        self._seq: dict[str, int] = {}
        # Seed per-prefix seq from the existing ids so mint is max + 1: a gap
        # left by a deleted id is never refilled.
        for rid in self._used:
            m = _NUM_SUFFIX.match(rid)
            if m:
                prefix, n = m.group(1), int(m.group(2))
                if n > self._seq.get(prefix, 0):
                    self._seq[prefix] = n

    @classmethod
    def from_high_water(cls, high_water: dict[str, int], extra_ids=()) -> IdAllocator:
        """Allocator for ``mint`` / ``observe`` seeded from per-prefix high-water marks.

        ``high_water`` is MemStore.id_high_water(): for each prefix, at least the
        largest numeric suffix of any stored id. ``mint(prefix)`` then gives the
        same ids as ``IdAllocator(every stored id | extra_ids)``: a stored id of
        that prefix never exceeds the mark, so the old full set only ever held
        ids below the first candidate. Cost O(prefixes + extra_ids), not O(store).
        Not for ``allocate_from_locator`` (its "already used" check needs every id).
        """
        alloc = cls(set(extra_ids))
        for prefix, n in high_water.items():
            if n > alloc._seq.get(prefix, 0):
                alloc._seq[prefix] = n
        return alloc

    def observe(self, rid: str) -> None:
        if rid and rid != "NEW":
            self._used.add(rid)
            m = _NUM_SUFFIX.match(rid)
            if m:
                prefix, n = m.group(1), int(m.group(2))
                self._seq[prefix] = max(self._seq.get(prefix, 0), n)

    def mint(self, prefix: str) -> str:
        """Mint next free id with prefix (e.g. CLM -> CLM1, E -> E1)."""
        prefix = prefix or "N"
        n = self._seq.get(prefix, 0) + 1
        while f"{prefix}{n}" in self._used:
            n += 1
        self._seq[prefix] = n
        rid = f"{prefix}{n}"
        self._used.add(rid)
        return rid

    def allocate_from_locator(self, kind: str, locator_key: str) -> str:
        """Deterministic id for pin-map ingest (MN-REQ-11.16)."""
        safe = re.sub(r"[^A-Za-z0-9_]+", "_", locator_key).strip("_")
        rid = f"{kind}_{safe}" if safe else self.mint(kind)
        if rid in self._used:
            return rid
        self._used.add(rid)
        return rid

    def mint_document(self, doc: Document) -> AssignedIdMap:
        """Replace NEW / [NEW] in a Tier A Document; return AssignedIdMap.

        No-op (empty map) when the batch has no NEW tokens.
        """
        assigned = AssignedIdMap()
        # First pass: observe ground ids already present
        for it in doc.items:
            if isinstance(it, NodeRec) and it.id != "NEW":
                self.observe(it.id)
            elif isinstance(it, EdgeRec):
                if it.edge_id and it.edge_id != "NEW":
                    self.observe(it.edge_id)
                if it.frm and it.frm != "NEW":
                    self.observe(it.frm)
                if it.to and it.to != "NEW":
                    self.observe(it.to)

        new_node_i = 0
        new_edge_i = 0
        for it in doc.items:
            if isinstance(it, NodeRec) and it.op == Op.CREATE and it.id == "NEW":
                prefix = it.kind if it.kind else "N"
                rid = self.mint(prefix)
                key = f"NEW_node_{new_node_i}"
                new_node_i += 1
                assigned.mapping[key] = rid
                it.id = rid
            elif isinstance(it, EdgeRec) and it.op == Op.CREATE:
                if it.edge_id == "NEW" or it.edge_id is None:
                    rid = self.mint("E")
                    key = f"NEW_edge_{new_edge_i}"
                    new_edge_i += 1
                    assigned.mapping[key] = rid
                    it.edge_id = rid
                # Endpoints NEW: rare open case — mint opaque N*
                if it.frm == "NEW":
                    it.frm = self.mint("N")
                if it.to == "NEW":
                    it.to = self.mint("N")
        return assigned
