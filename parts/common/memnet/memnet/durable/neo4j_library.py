"""Neo4j library namespace — locator-only read on a second database.

Same Bolt URL / process as the cabinet ``Neo4jAdapter``. Extra **0.16**.

- ``MEMNET_NEO4J_LIBRARY_DATABASE`` unset → skip (no second bind).
- If set, MUST differ from the cabinet database name
  (``MEMNET_NEO4J_DATABASE``, default ``neo4j``).
- Emit locators only. Never ``generate``. Never hydrate session ``S``.
- Never flush session pins into the library database.

Hid / elementId / ``_memnet_hid`` stay off the emit. Not a
``DurableStoreAdapter``. Extra **0.17** ``RagHostHook`` MAY consume
these locators; this port stays locators-only / ``generate=false``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from memnet.durable.neo4j import (
    DEFAULT_DATABASE,
    ENV_DATABASE,
    ENV_PASSWORD,
    ENV_URL,
    ENV_USER,
    cypher_ident,
)
from memnet.exceptions import MemNetError

ENV_LIBRARY_DATABASE = "MEMNET_NEO4J_LIBRARY_DATABASE"

LOCATOR_KEYS = ("path", "document_id", "qname", "session", "url")
_OFF_EMIT = frozenset(
    {
        "_memnet_hid",
        "_memnet_tag",
        "hid",
        "elementId",
        "element_id",
        "identity",
        "generate",
    }
)


def cabinet_database_name() -> str:
    return (os.environ.get(ENV_DATABASE) or "").strip() or DEFAULT_DATABASE


def library_database_name() -> str | None:
    name = (os.environ.get(ENV_LIBRARY_DATABASE) or "").strip()
    return name or None


def locator_fields(props: dict[str, Any] | None) -> dict[str, str]:
    """Keep locator properties only; strip hid / generate / cabinet stamps."""
    out: dict[str, str] = {}
    if not props:
        return out
    for key, val in props.items():
        if key in _OFF_EMIT or str(key).startswith("_memnet"):
            continue
        if key not in LOCATOR_KEYS:
            continue
        text = "" if val is None else str(val).strip()
        if text:
            out[key] = text
    return out


@dataclass(frozen=True)
class Neo4jLibraryConfig:
    url: str
    database: str
    user: str | None = None
    password: str | None = None

    @classmethod
    def from_env(cls) -> Neo4jLibraryConfig | None:
        url = (os.environ.get(ENV_URL) or "").strip()
        name = library_database_name()
        if not url or not name:
            return None
        cabinet = cabinet_database_name()
        if name == cabinet:
            raise MemNetError(
                "neo4j_library_same_as_cabinet",
                "MEMNET_NEO4J_LIBRARY_DATABASE must differ from the cabinet "
                f"database ({cabinet!r}); one database is not two namespaces.",
                example="export MEMNET_NEO4J_LIBRARY_DATABASE=library",
            )
        cypher_ident(name, kind="database")
        return cls(
            url=url,
            database=name,
            user=(os.environ.get(ENV_USER) or "").strip() or None,
            password=os.environ.get(ENV_PASSWORD) or None,
        )


def build_library_locator_cypher(
    cue: str | None = None,
    *,
    limit: int = 50,
) -> tuple[str, dict[str, Any]]:
    """MATCH corpus nodes; RETURN locator columns only. Never generate."""
    cap = max(1, int(limit))
    where = "WHERE n._memnet_tag IS NULL"
    params: dict[str, Any] = {"limit": cap}
    token = (cue or "").strip()
    if token:
        params["cue"] = token.lower()
        where += (
            " AND ("
            "toLower(toString(coalesce(n.path, ''))) CONTAINS $cue OR "
            "toLower(toString(coalesce(n.document_id, ''))) CONTAINS $cue OR "
            "toLower(toString(coalesce(n.qname, ''))) CONTAINS $cue OR "
            "toLower(toString(coalesce(n.session, ''))) CONTAINS $cue OR "
            "toLower(toString(coalesce(n.url, ''))) CONTAINS $cue"
            ")"
        )
    query = (
        f"MATCH (n)\n{where}\n"
        "RETURN n.path AS path, n.document_id AS document_id, "
        "n.qname AS qname, n.session AS session, n.url AS url\n"
        "LIMIT $limit"
    )
    return query, params


class Neo4jLibraryClient:
    """Locator-only client for the library database. Not a cabinet adapter."""

    generate = False

    def __init__(self, config: Neo4jLibraryConfig) -> None:
        self.config = config
        self._driver: Any = None

    @classmethod
    def from_env(cls) -> Neo4jLibraryClient | None:
        cfg = Neo4jLibraryConfig.from_env()
        if cfg is None:
            return None
        return cls(cfg)

    @property
    def name(self) -> str:
        return "neo4j_library"

    @property
    def database_name(self) -> str:
        return self.config.database

    def emit_locators(
        self,
        cue: str | None = None,
        *,
        limit: int = 50,
    ) -> list[dict[str, str]]:
        """Read locator properties from the library namespace."""
        if self.generate:
            raise MemNetError(
                "neo4j_library_generate_forbidden",
                "library port generate stays false",
            )
        self._ensure_driver()
        cypher, params = build_library_locator_cypher(cue, limit=limit)
        try:
            rows = self._run(cypher, params)
        except MemNetError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise MemNetError(
                "neo4j_query_failed",
                f"Neo4j library locator query failed: {type(exc).__name__}: {exc}",
                example="Check MEMNET_NEO4J_LIBRARY_DATABASE / network",
            ) from exc
        locators: list[dict[str, str]] = []
        for row in rows:
            loc = locator_fields(_row_as_mapping(row))
            if loc:
                locators.append(loc)
        return locators

    def hydrate(self, *_a: Any, **_k: Any) -> None:
        raise MemNetError(
            "neo4j_library_not_cabinet",
            "library namespace MUST NOT hydrate session S; use Neo4jAdapter "
            "on MEMNET_NEO4J_DATABASE.",
        )

    def flush(self, *_a: Any, **_k: Any) -> None:
        raise MemNetError(
            "neo4j_library_read_only",
            "library namespace MUST NOT receive flushed session pins.",
        )

    def close(self) -> None:
        driver = self._driver
        self._driver = None
        if driver is not None:
            try:
                driver.close()
            except Exception:  # noqa: BLE001
                pass

    def _import_graphdatabase(self) -> Any:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise MemNetError(
                "neo4j_unavailable",
                "MEMNET_NEO4J_LIBRARY_DATABASE is set but the neo4j driver is not installed.",
                example="pip install 'memnet-llm[neo4j]'",
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
                f"Could not connect to Neo4j library URL: {type(exc).__name__}: {exc}",
                example="Export MEMNET_NEO4J_URL to a reachable external process",
            ) from exc
        self._driver = driver
        return driver

    def _session(self) -> Any:
        driver = self._ensure_driver()
        try:
            return driver.session(database=self.config.database)
        except Exception as exc:  # noqa: BLE001
            raise MemNetError(
                "neo4j_connect_failed",
                f"Could not open Neo4j library database: {type(exc).__name__}: {exc}",
                example="Check MEMNET_NEO4J_LIBRARY_DATABASE",
            ) from exc

    def _run(self, cypher: str, params: dict[str, Any] | None = None) -> list[Any]:
        with self._session() as session:
            result = session.run(cypher, params or {})
            return list(result)


def make_library_client_from_env() -> Neo4jLibraryClient | None:
    """Skip unless URL and library database name are both set."""
    return Neo4jLibraryClient.from_env()


def _row_as_mapping(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    if hasattr(row, "data") and callable(row.data):
        try:
            data = row.data()
            if isinstance(data, dict):
                return data
        except Exception:  # noqa: BLE001
            pass
    if hasattr(row, "keys"):
        try:
            return {str(k): row[k] for k in row.keys()}
        except Exception:  # noqa: BLE001
            pass
    out: dict[str, Any] = {}
    for i, key in enumerate(LOCATOR_KEYS):
        try:
            out[key] = row[i]
        except (IndexError, TypeError, KeyError):
            continue
    return out
