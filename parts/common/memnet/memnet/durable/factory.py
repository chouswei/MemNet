"""Env → adapter selection. Prefer a real cabinet when configured."""

from __future__ import annotations

import os

from memnet.durable.adapter import DurableStoreAdapter
from memnet.durable.agensgraph import AgensGraphAdapter
from memnet.durable.fake import FakeDurableAdapter
from memnet.durable.neo4j import Neo4jAdapter
from memnet.exceptions import MemNetError

# When set to "1"/"true", make_adapter_from_env returns Fake even if URL is set
# (explicit local spike / CI). Without URL, Fake is also the default *seam*
# stand-in — not a production durable cabinet.
ENV_USE_FAKE = "MEMNET_DURABLE_FAKE"
ENV_BACKEND = "MEMNET_DURABLE_BACKEND"


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in {"1", "true", "yes", "on"}


def make_adapter_from_env() -> DurableStoreAdapter:
    """Bind one DurableStoreAdapter for ``get_sync_owner()``.

    Semantics (serve / MCP bind the result once via ``get_sync_owner()``):

    - ``MEMNET_DURABLE_FAKE`` truthy → Fake (even if URLs are set)
    - else both AgensGraph and Neo4j URLs set → error unless
      ``MEMNET_DURABLE_BACKEND`` is ``agensgraph`` or ``neo4j``
      (one sync owner; do not silently pick)
    - else ``MEMNET_AGENSGRAPH_URL`` set → ``AgensGraphAdapter``
    - else ``MEMNET_NEO4J_URL`` set → ``Neo4jAdapter``
    - else → Fake seam stand-in for tests/dev

    Fake is **not** a production durable store. Agents still MUST NOT talk to
    either adapter directly — only ``DurableSyncOwner`` / SessionLifecycle ports.
    """
    if _truthy(os.environ.get(ENV_USE_FAKE)):
        seed = _truthy(os.environ.get("MEMNET_DURABLE_FAKE_SEED_COMPANY"))
        return FakeDurableAdapter(seed_company_ego=seed)
    agens = AgensGraphAdapter.from_env()
    neo4j = Neo4jAdapter.from_env()
    if agens is not None and neo4j is not None:
        backend = (os.environ.get(ENV_BACKEND) or "").strip().lower()
        if backend == "agensgraph":
            return agens
        if backend == "neo4j":
            return neo4j
        raise MemNetError(
            "durable_backend_conflict",
            "Both MEMNET_AGENSGRAPH_URL and MEMNET_NEO4J_URL are set. "
            "Set MEMNET_DURABLE_BACKEND to 'agensgraph' or 'neo4j' "
            "(one sync owner; do not silently pick).",
            example="export MEMNET_DURABLE_BACKEND=neo4j",
        )
    if agens is not None:
        return agens
    if neo4j is not None:
        return neo4j
    return FakeDurableAdapter(seed_company_ego=False)


def reset_adapter_factory_for_tests() -> None:
    """Hook for tests — factory is currently pure; reserved for future cache."""
