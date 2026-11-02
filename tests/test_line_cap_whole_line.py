"""Mutate refuses a record whose WHOLE escaped snapshot line exceeds the line cap.

Per-value checks (value_bytes, per-value line_bytes) can each pass while the
record line as snapshot emit writes it is over caps.max_line_bytes; such a
record would be stored but could never be saved. Mutate must refuse it with
limit_exceeded line_bytes|n/max (n = whole escaped line bytes), storing nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.snapshot import load_snapshot, write_snapshot
from memnet.wire import emit_record_line

VALUE_CAP = 32768
LINE_CAP = 135168
FIELDS = ("id", "identity", "wealth", "cashflow", "monopoly", "reputation", "inventory")


@pytest.fixture
def default_caps(monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_VALUE_BYTES", raising=False)
    monkeypatch.delenv("MEMNET_MAX_LINE_BYTES", raising=False)
    caps = Caps()
    assert (caps.max_value_bytes, caps.max_line_bytes) == (VALUE_CAP, LINE_CAP)
    return caps


def _create(identity: str, inventory: str) -> str:
    return (
        "CREATE (:PLR {id: 'PLR_V', identity: '" + identity + "', wealth: 1, cashflow: 0, "
        "monopoly: 0, reputation: 0, inventory: '" + inventory + "'})"
    )


def _line_bytes(identity: str, inventory: str) -> int:
    """Escaped UTF-8 size of the PLR_V line exactly as snapshot emit writes it."""
    vals = {"id": "PLR_V", "identity": identity, "wealth": "1", "cashflow": "0",
            "monopoly": "0", "reputation": "0", "inventory": inventory}
    return len(emit_record_line("PLR", [vals[f] for f in FIELDS]).encode("utf-8"))


def _assert_line_refused(ei, n: int) -> None:
    assert n > LINE_CAP
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == f"line_bytes|{n}/{LINE_CAP}"


@pytest.mark.parametrize(
    "identity,inventory",
    [
        # Literal case: two 32768-byte values, each at the value cap and each
        # escaping to 131072 bytes (fits per value), together 262144+ bytes.
        ("\x1c" * VALUE_CAP, "\x1c" * VALUE_CAP),
        # Two 20000-byte values escaping to 80000 each: 160000+ together.
        ("\x1c" * 20000, "\x1c" * 20000),
    ],
    ids=["two_32768_byte_values", "two_20000_fs_values"],
)
def test_create_whole_line_over_cap_refused(
    memnet_temp, schema_file, default_caps, identity, inventory
):
    assert len(identity.encode()) <= VALUE_CAP and len(inventory.encode()) <= VALUE_CAP
    ss = open_session(map_file=str(schema_file), caps=default_caps)
    n = _line_bytes(identity, inventory)
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply([_create(identity, inventory)], mode="add")
    _assert_line_refused(ei, n)
    assert ss.store.get("PLR_V") is None


def test_set_pushing_whole_line_over_cap_refused(memnet_temp, schema_file, default_caps):
    ss = open_session(map_file=str(schema_file), caps=default_caps)
    identity = "\x1c" * VALUE_CAP  # escapes to 131072 bytes; line still fits
    MutateGate(ss).apply([_create(identity, "bag")], mode="add")
    before = dict(ss.store.get("PLR_V").fields)
    assert _line_bytes(identity, "bag") <= LINE_CAP
    added = "x" * 8000  # 8000 bytes: fine as a value, pushes the line over
    n = _line_bytes(identity, added)
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            ["MATCH (n:PLR {id: 'PLR_V'}) SET n.inventory = '" + added + "'"],
            mode="update",
        )
    _assert_line_refused(ei, n)
    assert dict(ss.store.get("PLR_V").fields) == before


def test_just_fitting_whole_line_saves_and_reloads(
    memnet_temp, schema_file, default_caps, tmp_path: Path
):
    ss = open_session(map_file=str(schema_file), caps=default_caps)
    identity = "\x1c" * VALUE_CAP  # 131072 escaped bytes
    inventory = "y" * (LINE_CAP - _line_bytes(identity, ""))
    assert _line_bytes(identity, inventory) == LINE_CAP
    MutateGate(ss).apply([_create(identity, inventory)], mode="add")
    fields = ss.store.get("PLR_V").fields
    assert (fields["identity"], fields["inventory"]) == (identity, inventory)
    path = tmp_path / "fit.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path, caps=Caps())
    got = loaded.store.get("PLR_V").fields
    assert (got["identity"], got["inventory"]) == (identity, inventory)
