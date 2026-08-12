"""One sync owner for hydrate/flush — MUST NOT dual-write."""

from __future__ import annotations

from memnet.durable.adapter import DurableStoreAdapter, DurableSubgraph, HydrateBudget
from memnet.durable.factory import make_adapter_from_env
from memnet.exceptions import MemNetError
from memnet.session import SessionStore

_OWNER: DurableSyncOwner | None = None


class DurableSyncOwner:
    """Sole process-local writer between sessions and the durable adapter.

    SysML: DurableHydrateFlow / DurableFlushFlow via SessionLifecycle ports.
    """

    def __init__(self, adapter: DurableStoreAdapter) -> None:
        self._adapter = adapter

    @property
    def adapter(self) -> DurableStoreAdapter:
        return self._adapter

    @property
    def adapter_name(self) -> str:
        return self._adapter.name

    def hydrate_into_session(
        self,
        session: SessionStore,
        ego_id: str,
        budget: HydrateBudget | None = None,
    ) -> DurableSubgraph:
        """Pull ego slice from durable store into the live session under budget."""
        if not ego_id or not str(ego_id).strip():
            raise MemNetError("no_ego", "hydrate requires ego_id")
        budget = budget or HydrateBudget()
        subgraph = self._adapter.hydrate(ego_id, budget).bounded(budget)
        with session.lock(exclusive=True):
            for rec in subgraph.all_records():
                session.store.upsert(
                    rec,
                    allow_new_relation=True,
                    relations=session.relations,
                )
            session.mark_written()
        return subgraph

    def flush_from_session(
        self,
        session: SessionStore,
        ego_id: str,
        budget: HydrateBudget | None = None,
    ) -> DurableSubgraph:
        """Push ego-bounded live slice to durable store (settled / durable pins)."""
        if not ego_id or not str(ego_id).strip():
            raise MemNetError("no_ego", "flush requires ego_id")
        budget = budget or HydrateBudget()
        with session.lock(exclusive=True):
            rows = session.store.context_pack(
                anchor_id=ego_id,
                depth=budget.depth,
                max_rows=budget.max_nodes + budget.max_edges,
                active_only=True,
            )
            session.touch()
        nodes = [r for r in rows if r.tag != "EDG" and r.tag != "LAW"]
        edges = [r for r in rows if r.tag == "EDG"]
        rels = {
            e.fields.get("relation", "")
            for e in edges
            if e.fields.get("relation")
        }
        subgraph = DurableSubgraph(
            ego_id=ego_id,
            nodes=nodes,
            edges=edges,
            relations=rels,
        ).bounded(budget)
        self._adapter.flush(subgraph)
        return subgraph


def get_sync_owner(adapter: DurableStoreAdapter | None = None) -> DurableSyncOwner:
    """Return the process-wide sync owner; bind adapter on first call only."""
    global _OWNER
    if _OWNER is None:
        _OWNER = DurableSyncOwner(adapter if adapter is not None else make_adapter_from_env())
        return _OWNER
    if adapter is not None and adapter is not _OWNER.adapter:
        raise MemNetError(
            "dual_sync_owner",
            "MUST NOT dual-write: a DurableSyncOwner is already bound in this "
            "process. Reset only in tests, or reuse get_sync_owner().",
        )
    return _OWNER


def reset_sync_owner_for_tests() -> None:
    """Drop the process owner (tests only)."""
    global _OWNER
    if _OWNER is not None:
        _OWNER.adapter.close()
    _OWNER = None
