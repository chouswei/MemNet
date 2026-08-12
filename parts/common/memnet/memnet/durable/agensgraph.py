"""AgensGraphAdapter — env-configured spike; real driver optional.

Connection placeholders (never hardcode secrets):

- MEMNET_AGENSGRAPH_URL       e.g. postgresql://host:5432/memnet
- MEMNET_AGENSGRAPH_USER
- MEMNET_AGENSGRAPH_PASSWORD
- MEMNET_AGENSGRAPH_GRAPH     optional named graph (AgensGraph)

This module does **not** teach LLM ↔ AgensGraph direct. Wire stays MemNet
GQL pin_map / mutate; the sync owner alone calls hydrate/flush.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from memnet.durable.adapter import DurableStoreAdapter, DurableSubgraph, HydrateBudget
from memnet.exceptions import MemNetError

ENV_URL = "MEMNET_AGENSGRAPH_URL"
ENV_USER = "MEMNET_AGENSGRAPH_USER"
ENV_PASSWORD = "MEMNET_AGENSGRAPH_PASSWORD"
ENV_GRAPH = "MEMNET_AGENSGRAPH_GRAPH"


@dataclass(frozen=True)
class AgensGraphConfig:
    url: str
    user: str | None = None
    password: str | None = None
    graph: str | None = None

    @classmethod
    def from_env(cls) -> AgensGraphConfig | None:
        url = (os.environ.get(ENV_URL) or "").strip()
        if not url:
            return None
        return cls(
            url=url,
            user=(os.environ.get(ENV_USER) or "").strip() or None,
            password=os.environ.get(ENV_PASSWORD) or None,
            graph=(os.environ.get(ENV_GRAPH) or "").strip() or None,
        )


class AgensGraphAdapter(DurableStoreAdapter):
    """Planned real adapter. Raises clearly until psycopg + store are wired."""

    def __init__(self, config: AgensGraphConfig) -> None:
        self.config = config
        self._conn = None

    @classmethod
    def from_env(cls) -> AgensGraphAdapter | None:
        cfg = AgensGraphConfig.from_env()
        if cfg is None:
            return None
        return cls(cfg)

    @property
    def name(self) -> str:
        return "agensgraph"

    def hydrate(self, ego_id: str, budget: HydrateBudget) -> DurableSubgraph:
        del ego_id, budget
        self._require_driver()
        raise MemNetError(
            "agensgraph_not_implemented",
            "AgensGraph hydrate spike: driver present but Cypher hydrate "
            "not wired yet — use FakeDurableAdapter for the seam; see "
            "docs/grammar/agensgraph-buffer.md",
        )

    def flush(self, subgraph: DurableSubgraph) -> None:
        del subgraph
        self._require_driver()
        raise MemNetError(
            "agensgraph_not_implemented",
            "AgensGraph flush spike: driver present but Cypher flush "
            "not wired yet — use FakeDurableAdapter for the seam; see "
            "docs/grammar/agensgraph-buffer.md",
        )

    def close(self) -> None:
        conn = self._conn
        self._conn = None
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001 — best-effort close
                pass

    def _require_driver(self) -> None:
        try:
            import psycopg  # noqa: F401
        except ImportError as exc:
            raise MemNetError(
                "agensgraph_unavailable",
                "MEMNET_AGENSGRAPH_URL is set but psycopg is not installed. "
                "Install psycopg into the MemNet venv, or unset the URL and "
                "use FakeDurableAdapter for local seam tests.",
                example="pip install 'psycopg[binary]'",
            ) from exc
