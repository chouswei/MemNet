# MemNet - system design notes (from SysML)

Target architecture notes for `deploy.sysml` / `behaviour.sysml` / `connections.sysml`.
Requirements and grammar doctrine win over today's Python layout. Novel-writer is out of scope.

**Primary term:** **pin map** (live turn-facing ego digest).  
**Items:** `LivePinMap` (turn payload), `PinMapProjection` (MN-REQ-11 export/ingest).  
**Composer:** `PinMapComposer` (legacy CLI/MCP `query_warm` = deprecated alias).  
**Removed from target:** `WarmComposer`, `TierBBridge` / standing Tier B pipe.  
**Deprecated stub:** `LegacyPipeImport` (one-shot `@TAG` pipe import; not nested in `MemNetSystem`).

## Mission

**MemNet = Net of Memory** — durable **NODE | EDGE** network between LLM pipelines and data search; aims to save wall-clock time and tokens while keeping factual accuracy. Agent I/O is Tier A Write=display both ways; humans inspect via canonical parser (ANTLR path).

## Target part tree

```text
MemNetSystem
├── MemNetCoreLibrary              → parts/common/memnet (evolving)
│   ├── TierACodec                 // SSOT parse/emit Write=display
│   ├── InProcessEngine            // primary binding (MN-REQ-06.1)
│   │   └── SessionLifecycle
│   │       ├── CapsPolicy
│   │       ├── SchemaRegistry
│   │       ├── TierACodec
│   │       ├── GraphStore
│   │       ├── MutateGate
│   │       │   └── IdAllocator    // NEW (goldfish) | pin-key (ingest)
│   │       ├── PinMapComposer     // LivePinMap emit
│   │       ├── WalkQuery
│   │       ├── HousekeepSettle
│   │       └── SnapshotStore
│   ├── LocalIpcGateway            // 06.2 — part present; LocalIpcFlow UNALLOCATED
│   ├── TcpServeBridge             // TCP localhost migration (06.3)
│   └── CliFacade                  // ipcOut ready; not wired on MemNetSystem yet
├── MemNetMcpServer                → parts/memnet-mcp
│   ├── McpFacade                  // in-process by default
│   ├── ServeBridge                // optional TCP client
│   └── LawSeedHelper
└── PinMapRoadmap
    ├── PinMapIngest_Sysml
    ├── PinMapIngest_Codebase
    ├── PinMapIngest_PcbaAto       // .ato == PCBA
    └── PinMapIngest_SkillsRules

(not nested) LegacyPipeImport     // DEPRECATED import-once
```

## Behaviours

| State machine | Role |
|---------------|------|
| `SessionLifecycleStates` | closed → opening/loading → active → saving → closed |
| `GoldfishLoop` | awaitingPinMap → presentingPinMap → applyingMutate → settling |
| `MutateWithNew` | idle → parsing → minting (no-op if no NEW) → committing |
| `PinMapIngestCycle` | pinIdle → selectingPins → projecting (deterministic locators; reject client NEW) |

## Interfaces

| Connection | From → To | Status |
|------------|-----------|--------|
| InProcessFlow | McpFacade/CliFacade → InProcessEngine | **Wired** (primary) |
| ServeCommandFlow / JsonEnvelopeFlow | Facades ↔ TcpServeBridge | **Wired** (migration) |
| LocalIpcFlow | CliFacade.ipcOut → LocalIpcGateway | **Unallocated stub** until IPC implemented |
| GraphRecordFlow | TierACodec → MutateGate → GraphStore | Nested under SessionLifecycle |
| LivePinMapFlow / TierAFlow | PinMapComposer / facades | Live pin map Write=display |
| SessionSnapshotFlow | SnapshotStore ↔ file | MN-REQ-01 |
| PinMapFlow | PinMapIngest_* | MN-REQ-11 selective pins |

## As-is → target map

| Target part | Today's module(s) | Gap |
|-------------|-------------------|-----|
| GraphStore | `mem_store.py`, `models.py` | Clarity rename |
| SchemaRegistry | `tag_map.py`, `fixed_tags.py` | Positional TagMap is legacy |
| TierACodec | `tier_a.py` | Pure-Python twin; ANTLR deferred |
| LegacyPipeImport | `wire.py` pipe | **Not target** — import-once only |
| IdAllocator | (pending) | NEW goldfish + deterministic pin keys |
| MutateGate | cli ingest | Tier A + NEW (skip mint if none) |
| PinMapComposer | `query_warm` + output | Emit Tier A `LivePinMap` |
| InProcessEngine | MCP inline / cli | Primary |
| LocalIpcGateway | — | Stub; **LocalIpcFlow unallocated** |
| TcpServeBridge | `serve.py` | Migration fallback |
| PinMapIngest_* | skills / future | Roadmap; no client NEW for source pins |

## Satisfy coverage

| Group | Coverage |
|-------|----------|
| MN-REQ-00 | `MemNetSystem` |
| MN-REQ-01 | SessionLifecycle, SnapshotStore, CliFacade, McpFacade |
| MN-REQ-02 | GraphStore, TierACodec, PinMapComposer, WalkQuery, MutateGate, SchemaRegistry, McpFacade |
| MN-REQ-03 | GraphStore, MutateGate, IdAllocator |
| MN-REQ-04 | PinMapComposer, WalkQuery, HousekeepSettle |
| MN-REQ-05 | CapsPolicy |
| MN-REQ-06 | InProcessEngine, LocalIpcGateway (stub), TcpServeBridge, SessionLifecycle, McpFacade |
| MN-REQ-07 | McpFacade, LawSeedHelper |
| MN-REQ-08 | TierACodec, CliFacade, McpFacade, PinMapComposer |
| MN-REQ-09 | TierACodec, CliFacade, McpFacade |
| MN-REQ-10 | GraphStore, CapsPolicy, PinMapComposer, CliFacade, TierACodec, IdAllocator, McpFacade |
| MN-REQ-11 | PinMapIngest_* + PinMapComposer (11.13) + IdAllocator (11.16) + SnapshotStore |

## Gaps / next steps

- PinMapComposer Tier A `LivePinMap` emit (`query_warm` alias until rename)
- Allocate `LocalIpcFlow` when LocalIpcGateway is implemented
- PinMapIngest_* deterministic locators (reject client NEW on projecting)
- Optional ANTLR codegen; LegacyPipeImport one-shot only
