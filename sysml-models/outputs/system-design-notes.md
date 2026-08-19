# MemNet - system design notes (from SysML)

Target architecture notes from nested `deploy.sysml` / `behaviour.sysml` / `connections.sysml` after **ADR-001**.
Novel-writer is out of scope.

**Paradox (GQL wire):** [`../../docs/grammar/gql-model-exam.md`](../../docs/grammar/gql-model-exam.md) (historical filename).  
**Case-study shelves:** [outputs/README.md](README.md) — **product canon** (mechanism) vs **application examples** (patterns on SharedLlmMemory). Do not flatten application studies as peer product cores.

**Product canon:** [goldfish desync](goldfish-chat-desync-case-study.md) · [multitask](multitask-case-study.md) · [async-parallel](async-parallel-conflict-case-study.md) · [TCP Multitask](tcp-shared-multitask-case-study.md) · [session-import](session-import-case-study.md) · [snapshot](snapshot-passport-case-study.md) · [durable M2.5](durable-hydrate-flush-case-study.md) · [NEW mint](new-mint-batch-case-study.md) · [session outline](session-outline-case-study.md).

**Application examples:** [company-memory](company-memory-case-study.md) · [evidence-centre](evidence-centre-case-study.md) · [host-search nest](host-search-nest-case-study.md) · [prose-rpg](prose-rpg-session-case-study.md) · [inverting-amp bind](inverting-amp-bind-relation-case-study.md) · [tech-docs SCPI](tech-docs-scpi-case-study.md) · [SysML goldfish](sysml-modeling-goldfish-case-study.md).

## Product framing (2026-08-13)

