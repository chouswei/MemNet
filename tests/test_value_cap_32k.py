"""MN-REQ-14.9 — default value cap 32768 bytes (was 4096)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.snapshot import load_snapshot, write_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "snapshot-0.19.18.snap"
CAP = 32768


def _create(val: str) -> str:
    return (
        "CREATE (:PLR {id: 'PLR_V', identity: '" + val + "', wealth: 1, cashflow: 0, "
        "monopoly: 0, reputation: 0, inventory: 'bag'})"
    )


def test_default_cap_is_32768(monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_VALUE_BYTES", raising=False)
    assert Caps().max_value_bytes == CAP


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_VALUE_BYTES", "4096")
    assert Caps().max_value_bytes == 4096


def test_32768_bytes_accepted(memnet_temp, schema_file, monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_VALUE_BYTES", raising=False)
    ss = open_session(map_file=str(schema_file), caps=Caps())
    MutateGate(ss).apply([_create("x" * CAP)], mode="add")
    assert len(ss.store.get("PLR_V").fields["identity"].encode()) == CAP


def test_32769_bytes_refused_with_clear_error(memnet_temp, schema_file, monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_VALUE_BYTES", raising=False)
    ss = open_session(map_file=str(schema_file), caps=Caps())
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply([_create("x" * (CAP + 1))], mode="add")
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == f"value_bytes|{CAP + 1}/{CAP}"
    assert ss.store.get("PLR_V") is None


def test_multibyte_counted_in_bytes(memnet_temp, schema_file, monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_VALUE_BYTES", raising=False)
    ss = open_session(map_file=str(schema_file), caps=Caps())
    # 10923 x 3-byte chars = 32769 bytes: fewer than 32768 characters, still refused.
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply([_create("测" * 10923)], mode="add")
    assert ei.value.message == f"value_bytes|{CAP + 1}/{CAP}"
    # 10922 x 3 bytes + 2 ASCII = exactly 32768 bytes: accepted.
    MutateGate(ss).apply([_create("测" * 10922 + "xx")], mode="add")
    assert len(ss.store.get("PLR_V").fields["identity"].encode()) == CAP


def test_old_snapshot_loads_under_new_cap(memnet_temp, monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_VALUE_BYTES", raising=False)
    loaded = load_snapshot(FIXTURE, caps=Caps())
    assert loaded.store.get("PLR_V118") is not None


def test_value_over_old_cap_round_trips(memnet_temp, schema_file, tmp_path: Path, monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_VALUE_BYTES", raising=False)
    ss = open_session(map_file=str(schema_file), caps=Caps())
    blob = "n" * 8000
    MutateGate(ss).apply([_create(blob)], mode="add")
    path = tmp_path / "big.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path, caps=Caps())
    assert loaded.store.get("PLR_V").fields["identity"] == blob


def test_value_at_cap_is_accepted_but_exceeds_default_line_cap_on_save(
    memnet_temp, schema_file, tmp_path: Path, monkeypatch
):
    # Open design point: line_bytes stays 32768, so a max-size value cannot be saved.
    monkeypatch.delenv("MEMNET_MAX_VALUE_BYTES", raising=False)
    monkeypatch.delenv("MEMNET_MAX_LINE_BYTES", raising=False)
    ss = open_session(map_file=str(schema_file), caps=Caps())
    MutateGate(ss).apply([_create("x" * CAP)], mode="add")
    with pytest.raises(MemNetError) as ei:
        write_snapshot(ss, tmp_path / "max.snap")
    assert ei.value.code == "snapshot_unsaveable"
    assert "line_bytes" in ei.value.message
