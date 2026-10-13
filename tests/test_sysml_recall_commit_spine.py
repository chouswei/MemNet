"""Honesty: MN-REQ-13 Recall/Commit is the requirements spine."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "sysml-models" / "models"
REQ = MODELS / "requirements.sysml"
DEPLOY = MODELS / "deploy.sysml"
COUSINS = MODELS / "cousins.sysml"
VERIFY = MODELS / "verify.sysml"
MAPPING = ROOT / "sysml-models" / "outputs" / "mn-req-13-spine-mapping.md"

CLOSED_SURFACES = {
    "Recall",
    "Commit",
    "option:Recall",
    "option:Commit",
    "session",
    "option:session",
    "internal",
    "ops",
    "surface",
    "mission",
    "spine",
}


def _req() -> str:
    return REQ.read_text(encoding="utf-8")


def _pairs(text: str) -> list[tuple[str, str]]:
    ids = re.findall(r'attribute requirementId : String = "(MN-REQ-[^"]+)"', text)
    surfaces = re.findall(r'attribute agentSurface : String = "([^"]+)"', text)
    assert len(ids) == len(surfaces), f"id/surface mismatch {len(ids)} vs {len(surfaces)}"
    return list(zip(ids, surfaces, strict=True))


def test_every_requirement_has_closed_agent_surface():
    pairs = _pairs(_req())
    assert len(pairs) == 133
    unknown = sorted({s for _, s in pairs if s not in CLOSED_SURFACES})
    assert unknown == []
    by_id = dict(pairs)
    assert by_id["MN-REQ-13"] == "spine"
    assert by_id["MN-REQ-13.Recall"] == "Recall"
    assert by_id["MN-REQ-13.Commit"] == "Commit"
    assert by_id["MN-REQ-13.2"] == "Commit"
    assert by_id["MN-REQ-03.1"] == "Commit"
    assert by_id["MN-REQ-03.2"] == "Commit"
    assert by_id["MN-REQ-03.3"] == "Commit"
    assert by_id["MN-REQ-04.9"] == "Recall"
    assert by_id["MN-REQ-04.13"] == "option:Recall"
    assert by_id["MN-REQ-09.1"] == "internal"
    assert by_id["MN-REQ-01.7"] == "session"
    assert by_id["MN-REQ-01.8"] == "session"
    assert by_id["MN-REQ-06.5"] == "ops"


def test_spine_nest_and_usages():
    text = _req()
    assert "requirement def MN_REQ_13_Recall" in text
    assert "requirement def MN_REQ_13_Commit" in text
    commit_block = text.split("requirement def MN_REQ_13_Commit {", 1)[1]
    commit_block = commit_block.split("requirement recallCommitReq", 1)[0]
    assert "requirement def MN_REQ_13_2_SameThingAbsorb" in commit_block
    assert (
        "MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_Commit"
        "::MN_REQ_13_2_SameThingAbsorb" in text
    )
    assert "requirement recallSpineReq" in text
    assert "requirement commitSpineReq" in text
    assert "deriveRecallSpineLeaves" in text
    assert "deriveCommitSpineLeaves" in text
    assert "end #original ::> recallSpineReq" in text
    assert "end #original ::> commitSpineReq" in text
    assert "end #derive ::> addFailsIfExistsReq" in text
    assert "end #derive ::> sessionOutlineEmptyCueReq" in text
    assert "end #derive ::> playbooksAsRecallOptionReq" in text


def test_agent_surface_five_verbs_and_kept_laws():
    text = _req()
    assert "verbs are exactly five: recall (pin_map), commit (mutate)" in text
    assert "session_open, session_save, and session_close" in text
    assert "Silent upsert SHALL NOT be offered" in text
    assert "opt-in Commit mode" in text
    assert "created, updated, or unchanged" in text
    assert "The merge is never silent" in text
    assert "owner decision and is pending" not in text
    assert "truncated=true" in text
    assert "Empty q SHALL be" in text or "empty q SHALL return" in text
    assert "canonical parser" in text.lower() or "Canonical parser" in text
    three_three = text.split("requirement def MN_REQ_03_3_NoSilentUpsert", 1)[1]
    three_three = three_three.split("requirement def MN_REQ_03_4_HonourWherePredicate", 1)[0]
    assert "report created, updated, or unchanged" in three_three
    assert "never silent" in three_three
    seven = text.split("requirement def MN_REQ_07_1_GenericToolSurface", 1)[1]
    seven = seven.split("requirement def MN_REQ_07_2_StructuredToolEnvelope", 1)[0]
    assert "Options of Recall: find" in seven
    assert "list_playbooks / get_playbook" in seven
    assert "Options of Commit: leftover add / update" in seven
    assert "merge-by-identity" in seven
    assert "Internal: housekeep_stats" in seven


def test_satisfy_paths_follow_commit_nest():
    path = (
        "MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit"
        "::MN_REQ_13_Commit::MN_REQ_13_2_SameThingAbsorb"
    )
    assert path in DEPLOY.read_text(encoding="utf-8")
    assert path in COUSINS.read_text(encoding="utf-8")
    old = "MN_REQ_13_RecallCommit::MN_REQ_13_2_SameThingAbsorb;"
    assert old not in DEPLOY.read_text(encoding="utf-8")
    assert old not in COUSINS.read_text(encoding="utf-8")


def test_mapping_table_and_verify_coverage():
    md = MAPPING.read_text(encoding="utf-8")
    assert "MN-REQ-13.Recall" in md
    assert "MN-REQ-13.Commit" in md
    assert "old organisational parent" in md.lower() or "Old parent" in md
    assert "MN-REQ-04.13" in md
    assert "opt-in" in md.lower()
    assert "never silent" in md
    assert "ids stable" in md
    assert "mn_" not in md
    assert "03.1–03.3 stay strict" not in md
    text = _req()
    pairs = _pairs(text)
    counts = Counter(s for _, s in pairs)
    assert counts["Recall"] + counts["option:Recall"] == 27
    assert counts["Commit"] + counts["option:Commit"] == 30
    assert counts["internal"] == 44
    assert counts["ops"] == 17
    usages = re.findall(r"^  requirement (missionReq|\w+Req)\b", text, re.M)
    assert "missionReq" in usages
    assert "recallSpineReq" in usages
    assert "commitSpineReq" in usages
    assert "playbooksAsRecallOptionReq" in usages
    assert len(usages) == 133
    verified = set(re.findall(r"verify (\w+);", VERIFY.read_text(encoding="utf-8")))
    unverified = [u for u in usages if u not in verified]
    assert len(verified & set(usages)) == 56
    assert len(unverified) == 77
    assert "recallSpineReq" in unverified
    assert "commitSpineReq" in unverified
    assert "playbooksAsRecallOptionReq" in verified
    assert "noSilentUpsertReq" in verified
    assert "addFailsIfExistsReq" in verified
    assert "updateFailsIfAbsentReq" in verified


def test_brace_balance_requirements():
    text = _req()
    assert text.count("{") == text.count("}")


def test_merge_and_report_and_playbooks_on_paper():
    deploy = DEPLOY.read_text(encoding="utf-8")
    verify = VERIFY.read_text(encoding="utf-8")
    assert 'attribute defaultMode : String = "merge_and_report"' in deploy
    assert "attribute reportCreatedUpdatedUnchanged : Boolean = true" in deploy
    assert "attribute silentUpsert : Boolean = false" in deploy
    assert "attribute optInStrictAddFailsIfExists : Boolean = true" in deploy
    assert "part def PlaybookGuide" in deploy
    assert "part listPlaybooks : CmdListPlaybooks" in deploy
    assert "part getPlaybook : CmdGetPlaybook" in deploy
    assert deploy.count("part listPlaybooks : CmdListPlaybooks") == 2
    assert deploy.count("part getPlaybook : CmdGetPlaybook") == 2
    assert (
        "attribute implemented : Boolean = false"
        in deploy.split("part def PlaybookGuide {", 1)[1].split("part def Commit {", 1)[0]
    )
    assert "MN-VER-03-S02" in verify
    assert "MN-VER-04-S07" in verify
    assert (
        "tests/test_mutate_merge_report.py::test_commit_reports_created_updated_unchanged" in verify
    )
    assert "tests/test_memnet_playbooks.py::test_list_playbooks_and_get_playbook" in verify
    assert verify.count("attribute decidingTestImplemented : Boolean = false") == 2
    assert "playbooksAsRecallOptionReq" in verify
    assert "noSilentUpsertReq" in verify
