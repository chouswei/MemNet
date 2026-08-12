"""M2.5 durable store adapter seam: hydrate → session → pin_map."""

from __future__ import annotations

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
from memnet.durable.agensgraph import AgensGraphAdapter, AgensGraphConfig
from memnet.exceptions import MemNetError
from memnet.models import Record
from memnet.pin_map_composer import PinMapComposer
from memnet.session import open_session
from memnet.session_lifecycle import SessionLifecycle

_COM_MAP = [
    "SCHEMA COM ; fields=id name kind",
    "SCHEMA TSK ; fields=id goal status recycle",
]


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
    fake = FakeDurableAdapter(seed_company_ego=True)
    owner = get_sync_owner(fake)
    ss = open_session(map_lines=list(_COM_MAP))

    loaded = owner.hydrate_into_session(
        ss, "COM_acme", HydrateBudget(max_nodes=20, max_edges=20, depth=2)
    )
    assert loaded.ego_id == "COM_acme"
    assert "COM_acme" in ss.store.by_id
    assert "TSK_mission_q3" in ss.store.by_id
    assert "ABOUT" in ss.relations

    rows, text = PinMapComposer(ss).compose(
        anchor="COM_acme", depth=2, max_rows=50
    )
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
    assert "COM_acme" in ss2.store.by_id
    _, text = PinMapComposer(ss2).compose(anchor="COM_acme", depth=2, max_rows=50)
    assert "Acme" in text


def test_one_sync_owner_rejects_second_adapter(memnet_temp):
    get_sync_owner(FakeDurableAdapter())
    with pytest.raises(MemNetError) as ei:
        get_sync_owner(FakeDurableAdapter())
    assert ei.value.code == "dual_sync_owner"


def test_make_adapter_from_env_defaults_to_fake(monkeypatch):
    monkeypatch.delenv("MEMNET_AGENSGRAPH_URL", raising=False)
    monkeypatch.delenv("MEMNET_DURABLE_FAKE", raising=False)
    adapter = make_adapter_from_env()
    assert isinstance(adapter, FakeDurableAdapter)


def test_make_adapter_from_env_agens_when_url(monkeypatch):
    monkeypatch.setenv("MEMNET_AGENSGRAPH_URL", "postgresql://localhost/memnet")
    monkeypatch.delenv("MEMNET_DURABLE_FAKE", raising=False)
    adapter = make_adapter_from_env()
    assert isinstance(adapter, AgensGraphAdapter)


def test_agens_hydrate_unavailable_without_psycopg():
    adapter = AgensGraphAdapter(
        AgensGraphConfig(url="postgresql://localhost/memnet")
    )
    with pytest.raises(MemNetError) as ei:
        adapter.hydrate("COM_acme", HydrateBudget())
    assert ei.value.code == "agensgraph_unavailable"


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
    assert "COM_missing" not in ss.store.by_id
