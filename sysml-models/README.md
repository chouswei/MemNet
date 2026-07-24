# MemNet SysML models

Software-only **target** system model for the MemNet core engine and generic MemNet MCP server.

**Layout:** `sysml-models/` per [SYSTEM-REPO-LAYOUT.md](../../SYSTEM-REPO-LAYOUT.md) and repo [LAYOUT.md](../LAYOUT.md).

Design authority: rebuilt requirements + `docs/grammar/memnet-grammar-design.md`. Today's `parts/common/memnet` and `parts/memnet-mcp` inform feasibility; see [outputs/system-design-notes.md](outputs/system-design-notes.md) for **target vs as-is**.

## Packages

| File | Package | Role |
|------|---------|------|
| `models/connections.sysml` | `MemNetConnections` | Tier A/B/C items, ports, connection defs |
| `models/requirements.sysml` | `MemNetRequirements` | MN-REQ-00…11 (no parts) |
| `models/deploy.sysml` | `MemNet` | Target parts + system composite + satisfy |
| `models/behaviour.sysml` | `MemNetBehaviour` | Session, goldfish, NEW mint, pin-map ingest |
| `models/root.sysml` | `ProjectMemNet` | Root imports (load last) |

## Target subsystems

- **Core:** CapsPolicy, SchemaRegistry, TierACodec, IdAllocator, GraphStore, MutateGate, PinMapComposer, WalkQuery, HousekeepSettle, SnapshotStore, SessionLifecycle, InProcessEngine, LocalIpcGateway, TcpServeBridge, CliFacade
- **MCP:** McpFacade (in-process default), ServeBridge (optional TCP), LawSeedHelper
- **Deprecated (not in target composition):** LegacyPipeImport (one-shot `@TAG` pipe)
- **Roadmap:** PinMapIngest_Sysml / Codebase / PcbaAto / SkillsRules (MN-REQ-11; `.ato` = PCBA)
- **Out of scope:** novel-writer and other domain-product tools

## Transport (MN-REQ-06)

1. **InProcessEngine** — primary (MCP / library)
2. **LocalIpcGateway** — named pipe / AF_UNIX when CLI + MCP share a registry
3. **TcpServeBridge** — TCP localhost migration / fallback only

## Live pin map (MN-REQ-04)

Turn-facing agent payload = **pin map** (ego digest). Composer: **PinMapComposer**. MCP `pin_map` / CLI `query pin-map`; `query_warm` / `query warm` = deprecated aliases.

## Libs

`libs/omg` is expected as the OMG SysML v2 Release tree (Kernel). Local checkouts may use a directory junction until `[deps.sysml_libs]` is pinned in `project.toml`.

## Validate

Prefer Cursor SysML v2 MCP `validate` / `validateFile` on files under `models/`. Load order is in `config.yaml`.

## Anchor

MemNet design memory (when serve is up): `TSK_model_memnet` — see [AGENT-CONTEXT.md](../AGENT-CONTEXT.md).
