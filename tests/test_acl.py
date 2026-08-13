"""CapsPolicy ACL — who / pin_map-vs-mutate / WorkerWriteScope / bind."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from memnet.acl import (
    WorkerWriteScope,
    check_bind,
    check_permission,
    check_write_scope,
    parse_write_scope,
)
from memnet.cli import app
from memnet.exceptions import MemNetError
from memnet.models import Record
from memnet.mutate_gate import MutateGate
from memnet.pin_map_composer import PinMapComposer
from memnet.session import get_session, open_session

runner = CliRunner()

_PLR = (
    "CREATE (:PLR {id: 'PLR01', identity: 'Hero', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)
_PLR2 = (
    "CREATE (:PLR {id: 'PLR02', identity: 'Villain', wealth: 1, cashflow: 0, "
    "monopoly: 0, reputation: 0, inventory: 'bag'})"
)


def _open(schema_file):
    ss = open_session(map_file=str(schema_file))
    return ss


def test_parse_write_scope():
    scope = parse_write_scope("anchors=A,B;ids=X;labels=tsk;relations=About,owns")
    assert scope is not None
    assert scope.anchors == frozenset({"A", "B"})
    assert scope.ids == frozenset({"X"})
    assert scope.labels == frozenset({"TSK"})
    assert scope.relations == frozenset({"about", "owns"})


def test_acl_who_missing_and_unknown(memnet_temp, schema_file):
    ss = _open(schema_file)
    ss.grant_caller("owner", can_pin_map=True, can_mutate=True)

    with pytest.raises(MemNetError) as ei:
        check_permission(ss.acl, caller=None, permission="mutate")
    assert ei.value.code == "acl_who"
    assert "mn_" not in (ei.value.example or "")

    with pytest.raises(MemNetError) as ei:
        check_permission(ss.acl, caller="intruder", permission="pin_map")
    assert ei.value.code == "acl_denied"


def test_acl_who_allow(memnet_temp, schema_file):
    ss = _open(schema_file)
    ss.grant_caller("owner", can_pin_map=True, can_mutate=True)
    assert check_permission(ss.acl, caller="owner", permission="mutate") == "owner"
    assert check_permission(ss.acl, caller="owner", permission="pin_map") == "owner"


def test_pin_map_vs_mutate_permission(memnet_temp, schema_file):
    ss = _open(schema_file)
    ss.grant_caller("reader", can_pin_map=True, can_mutate=False)
    ss.grant_caller("writer", can_pin_map=False, can_mutate=True)

    check_permission(ss.acl, caller="reader", permission="pin_map")
    with pytest.raises(MemNetError) as ei:
        check_permission(ss.acl, caller="reader", permission="mutate")
    assert ei.value.code == "acl_forbidden"

    check_permission(ss.acl, caller="writer", permission="mutate")
    with pytest.raises(MemNetError) as ei:
        check_permission(ss.acl, caller="writer", permission="pin_map")
    assert ei.value.code == "acl_forbidden"


def test_mutate_gate_rejects_reader(memnet_temp, schema_file):
    ss = _open(schema_file)
    ss.grant_caller("reader", can_pin_map=True, can_mutate=False)
    gate = MutateGate(ss)
    with pytest.raises(MemNetError) as ei:
        gate.apply([_PLR], mode="add", caller="reader", require_bind=True)
    assert ei.value.code == "acl_forbidden"


def test_mutate_gate_allows_writer(memnet_temp, schema_file):
    ss = _open(schema_file)
    ss.grant_caller("writer", can_pin_map=True, can_mutate=True)
    gate = MutateGate(ss)
    result = gate.apply([_PLR], mode="add", caller="writer", require_bind=True)
    assert result.records
    assert ss.store.get("PLR01") is not None


def test_pin_map_composer_who(memnet_temp, schema_file):
    ss = _open(schema_file)
    ss.grant_caller("writer", can_pin_map=True, can_mutate=True)
    MutateGate(ss).apply([_PLR], mode="add", caller="writer")
    ss.grant_caller("reader", can_pin_map=True, can_mutate=False)
    text = PinMapComposer(ss).compose(anchor="PLR01", caller="reader")[1]
    assert "PLR01" in text

    ss.grant_caller("muted", can_pin_map=False, can_mutate=False)
    with pytest.raises(MemNetError) as ei:
        PinMapComposer(ss).compose(anchor="PLR01", caller="muted")
    assert ei.value.code == "acl_forbidden"


def test_write_scope_hard_reject(memnet_temp, schema_file):
    ss = _open(schema_file)
    scope = WorkerWriteScope(ids=frozenset({"PLR01"}), labels=frozenset({"PLR"}))
    ss.grant_caller("worker", can_pin_map=True, can_mutate=True, write_scope=scope)
    gate = MutateGate(ss)
    gate.apply([_PLR], mode="add", caller="worker", require_bind=True)
    with pytest.raises(MemNetError) as ei:
        gate.apply([_PLR2], mode="add", caller="worker", require_bind=True)
    assert ei.value.code == "acl_scope"
    assert ss.store.get("PLR02") is None


def test_write_scope_label_allow(memnet_temp, schema_file):
    ss = _open(schema_file)
    scope = WorkerWriteScope(labels=frozenset({"PLR"}))
    ss.grant_caller("worker", can_pin_map=True, can_mutate=True, write_scope=scope)
    gate = MutateGate(ss)
    gate.apply([_PLR], mode="add", caller="worker")
    gate.apply([_PLR2], mode="add", caller="worker")
    assert ss.store.get("PLR02") is not None


def test_bind_mismatch_hard_reject(memnet_temp, schema_file):
    ss = _open(schema_file)
    ss.grant_caller("owner", can_pin_map=True, can_mutate=True)
    ss.set_bind("mission_a", "lease_1")
    gate = MutateGate(ss)
    with pytest.raises(MemNetError) as ei:
        gate.apply(
            [_PLR],
            mode="add",
            caller="owner",
            mission_id="mission_b",
            lease="lease_1",
            require_bind=True,
        )
    assert ei.value.code == "acl_bind"
    assert ss.store.get("PLR01") is None


def test_bind_match_allows(memnet_temp, schema_file):
    ss = _open(schema_file)
    ss.grant_caller("owner", can_pin_map=True, can_mutate=True)
    ss.set_bind("mission_a", "lease_1")
    gate = MutateGate(ss)
    gate.apply(
        [_PLR],
        mode="add",
        caller="owner",
        mission_id="mission_a",
        lease="lease_1",
        require_bind=True,
    )
    assert ss.store.get("PLR01") is not None


def test_in_process_skip_bind(memnet_temp, schema_file, monkeypatch):
    monkeypatch.setenv("MEMNET_SERVE_INTERNAL", "1")
    ss = _open(schema_file)
    ss.grant_caller("owner", can_pin_map=True, can_mutate=True)
    ss.set_bind("mission_a", "lease_1")
    gate = MutateGate(ss)
    # require_bind=False → documented in-process skip
    gate.apply(
        [_PLR],
        mode="add",
        caller="owner",
        mission_id="wrong",
        lease="wrong",
        require_bind=False,
    )
    assert ss.store.get("PLR01") is not None


def test_investor_api_style_requires_who_and_bind(memnet_temp, schema_file):
    """InvestorApi-style: require_bind=True enforces who + bind."""
    ss = _open(schema_file)
    ss.grant_caller("api", can_pin_map=True, can_mutate=True)
    ss.set_bind("m1", "l1")
    gate = MutateGate(ss)
    with pytest.raises(MemNetError) as ei:
        gate.apply([_PLR], mode="add", caller="api", require_bind=True)
    assert ei.value.code == "acl_bind"
    gate.apply(
        [_PLR],
        mode="add",
        caller="api",
        mission_id="m1",
        lease="l1",
        require_bind=True,
    )
    assert ss.store.get("PLR01") is not None


def test_cli_acl_grant_and_deny(memnet_temp, schema_file):
    r1 = runner.invoke(app, ["session", "open", "--map-file", str(schema_file)])
    assert r1.exit_code == 0, r1.stderr
    sid = r1.stdout.strip().split("|")[0].replace("@SESSION: ", "")

    g = runner.invoke(
        app,
        [
            "session",
            "acl-grant",
            "--caller",
            "owner",
            "--session",
            sid,
        ],
    )
    assert g.exit_code == 0, g.stderr

    denied = runner.invoke(
        app,
        ["add", "--stdin", "--session", sid, "--caller", "intruder"],
        input=_PLR + "\n",
    )
    assert denied.exit_code != 0
    assert "acl_denied" in denied.stderr

    ok = runner.invoke(
        app,
        ["add", "--stdin", "--session", sid, "--caller", "owner"],
        input=_PLR + "\n",
    )
    assert ok.exit_code == 0, ok.stderr

    pin = runner.invoke(
        app,
        ["query", "pin-map", "--anchor", "PLR01", "--session", sid, "--caller", "owner"],
    )
    assert pin.exit_code == 0, pin.stderr
    assert "PLR01" in pin.stdout


def test_acl_off_by_default_keeps_legacy_green(memnet_temp, schema_file):
    ss = _open(schema_file)
    assert ss.acl.enabled is False
    result = MutateGate(ss).apply([_PLR], mode="add")
    assert result.records
    text = PinMapComposer(ss).compose(anchor="PLR01")[1]
    assert "PLR01" in text


def test_check_write_scope_unit():
    from memnet.acl import SessionAcl

    acl = SessionAcl()
    acl.grant(
        "w",
        write_scope=WorkerWriteScope(ids=frozenset({"A"})),
    )
    rec_ok = Record(tag="PLR", fields={"id": "A"})
    rec_bad = Record(tag="PLR", fields={"id": "B"})
    check_write_scope(acl, caller="w", records=[rec_ok])
    with pytest.raises(MemNetError) as ei:
        check_write_scope(acl, caller="w", records=[rec_bad])
    assert ei.value.code == "acl_scope"


def test_check_bind_unit():
    from memnet.acl import SessionAcl

    acl = SessionAcl()
    acl.grant("o")
    acl.set_bind("m", "l")
    check_bind(acl, mission_id="m", lease="l", require=True)
    with pytest.raises(MemNetError):
        check_bind(acl, mission_id="x", lease="l", require=True)


def test_session_id_not_in_acl_error_examples(memnet_temp, schema_file):
    ss = _open(schema_file)
    ss.grant_caller("owner")
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply([_PLR], mode="add", caller=None, require_bind=True)
    assert ss.session_id not in str(ei.value)
    assert ss.session_id not in (ei.value.example or "")
    assert ss.session_id not in ei.value.message
