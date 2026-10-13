"""Honesty-c: MN-REQ-12.13 RSV is as-is shipped; behaviour must not deny it (#67)."""

from __future__ import annotations

from pathlib import Path

from memnet.neighbourhood_reserve import IMPLEMENTED as RSV_IMPLEMENTED

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
BEHAVIOUR = MODELS / "behaviour.sysml"
DEPLOY = MODELS / "deploy.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
IMPLEMENTATION = MODELS / "implementation.sysml"
NOTES = ROOT / "sysml-models" / "outputs" / "system-design-notes.md"
ASYNC_STUDY = ROOT / "sysml-models" / "outputs" / "async-parallel-conflict-case-study.md"
MAP = ROOT / "sysml-models" / "outputs" / "ssot-to-code-allocate-map.md"

_RSV_DENIALS = (
    "no neighbourhood reserve is shipped",
    "Neighbourhood reserve remains not shipped",
    "reserve is not shipped",
    "no RSV engine is claimed",
    "no neighbourhood reserve or Path-B PinMapIngest is claimed shipped",
    "no neighbourhood reserve coordinates overlapping writers",
    "reserve/lease remains doctrine",
)


def test_engine_rsv_is_shipped():
    assert RSV_IMPLEMENTED is True
    path = ROOT / "parts" / "common" / "memnet" / "memnet" / "neighbourhood_reserve.py"
    assert path.is_file()


def test_deploy_neighbourhood_reserve_implemented():
    text = DEPLOY.read_text(encoding="utf-8")
    block = text.split("part def NeighbourhoodReserve", 1)[1].split("part def ", 1)[0]
    assert "attribute implemented : Boolean = true;" in block
    assert 'attribute displayKind : String = "RSV";' in block
    assert "memnet.neighbourhood_reserve" in block
    dispatch = text.split("part def AsyncTaskDispatch", 1)[1].split("part def ", 1)[0]
    assert "no RSV engine is claimed" not in dispatch
    assert "NeighbourhoodReserve (RSV, MN-REQ-12.13) is shipped" in dispatch
    pool = text.split("part def WorkerPool", 1)[1].split("part def ", 1)[0]
    assert "no neighbourhood reserve or Path-B PinMapIngest is claimed shipped" not in pool
    assert "NeighbourhoodReserve (RSV) is shipped" in pool


def test_behaviour_and_verify_do_not_deny_shipped_rsv():
    blobs = {
        "behaviour.sysml": BEHAVIOUR.read_text(encoding="utf-8"),
        "deploy.sysml": DEPLOY.read_text(encoding="utf-8"),
        "verify.sysml": VERIFY.read_text(encoding="utf-8"),
        "connections.sysml": (MODELS / "connections.sysml").read_text(encoding="utf-8"),
        "async-parallel-conflict-case-study.md": ASYNC_STUDY.read_text(encoding="utf-8"),
    }
    found = []
    for name, text in blobs.items():
        for needle in _RSV_DENIALS:
            if needle in text:
                found.append(f"{name}: {needle}")
    assert found == [], f"RSV denial leftover: {found}"
    behaviour = blobs["behaviour.sysml"]
    assert "NeighbourhoodReserve (MN-REQ-12.13) is shipped" in behaviour
    assert "Overlapping writers on one session MAY take RSV" in behaviour
    ver = blobs["verify.sysml"]
    assert "NeighbourhoodReserve (RSV) is shipped" in ver
    assert "verification def MN_VER_12_S13_AsyncParallelDisjoint" in ver


def test_requirement_and_allocate_still_claim_rsv():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "requirement def MN_REQ_12_13_NeighbourhoodReserve" in req
    assert 'attribute requirementId : String = "MN-REQ-12.13"' in req
    assert "reserve_conflict" in req
    impl = IMPLEMENTATION.read_text(encoding="utf-8")
    assert "part def NeighbourhoodReserveMod" in impl
    assert "allocation rsvToMod" in impl
    assert "memnet.neighbourhood_reserve" in impl
    ledger = MAP.read_text(encoding="utf-8")
    assert "| rsvToMod |" in ledger
    study = ASYNC_STUDY.read_text(encoding="utf-8")
    assert "12.13" in study


def test_design_notes_retire_neo4j_live_claim():
    notes = NOTES.read_text(encoding="utf-8")
    assert "liveNeo4jClaimed=true" not in notes
    assert "MemNetArchive" in notes
    assert "Retired (#187)" in notes
