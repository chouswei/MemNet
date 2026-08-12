"""DurableStoreAdapter ABC — hydrate / flush contract behind sessions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from memnet.models import Record


@dataclass(frozen=True)
class HydrateBudget:
    """Pin / depth / view budget for ego-bounded hydrate (MN-REQ-06.4)."""

    max_nodes: int = 50
    max_edges: int = 100
    depth: int = 2
    view: str | None = None


@dataclass
class DurableSubgraph:
    """Ego-bounded property-graph slice exchanged with the durable store."""

    ego_id: str
    nodes: list[Record] = field(default_factory=list)
    edges: list[Record] = field(default_factory=list)
    relations: set[str] = field(default_factory=set)

    @classmethod
    def empty(cls, ego_id: str) -> DurableSubgraph:
        return cls(ego_id=ego_id)

    def bounded(self, budget: HydrateBudget) -> DurableSubgraph:
        """Apply soft node/edge caps (depth is adapter-side for real stores)."""
        nodes = list(self.nodes)
        if self.ego_id:
            nodes = sorted(nodes, key=lambda r: (0 if r.id == self.ego_id else 1, r.id))
        nodes = nodes[: max(0, budget.max_nodes)]
        kept = {r.id for r in nodes}
        edges: list[Record] = []
        if budget.max_edges > 0:
            for e in sorted(self.edges, key=lambda r: r.id):
                src = e.fields.get("src", "")
                dist = e.fields.get("dist", "")
                if src in kept or dist in kept or not kept:
                    edges.append(e)
                if len(edges) >= budget.max_edges:
                    break
        rels = set(self.relations)
        for e in edges:
            rel = e.fields.get("relation", "")
            if rel:
                rels.add(rel)
        return DurableSubgraph(
            ego_id=self.ego_id,
            nodes=nodes,
            edges=edges,
            relations=rels,
        )

    def all_records(self) -> list[Record]:
        """Nodes first, then edges — safe order for upsert into a live session."""
        return list(self.nodes) + list(self.edges)


class DurableStoreAdapter(ABC):
    """Backing-store port: pull / push ego slices. Not an agent teach surface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short adapter id for logs / diagnostics."""

    @abstractmethod
    def hydrate(self, ego_id: str, budget: HydrateBudget) -> DurableSubgraph:
        """Pull an ego-bounded durable subgraph (may be empty)."""

    @abstractmethod
    def flush(self, subgraph: DurableSubgraph) -> None:
        """Push a settled / durable subgraph into the backing store."""

    def close(self) -> None:
        """Release connections; default no-op."""
