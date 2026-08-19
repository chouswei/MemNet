"""M2.5 durable store adapter seam: hydrate → session → pin_map."""

from __future__ import annotations

import os

import pytest

from memnet.durable import (
    DurableStoreAdapter,
    DurableSubgraph,
    DurableSyncOwner,
    FakeDurableAdapter,
    HydrateBudget,
    company_ego_fixture,
    get_sync_owner,
    make_adapter_from_env,
    reset_sync_owner_for_tests,
)
from memnet.durable import neo4j as neo4j_cypher
from memnet.durable.agensgraph import (
    AgensGraphAdapter,
    AgensGraphConfig,
    build_hydrate_edges_cypher,
    build_hydrate_nodes_cypher,
    build_merge_edge_cypher,
    build_merge_node_cypher,
    map_edge_row,
    map_node_row,
)
from memnet.durable.neo4j import Neo4jAdapter, Neo4jConfig, first_label
from memnet.exceptions import MemNetError
from memnet.models import Record
from memnet.pin_map_composer import PinMapComposer
from memnet.session import open_session
from memnet.session_lifecycle import SessionLifecycle

_COM_MAP = [
    "SCHEMA COM ; fields=id name kind",
    "SCHEMA TSK ; fields=id goal status recycle",
]

_LIVE = bool((os.environ.get("MEMNET_AGENSGRAPH_URL") or "").strip())
_NEO4J_LIVE = bool((os.environ.get("MEMNET_NEO4J_URL") or "").strip())


@pytest.fixture(autouse=True)
def _reset_owner():
    reset_sync_owner_for_tests()
    yield
    reset_sync_owner_for_tests()


def test_adapter_is_abc_contract():
    assert issubclass(FakeDurableAdapter, DurableStoreAdapter)
    assert issubclass(AgensGraphAdapter, DurableStoreAdapter)
    assert issubclass(Neo4jAdapter, DurableStoreAdapter)


def test_fake_hydrate_respects_budget():
    fake = FakeDurableAdapter(seed_company_ego=True)
    full = fake.hydrate("COM_acme", HydrateBudget(max_nodes=50, max_edges=50))
    assert {n.id for n in full.nodes} == {"COM_acme", "TSK_mission_q3"}
    assert len(full.edges) == 1

    tiny = fake.hydrate("COM_acme", HydrateBudget(max_nodes=1, max_edges=0))
    assert [n.id for n in tiny.nodes] == ["COM_acme"]
    assert tiny.edges == []


def test_hydrate_into_session_then_pin_map(memnet_temp):
    fake = FakeDurableAdapter(seed_company_ego=True)
    owner = get_sync_owner(fake)
    ss = open_session(map_lines=list(_COM_MAP))

    loaded = owner.hydrate_into_session(
        ss, "COM_acme", HydrateBudget(max_nodes=20, max_edges=20, depth=2)
    )
    assert loaded.ego_id == "COM_acme"
    assert ss.store.get("COM_acme") is not None
    assert ss.store.get("TSK_mission_q3") is not None
    assert "ABOUT" in ss.relations

    rows, text = PinMapComposer(ss).compose(anchor="COM_acme", depth=2, max_rows=50)
    ids = {r.id for r in rows if r.tag != "LAW"}
    assert "COM_acme" in ids
    assert "TSK_mission_q3" in ids
    assert "CREATE" not in text  # shaped present form, not mutate
    assert "COM_acme" in text
    assert "ABOUT" in text


def test_session_lifecycle_hydrate_port(memnet_temp):
    fake = FakeDurableAdapter(seed_company_ego=True)
    get_sync_owner(fake)
    ss = SessionLifecycle.open(map_lines=list(_COM_MAP))
    SessionLifecycle.hydrate_from_durable(ss, "COM_acme", max_nodes=10, depth=2)
    rows, _ = PinMapComposer(ss).compose(anchor="COM_acme", depth=2, max_rows=20)
    assert any(r.id == "COM_acme" for r in rows)


