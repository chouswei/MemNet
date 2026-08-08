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
├── MemNetCoreLibrary              → parts/common/memnet
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
│   ├── LocalIpcGateway            // 06.2 — stub; LocalIpcFlow UNALLOCATED
│   ├── TcpServeBridge             // TCP localhost migration (06.3)
│   └── CliFacade                  // ipcOut ready; not wired on MemNetSystem yet
├── MemNetMcpServer                → parts/memnet-mcp
│   ├── McpFacade                  // in-process by default
│   ├── ServeBridge                // optional TCP client
│   └── LawSeedHelper
├── PinMapRoadmap
│   ├── PinMapIngest_Sysml
│   ├── PinMapIngest_Codebase
│   ├── PinMapIngest_PcbaAto       // .ato == PCBA
│   └── PinMapIngest_SkillsRules
└── MultitaskOperatingModel        // MN-REQ-12 agent doctrine
    ├── MultitaskCoordinator
    ├── MultitaskWorker
    └── MultitaskSharedStoreBinding

(not nested) LegacyPipeImport     // DEPRECATED import-once
```

Code module map: [`parts/README.md`](../../parts/README.md).

## Behaviours

| State machine | Role |
|---------------|------|
| `SessionLifecycleStates` | closed → opening/loading → active → saving → closed |
| `GoldfishLoop` | awaitingPinMap → presentingPinMap → applyingMutate → settling |
| `MutateWithNew` | idle → parsing → minting (no-op if no NEW) → committing |
| `PinMapIngestCycle` | pinIdle → selectingPins → projecting (deterministic locators; reject client NEW) |
| `ParentTaskLifecycle` | taskAbsent → taskMinted → taskScoped → taskDelegated → taskReconciling → taskSettled (TSK_*; relevant tasks) |
| `WorkerScopedTurn` | workerAwaitingPinMap → workerPresentingPinMap → workerApplyingScopedMutate → workerTurnDone |
| `MultitaskMissionCycle` | missionIdle → parentPreparing → workersDelegated → parentReconciling → missionComplete (MN-REQ-12.8 gate) |

## Interfaces

| Connection | From → To | Status |
|------------|-----------|--------|
| InProcessFlow | McpFacade/CliFacade → InProcessEngine | **Wired** (primary; MCP default; single-agent) |
| ServeCommandFlow / JsonEnvelopeFlow | Facades ↔ TcpServeBridge | **Wired** (`MEMNET_MCP_TRANSPORT=tcp`; Multitask shared store) |
| LocalIpcFlow | CliFacade.ipcOut → LocalIpcGateway | **Unallocated stub** |
| GraphRecordFlow | TierACodec → MutateGate → GraphStore | **Wired** via MutateGate |
| LivePinMapFlow / TierAFlow | PinMapComposer / facades | **Wired** (`query warm` → Tier A) |
| SessionSnapshotFlow | SnapshotStore ↔ file | MN-REQ-01 (still pipe snapshot body) |
| PinMapFlow | PinMapIngest_* | MN-REQ-11 stubs only |

## As-is → target map

| Target part | Today's module(s) | Status (this notch) |
|-------------|-------------------|---------------------|
| GraphStore | `mem_store.py` + `graph_store.py` alias | Aliased |
| SchemaRegistry | `tag_map.py` + `schema_registry.py` | Aliased; TagMap still positional for pipe |
| TierACodec | `tier_a.py` / `tier_a_codec.py` | Pure-Python twin; ANTLR deferred |
| LegacyPipeImport | `legacy_pipe_import.py` | Import-once path inside MutateGate |
| IdAllocator | `id_allocator.py` | Wired through MutateGate on Tier A |
| MutateGate | `mutate_gate.py` | Tier A + legacy pipe; NEW mint |
| PinMapComposer | `pin_map_composer.py` | `query warm` emits Tier A LivePinMap |
| InProcessEngine | `in_process_engine.py` | MCP/CLI primary |
| LocalIpcGateway | `local_ipc_gateway.py` | Stub |
| TcpServeBridge | `serve.py` / `tcp_serve_bridge.py` | Migration fallback; Multitask shared store |
| ServeBridge | `memnet_mcp` TCP client | Multitask shared-store client path |
| MultitaskOperatingModel | agent doctrine (not a Python package) | As-is MN-REQ-12; no engine ACL |
| PinMapIngest_* | `pin_map_ingest.py` | Roadmap stubs |

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
| MN-REQ-11 | PinMapIngest_* stubs + PinMapComposer (11.13) + IdAllocator (11.16) + SnapshotStore |
| MN-REQ-12 | MultitaskCoordinator, MultitaskWorker, MultitaskSharedStoreBinding, TcpServeBridge, ServeBridge; **verify** MN-VER-12-G00 + S01…S09 (`MemNetVerification`) |

## Multitask case study

Worked scenario (parent delegates a multi-step SysML review to one worker), step trace against MN-REQ-12 and behaviour states: [multitask-case-study.md](multitask-case-study.md).

## Gaps / next steps

- Session snapshot / `read get|list` still emit legacy pipe (agent mutate+warm are Tier A)
- `LocalIpcFlow` when LocalIpcGateway is implemented
- PinMapIngest_* deterministic locators (reject client NEW on projecting)
- Optional ANTLR codegen; LegacyPipeImport remains one-shot only
- Migrate `docs/LLM-GUIDE.md` off pipe-centric warm examples
- **To-be (not MN-REQ-12 as-is):** session ACL, neighbourhood reserve, Path-B ingest engines, engine WorkerWriteScope enforcement — design docs only; MultitaskOperatingModel does not claim them shipped (MN-REQ-12.7; MN-VER-12-S09). See also `docs/multi-agent-sessions.md` § Not implemented.
- Typed fields on `MissionTaskPin` / `WorkerWriteScope`
