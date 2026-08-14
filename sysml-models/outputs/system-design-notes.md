# MemNet - system design notes (from SysML)

Target architecture notes from nested `deploy.sysml` / `behaviour.sysml` / `connections.sysml` after **ADR-001**.
Novel-writer is out of scope.

**Exam:** [`../../docs/grammar/gql-model-exam.md`](../../docs/grammar/gql-model-exam.md).  
**Case-study shelves:** [outputs/README.md](README.md) — **product canon** (mechanism) vs **application examples** (patterns on SharedLlmMemory). Do not flatten application studies as peer product cores.

**Product canon:** [goldfish desync](goldfish-chat-desync-case-study.md) · [multitask](multitask-case-study.md) · [async-parallel](async-parallel-conflict-case-study.md) · [TCP Multitask](tcp-shared-multitask-case-study.md) · [session-import](session-import-case-study.md) · [snapshot](snapshot-passport-case-study.md) · [durable M2.5](durable-hydrate-flush-case-study.md) · [NEW mint](new-mint-batch-case-study.md).

**Application examples:** [company-memory](company-memory-case-study.md) · [evidence-centre](evidence-centre-case-study.md) · [prose-rpg](prose-rpg-session-case-study.md) · [inverting-amp bind](inverting-amp-bind-relation-case-study.md) · [tech-docs SCPI](tech-docs-scpi-case-study.md) · [SysML goldfish](sysml-modeling-goldfish-case-study.md).

## Product framing (2026-08-13)