def test_flush_round_trip_via_owner(memnet_temp):
    fake = FakeDurableAdapter()
    owner = DurableSyncOwner(fake)
    ss = open_session(map_lines=list(_COM_MAP))
    # Seed live session directly (agents would have mutated; we skip dual path).
    fixture = company_ego_fixture()
    for rec in fixture.all_records():
        ss.store.upsert(rec, allow_new_relation=True, relations=ss.relations)
    ss.mark_written()

    flushed = owner.flush_from_session(ss, "COM_acme")
    assert flushed.ego_id == "COM_acme"
    assert "COM_acme" in fake.egos()

    ss2 = open_session(map_lines=list(_COM_MAP))
    owner.hydrate_into_session(ss2, "COM_acme")
    assert ss2.store.get("COM_acme") is not None
    _, text = PinMapComposer(ss2).compose(anchor="COM_acme", depth=2, max_rows=50)
    assert "Acme" in text


def test_one_sync_owner_rejects_second_adapter(memnet_temp):
    get_sync_owner(FakeDurableAdapter())
    with pytest.raises(MemNetError) as ei:
        get_sync_owner(FakeDurableAdapter())
    assert ei.value.code == "dual_sync_owner"


def test_make_adapter_from_env_defaults_to_fake(monkeypatch):
    monkeypatch.delenv("MEMNET_AGENSGRAPH_URL", raising=False)
    monkeypatch.delenv("MEMNET_NEO4J_URL", raising=False)
    monkeypatch.delenv("MEMNET_DURABLE_BACKEND", raising=False)
    monkeypatch.delenv("MEMNET_DURABLE_FAKE", raising=False)
    adapter = make_adapter_from_env()
    assert isinstance(adapter, FakeDurableAdapter)


def test_make_adapter_from_env_agens_when_url(monkeypatch):
    monkeypatch.setenv("MEMNET_AGENSGRAPH_URL", "postgresql://localhost/memnet")
    monkeypatch.delenv("MEMNET_NEO4J_URL", raising=False)
    monkeypatch.delenv("MEMNET_DURABLE_BACKEND", raising=False)
    monkeypatch.delenv("MEMNET_DURABLE_FAKE", raising=False)
    adapter = make_adapter_from_env()
    assert isinstance(adapter, AgensGraphAdapter)


def test_make_adapter_from_env_neo4j_when_url(monkeypatch):
    monkeypatch.delenv("MEMNET_AGENSGRAPH_URL", raising=False)
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.delenv("MEMNET_DURABLE_BACKEND", raising=False)
    monkeypatch.delenv("MEMNET_DURABLE_FAKE", raising=False)
    adapter = make_adapter_from_env()
    assert isinstance(adapter, Neo4jAdapter)


def test_make_adapter_from_env_fake_overrides_url(monkeypatch):
    monkeypatch.setenv("MEMNET_AGENSGRAPH_URL", "postgresql://localhost/memnet")
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.setenv("MEMNET_DURABLE_FAKE", "1")
    adapter = make_adapter_from_env()
    assert isinstance(adapter, FakeDurableAdapter)


def test_make_adapter_from_env_both_urls_conflict(monkeypatch):
    monkeypatch.setenv("MEMNET_AGENSGRAPH_URL", "postgresql://localhost/memnet")
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.delenv("MEMNET_DURABLE_BACKEND", raising=False)
    monkeypatch.delenv("MEMNET_DURABLE_FAKE", raising=False)
    with pytest.raises(MemNetError) as ei:
        make_adapter_from_env()
    assert ei.value.code == "durable_backend_conflict"


def test_make_adapter_from_env_both_urls_backend_pick(monkeypatch):
    monkeypatch.setenv("MEMNET_AGENSGRAPH_URL", "postgresql://localhost/memnet")
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.delenv("MEMNET_DURABLE_FAKE", raising=False)
    monkeypatch.setenv("MEMNET_DURABLE_BACKEND", "neo4j")
    adapter = make_adapter_from_env()
    assert isinstance(adapter, Neo4jAdapter)
    monkeypatch.setenv("MEMNET_DURABLE_BACKEND", "agensgraph")
    adapter = make_adapter_from_env()
    assert isinstance(adapter, AgensGraphAdapter)


