# MemNet documentation

Two classes only. **Developers** — engine, MCP, GQL wire, and agent operating doctrine. **Applications** — how to apply MemNet in downstream work.

Hub: [`AGENTS.md`](../AGENTS.md) · layout: [`LAYOUT.md`](../LAYOUT.md) · doctrine entry: [`README.md`](../README.md).

## Load order (agents)

1. Repo [`README.md`](../README.md) — what MemNet is and how to run it.
2. [`SHAPE.md`](SHAPE.md) — product from the problem.
3. [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) — **M1** agent wire (GQL only).
4. [`LLM-GUIDE.md`](LLM-GUIDE.md) — goldfish loop.
5. **One job folder** below — do not load every note.

Do **not** teach Layer / Tier A. **1.0** = claim of 0.5–0.8 (unclaimed).

---

## Identity

| Doc | Role |
|-----|------|
| [`SHAPE.md`](SHAPE.md) | Product shape from the problem (0.8 teach) |
| [`ROADMAP.md`](ROADMAP.md) | **SemVer SSOT** — locked `a.b.c`; extras 0.10–0.19 in Hatch **0.19.5** |
| [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md) | Accepted: GQL wire; **no Layer** |

## Wire — `grammar/`

GQL + 0.5 math + openCypher spelling. Index: [`grammar/README.md`](grammar/README.md).

| Doc | Role |
|-----|------|
| [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) | **M1 SSOT** — GQL wire + shaped-read |
| [`grammar/math-skeleton.md`](grammar/math-skeleton.md) | **0.5 math SSOT** — Recall(\(q\)) / Commit(\(\Delta\)) |
| [`grammar/openCypher.bnf`](grammar/openCypher.bnf) | Official BNF (Apache-2.0) |

## Cabinet — `cabinet/`

Durable store **behind** sessions. Index: [`cabinet/README.md`](cabinet/README.md).

| Doc | Role |
|-----|------|
| [`cabinet/agensgraph-buffer.md`](cabinet/agensgraph-buffer.md) | AgensGraph adapter: 0.7 live hydrate/flush; Fake + URL skip |
| [`cabinet/neo4j-buffer.md`](cabinet/neo4j-buffer.md) | MemNet ↔ Neo4j; live claimed (0.14); two namespaces (0.16) |

## Extras — `extras/`

Shipped extras and remaining design notes. Index: [`extras/README.md`](extras/README.md).

| Doc | Role |
|-----|------|
| [`extras/memnet-neighbourhood-reserve.md`](extras/memnet-neighbourhood-reserve.md) | Neighbourhood reserve (RSV shipped; this file is still the design note) |
| [`extras/memnet-host-search-nest.md`](extras/memnet-host-search-nest.md) | Host locators into MutateGate (0.17 `RagHostHook`) |
| [`extras/memnet-session-strata.md`](extras/memnet-session-strata.md) | Sessions as strata (not Layer); 0.15 catalog Snap |
| [`extras/memnet-security-multi-agent.md`](extras/memnet-security-multi-agent.md) | Session ACL / multi-agent (design) |

## Operations — `operations/`

Multitask MUST for this product. Index: [`operations/README.md`](operations/README.md).

| Doc | Role |
|-----|------|
| [`operations/multi-agent-sessions.md`](operations/multi-agent-sessions.md) | Multitask operating model (as-is 0.8; RSV + Path-B ingest shipped; full ACL modes to-be) |
| [`operations/honesty-c-wire-audit.md`](operations/honesty-c-wire-audit.md) | 0.19.5 hid / nickname emit audit |

Product skill: [`.cursor/skills/memnet-reference/`](../.cursor/skills/memnet-reference/). SysML trail: MN-REQ-12 → [`sysml-models/outputs/multitask-case-study.md`](../sysml-models/outputs/multitask-case-study.md).

---

## Applications — `application-notes/`

Shared contract: [`application-notes/README.md`](application-notes/README.md). Dialect: **GQL only**.

### System

| Doc | Role |
|-----|------|
| [`application-notes/system/llm-system-dev-multitask.md`](application-notes/system/llm-system-dev-multitask.md) | Multitask in `modelbasedPrj-*` |
| [`application-notes/system/llm-software-development.md`](application-notes/system/llm-software-development.md) | Multi-turn coding |
| [`application-notes/system/llm-sysml-v2-modeling.md`](application-notes/system/llm-sysml-v2-modeling.md) | SysML SSOT; relatives + sub-unit sessions |
| [`../sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../sysml-models/outputs/sysml-session-nest-cuts-case-study.md) | Evidence: Turns A–I |
| [`application-notes/system/llm-build-on-memnet.md`](application-notes/system/llm-build-on-memnet.md) | Custom MCP + skill pack |

### Domains

| Doc | Role |
|-----|------|
| [`application-notes/domains/llm-tech-docs-decomposition.md`](application-notes/domains/llm-tech-docs-decomposition.md) | Manual / SCPI decomposition |
| [`application-notes/domains/llm-circuit-schematic.md`](application-notes/domains/llm-circuit-schematic.md) | Circuit schematic (GQL; see case study) |
| [`application-notes/domains/llm-nodal-analysis-formulas.md`](application-notes/domains/llm-nodal-analysis-formulas.md) | Nodal method (GQL; see case study) |
| [`application-notes/domains/llm-daily-news.md`](application-notes/domains/llm-daily-news.md) | Batch RSS digest |
| [`application-notes/domains/llm-mud.md`](application-notes/domains/llm-mud.md) | Multiplayer MUD |

### Examples

| Doc | Role |
|-----|------|
| [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md) | InvAmp GQL-wire case study |
| [`application-notes/examples/inverting-amplifier-memnet.md`](application-notes/examples/inverting-amplifier-memnet.md) | InvAmp math SSOT |

**Multitask (application):** [`.cursor/skills/memnet-multitask/`](../.cursor/skills/memnet-multitask/); ops MUST from [`operations/multi-agent-sessions.md`](operations/multi-agent-sessions.md).
