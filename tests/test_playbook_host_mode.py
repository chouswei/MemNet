"""Honesty-c: prefix is the host; modelbasedPrj-* MUST NOT use SysMLEdge as model SSOT."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "docs" / "LLM-GUIDE.md"
NOTE = ROOT / "docs" / "application-notes" / "system" / "llm-system-dev-multitask.md"
CHECKPOINT = ROOT / "docs" / "application-notes" / "system" / "llm-unsync-checkpoint-pipeline.md"
SHAPE = ROOT / "docs" / "SHAPE.md"
SKILL = ROOT / ".cursor" / "skills" / "memnet-multitask" / "SKILL.md"
COUSINS = ROOT / "sysml-models" / "models" / "cousins.sysml"
VERIFY = ROOT / "sysml-models" / "models" / "verify.sysml"
REQUIREMENTS = ROOT / "sysml-models" / "models" / "requirements.sysml"


def test_playbook_sysmledge_host_mode():
    playbook = PLAYBOOK.read_text(encoding="utf-8")
    note = NOTE.read_text(encoding="utf-8")
    checkpoint = CHECKPOINT.read_text(encoding="utf-8")
    shape = SHAPE.read_text(encoding="utf-8")
    skill = SKILL.read_text(encoding="utf-8")
    for blob in (playbook, note, checkpoint, shape, skill):
        assert "shared working memory" in blob or "campaign working memory" in blob
        assert "SysMLEdge-based" in blob
        assert "repo-based" in blob
        assert "use SysMLEdge as model SSOT" in blob
    assert "SSOT graph is hosted by SysMLEdge" in playbook
    assert "SSOT graph is hosted by SysMLEdge" in note
    assert "working_ssot=graph" in playbook
    assert "working_ssot=graph" in note
    assert "MUST NOT substitute" in playbook or "MUST NOT substitute" in note
    assert "Operator README on that overlay states SysMLEdge-based" in note
    assert "repo-based or SysMLEdge-based" not in playbook
    assert "repo-based or SysMLEdge-based" not in note
    assert "MUST NOT copy a SysMLEdge host onto a `modelbasedPrj-*`" in note
    assert "desk is a look, not SSOT" not in note
    assert "git `sysml-models/` stays structural SSOT" not in note
    assert "product `pin_map` / `ask`" in checkpoint
    assert "campaign only, not model SSOT" in checkpoint


def test_cousin_bound_desk_honesty():
    cousins = COUSINS.read_text(encoding="utf-8")
    verify = VERIFY.read_text(encoding="utf-8")
    req = REQUIREMENTS.read_text(encoding="utf-8")
    assert "attribute memnetIsMissionWorkingMemory : Boolean = true" in cousins
    assert "attribute modelbasedPrjRepoBased : Boolean = true" in cousins
    assert "attribute modelbasedPrjSysmlEdgeIsModelSsot : Boolean = false" in cousins
    assert "attribute operatorReadmeStatesHost : Boolean = true" in cousins
    assert "attribute downstreamBoundDeskIsWorkingModelSsot : Boolean = true" in cousins
    assert "attribute gitModelPathIsSsot : Boolean = true" in cousins
    assert "attribute thisRepoHasProductFace : Boolean = false" in cousins
    assert "SHALL NOT flip a modelbasedPrj-* tree" in cousins
    assert "downstreamBoundDeskIsWorkingModelSsot == true" in verify
    assert "memnetIsMissionWorkingMemory == true" in verify
    assert "modelbasedPrjRepoBased == true" in verify
    assert "modelbasedPrjSysmlEdgeIsModelSsot == false" in verify
    assert "not MemNet SSOT" in req
    assert "desk graph is working model SSOT" in req
    assert "MUST NOT use SysMLEdge as model SSOT" in req