def test_agens_hydrate_unavailable_without_psycopg(monkeypatch):
    adapter = AgensGraphAdapter(AgensGraphConfig(url="postgresql://localhost/memnet"))

    def _boom() -> None:
        raise MemNetError(
            "agensgraph_unavailable",
            "psycopg missing (simulated)",
            example="pip install 'psycopg[binary]'",
        )

    monkeypatch.setattr(adapter, "_import_psycopg", _boom)
    with pytest.raises(MemNetError) as ei:
        adapter.hydrate("COM_acme", HydrateBudget())
    assert ei.value.code == "agensgraph_unavailable"


def test_agens_connect_failed_is_clear(monkeypatch):
    adapter = AgensGraphAdapter(AgensGraphConfig(url="postgresql://127.0.0.1:1/memnet"))

    class _Psycopg:
        @staticmethod
        def connect(*_a, **_k):
            raise OSError("connection refused (simulated)")

    monkeypatch.setattr(adapter, "_import_psycopg", lambda: _Psycopg)
    with pytest.raises(MemNetError) as ei:
        adapter.hydrate("COM_acme", HydrateBudget())
    assert ei.value.code == "agensgraph_connect_failed"


def test_bounded_keeps_ego_first():
    nodes = [
        Record(tag="COM", fields={"id": "COM_other", "name": "Other"}),
        Record(tag="COM", fields={"id": "COM_acme", "name": "Acme"}),
    ]
    g = DurableSubgraph(ego_id="COM_acme", nodes=nodes).bounded(
        HydrateBudget(max_nodes=1, max_edges=0)
    )
    assert [n.id for n in g.nodes] == ["COM_acme"]


def test_hydrate_missing_ego_is_empty(memnet_temp):
    owner = get_sync_owner(FakeDurableAdapter())
    ss = open_session(map_lines=list(_COM_MAP))
    loaded = owner.hydrate_into_session(ss, "COM_missing")
    assert loaded.nodes == []
    assert ss.store.get("COM_missing") is None


def test_build_hydrate_nodes_cypher_includes_budget():
    cypher = build_hydrate_nodes_cypher("COM_acme", HydrateBudget(max_nodes=12, depth=2))
    assert "COM_acme" in cypher
    assert "*0..2" in cypher
    assert "LIMIT 12" in cypher
    assert "properties(n)" in cypher


def test_build_hydrate_edges_cypher_zero_budget():
    cypher = build_hydrate_edges_cypher("COM_acme", HydrateBudget(max_edges=0, depth=1))
    assert "LIMIT 0" in cypher


def test_build_hydrate_edges_cypher_filters_hydrated_ids():
    cypher = build_hydrate_edges_cypher(
        "COM_acme",
        HydrateBudget(max_edges=20, depth=2),
        node_ids=["COM_acme", "TSK_mission_q3"],
    )
    assert "WHERE src.id IN ['COM_acme', 'TSK_mission_q3']" in cypher
    assert "MATCH (src)-[rel]->(dst)" in cypher
    assert "UNWIND" not in cypher


def test_build_hydrate_edges_cypher_empty_ids_is_skip():
    cypher = build_hydrate_edges_cypher("COM_acme", HydrateBudget(max_edges=20, depth=2))
    assert "LIMIT 0" in cypher


def test_build_merge_node_and_edge_cypher():
    node = Record(
        tag="COM",
        fields={"id": "COM_acme", "name": "Acme", "kind": "company"},
    )
    edge = Record(
        tag="EDG",
        fields={
            "id": "E_about_q3",
            "src": "TSK_mission_q3",
            "relation": "ABOUT",
            "dist": "COM_acme",
        },
    )
    n_cypher = build_merge_node_cypher(node)
    assert "MERGE (n:COM {_memnet_hid:" in n_cypher or "_memnet_hid" in n_cypher
    assert "n.name = 'Acme'" in n_cypher
    assert "_memnet_tag" in n_cypher

    e_cypher = build_merge_edge_cypher(edge)
    assert "MERGE (a)-[r:ABOUT {id: 'E_about_q3'}]->(b)" in e_cypher
    assert "TSK_mission_q3" in e_cypher
    assert "COM_acme" in e_cypher


