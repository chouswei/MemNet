"""Honesty-c: drop real stale sessions (MN-REQ-01.9 / MN-VER-01-S04)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQ = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
BEHAVIOUR = MODELS / "behaviour.sysml"
CONNECTIONS = MODELS / "connections.sysml"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
GUIDE = ROOT / "docs" / "LLM-GUIDE.md"
README = ROOT / "README.md"
STRATA = ROOT / "docs" / "extras" / "memnet-session-strata.md"
NESTED = ROOT / ".cursor" / "skills" / "memnet-nested-sessions" / "SKILL.md"
GRAMMAR = ROOT / ".cursor" / "skills" / "mcp-memnet" / "references" / "tool-grammar.md"
POLICY = ROOT / ".cursor" / "skills" / "mcp-memnet" / "references" / "mcp-policy.md"
DASHBOARD = ROOT / "sysml-models" / "outputs" / "usage-dashboard-case-study.md"
PASSPORT = ROOT / "sysml-models" / "outputs" / "snapshot-passport-case-study.md"
PORTAL = ROOT / "docs" / "operations" / "tip-memnet-access-portal.md"
ROADMAP = ROOT / "docs" / "ROADMAP.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mn_req_01_9_drop_stale():
    text = _read(REQ)
    assert "requirement def MN_REQ_01_9_DropStaleSessions" in text
    assert "idle_minutes" in text
    assert "housekeep prune" in text
    assert "Sliding TTL SHALL NOT count as" in text
    assert "dropStaleSessionsReq" in text


def test_mn_req_01_3_and_06_look_name_drop_stale():
    text = _read(REQ)
    assert "session drop-stale apply unlinks that known sid" in text
    assert "session_drop_stale, mutate" in text
    assert "or session_drop_stale from the page" in text


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
    assert "attribute dropStaleApplyUnlinksExpireSnap : Boolean = true;" in text
    assert "attribute sessionDropStalePort : Boolean = false;" in text
    assert "attribute sessionDropStale : Boolean = false;" in text
    assert "Housekeep stale is not named-session drop" in text


def test_verify_mn_ver_01_s04():
    text = _read(VERIFY)
    assert "verification def MN_VER_01_S04_DropStaleSessions" in text
    assert 'attribute verificationId : String = "MN-VER-01-S04";' in text
    assert "dropStaleSessionsVerify" in text
    assert ".dropStaleDropsExpireSnap == true" in text
    assert "dashboard.sessionClosePort == false" in text
    assert "dashboard.sessionDropStalePort == false" in text
    assert "dashboard.sessionCensus.sessionDropStale == false" in text
    assert "portal.portal.sessionDropStalePort == false" in text


def test_behaviour_ev_drop_stale():
    text = _read(BEHAVIOUR)
    assert "attribute def EvDropStale" in text
    assert "accept EvDropStale" in text
    assert "Not housekeep prune stale" in text
    assert "session drop-stale apply unlinks that" in text


def test_connections_look_flow_must_not_drop_stale():
    text = _read(CONNECTIONS)
    assert "session_drop_stale" in text


def test_docs_distinguish_housekeep_rows():
    guide = _read(GUIDE)
    assert "session_drop_stale" in guide
    assert "housekeep prune stale" in guide
    assert "memnet session drop-stale --idle-minutes N" in guide
    nest = _read(NEST)
    assert "MN-VER-01-S04" in nest
    assert "session drop-stale" in nest
    assert "sessionDropStalePort=false" in nest
    readme = _read(README)
    assert "session drop-stale --idle-minutes N" in readme
    assert "housekeep prune stale" in readme
    strata = _read(STRATA)
    assert "session drop-stale --idle-minutes N" in strata
    assert "housekeep prune stale" in strata
    nested = _read(NESTED)
    assert "session_drop_stale" in nested
    grammar = _read(GRAMMAR)
    assert "`session_drop_stale`" in grammar
    assert "|dropped" in grammar
    policy = _read(POLICY)
    assert "session_drop_stale" in policy
    dashboard = _read(DASHBOARD)
    assert "session_drop_stale" in dashboard
    passport = _read(PASSPORT)
    assert "session drop-stale --apply" in passport
    portal = _read(PORTAL)
    assert "session_drop_stale" in portal
    roadmap = _read(ROADMAP)
    assert "session drop-stale" in roadmap
    assert "Later `c` (Unreleased)" in roadmap
