"""LLM-backed martial catalog expansion at bootstrap (novel_cursor adapter)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from llm_client import complete_messages

from novel_mcp.catalog_schema import CatalogSchema
from novel_mcp.martial_catalog_expand import expand_martial_catalog


def llm_complete(system: str, user: str, *, config: Any = None) -> str:
    return complete_messages(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        role="script",
        config=config,
    )


def load_schema(config: Any) -> CatalogSchema:
    path = getattr(config, "catalog_schema", None)
    if path is None or not Path(path).is_file():
        raise RuntimeError(
            "catalog_schema missing on instance json (required for catalog expand)"
        )
    return CatalogSchema.load_json(path)


def run_catalog_expand(
    session: str,
    *,
    schema: CatalogSchema,
    target: int = 80,
    seed: int | None = None,
    config: Any = None,
) -> dict[str, Any]:
    return expand_martial_catalog(
        session,
        schema,
        target_count=target,
        llm_complete=lambda s, u: llm_complete(s, u, config=config),
        seed=seed,
    )
