"""Product gateway: two real serve processes, plus routing unit checks."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from memnet.serve import probe, send_command
from memnet_mcp.client import _transport, run_memnet
from memnet_mcp.product_gateway import (
    GatewayBindError,
    ProductGateway,
    validate_gateway_bind,
)
from memnet_mcp.server import _parse_args

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "parts" / "common" / "memnet" / "memnet" / "examples" / "schema.example.txt"
ENDLEAF = "endleaf-secret"
ATELIER = "atelier-secret"
ADMIN = "admin-secret"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _config(
    path: Path,
    state: Path,
    port_a: int,
    port_b: int,
    *,
    pin: str = "0.19.18",
    body_max: int = 4 * 1024 * 1024,
) -> None:
    data = {
        "bind": "127.0.0.1",
        "port": 0,
        "path": "/gateway",
        "body_max_bytes": body_max,
        "state_path": str(state),
        "version_cache_s": 0,
        "backend_timeout_s": 10,
        "admin": {"sha256": _sha(ADMIN)},
        "backends": {
            "a": {"host": "127.0.0.1", "port": port_a},
            "b": {"host": "127.0.0.1", "port": port_b},
        },
        "products": {
            "endleaf": {
                "backends": ["a", "b"],
                "houses": {"syson": "a"},
                "pinned_version": pin,
                "credentials": [
                    {"id": "endleaf-1", "sha256": _sha(ENDLEAF), "revoked": False},
                    {"id": "endleaf-old", "sha256": _sha("endleaf-old"), "revoked": True},
                ],
            },
            "atelier": {
                "backends": ["b"],
                "houses": {},
                "pinned_version": "0.19.18",
                "credentials": [
                    {"id": "atelier-1", "sha256": _sha(ATELIER), "revoked": False},
                ],
            },
        },
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _start_serve(port: int, log_path: Path) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    for key in (
        "MEMNET_TEST_INLINE",
        "MEMNET_SERVE_INTERNAL",
        "MEMNET_SESSION",
        "MEMNET_GATEWAY_CONFIG",
        "MEMNET_GATEWAY_ALLOW_PUBLIC",
    ):
        env.pop(key, None)
    env["MEMNET_SERVE_HOST"] = "127.0.0.1"
    env["MEMNET_SERVE_PORT"] = str(port)
    log = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "memnet", "serve", "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        cwd=str(ROOT),
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    log.close()
    deadline = time.time() + 20
    while time.time() < deadline:
        if proc.poll() is not None:
            raise AssertionError(log_path.read_text(encoding="utf-8"))
        if probe(host="127.0.0.1", port=port):
            return proc
        time.sleep(0.05)
    proc.terminate()
    raise AssertionError("memnet serve did not start:\n" + log_path.read_text(encoding="utf-8"))


def _stop(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _post(url: str, token: str | None, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _sid(body: dict) -> str:
    for line in (body.get("stdout") or "").splitlines():
        if line.startswith("@SESSION:"):
            return line.split(":", 1)[1].strip().split("|", 1)[0].strip()
    raise AssertionError(body)


def _live_sids(port: int) -> set[str]:
    raw = send_command(["session", "list"], host="127.0.0.1", port=port, timeout=5)
    found = set()
    for line in (raw.get("stdout") or "").splitlines():
        if line.startswith("@SESSION:"):
            found.add(line.split(":", 1)[1].strip().split("|", 1)[0].strip())
    return found


def test_bind_is_loopback_or_tailnet(monkeypatch: pytest.MonkeyPatch) -> None:
    validate_gateway_bind("127.0.0.1")
    validate_gateway_bind("localhost")
    validate_gateway_bind("100.118.79.40")
    with pytest.raises(GatewayBindError):
        validate_gateway_bind("0.0.0.0")
    with pytest.raises(GatewayBindError):
        validate_gateway_bind("8.8.8.8")
    monkeypatch.setenv("MEMNET_GATEWAY_ALLOW_PUBLIC", "1")
    validate_gateway_bind("0.0.0.0")


def test_stdio_unchanged_when_registry_env_is_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MEMNET_GATEWAY_CONFIG", str(tmp_path / "gateway.json"))
    monkeypatch.delenv("MEMNET_MCP_TRANSPORT", raising=False)
    assert _transport() == "inprocess"
    args = _parse_args([])
    assert args.transport == "stdio"
    assert "gateway" in _parse_args(["--transport", "gateway"]).transport
    resp = run_memnet(["version"])
    assert resp.exit_code == 0
    assert "0.19.18" in resp.stdout


def test_forward_keeps_args_and_stdin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[dict] = []

    def fake_probe(host: str | None = None, port: int | None = None) -> bool:
        del host, port
        return True

    def fake_send(
        args, stdin=None, host=None, port=None, timeout=None, admin_token=None, admin_usage=False
    ):
        calls.append(
            {
                "args": list(args),
                "stdin": stdin,
                "host": host,
                "port": port,
                "admin_token": admin_token,
                "admin_usage": admin_usage,
            }
        )
        if args == ["version"]:
            return {"exit_code": 0, "stdout": "@VER: memnet|0.19.18\n", "stderr": ""}
        return {"exit_code": 0, "stdout": "@SESSION: mn_new|soon|60\n", "stderr": ""}

    monkeypatch.setattr("memnet_mcp.product_gateway.probe", fake_probe)
    monkeypatch.setattr("memnet_mcp.product_gateway.send_command", fake_send)
    cfg = tmp_path / "gw.json"
    state = tmp_path / "owners.json"
    _config(cfg, state, 1, 2)
    gw = ProductGateway.load(str(cfg))
    gql = "MATCH (n {id: 'TSK_gw'}) SET n.status = 'settled'\n"
    opened = gw.handle(
        method="POST",
        path="/gateway",
        authorization=f"Bearer {ENDLEAF}",
        body=json.dumps(
            {
                "args": ["session", "open", "--map-file", "map.txt"],
                "house": "syson",
                "namespace": "endleaf",
            }
        ).encode(),
    )
    assert opened.exit_code == 0
    assert calls[0]["args"] == ["version"]
    assert calls[1]["args"] == ["session", "open", "--map-file", "map.txt"]
    assert calls[1]["stdin"] is None
    assert calls[1]["admin_token"] is None
    assert calls[1]["host"] == "127.0.0.1"
    assert calls[1]["port"] == 1
    mutated = gw.handle(
        method="POST",
        path="/gateway",
        authorization=f"Bearer {ENDLEAF}",
        body=json.dumps(
            {
                "args": ["mutate", "--stdin", "--session", "mn_new"],
                "stdin": gql,
                "session": "mn_new",
            }
        ).encode(),
    )
    assert mutated.exit_code == 0
    assert calls[-1]["args"] == ["mutate", "--stdin", "--session", "mn_new"]
    assert calls[-1]["stdin"] == gql
    assert "namespace" not in calls[-1]


def test_two_real_serves_route_isolate_and_pass_through(tmp_path: Path) -> None:
    port_a = _free_port()
    port_b = _free_port()
    serve_a = _start_serve(port_a, tmp_path / "serve-a.log")
    serve_b = _start_serve(port_b, tmp_path / "serve-b.log")
    cfg = tmp_path / "gw.json"
    state = tmp_path / "owners.json"
    _config(cfg, state, port_a, port_b)
    gw = ProductGateway.load(str(cfg))
    gw.start()
    url = f"http://127.0.0.1:{gw.bound_port}/gateway"
    try:
        status, denied = _post(url, None, {"args": ["session", "list"]})
        assert status == 401
        assert denied["stderr"] == "@ERR: gateway_auth|bearer required\n"
        status, revoked = _post(url, "endleaf-old", {"args": ["session", "list"]})
        assert status == 401
        assert "gateway_auth" in revoked["stderr"]

        before_a = _live_sids(port_a)
        mismatch = ProductGateway.load(str(cfg))
        mismatch.products["endleaf"].pinned_version = "9.9.9"
        bad_ver = mismatch.handle(
            method="POST",
            path="/gateway",
            authorization=f"Bearer {ENDLEAF}",
            body=json.dumps(
                {"args": ["session", "open", "--map-file", str(SCHEMA)], "namespace": "endleaf"}
            ).encode(),
        )
        assert bad_ver.http_status == 409
        assert bad_ver.stderr.startswith("@ERR: gateway_backend_version_mismatch|")
        assert _live_sids(port_a) == before_a

        status, opened = _post(
            url,
            ENDLEAF,
            {
                "args": ["session", "open", "--map-file", str(SCHEMA)],
                "house": "syson",
                "namespace": "endleaf",
            },
        )
        assert status == 200, opened
        assert opened["exit_code"] == 0, opened
        sid_a = _sid(opened)
        assert sid_a in _live_sids(port_a)
        assert sid_a not in _live_sids(port_b)

        snap = tmp_path / "endleaf.snap"
        status, saved = _post(
            url,
            ENDLEAF,
            {
                "args": ["session", "save", "--file", str(snap), "--session", sid_a],
                "session": sid_a,
            },
        )
        assert status == 200 and saved["exit_code"] == 0, saved
        assert snap.is_file()
        status, closed_first = _post(
            url, ENDLEAF, {"args": ["session", "close", sid_a], "session": sid_a}
        )
        assert closed_first["exit_code"] == 0, closed_first
        assert sid_a not in _live_sids(port_a)
        status, loaded = _post(
            url,
            ENDLEAF,
            {
                "args": ["session", "load", "--file", str(snap), "--keep-id"],
                "house": "syson",
            },
        )
        assert loaded["exit_code"] == 0, loaded
        assert sid_a in (loaded.get("stdout") or "")
        assert sid_a in _live_sids(port_a)

        set_gql = "MATCH (n {id: 'TSK_gw'}) SET n.status = 'settled'\n"
        create = (
            "CREATE (:TSK {id: 'TSK_gw', goal: 'gateway', status: 'open'})\n"
            "CREATE (:TSK {id: 'TSK_gw2', goal: 'other', status: 'open'})\n"
        )
        status, created = _post(
            url,
            ENDLEAF,
            {"args": ["mutate", "--stdin", "--session", sid_a], "stdin": create, "session": sid_a},
        )
        assert created["exit_code"] == 0, created
        status, settled = _post(
            url,
            ENDLEAF,
            {"args": ["mutate", "--stdin", "--session", sid_a], "stdin": set_gql, "session": sid_a},
        )
        assert settled["exit_code"] == 0, settled
        edge = (
            "MATCH (a {id: 'TSK_gw'}), (b {id: 'TSK_gw2'}) CREATE (a)-[:owns {id: 'E_gw'}]->(b)\n"
        )
        status, linked = _post(
            url,
            ENDLEAF,
            {"args": ["mutate", "--stdin", "--session", sid_a], "stdin": edge, "session": sid_a},
        )
        assert linked["exit_code"] == 0, linked
        delete = "MATCH (n WHERE true)-[r {id: 'E_gw'}]->() DELETE r\n"
        status, dropped = _post(
            url,
            ENDLEAF,
            {"args": ["mutate", "--stdin", "--session", sid_a], "stdin": delete, "session": sid_a},
        )
        assert dropped["exit_code"] == 0, dropped

        missing = "MATCH (n {id: 'MISSING_GW'}) SET n.status = 'nope'\n"
        miss_args = ["mutate", "--stdin", "--session", sid_a]
        status, via_gw = _post(
            url, ENDLEAF, {"args": miss_args, "stdin": missing, "session": sid_a}
        )
        direct = send_command(miss_args, stdin=missing, host="127.0.0.1", port=port_a, timeout=10)
        assert via_gw["exit_code"] == direct["exit_code"]
        assert via_gw["stdout"] == (direct.get("stdout") or "")
        assert via_gw["stderr"] == (direct.get("stderr") or "")
        assert "@ERR:" in via_gw["stderr"]
        assert "gateway_" not in via_gw["stderr"]

        wide_args = ["query", "pin-map", "--max-rows", "10000", "--session", sid_a]
        status, wide = _post(url, ENDLEAF, {"args": wide_args, "session": sid_a})
        wide_direct = send_command(wide_args, host="127.0.0.1", port=port_a, timeout=10)
        assert wide["exit_code"] == wide_direct["exit_code"]
        assert wide["stdout"] == (wide_direct.get("stdout") or "")
        assert wide["stderr"] == (wide_direct.get("stderr") or "")

        status, atelier_open = _post(
            url,
            ATELIER,
            {"args": ["session", "open", "--map-file", str(SCHEMA)], "namespace": "atelier"},
        )
        assert atelier_open["exit_code"] == 0, atelier_open
        sid_b = _sid(atelier_open)
        assert sid_b in _live_sids(port_b)
        assert sid_b not in _live_sids(port_a)

        status, endleaf_list = _post(
            url, ENDLEAF, {"args": ["session", "list"], "namespace": "endleaf"}
        )
        status, atelier_list = _post(
            url, ATELIER, {"args": ["session", "list"], "namespace": "atelier"}
        )
        assert sid_a in endleaf_list["stdout"]
        assert sid_b not in endleaf_list["stdout"]
        assert sid_b in atelier_list["stdout"]
        assert sid_a not in atelier_list["stdout"]

        status, foreign = _post(
            url,
            ATELIER,
            {
                "args": ["mutate", "--stdin", "--session", sid_a],
                "stdin": set_gql,
                "session": sid_a,
            },
        )
        assert status == 403
        assert foreign["stderr"] == "@ERR: gateway_forbidden_session|not owned by this product\n"
        assert sid_a in _live_sids(port_a)

        counts_req = urllib.request.Request(
            f"http://127.0.0.1:{gw.bound_port}/gateway/admin/counts",
            method="GET",
            headers={"Authorization": f"Bearer {ADMIN}"},
        )
        with urllib.request.urlopen(counts_req, timeout=10) as resp:
            counts_body = json.loads(resp.read().decode("utf-8"))
        rendered = json.dumps(counts_body)
        assert "mn_" not in rendered
        assert sid_a not in rendered
        counts = json.loads(counts_body["stdout"])
        assert counts["products"]["endleaf"]["requests"] > 0
        assert "sessions" not in counts["products"]["endleaf"]

        _stop(serve_a)
        serve_a = None
        deadline = time.time() + 5
        while time.time() < deadline and probe(host="127.0.0.1", port=port_a):
            time.sleep(0.05)
        status, down = _post(
            url,
            ENDLEAF,
            {"args": ["mutate", "--stdin", "--session", sid_a], "stdin": set_gql, "session": sid_a},
        )
        assert status == 502
        assert down["stderr"].startswith("@ERR: gateway_backend_unreachable|a")
        assert sid_a not in _live_sids(port_b)

        status, moved = _post(
            url,
            ENDLEAF,
            {"args": ["session", "open", "--map-file", str(SCHEMA)], "namespace": "endleaf"},
        )
        assert moved["exit_code"] == 0, moved
        sid_c = _sid(moved)
        assert sid_c != sid_a
        assert sid_c in _live_sids(port_b)
        assert sid_a not in _live_sids(port_b)

        status, closed = _post(
            url, ENDLEAF, {"args": ["session", "close", sid_c], "session": sid_c}
        )
        assert closed["exit_code"] == 0, closed
        assert sid_c not in _live_sids(port_b)
        status, gone = _post(
            url,
            ENDLEAF,
            {
                "args": [
                    "session",
                    "save",
                    "--file",
                    str(tmp_path / "nope.snap"),
                    "--session",
                    sid_c,
                ]
            },
        )
        assert gone["stderr"].startswith("@ERR: gateway_forbidden_session|")
    finally:
        gw.stop()
        _stop(serve_a)
        _stop(serve_b)


def test_body_ceiling_is_the_only_gateway_size_gate(tmp_path: Path) -> None:
    cfg = tmp_path / "gw.json"
    _config(cfg, tmp_path / "owners.json", 9, 10, body_max=64)
    gw = ProductGateway.load(str(cfg))
    result = gw.handle(
        method="POST",
        path="/gateway",
        authorization=f"Bearer {ENDLEAF}",
        body=b'{"args": ["session", "list"], "stdin": "' + b"x" * 80,
    )
    assert result.http_status == 413
    assert result.stderr.startswith("@ERR: gateway_body_too_large|")
