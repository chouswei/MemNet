"""MN-REQ-05.4 / MN-VER-05-S02 — effective field cap (default 64)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.output import format_err
from memnet.session import open_session
from memnet.snapshot import (
    _snapshot_emit_tag_map,
    effective_snapshot_fields,
    first_over_field_cap,
    load_snapshot,
    write_snapshot,
)

_PRT_MAP = ["SCHEMA PRT ; fields=id name qname path sysml_kind session grain recycle"]
_CST_MAP = ["SCHEMA CST ; fields=id name role"]
_PRT_DECLARED = 8
_CST_DECLARED = 3


def _extras(n: int, *, start: int = 0) -> dict[str, str]:
    return {f"x{i:03d}": f"v{i:03d}" for i in range(start, start + n)}


def _gql_props(fields: dict[str, str]) -> str:
    return ", ".join(f"{k}: '{v}'" for k, v in fields.items())


def _create(kind: str, fields: dict[str, str]) -> str:
    return f"CREATE (:{kind} {{{_gql_props(fields)}}})"


def test_prt_38_fields_saves_and_reloads(memnet_temp, tmp_path: Path):
    ss = open_session(map_lines=list(_PRT_MAP))
    extras = _extras(38 - _PRT_DECLARED)
    fields = {
        "id": "PRT_38",
        "name": "wide",
        "qname": "N",
        "path": "p",
        "sysml_kind": "part",
        "session": "",
        "grain": "",
        "recycle": "",
        **extras,
    }
    MutateGate(ss).apply([_create("PRT", fields)], mode="add")
    rec = ss.store.get("PRT_38")
    assert rec is not None
    for key, val in extras.items():
        assert rec.fields.get(key) == val
    eff = effective_snapshot_fields(ss)["PRT"]
    assert len(eff) == 38
    path = tmp_path / "prt38.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path)
    got = loaded.store.get("PRT_38")
    assert got is not None
    for key, val in extras.items():
        assert got.fields.get(key) == val
    assert got.fields.get("name") == "wide"
    assert "x000" in loaded.tag_map.get("PRT").fields
    assert len(loaded.tag_map.get("PRT").fields) == 38


def test_mutate_refuses_over_cap_writes_nothing(memnet_temp):
    cap = Caps().max_fields
    over_n = cap - _CST_DECLARED + 1
    ss = open_session(map_lines=list(_CST_MAP))
    over = {"id": "N_OVER", "name": "a", "role": "b", **_extras(over_n)}
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply([_create("CST", over)], mode="add")
    assert ei.value.code == "limit_exceeded"
    assert f"fields|{_CST_DECLARED + over_n}/{cap}" in ei.value.message
    assert format_err(ei.value.code, ei.value.message) == (
        f"@ERR: limit_exceeded|fields {_CST_DECLARED + over_n}/{cap}"
    )
    assert ss.store.get("N_OVER") is None
    merge_fields = {"id": "N_MG", "name": "a", "role": "b", **_extras(over_n)}
    with pytest.raises(MemNetError) as ei2:
        MutateGate(ss).apply(
            [f"MERGE (:CST {{{_gql_props(merge_fields)}}})"],
            mode="mutate",
        )
    assert ei2.value.code == "limit_exceeded"
    assert "fields|" in ei2.value.message
    assert ss.store.get("N_MG") is None
    assert ss.store.get("N_OVER") is None


def test_mutate_set_past_cap_writes_nothing(memnet_temp):
    cap = Caps().max_fields
    ss = open_session(map_lines=list(_CST_MAP))
    at_cap = {"id": "N_SET", "name": "a", "role": "b", **_extras(cap - _CST_DECLARED)}
    MutateGate(ss).apply([_create("CST", at_cap)], mode="add")
    rec = ss.store.get("N_SET")
    assert rec is not None
    assert rec.fields.get("x000") == "v000"
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply(
            ["MATCH (n:CST {id: 'N_SET'}) SET n.x061 = 'nope'"],
            mode="mutate",
        )
    assert ei.value.code == "limit_exceeded"
    assert f"fields|{cap + 1}/{cap}" in ei.value.message
    rec = ss.store.get("N_SET")
    assert rec is not None
    assert rec.fields.get("name") == "a"
    assert rec.fields.get("x000") == "v000"
    assert rec.fields.get("x061") is None


def test_save_cap_not_stricter_than_mutate(memnet_temp, tmp_path: Path):
    ss = open_session(map_lines=list(_CST_MAP))
    cap = ss.caps.max_fields
    assert cap == Caps().max_fields == 64
    fields = {"id": "N_MAX", "name": "a", "role": "b", **_extras(cap - _CST_DECLARED)}
    MutateGate(ss).apply([_create("CST", fields)], mode="add")
    rec = ss.store.get("N_MAX")
    assert rec is not None
    eff = effective_snapshot_fields(ss)
    assert len(eff["CST"]) == cap
    assert first_over_field_cap(ss) is None
    emit = _snapshot_emit_tag_map(ss)
    assert list(emit.tags["CST"].fields) == list(eff["CST"])
    path = tmp_path / "at_cap.snap"
    write_snapshot(ss, path)
    loaded = load_snapshot(path)
    got = loaded.store.get("N_MAX")
    assert got is not None
    assert got.fields.get("x000") == "v000"
    last = f"x{cap - _CST_DECLARED - 1:03d}"
    assert got.fields.get(last) == f"v{cap - _CST_DECLARED - 1:03d}"
    assert len(loaded.tag_map.get("CST").fields) == cap


def test_load_snapshot_over_64_fails_loudly(memnet_temp, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MEMNET_MAX_FIELDS", "80")
    names = ["id"] + [f"p{i:03d}" for i in range(64)]
    assert len(names) == 65
    ss = open_session(
        map_lines=[f"SCHEMA WIDE ; fields={' '.join(names)}"],
        caps=Caps(),
    )
    path = tmp_path / "over.snap"
    write_snapshot(ss, path)
    monkeypatch.setenv("MEMNET_MAX_FIELDS", "64")
    with pytest.raises(MemNetError) as ei:
        load_snapshot(path, caps=Caps())
    assert ei.value.code == "limit_exceeded"
    assert "fields|65/64" in ei.value.message
