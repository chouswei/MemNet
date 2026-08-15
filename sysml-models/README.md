# MemNet SysML models

Software-only **target** system model for the MemNet core engine and generic MemNet MCP server.

**Layout:** `sysml-models/` per [SYSTEM-REPO-LAYOUT.md](../../SYSTEM-REPO-LAYOUT.md) and repo [LAYOUT.md](../LAYOUT.md).

Design authority: rebuilt requirements + ADR-001 (GQL agent wire) + `docs/grammar/`. Today's `parts/common/memnet` and `parts/memnet-mcp` inform feasibility; see [outputs/system-design-notes.md](outputs/system-design-notes.md) for **target vs as-is**. Exam: [`docs/grammar/gql-model-exam.md`](../docs/grammar/gql-model-exam.md).

## Product framing (2026-08-13)

1. **MemNet = mission working memory** — session-scoped NODE|EDGE buffer (brand SharedLlmMemory); **not** the search corpus, **not** GraphRAG. In-session recall = serial cue then `pin_map`; host RAG may propose locators only.
2. **Session as SSOT handle** — pass a mission SOMETHING by **session id only** (`SessionHandoff` / `SessionHandoffById`); module A→B pipe; peers re-`pin_map`; chat / MissionDock / HTTP never carry the graph. **sessionId = secret capability** (MUST NOT dump in chat/queue).
3. **Durable online GQL store** behind MemNet (`DurableBuffer` / AgensGraphAdapter) — **M2.5** client hydrate/flush landed; live AgensGraph path needs external cabinet (not claimed verified). LLM↔store direct out of teach.
4. **Lead imports member working memory** — **happy path A** shared session → re-`pin_map` (no second store; **no ImportGuard**). Path B → `WorkingMemorySlice` through **optional** nested `ImportGuard` (`ImportGuardHook` shipped; `CheapLlmImportGuard` shipped #63) then `ImportAbsorb` (engine hard). Product verb = **import**. Colloquial "session merge" means this import only (no SessionMerge* types). Distinct from Cypher `MERGE` and micro id re-id `merge=true`.
5. **CapsPolicy ACL cut** — **as-is shipped** when session ACL is enabled: who, pin_map-vs-mutate, WorkerWriteScope hard reject, and optional SessionBind. `engineAclShipped=true`; ACL remains off by default.

**Sequence:** M1 (done) → M2 (done) → **M2.5** (client landed; live cabinet deferred) → **M3** (in-repo playbook/app-note GQL rewrite).

## Packages

| File | Package | Role |
|------|---------|------|
| `models/connections.sysml` | `MemNetConnections` | SharedLlmMemory, SessionHandoff (+ CallerId / SessionBind / SessionCapability), WorkingMemorySlice, SessionImportRequest, optional ImportGuardDecision; application `CompanyAnalyticalSsot` / `HostSearchBridge`; retired TierA archive |
| `models/requirements.sysml` | `MemNetRequirements` | MN-REQ-00…13 (01.7/01.8, 06.4, 12.9–12.13, 13.1 Recall/Commit) |
| `models/deploy.sysml` | `MemNet` | Nested parts; `RecallCommit` two-operator cut; Multitask spine |
| `models/behaviour.sysml` | `MemNetBehaviour` | HandoffById, SessionImportReceive, Multitask async, M2.5 hydrate/flush |
| `models/verify.sysml` | `MemNetVerification` | MN-VER-12-G00 + S01…S14; MN-VER-04-S01; MN-VER-13-S01 |
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
│   │   │           ├── RecallCommit         // 0.5: TWO operators only
│   │   │           │   ├── Recall           // seed + k-hop; empty ⇒ skip
│   │   │           │   │   └── AgentShapedRead
│   │   │           │   │       ├── PinMapShapedRead // implemented=true
│   │   │           │   │       └── BoundedMatchFind // implemented=false #73
│   │   │           │   └── Commit           // ONE gate; id-mint rules
│   │   │           │       ├── MutateGate
│   │   │           │       └── NeighbourhoodReserve // lease, not 3rd API
│   │   │           └── Schema / Caps / Walk / Housekeep / Snapshot
│   │   │               (TierACodec RETIRED/REJECTED — leftover; not nested)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade                            // LLM <-> MemNet (GQL)
├── MemNetMcpServer                          // LLM <-> MemNet (MCP)
├── DurableBuffer                            // M2.5 client landed; live cabinet external
│   └── AgensGraphAdapter                    // hydrate/flush client; cabinet external
├── PinMapRoadmap                            // all PinMapIngest_* domains shipped (#64)
│   ├── PinMapIngest_Sysml                  // first engine (qname=/path=)
│   ├── PinMapIngest_Codebase               // MOD/SYM (path=/line=/signature=)
│   ├── PinMapIngest_PcbaAto                // CMP/NET/PIN (refdes=/net=/pin=)
│   └── PinMapIngest_SkillsRules            // SKL/RUL (skill_id=/phrase=)
└── MultitaskOperatingModel
    ├── MultitaskCoordinator                 // team lead
    │   ├── SessionHandoffEmit
    │   ├── AsyncTaskDispatch                // spawn N; end turn
    │   └── SessionImportReceive             // path B only
    │       ├── ImportGuard                  // OPTIONAL soft nest
    │       │   ├── ImportGuardHook          // shipped #49
    │       │   └── CheapLlmImportGuard      // shipped (#63 / 12.11; env-gated)
    │       └── ImportAbsorb                 // hard gates + import + settle
    ├── WorkerPool
    │   └── MultitaskWorker[1..*]            // async parallel members
    └── MultitaskSharedStoreBinding
```

**Happy path Multitask:** Path A shared session → re-`pin_map` (ImportGuard unused). Path B uses optional ImportGuard nest then ImportAbsorb. Hook shipped ≠ cheap LLM shipped.

**Story:** `SessionHandoffById` → `AsyncTaskDispatch` (end turn) → workers async → host `EvWorkerReturn` → (happy path A: shared re-`pin_map` | path B: `SessionImportReceive` → optional Guard → Absorb → Settle).

## Target subsystems

- **AgentMemory (SharedLlmMemory):** GraphStore, GqlCodec, **RecallCommit** (Recall: AgentShapedRead / PinMapShapedRead + BoundedMatchFind; Commit: MutateGate + RSV lease), SessionLifecycle
- **MCP / CLI:** LLM ↔ MemNet only (not DurableBuffer as primary)
- **DurableBuffer:** AgensGraphAdapter **client** hydrate/flush landed; live cabinet external / not claimed
- **Multitask:** nested lead handoff + AsyncTaskDispatch + WorkerPool + import spine; MN-REQ-12
- **Path-B PinMapIngest:** all domains shipped (`memnet.pin_map_ingest`; CLI/MCP `ingest sysml|codebase|pcba|skills`). Export/round-trip (#66) not claimed.
- **Optional soft policy:** `ImportGuard` nest (path B): `ImportGuardHook` shipped; `CheapLlmImportGuard` shipped (#63; env-gated); happy path A = re-pin without guard
- **WorkerWriteScope:** CapsPolicy / MutateGate hard-rejects out-of-scope mutate when session ACL is enabled; reserve/overlap coordination remains doctrine
- **CapsPolicy ACL (as-is):** who / pin_map-vs-mutate / WorkerWriteScope hard reject / optional bind are shipped (`engineAclShipped=true`); MutateGate, PinMapShapedRead, and SessionHandoffEmit consult; ACL is off by default
- **Out of scope:** novel-writer; EvidenceCentre / MissionDock / CompanyMemory / **HostSearchBridge** MUST NOT nest under MemNetSystem (optional host locators — design only)
- **Retired / archive (MUST NOT nest on product path):** TierACodec (REJECTED; M2 done); LegacyPipeImport; LegacyLayer*/TierA* connections archive

### CapsPolicy ACL (as-is 0.4.x)

| Check | As-is |
|-------|-------|
| Who (`CallerId`) | Shipped when session ACL is enabled |
| `pin_map` (read) vs mutate | Distinct shipped permissions |
| `WorkerWriteScope` | HARD reject on out-of-scope mutate |
| Optional `SessionBind` | Shipped; missionId + lease match, with documented in-process skip-bind |

Neighbourhood reserve (RSV) and all Path-B `PinMapIngest_*` domains are shipped;
full private/shared/open `session_token` modes remain deferred. `sessionId` is a
secret capability and MUST NOT be dumped. No Dock nest is introduced.

## Case studies

Two shelves (detail + principles: [outputs/README.md](outputs/README.md)). **Product canon** = MemNet mechanism. **Application examples** = patterns on SharedLlmMemory — not extra product cores.

### Product canon

| Study | Path |
|-------|------|
| Goldfish chat desync → re-pin | [outputs/goldfish-chat-desync-case-study.md](outputs/goldfish-chat-desync-case-study.md) |
| Multitask Mode (GQL pins + optional import) | [outputs/multitask-case-study.md](outputs/multitask-case-study.md) |
| Async parallel (canon companion) | [outputs/async-parallel-conflict-case-study.md](outputs/async-parallel-conflict-case-study.md) |
| TCP / streamable-http shared Multitask (transport) | [outputs/tcp-shared-multitask-case-study.md](outputs/tcp-shared-multitask-case-study.md) |
| Session import + optional ImportGuard (path B) | [outputs/session-import-case-study.md](outputs/session-import-case-study.md) |
| Snapshot passport | [outputs/snapshot-passport-case-study.md](outputs/snapshot-passport-case-study.md) |
| Durable hydrate/flush (M2.5) | [outputs/durable-hydrate-flush-case-study.md](outputs/durable-hydrate-flush-case-study.md) |
| `NEW` mint batch (mutate discipline) | [outputs/new-mint-batch-case-study.md](outputs/new-mint-batch-case-study.md) |

### Application examples (on SharedLlmMemory)

| Study | Path |
|-------|------|
| Company analytical SSOT (`COM_*`) | [outputs/company-memory-case-study.md](outputs/company-memory-case-study.md) |
| Evidence Centre (ai-investor librarian / MissionDock) | [outputs/evidence-centre-case-study.md](outputs/evidence-centre-case-study.md) |
| Host search nest (RAG / index outside MemNetSystem) | [outputs/host-search-nest-case-study.md](outputs/host-search-nest-case-study.md) |
| Prose RPG beat (novel-cut patterns → GQL) | [outputs/prose-rpg-session-case-study.md](outputs/prose-rpg-session-case-study.md) |
| Inverting amp bind vs relation (ego `CST_U1`) | [outputs/inverting-amp-bind-relation-case-study.md](outputs/inverting-amp-bind-relation-case-study.md) |
| Tech docs / SCPI atomisation | [outputs/tech-docs-scpi-case-study.md](outputs/tech-docs-scpi-case-study.md) |
| SysML modelling goldfish (MBSE meta) | [outputs/sysml-modeling-goldfish-case-study.md](outputs/sysml-modeling-goldfish-case-study.md) |

## Live pin map (MN-REQ-04)

Turn-facing agent payload = **shaped subgraph** via **PinMapShapedRead** (`pin_map` wraps GQL) when anchored. Sibling **BoundedMatchFind** (MN-REQ-04.6) is modelled under **Recall / AgentShapedRead** (`implemented=false`; leftover #73) — not shipped; do not teach MATCH…RETURN as goldfish. Both seeds are one **Recall** operator ([`docs/grammar/math-skeleton.md`](../docs/grammar/math-skeleton.md)).

## Property-graph ontology (first-class)

Node / Edge / Property / Label — [`docs/grammar/gql-wire-profile.md`](../docs/grammar/gql-wire-profile.md). **Agent wire = GQL only.** Dialect authority: openCypher CIP + oC9 (MemNet-gated subset).

## Validate

Prefer Cursor SysML v2 MCP `validate` on files under `models/`. Load order: `config.yaml`.

## Anchor

`TSK_model_memnet` — see [AGENT-CONTEXT.md](../AGENT-CONTEXT.md).
