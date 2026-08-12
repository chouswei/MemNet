"""Env → adapter selection. Prefer real AgensGraph when configured."""

from __future__ import annotations

import os

from memnet.durable.adapter import DurableStoreAdapter
from memnet.durable.agensgraph import AgensGraphAdapter
from memnet.durable.fake import FakeDurableAdapter

# When set to "1"/"true", make_adapter_from_env returns Fake even without URL
# (explicit local spike). Default without URL is also Fake for tests/dev.
ENV_USE_FAKE = "MEMNET_DURABLE_FAKE"


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in {"1", "true", "yes", "on"}


def make_adapter_from_env() -> DurableStoreAdapter:
    """Return AgensGraphAdapter when URL set; else FakeDurableAdapter.

    Fake is a *seam* stand-in, not a production durable store. Agents still
    MUST NOT talk to either adapter directly.
    """
    if _truthy(os.environ.get(ENV_USE_FAKE)):
        seed = _truthy(os.environ.get("MEMNET_DURABLE_FAKE_SEED_COMPANY"))
        return FakeDurableAdapter(seed_company_ego=seed)
    agens = AgensGraphAdapter.from_env()
    if agens is not None:
        return agens
    return FakeDurableAdapter(seed_company_ego=False)


def reset_adapter_factory_for_tests() -> None:
    """Hook for tests — factory is currently pure; reserved for future cache."""
