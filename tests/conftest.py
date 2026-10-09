"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from memnet.config import examples_dir
from memnet.session import purge_expired, reset_registry, set_now_override


@pytest.fixture(autouse=True)
def _upgrade_retry_off(monkeypatch: pytest.MonkeyPatch):
    """Production default is a 30s upgrade retry. Tests opt in."""
    monkeypatch.setenv("MEMNET_UPGRADE_RETRY_S", "0")


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


@pytest.fixture
def schema_file():
    return examples_dir() / "schema.example.txt"


@pytest.fixture
def workflow_file():
    return examples_dir() / "workflow.example.txt"
