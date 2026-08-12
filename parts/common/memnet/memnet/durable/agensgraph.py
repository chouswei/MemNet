"""AgensGraphAdapter — client/adapter for an *external* AgensGraph cabinet.

Connection placeholders (never hardcode secrets):

- MEMNET_AGENSGRAPH_URL       e.g. postgresql://host:5432/memnet
- MEMNET_AGENSGRAPH_USER
- MEMNET_AGENSGRAPH_PASSWORD
- MEMNET_AGENSGRAPH_GRAPH     named graph (default: memnet)

This module is a **client** only: it speaks openCypher over psycopg to a
store the operator already runs. It does **not** vendor or require an
AgensGraph server binary in this repo.

Wire stays MemNet GQL pin_map / mutate; the sync owner alone calls
hydrate/flush. Agents MUST NOT talk to AgensGraph directly.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from memnet.durable.adapter import DurableStoreAdapter, DurableSubgraph, HydrateBudget
from memnet.exceptions import MemNetError
from memnet.models import Record

ENV_URL = "MEMNET_AGENSGRAPH_URL"
ENV_USER = "MEMNET_AGENSGRAPH_USER"
ENV_PASSWORD = "MEMNET_AGENSGRAPH_PASSWORD"
ENV_GRAPH = "MEMNET_AGENSGRAPH_GRAPH"

DEFAULT_GRAPH = "memnet"
_MEMNET_TAG_KEY = "_memnet_tag"
_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:/@+-]+$")


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

    @property
    def graph_name(self) -> str:
        return self.graph or DEFAULT_GRAPH


def cypher_quote(value: str) -> str:
    """Quote a Cypher string literal (single quotes, escape \\ and ')."""
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def cypher_ident(name: str, *, kind: str = "label") -> str:
    """Validate and return a Cypher identifier (vertex/edge label)."""
    if not name or not _SAFE_IDENT.match(name):
        raise MemNetError(
            "agensgraph_bad_ident",
            f"AgensGraph {kind} must be a simple identifier, got {name!r}",
        )
    return name


def cypher_id_literal(value: str) -> str:
    """Validate a MemNet record id and return a Cypher string literal."""
    if not value or not _SAFE_ID.match(value):
        raise MemNetError(
            "agensgraph_bad_id",
            f"AgensGraph id must be a simple token, got {value!r}",
        )
    return cypher_quote(value)


def props_to_set_clause(alias: str, fields: dict[str, str], *, skip: set[str]) -> str:
    """Build ``alias.k = 'v', ...`` assignments from string fields."""
    parts: list[str] = []
    for key, val in sorted(fields.items()):
        if key in skip:
            continue
        if not _SAFE_IDENT.match(key):
            continue
        parts.append(f"{alias}.{key} = {cypher_quote(str(val))}")
    return ", ".join(parts)


def build_hydrate_nodes_cypher(ego_id: str, budget: HydrateBudget) -> str:
    """Ego-bounded node walk: vertices within ``budget.depth`` of ego."""
    ego = cypher_id_literal(ego_id)
    depth = max(0, int(budget.depth))
    limit = max(1, int(budget.max_nodes))
    # *0..depth includes the ego vertex itself.
    return (
        f"MATCH (ego {{id: {ego}}})\n"
        f"OPTIONAL MATCH (ego)-[*0..{depth}]-(n)\n"
        f"WITH DISTINCT n\n"
        f"WHERE n IS NOT NULL\n"
        f"RETURN label(n) AS label, properties(n) AS props\n"
        f"LIMIT {limit}"
    )


def build_hydrate_edges_cypher(ego_id: str, budget: HydrateBudget) -> str:
    """Edges whose both endpoints lie inside the ego-bounded node set."""
    ego = cypher_id_literal(ego_id)
    depth = max(0, int(budget.depth))
    limit = max(0, int(budget.max_edges))
    if limit == 0:
        return (
            f"MATCH (ego {{id: {ego}}})\n"
            f"WHERE false\n"
            f"RETURN null AS label, null AS props, null AS src, null AS dist\n"
            f"LIMIT 0"
        )
    return (
        f"MATCH (ego {{id: {ego}}})\n"
        f"OPTIONAL MATCH (ego)-[*0..{depth}]-(n)\n"
        f"WITH collect(DISTINCT n) AS nodes\n"
        f"UNWIND nodes AS a\n"
        f"UNWIND nodes AS b\n"
        f"MATCH (a)-[r]->(b)\n"
        f"RETURN DISTINCT label(r) AS label, properties(r) AS props, "
        f"a.id AS src, b.id AS dist\n"
        f"LIMIT {limit}"
    )


def build_merge_node_cypher(record: Record) -> str:
    """MERGE/SET one MemNet node record into the named graph."""
    tag = cypher_ident(record.tag.upper(), kind="vertex label")
    rid = cypher_id_literal(record.id)
    sets = props_to_set_clause("n", dict(record.fields), skip={"id"})
    tag_set = f"n.{_MEMNET_TAG_KEY} = {cypher_quote(record.tag.upper())}"
    set_body = f"{sets}, {tag_set}" if sets else tag_set
    return f"MERGE (n:{tag} {{id: {rid}}})\nSET {set_body}"


def build_merge_edge_cypher(record: Record) -> str:
    """MERGE/SET one MemNet EDG record (relation → edge label)."""
    if record.tag.upper() != "EDG":
        raise MemNetError(
            "agensgraph_bad_edge",
            f"flush edge expects tag EDG, got {record.tag!r}",
        )
    src = record.fields.get("src") or ""
    dist = record.fields.get("dist") or ""
    rel = record.fields.get("relation") or ""
    if not src or not dist or not rel:
        raise MemNetError(
            "agensgraph_bad_edge",
            "flush edge requires fields src, dist, relation",
        )
    rel_label = cypher_ident(rel, kind="edge label")
    src_lit = cypher_id_literal(src)
    dist_lit = cypher_id_literal(dist)
    rid = cypher_id_literal(record.id) if record.id else None
    skip = {"src", "dist", "relation"}
    sets = props_to_set_clause("r", dict(record.fields), skip=skip)
    tag_set = f"r.{_MEMNET_TAG_KEY} = 'EDG'"
    rel_set = f"r.relation = {cypher_quote(rel)}"
    extras = ", ".join(p for p in (sets, tag_set, rel_set) if p)
    if rid is not None:
        merge_edge = f"MERGE (a)-[r:{rel_label} {{id: {rid}}}]->(b)"
    else:
        merge_edge = f"MERGE (a)-[r:{rel_label}]->(b)"
    return f"MATCH (a {{id: {src_lit}}}), (b {{id: {dist_lit}}})\n{merge_edge}\nSET {extras}"


def _coerce_props(raw: Any) -> dict[str, str]:
    """Normalize AgensGraph/jsonb property bags to str→str MemNet fields."""
    if raw is None:
        return {}
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, val in raw.items():
        if key is None:
            continue
        k = str(key)
        if val is None:
            continue
        if isinstance(val, (dict, list)):
            out[k] = json.dumps(val, separators=(",", ":"))
        else:
            out[k] = str(val)
    return out


def _coerce_scalar(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        text = raw.strip()
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            try:
                return str(json.loads(text))
            except json.JSONDecodeError:
                return text[1:-1]
        return text
    return str(raw)


def map_node_row(label: Any, props: Any) -> Record | None:
    """Map a hydrate node row → MemNet Record (or None if unusable)."""
    fields = _coerce_props(props)
    tag = fields.pop(_MEMNET_TAG_KEY, None) or _coerce_scalar(label) or "NOD"
    tag = str(tag).upper()
    if not tag or tag == "AG_VERTEX":
        tag = str(fields.get("tag") or "NOD").upper()
    rid = fields.get("id") or ""
    if not rid:
        return None
    fields["id"] = rid
    return Record(tag=tag, fields=fields)


def map_edge_row(label: Any, props: Any, src: Any, dist: Any) -> Record | None:
    """Map a hydrate edge row → MemNet EDG Record."""
    fields = _coerce_props(props)
    fields.pop(_MEMNET_TAG_KEY, None)
    rel = fields.get("relation") or _coerce_scalar(label) or ""
    if not rel or rel.upper() == "AG_EDGE":
        return None
    src_id = _coerce_scalar(src) or fields.get("src") or ""
    dist_id = _coerce_scalar(dist) or fields.get("dist") or ""
    if not src_id or not dist_id:
        return None
    rid = fields.get("id") or f"E_{src_id}_{rel}_{dist_id}"
    fields["id"] = rid
    fields["src"] = src_id
    fields["dist"] = dist_id
    fields["relation"] = rel
    return Record(tag="EDG", fields=fields)


class AgensGraphAdapter(DurableStoreAdapter):
    """Client adapter: hydrate/flush ego slices against external AgensGraph."""

    def __init__(self, config: AgensGraphConfig) -> None:
        self.config = config
        self._conn: Any = None

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
        if not ego_id or not str(ego_id).strip():
            raise MemNetError("no_ego", "hydrate requires ego_id")
        budget = budget or HydrateBudget()
        conn = self._ensure_conn()
        nodes_cypher = build_hydrate_nodes_cypher(ego_id, budget)
        edges_cypher = build_hydrate_edges_cypher(ego_id, budget)
        try:
            node_rows = self._execute(conn, nodes_cypher)
            edge_rows = self._execute(conn, edges_cypher) if budget.max_edges > 0 else []
        except MemNetError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface driver errors clearly
            raise MemNetError(
                "agensgraph_query_failed",
                f"AgensGraph hydrate query failed: {type(exc).__name__}: {exc}",
                example="Check MEMNET_AGENSGRAPH_URL / graph name / network",
            ) from exc

        nodes: list[Record] = []
        seen_nodes: set[str] = set()
        for row in node_rows:
            rec = map_node_row(_row_get(row, 0, "label"), _row_get(row, 1, "props"))
            if rec is None or rec.id in seen_nodes:
                continue
            seen_nodes.add(rec.id)
            nodes.append(rec)

        edges: list[Record] = []
        seen_edges: set[str] = set()
        relations: set[str] = set()
        for row in edge_rows:
            rec = map_edge_row(
                _row_get(row, 0, "label"),
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
            raise MemNetError("agensgraph_bad_flush", "flush requires a DurableSubgraph")
        conn = self._ensure_conn()
        statements: list[str] = []
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
        try:
            with conn.transaction():
                for cypher in statements:
                    self._execute(conn, cypher)
        except MemNetError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MemNetError(
                "agensgraph_query_failed",
                f"AgensGraph flush failed: {type(exc).__name__}: {exc}",
                example="Check MERGE permissions / graph_path / endpoint ids exist",
            ) from exc

    def close(self) -> None:
        conn = self._conn
        self._conn = None
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001 — best-effort close
                pass

    def _import_psycopg(self) -> Any:
        try:
            import psycopg
        except ImportError as exc:
            raise MemNetError(
                "agensgraph_unavailable",
                "MEMNET_AGENSGRAPH_URL is set but psycopg is not installed. "
                "Install the optional client extra, or unset the URL and use "
                "FakeDurableAdapter for local seam tests.",
                example=(
                    "pip install 'memnet-llm[agensgraph]'  # or: pip install 'psycopg[binary]'"
                ),
            ) from exc
        return psycopg

    def _ensure_conn(self) -> Any:
        if self._conn is not None and not getattr(self._conn, "closed", False):
            return self._conn
        psycopg = self._import_psycopg()
        kwargs: dict[str, Any] = {}
        if self.config.user:
            kwargs["user"] = self.config.user
        if self.config.password is not None:
            kwargs["password"] = self.config.password
        try:
            conn = psycopg.connect(self.config.url, **kwargs)
        except MemNetError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MemNetError(
                "agensgraph_connect_failed",
                f"Could not connect to AgensGraph at configured URL: {type(exc).__name__}: {exc}",
                example="Export MEMNET_AGENSGRAPH_URL to a reachable external cabinet",
            ) from exc
        try:
            self._prepare_graph(conn)
        except MemNetError:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
            raise
        except Exception as exc:  # noqa: BLE001
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
            raise MemNetError(
                "agensgraph_connect_failed",
                f"Connected but failed to set graph_path={self.config.graph_name!r}: "
                f"{type(exc).__name__}: {exc}",
                example="CREATE GRAPH on the server, or set MEMNET_AGENSGRAPH_GRAPH",
            ) from exc
        self._conn = conn
        return conn

    def _prepare_graph(self, conn: Any) -> None:
        graph = cypher_ident(self.config.graph_name, kind="graph name")
        with conn.cursor() as cur:
            # CREATE GRAPH IF NOT EXISTS is not universal; ignore "already exists".
            try:
                cur.execute(f"CREATE GRAPH {graph}")
                conn.commit()
            except Exception:  # noqa: BLE001 — graph may already exist
                conn.rollback()
            cur.execute(f"SET graph_path = {graph}")

    def _execute(self, conn: Any, cypher: str) -> list[Any]:
        with conn.cursor() as cur:
            cur.execute(cypher)
            if cur.description is None:
                return []
            return list(cur.fetchall())


def _row_get(row: Any, index: int, key: str) -> Any:
    """Support tuple rows and mapping rows from psycopg."""
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[index]
    except (IndexError, TypeError, KeyError):
        if hasattr(row, "get"):
            return row.get(key)
        return None
