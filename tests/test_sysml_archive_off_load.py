"""Honesty-c: leftover archive off ProjectMemNet load + one-page nest."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
CONFIG = ROOT / "sysml-models" / "config.yaml"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
DEPLOY = MODELS / "deploy.sysml"
ROOT_SYSML = MODELS / "root.sysml"
ARCHIVE = MODELS / "archive.sysml"
PARTS = ROOT / "parts"


def test_archive_off_config_and_root_load():
    cfg = CONFIG.read_text(encoding="utf-8")
    assert "archive.sysml" not in [
        line.split("#", 1)[0].strip().lstrip("- ").strip()
        for line in cfg.splitlines()
        if line.strip().startswith("- ")
    ]
    assert "archive.sysml is OFF this load" in cfg
    root = ROOT_SYSML.read_text(encoding="utf-8")
    assert "private import MemNetArchive" not in root
    assert "MUST NOT import MemNetArchive" in root


def test_archive_shelf_keeps_leftover_honesty():
    text = ARCHIVE.read_text(encoding="utf-8")
    assert "package MemNetArchive" in text
    for name in (
        "leftover_id_first",
        "leftover_by_id",
        "leftover_MERGE_by_id",
        "leftover_NEW_mint",
        "leftover_allocate_from_locator",
        "leftover_require_anchor",
        "leftover_empty_seed_skip",
        "leftover_ingestIsIdRule",
        "leftover_read_get",
        "leftover_AssignedIdMap",
        "TierACodec",
        "LegacyPipeImport",
    ):
        assert f"part def {name}" in text


def test_product_deploy_does_not_nest_leftover_fog():
    text = DEPLOY.read_text(encoding="utf-8")
    assert not re.search(r"^  part def leftover_", text, re.M)
    assert not re.search(r"^  part def TierACodec", text, re.M)
    assert not re.search(r"^  part def LegacyPipeImport", text, re.M)
    assert "part leftover_id_first" not in text
    assert "part leftover_by_id" not in text
    assert "part leftover_MERGE_by_id" not in text
    assert "part leftover_NEW_mint" not in text
    assert "part leftover_require_anchor" not in text
    assert "part leftover_allocate_from_locator" not in text
    assert "part leftover_ingestIsIdRule" not in text
    assert "part leftover_read_get" not in text
    assert "part leftover_AssignedIdMap" not in text
    assert "part leftoverEmptySkip" not in text
    assert "leftoverFogNested : Boolean = false" in text
    assert "leftoverArchiveOffLoad : Boolean = true" in text
    assert "httpImplemented : Boolean = false" in text
    assert "tipIsFace : Boolean = false" in text
    assert "agentWire : Boolean = false" in text


def test_one_page_nest_labels_shelves():
    text = NEST.read_text(encoding="utf-8")
    for needle in (
        "Core",
        "RecallCommit",
        "Path A",
        "Path B",
        "ImportGuard",
        "ImportAbsorb",
        "DurableBuffer",
        "APPLICATION LOOK",
        "ARCHIVE LOOK",
        "OPS LOOK",
        "CousinPointingContrast",
        "MemNetUsageDashboard",
        "httpImplemented=false",
        "tipIsFace=false",
    ):
        assert needle in text


def test_no_http_dashboard_code_in_engine():
    hits = []
    for path in PARTS.rglob("*.py"):
        blob = path.read_text(encoding="utf-8", errors="replace")
        if "MemNetUsageDashboard" in blob or "usage_dashboard_http" in blob:
            hits.append(str(path.relative_to(ROOT)))
    assert hits == []
