"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from memnet.config import examples_dir
from memnet.session import purge_expired, reset_registry, set_now_override


@pytest.fixture
def memnet_temp(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    monkeypatch.delenv("MEMNET_SESSION", raising=False)
    monkeypatch.delenv("MEMNET_ADMIN_TOKEN", raising=False)
    reset_registry()
    purge_expired()
    from memnet.admin_usage import reset_pressure

    reset_pressure()
    from memnet.upgrade import reset_drain_gate

    reset_drain_gate()
    yield
    set_now_override(None)
    reset_registry()
    purge_expired()
    reset_pressure()
    reset_drain_gate()


@pytest.fixture(autouse=True)
def _debug_session_bytes(monkeypatch: pytest.MonkeyPatch):
    """Whole suite: every session-bytes check also asserts incremental == full recount."""
    monkeypatch.setenv("MEMNET_DEBUG_SESSION_BYTES", "1")


@pytest.fixture
def schema_file():
    return examples_dir() / "schema.example.txt"


@pytest.fixture
def workflow_file():
    return examples_dir() / "workflow.example.txt"


@pytest.fixture(scope="session")
def old_build(tmp_path_factory):
    """A real 0.20.4 build in a temp venv (tests/old_build_lib.py); skips on a shallow clone."""
    from old_build_lib import build_old

    return build_old(tmp_path_factory.mktemp("old-build"))
