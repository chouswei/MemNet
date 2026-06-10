"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from memnet.config import examples_dir
from memnet.session import purge_expired, reset_registry, set_now_override


@pytest.fixture
def memnet_temp(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MEMNET_TEST_INLINE", "1")
    monkeypatch.delenv("MEMNET_SESSION", raising=False)
    reset_registry()
    purge_expired()
    yield
    set_now_override(None)
    reset_registry()
    purge_expired()


@pytest.fixture
def schema_file():
    return examples_dir() / "schema.example.txt"


@pytest.fixture
def workflow_file():
    return examples_dir() / "workflow.example.txt"
