# MemNet SysML models

Software-only **target** system model for the MemNet core engine and generic MemNet MCP server.

**Layout:** `sysml-models/` per [SYSTEM-REPO-LAYOUT.md](../../SYSTEM-REPO-LAYOUT.md) and repo [LAYOUT.md](../LAYOUT.md).

Design authority: rebuilt requirements + ADR-001 (GQL agent wire) + `docs/grammar/`. Today's `parts/common/memnet` and `parts/memnet-mcp` inform feasibility; see [outputs/system-design-notes.md](outputs/system-design-notes.md) for **target vs as-is**. Exam: [`docs/grammar/gql-model-exam.md`](../docs/grammar/gql-model-exam.md).

## Product framing (2026-08-13)

1. **MemNet = shared LLM memory** — session-scoped working-memory buffer; brand SharedLlmMemory.
2. **Session as SSOT handle** — pass a mission SOMETHING by **session id only** (`SessionHandoffById`); peers re-`pin_map`; chat never SSOT.
3. **Durable online GQL store** behind MemNet (`DurableBuffer` / AgensGraphAdapter) — planned **M2.5**; LLM↔store direct out of teach.
4. **Lead imports member working memory** — path A shared session → re-`pin_map` (no import); path B → `WorkingMemorySlice` through nested `ImportGuard` (cheap LLM) then `ImportAbsorb`. Product verb = **import** (not "session merge"). Cypher `MERGE` and micro id re-id `merge=true` are different.

**Sequence:** M1 (done) → M2 (engine GQL; remove as-is codecs) → **M2.5** (durable adapter) → M3.

## Packages

| File | Package | Role |
|------|---------|------|
| `models/connections.sysml` | `MemNetConnections` | SharedLlmMemory, SessionHandoff, WorkingMemorySlice, SessionImportRequest, ImportGuardDecision |
| `models/requirements.sysml` | `MemNetRequirements` | MN-REQ-00…12 (01.7/01.8, 06.4, 12.9–12.11 import + guard) |
| `models/deploy.sysml` | `MemNet` | Nested parts; Multitask lead/member spine |
| `models/behaviour.sysml` | `MemNetBehaviour` | HandoffById, SessionImportReceive, Multitask, M2.5 hydrate/flush |
| `models/verify.sysml` | `MemNetVerification` | MN-VER-12-G00 + S01…S12 |
| `models/root.sysml` | `ProjectMemNet` | Root imports (load last) |

## Nesting outline (target)

```text
MemNetSystem                                 // SharedLlmMemory product
├── MemNetCoreLibrary
│   ├── TransportBoundary
│   │   ├── InProcessEngine
│   │   │   └── AgentMemory                  // session-scoped working set
│   │   │       └── SessionLifecycle         // session id = SSOT handle
│   │   │           ├── GraphStore
│   │   │           ├── GqlCodec             // CIP/oC9 dialect authority
│   │   │           ├── PinMapShapedRead
│   │   │           ├── MutateGate
│   │   │           └── Schema / Caps / Walk / Housekeep / Snapshot
│   │   │               (TierACodec quarantined — remove in M2; not nested)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade                            // LLM <-> MemNet (GQL)
├── MemNetMcpServer                          // LLM <-> MemNet (MCP)
├── DurableBuffer                            // planned M2.5
│   └── AgensGraphAdapter                    // hydrate/flush <-> sessions
├── PinMapRoadmap
└── MultitaskOperatingModel
    ├── MultitaskCoordinator                 // team lead
    │   └── SessionImportReceive             // path B only
    │       ├── ImportGuard                  // cheap LLM soft review
    │       └── ImportAbsorb                 // hard gates + import + settle
    ├── MultitaskWorker                      // team member (handoff in + slice export)
    └── MultitaskSharedStoreBinding
```

**Story:** `SessionHandoffById` → (shared re-`pin_map` | `SessionImportReceive` → Guard → Absorb → Settle).

## Target subsystems

- **AgentMemory (SharedLlmMemory):** GraphStore, GqlCodec, PinMapShapedRead, MutateGate, SessionLifecycle
- **MCP / CLI:** LLM ↔ MemNet only (not DurableBuffer as primary)
- **DurableBuffer:** AgensGraphAdapter planned **M2.5**
- **Multitask:** nested lead import spine + member export; MN-REQ-12
- **Quarantined:** TierACodec (remove in M2); LegacyPipeImport
- **Out of scope:** novel-writer

## Case studies

| Study | Path |
|-------|------|
| Multitask Mode (GQL pins + optional import) | [outputs/multitask-case-study.md](outputs/multitask-case-study.md) |
| Session import + ImportGuard | [outputs/session-import-case-study.md](outputs/session-import-case-study.md) |
| Company analytical SSOT (`COM_*`) | [outputs/company-memory-case-study.md](outputs/company-memory-case-study.md) |
| Prose RPG beat (novel-cut patterns → GQL) | [outputs/prose-rpg-session-case-study.md](outputs/prose-rpg-session-case-study.md) |

## Live pin map (MN-REQ-04)

Turn-facing agent payload = **shaped subgraph** via **PinMapShapedRead** (`pin_map` wraps GQL).

## Property-graph ontology (first-class)

Node / Edge / Property / Label — [`docs/grammar/gql-wire-profile.md`](../docs/grammar/gql-wire-profile.md). **Agent wire = GQL only.** Dialect authority: openCypher CIP + oC9 (MemNet-gated subset).

## Validate

Prefer Cursor SysML v2 MCP `validate` on files under `models/`. Load order: `config.yaml`.

## Anchor

`TSK_model_memnet` — see [AGENT-CONTEXT.md](../AGENT-CONTEXT.md).
