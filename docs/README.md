# MemNet documentation

Two classes only. **Developers** — engine, MCP, GQL wire, and agent operating doctrine for this product. **Applications** — how to apply MemNet in downstream work (system repos, domains, custom MCP).

Hub: [`AGENTS.md`](../AGENTS.md) · layout: [`LAYOUT.md`](../LAYOUT.md) · doctrine entry: [`README.md`](../README.md).

---

## For developers

MemNet engine / generic MCP / GQL wire / operating the product as an agent.

| Doc | Role |
|-----|------|
| [`LLM-GUIDE.md`](LLM-GUIDE.md) | Agent playbook (GQL teach) |
| [`SHAPE.md`](SHAPE.md) | Product shape from the problem (0.8 teach) |
| [`ROADMAP.md`](ROADMAP.md) | **Version map SSOT** — one picture; 1.0 = claim; numbered extras 0.10–0.19 on master (untagged) |
| [`ROADMAP-0.5.md`](ROADMAP-0.5.md) | Historical pointer (old SemVer filename) |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | Accepted: GQL wire; **no Layer** (supersession) |
| [`grammar/math-skeleton.md`](grammar/math-skeleton.md) | **0.5 math SSOT** — Recall(\(q\)) / Commit(\(\Delta\)); Absorb join; one \(S\) per generate |
| [`../sysml-models/outputs/recall-commit-orthodox-plan.md`](../sysml-models/outputs/recall-commit-orthodox-plan.md) | Orthodox review; all tests are paradox |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** — GQL wire + shaped-read contract |
| [`grammar/openCypher.bnf`](grammar/openCypher.bnf) | Official grammar BNF (spelling/identity SSOT; Apache-2.0) |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask operating model (as-is 0.8; RSV + Path-B ingest shipped; full ACL modes to-be) |
| [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md) | GQL-wire paradox (historical filename) |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | Durable adapter: 0.7 live hydrate/flush proven; Fake + URL skip |
| [`grammar/neo4j-buffer.md`](grammar/neo4j-buffer.md) | MemNet ↔ Neo4j; RAG relatives on Snap / Shape / cabinet; live claimed (0.14); two namespaces (0.16) |
| [`grammar/memnet-field-formulas.md`](grammar/memnet-field-formulas.md) | Formula-as-EDGE design (historical; prefer law-on-node in GQL profile) |
| [`grammar/memnet-neighbourhood-reserve.md`](grammar/memnet-neighbourhood-reserve.md) | Neighbourhood reserve (shipped RSV; grammar still the design note) |
| [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md) | Host locators into MutateGate (0.17 `RagHostHook`; Snap vs Shape; skip valid) |
| [`grammar/rag-relative-algorithms.md`](grammar/rag-relative-algorithms.md) | RAG-relative retrieve algorithms (research; GraphRAG / Graphiti / LightRAG / HippoRAG / …) |
| [`grammar/memnet-neo4j-rag-rethink.md`](grammar/memnet-neo4j-rag-rethink.md) | Design proposal: two ports; catalog Snap; join by Absorb (not shipped HostSearch) |
| [`grammar/memnet-harness-thesis.md`](grammar/memnet-harness-thesis.md) | Design thesis: harness memory plane; GitHub review + objections |
| [`grammar/memnet-session-strata.md`](grammar/memnet-session-strata.md) | Sessions as strata (not Layer); 0.15 catalog Snap |
| [`grammar/memnet-security-multi-agent.md`](grammar/memnet-security-multi-agent.md) | Session ACL / multi-agent (design) |
| [`grammar/memnet-grammar-design.md`](grammar/memnet-grammar-design.md) | As-is line-codec harness notes (not GQL teach) |
| [`grammar/archive/`](grammar/archive/) | Quarantined historical Layer / Tier A sources |
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL-wire case study |
| [`grammar/examples/`](grammar/examples/) | As-is golden fixtures (harness; Layer examples archived) |

**Multitask (developer):** [`multi-agent-sessions.md`](multi-agent-sessions.md). Product skill: [`.cursor/skills/memnet-reference/`](../.cursor/skills/memnet-reference/). SysML trail: MN-REQ-12 → [`sysml-models/outputs/multitask-case-study.md`](../sysml-models/outputs/multitask-case-study.md).

---

## For applications

Downstream system development and domain patterns — MemNet as working memory.

**Dialect:** **GQL only** — [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md). Shared contract: [`application-notes/README.md`](application-notes/README.md). Product shape: [`SHAPE.md`](SHAPE.md).

| Doc | Role |
|-----|------|
| [`application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md) | Multitask in `modelbasedPrj-*` |
| [`application-notes/llm-software-development.md`](application-notes/llm-software-development.md) | Multi-turn coding |
| [`application-notes/llm-sysml-v2-modeling.md`](application-notes/llm-sysml-v2-modeling.md) | SysML SSOT; relatives + sub-unit sessions |
| [`../sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../sysml-models/outputs/sysml-session-nest-cuts-case-study.md) | Evidence: Turns A–I (look loop, parallel interiors) |
| [`application-notes/llm-build-on-memnet.md`](application-notes/llm-build-on-memnet.md) | Custom MCP + skill pack |
| [`application-notes/llm-tech-docs-decomposition.md`](application-notes/llm-tech-docs-decomposition.md) | Manual / SCPI decomposition |
| [`application-notes/llm-circuit-schematic.md`](application-notes/llm-circuit-schematic.md) | Circuit schematic (GQL; see case study) |
| [`application-notes/llm-nodal-analysis-formulas.md`](application-notes/llm-nodal-analysis-formulas.md) | Nodal method (GQL; see case study) |
| [`application-notes/llm-daily-news.md`](application-notes/llm-daily-news.md) | Batch RSS digest |
| [`application-notes/llm-mud.md`](application-notes/llm-mud.md) | Multiplayer MUD |
| [`application-notes/`](application-notes/) | Application-notes index |
| [`application-notes/examples/`](application-notes/examples/) | Worked examples (GQL case study + math SSOT) |

**Multitask (application):** user-pack `~/.cursor/skills/memnet-multitask/`; [`application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md); ops MUST from [`multi-agent-sessions.md`](multi-agent-sessions.md).
