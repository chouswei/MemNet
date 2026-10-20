"""MN-REQ-05.5 session cap LRU evict: SysML text checks (proposed, not shipped)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
README = ROOT / "sysml-models" / "README.md"
DEPLOY = MODELS / "deploy.sysml"
REQ = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
BEHAVIOUR = MODELS / "behaviour.sysml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mn_req_05_5_requirement_def_and_usage():
    text = _read(REQ)
    assert "MN-REQ-05.5        Session cap evicts least-recently-touched" in text
    assert "requirement def MN_REQ_05_5_SessionCapEvictLru {" in text
    assert 'attribute requirementId : String = "MN-REQ-05.5";' in text
    assert "requirement sessionCapEvictLruReq" in text
    assert "MN_REQ_05_HardCaps::MN_REQ_05_5_SessionCapEvictLru;" in text
    assert "end #derive ::> sessionCapEvictLruReq;" in text


def test_mn_req_05_5_rules_in_doc():
    text = _read(REQ)
    start = text.index("requirement def MN_REQ_05_5_SessionCapEvictLru {")
    body = text[start : text.index('attribute requirementId : String = "MN-REQ-05.5";', start)]
    assert "MEMNET_MAX_SESSIONS" in body
    assert "oldest last-touch time" in body
    assert "fsync" in body
    assert "@SNAP version 2" in body
    assert "snapshot_unsaveable" in body
    assert "limit_exceeded|sessions n/cap" in body
    assert "active write lock" in body
    assert "sessions_evicted" in body
    assert "later session_load SHALL restore" in body
    assert "MN-VER-05-S03 to MN-VER-05-S09" in body


def test_mn_req_05_5_derivation_links():
    text = _read(REQ)
    assert "end #original ::> sessionTtlAndCapsReq;" in text
    assert "end #original ::> snapshotLosslessRoundTripReq;" in text
    assert "end #original ::> snapshotAclReq;" in text
    assert "#derivation connection deriveSessionCapEvictFromCapsAndSnapshot" in text


def test_deploy_caps_evict_flags():
    text = _read(DEPLOY)
    assert "attribute maxSessions : Integer = 1024;" in text
    assert "attribute evictOnSessionCap : Boolean = true;" in text
    assert 'attribute envMaxSessions : String = "MEMNET_MAX_SESSIONS";' in text
    assert "attribute evictPicksOldestTouch : Boolean = true;" in text
    assert "attribute evictTouchOnReadOrWrite : Boolean = true;" in text
    assert "attribute evictSavesFirstFsync : Boolean = true;" in text
    assert "attribute evictSkipsUnsaveable : Boolean = true;" in text
    assert "attribute evictRefusesWhenNoneEvictable : Boolean = true;" in text
    assert "attribute evictNeverSelf : Boolean = true;" in text
    assert "attribute evictNeverWriteLocked : Boolean = true;" in text
    assert "attribute evictReportsNameNotId : Boolean = true;" in text
    assert "attribute evictLoadRestores : Boolean = true;" in text
    assert "attribute evictKeepsAclLease : Boolean = true;" in text
    assert "attribute evictShipped : Boolean = false;" in text
    assert "satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_5_SessionCapEvictLru;" in text


def test_serve_status_sessions_evicted_counter():
    text = _read(DEPLOY)
    start = text.index("part def ServeStatusLook {")
    body = text[start : text.index("part def SessionCensusLook {", start)]
    assert "attribute sessionsEvictedCounter : Boolean = true;" in body


def test_behaviour_evict_saving_state():
    text = _read(BEHAVIOUR)
    assert "attribute def EvEvictForCap" in text
    assert "state evictSaving" in text
    assert "accept EvEvictForCap" in text
    assert "then evictSaving;" in text
    assert "transition evict_saving_to_closed" in text
    assert "transition evict_saving_to_active" in text
    assert "An evicted session (MN-REQ-05.5)" in text
    assert "closed_to_loading via EvLoadSnapshot restores it" in text


def test_verify_mn_ver_05_s03_to_s09_defs_and_usages():
    text = _read(VERIFY)
    defs = [
        ("MN_VER_05_S03_SessionCapEvictOldestTouch", "MN-VER-05-S03", "sessionCapEvictOldestTouchVerify"),
        ("MN_VER_05_S04_SessionCapEvictSaveFirst", "MN-VER-05-S04", "sessionCapEvictSaveFirstVerify"),
        ("MN_VER_05_S05_SessionCapEvictSkipUnsaveable", "MN-VER-05-S05", "sessionCapEvictSkipUnsaveableVerify"),
        ("MN_VER_05_S06_SessionCapEvictNoneEvictable", "MN-VER-05-S06", "sessionCapEvictNoneEvictableVerify"),
        (
            "MN_VER_05_S07_SessionCapEvictExemptSelfAndLocked",
            "MN-VER-05-S07",
            "sessionCapEvictExemptSelfAndLockedVerify",
        ),
        ("MN_VER_05_S08_SessionCapEvictReportNameNotId", "MN-VER-05-S08", "sessionCapEvictReportNameNotIdVerify"),
        ("MN_VER_05_S09_SessionCapEvictLoadRestores", "MN-VER-05-S09", "sessionCapEvictLoadRestoresVerify"),
    ]
    for def_name, ver_id, usage in defs:
        assert f"verification def {def_name} {{" in text
        assert f'attribute verificationId : String = "{ver_id}";' in text
        assert f"verification {usage}" in text
        assert f"    : {def_name};" in text
    assert "verify sessionCapEvictLruReq;" in text
    assert "verify snapshotAclReq;" in text
    assert "verify loadSessionSnapshotReq;" in text


def test_verify_05_5_constraints_use_caps_paths():
    text = _read(VERIFY)
    start = text.index("verification def MN_VER_05_S03_SessionCapEvictOldestTouch {")
    end = text.index("verification def MN_VER_06_S06_StorageRoles {", start)
    block = text[start:end]
    assert block.count("system.core.transport.inProcess.memory.sessions.caps") >= 7
    assert ".envMaxSessions == \"MEMNET_MAX_SESSIONS\"" in block
    assert block.count(".evictShipped == false") == 7


def test_readme_lists_05_5():
    text = _read(README)
    assert "**05.5** session cap LRU evict (proposed, not shipped)" in text
    assert "MN-VER-05-S03…S09 (MN-REQ-05.5 session cap LRU evict, proposed)" in text
