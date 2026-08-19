"""Neo4jAdapter — client/adapter for an *external* Neo4j cabinet.

Connection placeholders (never hardcode secrets):

- MEMNET_NEO4J_URL        e.g. bolt://127.0.0.1:7687 or neo4j://…
- MEMNET_NEO4J_USER
- MEMNET_NEO4J_PASSWORD
- MEMNET_NEO4J_DATABASE   named database (default: neo4j)

This module is a **client** only: it speaks Neo4j Cypher over the official
``neo4j`` Python driver to a store the operator already runs. It does
**not** vendor or require a Neo4j server binary in this repo.

Wire stays MemNet GQL pin_map / mutate; the sync owner alone calls
hydrate/flush. Agents MUST NOT talk Bolt.

Live Bolt round-trip is **not** claimed here (``liveNeo4jClaimed=false``).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

from memnet.durable.adapter import DurableStoreAdapter, DurableSubgraph, HydrateBudget
from memnet.durable.agensgraph import map_edge_row, map_node_row
from memnet.exceptions import MemNetError
from memnet.models import Record

ENV_URL = "MEMNET_NEO4J_URL"
ENV_USER = "MEMNET_NEO4J_USER"
ENV_PASSWORD = "MEMNET_NEO4J_PASSWORD"
ENV_DATABASE = "MEMNET_NEO4J_DATABASE"

DEFAULT_DATABASE = "neo4j"
_MEMNET_TAG_KEY = "_memnet_tag"
_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:/@+-]+$")


@dataclass(frozen=True)
class Neo4jConfig:
    url: str
    user: str | None = None
    password: str | None = None
    database: str | None = None

    @classmethod
    def from_env(cls) -> Neo4jConfig | None:
        url = (os.environ.get(ENV_URL) or "").strip()
        if not url:
            return None
        return cls(
            url=url,
            user=(os.environ.get(ENV_USER) or "").strip() or None,
            password=os.environ.get(ENV_PASSWORD) or None,
            database=(os.environ.get(ENV_DATABASE) or "").strip() or None,
        )

    @property
    def database_name(self) -> str:
        return self.database or DEFAULT_DATABASE


def cypher_ident(name: str, *, kind: str = "label") -> str:
    """Validate and return a Neo4j identifier (node label / rel type)."""
    if not name or not _SAFE_IDENT.match(name):
        raise MemNetError(
            "neo4j_bad_ident",
            f"Neo4j {kind} must be a simple identifier, got {name!r}",
        )
    return name


def require_id(value: str, *, kind: str = "id") -> str:
    """Reject unsafe MemNet ids before they reach Bolt parameters."""
    if not value or not _SAFE_ID.match(value):
        raise MemNetError(
            "neo4j_bad_id",
            f"Neo4j {kind} must be a simple token, got {value!r}",
        )
    return value


def props_for_set(fields: dict[str, str], *, skip: set[str]) -> dict[str, str]:
    """String fields with safe keys — values travel as Bolt parameters."""
    out: dict[str, str] = {}
    for key, val in fields.items():
        if key in skip or not _SAFE_IDENT.match(key):
            continue
        out[key] = str(val)
    return out


def build_hydrate_nodes_cypher(ego_id: str, budget: HydrateBudget) -> tuple[str, dict[str, Any]]:
    """Ego-bounded node walk: vertices within ``budget.depth`` of ego.

    Neo4j Cypher: ``labels(n)`` (list), not AgensGraph ``label(n)``.
    """
    ego = require_id(ego_id, kind="ego id")
    depth = max(0, int(budget.depth))
    limit = max(1, int(budget.max_nodes))
    query = (
        "MATCH (ego {_memnet_hid: $ego_id})\n"
        f"OPTIONAL MATCH (ego)-[*0..{depth}]-(n)\n"
        "WITH DISTINCT n\n"
        "WHERE n IS NOT NULL\n"
        "RETURN labels(n) AS labels, properties(n) AS props\n"
        f"LIMIT {limit}"
    )
    return query, {"ego_id": ego}


def build_hydrate_edges_cypher(
    ego_id: str,
    budget: HydrateBudget,
    node_ids: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Edges whose both endpoints lie inside the already-hydrated node set."""
    ego = require_id(ego_id, kind="ego id")
    limit = max(0, int(budget.max_edges))
    skip = (
        "MATCH (ego {_memnet_hid: $ego_id})\n"
        "WHERE false\n"
        "RETURN null AS rel_type, null AS props, null AS src, null AS dist\n"
        "LIMIT 0"
    )
    if limit == 0:
        return skip, {"ego_id": ego}
    ids = [require_id(i) for i in (node_ids or []) if i]
    if not ids:
        return skip, {"ego_id": ego}
    query = (
        "MATCH (src)-[rel]->(dst)\n"
        "WHERE src._memnet_hid IN $node_ids AND dst._memnet_hid IN $node_ids\n"
        "RETURN DISTINCT type(rel) AS rel_type, properties(rel) AS props, "
        "src._memnet_hid AS src, dst._memnet_hid AS dist\n"
        f"LIMIT {limit}"
    )
    return query, {"node_ids": ids}


