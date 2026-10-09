"""Safe serve upgrade: drain, manifest, restore, retry, rollback (MN-REQ-06.14)."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from memnet.exceptions import MemNetError
from memnet.in_process_engine import run_argv
from memnet.registry import get_entry
from memnet.serve import probe, send_command
from memnet.session import open_session, reset_registry, utc_now
from memnet.snapshot import write_snapshot
from memnet.upgrade import (
    BLOCKED_NAME,
    MANIFEST_NAME,
    drain_gate,
    prepare_upgrade,
    reset_drain_gate,
    restore_manifest,
)
from memnet.upgrade_retry import call_with_upgrade_retry
from memnet.upgrade_run import UpgradeRunError, run_upgrade, set_pinned_version, swap_execstart

TOKEN = "test-admin-token"


def _mutate(sid: str, text: str) -> None:
    raw = run_argv(["mutate", "--stdin", "--session", sid], stdin=text)
    assert raw["exit_code"] == 0, raw["stderr"]


def _edge_poison(sid: str) -> None:
    entry = get_entry(sid)
    assert entry is not None
    for hid in entry.store.write_order:
        rec = entry.store._by_hid.get(hid)
        if rec is not None and rec.tag == "EDG":
            rec.fields["not_a_field"] = "x"
            return
    raise AssertionError("expected an edge to poison")


def test_round_trip_keeps_id_acl_ttl_and_near_cap(memnet_temp, monkeypatch, tmp_path, schema_file):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    monkeypatch.setenv("MEMNET_MAX_ROWS", "80")
    monkeypatch.setenv("MEMNET_STATE_DIR", str(tmp_path))
    plain = open_session(map_file=str(schema_file), product="gateapp")
    _mutate(plain.session_id, "CREATE (:TSK {id: 'TSK_keep', goal: 'kept-fact', status: 'open'})\n")
    acl = open_session(map_file=str(schema_file), ttl_minutes=2)
    from datetime import timedelta

    _mutate(acl.session_id, "CREATE (:TSK {id: 'TSK_acl', goal: 'bound', status: 'open'})\n")
    soon = (utc_now() + timedelta(seconds=90)).isoformat().replace("+00:00", "Z")
    acl.meta.expires_at = soon
    acl.enable_acl()
    acl.grant_caller("caller-demo", can_pin_map=True, can_mutate=False, write_scope="labels=TSK")
    acl.set_bind("mission-demo", "lease-demo")
    wide = open_session(map_file=str(schema_file))
    lines = [f"CREATE (:TSK {{id: 'TSK_{i}', goal: 'g{i}', status: 'open'}})" for i in range(70)]
    lines.append(
        "MATCH (a {id: 'TSK_0'}), (b {id: 'TSK_1'}) CREATE (a)-[:owns {id: 'E_link'}]->(b)"
    )
    _mutate(wide.session_id, "\n".join(lines) + "\n")
    wide_rows = get_entry(wide.session_id).store.row_count_non_law()
    assert wide_rows >= 71
    assert wide_rows >= int(0.85 * 80)
    want = {
        plain.session_id: {"expires": plain.meta.expires_at, "product": "gateapp"},
        acl.session_id: {"expires": soon},
        wide.session_id: {"rows": wide_rows},
    }
    result = prepare_upgrade(TOKEN, directory=tmp_path)
    assert result.ready_to_stop is True
    assert result.unsaved == []
    assert (tmp_path / MANIFEST_NAME).is_file()
    reset_registry()
    reset_drain_gate()
    report = restore_manifest(tmp_path)
    assert report.failed == 0
    assert report.ok == 3
    assert set(report.session_ids) == set(want)
    plain_back = get_entry(plain.session_id)
    acl_back = get_entry(acl.session_id)
    wide_back = get_entry(wide.session_id)
    assert plain_back is not None and acl_back is not None and wide_back is not None
    assert plain_back.meta.expires_at == want[plain.session_id]["expires"]
    assert plain_back.meta.product == "gateapp"
    assert acl_back.meta.expires_at == soon
    assert acl_back.acl is not None and acl_back.acl.enabled is True
    assert acl_back.acl.bind is not None
    assert acl_back.acl.bind.mission_id == "mission-demo"
    assert acl_back.acl.bind.lease == "lease-demo"
    grant = acl_back.acl.callers["caller-demo"]
    assert grant.can_pin_map is True
    assert grant.can_mutate is False
    assert grant.write_scope is not None
    assert "TSK" in grant.write_scope.labels
    assert wide_back.store.row_count_non_law() == wide_rows
    snaps = list((tmp_path / "upgrade-snapshots").glob("*.snap"))
    assert len(snaps) == 3


def test_unsaveable_blocks_ready_unless_override(memnet_temp, monkeypatch, tmp_path, schema_file):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    ss = open_session(map_file=str(schema_file))
    _mutate(
        ss.session_id,
        "CREATE (:TSK {id: 'TSK_a', goal: 'a', status: 'open'})\n"
        "CREATE (:TSK {id: 'TSK_b', goal: 'b', status: 'open'})\n"
        "MATCH (a {id: 'TSK_a'}), (b {id: 'TSK_b'}) "
        "CREATE (a)-[:owns {id: 'E_bad'}]->(b)\n",
    )
    _edge_poison(ss.session_id)
    blocked = prepare_upgrade(TOKEN, directory=tmp_path)
    assert blocked.ready_to_stop is False
    assert blocked.exit_code == 2
    assert blocked.unsaved
    assert blocked.unsaved[0]["code"] == "snapshot_unsaveable"
    assert blocked.unsaved[0]["session_id"] == ss.session_id
    assert not (tmp_path / MANIFEST_NAME).exists()
    assert (tmp_path / BLOCKED_NAME).is_file()
    assert drain_gate.phase == "open"
    again = open_session(map_file=str(schema_file))
    assert again.session_id != ss.session_id
    forced = prepare_upgrade(TOKEN, allow_unsaved=True, directory=tmp_path)
    assert forced.ready_to_stop is True
    manifest = json.loads((tmp_path / MANIFEST_NAME).read_text(encoding="utf-8"))
    saved_ids = {row["session_id"] for row in manifest["sessions"]}
    assert ss.session_id not in saved_ids
    assert any(row["session_id"] == ss.session_id for row in manifest["unsaved"])


def test_corrupt_snapshot_fails_loud_and_keeps_bytes(
    memnet_temp, monkeypatch, tmp_path, schema_file
):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    ss = open_session(map_file=str(schema_file))
    _mutate(ss.session_id, "CREATE (:TSK {id: 'TSK_c', goal: 'c', status: 'open'})\n")
    assert prepare_upgrade(TOKEN, directory=tmp_path).ready_to_stop is True
    snap = next((tmp_path / "upgrade-snapshots").glob("*.snap"))
    original = snap.read_bytes()
    snap.write_bytes(original[:40] + b"XXXX" + original[44:])
    corrupt = snap.read_bytes()
    reset_registry()
    reset_drain_gate()
    report = restore_manifest(tmp_path)
    assert report.failed == 1
    assert report.ok == 0
    assert snap.read_bytes() == corrupt
    assert snap.is_file()


def test_older_patch_snapshot_loads(memnet_temp, monkeypatch, tmp_path, schema_file):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    ss = open_session(map_file=str(schema_file))
    _mutate(ss.session_id, "CREATE (:TSK {id: 'TSK_old', goal: 'legacy', status: 'open'})\n")
    entry = get_entry(ss.session_id)
    assert entry is not None
    snap_dir = tmp_path / "upgrade-snapshots"
    snap_dir.mkdir()
    path = snap_dir / "legacy.snap"
    write_snapshot(ss, path)
    assert b"upgrade-passport" not in path.read_bytes()
    import hashlib

    rows = entry.store.row_count_non_law()
    edges = sum(1 for hid in entry.store.write_order if entry.store._by_hid[hid].tag == "EDG")
    manifest = {
        "manifest_format": 1,
        "snapshot_format": 1,
        "serve_version": "0.19.19",
        "ready_to_stop": True,
        "retired": False,
        "allow_unsaved": False,
        "sessions": [
            {
                "session_id": ss.session_id,
                "file": "upgrade-snapshots/legacy.snap",
                "rows": rows,
                "edges": edges,
                "checksum_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "expires_at": entry.meta.expires_at,
                "created_at": entry.meta.created_at,
                "ttl_minutes": entry.meta.ttl_minutes,
                "house_tags": sorted(entry.tag_map.tags),
                "product": None,
                "saved": True,
            }
        ],
        "unsaved": [],
    }
    (tmp_path / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    expires = entry.meta.expires_at
    sid = ss.session_id
    before = path.read_bytes()
    reset_registry()
    report = restore_manifest(tmp_path)
    assert report.failed == 0, report.errors
    assert report.ok == 1
    back = get_entry(sid)
    assert back is not None
    assert back.meta.session_id == sid
    assert back.meta.expires_at == expires
    assert back.store.row_count_non_law() == rows
    assert path.read_bytes() == before


def test_unsupported_format_leaves_file(memnet_temp, tmp_path, schema_file):
    ss = open_session(map_file=str(schema_file))
    snap_dir = tmp_path / "upgrade-snapshots"
    snap_dir.mkdir()
    path = snap_dir / "one.snap"
    write_snapshot(ss, path)
    before = path.read_bytes()
    manifest = {
        "snapshot_format": 99,
        "ready_to_stop": True,
        "retired": False,
        "sessions": [],
    }
    (tmp_path / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    reset_registry()
    with pytest.raises(MemNetError) as exc:
        restore_manifest(tmp_path)
    assert exc.value.code == "upgrade_snapshot_format"
    assert path.read_bytes() == before


def test_drain_refuses_session_open(memnet_temp, schema_file):
    drain_gate.enter_quiesce(5)
    with pytest.raises(MemNetError) as exc:
        open_session(map_file=str(schema_file))
    assert exc.value.code == "serve_draining"
    assert "retry_after_s=5" in exc.value.message


def test_inflight_blocks_ready_until_finished():
    reset_drain_gate()
    counted, err = drain_gate.begin(["mutate", "--stdin"])
    assert counted is True and err is None
    drain_gate.enter_quiesce(5)
    _counted, refused = drain_gate.begin(["session", "open", "--map-file", "x"])
    assert refused == "serve_draining"
    assert drain_gate.wait_idle(0.05) is False
    drain_gate.end(counted)
    assert drain_gate.wait_idle(0.2) is True
    reset_drain_gate()


def test_client_retries_connection_refusal_and_draining(monkeypatch):
    monkeypatch.setenv("MEMNET_UPGRADE_RETRY_S", "2")
    state = {"n": 0}

    def flaky() -> dict:
        state["n"] += 1
        if state["n"] < 3:
            raise ConnectionRefusedError("down")
        return {"exit_code": 0, "stdout": "", "stderr": ""}

    raw = call_with_upgrade_retry(flaky)
    assert raw["exit_code"] == 0
    assert state["n"] == 3

    state["n"] = 0

    def draining() -> dict:
        state["n"] += 1
        if state["n"] < 3:
            return {
                "exit_code": 2,
                "stdout": "",
                "stderr": "@ERR: serve_draining|retry_after_s=5\n",
            }
        return {"exit_code": 0, "stdout": "ok\n", "stderr": ""}

    raw = call_with_upgrade_retry(draining)
    assert raw["stdout"] == "ok\n"
    assert state["n"] == 3


def test_client_no_retry_when_window_disabled(monkeypatch):
    monkeypatch.setenv("MEMNET_UPGRADE_RETRY_S", "0")

    def down() -> dict:
        raise ConnectionRefusedError("down")

    with pytest.raises(ConnectionRefusedError):
        call_with_upgrade_retry(down)


def test_mcp_tcp_retries_until_serve_accepts(monkeypatch):
    monkeypatch.setenv("MEMNET_UPGRADE_RETRY_S", "2")
    monkeypatch.setenv("MEMNET_MCP_TRANSPORT", "tcp")
    monkeypatch.delenv("MEMNET_TEST_INLINE", raising=False)
    calls = {"n": 0}

    def fake_probe(*_a, **_k) -> bool:
        calls["n"] += 1
        return calls["n"] >= 3

    def fake_send(*_a, **_k) -> dict:
        return {"exit_code": 0, "stdout": "@STAT: sessions|0|1024\n", "stderr": ""}

    monkeypatch.setattr("memnet_mcp.client.probe", fake_probe)
    monkeypatch.setattr("memnet_mcp.client.send_command", fake_send)
    from memnet_mcp.client import run_memnet

    resp = run_memnet(["session", "list"])
    assert resp.exit_code == 0
    assert calls["n"] >= 3


def test_rollback_restores_unit_and_pin(memnet_temp, tmp_path):
    unit = tmp_path / "memnet-serve.service"
    unit.write_text("[Service]\nExecStart=/old/venv/bin/memnet serve\n", encoding="utf-8")
    gateway = tmp_path / "gateway.json"
    gateway.write_text(
        json.dumps({"products": {"endleaf": {"pinned_version": "0.19.19", "backends": []}}}),
        encoding="utf-8",
    )
    state = tmp_path / "state"
    state.mkdir()
    calls = {"n": 0}

    def drainer() -> None:
        manifest = {
            "ready_to_stop": True,
            "retired": False,
            "snapshot_format": 1,
            "sessions": [],
            "unsaved": [],
        }
        (state / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")

    def restarter() -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            (state / "upgrade-restore.json").write_text(
                json.dumps({"ok": 0, "failed": 1, "skipped": False, "errors": []}),
                encoding="utf-8",
            )

    with pytest.raises(UpgradeRunError) as exc:
        run_upgrade(
            new_python=sys.executable,
            new_exec="/new/venv/bin/memnet serve",
            state=state,
            clients_ready=True,
            unit_path=unit,
            gateway_config=gateway,
            product="endleaf",
            drainer=drainer,
            restarter=restarter,
            verify_wait_s=1,
        )
    assert exc.value.code == "upgrade_verify"
    assert "ExecStart=/old/venv/bin/memnet serve" in unit.read_text(encoding="utf-8")
    pin = json.loads(gateway.read_text(encoding="utf-8"))
    assert pin["products"]["endleaf"]["pinned_version"] == "0.19.19"
    assert (unit.with_suffix(".service.bak")).is_file()
    assert calls["n"] == 2


def test_clients_must_be_ready_before_swap(tmp_path):
    unit = tmp_path / "memnet-serve.service"
    unit.write_text("ExecStart=/old/venv/bin/memnet serve\n", encoding="utf-8")
    with pytest.raises(UpgradeRunError) as exc:
        run_upgrade(
            new_python=sys.executable,
            new_exec="/new/venv/bin/memnet serve",
            state=tmp_path,
            clients_ready=False,
            unit_path=unit,
            drainer=lambda: None,
            restarter=lambda: None,
        )
    assert exc.value.code == "upgrade_clients"
    assert unit.read_text(encoding="utf-8").startswith("ExecStart=/old")


def test_swap_and_pin_helpers():
    swapped = swap_execstart("ExecStart=/old/bin/memnet serve\n", "/new/bin/memnet serve")
    assert swapped == "ExecStart=/new/bin/memnet serve\n"
    pinned = set_pinned_version(
        json.dumps({"products": {"endleaf": {"pinned_version": "0.19.19"}}}),
        "endleaf",
        "0.19.20",
    )
    assert json.loads(pinned)["products"]["endleaf"]["pinned_version"] == "0.19.20"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_probe(port: int, timeout_s: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if probe(host="127.0.0.1", port=port):
            return True
        time.sleep(0.05)
    return False


def test_tcp_restart_restores_same_sessions(memnet_temp, monkeypatch, tmp_path, schema_file):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", TOKEN)
    port = _free_port()
    state = tmp_path / "state"
    state.mkdir()
    log = tmp_path / "serve.log"
    env = os.environ.copy()
    env.update(
        {
            "MEMNET_ADMIN_TOKEN": TOKEN,
            "MEMNET_STATE_DIR": str(state),
            "MEMNET_SERVE_HOST": "127.0.0.1",
            "MEMNET_SERVE_PORT": str(port),
            "MEMNET_MAX_ROWS": "80",
            "MEMNET_UPGRADE_RETRY_S": "0",
        }
    )
    env.pop("MEMNET_TEST_INLINE", None)
    env.pop("MEMNET_SESSION", None)

    def start() -> subprocess.Popen[bytes]:
        handle = log.open("a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, "-m", "memnet", "serve", "--host", "127.0.0.1", "--port", str(port)],
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
        handle.close()
        assert _wait_probe(port), log.read_text(encoding="utf-8")
        return proc

    def stop(proc: subprocess.Popen[bytes]) -> None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and probe(host="127.0.0.1", port=port):
            time.sleep(0.05)

    proc = start()
    try:
        opened = send_command(
            [
                "session",
                "open",
                "--map-file",
                str(schema_file),
                "--ttl",
                "2",
                "--product",
                "gateapp",
            ],
            host="127.0.0.1",
            port=port,
        )
        assert opened["exit_code"] == 0, opened
        sid = opened["stdout"].split("|", 1)[0].replace("@SESSION: ", "").strip()
        mutated = send_command(
            ["mutate", "--stdin", "--session", sid],
            stdin="CREATE (:TSK {id: 'TSK_live', goal: 'kept-fact', status: 'open'})\n",
            host="127.0.0.1",
            port=port,
        )
        assert mutated["exit_code"] == 0, mutated
        granted = send_command(
            [
                "session",
                "acl-enable",
                "--session",
                sid,
            ],
            host="127.0.0.1",
            port=port,
        )
        assert granted["exit_code"] == 0, granted
        bound = send_command(
            [
                "session",
                "acl-bind",
                "--mission-id",
                "mission-demo",
                "--lease",
                "lease-demo",
                "--session",
                sid,
            ],
            host="127.0.0.1",
            port=port,
        )
        assert bound["exit_code"] == 0, bound
        prepared = send_command(
            ["admin", "upgrade-prepare", "--state-dir", str(state)],
            admin_token=TOKEN,
            host="127.0.0.1",
            port=port,
            timeout=30,
        )
        assert prepared["exit_code"] == 0, prepared
        assert "upgrade_prepare|ready|1" in prepared["stderr"]
        refused = send_command(
            ["session", "open", "--map-file", str(schema_file)],
            host="127.0.0.1",
            port=port,
        )
        assert "serve_draining" in refused["stderr"]
        assert "retry_after_s" in refused["stderr"]
    finally:
        stop(proc)

    proc = start()
    try:
        report = json.loads((state / "upgrade-restore.json").read_text(encoding="utf-8"))
        assert report["failed"] == 0
        assert report["ok"] == 1
        assert report["stat"] == "@STAT: upgrade_restore|ok|1|failed|0"
        assert sid in report["session_ids"]
        detail = report["details"][0]
        assert detail["acl_enabled"] is True
        assert detail["bind_mission"] == "mission-demo"
        assert detail["product"] == "gateapp"
        found = send_command(
            ["query", "find", "--kind", "TSK", "--limit", "5", "--session", sid],
            host="127.0.0.1",
            port=port,
        )
        assert found["exit_code"] == 0, found
        assert "kept-fact" in found["stdout"]
        assert (state / "upgrade-snapshots").is_dir()
        assert list((state / "upgrade-snapshots").glob("*.snap"))
    finally:
        stop(proc)


def test_upgrade_doc_has_no_session_id():
    text = (Path(__file__).resolve().parents[1] / "docs/operations/safe-upgrade.md").read_text(
        encoding="utf-8"
    )
    assert "mn_" not in text