1. **MemNet = shared LLM memory** (`SharedLlmMemory`).
2. **Session as SSOT handle** — `SessionHandoff` / `SessionHandoffById`; module A→B pipe; chat / MissionDock / HTTP never carry the graph. **sessionId = SessionCapability** (secret; MUST NOT dump in chat/queue).
3. **Durable GQL store behind MemNet** — M2.5 **client** hydrate/flush landed (`DurableStoreAdapter` / Fake / optional AgensGraph client; one sync owner). Live external cabinet deferred (not claimed; not vendored).
4. **Lead imports member WM** — **path A** shared mission `sessionId` → `pin_map` only (import nest skipped); **path B** `WorkingMemorySliceExport` → optional nested `ImportGuard` (`ImportGuardHook` shipped; `CheapLlmImportGuard` shipped #63) → `ImportAbsorb` (engine SHALL hard; `id_policy` keep|reject|remint). Product verb = **import** (`SessionImport*` only). `keep` = MERGE-by-id upsert into lead SSOT (not append). Micro `merge=true` ≠ this. Module: `memnet.import_absorb`.
5. **CapsPolicy ACL cut (as-is shipped)** — beyond size: who /
   pin_map-vs-mutate / WorkerWriteScope HARD reject / optional SessionBind.
   MutateGate, PinMapShapedRead, and SessionHandoffEmit consult.
   `engineAclShipped=true`; ACL is enabled per session and off by default.
   Reserve/ingest and full ACL modes remain deferred (MN-REQ-12.7).

**Sequence:** M1 → M2 → **M2.5** → M3.

**Primary codec:** `GqlCodec` (**M2 shipped**) — dialect authority openCypher CIP tree + oC9 baseline + ISO GQL; MemNet-gated pin_map/mutate subset. As-is TierA codecs **retired** from product accept (archive/tests only).
**Composer:** `PinMapShapedRead` under `AgentShapedRead` (as-is `PinMapComposer` / `query pin-map`) — shaped GQL subgraph emit. Sibling `BoundedMatchFind` is modelled (`implemented=false`; leftover #73) — not shipped; do not teach MATCH…RETURN as goldfish.
**Dialect authority:** see [`../../docs/grammar/gql-wire-profile.md`](../../docs/grammar/gql-wire-profile.md) (External dialect authority) and ADR-001.

## Application patterns (not second products)

Patterns on **SharedLlmMemory** — application shelf. Product-canon mechanism studies (Multitask, import, mint, snapshot, durable, TCP) are listed separately in [README.md](README.md); do not treat them as peer “extra products.”

| Pattern | Item / study |
|---------|----------------|
| Company analytical SSOT | `CompanyAnalyticalSsot` (**application pattern section** in connections — not core item zoo) → [company-memory-case-study.md](company-memory-case-study.md) |
| Evidence Centre (ai-investor) | Application librarian / MissionDock → [evidence-centre-case-study.md](evidence-centre-case-study.md) |
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

## Nesting outline

```text
MemNetSystem                                 // SharedLlmMemory
├── MemNetCoreLibrary
│   ├── TransportBoundary
│   │   ├── InProcessEngine → AgentMemory → SessionLifecycle
│   │   │     ├── GqlCodec / GraphStore / MutateGate / AgentShapedRead /
│   │   │     │     PinMapShapedRead (shipped) / BoundedMatchFind (not shipped #73)
│   │   │     └── (TierACodec RETIRED/REJECTED — M2 done; not nested)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade
├── MemNetMcpServer
├── DurableBuffer → AgensGraphAdapter        // M2.5 client landed; live cabinet external
├── PinMapRoadmap                            // PinMapIngest_* domains shipped (#64)
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
```

**Path A:** shared mission sessionId → re-`pin_map` (ImportGuard / ImportAbsorb unused).  
**Path B:** export slice → optional `ImportGuard` nest → `ImportAbsorb` (`keep`|`reject`|`remint`) into lead session. Hook (#49) + cheap LLM (#63) are separate; both soft-only.

**Async parallel:** disjoint `WorkerWriteScope` or separate sessions; `EvEndCoordinatorTurn`; host-driven `EvWorkerReturn` (MN-REQ-12.12). **As-is:** CapsPolicy hard-rejects out-of-scope mutate when session ACL is enabled. Overlap coordination still follows host doctrine because no neighbourhood reserve is shipped.

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

| Check | TARGET | As-is 0.4.x |
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
binds. Full private/shared/open `session_token` modes, durable mission
open/import absorb depth, neighbourhood reserve, and Path-B ingest WAIT.

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
| DurableHydrate/FlushFlow | AgensGraphAdapter ↔ SessionLifecycle | M2.5 client landed; live cabinet external |
| InProcess / TCP flows | MCP/CLI ↔ engine | Wired |

## Target ↔ as-is modules (engine)

| Target part | Today's module(s) | Status |
|-------------|-------------------|--------|
| GraphStore | `mem_store.py` + `graph_store.py` | Aliased |
| GqlCodec | `gql.py` / `gql_codec.py` | **Shipped (M2)** |
| (as-is line codec) | `tier_a.py` / `tier_a_codec.py` | RETIRED/REJECTED on product path (M2 done) |
| PinMapShapedRead | `pin_map_composer.py` + `acl.py` | Shaped GQL subgraph emit (M2); shipped ACL read consult when session ACL is enabled; nested under AgentShapedRead (`implemented=true`) |
| BoundedMatchFind | — | Modelled under AgentShapedRead (`implemented=false`; leftover #73); not engine/MCP |
| MutateGate | `mutate_gate.py` + `acl.py` | GQL primary; Layer/Tier A rejected; shipped ACL mutate/scope/bind gates when session ACL is enabled |
| CapsPolicy | `config.Caps` + `acl.py` | Size caps and ACL who/read-vs-mutate/scope/bind shipped; `engineAclShipped=true` |
| AgensGraphAdapter | `memnet.durable` (Fake + optional AgensGraph client) | **Client landed**; live cabinet external / not claimed |

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
- **M2.5:** Client hydrate/flush **landed**; live external cabinet deferred ([durable-hydrate-flush-case-study.md](durable-hydrate-flush-case-study.md))
- **M3:** In-repo playbook / app-note GQL rewrite (plan)
- ImportGuardHook — host plug-in (`set_import_guard` / `--no-guard` / GuardPassthrough); **shipped** (`implemented=true`; #49)
- CheapLlmImportGuard — optional default LLM adapter (MN-REQ-12.11); **shipped** (`implemented=true`; **#63**; env-gated)
- ImportAbsorb — engine-hard nest (DistinctSession / LawVocab / Acl / Schema / IdPolicyKeep|Reject|Remint / NodesThenEdgesCommit); **landed** (`import_slice`; `implemented=true`; keep = MERGE-by-id, not append)
- CapsPolicy ACL (who / pin_map-vs-mutate / WorkerWriteScope hard reject / bind) — **shipped when session ACL is enabled**; `engineAclShipped=true`
- WorkerWriteScope — **hard reject via shipped CapsPolicy ACL**; overlap/reserve coordination remains doctrine
- MN-REQ-12.7 — ACL cut is shipped; neighbourhood reserve + Path-B ingest + full ACL modes WAIT
- `LocalIpcFlow` when LocalIpcGateway is implemented
- PinMapIngest (roadmap-only; domainVariant) deterministic locators
- TierA / LegacyPipe* — parked in connections RETIRED archive; MUST NOT nest on product path
- EvidenceCentre / MissionDock / CompanyMemory — application patterns only; MUST NOT nest under MemNetSystem
- BoundedMatchFind — modelled under AgentShapedRead (`implemented=false`; MN-REQ-04.6 / #73); pin_map remains default goldfish when anchored