def build_merge_node_cypher(record: Record) -> tuple[str, dict[str, Any]]:
    """MERGE/SET one MemNet node record into Neo4j."""
    tag = cypher_ident(record.tag.upper(), kind="node label")
    query = f"MERGE (n:{tag} {{_memnet_hid: $hid}})\nSET n += $props, n.{_MEMNET_TAG_KEY} = $tag"
    hid = record.hid if getattr(record, "hid", "") else (record.id or "")
    if hid:
        hid = require_id(hid, kind="hid")
    props = props_for_set(dict(record.fields), skip=set())
    return query, {"hid": hid, "props": props, "tag": record.tag.upper()}


def build_merge_edge_cypher(record: Record) -> tuple[str, dict[str, Any]]:
    """MERGE/SET one MemNet EDG record (relation → relationship type)."""
    if record.tag.upper() != "EDG":
        raise MemNetError(
            "neo4j_bad_edge",
            f"flush edge expects tag EDG, got {record.tag!r}",
        )
    src = record.fields.get("src") or ""
    dist = record.fields.get("dist") or ""
    rel = record.fields.get("relation") or ""
    if not src or not dist or not rel:
        raise MemNetError(
            "neo4j_bad_edge",
            "flush edge requires fields src, dist, relation",
        )
    rel_type = cypher_ident(rel, kind="relationship type")
    src_id = require_id(src, kind="src hid")
    dist_id = require_id(dist, kind="dist hid")
    skip = {"src", "dist", "relation"}
    props = props_for_set(dict(record.fields), skip=skip)
    hid = record.hid if getattr(record, "hid", "") else (record.id or "")
    merge_edge = f"MERGE (a)-[r:{rel_type}]->(b)"
    params: dict[str, Any] = {
        "src": src_id,
        "dist": dist_id,
        "props": props,
        "rel": rel,
    }
    if hid:
        params["hid"] = require_id(hid, kind="hid")
        merge_edge = f"MERGE (a)-[r:{rel_type} {{_memnet_hid: $hid}}]->(b)"
    query = (
        "MATCH (a {_memnet_hid: $src}), (b {_memnet_hid: $dist})\n"
        f"{merge_edge}\n"
        f"SET r += $props, r.{_MEMNET_TAG_KEY} = 'EDG', r.relation = $rel"
    )
    return query, params


def first_label(labels: Any) -> str:
    """Pick a single label from Neo4j ``labels(n)`` (list) or a scalar."""
    if labels is None:
        return ""
    if isinstance(labels, str):
        return labels
    if isinstance(labels, (list, tuple)):
        for item in labels:
            if item:
                return str(item)
        return ""
    return str(labels)