def test_map_node_and_edge_rows():
    node = map_node_row(
        "COM",
        {"id": "COM_acme", "name": "Acme", "_memnet_tag": "COM"},
    )
    assert node is not None
    assert node.tag == "COM"
    assert node.fields["name"] == "Acme"

    edge = map_edge_row(
        "ABOUT",
        {"id": "E_about_q3", "relation": "ABOUT"},
        "TSK_mission_q3",
        "COM_acme",
    )
    assert edge is not None
    assert edge.tag == "EDG"
    assert edge.fields["src"] == "TSK_mission_q3"
    assert edge.fields["dist"] == "COM_acme"


def test_agens_hydrate_maps_mocked_rows(monkeypatch):
    adapter = AgensGraphAdapter(AgensGraphConfig(url="postgresql://localhost/memnet"))
    monkeypatch.setattr(adapter, "_ensure_conn", lambda: object())

    def _exec(_conn, cypher: str):
        if "properties(n)" in cypher:
            return [
                ("COM", {"id": "COM_acme", "name": "Acme", "_memnet_tag": "COM"}),
                (
                    "TSK",
                    {
                        "id": "TSK_mission_q3",
                        "goal": "Q3 mission",
                        "status": "settled",
                        "_memnet_tag": "TSK",
                    },
                ),
            ]
        return [
            (
                "ABOUT",
                {"id": "E_about_q3", "relation": "ABOUT", "_memnet_tag": "EDG"},
                "TSK_mission_q3",
                "COM_acme",
            )
        ]

    monkeypatch.setattr(adapter, "_execute", _exec)
    g = adapter.hydrate("COM_acme", HydrateBudget(max_nodes=10, max_edges=10, depth=2))
    assert {n.id for n in g.nodes} == {"COM_acme", "TSK_mission_q3"}
    assert len(g.edges) == 1
    assert "ABOUT" in g.relations


def test_agens_flush_emits_merge_statements(monkeypatch):
    adapter = AgensGraphAdapter(AgensGraphConfig(url="postgresql://localhost/memnet"))
    seen: list[str] = []

    class _Txn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class _Conn:
        def transaction(self):
            return _Txn()

    monkeypatch.setattr(adapter, "_ensure_conn", lambda: _Conn())

    def _exec(_conn, cypher: str):
        seen.append(cypher)
        return []

    monkeypatch.setattr(adapter, "_execute", _exec)
    adapter.flush(company_ego_fixture())
    assert any("MERGE (n:COM" in c for c in seen)
    assert any("MERGE (n:TSK" in c for c in seen)
    assert any("MERGE (a)-[r:ABOUT" in c for c in seen)


@pytest.mark.agensgraph_live
@pytest.mark.skipif(not _LIVE, reason="MEMNET_AGENSGRAPH_URL not set")
def test_agens_live_flush_hydrate_round_trip(memnet_temp):
    """Optional: exercise external AgensGraph cabinet when URL is exported."""
    adapter = AgensGraphAdapter.from_env()
    assert adapter is not None
    fixture = company_ego_fixture(ego_id="COM_acme_live_m25")
    try:
        adapter.flush(fixture)
        loaded = adapter.hydrate(fixture.ego_id, HydrateBudget(max_nodes=20, max_edges=20, depth=2))
    finally:
        adapter.close()
    assert any(n.id == fixture.ego_id for n in loaded.nodes)
    assert any(e.fields.get("relation") == "ABOUT" for e in loaded.edges)


def test_neo4j_from_env(monkeypatch):
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.setenv("MEMNET_NEO4J_USER", "neo4j")
    monkeypatch.setenv("MEMNET_NEO4J_PASSWORD", "test")
    monkeypatch.setenv("MEMNET_NEO4J_DATABASE", "memnet")
    adapter = Neo4jAdapter.from_env()
    assert adapter is not None
    assert adapter.name == "neo4j"
    assert adapter.config.database_name == "memnet"
    assert adapter.config.user == "neo4j"


