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
                   is a distinct pin_map / not MemNet SSOT; overlay family
                   SysMLEdgePrj-*; this engine repo is repo-based git SSOT;
                   downstream bound desk is working model SSOT),
                   HostSearchBridge, …
ARCHIVE LOOK       MemNetArchive (models/archive.sysml) — leftover_* /
                   TierACodec / LegacyPipe* shelf; ProjectMemNet MUST NOT import
OPS LOOK           MemNetUsageDashboard — human look only; not agent wire
OPS FLEET          MemNetOpsFleet — device MemNet services; one MemNet MCP at droplet (tip/ops; tip≠face; product face is sysmledge)
OPS ACCESS         TipMemNetAccessPortal — Szu-Wei invite, Google login, Bearer for keyed tip MCP at droplet WWW (tip≠face; not sysmledge; portal sidecar)
IMPLEMENTATION     MemNetImplementation — SoftwareAllocate SSOT → live modules; tracker ledger; one Hatch wheel many hosts; sysmledge not in wheel
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
- Tip access portal as a sysmledge / `openProject` key page (`isSysmlEdgeProduct=false`)
- Unauthenticated MemNet MCP on droplet WWW (`unauthenticatedWwwMcp=false`; keyed tip stays)
- This portal granting open MemNet to strangers (free path is SysMLEdge free tier or `memnet-llm` self-host)
- Selling invent_2_green (`sellsInvent2Green=false`; `portalWebImplemented=true`; `inventOnly=false`)
- N-server federation (`nServerFederation=false`; #47)
- SemVer `b` (honesty `c` only; goldfish loop unchanged)
- SysMLEdge product face nested in the Hatch wheel (`sysmlEdgeInWheel=false`; `CousinSysMLEdgeNotInRepo`)
- One Python package per host (`oneWheelManyHosts=true`)

Honesty that leftovers exist lives on the **ARCHIVE** shelf, not on `ProjectMemNet` load (`sysml-models/config.yaml` omits `archive.sysml`; `root.sysml` does not import `MemNetArchive`).

## Review (TTL file + nest)

Session TTL drops **RAM**. Expire `session_save` is **off** unless `MEMNET_SAVE_ON_EXPIRE`. Disk file stays until the user deletes it; `session_load` restores RAM. DurableBuffer / Neo4j is a different cabinet story, not this file (`MN-VER-01-S03`).

ARCHIVE leftover fog remains **off** `ProjectMemNet` load (`leftoverFogNested=false`, `leftoverArchiveOffLoad=true`). OPS `MemNetUsageDashboard` remains look-only (`httpImplemented=false`, `tipIsFace=false`, `agentWire=false`). OPS `MemNetOpsFleet` remains outside `MemNetSystem` (`mcpCount=1` = one MemNet MCP at droplet, `nServerFederation=false`, `productInventFace=sysmledge`, `tipIsFace=false`). OPS `TipMemNetAccessPortal` remains outside `MemNetSystem` (`tipIsFace=false`, `keyedWwwMcp=true`, `unauthenticatedWwwMcp=false`, `isSysmlEdgeProduct=false`, `inventOnly=false`, `portalWebImplemented=true`, `sellsInvent2Green=false`). IMPLEMENTATION `MemNetLlmWheel` remains one Hatch package for many hosts (`oneWheelManyHosts=true`, `sysmlEdgeInWheel=false`). IMPLEMENTATION tracker (`ImplementationTracker`) watches allocate rows (`missingPathFailsCi`; `sysmlEdgeTracked=false`).
