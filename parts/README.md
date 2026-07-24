# parts/ — MemNet software layout

Only two product parts (novel-writer is out of scope; see root `DROP-NOVEL-WRITER.md`).

| Part | Path | SysML composite |
|------|------|-----------------|
| Core library | `parts/common/memnet` | `MemNetCoreLibrary` |
| Generic MCP | `parts/memnet-mcp` | `MemNetMcpServer` |

## Module ↔ SysML part map (`memnet` package)

| SysML part | Python module | Notes |
|------------|---------------|-------|
| CapsPolicy | `caps_policy.py` (`config.Caps`) | Env-overridable caps |
| SchemaRegistry | `schema_registry.py` (`tag_map` / `TagMap`) | Positional TagMap is legacy surface |
| TierACodec | `tier_a.py` + `tier_a_codec.py` | Write=display SSOT; ANTLR deferred |
| LegacyPipeImport | `legacy_pipe_import.py` (`wire` / `tag_map.parse_line`) | Import-once only; not agent dialect |
| IdAllocator | `id_allocator.py` | `NEW` mint + locator keys |
| GraphStore | `graph_store.py` (`mem_store.MemStore`) | NODE\|EDGE indexes |
| MutateGate | `mutate_gate.py` | Parse → mint → commit (Tier A + pipe) |
| PinMapComposer | `pin_map_composer.py` | Live pin map Tier A; CLI `query pin-map` (`query warm` alias) |
| WalkQuery | `walk_query.py` | Hop lines |
| HousekeepSettle | `housekeep_settle.py` (`housekeep`) | Stats / prune |
| SnapshotStore | `snapshot_store.py` (`snapshot`) | Session file; not MN-REQ-11 |
| SessionLifecycle | `session_lifecycle.py` (`session` / `registry`) | Named sessions |
| InProcessEngine | `in_process_engine.py` | Primary binding |
| LocalIpcGateway | `local_ipc_gateway.py` | Stub; LocalIpcFlow unallocated |
| TcpServeBridge | `tcp_serve_bridge.py` (`serve`) | TCP migration |
| CliFacade | `cli.py` | Thin entry; console script `memnet` |
| PinMapIngest_* | `pin_map_ingest.py` | Roadmap stubs |

## MCP (`memnet_mcp`)

| SysML part | Module | Notes |
|------------|--------|-------|
| McpFacade | `server.py` / `mcp_facade.py` | Generic tools only |
| ServeBridge | `serve_bridge.py` / `client.py` TCP path | Optional; default in-process |
| LawSeedHelper | `seed.py` / `law_seed_helper.py` | LAW seed on open |

Set `MEMNET_MCP_TRANSPORT=tcp` to force TCP serve client; default is in-process.

Authority for target architecture: `sysml-models/models/deploy.sysml` and `sysml-models/outputs/system-design-notes.md`.