def test_neo4j_hydrate_unavailable_without_driver(monkeypatch):
    adapter = Neo4jAdapter(Neo4jConfig(url="bolt://127.0.0.1:7687"))

    def _boom() -> None:
        raise MemNetError(
            "neo4j_unavailable",
            "neo4j missing (simulated)",
            example="pip install neo4j",
        )

    monkeypatch.setattr(adapter, "_import_graphdatabase", _boom)
    with pytest.raises(MemNetError) as ei:
        adapter.hydrate("COM_acme", HydrateBudget())
    assert ei.value.code == "neo4j_unavailable"


def test_neo4j_connect_failed_is_clear(monkeypatch):
    adapter = Neo4jAdapter(Neo4jConfig(url="bolt://127.0.0.1:1"))

    class _GraphDatabase:
        @staticmethod
        def driver(*_a, **_k):
            raise OSError("connection refused (simulated)")

    monkeypatch.setattr(adapter, "_import_graphdatabase", lambda: _GraphDatabase)
    with pytest.raises(MemNetError) as ei:
        adapter.hydrate("COM_acme", HydrateBudget())
    assert ei.value.code == "neo4j_connect_failed"


def test_neo4j_build_hydrate_nodes_cypher():
    cypher, params = neo4j_cypher.build_hydrate_nodes_cypher(
        "COM_acme", HydrateBudget(max_nodes=12, depth=2)
    )
    assert params["ego_id"] == "COM_acme"
    assert "*0..2" in cypher
    assert "LIMIT 12" in cypher
    assert "labels(n)" in cypher
    assert "label(n)" not in cypher
    assert "properties(n)" in cypher


def test_neo4j_build_hydrate_edges_cypher_filters_ids():
    cypher, params = neo4j_cypher.build_hydrate_edges_cypher(
        "COM_acme",
        HydrateBudget(max_edges=20, depth=2),
        node_ids=["COM_acme", "TSK_mission_q3"],
    )
    assert params["node_ids"] == ["COM_acme", "TSK_mission_q3"]
    assert "src.id IN $node_ids" in cypher
    assert "type(rel)" in cypher
    assert "label(rel)" not in cypher


def test_neo4j_build_hydrate_edges_zero_or_empty():
    cypher, _params = neo4j_cypher.build_hydrate_edges_cypher(
        "COM_acme", HydrateBudget(max_edges=0)
    )
    assert "LIMIT 0" in cypher
    cypher, _params = neo4j_cypher.build_hydrate_edges_cypher(
        "COM_acme", HydrateBudget(max_edges=20)
    )
    assert "LIMIT 0" in cypher


def test_neo4j_build_merge_node_and_edge_cypher():
    node = Record(
        tag="COM",
        fields={"id": "COM_acme", "name": "Acme", "kind": "company"},
    )
    edge = Record(
        tag="EDG",
        fields={
            "id": "E_about_q3",
            "src": "TSK_mission_q3",
            "relation": "ABOUT",
            "dist": "COM_acme",
        },
    )
    n_cypher, n_params = neo4j_cypher.build_merge_node_cypher(node)
    assert "MERGE (n:COM {_memnet_hid: $hid})" in n_cypher
    assert n_params["hid"] == node.hid
    assert n_params["props"]["name"] == "Acme"
    assert "_memnet_tag" in n_cypher

    e_cypher, e_params = neo4j_cypher.build_merge_edge_cypher(edge)
    assert "_memnet_hid" in e_cypher
    assert e_params["src"] == "TSK_mission_q3"
    assert e_params["dist"] == "COM_acme"


def test_neo4j_rejects_unsafe_ident_and_id():
    with pytest.raises(MemNetError) as ei:
        neo4j_cypher.build_merge_node_cypher(Record(tag="COM;DROP", fields={"id": "COM_acme"}))
    assert ei.value.code == "neo4j_bad_ident"
    with pytest.raises(MemNetError) as ei:
        neo4j_cypher.build_hydrate_nodes_cypher("COM_acme' OR 1=1", HydrateBudget())
    assert ei.value.code == "neo4j_bad_id"


def test_first_label_from_neo4j_list():
    assert first_label(["COM", "Entity"]) == "COM"
    assert first_label("TSK") == "TSK"
    assert first_label([]) == ""


