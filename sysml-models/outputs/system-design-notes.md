# MemNet - system design notes (from SysML)

Brief notes aligned with `deploy.sysml` / `behaviour.sysml`. Novel-writer is out of scope.

## Mission

**MemNet = Net of Memory** - a memory *network* of **NODE** and **EDGE** only (durable facts + relations), not a chat notepad and not the search corpus. It sits **between** pipelines of LLM calls and data searching; aids the LLM for system, programme, and hardware development, and for documentation; aims to **save time** and **token usage** while **keeping high accuracy** when presenting facts. Agent I/O is LLM-produced/consumed and SHALL follow **prompt rules**; humans inspect via a **canonical parser**.

## Context

Mechanisms: durable named sessions; atomised facts + first-class relations; strict add/update; anchored warm slice with recycle hide and caps; shared local serve; generic MCP boundary. Grammar is the agent language; the parser recovers structure for humans/tools. Concrete spellings (`@TAG` pipe, TagMap, LAW01-LAW05, length-prefixed JSON) are current realisations, not eternal identity.

## Part tree (logical)

```text
MemNetSystem
├── MemNetCoreLibrary          → parts/common/memnet
│   ├── WireCodec
│   ├── MemNetCliApp
│   └── MemNetServeDaemon
│       ├── SessionRegistryService (+ CapsConfig)
│       └── SessionStoreFacade
│           ├── TagMapService
│           ├── MemStoreEngine
│           ├── HousekeepService
│           └── SnapshotService
└── MemNetMcpServer            → parts/memnet-mcp
    ├── MemNetMcpToolSurface
    ├── MemNetServeClient
    └── MemNetSeedHelper
```

## Interfaces

| Connection | From → To | Payload |
|------------|-----------|---------|
| ServeCommandFlow | MCP client / CLI → ServeDaemon | JSON `{args, stdin}` |
| JsonEnvelopeFlow | Serve / tools → host | `exit_code`, stdout wire, stderr `@ERR` |
| WirePayloadFlow | Host tools ↔ ingest / codec | `@TAG:` batches |
| WarmSliceFlow | MemStore → consumer | LAW + active subgraph |
| SnapshotFlow | Session ↔ file | save/load blob |

## Session lifecycle

`closed` → `opening`/`loading` → `active` (warm/mutate loop) → `saving` → `active` or `closed` (close/TTL). Errors on a command typically stay in `active` without closing the session.

## Requirements tree

Hierarchy is **nested `requirement def`s** under `MN-REQ-00` (not deploy parts). Formal **deriveReqt** in SysML v2 is `#derivation connection` (`RequirementDerivation`: `#original` parent, `#derive` children) on requirement *usages*. Groups derive from mission; leaves derive from their group. ID scheme: `MN-REQ-NN` groups, `MN-REQ-NN.M` atomic leaves. `satisfy` targets leaves on implementing parts; only `MN-REQ-00` on `MemNetSystem`.

```text
MN-REQ-00 MissionBridge
├── MN-REQ-01 SessionLifecycle
│   ├── 01.1 Named sessions
│   ├── 01.2 open/resume/save/load/close
│   └── 01.3 TTL + session caps
├── MN-REQ-02 MemoryNetGraph (conceptual kinds: NODE | EDGE only)
│   ├── 02.1 Exactly NODE and EDGE
│   ├── 02.2 Nodes hold atomised facts
│   ├── 02.3 Edges are first-class
│   ├── 02.4 Query warm/walk over NODE+EDGE
│   ├── 02.5 Grammar expresses both
│   ├── 02.6 Parser recovers both
│   └── 02.7 Schema-validated ingest (tags may realise node kinds)
├── MN-REQ-03 StrictMutate
│   ├── 03.1 add fails if exists
│   ├── 03.2 update fails if absent
│   └── 03.3 no silent upsert
├── MN-REQ-04 SliceEconomy
│   ├── 04.1 Anchored warm slice
│   ├── 04.2 Recycle hidden from warm
│   ├── 04.3 Warm depth/row caps
│   ├── 04.4 Engine-law prepend
│   └── 04.5 Anchored walk SHOULD
├── MN-REQ-05 HardCaps
│   ├── 05.1 Store resource caps
│   └── 05.2 Query fanout caps
├── MN-REQ-06 BoundaryServe
│   ├── 06.1 Shared session registry
│   └── 06.2 Local serve endpoint
├── MN-REQ-07 McpAgentBoundary
│   ├── 07.1 Generic tool surface
│   ├── 07.2 Structured tool envelope
│   ├── 07.3 No domain-product tools
│   └── 07.4 MCP law seed on open
├── MN-REQ-08 AgentIoGrammar (LLM is I/O actor; follow prompt rules)
│   ├── 08.1 LLM-friendly stdio
│   ├── 08.2 LLM-friendly MCP
│   ├── 08.3 No hostile positional dump
│   ├── 08.4 Boundary friendly if internal differs
│   ├── 08.5 I/O actor is LLM
│   ├── 08.6 Follow prompt rules (WDC/novel-cut as example families)
│   ├── 08.7 Write ≈ display
│   └── 08.8 Template-copyable shapes
├── MN-REQ-09 HumanInspect
│   ├── 09.1 Canonical parser SSOT
│   ├── 09.2 Reject invalid wire
│   ├── 09.3 Parse-faithful inspect
│   └── 09.4 No ad-hoc consumer splits
└── MN-REQ-10 LlmPropertiesAndLimits (assumed LLM attrs + limitation leaves)
    ├── 10.1 No chat as durable store
    ├── 10.2 Warm must fit context
    ├── 10.3 Minimise token round-trips
    ├── 10.4 External ground truth required
    ├── 10.5 Grammar must be LLM-learnable
    ├── 10.6 Prefer template-friendly pins
    └── 10.7 Human verify via parser
```

Agent-facing MemNet I/O is LLM-produced/consumed and SHALL follow prompt rules; mechanism groups also `#derive` from MN-REQ-10 limitation leaves.

Domain products (e.g. novel-writer) are out of scope for this model.

## Gaps / next modelling steps

- Finer allocate from parts to Python modules (`@SYM`-level) once MemNet design snap is warm
- Explicit prune/settle action defs if behaviour depth needed
- Pin `sysml-models/libs` via `project.toml` submodule (replace local OMG junction; do not commit junction)
- Full-project load validate once OMG Kernel is pinned (MCP package smoke already green)
- Optional interconnection Mermaid in outputs when diagrams are requested
