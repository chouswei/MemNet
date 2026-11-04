"""Mixed versions during an upgrade, real processes both ways (MN-REQ-06.14).

- a 0.20.4 ``memnet`` client (no keep-alive, one connection per command) against this serve;
- this build's pooled client (memnet.serve_pool, keep-alive) against a 0.20.4 serve that
  closes the connection after every reply, and against a serve that goes away mid-sequence.
"""

from __future__ import annotations

import signal

import pytest

from memnet.serve_pool import POOL
from old_build_lib import Serve, new_build

TSK = "CREATE (:TSK {id: 'TSK_%s', goal: 'goal-%s', status: 'open'})\n"


@pytest.fixture
def serve(memnet_temp, monkeypatch, tmp_path, schema_file):
    monkeypatch.delenv("MEMNET_SERVE_KEEPALIVE", raising=False)
    POOL.close_all()
    handle = Serve(tmp_path, schema_file)
    yield handle
    POOL.close_all()
    handle.kill_any()


def _idle(serve: Serve) -> int:
    return len(POOL._idle.get(("127.0.0.1", serve.port), []))


def _pooled_sequence(serve: Serve, tag: str) -> str:
    """Session open, mutate, query through the pooled client; returns the session id."""
    sid = serve.open()
    serve.mutate(sid, TSK % (tag, tag))
    assert any(f"goal-{tag}" in line for line in serve.find(sid))
    return sid


def test_old_client_against_new_serve(serve, old_build, tmp_path, schema_file):
    serve.start(new_build(tmp_path))
    opened = serve.client(
        old_build, ["session", "open", "--map-file", str(schema_file), "--ttl", "30"]
    )
    assert opened.returncode == 0, opened.stderr
    sid = opened.stdout.split("|", 1)[0].replace("@SESSION: ", "").strip()
    for tag in ("a", "b"):
        got = serve.client(
            old_build, ["mutate", "--stdin", "--session", sid], stdin=TSK % (tag, tag)
        )
        assert got.returncode == 0, got.stderr
    found = serve.client(
        old_build, ["query", "find", "--kind", "TSK", "--limit", "20", "--session", sid]
    )
    assert found.returncode == 0, found.stderr
    assert "goal-a" in found.stdout and "goal-b" in found.stdout
    # The serve still takes keep-alive clients after the old one-shot connections.
    assert any("goal-b" in line for line in serve.find(sid))
    assert sid in serve.session_ids()


def test_pooled_client_against_old_serve(serve, old_build):
    serve.start(old_build)
    sids = [_pooled_sequence(serve, tag) for tag in ("a", "b", "c")]
    assert serve.session_ids() == set(sids)
    # The old serve never answers keep_alive, so the pool parks nothing it would reuse.
    assert _idle(serve) == 0


def test_pooled_client_recovers_when_the_serve_closes(serve, tmp_path):
    new = new_build(tmp_path)
    serve.start(new)
    _pooled_sequence(serve, "a")
    assert _idle(serve) == 1, "keep-alive serve: the socket is parked for reuse"
    serve.stop(signal.SIGTERM)  # server-side close of the parked socket
    serve.start(new)
    sid = _pooled_sequence(serve, "b")
    assert sid in serve.session_ids()


def test_pooled_client_recovers_across_old_and_new_serves(serve, old_build, tmp_path):
    new = new_build(tmp_path)
    serve.start(new)
    _pooled_sequence(serve, "a")
    assert _idle(serve) == 1
    serve.stop(signal.SIGKILL)
    serve.start(old_build)  # rollback with a keep-alive socket still parked
    _pooled_sequence(serve, "b")
    assert _idle(serve) == 0
    serve.stop(signal.SIGKILL)
    serve.start(new)
    _pooled_sequence(serve, "c")
    assert _idle(serve) == 1
