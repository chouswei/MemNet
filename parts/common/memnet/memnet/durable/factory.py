"""Env → adapter selection. Prefer a real cabinet when configured."""

from __future__ import annotations

import logging
import os

from memnet.durable.adapter import DurableStoreAdapter
from memnet.durable.agensgraph import AgensGraphAdapter
from memnet.durable.fake import FakeDurableAdapter

logger = logging.getLogger(__name__)

# When set to "1"/"true", make_adapter_from_env returns Fake even if URL is set
# (explicit local spike / CI). Without URL, Fake is also the default *seam*
# stand-in — not a production durable cabinet.
ENV_USE_FAKE = "MEMNET_DURABLE_FAKE"
_NEO4J_ENV_PREFIX = "MEMNET_NEO4J_"
_neo4j_retired_warned = False


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in {"1", "true", "yes", "on"}


def warn_retired_neo4j_env() -> None:
    """Ignore ``MEMNET_NEO4J_*``. One warning. Names only — never values. Never raise."""
    global _neo4j_retired_warned
    if _neo4j_retired_warned:
        return
    present = sorted(key for key in os.environ if key.startswith(_NEO4J_ENV_PREFIX))
    if not present:
        return
    _neo4j_retired_warned = True
    logger.warning(
        "Ignoring retired Neo4j settings (%s). Neo4j cabinet is archived. Starting without it.",
        ", ".join(present),
    )


def reset_neo4j_retired_warning_for_tests() -> None:
    """Allow a later test to observe the one-shot warning again."""
    global _neo4j_retired_warned
    _neo4j_retired_warned = False


def make_adapter_from_env() -> DurableStoreAdapter:
    """Bind one DurableStoreAdapter for ``get_sync_owner()``.

    Semantics (serve / MCP bind the result once via ``get_sync_owner()``):

    - ``MEMNET_NEO4J_*`` is ignored. One log warning. The engine starts.
      SHALL NOT crash. SHALL NOT bind a Neo4j adapter.
    - ``MEMNET_DURABLE_FAKE`` truthy → Fake (even if an AgensGraph URL is set)
    - else ``MEMNET_AGENSGRAPH_URL`` set → ``AgensGraphAdapter``
    - else → Fake seam stand-in for tests/dev

    Factory binds exactly one of fake or AgensGraph. Fake is **not** a
    production durable store. Agents still MUST NOT talk to the adapter
    directly — only ``DurableSyncOwner`` / SessionLifecycle ports.
    """
    warn_retired_neo4j_env()
    if _truthy(os.environ.get(ENV_USE_FAKE)):
        seed = _truthy(os.environ.get("MEMNET_DURABLE_FAKE_SEED_COMPANY"))
        return FakeDurableAdapter(seed_company_ego=seed)
    agens = AgensGraphAdapter.from_env()
    if agens is not None:
        return agens
    return FakeDurableAdapter(seed_company_ego=False)


def reset_adapter_factory_for_tests() -> None:
    """Hook for tests — factory is currently pure; reserved for future cache."""
    reset_neo4j_retired_warning_for_tests()
