"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from memnet.config import examples_dir
from memnet.session import purge_expired, reset_registry, set_now_override
from novel_mcp.catalog_schema import CatalogSchema

_REPO = Path(__file__).resolve().parents[1]


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


@pytest.fixture
def wuxia_schema() -> CatalogSchema:
    return CatalogSchema.load_json(
        _REPO / "applications/novel_cursor/catalog_specs/wuxia_jinyong.json"
    )


@pytest.fixture
def fantasy_schema() -> CatalogSchema:
    return CatalogSchema.load_json(_REPO / "tests/fixtures/catalog_schema_fantasy.json")
