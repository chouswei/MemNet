"""Honesty-c: ClusterRoute vs SliceHandCarry invent (#191 / #47 cousin; tip≠face)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
DEPLOY = MODELS / "deploy.sysml"
REQUIREMENTS = MODELS / "requirements.sysml"
VERIFY = MODELS / "verify.sysml"
CONNECTIONS = MODELS / "connections.sysml"
ROOT_SYSML = MODELS / "root.sysml"
CONFIG = ROOT / "sysml-models" / "config.yaml"
NEST = ROOT / "sysml-models" / "outputs" / "product-nest-one-page.md"
STUDY = ROOT / "sysml-models" / "outputs" / "cluster-route-vs-slice-hand-carry-case-study.md"
TEACH = ROOT / "docs" / "operations" / "cluster-route-vs-slice-hand-carry.md"
LAN_TEACH = ROOT / "docs" / "operations" / "memnet-lan-mcp-front.md"

_PROJECT = ROOT / "project.toml"


def test_two_moves_parts_outside_system():
    text = DEPLOY.read_text(encoding="utf-8")
    assert "part def ClusterRoute" in text
    assert "part def SliceHandCarry" in text
    assert "part def MemNetTwoMoves" in text
    assert "part def SliceExportCarry" in text
    assert "part def LanFileCopy" in text
    assert "part def DestSessionAbsorb" in text
    assert "part clusterRoute : ClusterRoute" in text
    assert "part sliceHandCarry : SliceHandCarry" in text
    assert "part twoMoves : MemNetTwoMoves" in text
    assert "twoMovesInsideSystem : Boolean = false" in text
    assert "MemNetTwoMoves / SliceHandCarry MUST NOT nest here" in text
    assert "attribute isWhereSessionLives : Boolean = true" in text
    assert "attribute isExplicitCopy : Boolean = true" in text
    assert "attribute isLiveHop : Boolean = false" in text
    assert "attribute importSliceSameServeOnly : Boolean = true" in text
    assert "attribute importSliceAcrossHosts : Boolean = false" in text
    assert "attribute importSliceFromUrl : Boolean = false" in text
    assert "attribute realisedByLanFront : Boolean = true" in text
    assert "attribute destIsDifferentSession : Boolean = true" in text
    assert "attribute sourceSessionStays : Boolean = true" in text
    assert "attribute truncationFlagsSurviveBothMoves : Boolean = true" in text
    assert "attribute clippedMustNotLookComplete : Boolean = true" in text
    assert "part lanMcpFront : MemNetLanMcpFront" in text
    assert text.count("part def MemNetLanMcpFront") == 1
    assert "end port source ::> exportCarry.fileOut" in text
    assert "end port sink ::> lanCopy.fileIn" in text
    assert "end port source ::> lanCopy.fileOut" in text
    assert "end port sink ::> destAbsorb.fileIn" in text


def test_requirement_verify_and_load():
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "MN-REQ-06.10" in req
    assert "requirement def MN_REQ_06_10_SliceHandCarryAcrossServes" in req
    assert "sliceHandCarryAcrossServesReq" in req
    assert "ClusterRoute" in req
    assert "SliceHandCarry" in req
    assert "import_slice(from_url)" in req
    assert "#47" in req
    ver = VERIFY.read_text(encoding="utf-8")
    assert "verification def MN_VER_06_S08_ClusterRouteVsSliceHandCarry" in ver
    assert "verify sliceHandCarryAcrossServesReq" in ver
    assert "twoMoves.clusterIsWhereSessionLives == true" in ver
    assert "twoMoves.sliceIsExplicitCopy == true" in ver
    assert "twoMoves.liveHop == false" in ver
    assert "slice.importSliceAcrossHosts == false" in ver
    assert "front.clusterRoute.openRoute.writesRegistry == true" in ver
    conn = CONNECTIONS.read_text(encoding="utf-8")
    assert "item def MemNetTwoMovesContrast" in conn
    assert "item def SliceHandCarryFile" in conn
    assert "connection def SliceFileFlow" in conn
    assert "import_slice(from_url)" in conn
    root = ROOT_SYSML.read_text(encoding="utf-8")
    assert "MemNetTwoMoves" in root
    assert "SliceHandCarry" in root
    assert "private import MemNet::" in root
    cfg = CONFIG.read_text(encoding="utf-8")
    assert "deploy.sysml" in cfg
    assert "MemNetTwoMoves / SliceHandCarry nests in deploy.sysml" in cfg


def test_teach_one_screen_contrast():
    study = STUDY.read_text(encoding="utf-8")
    teach = TEACH.read_text(encoding="utf-8")
    nest = NEST.read_text(encoding="utf-8")
    lan = LAN_TEACH.read_text(encoding="utf-8")
    for blob in (study, teach, nest):
        assert "tip≠face" in blob
        assert "inventOnly" in blob
        assert "ClusterRoute" in blob
        assert "SliceHandCarry" in blob
    assert "Where the session **lives**" in teach or "where the session lives" in teach.lower()
    assert "Explicit **copy**" in teach or "explicit copy" in teach.lower()
    assert "import_slice" in teach
    assert "SAME" in teach or "same serve" in teach.lower()
    assert "from_url" in teach
    assert "InkMirage" in teach
    assert "Szu-Wei" not in teach
    assert "Szu-Wei" not in study
    assert "MN-REQ-06.10" in study
    assert "MN-VER-06-S08" in study
    assert "MemNetTwoMoves" in nest
    assert "liveHop=false" in nest
    assert "cluster-route-vs-slice-hand-carry.md" in lan
    assert "no SemVer" in teach or "no SemVer" in study


def test_no_semver_bump_in_this_invent():
    text = _PROJECT.read_text(encoding="utf-8")
    assert 'version = "0.19.22"' in text
    assert "0.19.23" not in text
