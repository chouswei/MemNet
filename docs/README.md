# MemNet documentation

Two classes only. **Developers** — engine, MCP, GQL wire, and agent operating doctrine for this product. **Applications** — how to apply MemNet in downstream work (system repos, domains, custom MCP).

Hub: [`AGENTS.md`](../AGENTS.md) · layout: [`LAYOUT.md`](../LAYOUT.md) · doctrine entry: [`README.md`](../README.md).

---

## For developers

MemNet engine / generic MCP / GQL wire / operating the product as an agent.

| Doc | Role |
|-----|------|
| [`LLM-GUIDE.md`](LLM-GUIDE.md) | Agent playbook (GQL teach; as-is engine until M2) |
| [`ROADMAP-0.5.md`](ROADMAP-0.5.md) | One-path / 0.5.0 plan; **Next: M2**, then **M2.5** durable store |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | Accepted: GQL wire; **no Layer** (supersession) |
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** — GQL wire + shaped-read contract |
| [`multi-agent-sessions.md`](multi-agent-sessions.md) | Multitask operating model (as-is 0.4.x) |
| [`grammar/gql-model-exam.md`](grammar/gql-model-exam.md) | Nested GQL model exam |
| [`grammar/agensgraph-buffer.md`](grammar/agensgraph-buffer.md) | Durable GQL store adapter sketch (**planned M2.5**) |
| [`grammar/memnet-field-formulas.md`](grammar/memnet-field-formulas.md) | Formula-as-EDGE design (historical; prefer law-on-node in GQL profile) |
| [`grammar/memnet-neighbourhood-reserve.md`](grammar/memnet-neighbourhood-reserve.md) | Neighbourhood reserve (design) |
| [`grammar/memnet-host-search-nest.md`](grammar/memnet-host-search-nest.md) | Host RAG/index nest (design; outside MemNetSystem; math pointers) |
| [`grammar/memnet-security-multi-agent.md`](grammar/memnet-security-multi-agent.md) | Session ACL / multi-agent (design) |
| [`grammar/memnet-grammar-design.md`](grammar/memnet-grammar-design.md) | As-is line-codec harness notes (not 1.x teach) |
| [`grammar/archive/`](grammar/archive/) | Quarantined historical Layer / Tier A sources |
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL-wire case study |
| [`grammar/examples/`](grammar/examples/) | As-is golden fixtures (harness until M2) |

**Multitask (developer):** [`multi-agent-sessions.md`](multi-agent-sessions.md). Product skill: [`.cursor/skills/memnet-reference/`](../.cursor/skills/memnet-reference/). SysML trail: MN-REQ-12 → [`sysml-models/outputs/multitask-case-study.md`](../sysml-models/outputs/multitask-case-study.md).

---

## For applications

Downstream system development and domain patterns — MemNet as working memory.

**Dialect:** **GQL only** — [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md). Application-note **bodies** still being migrated (M3); prefer the GQL case study and profile for wire shapes.

| Doc | Role |
|-----|------|
| [`application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md) | Multitask in `modelbasedPrj-*` |
| [`application-notes/llm-software-development.md`](application-notes/llm-software-development.md) | Multi-turn coding |
| [`application-notes/llm-sysml-v2-modeling.md`](application-notes/llm-sysml-v2-modeling.md) | SysML v2 modeling |
| [`application-notes/llm-build-on-memnet.md`](application-notes/llm-build-on-memnet.md) | Custom MCP + skill pack |
| [`application-notes/llm-tech-docs-decomposition.md`](application-notes/llm-tech-docs-decomposition.md) | Manual / SCPI decomposition |
| [`application-notes/llm-circuit-schematic.md`](application-notes/llm-circuit-schematic.md) | Circuit schematic (body M3; see GQL case study) |
| [`application-notes/llm-nodal-analysis-formulas.md`](application-notes/llm-nodal-analysis-formulas.md) | Nodal method (body M3; see GQL case study) |
| [`application-notes/llm-daily-news.md`](application-notes/llm-daily-news.md) | Batch RSS digest |
| [`application-notes/llm-mud.md`](application-notes/llm-mud.md) | Multiplayer MUD |
| [`application-notes/`](application-notes/) | Application-notes index |
| [`application-notes/examples/`](application-notes/examples/) | Worked examples (GQL case study + historical seeds) |

**Multitask (application):** user-pack `~/.cursor/skills/memnet-multitask/`; [`application-notes/llm-system-dev-multitask.md`](application-notes/llm-system-dev-multitask.md); ops MUST from [`multi-agent-sessions.md`](multi-agent-sessions.md).