def test_neo4j_hydrate_maps_mocked_rows(monkeypatch):
    adapter = Neo4jAdapter(Neo4jConfig(url="bolt://127.0.0.1:7687"))
    monkeypatch.setattr(adapter, "_ensure_driver", lambda: object())

    def _run(_cypher: str, params=None):
        if "labels(n)" in _cypher:
            return [
                {
                    "labels": ["COM"],
                    "props": {"id": "COM_acme", "name": "Acme", "_memnet_tag": "COM"},
                },
                {
                    "labels": ["TSK"],
                    "props": {
                        "id": "TSK_mission_q3",
                        "goal": "Q3 mission",
                        "status": "settled",
                        "_memnet_tag": "TSK",
                    },
                },
            ]
        return [
            {
                "rel_type": "ABOUT",
                "props": {"id": "E_about_q3", "relation": "ABOUT", "_memnet_tag": "EDG"},
                "src": "TSK_mission_q3",
                "dist": "COM_acme",
            }
        ]

    monkeypatch.setattr(adapter, "_run", _run)
    g = adapter.hydrate("COM_acme", HydrateBudget(max_nodes=10, max_edges=10, depth=2))
    assert {n.id for n in g.nodes} == {"COM_acme", "TSK_mission_q3"}
    assert len(g.edges) == 1
    assert "ABOUT" in g.relations


def test_neo4j_flush_emits_merge_statements(monkeypatch):
    adapter = Neo4jAdapter(Neo4jConfig(url="bolt://127.0.0.1:7687"))
    seen: list[str] = []
    monkeypatch.setattr(adapter, "_ensure_driver", lambda: object())

    def _run(cypher: str, params=None):
        seen.append(cypher)
        return []

    monkeypatch.setattr(adapter, "_run", _run)
    adapter.flush(company_ego_fixture())
    assert any("MERGE (n:COM" in c for c in seen)
    assert any("MERGE (n:TSK" in c for c in seen)
    assert any("MERGE (a)-[r:ABOUT" in c for c in seen)
    assert seen.index(next(c for c in seen if "MERGE (n:COM" in c)) < seen.index(
        next(c for c in seen if "MERGE (a)-[r:ABOUT" in c)
    )


def test_neo4j_recorded_session_stub(monkeypatch):
    """Always-on Bolt stub: session.run is recorded; no live server."""

    class _Session:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def run(self, query: str, params=None, **_k):
            self.queries.append(query)
            if "labels(n)" in query:
                return [
                    {
                        "labels": ["COM"],
                        "props": {"id": "COM_acme", "name": "Acme", "_memnet_tag": "COM"},
                    }
                ]
            return []

        def close(self) -> None:
            return None

    session = _Session()

    class _Driver:
        def session(self, database=None):
            assert database == "neo4j"
            return session

        def close(self) -> None:
            return None

    adapter = Neo4jAdapter(Neo4jConfig(url="bolt://127.0.0.1:7687"))
    monkeypatch.setattr(adapter, "_ensure_driver", lambda: _Driver())
    g = adapter.hydrate("COM_acme", HydrateBudget(max_nodes=5, max_edges=5, depth=1))
    assert any(n.id == "COM_acme" for n in g.nodes)
    assert any("labels(n)" in q for q in session.queries)


@pytest.mark.neo4j_live
@pytest.mark.skipif(not _NEO4J_LIVE, reason="MEMNET_NEO4J_URL not set")
def test_neo4j_live_flush_hydrate_round_trip(memnet_temp):
    """Optional: exercise external Neo4j cabinet when URL is exported."""
    adapter = Neo4jAdapter.from_env()
    assert adapter is not None
    fixture = company_ego_fixture(ego_id="COM_acme_live_neo4j")
    try:
        adapter.flush(fixture)
        loaded = adapter.hydrate(fixture.ego_id, HydrateBudget(max_nodes=20, max_edges=20, depth=2))
    finally:
        adapter.close()
    assert any(n.id == fixture.ego_id for n in loaded.nodes)
    assert any(e.fields.get("relation") == "ABOUT" for e in loaded.edges)
