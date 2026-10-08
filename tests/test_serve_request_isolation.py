"""MN-REQ-06.13 — concurrent serve commands do not share stdout or exit_code."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from memnet import __version__
from memnet.serve import probe, send_command

ROOT = Path(__file__).resolve().parents[1]
N = 12
MAP_LINE = "SCHEMA CST ; fields=id name role"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _sid(blob: str) -> str:
    for line in blob.splitlines():
        if line.startswith("@SESSION:"):
            return line.split("|", 1)[0].replace("@SESSION:", "").strip()
    raise AssertionError(blob)


def _start_serve(port: int, log_path: Path) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    for key in (
        "MEMNET_TEST_INLINE",
        "MEMNET_SERVE_INTERNAL",
        "MEMNET_SESSION",
        "MEMNET_GATEWAY_CONFIG",
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
    raise AssertionError(log_path.read_text(encoding="utf-8"))


def _stop(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _open(host: str, port: int) -> str:
    resp = send_command(
        ["session", "open", "--map", MAP_LINE],
        host=host,
        port=port,
    )
    assert resp["exit_code"] == 0, resp
    return _sid(resp.get("stdout") or "")


def _check(kind: str, marker: str, resp: dict, others: list[str]) -> None:
    blob = (resp.get("stdout") or "") + "\n" + (resp.get("stderr") or "")
    if kind == "ok":
        assert resp["exit_code"] == 0, resp
        assert marker in blob
        assert "ok=1 fail=0" in (resp.get("stderr") or "")
        assert "@ERR:" not in (resp.get("stderr") or "")
    else:
        assert resp["exit_code"] != 0, resp
        assert "@ERR:" in (resp.get("stderr") or "")
        assert "ok=1 fail=0" not in (resp.get("stderr") or "")
        assert marker not in blob
    for other in others:
        if other != marker:
            assert other not in blob, resp


def _burst(fns: list) -> tuple[list, float]:
    barrier = threading.Barrier(len(fns))
    out: list = [None] * len(fns)
    errors: list = [None] * len(fns)

    def run(i: int, fn) -> None:
        barrier.wait(timeout=30)
        try:
            out[i] = fn()
        except Exception as exc:  # noqa: BLE001 — collected for the assertion
            errors[i] = exc

    threads = [threading.Thread(target=run, args=(i, fn)) for i, fn in enumerate(fns)]
    started = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    elapsed = time.perf_counter() - started
    for i, thread in enumerate(threads):
        assert not thread.is_alive(), f"thread {i} still running"
        assert errors[i] is None, errors[i]
    return out, elapsed


def test_tcp_serve_isolates_concurrent_mutate(tmp_path: Path):
    port = _free_port()
    proc = _start_serve(port, tmp_path / "serve.log")
    try:
        sids = [_open("127.0.0.1", port) for _ in range(N)]
        markers = [f"ISO_MARK_{i:02d}_ZXQ" for i in range(N)]
        kinds = ["ok" if i % 2 == 0 else "fail" for i in range(N)]

        def call(i: int):
            if kinds[i] == "ok":
                stdin = (
                    "CREATE (:CST {id: 'N"
                    + f"{i:02d}"
                    + "', name: '"
                    + markers[i]
                    + "', role: 'r'})\n"
                )
            else:
                stdin = "CREATE (:NOPE {id: 'BAD" + f"{i:02d}" + "', name: 'x'})\n"
            return send_command(
                ["mutate", "--stdin", "--session", sids[i]],
                stdin=stdin,
                host="127.0.0.1",
                port=port,
            )

        results, _mixed_s = _burst([lambda i=i: call(i) for i in range(N)])
        for i, resp in enumerate(results):
            own = markers[i] if kinds[i] == "ok" else f"ISO_FAIL_{i:02d}_ZXQ"
            _check(kinds[i], own if kinds[i] == "ok" else "ISO_MARK_", resp, markers)

        time_sids = [_open("127.0.0.1", port) for _ in range(N)]

        def ok_call(i: int):
            return send_command(
                ["mutate", "--stdin", "--session", time_sids[i]],
                stdin=(
                    "CREATE (:CST {id: 'T"
                    + f"{i:02d}"
                    + "', name: 'TIME"
                    + f"{i:02d}"
                    + "', role: 'r'})\n"
                ),
                host="127.0.0.1",
                port=port,
            )

        _timed, parallel_s = _burst([lambda i=i: ok_call(i) for i in range(N)])
        for resp in _timed:
            assert resp["exit_code"] == 0, resp
        serial_sids = [_open("127.0.0.1", port) for _ in range(N)]
        serial_started = time.perf_counter()
        for i, sid in enumerate(serial_sids):
            resp = send_command(
                ["mutate", "--stdin", "--session", sid],
                stdin=(
                    "CREATE (:CST {id: 'S"
                    + f"{i:02d}"
                    + "', name: 'SER"
                    + f"{i:02d}"
                    + "', role: 'r'})\n"
                ),
                host="127.0.0.1",
                port=port,
            )
            assert resp["exit_code"] == 0, resp
        serial_s = time.perf_counter() - serial_started
        note = (
            f"tcp parallel_s={parallel_s:.4f} serial_s={serial_s:.4f} "
            f"ratio={parallel_s / serial_s if serial_s else 0:.3f}\n"
        )
        path = Path("/tmp/memnet-isolation-throughput.txt")
        path.write_text(note, encoding="utf-8")
        art = Path("/opt/cursor/artifacts")
        if art.is_dir():
            (art / "isolation-throughput.txt").write_text(note, encoding="utf-8")
    finally:
        _stop(proc)


def _post(url: str, token: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))


def test_product_gateway_isolates_concurrent_mutate(tmp_path: Path):
    serve_port = _free_port()
    gw_port = _free_port()
    serve = _start_serve(serve_port, tmp_path / "serve.log")
    token = "endleaf-secret"
    cfg = tmp_path / "gateway.json"
    state = tmp_path / "owners.json"
    cfg.write_text(
        json.dumps(
            {
                "bind": "127.0.0.1",
                "port": gw_port,
                "path": "/gateway",
                "body_max_bytes": 4194304,
                "state_path": str(state),
                "version_cache_s": 0,
                "backend_timeout_s": 20,
                "admin": {"sha256": _sha("admin-secret")},
                "backends": {"pi-endleaf": {"host": "127.0.0.1", "port": serve_port}},
                "products": {
                    "endleaf": {
                        "backends": ["pi-endleaf"],
                        "houses": {"syson": "pi-endleaf"},
                        "pinned_version": __version__,
                        "credentials": [
                            {"id": "endleaf-1", "sha256": _sha(token), "revoked": False}
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    for key in ("MEMNET_TEST_INLINE", "MEMNET_SERVE_INTERNAL", "MEMNET_SESSION"):
        env.pop(key, None)
    env["MEMNET_GATEWAY_CONFIG"] = str(cfg)
    log_path = tmp_path / "gateway.log"
    log = log_path.open("w", encoding="utf-8")
    gw = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "memnet_mcp.server",
            "--transport",
            "gateway",
            "--host",
            "127.0.0.1",
            "--port",
            str(gw_port),
        ],
        env=env,
        cwd=str(ROOT),
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    log.close()
    url = f"http://127.0.0.1:{gw_port}/gateway"
    try:
        deadline = time.time() + 20
        while time.time() < deadline:
            if gw.poll() is not None:
                raise AssertionError(log_path.read_text(encoding="utf-8"))
            try:
                ready = _post(url, token, {"args": ["version"], "namespace": "endleaf"})
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(0.05)
                continue
            if ready.get("exit_code") == 0 and "@VER:" in (ready.get("stdout") or ""):
                break
            time.sleep(0.05)
        else:
            raise AssertionError(log_path.read_text(encoding="utf-8"))

        def open_one() -> str:
            body = _post(
                url,
                token,
                {
                    "args": ["session", "open", "--map", MAP_LINE],
                    "namespace": "endleaf",
                    "backend": "pi-endleaf",
                },
            )
            assert body["exit_code"] == 0, body
            return _sid(body.get("stdout") or "")

        sids = [open_one() for _ in range(N)]
        markers = [f"GW_MARK_{i:02d}_ZXQ" for i in range(N)]
        kinds = ["ok" if i % 2 == 0 else "fail" for i in range(N)]

        def call(i: int) -> dict:
            if kinds[i] == "ok":
                stdin = (
                    "CREATE (:CST {id: 'G"
                    + f"{i:02d}"
                    + "', name: '"
                    + markers[i]
                    + "', role: 'r'})\n"
                )
            else:
                stdin = "CREATE (:NOPE {id: 'BAD" + f"{i:02d}" + "', name: 'x'})\n"
            return _post(
                url,
                token,
                {
                    "args": ["mutate", "--stdin", "--session", sids[i]],
                    "stdin": stdin,
                    "session": sids[i],
                    "namespace": "endleaf",
                },
            )

        results, _elapsed = _burst([lambda i=i: call(i) for i in range(N)])
        for i, resp in enumerate(results):
            _check(kinds[i], markers[i] if kinds[i] == "ok" else "GW_MARK_", resp, markers)
    finally:
        _stop(gw)
        _stop(serve)
