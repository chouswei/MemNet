"""Neighbourhood reserve (RSV) — llm_id + TTL (MN-REQ-12.13)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.neighbourhood_reserve import (
    IMPLEMENTED,
    extend,
    release,
    reserve,
)
from memnet.pin_map_composer import PinMapComposer
from memnet.session import open_session, set_now_override

_PLR = (
    "CREATE (:PLR {id: 'PLR01', identity: 'Hero', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)
_PLR2 = (
    "CREATE (:PLR {id: 'PLR02', identity: 'Villain', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)
_PATCH = "MATCH (n {id: 'PLR01'}) SET n.wealth = 9"


def test_reserve_implemented_flag():
    assert IMPLEMENTED is True


def test_reserve_expire_auto_release(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    t0 = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)
    set_now_override(t0)
    lease = reserve(
        ss.reserves,
        ss.store,
        anchor="PLR01",
        llm_id="coder_a",
        depth=1,
        ttl_s=60,
        now=t0,
    )
    assert lease.rid == "R1"
    assert "PLR01" in lease.ids

    # Still active within TTL
    set_now_override(t0 + timedelta(seconds=30))
    text = PinMapComposer(ss).compose(anchor="PLR01")[1]
    assert "## Reserves" in text
    assert "RSV [R1]" in text
    assert "llm_id=coder_a" in text

    # Expired → purged on pin_map / mutate path
    set_now_override(t0 + timedelta(seconds=120))
    text2 = PinMapComposer(ss).compose(anchor="PLR01")[1]
    assert "## Reserves" not in text2
    assert "R1" not in ss.reserves.leases

    # Other writer may mutate after expiry without llm_id
    MutateGate(ss).apply([_PATCH], mode="update")
    assert ss.store.get("PLR01").fields["wealth"] == "9"


def test_reserve_blocks_foreign_mutate(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    t0 = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)
    set_now_override(t0)
    reserve(
        ss.reserves,
        ss.store,
        anchor="PLR01",
        llm_id="coder_a",
        depth=1,
        ttl_s=120,
        now=t0,
    )
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply([_PATCH], mode="update", llm_id="coder_b")
    assert ei.value.code == "reserved"

    with pytest.raises(MemNetError) as ei2:
        MutateGate(ss).apply([_PATCH], mode="update")
    assert ei2.value.code == "no_llm_id"

    MutateGate(ss).apply([_PATCH], mode="update", llm_id="coder_a")
    assert ss.store.get("PLR01").fields["wealth"] == "9"


def test_reserve_conflict_on_overlap(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR, _PLR2], mode="add")
    t0 = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)
    set_now_override(t0)
    reserve(
        ss.reserves,
        ss.store,
        anchor="PLR01",
        llm_id="coder_a",
        depth=0,
        ttl_s=120,
        now=t0,
    )
    with pytest.raises(MemNetError) as ei:
        reserve(
            ss.reserves,
            ss.store,
            anchor="PLR01",
            llm_id="coder_b",
            depth=0,
            ttl_s=120,
            now=t0,
        )
    assert ei.value.code == "reserve_conflict"


def test_extend_and_release(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    t0 = datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)
    set_now_override(t0)
    lease = reserve(
        ss.reserves,
        ss.store,
        anchor="PLR01",
        llm_id="coder_a",
        depth=1,
        ttl_s=30,
        now=t0,
    )
    set_now_override(t0 + timedelta(seconds=20))
    extended = extend(
        ss.reserves,
        rid=lease.rid,
        llm_id="coder_a",
        ttl_s=120,
        now=t0 + timedelta(seconds=20),
    )
    assert extended.left_s(t0 + timedelta(seconds=20)) == 120

    with pytest.raises(MemNetError) as ei:
        release(ss.reserves, rid=lease.rid, llm_id="coder_b")
    assert ei.value.code == "reserve_mismatch"

    release(ss.reserves, rid=lease.rid, llm_id="coder_a")
    assert lease.rid not in ss.reserves.leases
