"""Mutate without rid behaves exactly as today (MN-REQ-12.13 reserve check unchanged).

Regression guard for MN-REQ-05.5 "Lost lease": the new rid= arg is additive.
A commit that names no rid keeps the existing reserve rule. Not xfail: these
pass on the shipped engine and must keep passing after the eviction engine ships.
"""

from __future__ import annotations

import asyncio
import json

from memnet.mutate_gate import MutateGate
from memnet.neighbourhood_reserve import reserve
from memnet.session import open_session
from memnet_mcp.server import mutate

_PLR = (
    "CREATE (:PLR {id: 'PLR01', identity: 'Hero', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)
_PATCH = "MATCH (n {id: 'PLR01'}) SET n.wealth = 999"


def _commit(**kwargs) -> dict:
    return json.loads(asyncio.run(mutate(wire_lines=[_PATCH], **kwargs)))


def test_no_rid_mutate_without_leases_succeeds(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")

    res = _commit(session=ss.session_id)

    assert res["exit_code"] == 0, res["stderr"]
    assert ss.store.get("PLR01").fields["wealth"] == "999"


def test_no_rid_mutate_on_leased_row_follows_reserve_rule(memnet_temp, schema_file):
    ss = open_session(map_file=str(schema_file))
    MutateGate(ss).apply([_PLR], mode="add")
    reserve(ss.reserves, ss.store, anchor="PLR01", llm_id="llm-1", ttl_s=600)

    other = _commit(session=ss.session_id, llm_id="llm-2")
    assert other["exit_code"] != 0
    assert "@ERR: reserved|" in other["stderr"], "another llm_id is refused by the reserve check"

    anonymous = _commit(session=ss.session_id)
    assert anonymous["exit_code"] != 0
    assert "@ERR: no_llm_id|" in anonymous["stderr"], "no llm_id on a leased row is refused"

    assert ss.store.get("PLR01").fields["wealth"] == "1", "a refused commit writes nothing"
