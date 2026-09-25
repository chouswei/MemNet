"""M2.5 durable store adapter seam: hydrate → session → pin_map."""

from __future__ import annotations

import logging
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
from memnet.durable.factory import reset_neo4j_retired_warning_for_tests
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


@pytest.fixture(autouse=True)
def _reset_owner():
    reset_sync_owner_for_tests()
    yield
    reset_sync_owner_for_tests()


def test_adapter_is_abc_contract():
    assert issubclass(FakeDurableAdapter, DurableStoreAdapter)
    assert issubclass(AgensGraphAdapter, DurableStoreAdapter)


def test_fake_hydrate_respects_budget():
    fake = FakeDurableAdapter(seed_company_ego=True)
    full = fake.hydrate("COM_acme", HydrateBudget(max_nodes=50, max_edges=50))
    assert {n.id for n in full.nodes} == {"COM_acme", "TSK_mission_q3"}
    assert len(full.edges) == 1

    tiny = fake.hydrate("COM_acme", HydrateBudget(max_nodes=1, max_edges=0))
    assert [n.id for n in tiny.nodes] == ["COM_acme"]
    assert tiny.edges == []


def test_hydrate_into_session_then_pin_map(memnet_temp):
    """Leftover cue path: PinMapComposer.compose(anchor=nickname) after hydrate."""
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
    assert "name: 'Acme'" in text
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


def test_retired_neo4j_env_is_ignored_and_engine_starts(monkeypatch, caplog):
    """A deployed host may still export MEMNET_NEO4J_*. Ignore and start."""
    monkeypatch.delenv("MEMNET_AGENSGRAPH_URL", raising=False)
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.setenv("MEMNET_NEO4J_USER", "neo4j")
    monkeypatch.setenv("MEMNET_NEO4J_PASSWORD", "do-not-log")
    monkeypatch.setenv("MEMNET_NEO4J_DATABASE", "memnet")
    monkeypatch.setenv("MEMNET_NEO4J_LIBRARY_DATABASE", "library")
    monkeypatch.setenv("MEMNET_DURABLE_BACKEND", "neo4j")
    monkeypatch.delenv("MEMNET_DURABLE_FAKE", raising=False)
    reset_neo4j_retired_warning_for_tests()
    reset_sync_owner_for_tests()
    with caplog.at_level(logging.WARNING):
        adapter = make_adapter_from_env()
        owner = get_sync_owner()
    assert isinstance(adapter, FakeDurableAdapter)
    assert owner is get_sync_owner()
    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "MEMNET_NEO4J_URL" in warnings[0]
    assert "MEMNET_NEO4J_PASSWORD" in warnings[0]
    assert "do-not-log" not in warnings[0]
    assert "bolt://" not in warnings[0]
    # Second start does not raise and does not warn again.
    caplog.clear()
    again = make_adapter_from_env()
    assert isinstance(again, FakeDurableAdapter)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_retired_neo4j_env_does_not_block_agens(monkeypatch, caplog):
    monkeypatch.setenv("MEMNET_AGENSGRAPH_URL", "postgresql://localhost/memnet")
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.delenv("MEMNET_DURABLE_BACKEND", raising=False)
    monkeypatch.delenv("MEMNET_DURABLE_FAKE", raising=False)
    reset_neo4j_retired_warning_for_tests()
    with caplog.at_level(logging.WARNING):
        adapter = make_adapter_from_env()
    assert isinstance(adapter, AgensGraphAdapter)
    assert any("MEMNET_NEO4J_URL" in r.getMessage() for r in caplog.records)


def test_make_adapter_from_env_fake_overrides_url(monkeypatch):
    monkeypatch.setenv("MEMNET_AGENSGRAPH_URL", "postgresql://localhost/memnet")
    monkeypatch.setenv("MEMNET_NEO4J_URL", "bolt://127.0.0.1:7687")
    monkeypatch.setenv("MEMNET_DURABLE_FAKE", "1")
    adapter = make_adapter_from_env()
    assert isinstance(adapter, FakeDurableAdapter)


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
    assert "{_memnet_hid:" in cypher
    assert "MATCH (ego {id:" not in cypher
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
    assert "WHERE src._memnet_hid IN ['COM_acme', 'TSK_mission_q3']" in cypher
    assert "MATCH (src)-[rel]->(dst)" in cypher
    assert "UNWIND" not in cypher


def test_build_hydrate_edges_cypher_empty_ids_is_skip():
    cypher = build_hydrate_edges_cypher("COM_acme", HydrateBudget(max_edges=20, depth=2))
    assert "LIMIT 0" in cypher


