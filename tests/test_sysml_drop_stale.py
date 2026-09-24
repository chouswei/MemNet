"""Honesty-c: drop real stale sessions (MN-REQ-01.9 / MN-VER-01-S04)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQ = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
BEHAVIOUR = MODELS / "behaviour.sysml"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
GUIDE = ROOT / "docs" / "LLM-GUIDE.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mn_req_01_9_drop_stale():
    text = _read(REQ)
    assert "requirement def MN_REQ_01_9_DropStaleSessions" in text
    assert "idle_minutes" in text
    assert "housekeep prune" in text
    assert "Sliding TTL SHALL NOT count as activity" in text
    assert "dropStaleSessionsReq" in text


def test_cmd_session_drop_stale_nest():
    text = _read(DEPLOY)
    assert "part def CmdSessionDropStale" in text
    assert "attribute dryRunDefault : Boolean = true;" in text
    assert "attribute dropsExpireSnap : Boolean = true;" in text
    assert "attribute notHousekeepRows : Boolean = true;" in text
    assert "attribute slidingTtlIsNotActivity : Boolean = true;" in text
    assert "part sessionDropStale : CmdSessionDropStale;" in text
    assert "attribute dropStaleImplemented : Boolean = true;" in text
    assert "attribute dropStaleNotHousekeepRows : Boolean = true;" in text


def test_verify_mn_ver_01_s04():
    text = _read(VERIFY)
    assert "verification def MN_VER_01_S04_DropStaleSessions" in text
    assert 'attribute verificationId : String = "MN-VER-01-S04";' in text
    assert "dropStaleSessionsVerify" in text
    assert ".dropStaleDropsExpireSnap == true" in text
    assert "dashboard.sessionClosePort == false" in text


def test_behaviour_ev_drop_stale():
    text = _read(BEHAVIOUR)
    assert "attribute def EvDropStale" in text
    assert "accept EvDropStale" in text
    assert "Not housekeep prune stale" in text


def test_docs_distinguish_housekeep_rows():
    guide = _read(GUIDE)
    assert "session_drop_stale" in guide
    assert "housekeep prune stale" in guide
    nest = _read(NEST)
    assert "MN-VER-01-S04" in nest
    assert "session drop-stale" in nest
