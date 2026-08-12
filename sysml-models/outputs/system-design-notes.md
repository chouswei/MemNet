# MemNet - system design notes (from SysML)

Target architecture notes from nested `deploy.sysml` / `behaviour.sysml` / `connections.sysml` after **ADR-001**.
Novel-writer is out of scope.

**Exam:** [`../../docs/grammar/gql-model-exam.md`](../../docs/grammar/gql-model-exam.md).  
**Case studies:** [multitask](multitask-case-study.md) · [session-import](session-import-case-study.md) · [async-parallel](async-parallel-conflict-case-study.md) · [durable M2.5](durable-hydrate-flush-case-study.md) · [snapshot passport](snapshot-passport-case-study.md) · [SysML goldfish](sysml-modeling-goldfish-case-study.md) · [company-memory](company-memory-case-study.md) · [prose-rpg](prose-rpg-session-case-study.md).

## Product framing (2026-08-13)

1. **MemNet = shared LLM memory** (`SharedLlmMemory`).
2. **Session as SSOT handle** — `SessionHandoff` / `SessionHandoffById`; chat never SSOT.
3. **Durable GQL store behind MemNet** — `DurableBuffer` / `AgensGraphAdapter` planned **M2.5**.
4. **Lead imports member WM** - path A re-`pin_map` (skip import nest); path B `WorkingMemorySlice` -> nested `ImportGuard` -> `ImportAbsorb`. Product verb = **import**. Colloquial "session merge" means this import only (no SessionMerge* types). Cypher `MERGE` and micro `merge=true` are not this behaviour.

**Sequence:** M1 → M2 → **M2.5** → M3.

**Primary codec:** `GqlCodec` (**M2 shipped**) — dialect authority openCypher CIP tree + oC9 baseline + ISO GQL; MemNet-gated pin_map/mutate subset. As-is TierA codecs **retired** from product accept (archive/tests only).
**Composer:** `PinMapShapedRead` (as-is `PinMapComposer` / `query pin-map`) — shaped GQL subgraph emit.
**Dialect authority:** see [`../../docs/grammar/gql-wire-profile.md`](../../docs/grammar/gql-wire-profile.md) (External dialect authority) and ADR-001.

## Application patterns (not second products)

| Pattern | Item / study |
|---------|----------------|
| Company analytical SSOT | `CompanyAnalyticalSsot` → [company-memory-case-study.md](company-memory-case-study.md) |
| Prose RPG beat session | SharedLlmMemory + goldfish → [prose-rpg-session-case-study.md](prose-rpg-session-case-study.md) |
| Lead imports member WM | Nested ImportGuard/Absorb -> [session-import-case-study.md](session-import-case-study.md) |
| Async parallel Multitask | AsyncTaskDispatch + WorkerPool → [async-parallel-conflict-case-study.md](async-parallel-conflict-case-study.md) |
| Durable hydrate/flush | DurableBuffer M2.5 → [durable-hydrate-flush-case-study.md](durable-hydrate-flush-case-study.md) |
| Snapshot passport | SnapshotStore save/load → [snapshot-passport-case-study.md](snapshot-passport-case-study.md) |
| SysML modelling goldfish | TSK_model_memnet loop → [sysml-modeling-goldfish-case-study.md](sysml-modeling-goldfish-case-study.md) |

## Nesting outline

```text
MemNetSystem                                 // SharedLlmMemory
├── MemNetCoreLibrary
│   ├── TransportBoundary
│   │   ├── InProcessEngine → AgentMemory → SessionLifecycle
│   │   │     ├── GqlCodec / GraphStore / MutateGate / PinMapShapedRead / …
│   │   │     └── (TierACodec quarantined — not nested)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade
├── MemNetMcpServer
├── DurableBuffer → AgensGraphAdapter        // M2.5
├── PinMapRoadmap
└── MultitaskOperatingModel
    ├── MultitaskCoordinator                 // team lead
    │   ├── SessionHandoffEmit
    │   ├── AsyncTaskDispatch                // spawn N; end turn
    │   └── SessionImportReceive             // path B
    │       ├── ImportGuard                  // cheap LLM — soft review
    │       └── ImportAbsorb                 // hard gates + import + settle
    ├── WorkerPool
    │   └── MultitaskWorker[1..*]            // async parallel members
    └── MultitaskSharedStoreBinding
```

