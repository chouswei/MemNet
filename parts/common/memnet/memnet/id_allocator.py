"""IdAllocator — mint NEW for goldfish mutate; pin-key path for ingest.

Goldfish: LLM writes [NEW] / NEW; engine allocates session-scoped ids.
Pin-map ingest: use allocate_from_locator (deterministic); never client NEW.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from memnet.tier_a import Document, EdgeRec, NodeRec, Op

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
