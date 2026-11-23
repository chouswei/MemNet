"""Compare-and-set over mutate: the write shape the Atelier single-store design relies on.

Atelier's design (docs/memnet-single-store/design.md section 4, MN-ATOMIC) allocates
with ``MATCH (c:CTR {acct:'A1'}) WHERE c.view = 8 AND c.rev = 41 ... SET ...`` and needs:
exactly one match or the batch fails, a miss writes nothing, and an earlier line in the
same batch is undone when a later CAS misses. These tests pin what the engine does today.
"""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

_MAP = ["SCHEMA CTR ; fields=id acct rev seq view", "SCHEMA PRT ; fields=id name"]


def _cas(*, view, rev, seq) -> str:
    return (
        f"MATCH (c:CTR {{acct: 'A1'}}) WHERE c.view = {view} AND c.rev = {rev} "
        f"AND c.seq = {seq} SET c.rev = 43, c.seq = 12, c.view = 9"
    )


def _apply(ss, *stmts):
    return MutateGate(ss).apply(list(stmts), mode="mutate")


def _session():
    ss = open_session(map_lines=_MAP)
    _apply(ss, "CREATE (:CTR {id: 'C1', acct: 'A1', rev: 41, seq: 11, view: 8})")
    return ss


def _ctr(ss) -> dict[str, str]:
    rec = ss.store.get("C1")
    assert rec is not None
    return {k: rec.fields[k] for k in ("rev", "seq", "view")}


def _names(ss) -> list[str]:
    return sorted(r.fields.get("name", "") for r in ss.store.list_records("PRT"))


def test_cas_hit_updates_the_counter():
    ss = _session()
    _apply(ss, _cas(view=8, rev=41, seq=11))
    assert _ctr(ss) == {"rev": "43", "seq": "12", "view": "9"}


@pytest.mark.parametrize(
    "expect",
    [
        {"view": 7, "rev": 41, "seq": 11},  # stale view
        {"view": 8, "rev": 40, "seq": 11},  # stale rev
        {"view": 8, "rev": 41, "seq": 10},  # stale seq
    ],
)
def test_cas_miss_is_not_found_and_writes_nothing(expect):
    ss = _session()
    with pytest.raises(MemNetError) as ei:
        _apply(ss, _cas(**expect))
    assert ei.value.code == "not_found"
    assert _ctr(ss) == {"rev": "41", "seq": "11", "view": "8"}


def test_cas_miss_rolls_back_earlier_lines_of_the_same_batch():
    ss = _session()
    with pytest.raises(MemNetError) as ei:
        _apply(
            ss,
            "CREATE (:PRT {id: 'P1', name: 'first'})",
            _cas(view=7, rev=41, seq=11),  # stale: misses
        )
    assert ei.value.code == "not_found"
    assert _names(ss) == []
    assert _ctr(ss) == {"rev": "41", "seq": "11", "view": "8"}


def test_batch_wheres_see_the_pre_batch_state():
    """Pinned current behaviour: every line of a batch is resolved against the store as
    it was before the batch, so a second CAS in the same batch still hits. The design
    must therefore use one CAS per batch (see design.md section 4)."""
    ss = _session()
    _apply(ss, _cas(view=8, rev=41, seq=11), _cas(view=8, rev=41, seq=11))
    assert _ctr(ss) == {"rev": "43", "seq": "12", "view": "9"}


@pytest.mark.xfail(
    strict=True,
    reason="lost update: two SETs on one node in one batch apply the second to the "
    "pre-batch record, so the first is lost (rev reverts to 41). Desired: both apply.",
)
def test_two_sets_on_one_node_in_one_batch_both_apply():
    ss = _session()
    _apply(
        ss,
        "MATCH (c:CTR {acct: 'A1'}) SET c.rev = 50",
        "MATCH (c:CTR {acct: 'A1'}) SET c.seq = 99",
    )
    assert _ctr(ss) == {"rev": "50", "seq": "99", "view": "8"}


def test_cas_equality_is_numeric_for_number_literals_and_exact_text_otherwise():
    ss = _session()
    _apply(ss, "MATCH (c:CTR {acct: 'A1'}) SET c.seq = '000011'")
    with pytest.raises(MemNetError):  # 11 does not match the text '000011'
        _apply(ss, _cas(view=8, rev=41, seq=11))
    _apply(
        ss,
        "MATCH (c:CTR {acct: 'A1'}) WHERE c.seq = '000011' SET c.seq = 12",
    )
    assert _ctr(ss)["seq"] == "12"
