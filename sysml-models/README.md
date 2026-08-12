# MemNet SysML models

Software-only **target** system model for the MemNet core engine and generic MemNet MCP server.

**Layout:** `sysml-models/` per [SYSTEM-REPO-LAYOUT.md](../../SYSTEM-REPO-LAYOUT.md) and repo [LAYOUT.md](../LAYOUT.md).

Design authority: rebuilt requirements + `docs/grammar/memnet-grammar-design.md`. Today's `parts/common/memnet` and `parts/memnet-mcp` inform feasibility; see [outputs/system-design-notes.md](outputs/system-design-notes.md) for **target vs as-is**.

## Packages

| File | Package | Role |
|------|---------|------|
| `models/connections.sysml` | `MemNetConnections` | Tier A/B/C items, ports, connection defs |
| `models/requirements.sysml` | `MemNetRequirements` | MN-REQ-00…12 (no parts) |
| `models/deploy.sysml` | `MemNet` | Target parts + system composite + satisfy |
| `models/behaviour.sysml` | `MemNetBehaviour` | Session, goldfish, NEW mint, pin-map ingest, Multitask |
| `models/verify.sysml` | `MemNetVerification` | MN-VER-12-G00 (group) + S01…S09 verify cases (Multitask case-study trace) |
| `models/root.sysml` | `ProjectMemNet` | Root imports (load last) |

## Target subsystems

- **Core:** CapsPolicy, SchemaRegistry, TierACodec, IdAllocator, GraphStore, MutateGate, PinMapComposer, WalkQuery, HousekeepSettle, SnapshotStore, SessionLifecycle, InProcessEngine, LocalIpcGateway, TcpServeBridge, CliFacade
- **MCP:** McpFacade (in-process default), ServeBridge (optional TCP), LawSeedHelper
- **Multitask (MN-REQ-12):** MultitaskOperatingModel — coordinator / worker roles + shared-store binding (agent doctrine; not Python modules)
- **Deprecated (not in target composition):** LegacyPipeImport (one-shot `@TAG` pipe)
- **Roadmap:** PinMapIngest_Sysml / Codebase / PcbaAto / SkillsRules (MN-REQ-11; `.ato` = PCBA)
- **Out of scope:** novel-writer and other domain-product tools

## Transport (MN-REQ-06 / MN-REQ-12)

1. **InProcessEngine** — primary single-agent (MCP / library)
2. **LocalIpcGateway** — named pipe / AF_UNIX when CLI + MCP share a registry
3. **TcpServeBridge** / streamable-http — TCP localhost migration; **MUST** for Multitask shared store (MN-REQ-12.2)
## Live pin map (MN-REQ-04)

Turn-facing agent payload = **pin map** (ego digest). Composer: **PinMapComposer**. MCP `pin_map` / CLI `query pin-map`; `query_warm` / `query warm` = deprecated aliases.

## Property-graph map (GQL-aligned ontology)

`MemNetConnections` includes map stereotypes (`PropertyGraphNode` / `Edge` / `Property` / `Label`) for durable-side / AgensGraph adapter vocabulary. Construct crosswalk: [`docs/grammar/layer-gql-map.md`](../docs/grammar/layer-gql-map.md). **Agent wire stays Layer** (Write = display); GQL/`MATCH`/`RETURN` are not agent ops.

## Libs

`libs/omg` is expected as the OMG SysML v2 Release tree (Kernel). Local checkouts may use a directory junction until `[deps.sysml_libs]` is pinned in `project.toml`.

## Validate

Prefer Cursor SysML v2 MCP `validate` / `validateFile` on files under `models/`. Load order is in `config.yaml`.

## Anchor

MemNet design memory (when serve is up): `TSK_model_memnet` — see [AGENT-CONTEXT.md](../AGENT-CONTEXT.md).
