"""Per-request serve log: fields, no id/payload leak, queue wait, rotation, sink failure."""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

import pytest

from memnet import request_log
from memnet.serve import _Handler, _Server, send_command

SECRET_SID = "mn_SECRETSESSIONID1234567890"
SECRET_TEXT = "payload-text-that-must-not-leak"
FIELDS = {
    "received_ms",
    "finished_ms",
    "queue_wait_ms",
    "server_ms",
    "op",
    "session",
    "bytes_in",
    "bytes_out",
    "lines_in",
    "lines_out",
    "nodes_touched",
    "outcome",
    "conn_id",
    "seq",
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def served(memnet_temp, monkeypatch, tmp_path):
    log = tmp_path / "req.jsonl"
    monkeypatch.setenv("MEMNET_REQUEST_LOG", str(log))
    port = _free_port()
    server = _Server(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port, log
    finally:
        server.shutdown()
        server.server_close()


def _lines(log: Path) -> list[dict]:
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x]


def test_line_has_all_fields_and_no_leak(served):
    port, log = served
    send_command(
        ["query", "pin-map", "--session", SECRET_SID, "--cue", SECRET_TEXT],
        stdin=f"{SECRET_TEXT}\nsecond\n",
        port=port,
    )
    time.sleep(0.2)
    rec = _lines(log)[-1]
    assert set(rec) == FIELDS
    assert rec["op"] == "query pin-map"
    assert rec["session"].startswith("s_") and len(rec["session"]) == 10
    assert rec["lines_in"] == 2
    assert rec["bytes_in"] > 0 and rec["bytes_out"] > 0
    assert rec["nodes_touched"] is None
    assert rec["finished_ms"] >= rec["received_ms"]
    assert rec["conn_id"] >= 1 and rec["seq"] == 1
    raw = log.read_text(encoding="utf-8")
    assert SECRET_SID not in raw and SECRET_TEXT not in raw and "mn_" not in raw


def test_error_outcome_and_probe_not_logged(served):
    port, log = served
    socket.create_connection(("127.0.0.1", port), timeout=1).close()  # bare probe
    send_command(["no-such-command"], port=port)
    time.sleep(0.2)
    recs = _lines(log)
    assert len(recs) == 1
    assert recs[0]["outcome"] != "ok"


def test_queue_wait_measured_under_two_concurrent_requests(served, monkeypatch):
    port, log = served
    from memnet.upgrade import drain_gate

    gate = threading.Lock()
    real_begin = drain_gate.begin

    def slow_begin(argv):
        with gate:  # stands in for any serialisation point before the work starts
            time.sleep(0.3)
            return real_begin(argv)

    monkeypatch.setattr(drain_gate, "begin", slow_begin)
    threads = [
        threading.Thread(target=send_command, args=(["version"],), kwargs={"port": port})
        for _ in range(2)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    time.sleep(0.2)
    recs = _lines(log)
    assert len(recs) == 2
    waits = sorted(r["queue_wait_ms"] for r in recs)
    assert waits[0] >= 250
    assert waits[1] >= 500
    assert recs[0]["conn_id"] != recs[1]["conn_id"]


def test_rotation(memnet_temp, monkeypatch, tmp_path):
    log = tmp_path / "r.jsonl"
    monkeypatch.setenv("MEMNET_REQUEST_LOG", str(log))
    monkeypatch.setenv("MEMNET_REQUEST_LOG_MAX_BYTES", "400")
    monkeypatch.setenv("MEMNET_REQUEST_LOG_BACKUPS", "2")
    for i in range(30):
        trace = request_log.begin(i + 1)
        trace.op = "version"
        request_log.finish(trace)
    assert (tmp_path / "r.jsonl.1").exists()
    assert not (tmp_path / "r.jsonl.3").exists()
    assert log.stat().st_size <= 800


def test_zero_backups_still_rotates(memnet_temp, monkeypatch, tmp_path):
    log = tmp_path / "z.jsonl"
    monkeypatch.setenv("MEMNET_REQUEST_LOG", str(log))
    monkeypatch.setenv("MEMNET_REQUEST_LOG_MAX_BYTES", "400")
    monkeypatch.setenv("MEMNET_REQUEST_LOG_BACKUPS", "0")
    for i in range(30):
        request_log.finish(request_log.begin(i + 1))
    assert log.stat().st_size <= 800


def test_session_lock_wait_counts_as_queue_wait():
    trace = request_log.begin(1)
    request_log.mark_work_start()
    time.sleep(0.05)
    request_log.mark_lock_acquired()
    time.sleep(0.01)
    trace.t_done = time.perf_counter()
    rec = json.loads(request_log.to_line(trace))
    assert rec["queue_wait_ms"] >= 50
    request_log._current.set(None)


def test_sink_failure_is_harmless(memnet_temp, monkeypatch, tmp_path, caplog):
    bad = tmp_path / "no" / "such" / "dir" / "x.jsonl"
    monkeypatch.setenv("MEMNET_REQUEST_LOG", str(bad))
    for i in range(3):
        trace = request_log.begin(i + 1)
        request_log.finish(trace)  # must not raise
    warnings = [r for r in caplog.records if "request log" in r.getMessage()]
    assert len(warnings) <= 1


def test_off_by_default(memnet_temp, monkeypatch, tmp_path):
    monkeypatch.delenv("MEMNET_REQUEST_LOG", raising=False)
    trace = request_log.begin(1)
    request_log.finish(trace)
    assert list(tmp_path.iterdir()) == []
