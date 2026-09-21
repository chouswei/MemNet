"""Honesty-c: skills route SSOT-to-code tracker; no drifting code map."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".cursor" / "skills"
GRAPH = SKILLS / "SKILL-GRAPH.md"
REF = SKILLS / "memnet-reference" / "SKILL.md"
NEW = SKILLS / "sysml-ssot-to-code" / "SKILL.md"
CACHE_MAP = SKILLS / "sysml-memnet-documentation" / "references" / "relatives-cache-map.md"
AGENTS = ROOT / "AGENTS.md"


def test_ssot_to_code_skill_vendored_and_routed():
    assert NEW.is_file()
    text = NEW.read_text(encoding="utf-8")
    assert "SoftwareAllocate" in text
    assert "ssot-to-code-allocate-map.md" in text
    assert "MUST NOT" in text
    assert "sysmledge" in text
    assert "sysml-allocate-generator" in text
    graph = GRAPH.read_text(encoding="utf-8")
    assert "sysml-ssot-to-code" in graph
    assert "track implementation" in graph
    agents = AGENTS.read_text(encoding="utf-8")
    assert "sysml-ssot-to-code" in agents


def test_memnet_reference_drops_duplicate_code_map():
    text = REF.read_text(encoding="utf-8")
    assert "Implementation tracker" in text
    assert "ssot-to-code-allocate-map.md" in text
    assert "sysml-ssot-to-code" in text
    assert "parts/common/memnet/memnet/cli/" not in text
    assert "| GqlCodec |" not in text
    assert "| MutateGate |" not in text
    assert "cli.py" in text


def test_pack_only_allocate_generator_not_vendored():
    assert not (SKILLS / "sysml-allocate-generator").exists()
    assert not (SKILLS / "sysml-hardware-part-generator").exists()
    cache = CACHE_MAP.read_text(encoding="utf-8")
    assert "sysml-ssot-to-code" in cache
    assert "MUST NOT invent those folders" in cache
    assert "| sysml-allocate-generator |" not in cache
    assert "| sysml-hardware-part-generator |" not in cache
    assert "| sysml-interconnection-mermaid |" not in cache
