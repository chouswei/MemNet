# SSOT → code allocate map (implementation tracker)

**SSOT:** `sysml-models/models/implementation.sysml` (`SoftwareAllocate`).  
**Verify:** MN-REQ-06.7 / MN-VER-06-S04 (`ImplementationTracker`).  
**Use:** this table is the ledger. Cue `TSK_model_alloc` / `qname=MemNetImplementation`. When a module ships or moves, edit the allocate row, sync this file, run `pytest tests/test_sysml_ssot_to_code.py`. A missing path fails CI (`missingPathFailsCi`). Hatch stays **0.19.12**. Not #47.

**Wheel:** one `memnet-llm` package, many hosts (`oneWheelManyHosts=true`). MemNet MCP = tip/ops (`tipIsFace=false`). Cousin `sysmledge` is **not** a row (`sysmlEdgeTracked=false`).

| Allocate | Logical (SSOT) | Code | path | pyName | track |
|----------|----------------|------|------|--------|-------|
| coreToWheel | `memNetSystem.core` | `wheel.core` | `parts/common/memnet/memnet` | `memnet` | true |
| mcpToWheel | `memNetSystem.mcp` | `wheel.mcp` | `parts/memnet-mcp/software/memnet_mcp/server.py` | `memnet_mcp.server` | true |
| fleetToWheel | `opsFleet` | `wheel` | Hatch `memnet-llm` | `memnet-llm` | true |
| dropletServiceToCore | `opsFleet.droplet.memnet.core` | `wheel.core` | `parts/common/memnet/memnet` | `memnet` | true |
| dropletMcpToTip | `opsFleet.droplet.memnet.mcp` | `wheel.mcp` | `parts/memnet-mcp/software/memnet_mcp/server.py` | `memnet_mcp.server` | true |
| deviceServiceToCore | `opsFleet.devices.service` | `wheel.core` | `parts/common/memnet/memnet` | `memnet` | true |
| inProcessToMod | `…transport.inProcess` | `inProcessMod` | `parts/common/memnet/memnet/in_process_engine.py` | `memnet.in_process_engine` | true |
| ipcToMod | `…transport.ipc` | `ipcMod` | `parts/common/memnet/memnet/local_ipc_gateway.py` | `memnet.local_ipc_gateway` | true |
| tcpToMod | `…transport.tcp` | `tcpMod` | `parts/common/memnet/memnet/tcp_serve_bridge.py` | `memnet.tcp_serve_bridge` | true |
| tcpDaemonToMod | `…transport.tcp` | `serveDaemonMod` | `parts/common/memnet/memnet/serve.py` | `memnet.serve` | true |
| cliToMod | `memNetSystem.core.cli` | `cliMod` | `parts/common/memnet/memnet/cli.py` | `memnet.cli` | true |
| sessionsToMod | `…sessions` | `sessionsMod` | `parts/common/memnet/memnet/session_lifecycle.py` | `memnet.session_lifecycle` | true |
| storeToMod | `…sessions.store` | `storeMod` | `parts/common/memnet/memnet/graph_store.py` | `memnet.graph_store` | true |
| memStoreToMod | `…sessions.store` | `memStoreMod` | `parts/common/memnet/memnet/mem_store.py` | `memnet.mem_store` | true |
| capsToMod | `…sessions.caps` | `capsMod` | `parts/common/memnet/memnet/caps_policy.py` | `memnet.caps_policy` | true |
| capsAclToMod | `…sessions.caps` | `capsAclMod` | `parts/common/memnet/memnet/acl.py` | `memnet.acl` | true |
| gqlToMod | `…sessions.gqlWire` | `gqlMod` | `parts/common/memnet/memnet/gql_codec.py` | `memnet.gql_codec` | true |
| parseFrontToMod | `…gqlWire.parseFront` | `parseFrontMod` | `parts/common/memnet/memnet/gql_parse_front.py` | `memnet.gql_parse_front` | true |
| productGateToMod | `…gqlWire.productGate` | `gqlPyMod` | `parts/common/memnet/memnet/gql.py` | `memnet.gql` | true |
| schemaToMod | `…sessions.schema` | `schemaMod` | `parts/common/memnet/memnet/schema_registry.py` | `memnet.schema_registry` | true |
| snapToMod | `…sessions.snap` | `snapMod` | `parts/common/memnet/memnet/snapshot_store.py` | `memnet.snapshot_store` | true |
| housekeepToMod | `…sessions.housekeep` | `housekeepMod` | `parts/common/memnet/memnet/housekeep_settle.py` | `memnet.housekeep_settle` | true |
| mutateToMod | `…commit.mutate` | `mutateMod` | `parts/common/memnet/memnet/mutate_gate.py` | `memnet.mutate_gate` | true |
| rsvToMod | `…commit.reserve` | `rsvMod` | `parts/common/memnet/memnet/neighbourhood_reserve.py` | `memnet.neighbourhood_reserve` | true |
| sameThingToMod | `…commit.sameThing` | `sameThingMod` | `parts/common/memnet/memnet/same_thing_absorb.py` | `memnet.same_thing_absorb` | true |
| pinMapToMod | `…shapedRead.pinMap` | `pinMapMod` | `parts/common/memnet/memnet/pin_map_composer.py` | `memnet.pin_map_composer` | true |
| findToMod | `…shapedRead.find` | `pinMapMod` | `parts/common/memnet/memnet/pin_map_composer.py` | `memnet.pin_map_composer` | true |
| peakLToMod | `…recall.seed.peak` | `peakLMod` | `parts/common/memnet/memnet/peak_l.py` | `memnet.peak_l` | true |
| absorbToMod | `…importReceive.absorb` | `absorbMod` | `parts/common/memnet/memnet/import_absorb.py` | `memnet.import_absorb` | true |
| cheapLlmToMod | `…guard.cheapLlm` | `cheapLlmMod` | `parts/common/memnet/memnet/cheap_llm_import_guard.py` | `memnet.cheap_llm_import_guard` | true |
| ingestToMod | `memNetSystem.pinMaps` | `ingestMod` | `parts/common/memnet/memnet/pin_map_ingest.py` | `memnet.pin_map_ingest` | true |
| exportToMod | `memNetSystem.pinMaps.export` | `exportMod` | `parts/common/memnet/memnet/pin_map_export.py` | `memnet.pin_map_export` | true |
| catalogToMod | `memNetSystem.pinMaps.catalog` | `catalogMod` | `parts/common/memnet/memnet/catalog_snap.py` | `memnet.catalog_snap` | true |
| agensToMod | `memNetSystem.durable.agens` | `agensMod` | `parts/common/memnet/memnet/durable/agensgraph.py` | `memnet.durable.agensgraph` | true |
| neo4jToMod | `memNetSystem.durable.neo4j` | `neo4jMod` | `parts/common/memnet/memnet/durable/neo4j.py` | `memnet.durable.neo4j` | true |
| libraryToMod | `memNetSystem.durable.library` | `libraryMod` | `parts/common/memnet/memnet/durable/neo4j_library.py` | `memnet.durable.neo4j_library` | true |
| ragHookToMod | `hostSearch.hook` | `ragHookMod` | `parts/common/memnet/memnet/rag_host_hook.py` | `memnet.rag_host_hook` | true |
| mcpToolsToMod | `memNetSystem.mcp.tools` | `mcpFacadeMod` | `parts/memnet-mcp/software/memnet_mcp/mcp_facade.py` | `memnet_mcp.mcp_facade` | true |
| mcpToolsToServer | `memNetSystem.mcp.tools` | `wheel.mcp` | `parts/memnet-mcp/software/memnet_mcp/server.py` | `memnet_mcp.server` | true |
| mcpBridgeToMod | `memNetSystem.mcp.bridge` | `mcpBridgeMod` | `parts/memnet-mcp/software/memnet_mcp/serve_bridge.py` | `memnet_mcp.serve_bridge` | true |
| mcpHttpToMod | `memNetSystem.multitask.sharedStore` | `mcpHttpMod` | `parts/memnet-mcp/software/memnet_mcp/http_transport.py` | `memnet_mcp.http_transport` | true |
| lawSeedToMod | `memNetSystem.mcp.seed` | `lawSeedMod` | `parts/memnet-mcp/software/memnet_mcp/law_seed_helper.py` | `memnet_mcp.law_seed_helper` | true |

Ellipsis `…` shortens `memNetSystem.core.transport.inProcess.memory.sessions` (and RecallCommit under that). Full qnames live on the `end logical` lines in `implementation.sysml`.

## Not tracked (MUST NOT invent)

| Name | Why |
|------|-----|
| `CousinSysMLEdgeNotInRepo` / `sysmledge` | Product invent face is cousin; `inThisRepo=false`; `track=false`; `sysmlEdgeTracked=false`; `mustNotInventUploadBind` |
| N-server federation (#47) | `nServerFederation=false`; not a code allocate |

## How to track

1. Open this map (or `pin_map` on `goal=TSK_model_alloc`).
2. Find the logical part. The `path` column is the live module.
3. `track=true` and `implemented=true` means the file or directory **must exist** (honesty test).
4. Ship or move a module → edit `implementation.sysml` first, then this map, then pytest.
5. MUST NOT add a `sysmledge` path row.
