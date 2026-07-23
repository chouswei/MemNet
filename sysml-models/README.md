# MemNet SysML models

Software-only system model for the MemNet core engine and generic MemNet MCP server.

**Layout:** `sysml-models/` per [SYSTEM-REPO-LAYOUT.md](../../SYSTEM-REPO-LAYOUT.md) and repo [LAYOUT.md](../LAYOUT.md).

## Packages

| File | Package | Role |
|------|---------|------|
| `models/connections.sysml` | `MemNetConnections` | Ports, connection defs, flow items |
| `models/requirements.sysml` | `MemNetRequirements` | Nested MN-REQ-00…10 (groups + atomic leaves; LLM props/limits; MN-R* retired) |
| `models/deploy.sysml` | `MemNet` | Core + MCP parts and system composite |
| `models/behaviour.sysml` | `MemNetBehaviour` | Session lifecycle state machine |
| `models/root.sysml` | `ProjectMemNet` | Root imports (load last) |

## Subsystems modelled

- **Core (`parts/common/memnet`):** Caps, WireCodec, TagMap, MemStore (add/update, warm/walk, LAW prepend), SessionRegistry/SessionStore, Snapshot, Housekeep, CLI, Serve TCP daemon
- **MCP (`parts/memnet-mcp`):** Tool surface, serve client bridge, LAW seed helper, JSON envelope vs wire payload
- **Out of scope:** domain product surfaces (this model covers engine + generic MCP only)

## Libs

`libs/omg` is expected as the OMG SysML v2 Release tree (Kernel). Local checkouts may use a directory junction until `[deps.sysml_libs]` is pinned in `project.toml`.

## Validate

Prefer Cursor SysML v2 MCP `validate` / `parse` on files under `models/`. Load order is in `config.yaml`.

## Anchor

MemNet design memory (when serve is up): `TSK_model_memnet` — see [AGENT-CONTEXT.md](../AGENT-CONTEXT.md).
