# parts/ — MemNet software layout

Only two product parts (novel-writer is out of scope; see root `DROP-NOVEL-WRITER.md`).

| Part | Path | SysML composite |
|------|------|-----------------|
| Core library | `parts/common/memnet` | `MemNetCoreLibrary` |
| Generic MCP | `parts/memnet-mcp` | `MemNetMcpServer` |

## Module ↔ SysML part map (`memnet` package)

| SysML part | Python module | Notes |
|------------|---------------|-------|
| CapsPolicy | `config.py` (`Caps`) | Env-overridable caps |
| SchemaRegistry | `tag_map.py` (`TagMap`) | Positional TagMap is legacy surface |
| TierACodec | none (archive only) | Tier A codec deleted; mutate record classes live in `records.py` |
| LegacyPipeImport | `legacy_pipe_import.py` (`wire` / `tag_map.parse_line`) | Import-once only; not agent dialect |
| IdAllocator | `id_allocator.py` | `NEW` mint + locator keys |
| GraphStore | `mem_store.py` (`MemStore`) | NODE\|EDGE indexes |
| MutateGate | `mutate_gate.py` | Parse → mint → commit (GQL; pipe import-once) |
| PinMapComposer | `pin_map_composer.py` | Live pin map Tier A; CLI `query pin-map` (`query warm` alias) |
| WalkQuery | `walk_query.py` | Hop lines |
| HousekeepSettle | `housekeep.py` | Stats / prune |
| SnapshotStore | `snapshot.py` | Session file; not MN-REQ-11 |
| SessionLifecycle | `session.py` + `registry.py` | Named sessions |
| InProcessEngine | `in_process_engine.py` | Primary binding |
| LocalIpcGateway | `local_ipc_gateway.py` | AF_UNIX; `MEMNET_IPC_SOCKET`; `memnet serve --ipc` (MN-REQ-06.2) |
| NeighbourhoodReserve | `neighbourhood_reserve.py` | RSV leases (`llm_id` + TTL); MN-REQ-12.13 |
| TcpServeBridge | `serve.py` | TCP migration |
| CliFacade | `cli.py` | Thin entry; console script `memnet` |
| PinMapIngest_* | `pin_map_ingest.py` | Path-B ingest (Sysml/Codebase/PcbaAto/SkillsRules; MN-REQ-11; #31/#64) |
| PinMapExport | `pin_map_export.py` | 0.19 cue pin_map GQL write-out (MN-REQ-11.1–11.4; #66); not Absorb |

## MCP (`memnet_mcp`)

| SysML part | Module | Notes |
|------------|--------|-------|
| McpFacade | `server.py` | Generic tools only |
| ServeBridge | `client.py` (TCP path) | Optional; default in-process |
| LawSeedHelper | `seed.py` | LAW seed on open |

Set `MEMNET_MCP_TRANSPORT=tcp` to force TCP serve client; default is in-process.

Authority for target architecture: `sysml-models/models/deploy.sysml` and `sysml-models/outputs/system-design-notes.md`.
