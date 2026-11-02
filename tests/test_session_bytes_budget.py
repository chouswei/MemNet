"""MN-REQ-14.10 — per-session byte budget (escaped snapshot line bytes)."""

from __future__ import annotations

import pytest

from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.snapshot import snapshot_text


def _create(n: int, val: str = "v") -> str:
    return (
        f"CREATE (:PLR {{id: 'PLR_{n}', identity: '{val}', wealth: 1, cashflow: 0, "
        "monopoly: 0, reputation: 0, inventory: 'bag'})"
    )


def _open(schema_file, monkeypatch, budget: str | None):
    if budget is None:
        monkeypatch.delenv("MEMNET_MAX_SESSION_BYTES", raising=False)
    else:
        monkeypatch.setenv("MEMNET_MAX_SESSION_BYTES", budget)
    return open_session(map_file=str(schema_file), caps=Caps())


def test_default_session_bytes_when_env_unset(monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_SESSION_BYTES", raising=False)
    assert Caps().max_session_bytes == 163840000 == 5000 * 32768


def test_env_override_session_bytes(monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_SESSION_BYTES", "12345")
    assert Caps().max_session_bytes == 12345


def test_refusal_at_budget_leaves_session_unchanged(memnet_temp, schema_file, monkeypatch):
    ss = _open(schema_file, monkeypatch, "3000")
    gate = MutateGate(ss)
    n = 0
    with pytest.raises(MemNetError) as ei:
        while n < 200:
            before = snapshot_text(ss)
            gate.apply([_create(n, "x" * 100)], mode="add")
            n += 1
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message.startswith("session_bytes|")
    total, cap = ei.value.message.split("|")[1].split("/")
    assert cap == "3000" and int(total) > 3000
    assert n > 0
    assert snapshot_text(ss) == before
    assert ss.store.get(f"PLR_{n}") is None


def test_delete_allowed_at_budget(memnet_temp, schema_file, monkeypatch):
    ss = _open(schema_file, monkeypatch, "3000")
    gate = MutateGate(ss)
    n = 0
    with pytest.raises(MemNetError):
        while n < 200:
            gate.apply([_create(n, "x" * 100)], mode="add")
            n += 1
    gate.apply(["MATCH (p:PLR {id: 'PLR_0'}) DELETE p"], mode="mutate")
    assert ss.store.get("PLR_0") is None
    gate.apply([_create(n, "x" * 100)], mode="add")
    assert ss.store.get(f"PLR_{n}") is not None
