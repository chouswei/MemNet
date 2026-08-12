# MemNet - system design notes (from SysML)

Target architecture notes for nested `deploy.sysml` / `behaviour.sysml` / `connections.sysml` after **ADR-001**.
Requirements and grammar doctrine win over today's Python layout. Novel-writer is out of scope.

**Exam:** [`../../docs/grammar/gql-model-exam.md`](../../docs/grammar/gql-model-exam.md).  
**GQL case study:** [`../../docs/application-notes/examples/inverting-amplifier-gql-case-study.md`](../../docs/application-notes/examples/inverting-amplifier-gql-case-study.md).  
**Multitask case study:** [`multitask-case-study.md`](multitask-case-study.md).  
**Session merge case study:** [`session-merge-case-study.md`](session-merge-case-study.md).

## Product framing (2026-08-13)

1. **MemNet = shared LLM memory** (`SharedLlmMemory`) — session-scoped goldfish buffer for multi-agent work.
2. **Session as SSOT handle** — pass a mission SOMETHING by **session id only** (`SessionHandoff` / `SessionHandoffById`); peers re-`pin_map`; chat never SSOT.
3. **Durable GQL store behind MemNet** — `DurableBuffer` / `AgensGraphAdapter` planned **M2.5**; LLM ↔ store direct out of default teach.
4. **Session merge = lead receives member WM** — path A shared re-`pin_map`; path B bounded `WorkingMemorySlice` (`SessionMergeReceive`).

**Sequence:** M1 (done) → M2 (engine GQL; remove as-is codecs) → **M2.5** (durable adapter) → M3.

**Primary term:** **pin map** = shaped subgraph read wrapping GQL (Write = display redefined).  
**Items:** `LivePinMap` / `ShapedSubgraph` / `GqlWireBatch`; also `SessionHandoff`, `WorkingMemorySlice`, `SessionMergeRequest`. Historical Layer batches are **quarantined** (remove in M2) — not accept doctrine.  
**Composer:** `PinMapShapedRead` (as-is `PinMapComposer` / `query_warm`).  
**Primary codec:** `GqlCodec` — dialect authority openCypher **CIP + oC9** (MemNet-gated subset); ISO GQL for GQL-native features. See wire profile External dialect authority.  
**Removed from target nest:** TierACodec accept path; standing Tier B pipe. **Deprecated stub:** `LegacyPipeImport`.

## Mission

**MemNet = Net of Memory / shared LLM memory** — durable **Node | Edge** property-graph working memory between LLM pipelines and data search. Agent I/O is **openCypher-shaped GQL only** with **shaped pin_map** emit ([`../../docs/grammar/gql-wire-profile.md`](../../docs/grammar/gql-wire-profile.md)).

## Nesting outline

```text
MemNetSystem                                 // SharedLlmMemory
├── MemNetCoreLibrary
│   ├── TransportBoundary
│   │   ├── InProcessEngine
│   │   │   └── AgentMemory
│   │   │       └── SessionLifecycle         // session id = SSOT handle
│   │   │           ├── CapsPolicy / SchemaRegistry
│   │   │           ├── GqlCodec             // CIP/oC9 authority
│   │   │           ├── GraphStore
│   │   │           ├── MutateGate → IdAllocator
│   │   │           ├── PinMapShapedRead
│   │   │           ├── WalkQuery / HousekeepSettle / SnapshotStore
│   │   │           └── (TierACodec quarantined — remove in M2; not nested)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade                            // LLM <-> MemNet
├── MemNetMcpServer → McpFacade / ServeBridge / LawSeedHelper
├── DurableBuffer → AgensGraphAdapter        // planned M2.5 hydrate/flush
├── PinMapRoadmap → PinMapIngest_*
└── MultitaskOperatingModel                  // handoff + SessionMergeReceive
```

Code module map: [`parts/README.md`](../../parts/README.md).

## Behaviours

| State machine | Role |
|---------------|------|
| `SessionLifecycleStates` | closed → opening/loading → active → saving → closed |
| `GoldfishLoop` | awaitingPinMap → presentingPinMap → applyingMutate → settling |
| `MutateWithNew` | idle → parsing → minting → committing |
| `PinMapIngestCycle` | pinIdle → selectingPins → projecting |
| `ParentTaskLifecycle` / `WorkerScopedTurn` / `MultitaskMissionCycle` | MN-REQ-12 Multitask |
| `SessionHandoffById` | deliver session id → worker pin_map → scoped mutate (vs `EvDumpGraphInChat`) |
| `SessionMergeReceive` | path A re-pin_map; path B slice absorb + settle (vs `EvMergeFromChat`) |
| `DurableHydrateFlushRoadmap` | M2.5 hydrate/flush (not shipped) |

