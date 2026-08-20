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
| [`ROADMAP.md`](ROADMAP.md) | **Version map SSOT** — one picture; 1.0 = claim; numbered extras 0.10–0.19 packaged as Hatch **0.19.0** |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | Accepted: GQL wire; **no Layer** (supersession) |
| [`grammar/README.md`](grammar/README.md) | Grammar folder — GQL teach only |
| [`grammar/math-skeleton.md`](grammar/math-skeleton.md) | **0.5 math SSOT** — Recall(\(q\)) / Commit(\(\Delta\)); Absorb join; one \(S\) per generate |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** — GQL wire + shaped-read contract |
| [`grammar/openCypher.bnf`](grammar/openCypher.bnf) | Official grammar BNF (spelling/identity SSOT; Apache-2.0) |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask operating model (as-is 0.8; RSV + Path-B ingest shipped; full ACL modes to-be) |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | Durable adapter: 0.7 live hydrate/flush proven; Fake + URL skip |
| [`grammar/neo4j-buffer.md`](grammar/neo4j-buffer.md) | MemNet ↔ Neo4j; live claimed (0.14); two namespaces (0.16) |
| [`grammar/memnet-neighbourhood-reserve.md`](grammar/memnet-neighbourhood-reserve.md) | Neighbourhood reserve (shipped RSV; grammar still the design note) |
| [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md) | Host locators into MutateGate (0.17 `RagHostHook`; Snap vs Shape; skip valid) |
| [`grammar/memnet-session-strata.md`](grammar/memnet-session-strata.md) | Sessions as strata (not Layer); 0.15 catalog Snap |
| [`grammar/memnet-security-multi-agent.md`](grammar/memnet-security-multi-agent.md) | Session ACL / multi-agent (design) |
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL-wire case study |

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

**Multitask (application):** [`.cursor/skills/memnet-multitask/`](../.cursor/skills/memnet-multitask/); [`application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md); ops MUST from [`multi-agent-sessions.md`](multi-agent-sessions.md).
