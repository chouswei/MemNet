# MemNet - system design notes (from SysML)

Target architecture notes from nested `deploy.sysml` / `behaviour.sysml` / `connections.sysml` after **ADR-001**.
Novel-writer is out of scope.

**Exam:** [`../../docs/grammar/gql-model-exam.md`](../../docs/grammar/gql-model-exam.md).  
**Case studies:** [multitask](multitask-case-study.md) · [session-import](session-import-case-study.md) · [company-memory](company-memory-case-study.md) · [prose-rpg](prose-rpg-session-case-study.md).

## Product framing (2026-08-13)

1. **MemNet = shared LLM memory** (`SharedLlmMemory`).
2. **Session as SSOT handle** — `SessionHandoff` / `SessionHandoffById`; chat never SSOT.
3. **Durable GQL store behind MemNet** — `DurableBuffer` / `AgensGraphAdapter` planned **M2.5**.
4. **Lead imports member WM** — path A re-`pin_map` (skip import nest); path B `WorkingMemorySlice` → nested `ImportGuard` → `ImportAbsorb`. Product verb = **import**. Cypher `MERGE` and micro `merge=true` are not this behaviour.

**Sequence:** M1 → M2 → **M2.5** → M3.

**Primary codec:** `GqlCodec` — dialect authority openCypher CIP tree + oC9 baseline + ISO GQL; MemNet-gated pin_map/mutate subset. As-is TierA codecs quarantined — remove in M2.

## Application patterns (not second products)

| Pattern | Item / study |
|---------|----------------|
| Company analytical SSOT | `CompanyAnalyticalSsot` → [company-memory-case-study.md](company-memory-case-study.md) |
| Prose RPG beat session | SharedLlmMemory + goldfish → [prose-rpg-session-case-study.md](prose-rpg-session-case-study.md) |
| Lead imports member WM | Nested ImportGuard/Absorb → [session-import-case-study.md](session-import-case-study.md) |

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
    │   └── SessionImportReceive             // path B
    │       ├── ImportGuard                  // cheap LLM — where the soft review sits
    │       └── ImportAbsorb                 // hard gates + import + settle
    ├── MultitaskWorker                      // member: handoff in + slice export
    └── MultitaskSharedStoreBinding
```

**How lead gets member WM:** shared session → re-`pin_map`; else export slice → `ImportGuard` → `ImportAbsorb` into lead session.

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

## Satisfy (MN-REQ-12 import)

| Leaf | Parts |
|------|-------|
| 12.9 LeadOwnsSessionImport | Coordinator, SessionImportReceive, ImportAbsorb, SessionLifecycle |
| 12.10 NoChatOrWholeStoreImport | Coordinator, Worker, ImportGuard, ImportAbsorb |
| 12.11 CheapLlmImportGuardSoft | ImportGuard, SessionImportReceive |

## Gaps

- M2 engine GQL; remove TierA codec
- M2.5 AgensGraph adapter — plan only
- ImportGuard / ImportAbsorb — doctrine nested; engine not claimed shipped
- MN-REQ-12.7 ACL/reserve/ingest still to-be
