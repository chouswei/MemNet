"""MN-VER-14-D02 follow-ups (PR #246 model review B1-B3, quoted literals, L-246-4).

B1: a relationship WHERE + SET that matches nothing, or whose end id does not
resolve, is refused not_found with no write.
B2: SET on a protected relationship field (id, merge, src, dist, relation) is
refused invalid_field with no write.
B3: a relationship SET with no WHERE and no id pattern is refused
unsupported_predicate naming SET and WHERE (never DELETE) with no write; a SET
with an id pattern needs no WHERE.
Quoted literals are never scanned as SET targets.
L-246-4 (MN_VER_14_S12 (g)): the session byte ledger is dropped on expire and on
save-on-expire, and the next load rebuilds a total equal to a full recount.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.registry import contains, get_entry
from memnet.session import expire_snap_path, open_session, purge_expired, set_now_override
from memnet.session_bytes import full_recount_total, incremental_total, ledger_for
from memnet.snapshot import load_snapshot

_MAP = ["SCHEMA PRT ; fields=id name role"]


def _apply(ss, *stmts, **kw):
    return MutateGate(ss).apply(list(stmts), mode="mutate", **kw)


def _session(e1_kind: str = "a"):
    """P0-[E1 links kind=<e1_kind>]->P1-[E2 links kind=c]->P2."""
    ss = open_session(map_lines=_MAP)
    _apply(
        ss,
        *[f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: 'r'}})" for i in range(3)],
        allow_new_relation=True,
    )
    _apply(
        ss,
        "MATCH (a {id: 'P0'}), (b {id: 'P1'}) "
        f"CREATE (a)-[:links {{id: 'E1', kind: '{e1_kind}', n: 2}}]->(b)",
        allow_new_relation=True,
    )
    _apply(
        ss,
        "MATCH (a {id: 'P1'}), (b {id: 'P2'}) CREATE (a)-[:links {id: 'E2', kind: 'c', n: 0}]->(b)",
        allow_new_relation=True,
    )
    return ss


def _attrs(rec) -> dict[str, str]:
    raw = rec.fields.get("attrs", "")
    return dict(kv.split("=", 1) for kv in raw.split(";") if kv)


def _edges(ss) -> dict[str, dict[str, str]]:
    return {e.fields["id"]: _attrs(e) for e in ss.store.list_records("EDG")}


def _state(ss):
    nodes = sorted((r.hid, tuple(sorted(r.fields.items()))) for r in ss.store.list_records("PRT"))
    edges = sorted((e.hid, tuple(sorted(e.fields.items()))) for e in ss.store.list_records("EDG"))
    return nodes, edges


def _refused(ss, statement: str, code: str) -> MemNetError:
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        _apply(ss, statement)
    assert ei.value.code == code, f"{statement!r}: {ei.value.code} {ei.value}"
    assert _state(ss) == before, f"{statement!r} wrote before refusing"
    return ei.value


# --- B1: no match / unresolved end id -> not_found ------------------------------


def test_b1_where_set_matching_nothing_is_not_found(memnet_temp):
    ss = _session()
    _refused(ss, "MATCH ()-[r:links]-() WHERE r.kind = 'zzz' SET r.kind = 'b'", "not_found")


def test_b1_unresolved_end_id_is_not_found(memnet_temp):
    ss = _session()
    _refused(
        ss,
        "MATCH (a {id: 'NOPE'})-[r:links]->(b) WHERE r.kind = 'a' SET r.kind = 'b'",
        "not_found",
    )


# --- B2: protected relationship fields -> invalid_field ------------------------


@pytest.mark.parametrize("key", ["id", "merge", "src", "dist", "relation"])
def test_b2_set_protected_relationship_field_is_invalid_field(memnet_temp, key):
    ss = _session()
    _refused(ss, f"MATCH ()-[r:links]-() WHERE r.kind = 'a' SET r.{key} = 'X'", "invalid_field")


# --- B3: no WHERE and no id -> unsupported_predicate; id pattern needs no WHERE --


def test_b3_set_without_where_or_id_is_refused(memnet_temp):
    ss = _session()
    err = _refused(ss, "MATCH ()-[r:links]-() SET r.kind = 'b'", "unsupported_predicate")
    msg = str(err).upper()
    assert "SET" in msg and "WHERE" in msg, f"refusal does not name SET and WHERE: {err}"
    assert "DELETE" not in msg, f"refusal names DELETE: {err}"


def test_b3_set_with_id_pattern_needs_no_where(memnet_temp):
    ss = _session()
    _apply(ss, "MATCH ()-[r {id: 'E1'}]-() SET r.kind = 'b'")
    edges = _edges(ss)
    assert edges["E1"]["kind"] == "b"
    assert edges["E1"]["n"] == "2"
    assert edges["E2"] == {"kind": "c", "n": "0"}


# --- quoted literals are not SET targets ---------------------------------------


def test_quoted_where_value_not_scanned_as_set_target(memnet_temp):
    ss = _session(e1_kind="x.y = z")
    assert _edges(ss)["E1"]["kind"] == "x.y = z"
    _apply(ss, "MATCH ()-[r:links]-() WHERE r.kind = 'x.y = z' SET r.kind = 'b'")
    edges = _edges(ss)
    assert edges["E1"]["kind"] == "b"
    assert edges["E2"] == {"kind": "c", "n": "0"}


def test_quoted_set_value_stored_as_literal(memnet_temp):
    ss = _session()
    _apply(ss, "MATCH ()-[r:links]-() WHERE r.kind = 'a' SET r.kind = 'a.b = c'")
    edges = _edges(ss)
    assert edges["E1"]["kind"] == "a.b = c"
    assert edges["E1"]["n"] == "2"
    assert edges["E2"] == {"kind": "c", "n": "0"}


# --- L-246-4: ledger dropped on expire / save-on-expire, rebuilt on load --------


def _session_with_ledger(caps: Caps | None = None):
    ss = open_session(map_lines=_MAP, ttl_minutes=1, caps=caps)
    _apply(
        ss,
        *[f"CREATE (:PRT {{id: 'P{i}', name: 'part{i}', role: 'r'}})" for i in range(3)],
        "MATCH (a {id: 'P0'}), (b {id: 'P1'}) CREATE (a)-[:links {id: 'E1', kind: 'a'}]->(b)",
        allow_new_relation=True,
    )
    total = incremental_total(ss)
    assert total is not None
    entry = get_entry(ss.session_id)
    assert entry is not None and entry.bytes_ledger is not None
    return ss, entry, total


def _expire_now() -> None:
    set_now_override(datetime.now(UTC) + timedelta(minutes=5))


def test_ledger_dropped_on_expire(memnet_temp, monkeypatch):
    monkeypatch.delenv("MEMNET_SAVE_ON_EXPIRE", raising=False)
    ss, entry, _ = _session_with_ledger()
    sid = ss.session_id
    _expire_now()
    purge_expired()
    set_now_override(None)
    assert not contains(sid)
    assert get_entry(sid) is None


def test_ledger_dropped_on_save_on_expire_and_rebuilt_on_load(
    memnet_temp, tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("MEMNET_SAVE_ON_EXPIRE", "1")
    monkeypatch.setenv("MEMNET_EXPIRE_SNAPSHOT_DIR", str(tmp_path))
    caps = Caps()
    ss, old_entry, total_before = _session_with_ledger(caps)
    sid = ss.session_id
    old_ledger = old_entry.bytes_ledger
    _expire_now()
    purge_expired(caps)
    set_now_override(None)
    assert not contains(sid)
    snap = expire_snap_path(sid, caps)
    assert snap is not None and snap.is_file()

    loaded = load_snapshot(snap, caps=caps)
    new_entry = get_entry(loaded.session_id)
    assert new_entry is not None and new_entry is not old_entry
    ledger = ledger_for(loaded)
    assert ledger is not old_ledger
    total = incremental_total(loaded)
    assert total is not None
    assert total == full_recount_total(loaded)
    assert total == total_before
