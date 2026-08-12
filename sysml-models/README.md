# MemNet SysML models

Software-only **target** system model for the MemNet core engine and generic MemNet MCP server.

**Layout:** `sysml-models/` per [SYSTEM-REPO-LAYOUT.md](../../SYSTEM-REPO-LAYOUT.md) and repo [LAYOUT.md](../LAYOUT.md).

Design authority: rebuilt requirements + ADR-001 (GQL agent wire) + `docs/grammar/`. Today's `parts/common/memnet` and `parts/memnet-mcp` inform feasibility; see [outputs/system-design-notes.md](outputs/system-design-notes.md) for **target vs as-is**. Exam: [`docs/grammar/gql-model-exam.md`](../docs/grammar/gql-model-exam.md).

## Product framing (2026-08-13)

1. **MemNet = shared LLM memory** — session-scoped working-memory buffer; brand SharedLlmMemory.
2. **Session as SSOT handle** — pass a mission SOMETHING by **session id only** (`SessionHandoffById`); peers re-`pin_map`; chat never SSOT.
3. **Durable online GQL store** behind MemNet (`DurableBuffer` / AgensGraphAdapter) — **M2.5** client hydrate/flush landed; live AgensGraph path needs external cabinet (not claimed verified). LLM↔store direct out of teach.
4. **Lead imports member working memory** - path A shared session -> re-`pin_map` (no second store); path B -> `WorkingMemorySlice` through nested `ImportGuard` (cheap LLM soft) then `ImportAbsorb` (engine hard). Product verb = **import**. Colloquial "session merge" means this import only (no SessionMerge* types). Distinct from Cypher `MERGE` and micro id re-id `merge=true`.

**Sequence:** M1 (done) → M2 (done) → **M2.5** (client landed; live cabinet deferred) → **M3** (in-repo playbook/app-note GQL rewrite).

## Packages

| File | Package | Role |
|------|---------|------|
| `models/connections.sysml` | `MemNetConnections` | SharedLlmMemory, SessionHandoff, WorkingMemorySlice, SessionImportRequest, ImportGuardDecision |
| `models/requirements.sysml` | `MemNetRequirements` | MN-REQ-00…12 (01.7/01.8, 06.4, 12.9–12.12 import + guard + async) |
| `models/deploy.sysml` | `MemNet` | Nested parts; Multitask lead/dispatch/WorkerPool spine |
| `models/behaviour.sysml` | `MemNetBehaviour` | HandoffById, SessionImportReceive, Multitask async, M2.5 hydrate/flush |
| `models/verify.sysml` | `MemNetVerification` | MN-VER-12-G00 + S01…S13 |
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
│   │   │               (TierACodec retired — M2 done; not nested)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade                            // LLM <-> MemNet (GQL)
├── MemNetMcpServer                          // LLM <-> MemNet (MCP)
├── DurableBuffer                            // planned M2.5
│   └── AgensGraphAdapter                    // hydrate/flush <-> sessions
├── PinMapRoadmap
└── MultitaskOperatingModel
    ├── MultitaskCoordinator                 // team lead
    │   ├── SessionHandoffEmit
    │   ├── AsyncTaskDispatch                // spawn N; end turn
    │   └── SessionImportReceive             // path B only
    │       ├── ImportGuard                  // cheap LLM soft review
    │       └── ImportAbsorb                 // hard gates + import + settle
    ├── WorkerPool
    │   └── MultitaskWorker[1..*]            // async parallel members
    └── MultitaskSharedStoreBinding
```

**Story:** `SessionHandoffById` → `AsyncTaskDispatch` (end turn) → workers async → host `EvWorkerReturn` → (shared re-`pin_map` | `SessionImportReceive` → Guard → Absorb → Settle).

## Target subsystems

- **AgentMemory (SharedLlmMemory):** GraphStore, GqlCodec, PinMapShapedRead, MutateGate, SessionLifecycle
- **MCP / CLI:** LLM ↔ MemNet only (not DurableBuffer as primary)
- **DurableBuffer:** AgensGraphAdapter planned **M2.5**
- **Multitask:** nested lead handoff + AsyncTaskDispatch + WorkerPool + import spine; MN-REQ-12
- **Retired / quarantined:** TierACodec (M2 done); LegacyPipeImport
- **Out of scope:** novel-writer

## Case studies

Two shelves (detail + principles: [outputs/README.md](outputs/README.md)). **Product canon** = MemNet mechanism. **Application examples** = patterns on SharedLlmMemory — not extra product cores.

### Product canon

| Study | Path |
|-------|------|
| Goldfish chat desync → re-pin | [outputs/goldfish-chat-desync-case-study.md](outputs/goldfish-chat-desync-case-study.md) |
| Multitask Mode (GQL pins + optional import) | [outputs/multitask-case-study.md](outputs/multitask-case-study.md) |
| Async parallel (canon companion) | [outputs/async-parallel-conflict-case-study.md](outputs/async-parallel-conflict-case-study.md) |
| TCP / streamable-http shared Multitask (transport) | [outputs/tcp-shared-multitask-case-study.md](outputs/tcp-shared-multitask-case-study.md) |
| Session import + ImportGuard (path B detail) | [outputs/session-import-case-study.md](outputs/session-import-case-study.md) |
| Snapshot passport | [outputs/snapshot-passport-case-study.md](outputs/snapshot-passport-case-study.md) |
| Durable hydrate/flush (M2.5) | [outputs/durable-hydrate-flush-case-study.md](outputs/durable-hydrate-flush-case-study.md) |
| `NEW` mint batch (mutate discipline) | [outputs/new-mint-batch-case-study.md](outputs/new-mint-batch-case-study.md) |

### Application examples (on SharedLlmMemory)

| Study | Path |
|-------|------|
| Company analytical SSOT (`COM_*`) | [outputs/company-memory-case-study.md](outputs/company-memory-case-study.md) |
| Evidence Centre (ai-investor librarian / MissionDock) | [outputs/evidence-centre-case-study.md](outputs/evidence-centre-case-study.md) |
| Prose RPG beat (novel-cut patterns → GQL) | [outputs/prose-rpg-session-case-study.md](outputs/prose-rpg-session-case-study.md) |
| Inverting amp bind vs relation (ego `CST_U1`) | [outputs/inverting-amp-bind-relation-case-study.md](outputs/inverting-amp-bind-relation-case-study.md) |
| Tech docs / SCPI atomisation | [outputs/tech-docs-scpi-case-study.md](outputs/tech-docs-scpi-case-study.md) |
| SysML modelling goldfish (MBSE meta) | [outputs/sysml-modeling-goldfish-case-study.md](outputs/sysml-modeling-goldfish-case-study.md) |

## Live pin map (MN-REQ-04)

Turn-facing agent payload = **shaped subgraph** via **PinMapShapedRead** (`pin_map` wraps GQL).

## Property-graph ontology (first-class)

Node / Edge / Property / Label — [`docs/grammar/gql-wire-profile.md`](../docs/grammar/gql-wire-profile.md). **Agent wire = GQL only.** Dialect authority: openCypher CIP + oC9 (MemNet-gated subset).

## Validate

Prefer Cursor SysML v2 MCP `validate` on files under `models/`. Load order: `config.yaml`.

## Anchor

`TSK_model_memnet` — see [AGENT-CONTEXT.md](../AGENT-CONTEXT.md).
