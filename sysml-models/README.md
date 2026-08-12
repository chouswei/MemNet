# MemNet SysML models

Software-only **target** system model for the MemNet core engine and generic MemNet MCP server.

**Layout:** `sysml-models/` per [SYSTEM-REPO-LAYOUT.md](../../SYSTEM-REPO-LAYOUT.md) and repo [LAYOUT.md](../LAYOUT.md).

Design authority: rebuilt requirements + ADR-001 (GQL agent wire) + `docs/grammar/`. Today's `parts/common/memnet` and `parts/memnet-mcp` inform feasibility; see [outputs/system-design-notes.md](outputs/system-design-notes.md) for **target vs as-is**. Exam: [`docs/grammar/gql-model-exam.md`](../docs/grammar/gql-model-exam.md).

## Packages

| File | Package | Role |
|------|---------|------|
| `models/connections.sysml` | `MemNetConnections` | Property-graph items, GQL/shaped/legacy ports |
| `models/requirements.sysml` | `MemNetRequirements` | MN-REQ-00…12 (no parts) |
| `models/deploy.sysml` | `MemNet` | Nested target parts + system composite + satisfy |
| `models/behaviour.sysml` | `MemNetBehaviour` | Session, goldfish, NEW mint, pin-map ingest, Multitask |
| `models/verify.sysml` | `MemNetVerification` | MN-VER-12-G00 + S01…S09 |
| `models/root.sysml` | `ProjectMemNet` | Root imports (load last) |

## Nesting outline (target)

```text
MemNetSystem
├── MemNetCoreLibrary
│   ├── TransportBoundary
│   │   ├── InProcessEngine
│   │   │   └── AgentMemory
│   │   │       └── SessionLifecycle
│   │   │           ├── GraphStore
│   │   │           ├── GqlCodec              // 1.x primary wire
│   │   │           ├── PinMapShapedRead      // shaped pin_map
│   │   │           ├── MutateGate
│   │   │           └── Schema / Caps / Walk / Housekeep / Snapshot
│   │   │               (as-is line codecs → delete in M2)
│   │   ├── LocalIpcGateway
│   │   └── TcpServeBridge
│   └── CliFacade
├── MemNetMcpServer
├── DurableBuffer
│   └── AgensGraphAdapter                     // planned M2.5 (after M2)
├── PinMapRoadmap
└── MultitaskOperatingModel
```

## Target subsystems

- **AgentMemory:** GraphStore, GqlCodec, PinMapShapedRead, MutateGate, SessionLifecycle (remove as-is TierA codecs in M2)
- **Transport:** InProcessEngine, LocalIpcGateway, TcpServeBridge
- **MCP:** McpFacade, ServeBridge, LawSeedHelper
- **DurableBuffer:** AgensGraphAdapter (planned **M2.5**, after M2)
- **Multitask (MN-REQ-12):** MultitaskOperatingModel
- **Deprecated:** LegacyPipeImport (not nested)
- **Out of scope:** novel-writer

## Live pin map (MN-REQ-04)

Turn-facing agent payload = **shaped subgraph** via **PinMapShapedRead** (`pin_map` wraps GQL). Legacy CLI/MCP `query_warm` = deprecated alias.

## Property-graph ontology (first-class)

**Property-graph ontology:** Node / Edge / Property / Label; bind vs relation; law on node / ports — [`docs/grammar/gql-wire-profile.md`](../docs/grammar/gql-wire-profile.md). **Agent wire = GQL only.**

## Validate

Prefer Cursor SysML v2 MCP `validate` / `validateFile` on files under `models/`. Load order is in `config.yaml`.

## Anchor

MemNet design memory (when serve is up): `TSK_model_memnet` — see [AGENT-CONTEXT.md](../AGENT-CONTEXT.md).
