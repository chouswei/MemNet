"""In-process FakeDurableAdapter — proves the M2.5 seam without AgensGraph."""

from __future__ import annotations

from memnet.durable.adapter import DurableStoreAdapter, DurableSubgraph, HydrateBudget
from memnet.models import Record


def company_ego_fixture(ego_id: str = "COM_acme") -> DurableSubgraph:
    """Case-study company ego (durable-hydrate-flush-case-study.md)."""
    company = Record(
        tag="COM",
        fields={"id": ego_id, "name": "Acme", "kind": "company"},
    )
    task = Record(
        tag="TSK",
        fields={
            "id": "TSK_mission_q3",
            "goal": "Q3 mission",
            "status": "settled",
        },
    )
    edge = Record(
        tag="EDG",
        fields={
            "id": "E_about_q3",
            "src": "TSK_mission_q3",
            "relation": "ABOUT",
            "dist": ego_id,
        },
    )
    return DurableSubgraph(
        ego_id=ego_id,
        nodes=[company, task],
        edges=[edge],
        relations={"ABOUT"},
    )


class FakeDurableAdapter(DurableStoreAdapter):
    """Dict-backed durable store for tests and local spike demos."""

    def __init__(self, *, seed_company_ego: bool = False) -> None:
        self._by_ego: dict[str, DurableSubgraph] = {}
        if seed_company_ego:
            fixture = company_ego_fixture()
            self._by_ego[fixture.ego_id] = fixture

    @property
    def name(self) -> str:
        return "fake"

    def seed(self, subgraph: DurableSubgraph) -> None:
        self._by_ego[subgraph.ego_id] = DurableSubgraph(
            ego_id=subgraph.ego_id,
            nodes=list(subgraph.nodes),
            edges=list(subgraph.edges),
            relations=set(subgraph.relations),
        )

    def hydrate(self, ego_id: str, budget: HydrateBudget) -> DurableSubgraph:
        stored = self._by_ego.get(ego_id)
        if stored is None:
            return DurableSubgraph.empty(ego_id)
        return stored.bounded(budget)

    def flush(self, subgraph: DurableSubgraph) -> None:
        # Merge by record id (single fake writer — sync owner still required).
        existing = self._by_ego.get(subgraph.ego_id) or DurableSubgraph.empty(
            subgraph.ego_id
        )
        nodes = {r.id: r for r in existing.nodes}
        edges = {r.id: r for r in existing.edges}
        for r in subgraph.nodes:
            nodes[r.id] = r
        for r in subgraph.edges:
            edges[r.id] = r
        rels = set(existing.relations) | set(subgraph.relations)
        for e in edges.values():
            rel = e.fields.get("relation", "")
            if rel:
                rels.add(rel)
        self._by_ego[subgraph.ego_id] = DurableSubgraph(
            ego_id=subgraph.ego_id,
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            relations=rels,
        )

    def egos(self) -> list[str]:
        return sorted(self._by_ego)
