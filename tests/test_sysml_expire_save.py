"""Honesty-c: SysML TTL expire-save + leftover/dashboard nest review."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
DEPLOY = MODELS / "deploy.sysml"
REQ = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
BEHAVIOUR = MODELS / "behaviour.sysml"
CONFIG = ROOT / "sysml-models" / "config.yaml"
ROOT_SYSML = MODELS / "root.sysml"
ENGINE_CONFIG = ROOT / "parts" / "common" / "memnet" / "memnet" / "config.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mn_req_01_3_ttl_file_honesty():
    text = _read(REQ)
    assert "SHALL NOT auto-flush Neo4j" in text
    assert "MEMNET_SAVE_ON_EXPIRE" in text
    assert "session_load restores RAM" in text


def test_snapshot_store_and_caps_default_off():
    text = _read(DEPLOY)
    assert "attribute saveOnExpireDefault : Boolean = false;" in text
    assert "attribute saveOnExpireConfigurable : Boolean = true;" in text
    assert 'attribute envSaveOnExpire : String = "MEMNET_SAVE_ON_EXPIRE";' in text
    assert 'attribute envExpireSnapshotDir : String = "MEMNET_EXPIRE_SNAPSHOT_DIR";' in text
    assert "attribute ramDropsOnTtl : Boolean = true;" in text
    assert "attribute fileUntilUserDrop : Boolean = true;" in text
    assert "attribute loadRestoresRam : Boolean = true;" in text
    assert "attribute notNeo4j : Boolean = true;" in text
    assert "attribute ramDropsAfterExpireSave : Boolean = true;" in text
    assert "attribute ttlResetsOnLoad : Boolean = true;" in text


def test_verify_mn_ver_01_s03_and_nest_review():
    text = _read(VERIFY)
    assert "verification def MN_VER_01_S03_ExpireSaveConfigurable" in text
    assert 'attribute verificationId : String = "MN-VER-01-S03";' in text
    assert "expireSaveConfigurableVerify" in text
    assert ".saveOnExpireDefault == false" in text
    assert ".notNeo4j == true" in text
    assert "system.leftoverFogNested == false" in text
    assert "system.leftoverArchiveOffLoad == true" in text
    assert "dashboard.httpImplemented == false" in text
    assert "dashboard.tipIsFace == false" in text
    assert "dashboard.agentWire == false" in text


def test_behaviour_expire_ttl_fork():
    text = _read(BEHAVIOUR)
    assert "attribute def EvExpireTtl" in text
    assert "state expireSaving" in text
    assert "then expireSaving;" in text
    assert "Not Neo4j" in text


def test_leftover_archive_still_off_load():
    cfg = _read(CONFIG)
    assert "archive.sysml is OFF this load" in cfg
    assert "archive.sysml" not in [
        line.split("#", 1)[0].strip().lstrip("- ").strip()
        for line in cfg.splitlines()
        if line.strip().startswith("- ")
    ]
    root = _read(ROOT_SYSML)
    assert "private import MemNetArchive" not in root
    deploy = _read(DEPLOY)
    assert "leftoverFogNested : Boolean = false" in deploy
    assert "leftoverArchiveOffLoad : Boolean = true" in deploy


def test_dashboard_still_look_only():
    text = _read(DEPLOY)
    assert "attribute httpImplemented : Boolean = false;" in text
    assert "attribute tipIsFace : Boolean = false;" in text
    assert "attribute agentWire : Boolean = false;" in text
    nest = _read(NEST)
    assert "MEMNET_SAVE_ON_EXPIRE" in nest
    assert "leftoverFogNested=false" in nest
    assert "httpImplemented=false" in nest
    assert "MN-VER-01-S03" in nest


def test_engine_caps_still_default_off():
    text = _read(ENGINE_CONFIG)
    assert "MEMNET_SAVE_ON_EXPIRE" in text
    assert "def save_on_expire()" in text