## Interfaces

| Connection | From → To | Status |
|------------|-----------|--------|
| InProcessFlow | McpFacade/CliFacade → InProcessEngine | **Wired** (primary) |
| ServeCommandFlow / JsonEnvelopeFlow | Facades ↔ TcpServeBridge | **Wired** (Multitask) |
| LocalIpcFlow | CliFacade.ipcOut → LocalIpcGateway | **Unallocated stub** |
| GraphRecordFlow | GqlCodec → MutateGate → GraphStore | **Target wired** |
| LivePinMapFlow / ShapedSubgraphFlow / GqlWireFlow | PinMapShapedRead / facades | **Target** |
| SessionHandoffFlow | MultitaskCoordinator → MultitaskWorker | **Target** |
| WorkingMemorySliceFlow | MultitaskWorker → MultitaskCoordinator | **Target** (path B merge) |
| DurableHydrateFlow / DurableFlushFlow | AgensGraphAdapter ↔ SessionLifecycle | **Roadmap M2.5** |
| SessionSnapshotFlow | SnapshotStore ↔ file | MN-REQ-01 |
| PinMapFlow | PinMapIngest_* | MN-REQ-11 stubs |

## As-is → target map

| Target part | Today's module(s) | Status |
|-------------|-------------------|--------|
| GraphStore | `mem_store.py` + `graph_store.py` | Aliased |
| GqlCodec | *(target; M2)* | Not shipped; CIP/oC9 authority modelled |
| (as-is line codec) | `tier_a.py` / `tier_a_codec.py` | **Remove in M2** — quarantined |
| PinMapShapedRead | `pin_map_composer.py` | As-is emit; target shaped GQL |
| MutateGate | `mutate_gate.py` | GQL path in M2 |
| AgensGraphAdapter | — | Planned **M2.5** (after M2) |
| MultitaskOperatingModel | agent doctrine | As-is MN-REQ-12 + merge doctrine |
| SessionMergeReceive | — | Doctrine / behaviour modelled; engine not claimed |

## Satisfy coverage

| Group | Coverage |
|-------|----------|
| MN-REQ-00 | `MemNetSystem` |
| MN-REQ-01 | SessionLifecycle (+ 01.7/01.8), SnapshotStore, CliFacade, McpFacade, MultitaskCoordinator/Worker |
| MN-REQ-02 | GraphStore, GqlCodec, PinMapShapedRead, WalkQuery, MutateGate, SchemaRegistry, McpFacade |
| MN-REQ-03 | GraphStore, MutateGate, IdAllocator |
| MN-REQ-04 | PinMapShapedRead, WalkQuery, HousekeepSettle |
| MN-REQ-05 | CapsPolicy |
| MN-REQ-06 | InProcessEngine, LocalIpcGateway, TcpServeBridge, SessionLifecycle, McpFacade, DurableBuffer (06.4) |
| MN-REQ-07 | McpFacade, LawSeedHelper |
| MN-REQ-08 | GqlCodec, CliFacade, McpFacade, PinMapShapedRead |
| MN-REQ-09 | GqlCodec, CliFacade, McpFacade |
| MN-REQ-10 | GraphStore, CapsPolicy, PinMapShapedRead, CliFacade, GqlCodec, IdAllocator, McpFacade |
| MN-REQ-11 | PinMapIngest_* stubs + PinMapShapedRead + IdAllocator + SnapshotStore |
| MN-REQ-12 | MultitaskCoordinator/Worker/SharedStoreBinding, TcpServeBridge, ServeBridge, SessionLifecycle (12.9/12.10) |

## Gaps / next steps

- **M1:** GQL wire profile — **done**; Layer docs archived; CIP/oC9 cited as dialect authority
- **M2:** Engine/MCP GQL accept + shaped pin_map emit; **remove** as-is Tier A codec from product path
- **M2.5:** Durable online GQL store adapter (AgensGraph hydrate/flush) — [`../../docs/grammar/agensgraph-buffer.md`](../../docs/grammar/agensgraph-buffer.md); plan only
- SessionMergeReceive engine enforcement — doctrine modelled; not claimed shipped
- As-is Python still on old line codec — implementation lag until M2 (not dual-teach)
- `LocalIpcFlow` when LocalIpcGateway is implemented
- PinMapIngest_* deterministic locators
- **To-be:** session ACL, neighbourhood reserve, Path-B ingest — MN-REQ-12.7
