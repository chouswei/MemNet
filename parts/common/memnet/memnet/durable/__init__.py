"""Durable online GQL store adapter seam (M2.5).

MemNet sessions remain the agent SSOT handle. This package sits *behind*
sessions (hydrate / flush, one sync owner). Agents keep talking GQL pin_map /
mutate to MemNet — not to AgensGraph / Neo4j / FakeDurableAdapter directly.

See docs/cabinet/agensgraph-buffer.md, docs/cabinet/neo4j-buffer.md, and
SysML DurableBuffer / AgensGraphAdapter / Neo4jAdapter.
"""

from __future__ import annotations

from memnet.durable.adapter import (
    DurableStoreAdapter,
    DurableSubgraph,
    HydrateBudget,
)
from memnet.durable.agensgraph import AgensGraphAdapter
from memnet.durable.factory import make_adapter_from_env, reset_adapter_factory_for_tests
from memnet.durable.fake import FakeDurableAdapter, company_ego_fixture
from memnet.durable.neo4j import Neo4jAdapter
from memnet.durable.neo4j_library import (
    Neo4jLibraryClient,
    make_library_client_from_env,
)
from memnet.durable.sync import (
    DurableSyncOwner,
    get_sync_owner,
    reset_sync_owner_for_tests,
)

__all__ = [
    "AgensGraphAdapter",
    "Neo4jAdapter",
    "Neo4jLibraryClient",
    "make_library_client_from_env",
    "DurableStoreAdapter",
    "DurableSubgraph",
    "DurableSyncOwner",
    "FakeDurableAdapter",
    "HydrateBudget",
    "company_ego_fixture",
    "get_sync_owner",
    "make_adapter_from_env",
    "reset_adapter_factory_for_tests",
    "reset_sync_owner_for_tests",
]
