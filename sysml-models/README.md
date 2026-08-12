# MemNet SysML models

Software-only **target** system model for the MemNet core engine and generic MemNet MCP server.

**Layout:** `sysml-models/` per [SYSTEM-REPO-LAYOUT.md](../../SYSTEM-REPO-LAYOUT.md) and repo [LAYOUT.md](../LAYOUT.md).

Design authority: rebuilt requirements + ADR-001 (GQL agent wire) + `docs/grammar/`. Today's `parts/common/memnet` and `parts/memnet-mcp` inform feasibility; see [outputs/system-design-notes.md](outputs/system-design-notes.md) for **target vs as-is**. Exam: [`docs/grammar/gql-model-exam.md`](../docs/grammar/gql-model-exam.md).

## Product framing (2026-08-13)

1. **MemNet = shared LLM memory** — session-scoped working-memory buffer (multi-agent goldfish); brand SharedLlmMemory.
2. **Session as SSOT handle** — pass a mission SOMETHING by **session id only** (+ anchors / write scope); peers re-`pin_map`; chat is never SSOT; no graph-dump handoff (`SessionHandoffById`).
3. **Durable online GQL store** (AgensGraph-class) sits **behind** MemNet (hydrate/flush). LLM ↔ store direct is out of default teach. Adapter planned **M2.5** (after M2).
4. **Session merge = team lead receives member working memory** — shared session → re-`pin_map` (path A); separate sessions → bounded `WorkingMemorySlice` into lead (`SessionMergeReceive`, path B). Chat/transcript merge is forbidden.

**Sequence:** M1 (GQL wire profile, done) → M2 (engine/MCP GQL; remove as-is codecs) → **M2.5** (durable adapter) → M3 (playbook rewrites).

## Packages

| File | Package | Role |
|------|---------|------|
| `models/connections.sysml` | `MemNetConnections` | SharedLlmMemory, SessionHandoff, WorkingMemorySlice, SessionMergeRequest |
| `models/requirements.sysml` | `MemNetRequirements` | MN-REQ-00…12 (01.7/01.8 handoff, 06.4 durable, 12.9/12.10 merge) |
| `models/deploy.sysml` | `MemNet` | Nested target parts + system composite + satisfy |
| `models/behaviour.sysml` | `MemNetBehaviour` | Goldfish, SessionHandoffById, SessionMergeReceive, Multitask, M2.5 hydrate/flush |
| `models/verify.sysml` | `MemNetVerification` | MN-VER-12-G00 + S01…S11 |
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
│   │   │           ├── GqlCodec             // 1.x; CIP/oC9 dialect authority
│   │   │           ├── PinMapShapedRead     // shaped pin_map
│   │   │           ├── MutateGate
│   │   │           └── Schema / Caps / Walk / Housekeep / Snapshot
│   │   │               (TierACodec quarantined — remove in M2; not nested)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade                            // LLM <-> MemNet (GQL)
├── MemNetMcpServer                          // LLM <-> MemNet (MCP)
├── DurableBuffer                            // planned M2.5
│   └── AgensGraphAdapter                    // hydrate/flush <-> sessions
├── PinMapRoadmap
└── MultitaskOperatingModel                  // SessionHandoffById + SessionMergeReceive
```

## Target subsystems

- **AgentMemory (SharedLlmMemory):** GraphStore, GqlCodec (CIP/oC9 authority), PinMapShapedRead, MutateGate, SessionLifecycle
- **Transport:** InProcessEngine, LocalIpcGateway, TcpServeBridge
- **MCP / CLI:** LLM agents connect to MemNet (GQL/MCP) — not to DurableBuffer as primary
- **DurableBuffer:** AgensGraphAdapter (planned **M2.5**, after M2); connects to GraphStore / SessionLifecycle
- **Multitask (MN-REQ-12):** MultitaskOperatingModel — session-id handoff + lead-owned SessionMergeReceive
- **Quarantined (not nested):** TierACodec (remove in M2); LegacyPipeImport
- **Out of scope:** novel-writer

## Case studies

| Study | Path |
|-------|------|
| Multitask Mode | [outputs/multitask-case-study.md](outputs/multitask-case-study.md) |
| Session merge (lead receives member WM) | [outputs/session-merge-case-study.md](outputs/session-merge-case-study.md) |

## Live pin map (MN-REQ-04)

Turn-facing agent payload = **shaped subgraph** via **PinMapShapedRead** (`pin_map` wraps GQL). Legacy CLI/MCP `query_warm` = deprecated alias.

## Property-graph ontology (first-class)

**Property-graph ontology:** Node / Edge / Property / Label; bind vs relation; law on node / ports — [`docs/grammar/gql-wire-profile.md`](../docs/grammar/gql-wire-profile.md). **Agent wire = GQL only.** Dialect authority: openCypher CIP + oC9 (MemNet-gated subset).

## Validate

Prefer Cursor SysML v2 MCP `validate` / `validateFile` on files under `models/`. Load order is in `config.yaml`.

## Anchor

MemNet design memory (when serve is up): `TSK_model_memnet` — see [AGENT-CONTEXT.md](../AGENT-CONTEXT.md).
