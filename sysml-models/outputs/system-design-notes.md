# MemNet - system design notes (from SysML)

Target architecture notes for nested `deploy.sysml` / `behaviour.sysml` / `connections.sysml` after **ADR-001**.
Requirements and grammar doctrine win over today's Python layout. Novel-writer is out of scope.

**Exam:** [`../../docs/grammar/gql-model-exam.md`](../../docs/grammar/gql-model-exam.md).  
**GQL case study:** [`../../docs/application-notes/examples/inverting-amplifier-gql-case-study.md`](../../docs/application-notes/examples/inverting-amplifier-gql-case-study.md).

**Primary term:** **pin map** = shaped subgraph read wrapping GQL (Write = display redefined).  
**Items:** `LivePinMap` / `ShapedSubgraph` (turn payload), `GqlWireBatch` (mutate). Historical Layer batch types are **not** product doctrine.  
**Composer:** `PinMapShapedRead` (as-is `PinMapComposer` / `query_warm`).  
**Primary codec:** `GqlCodec`. As-is `tier_a` codecs = **implementation lag → remove in M2** (not an accept teach path).  
**Dialect authority:** `GqlCodec` / wire profile are **openCypher CIP + oC9**-backed (family refs); ISO GQL for GQL-native features; agent surface stays MemNet-gated — not “implement every CIP”. See [`../../docs/grammar/gql-wire-profile.md`](../../docs/grammar/gql-wire-profile.md) (External dialect authority) and ADR-001.  
**Removed from target nest:** standing Tier B pipe; Layer/Tier A teach. **Deprecated stub:** `LegacyPipeImport`.

## Mission

**MemNet = Net of Memory** — durable **Node | Edge** property-graph working memory between LLM pipelines and data search. Agent I/O is **openCypher-shaped GQL only** with **shaped pin_map** emit ([`../../docs/grammar/gql-wire-profile.md`](../../docs/grammar/gql-wire-profile.md)).

## Nesting outline

```text
MemNetSystem
├── MemNetCoreLibrary
│   ├── TransportBoundary
│   │   ├── InProcessEngine
│   │   │   └── AgentMemory
│   │   │       └── SessionLifecycle
│   │   │           ├── CapsPolicy / SchemaRegistry
│   │   │           ├── GqlCodec                 // 1.x primary
│   │   │           ├── GraphStore
│   │   │           ├── MutateGate → IdAllocator
│   │   │           ├── PinMapShapedRead
│   │   │           ├── WalkQuery / HousekeepSettle / SnapshotStore
│   │   │           └── (as-is TierACodec → delete in M2)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade
├── MemNetMcpServer → McpFacade / ServeBridge / LawSeedHelper
├── DurableBuffer → AgensGraphAdapter            // planned M2.5
├── PinMapRoadmap → PinMapIngest_*
└── MultitaskOperatingModel
```

Code module map: [`parts/README.md`](../../parts/README.md).

## Behaviours

| State machine | Role |
|---------------|------|
| `SessionLifecycleStates` | closed → opening/loading → active → saving → closed |
| `GoldfishLoop` | awaitingPinMap → presentingPinMap → applyingMutate → settling |
| `MutateWithNew` | idle → parsing → minting → committing |
| `PinMapIngestCycle` | pinIdle → selectingPins → projecting |
| `ParentTaskLifecycle` / `WorkerScopedTurn` / `MultitaskMissionCycle` | MN-REQ-12 |

## Interfaces

| Connection | From → To | Status |
|------------|-----------|--------|
| InProcessFlow | McpFacade/CliFacade → InProcessEngine | **Wired** (primary) |
| ServeCommandFlow / JsonEnvelopeFlow | Facades ↔ TcpServeBridge | **Wired** (Multitask) |
| LocalIpcFlow | CliFacade.ipcOut → LocalIpcGateway | **Unallocated stub** |
| GraphRecordFlow | GqlCodec → MutateGate → GraphStore | **Target wired** |
| LivePinMapFlow / ShapedSubgraphFlow / GqlWireFlow | PinMapShapedRead / facades | **Target** |
| SessionSnapshotFlow | SnapshotStore ↔ file | MN-REQ-01 |
| PinMapFlow | PinMapIngest_* | MN-REQ-11 stubs |

## As-is → target map

| Target part | Today's module(s) | Status |
|-------------|-------------------|--------|
| GraphStore | `mem_store.py` + `graph_store.py` | Aliased |
| GqlCodec | *(target; M2)* | Not shipped |
| (as-is line codec) | `tier_a.py` / `tier_a_codec.py` | **Remove in M2** — not doctrine |
| PinMapShapedRead | `pin_map_composer.py` | As-is emit; target shaped GQL |
| MutateGate | `mutate_gate.py` | GQL path in M2 |
| AgensGraphAdapter | — | Planned **M2.5** (after M2) |
| MultitaskOperatingModel | agent doctrine | As-is MN-REQ-12 |

## Satisfy coverage

| Group | Coverage |
|-------|----------|
| MN-REQ-00 | `MemNetSystem` |
| MN-REQ-01 | SessionLifecycle, SnapshotStore, CliFacade, McpFacade |
| MN-REQ-02 | GraphStore, GqlCodec, PinMapShapedRead, WalkQuery, MutateGate, SchemaRegistry, McpFacade |
| MN-REQ-03 | GraphStore, MutateGate, IdAllocator |
| MN-REQ-04 | PinMapShapedRead, WalkQuery, HousekeepSettle |
| MN-REQ-05 | CapsPolicy |
| MN-REQ-06 | InProcessEngine, LocalIpcGateway, TcpServeBridge, SessionLifecycle, McpFacade |
| MN-REQ-07 | McpFacade, LawSeedHelper |
| MN-REQ-08 | GqlCodec, CliFacade, McpFacade, PinMapShapedRead |
| MN-REQ-09 | GqlCodec, CliFacade, McpFacade |
| MN-REQ-10 | GraphStore, CapsPolicy, PinMapShapedRead, CliFacade, GqlCodec, IdAllocator, McpFacade |
| MN-REQ-11 | PinMapIngest_* stubs + PinMapShapedRead + IdAllocator + SnapshotStore |
| MN-REQ-12 | MultitaskCoordinator, MultitaskWorker, MultitaskSharedStoreBinding, TcpServeBridge, ServeBridge |

## Gaps / next steps

- **M1:** GQL wire profile — **done** ([`../../docs/grammar/gql-wire-profile.md`](../../docs/grammar/gql-wire-profile.md)); Layer docs archived
- **M2:** Engine/MCP GQL accept + shaped pin_map emit; **remove** as-is Layer/Tier A codec from product path
- **M2.5:** Durable online GQL store adapter (AgensGraph hydrate/flush) — [`../../docs/grammar/agensgraph-buffer.md`](../../docs/grammar/agensgraph-buffer.md); plan only
- As-is Python still on old line codec — implementation lag until M2 (not dual-teach)
- `LocalIpcFlow` when LocalIpcGateway is implemented
- PinMapIngest_* deterministic locators
- **To-be:** session ACL, neighbourhood reserve, Path-B ingest — MN-REQ-12.7
