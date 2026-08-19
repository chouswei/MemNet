"""Extra 0.16: Neo4j cabinet vs library namespaces (same process, two DBs)."""

from __future__ import annotations

import inspect
import os

import pytest

from memnet.durable.adapter import DurableStoreAdapter
from memnet.durable.neo4j import Neo4jAdapter, Neo4jConfig
from memnet.durable.neo4j_library import (
    Neo4jLibraryClient,
    Neo4jLibraryConfig,
    build_library_locator_cypher,
    locator_fields,
    make_library_client_from_env,
)
from memnet.exceptions import MemNetError
from memnet.pin_map_composer import PinMapComposer

_NEO4J_LIVE = bool((os.environ.get("MEMNET_NEO4J_URL") or "").strip())


def test_library_skips_when_name_unset(monkeypatch):
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.delenv("MEMNET_NEO4J_LIBRARY_DATABASE", raising=False)
    monkeypatch.delenv("MEMNET_NEO4J_DATABASE", raising=False)
    assert make_library_client_from_env() is None
    assert Neo4jLibraryConfig.from_env() is None


def test_library_skips_when_url_unset(monkeypatch):
    monkeypatch.delenv("MEMNET_NEO4J_URL", raising=False)
    monkeypatch.setenv("MEMNET_NEO4J_LIBRARY_DATABASE", "library")
    assert make_library_client_from_env() is None


def test_cabinet_and_library_databases_are_distinct(monkeypatch):
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.setenv("MEMNET_NEO4J_DATABASE", "neo4j")
    monkeypatch.setenv("MEMNET_NEO4J_LIBRARY_DATABASE", "library")
    cabinet = Neo4jAdapter.from_env()
    library = Neo4jLibraryClient.from_env()
    assert cabinet is not None
    assert library is not None
    assert cabinet.config.database_name == "neo4j"
    assert library.database_name == "library"
    assert cabinet.config.database_name != library.database_name
    assert not isinstance(library, DurableStoreAdapter)
    assert library.generate is False


def test_same_database_name_is_rejected(monkeypatch):
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.setenv("MEMNET_NEO4J_DATABASE", "neo4j")
    monkeypatch.setenv("MEMNET_NEO4J_LIBRARY_DATABASE", "neo4j")
    with pytest.raises(MemNetError) as ei:
        Neo4jLibraryClient.from_env()
    assert ei.value.code == "neo4j_library_same_as_cabinet"
    with pytest.raises(MemNetError) as ei2:
        Neo4jAdapter.from_env()
    assert ei2.value.code == "neo4j_library_same_as_cabinet"


def test_library_emit_is_locators_only_stub():
    client = Neo4jLibraryClient(Neo4jLibraryConfig(url="bolt://127.0.0.1:7687", database="library"))
    rows = [
        {
            "path": "docs/SHAPE.md",
            "document_id": "DOC_shape",
            "qname": "",
            "session": "",
            "url": "",
            "_memnet_hid": "el1",
            "generate": True,
            "hid": "secret",
        }
    ]
    client._run = lambda *_a, **_k: rows  # type: ignore[method-assign]
    client._ensure_driver = lambda: None  # type: ignore[method-assign]
    locators = client.emit_locators("shape", limit=8)
    assert locators == [{"path": "docs/SHAPE.md", "document_id": "DOC_shape"}]
    assert "generate" not in locators[0]
    assert "_memnet_hid" not in locators[0]
    assert client.generate is False


def test_locator_fields_strips_hid():
    got = locator_fields(
        {
            "path": "/tmp/a.md",
            "_memnet_hid": "el9",
            "elementId": "4:abc",
            "generate": "true",
            "note": "chunk body",
        }
    )
    assert got == {"path": "/tmp/a.md"}


def test_library_must_not_hydrate_or_flush():
    client = Neo4jLibraryClient(Neo4jLibraryConfig(url="bolt://127.0.0.1:7687", database="library"))
    with pytest.raises(MemNetError) as h:
        client.hydrate("COM_acme")
    assert h.value.code == "neo4j_library_not_cabinet"
    with pytest.raises(MemNetError) as f:
        client.flush(None)
    assert f.value.code == "neo4j_library_read_only"


def test_library_locator_cypher_has_no_generate():
    cypher, params = build_library_locator_cypher("qname", limit=7)
    assert params["limit"] == 7
    assert params["cue"] == "qname"
    assert "generate" not in cypher.lower()
    assert "rrf" not in cypher.lower()
    assert "ppr" not in cypher.lower()
    assert "_memnet_hid" not in cypher
    assert "RETURN n.path" in cypher
    assert "n._memnet_tag IS NULL" in cypher


def test_pin_map_does_not_fuse_rrf_ppr():
    source = inspect.getsource(PinMapComposer)
    lowered = source.lower()
    for token in ("rrf", "ppr", "leiden", "reciprocal_rank", "generate("):
        assert token not in lowered
    cfg_src = inspect.getsource(Neo4jAdapter)
    assert "rrf" not in cfg_src.lower()


def test_library_session_uses_library_database():
    client = Neo4jLibraryClient(Neo4jLibraryConfig(url="bolt://127.0.0.1:7687", database="library"))
    cabinet = Neo4jAdapter(Neo4jConfig(url="bolt://127.0.0.1:7687", database="neo4j"))

    class _Sess:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def run(self, *_a, **_k):
            return []

    opened: list[str] = []

    class _Driver:
        def session(self, database="neo4j"):
            opened.append(database)
            return _Sess()

        def close(self):
            return None

    client._driver = _Driver()
    cabinet._driver = _Driver()
    client._run("RETURN 1", {})
    cabinet._run("RETURN 1", {})
    assert opened == ["library", "neo4j"]


@pytest.mark.neo4j_live
@pytest.mark.skipif(not _NEO4J_LIVE, reason="MEMNET_NEO4J_URL not set")
def test_neo4j_live_library_skip_or_distinct():
    """Live: skip library unless name set; never fuse cabinet hydrate."""
    lib = make_library_client_from_env()
    if lib is None:
        pytest.skip("MEMNET_NEO4J_LIBRARY_DATABASE not set")
    cabinet = Neo4jAdapter.from_env()
    assert cabinet is not None
    assert lib.database_name != cabinet.config.database_name
    assert lib.generate is False
    locators = lib.emit_locators(limit=5)
    lib.close()
    for loc in locators:
        assert "generate" not in loc
        assert "_memnet_hid" not in loc
        assert "hid" not in loc
        assert "elementId" not in loc
