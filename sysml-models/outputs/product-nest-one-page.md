# Product nest (one page)

Mission working memory: hand off by **session id**; GQL ask/commit; no graph dump in chat.

```text
MemNetSystem                          // SharedLlmMemory product
├── Core
│   ├── Session                       // session id = SSOT handle
│   ├── GQL                           // GqlCodec + ProductGqlGate (reject Layer)
│   └── RecallCommit                  // TWO operators only
│       ├── Recall                    // cue → pin_map (outline / Peak_L honesty)
│       └── Commit                    // mutate (+ RSV lease)
├── Multitask
│   ├── Path A                        // shared session → re-pin (no import nest)
│   └── Path B                        // slice → ImportGuard (optional soft)
│                                     //        → ImportAbsorb (hard)
└── DurableBuffer                     // ONE primary cabinet story (hydrate/flush)

APPLICATION LOOK   CousinPointingContrast (eight cousins; SysMLEdge
                   is a distinct pin_map / not SSOT; overlay family
                   SysMLEdgePrj-*; git sysml-models/ is SSOT),
                   HostSearchBridge, …
ARCHIVE LOOK       MemNetArchive (models/archive.sysml) — leftover_* /
                   TierACodec / LegacyPipe* shelf; ProjectMemNet MUST NOT import
OPS LOOK           MemNetUsageDashboard — human look only; not agent wire
OPS FLEET          MemNetOpsFleet — device MemNet services; one MemNet MCP at droplet (tip/ops; tip≠face; product face is sysmledge)
```

## Soft-pass kills (this cut)

- Leftovers nested under Schema / GraphStore on the product path
- Dashboard as manage / agent web API (`agentWire=false`, `httpImplemented=false`)
- Tip as face (`tipIsFace=false`)
- Unparking HTTP dashboard code
- A second product MCP on a device (`mcpCount=1`, `mcpNested=false` = no product MCP nested; `tipMcpLegal=true`)
- Teaching droplet MemNet MCP as the product invent face (product face is `sysmledge`; `mustNotInventUploadBind`; tip≠face)
- Teaching “device must never run any MCP” as a ban on ops tip
- Tip path answering a product question (product agents → `sysmledge` only)
- N-server federation (`nServerFederation=false`; #47)
- SemVer `b` (honesty `c` only; goldfish loop unchanged)

Honesty that leftovers exist lives on the **ARCHIVE** shelf, not on `ProjectMemNet` load (`sysml-models/config.yaml` omits `archive.sysml`; `root.sysml` does not import `MemNetArchive`).

## Review (TTL file + nest)

Session TTL drops **RAM**. Expire `session_save` is **off** unless `MEMNET_SAVE_ON_EXPIRE`. Disk file stays until the user deletes it; `session_load` restores RAM. DurableBuffer / Neo4j is a different cabinet story, not this file (`MN-VER-01-S03`).

ARCHIVE leftover fog remains **off** `ProjectMemNet` load (`leftoverFogNested=false`, `leftoverArchiveOffLoad=true`). OPS `MemNetUsageDashboard` remains look-only (`httpImplemented=false`, `tipIsFace=false`, `agentWire=false`). OPS `MemNetOpsFleet` remains outside `MemNetSystem` (`mcpCount=1` = one MemNet MCP at droplet, `nServerFederation=false`, `productInventFace=sysmledge`, `tipIsFace=false`).
