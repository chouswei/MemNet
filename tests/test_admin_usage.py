"""Admin serve usage report (MN-REQ-06.11): credential, alias, counters."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from memnet.admin_usage import (
    ERR_DENIED,
    ERR_UNCONFIGURED,
    reset_pressure,
    session_alias,
)
from memnet.cli import app
from memnet.config import Caps
from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.pin_map_composer import PinMapComposer
from memnet.session import open_session

runner = CliRunner()
_MAP = ["SCHEMA CST ; fields=id name role ports law recycle"]


def _report(token: str | None = None) -> tuple[int, str, str]:
    args = ["admin", "usage-report"]
    if token is not None:
        args.extend(["--token", token])
    result = runner.invoke(app, args)
    return result.exit_code, result.stdout, result.stderr


def test_unconfigured_refuses_without_report_body(memnet_temp, monkeypatch):
    monkeypatch.delenv("MEMNET_ADMIN_TOKEN", raising=False)
    code, out, err = _report("any-token")
    assert code == 2
    assert out == ""
    assert f"@ERR: {ERR_UNCONFIGURED}|" in err
    assert "MEMNET_ADMIN_TOKEN" in err
    assert "ok" not in out


def test_wrong_token_denied(memnet_temp, monkeypatch):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", "secret-token")
    code, out, err = _report("wrong")
    assert code == 2
    assert out == ""
    assert f"@ERR: {ERR_DENIED}|" in err


def test_missing_token_denied_when_configured(memnet_temp, monkeypatch):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", "secret-token")
    code, out, err = _report(None)
    assert code == 2
    assert out == ""
    assert f"@ERR: {ERR_DENIED}|" in err


def test_alias_not_real_session_id(memnet_temp, monkeypatch, schema_file):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", "secret-token")
    ss = open_session(map_file=str(schema_file), product="inkmirage")
    sid = ss.session_id
    assert sid.startswith("mn_")
    expires_before = ss.meta.expires_at
    code, out, err = _report("secret-token")
    assert code == 0, err
    assert sid not in out
    assert sid not in err
    assert "mn_" not in out
    report = json.loads(out)
    assert report["ok"] is True
    assert report["sessions"]["live"] == 1
    assert report["sessions"]["max"] == Caps().max_sessions
    rows = report["session_rows"]
    assert len(rows) == 1
    alias = rows[0]["alias"]
    assert alias == session_alias(sid, token="secret-token")
    assert alias.startswith("s_")
    assert "mn_" not in alias
    assert rows[0]["product"] == "inkmirage"
    assert isinstance(rows[0]["rows"], int)
    assert rows[0]["rows_max"] == Caps().max_rows
    assert rows[0]["relations_max"] == Caps().max_relations
    assert rows[0]["ttl_left_s"] >= 0
    assert isinstance(rows[0]["save_on_expire_armed"], bool)
    assert ss.meta.expires_at == expires_before
    assert "process" in report
    assert report["process"]["version"]
    assert "max_sessions" in report["process"]["caps"]
    assert isinstance(report["unavailable"], list)


def test_row_cap_increments_limit_exceeded_counter(memnet_temp, monkeypatch):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", "secret-token")
    monkeypatch.setenv("MEMNET_MAX_ROWS", "2")
    reset_pressure()
    ss = open_session(map_lines=list(_MAP), caps=Caps())
    gate = MutateGate(ss)
    gate.apply(
        ["CREATE (:CST {id: 'CST_A', name: 'a', role: 'person'})"],
        mode="add",
        allow_new_relation=True,
    )
    with pytest.raises(MemNetError) as exc:
        gate.apply(
            [
                "CREATE (:CST {id: 'CST_B', name: 'b', role: 'person'})",
                "CREATE (:CST {id: 'CST_C', name: 'c', role: 'person'})",
            ],
            mode="add",
            allow_new_relation=True,
        )
    assert exc.value.code == "limit_exceeded"
    assert exc.value.message.startswith("rows|")
    code, out, err = _report("secret-token")
    assert code == 0, err
    report = json.loads(out)
    assert report["pressure"]["limit_exceeded"]["rows"] >= 1
    assert "mn_" not in out


def test_truncation_increments_pressure(memnet_temp, monkeypatch):
    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", "secret-token")
    reset_pressure()
    ss = open_session(map_lines=list(_MAP))
    lines = ["CREATE (:CST {id: 'CST_Hub', name: 'hub', role: 'person'})"]
    for i in range(8):
        lid = f"CST_L{i:02d}"
        lines.append(f"CREATE (:CST {{id: '{lid}', name: 'leaf{i}', role: 'person'}})")
        lines.append(
            f"MATCH (a {{id: '{lid}'}}), (b {{id: 'CST_Hub'}})\n"
            f"CREATE (a)-[:member_of {{id: 'E_m{i:02d}'}}]->(b)"
        )
    MutateGate(ss).apply(lines, mode="add", allow_new_relation=True)
    _rows, text = PinMapComposer(ss).compose(anchor="CST_Hub", depth=1, max_rows=4)
    assert "## Truncation" in text
    code, out, err = _report("secret-token")
    assert code == 0, err
    report = json.loads(out)
    assert report["pressure"]["truncation"]["max_rows"] >= 1
    assert "mn_" not in out


def test_serve_envelope_admin_usage_entry(memnet_temp, monkeypatch, schema_file):
    import socket
    import threading
    import time

    from memnet.serve import probe, run_serve, send_command
    from memnet.session import reset_registry

    monkeypatch.setenv("MEMNET_ADMIN_TOKEN", "secret-token")
    monkeypatch.delenv("MEMNET_TEST_INLINE", raising=False)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    monkeypatch.setenv("MEMNET_SERVE_PORT", str(port))
    monkeypatch.setenv("MEMNET_SERVE_HOST", "127.0.0.1")
    thread = threading.Thread(
        target=run_serve, kwargs={"host": "127.0.0.1", "port": port}, daemon=True
    )
    thread.start()
    for _ in range(100):
        if probe(host="127.0.0.1", port=port):
            break
        time.sleep(0.05)
    else:
        pytest.fail("memnet serve did not start")
    open_session(map_file=str(schema_file), product="gateapp")
    env = send_command(
        [],
        admin_usage=True,
        admin_token="secret-token",
        host="127.0.0.1",
        port=port,
    )
    assert env["exit_code"] == 0, env["stderr"]
    assert "mn_" not in env["stdout"]
    report = json.loads(env["stdout"])
    assert report["ok"] is True
    assert report["session_rows"][0]["product"] == "gateapp"
    denied = send_command([], admin_usage=True, admin_token="nope", host="127.0.0.1", port=port)
    assert denied["exit_code"] == 2
    assert denied["stdout"] == ""
    assert "admin_denied" in denied["stderr"]
    reset_registry()


def test_mcp_does_not_list_admin_usage(monkeypatch):
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    import asyncio

    from memnet_mcp.server import mcp

    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "admin_usage_report" not in names
    assert "usage_report" not in names
    assert "admin_usage" not in names
    open_tool = next(t for t in asyncio.run(mcp.list_tools()) if t.name == "session_open")
    props = (open_tool.inputSchema or {}).get("properties") or {}
    assert "product" not in props