1. **MemNet = shared LLM memory** (`SharedLlmMemory`).
2. **Session as SSOT handle** — `SessionHandoff` / `SessionHandoffById`; module A→B pipe; chat / MissionDock / HTTP never carry the graph. **sessionId = SessionCapability** (secret; MUST NOT dump in chat/queue).
3. **Durable GQL store behind MemNet** — M2.5 / **0.7** Agens live hydrate/flush (`DurableStoreAdapter` / Fake / optional AgensGraph client; optional Neo4j extra **0.14** `liveNeo4jClaimed=true`; extra **0.16** optional library database name on the same Neo4j process, locators only, name MUST differ from the cabinet (`rejectSameNameAsCabinet`); one sync owner). `RagHostHook.implemented=false` until 0.17. Cabinets external / not vendored.
4. **Lead imports member WM** — **path A** shared mission `sessionId` → `pin_map` only (import nest skipped); **path B** `WorkingMemorySliceExport` → optional nested `ImportGuard` (`ImportGuardHook` shipped; `CheapLlmImportGuard` shipped #63) → `ImportAbsorb` (engine SHALL hard; `id_policy` keep|reject|remint). Product verb = **import** (`SessionImport*` only). TARGET `keep` = MERGE of labels+props / type+ends (GraphElement). leftover_MERGE_by_id is 0.9 leftover, not keep. Micro `merge=true` ≠ this. Module: `memnet.import_absorb`.
5. **CapsPolicy ACL cut (as-is shipped)** — beyond size: who /
   pin_map-vs-mutate / WorkerWriteScope HARD reject / optional SessionBind.
   MutateGate, PinMapShapedRead, and SessionHandoffEmit consult.
   `engineAclShipped=true`; ACL is enabled per session and off by default.
   Reserve + Path-B ingest are **shipped**; full ACL modes remain deferred (MN-REQ-12.7).

**Sequence:** M1 → M2 → **M2.5** → M3 — **all done** (0.8 teach; 0.7 cabinet). **1.0** = claim.

**Primary codec:** `GqlCodec` (**M2 shipped**) — dialect authority openCypher CIP tree + oC9 baseline + ISO GQL; MemNet-gated pin_map/mutate subset. As-is TierA codecs **retired** from product accept (archive/tests only).
**Composer:** `PinMapShapedRead` under `Recall` / `AgentShapedRead` (as-is `PinMapComposer` / `query pin-map`) — shaped GQL subgraph emit. Sibling `BoundedMatchFind` is **shipped** (`implemented=true`; #73 seed-only `find`) — then `pin_map`; do not teach MATCH…RETURN as goldfish. Parent nest `RecallCommit` = two operators (Recall + Commit). Math: [`../../docs/grammar/math-skeleton.md`](../../docs/grammar/math-skeleton.md).
**Dialect authority:** see [`../../docs/grammar/gql-wire-profile.md`](../../docs/grammar/gql-wire-profile.md) (External dialect authority) and ADR-001.

## Application patterns (not second products)

Patterns on **SharedLlmMemory** — application shelf. Product-canon mechanism studies (Multitask, import, mint, snapshot, durable, TCP) are listed separately in [README.md](README.md); do not treat them as peer “extra products.”

| Pattern | Item / study |
|---------|----------------|
| Company analytical SSOT | `CompanyAnalyticalSsot` (**application pattern section** in connections — not core item zoo) → [company-memory-case-study.md](company-memory-case-study.md) |
| Evidence Centre (ai-investor) | Application librarian / MissionDock → [evidence-centre-case-study.md](evidence-centre-case-study.md) |
| Host search (index / RAG) | Optional locators into MutateGate **outside** MemNetSystem → [host-search-nest-case-study.md](host-search-nest-case-study.md) |
| Cousin pointing contrast | TARGET cue→RelativeSeed→ShapeWalk vs seven cousins (`CousinPointingContrast` in `models/cousins.sysml`; MN-REQ-02.9 / 04.8). Copy cue-without-store-key + neighbourhood emit. Do not copy engines, unique-name MERGE, silent LLM same-name merge, content-hash ids, typed path-ids, or vector indexes as identity. |
| Prose RPG beat session | SharedLlmMemory + goldfish → [prose-rpg-session-case-study.md](prose-rpg-session-case-study.md) |
| Dual-EDGE bind / law-on-node | Circuit ego `CST_U1` → [inverting-amp-bind-relation-case-study.md](inverting-amp-bind-relation-case-study.md) |
| Tech-docs / SCPI working set | Art/Sec/Cmd on SharedLlmMemory → [tech-docs-scpi-case-study.md](tech-docs-scpi-case-study.md) |
| SysML modelling goldfish (MBSE meta) | TSK_model_memnet loop → [sysml-modeling-goldfish-case-study.md](sysml-modeling-goldfish-case-study.md) |

### Product-canon pointers (mechanism)

| Mechanism | Study |
|-----------|--------|
| Goldfish / chat ≠ SSOT | [goldfish-chat-desync-case-study.md](goldfish-chat-desync-case-study.md) |
| Multitask + async companion | [multitask-case-study.md](multitask-case-study.md) · [async-parallel-conflict-case-study.md](async-parallel-conflict-case-study.md) |
| Multitask transport | [tcp-shared-multitask-case-study.md](tcp-shared-multitask-case-study.md) |
| Lead imports member WM (path B) | [session-import-case-study.md](session-import-case-study.md) |
| Snapshot passport | [snapshot-passport-case-study.md](snapshot-passport-case-study.md) |
| Durable hydrate/flush | [durable-hydrate-flush-case-study.md](durable-hydrate-flush-case-study.md) |
| `NEW` mint batch | [new-mint-batch-case-study.md](new-mint-batch-case-study.md) |
| Empty-cue session outline | [session-outline-case-study.md](session-outline-case-study.md) |

## Nesting outline

```text
MemNetSystem                                 // SharedLlmMemory
├── MemNetCoreLibrary
│   ├── TransportBoundary
│   │   ├── InProcessEngine → AgentMemory → SessionLifecycle
│   │   │     ├── GqlCodec / GraphStore / RecallCommit
│   │   │     │     Recall / SessionOutline (empty-q census; 0.11 TARGET) /
│   │   │     │     AgentShapedRead /
│   │   │     │     PinMapShapedRead (shipped; CueConflict mark when |Q|>1) /
│   │   │     │     BoundedMatchFind (shipped #73 seed-only)
│   │   │     │     Commit / MutateGate / NeighbourhoodReserve (lease) /
│   │   │     │     SameThingAbsorb (in-session Commit rule; not ImportAbsorb)
│   │   │     └── (TierACodec RETIRED/REJECTED — leftover retire-from-wheel; not nested)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade                            // catalog Snap + session list (0.15); pin-map export (0.19)
├── MemNetMcpServer                          // snap_model / session_list / export_pin_map
├── DurableBuffer → AgensGraphAdapter + Neo4jAdapter  // M2.5; Agens 0.7; Neo4j 0.14 claimed
│                         + Neo4jLibraryPort          // 0.16 locators; rejectSameNameAsCabinet
├── PinMapRoadmap                            // PinMapIngest_* + CatalogSnap (0.15) + PinMapExport (0.19)
└── MultitaskOperatingModel
    ├── MultitaskCoordinator                 // team lead
    │   ├── SessionHandoffEmit
    │   ├── AsyncTaskDispatch                // spawn N; end turn
    │   └── SessionImportReceive             // path B only
    │       ├── ImportGuard                  // soft nest (PinMapIngest-style)
    │       │   ├── ImportGuardHook          // shipped #49 (+ GuardPassthrough)
    │       │   ├── CheapLlmImportGuard      // shipped #63 (12.11; env-gated)
    │       │   └── Soft* leaves
    │       └── ImportAbsorb                 // engine SHALL hard
    │           └── DistinctSession / LawVocab / Acl / Schema /
    │               IdPolicyKeep|Reject|Remint / NodesThenEdgesCommit
    ├── WorkerPool
    │   └── MultitaskWorker[1..*]
    │       └── WorkingMemorySliceExport     // hard: anchors, budget, LAW skip
    └── MultitaskSharedStoreBinding

HostSearchBridge / EvidenceCentre / CompanyMemory / CousinPointingContrast
    // APPLICATION — MUST NOT nest here
```

**Path A:** shared mission sessionId → re-`pin_map` (ImportGuard / ImportAbsorb unused).  
**Path B:** export slice → optional `ImportGuard` nest → `ImportAbsorb` (`keep`|`reject`|`remint`) into lead session. Hook (#49) + cheap LLM (#63) are separate; both soft-only.

**Async parallel:** disjoint `WorkerWriteScope` or separate sessions; `EvEndCoordinatorTurn`; host-driven `EvWorkerReturn` (MN-REQ-12.12). **As-is:** CapsPolicy hard-rejects out-of-scope mutate when session ACL is enabled. Overlap: serialise or take an **RSV** lease (RSV shipped).

## CapsPolicy ACL (TARGET vs as-is)

### Privilege grain (analogy once)

Steal ACL **grain** from Neo4j / AgensGraph-class RBAC — do **not** become those
products. Agent wire stays **gated GQL only**. MUST NOT: Bolt as agent wire,
LLM↔Neo4j/AgensGraph teach, or MemNet-as-Cypher-proxy.

| Neo4j / AgensGraph-class | MemNet CapsPolicy ACL |
|--------------------------|------------------------|
| TRAVERSE / MATCH | `pin_map` (read walk / shaped ego) |
| WRITE (CREATE / SET / DELETE) | `mutate` (`add` / `update`) |
| label / id GRANT | `WorkerWriteScope` hard reject (cumulative OR) |
| role / user | `caller` (who) |
| — (not a Neo4j concept) | optional `SessionBind` = `missionId` + `lease` |

Engine module: `parts/common/memnet/memnet/acl.py`.

| Check | TARGET | As-is 0.8 |
|-------|--------|-------------|
| Size / depth / row caps | Yes | **Shipped** (`memnet.config.Caps`) |
| Who (CallerId) | Yes — MutateGate / PinMap / HandoffEmit consult | **Shipped when session ACL is enabled** |
| pin_map (TRAVERSE) vs mutate (WRITE) | Distinct permissions | **Shipped when session ACL is enabled** |
| WorkerWriteScope (label/id GRANT) | **HARD reject** out-of-scope mutate | **Shipped when session ACL is enabled** |
| Optional SessionBind | missionId + lease | **Shipped when configured; in-process MAY skip bind** |
| sessionId as SessionCapability | Secret; MUST NOT dump in chat/queue | Practical join key; treat as secret in doctrine |

`CapsPolicy.engineAclShipped = true` + `doctrineAsIs = false` describe the
shipped ACL cut. ACL remains off by default; in-process MAY skip bind under
`MEMNET_SERVE_INTERNAL`, while require-bind boundaries enforce configured
binds. Full private/shared/open `session_token` modes WAIT. Neighbourhood
reserve and Path-B ingest are **shipped**.

## Behaviours

| State machine | Role |
|---------------|------|
| `GoldfishLoop` / `MutateWithNew` / `SessionLifecycleStates` | Engine goldfish |
| `SessionHandoffById` | Pass session id (vs `EvDumpGraphInChat`) |
| `SessionImportReceive` | path A = pin_map only; path B Guard soft → Absorb hard (vs `EvImportFromChat`) |
| `ParentTaskLifecycle` / `WorkerScopedTurn` / `MultitaskMissionCycle` | MN-REQ-12 |
| `DurableHydrateFlushRoadmap` | M2.5 client landed; live cabinet external |

## Interfaces (selected)

| Connection | From → To | Status |
|------------|-----------|--------|
| SessionHandoffFlow | Coordinator → Worker | Target |
| WorkingMemorySliceFlow | Worker → `coordinator.importReceive.guard` | Target path B |
| ImportGuardDecisionFlow | Guard → Absorb (nested) | Target |
| DurableHydrate/FlushFlow | DurableBuffer adapters ↔ SessionLifecycle | M2.5; Agens 0.7; Neo4j 0.14 claimed |
| InProcess / TCP flows | MCP/CLI ↔ engine | Wired |

## Target ↔ as-is modules (engine)

| Target part | Today's module(s) | Status |
|-------------|-------------------|--------|
| GraphStore | `mem_store.py` + `graph_store.py` | Aliased |
| GqlCodec | `gql.py` / `gql_codec.py` | **Shipped (M2)** |
| (as-is line codec) | `tier_a.py` / `tier_a_codec.py` | RETIRED/REJECTED on product path (M2 done) |
| PinMapShapedRead | `pin_map_composer.py` + `acl.py` | Shaped GQL subgraph emit (M2); nested under Recall / AgentShapedRead (`implemented=true`) |
| BoundedMatchFind | `query find` / MCP `find` | Nested under Recall / AgentShapedRead (`implemented=true`; #73 seed-only; then `pin_map`) |
| RecallCommit | — | Modelled two-operator parent (MN-REQ-13); SameThingAbsorb is a Commit rule, not a third operator; no engine cut |
| MutateGate | `mutate_gate.py` + `acl.py` | Commit gate (GQL); leftover_NEW_mint as-is; TARGET GraphElement create; Layer/Tier A rejected |
| CapsPolicy | `config.Caps` + `acl.py` | Size caps and ACL who/read-vs-mutate/scope/bind shipped; `engineAclShipped=true` |
| AgensGraphAdapter | `memnet.durable` (Fake + optional AgensGraph client) | **0.7** live hydrate/flush; cabinet external / not vendored |
| Neo4jAdapter | `memnet.durable` (optional Neo4j client) | Extra **0.14** live claimed; `liveNeo4jClaimed=true` |

## Satisfy (MN-REQ-12 import + async + ACL honesty)

| Leaf | Parts |
|------|-------|
| 12.7 NoAssumeAclReserveIngest | CapsPolicy, MutateGate, PinMapShapedRead, SessionHandoffEmit, AsyncTaskDispatch, Coordinator, Worker, WorkerPool |
| 12.9 LeadOwnsSessionImport | Coordinator, SessionImportReceive, ImportAbsorb (+ IdPolicy* leaves), WorkingMemorySliceExport, SessionLifecycle |
| 12.10 NoChatOrWholeStoreImport | Coordinator, Worker, WorkingMemorySliceExport, ImportGuard / ImportGuardHook, ImportAbsorb |
| 12.11 CheapLlmImportGuardSoft (OPTIONAL soft) | **CheapLlmImportGuard** (`implemented=true`; #63) — not the hook |
| 12.12 HostDrivenAsyncParallel | AsyncTaskDispatch, Coordinator, WorkerPool, MultitaskWorker |

## Gaps

- **M1:** GQL wire profile — **done**
- **M2:** Engine/MCP GQL accept + shaped pin_map emit; Layer/Tier A retired — **done**
- **M2.5:** Client + **0.7** Agens live hydrate/flush + extra **0.14** Neo4j live claim; cabinets external / not vendored ([durable-hydrate-flush-case-study.md](durable-hydrate-flush-case-study.md))
- **M3:** In-repo playbook / app-note GQL rewrite — **done** (0.8)
- ImportGuardHook — host plug-in (`set_import_guard` / `--no-guard` / GuardPassthrough); **shipped** (`implemented=true`; #49)
- CheapLlmImportGuard — optional default LLM adapter (MN-REQ-12.11); **shipped** (`implemented=true`; **#63**; env-gated)
- RecallCommit — modelled two-operator cut (MN-REQ-13.1); empty q is **session outline** (MN-REQ-04.9; `implemented=false`); leftover empty-seed skip is leftover; SameThingAbsorb modelled as a distinct Commit rule (MN-REQ-13.2; `implemented=false`); CueConflict is an emit mark on find/pin_map when `|Q|>1` (`implemented=false`; not a product command); engine cut not claimed; **1.0** = claim of 0.5–0.8
- ImportAbsorb — engine-hard nest (DistinctSession / LawVocab / Acl / Schema / IdPolicyKeep|Reject|Remint / NodesThenEdgesCommit); **landed** (`import_slice`; `implemented=true`; TARGET keep = labels+props MERGE; leftover_MERGE_by_id leftover, not append). Distinct from SameThingAbsorb (in-session collapse; SHALL NOT entity-resolve).
- CapsPolicy ACL (who / pin_map-vs-mutate / WorkerWriteScope hard reject / bind) — **shipped when session ACL is enabled**; `engineAclShipped=true`
- WorkerWriteScope — **hard reject via shipped CapsPolicy ACL**; overlap: serialise or **RSV** lease
- MN-REQ-12.7 — ACL cut is shipped; RSV + Path-B ingest **shipped**; full ACL modes WAIT
- `LocalIpcFlow` — `LocalIpcGateway` **shipped** (`memnet serve --ipc`)
- PinMapIngest — all leftover domains **shipped** (#64); CatalogSnap 0.15 = catalog + interiors; PinMapExport 0.19 = cue GQL write-out (#66); re-ingest later
- TierA / LegacyPipe* — parked in connections RETIRED archive; MUST NOT nest on product path
- EvidenceCentre / MissionDock / CompanyMemory / **HostSearchBridge** / **CousinPointingContrast** — application / contrast nests only; MUST NOT nest under MemNetSystem ([host-search-nest-case-study.md](host-search-nest-case-study.md); `models/cousins.sysml`)
- BoundedMatchFind — **shipped** (`implemented=true`; MN-REQ-04.6 / #73 seed-only); pin_map remains default goldfish when anchored
