"""Mutate refuses an EDGE line or the SCHEMA line over the line cap.

Record lines are covered in test_line_cap_whole_line.py. Edge lines (written
with endpoint nicks) and the per-tag SCHEMA line (widened by undeclared keys)
can also pass every per-value check yet make a snapshot unsaveable; mutate must
refuse them with limit_exceeded line_bytes|n/max and roll the session back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session
from memnet.snapshot import load_snapshot, snapshot_text, write_snapshot

LINE_CAP = 135168
EDGE = "MATCH (a:PLR {id:'A'}),(b:PLR {id:'B'}) CREATE (a)-[:OWNS {%s}]->(b)"


@pytest.fixture
def default_caps(monkeypatch):
    monkeypatch.delenv("MEMNET_MAX_VALUE_BYTES", raising=False)
    monkeypatch.delenv("MEMNET_MAX_LINE_BYTES", raising=False)
    caps = Caps()
    assert caps.max_line_bytes == LINE_CAP
    return caps


@pytest.fixture
def ss(memnet_temp, schema_file, default_caps):
    s = open_session(map_file=str(schema_file), caps=default_caps)
    MutateGate(s).apply(
        [
            "CREATE (:PLR {id:'A', identity:'x'})",
            "CREATE (:PLR {id:'B', identity:'y'})",
            "CREATE (:TSK {id:'T1', goal:'g'})",
        ],
        mode="add",
    )
    return s


def _body(s) -> str:
    return "\n".join(ln for ln in snapshot_text(s).split("\n") if not ln.startswith("@SNAP:"))


def _state(s):
    return _body(s), {h: dict(r.fields) for h, r in s.store._by_hid.items()}


def _edge_props(at: int, attrs: int) -> str:
    return f"at: '{chr(28) * at}', attrs: '{chr(28) * attrs}'"


def _edge_line_bytes(s) -> int:
    (edge,) = [r for r in s.store._by_hid.values() if r.tag == "EDG"]
    text = snapshot_text(s)
    line = next(ln for ln in text.split("\n") if ln.startswith("@EDG: " + edge.fields["id"]))
    return len(line.encode("utf-8"))


def _fit_edge_props(ss, margin: int) -> str:
    """Edge props whose line is exactly LINE_CAP - margin bytes (ids A, B)."""
    at = "\x1c" * 20000  # 80000 escaped bytes
    attrs = "\x1c" * 13000  # 52000 escaped bytes
    probe = open_session(
        map_file=str(
            Path(__file__).parent.parent / "parts/common/memnet/memnet/examples/schema.example.txt"
        ),
        caps=ss.caps,
    )
    MutateGate(probe).apply(
        [
            "CREATE (:PLR {id:'A', identity:'x'})",
            "CREATE (:PLR {id:'B', identity:'y'})",
            "CREATE (:TSK {id:'T1', goal:'g'})",
        ],
        mode="add",
    )
    MutateGate(probe).apply([EDGE % f"at: '{at}', attrs: '{attrs}'"], mode="add")
    pad = LINE_CAP - margin - _edge_line_bytes(probe)
    assert pad > 0
    return f"at: '{at}', attrs: '{attrs}{'x' * pad}'"


def _schema_set(n_keys: int, key_len: int) -> str:
    sets = ", ".join(f"n.k{i:03d}{'x' * (key_len - 4)} = 'v'" for i in range(n_keys))
    return f"MATCH (n:TSK {{id:'T1'}}) SET {sets}"


def test_oversized_edge_line_refused_state_unchanged(ss):
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply([EDGE % _edge_props(20000, 20000)], mode="add")
    assert ei.value.code == "limit_exceeded"
    n, cap = ei.value.message.removeprefix("line_bytes|").split("/")
    assert int(n) > LINE_CAP == int(cap)
    assert _state(ss) == before
    assert not [r for r in ss.store._by_hid.values() if r.tag == "EDG"]


def test_rename_making_edge_line_oversized_refused(ss):
    # The edge record is untouched, but its line is written with endpoint nicks,
    # so renaming an endpoint to a longer nick can push the edge line over.
    fit = _fit_edge_props(ss, margin=10)
    MutateGate(ss).apply([EDGE % fit], mode="add")
    assert _edge_line_bytes(ss) == LINE_CAP - 10
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            ["MATCH (n:PLR {id:'A'}) SET n.id = '" + "N" * 40 + "'"], mode="update"
        )
    assert ei.value.code == "limit_exceeded"
    assert ei.value.message == f"line_bytes|{LINE_CAP - 10 + 39}/{LINE_CAP}"
    assert _state(ss) == before


def test_oversized_schema_line_refused_state_unchanged(ss):
    before = _state(ss)
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply([_schema_set(58, 2400)], mode="update")
    assert ei.value.code == "limit_exceeded"
    n, cap = ei.value.message.removeprefix("line_bytes|").split("/")
    assert int(n) > LINE_CAP == int(cap)
    assert _state(ss) == before
    assert "k000" not in before[0]


def test_just_fitting_edge_line_saves_and_reloads(ss, tmp_path: Path):
    MutateGate(ss).apply([EDGE % _fit_edge_props(ss, margin=0)], mode="add")
    assert _edge_line_bytes(ss) == LINE_CAP
    path = tmp_path / "edge.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path, caps=Caps())
    assert _body(loaded) == _body(ss)


def test_just_fitting_schema_line_saves_and_reloads(ss, tmp_path: Path):
    MutateGate(ss).apply([_schema_set(50, 2400)], mode="update")
    schema = next(ln for ln in snapshot_text(ss).split("\n") if ln.startswith("SCHEMA TSK ;"))
    assert len(schema.encode()) <= LINE_CAP
    path = tmp_path / "schema.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path, caps=Caps())
    assert _body(loaded) == _body(ss)