def test_build_merge_node_and_edge_cypher():
    fixture = company_ego_fixture()
    node = next(n for n in fixture.nodes if n.tag == "COM")
    task = next(n for n in fixture.nodes if n.tag == "TSK")
    edge = fixture.edges[0]
    n_cypher = build_merge_node_cypher(node)
    assert "MERGE (n:COM {_memnet_hid:" in n_cypher
    assert "MERGE (n:COM {id:" not in n_cypher
    assert "n.name = 'Acme'" in n_cypher
    assert "_memnet_tag" in n_cypher
    assert node.hid in n_cypher

    e_cypher = build_merge_edge_cypher(edge, nodes=fixture.nodes)
    assert "_memnet_hid" in e_cypher
    assert "MERGE (a)-[r:ABOUT {id:" not in e_cypher
    assert "MATCH (a {id:" not in e_cypher
    assert task.hid in e_cypher
    assert node.hid in e_cypher


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
    assert any("MERGE (n:COM {_memnet_hid:" in c for c in seen)
    assert not any("MERGE (n:COM {id:" in c for c in seen)
    assert any("MERGE (n:TSK" in c for c in seen)
    assert any("MERGE (a)-[r:ABOUT" in c for c in seen)


@pytest.mark.agensgraph_live
@pytest.mark.skipif(not _LIVE, reason="MEMNET_AGENSGRAPH_URL not set")
def test_agens_live_flush_hydrate_round_trip(memnet_temp):
    """Optional: exercise external AgensGraph cabinet when URL is exported."""
    adapter = AgensGraphAdapter.from_env()
    assert adapter is not None
    fixture = company_ego_fixture(ego_id="COM_acme_live_m25")
    ego = next(n for n in fixture.nodes if n.id == fixture.ego_id)
    try:
        adapter.flush(fixture)
        loaded = adapter.hydrate(ego.hid, HydrateBudget(max_nodes=20, max_edges=20, depth=2))
    finally:
        adapter.close()
    assert any(n.id == fixture.ego_id for n in loaded.nodes)
    assert any(e.fields.get("relation") == "ABOUT" for e in loaded.edges)


def test_agens_hydrate_after_flush_uses_hid(monkeypatch):
    """Fixture flush then hydrate by the written hid."""
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
    fixture = company_ego_fixture(ego_id="COM_acme_live_m25")
    ego = next(n for n in fixture.nodes if n.id == fixture.ego_id)
    task = next(n for n in fixture.nodes if n.tag == "TSK")

    def _exec(_conn, cypher: str):
        seen.append(cypher)
        if "properties(n)" in cypher:
            if f"_memnet_hid: '{ego.hid}'" not in cypher:
                return []
            return [
                (
                    "COM",
                    {
                        "id": "COM_acme_live_m25",
                        "name": "Acme",
                        "_memnet_tag": "COM",
                        "_memnet_hid": ego.hid,
                    },
                ),
                (
                    "TSK",
                    {
                        "id": "TSK_mission_q3",
                        "goal": "Q3 mission",
                        "status": "settled",
                        "_memnet_tag": "TSK",
                        "_memnet_hid": task.hid,
                    },
                ),
            ]
        if "src._memnet_hid" in cypher:
            if ego.hid not in cypher or task.hid not in cypher:
                return []
            return [
                (
                    "ABOUT",
                    {"id": "E_about_q3", "relation": "ABOUT", "_memnet_tag": "EDG"},
                    task.hid,
                    ego.hid,
                )
            ]
        return []

    monkeypatch.setattr(adapter, "_execute", _exec)
    adapter.flush(fixture)
    assert any("MERGE (n:COM {_memnet_hid:" in c for c in seen)
    assert not any("MERGE (n:COM {id:" in c for c in seen)
    about = next(c for c in seen if "MERGE (a)-[r:ABOUT" in c)
    assert task.hid in about
    assert ego.hid in about
    seen.clear()
    loaded = adapter.hydrate(ego.hid, HydrateBudget(max_nodes=20, max_edges=20, depth=2))
    assert any("_memnet_hid:" in c and "properties(n)" in c for c in seen)
    assert not any("MATCH (ego {id:" in c for c in seen)
    assert any(n.id == "COM_acme_live_m25" for n in loaded.nodes)
    about_e = next(e for e in loaded.edges if e.fields.get("relation") == "ABOUT")
    assert about_e.fields.get("dist") == "COM_acme_live_m25"