class Neo4jAdapter(DurableStoreAdapter):
    """Client adapter: hydrate/flush ego slices against external Neo4j."""

    def __init__(self, config: Neo4jConfig) -> None:
        self.config = config
        self._driver: Any = None

    @classmethod
    def from_env(cls) -> Neo4jAdapter | None:
        cfg = Neo4jConfig.from_env()
        if cfg is None:
            return None
        return cls(cfg)

    @property
    def name(self) -> str:
        return "neo4j"

    def hydrate(self, ego_id: str, budget: HydrateBudget) -> DurableSubgraph:
        if not ego_id or not str(ego_id).strip():
            raise MemNetError("no_ego", "hydrate requires ego_id")
        budget = budget or HydrateBudget()
        self._ensure_driver()
        nodes_cypher, nodes_params = build_hydrate_nodes_cypher(ego_id, budget)
        try:
            node_rows = self._run(nodes_cypher, nodes_params)
        except MemNetError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface driver errors clearly
            raise MemNetError(
                "neo4j_query_failed",
                f"Neo4j hydrate query failed: {type(exc).__name__}: {exc}",
                example="Check MEMNET_NEO4J_URL / database / network",
            ) from exc

        nodes: list[Record] = []
        seen_nodes: set[str] = set()
        for row in node_rows:
            rec = map_node_row(
                first_label(_row_get(row, 0, "labels")),
                _row_get(row, 1, "props"),
            )
            if rec is None or rec.id in seen_nodes:
                continue
            seen_nodes.add(rec.id)
            nodes.append(rec)

        edges_cypher, edges_params = build_hydrate_edges_cypher(
            ego_id, budget, node_ids=[n.id for n in nodes]
        )
        try:
            edge_rows = self._run(edges_cypher, edges_params) if budget.max_edges > 0 else []
        except MemNetError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MemNetError(
                "neo4j_query_failed",
                f"Neo4j hydrate query failed: {type(exc).__name__}: {exc}",
                example="Check MEMNET_NEO4J_URL / database / network",
            ) from exc

        edges: list[Record] = []
        seen_edges: set[str] = set()
        relations: set[str] = set()
        for row in edge_rows:
            rec = map_edge_row(
                _row_get(row, 0, "rel_type"),
                _row_get(row, 1, "props"),
                _row_get(row, 2, "src"),
                _row_get(row, 3, "dist"),
            )
            if rec is None or rec.id in seen_edges:
                continue
            seen_edges.add(rec.id)
            edges.append(rec)
            rel = rec.fields.get("relation") or ""
            if rel:
                relations.add(rel)

        return DurableSubgraph(
            ego_id=ego_id,
            nodes=nodes,
            edges=edges,
            relations=relations,
        ).bounded(budget)

    def flush(self, subgraph: DurableSubgraph) -> None:
        if subgraph is None:
            raise MemNetError("neo4j_bad_flush", "flush requires a DurableSubgraph")
        self._ensure_driver()
        statements: list[tuple[str, dict[str, Any]]] = []
        for rec in subgraph.nodes:
            if not rec.id:
                continue
            statements.append(build_merge_node_cypher(rec))
        for rec in subgraph.edges:
            if rec.tag.upper() != "EDG":
                continue
            statements.append(build_merge_edge_cypher(rec))
        if not statements:
            return
        # Auto-commit each MERGE (Neo4j session.run). A later hydrate error
        # cannot roll back a successful flush (AgensGraph 0.7 lesson).
        try:
            for cypher, params in statements:
                self._run(cypher, params)
        except MemNetError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MemNetError(
                "neo4j_query_failed",
                f"Neo4j flush failed: {type(exc).__name__}: {exc}",
                example="Check MERGE permissions / endpoint ids exist",
            ) from exc

    def close(self) -> None:
        driver = self._driver
        self._driver = None
        if driver is not None:
            try:
                driver.close()
            except Exception:  # noqa: BLE001 — best-effort close
                pass

    def _import_graphdatabase(self) -> Any:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise MemNetError(
                "neo4j_unavailable",
                "MEMNET_NEO4J_URL is set but the neo4j driver is not installed. "
                "Install the optional client extra, or unset the URL and use "
                "FakeDurableAdapter for local seam tests.",
                example="pip install 'memnet-llm[neo4j]'  # or: pip install neo4j",
            ) from exc
        return GraphDatabase

    def _ensure_driver(self) -> Any:
        if self._driver is not None:
            return self._driver
        GraphDatabase = self._import_graphdatabase()
        kwargs: dict[str, Any] = {}
        if self.config.user is not None:
            kwargs["auth"] = (self.config.user, self.config.password or "")
        try:
            driver = GraphDatabase.driver(self.config.url, **kwargs)
        except MemNetError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MemNetError(
                "neo4j_connect_failed",
                f"Could not connect to Neo4j at configured URL: {type(exc).__name__}: {exc}",
                example="Export MEMNET_NEO4J_URL to a reachable external cabinet",
            ) from exc
        self._driver = driver
        return driver

    def _session(self) -> Any:
        driver = self._ensure_driver()
        try:
            return driver.session(database=self.config.database_name)
        except Exception as exc:  # noqa: BLE001
            raise MemNetError(
                "neo4j_connect_failed",
                f"Could not open Neo4j session: {type(exc).__name__}: {exc}",
                example="Check MEMNET_NEO4J_DATABASE (default neo4j)",
            ) from exc

    def _run(self, cypher: str, params: dict[str, Any] | None = None) -> list[Any]:
        with self._session() as session:
            result = session.run(cypher, params or {})
            return list(result)


def _row_get(row: Any, index: int, key: str) -> Any:
    """Support neo4j.Record, mapping rows, and tuple rows from mocks."""
    if isinstance(row, dict):
        return row.get(key)
    if hasattr(row, "get"):
        try:
            val = row.get(key)
            if val is not None:
                return val
        except Exception:  # noqa: BLE001
            pass
    try:
        return row[index]
    except (IndexError, TypeError, KeyError):
        return None