**How lead gets member WM:** shared session → re-`pin_map`; else export slice → `ImportGuard` → `ImportAbsorb` into lead session.

**Async parallel:** disjoint `WorkerWriteScope` or separate sessions; `EvEndCoordinatorTurn`; host-driven `EvWorkerReturn` (MN-REQ-12.12). Engine does not enforce scope (doctrineAsIs).

## Behaviours

| State machine | Role |
|---------------|------|
| `GoldfishLoop` / `MutateWithNew` / `SessionLifecycleStates` | Engine goldfish |
| `SessionHandoffById` | Pass session id (vs `EvDumpGraphInChat`) |
| `SessionImportReceive` | path A repin; path B Guard → Absorb → Settle (vs `EvImportFromChat`) |
| `ParentTaskLifecycle` / `WorkerScopedTurn` / `MultitaskMissionCycle` | MN-REQ-12 |
| `DurableHydrateFlushRoadmap` | M2.5 (not shipped) |

## Interfaces (selected)

| Connection | From → To | Status |
|------------|-----------|--------|
| SessionHandoffFlow | Coordinator → Worker | Target |
| WorkingMemorySliceFlow | Worker → `coordinator.importReceive.guard` | Target path B |
| ImportGuardDecisionFlow | Guard → Absorb (nested) | Target |
| DurableHydrate/FlushFlow | AgensGraphAdapter ↔ SessionLifecycle | Roadmap M2.5 |
| InProcess / TCP flows | MCP/CLI ↔ engine | Wired |

## Target ↔ as-is modules (engine)

| Target part | Today's module(s) | Status |
|-------------|-------------------|--------|
| GraphStore | `mem_store.py` + `graph_store.py` | Aliased |
| GqlCodec | `gql.py` / `gql_codec.py` | **Shipped (M2)** |
| (as-is line codec) | `tier_a.py` / `tier_a_codec.py` | Retired from product accept (M2) |
| PinMapShapedRead | `pin_map_composer.py` | Shaped GQL subgraph emit (M2) |
| MutateGate | `mutate_gate.py` | GQL primary; Layer/Tier A rejected |
| AgensGraphAdapter | — | Planned **M2.5** |

## Satisfy (MN-REQ-12 import + async)

| Leaf | Parts |
|------|-------|
| 12.9 LeadOwnsSessionImport | Coordinator, SessionImportReceive, ImportAbsorb, SessionLifecycle |
| 12.10 NoChatOrWholeStoreImport | Coordinator, Worker, ImportGuard, ImportAbsorb |
| 12.11 CheapLlmImportGuardSoft | ImportGuard, SessionImportReceive |
| 12.12 HostDrivenAsyncParallel | AsyncTaskDispatch, Coordinator, WorkerPool, MultitaskWorker |

## Gaps

- **M1:** GQL wire profile — **done**
- **M2:** Engine/MCP GQL accept + shaped pin_map emit; Layer/Tier A retired — **done**
- **M2.5:** AgensGraph adapter — plan only ([durable-hydrate-flush-case-study.md](durable-hydrate-flush-case-study.md))
- **M3:** In-repo playbook / app-note GQL rewrite (plan)
- ImportGuard / ImportAbsorb — doctrine nested; engine not claimed shipped
- WorkerWriteScope — doctrineAsIs; engine does not enforce (see async-parallel study)
- MN-REQ-12.7 ACL/reserve/ingest still to-be
- `LocalIpcFlow` when LocalIpcGateway is implemented
- PinMapIngest_* deterministic locators
