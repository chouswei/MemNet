/*
  MemNet implementation allocate — SSOT parts → live code in this checkout.

  One Hatch wheel (memnet-llm) for many hosts (droplet + devices).
  MemNet MCP module = tip/ops (tip≠face). Cousin sysmledge is NOT
  allocated here (thisRepoHasProductFace=false; mustNotInventUploadBind).
  Not N-server federation (#47).
*/
package MemNetImplementation {
  private import ScalarValues::*;
  private import MemNetRequirements::*;
  private import MemNet::*;

  allocation def SoftwareAllocate {
    doc /*
      Logical SysML part (SSOT) → code module on disk.
      Source end = logical; target end = code. Many hosts bind the
      same wheel; hosts are not extra packages.
    */
    end logical;
    end code;
  }

  part def CodeModule {
    doc /*
      Live Python module or package directory in this repo.
      Tracking record: implemented=true and inThisRepo=true means
      the path exists here; track=true means honesty tests watch it.
    */
    attribute path : String;
    attribute pyName : String;
    attribute implemented : Boolean = true;
    attribute inThisRepo : Boolean = true;
    attribute track : Boolean = true;
  }

  part def ImplementationTracker {
    doc /*
      Implementation ledger. Each SoftwareAllocate row tracks one
      SSOT part to a live path. Derived map:
      sysml-models/outputs/ssot-to-code-allocate-map.md
      Cue TSK_model_alloc / qname=MemNetImplementation. A missing
      path fails honesty tests — that is the tracker. MUST NOT
      track cousin sysmledge (sysmlEdgeTracked=false).
    */
    attribute trackAllocateRows : Boolean = true;
    attribute mapPath : String = "sysml-models/outputs/ssot-to-code-allocate-map.md";
    attribute sysmlEdgeTracked : Boolean = false;
    attribute missingPathFailsCi : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_7_SsotToCodeAllocate;
  }

  // ----- Wheel (one package, many hosts) -----

  part def CoreLibraryMod {
    attribute path : String = "parts/common/memnet/memnet";
    attribute pyName : String = "memnet";
    attribute hatchTarget : String = "parts/common/memnet/memnet";
    attribute implemented : Boolean = true;
    attribute inThisRepo : Boolean = true;
    attribute track : Boolean = true;
  }

  part def McpServerMod {
    doc /*
      memnet-mcp console: memnet_mcp.server:main. Tip/ops engine face.
      MUST NOT be taught as product invent face (tipIsFace=false).
    */
    attribute path : String = "parts/memnet-mcp/software/memnet_mcp/server.py";
    attribute pyName : String = "memnet_mcp.server";
    attribute consoleEntry : String = "memnet_mcp.server:main";
    attribute tipIsFace : Boolean = false;
    attribute implemented : Boolean = true;
    attribute inThisRepo : Boolean = true;
    attribute track : Boolean = true;
  }

  part def MemNetLlmWheel {
    doc /*
      Hatch memnet-llm. Droplet and device hosts instantiate this
      same wheel. MUST NOT nest a SysMLEdge product face in the wheel.
    */
    part core : CoreLibraryMod;
    part mcp : McpServerMod;
    attribute hatchPackage : String = "memnet-llm";
    attribute hatchCorePackage : String = "parts/common/memnet/memnet";
    attribute hatchMcpPackage : String = "parts/memnet-mcp/software/memnet_mcp";
    attribute consoleMemnet : String = "memnet.cli:main";
    attribute consoleMemnetMcp : String = "memnet_mcp.server:main";
    attribute oneWheelManyHosts : Boolean = true;
    attribute sysmlEdgeInWheel : Boolean = false;
    attribute track : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_7_SsotToCodeAllocate;
  }

  // ----- Engine modules (names match SysML part defs) -----

  part def InProcessEngineMod {
    attribute path : String = "parts/common/memnet/memnet/in_process_engine.py";
    attribute pyName : String = "memnet.in_process_engine";
  }
  part def LocalIpcGatewayMod {
    attribute path : String = "parts/common/memnet/memnet/local_ipc_gateway.py";
    attribute pyName : String = "memnet.local_ipc_gateway";
  }
  part def TcpServeBridgeMod {
    attribute path : String = "parts/common/memnet/memnet/tcp_serve_bridge.py";
    attribute pyName : String = "memnet.tcp_serve_bridge";
  }
  part def ServeDaemonMod {
    attribute path : String = "parts/common/memnet/memnet/serve.py";
    attribute pyName : String = "memnet.serve";
  }
  part def CliFacadeMod {
    attribute path : String = "parts/common/memnet/memnet/cli.py";
    attribute pyName : String = "memnet.cli";
    attribute consoleEntry : String = "memnet.cli:main";
  }
  part def SessionLifecycleMod {
    attribute path : String = "parts/common/memnet/memnet/session_lifecycle.py";
    attribute pyName : String = "memnet.session_lifecycle";
  }
  part def GraphStoreMod {
    attribute path : String = "parts/common/memnet/memnet/graph_store.py";
    attribute pyName : String = "memnet.graph_store";
  }
  part def MemStoreMod {
    doc /* Backing store aliased with GraphStore (system-design-notes). */
    attribute path : String = "parts/common/memnet/memnet/mem_store.py";
    attribute pyName : String = "memnet.mem_store";
  }
  part def CapsPolicyMod {
    attribute path : String = "parts/common/memnet/memnet/caps_policy.py";
    attribute pyName : String = "memnet.caps_policy";
  }
  part def CapsAclMod {
    doc /* CapsPolicy ACL who / pin_map-vs-mutate / scope (acl.py). */
    attribute path : String = "parts/common/memnet/memnet/acl.py";
    attribute pyName : String = "memnet.acl";
  }
  part def GqlCodecMod {
    attribute path : String = "parts/common/memnet/memnet/gql_codec.py";
    attribute pyName : String = "memnet.gql_codec";
  }
  part def ProductGqlGateMod {
    doc /* Product gate + leftover lowering (memnet.gql); not GraphGlot parse. */
    attribute path : String = "parts/common/memnet/memnet/gql.py";
    attribute pyName : String = "memnet.gql";
  }
  part def GraphGlotParseFrontMod {
    attribute path : String = "parts/common/memnet/memnet/gql_parse_front.py";
    attribute pyName : String = "memnet.gql_parse_front";
  }
  part def MutateGateMod {
    attribute path : String = "parts/common/memnet/memnet/mutate_gate.py";
    attribute pyName : String = "memnet.mutate_gate";
  }
  part def PinMapComposerMod {
    doc /* PinMapShapedRead + BoundedMatchFind (FindResult). */
    attribute path : String = "parts/common/memnet/memnet/pin_map_composer.py";
    attribute pyName : String = "memnet.pin_map_composer";
  }
  part def PeakLMod {
    attribute path : String = "parts/common/memnet/memnet/peak_l.py";
    attribute pyName : String = "memnet.peak_l";
  }
  part def NeighbourhoodReserveMod {
    attribute path : String = "parts/common/memnet/memnet/neighbourhood_reserve.py";
    attribute pyName : String = "memnet.neighbourhood_reserve";
  }
  part def SameThingAbsorbMod {
    attribute path : String = "parts/common/memnet/memnet/same_thing_absorb.py";
    attribute pyName : String = "memnet.same_thing_absorb";
  }
  part def ImportAbsorbMod {
    attribute path : String = "parts/common/memnet/memnet/import_absorb.py";
    attribute pyName : String = "memnet.import_absorb";
  }
  part def CheapLlmImportGuardMod {
    attribute path : String = "parts/common/memnet/memnet/cheap_llm_import_guard.py";
    attribute pyName : String = "memnet.cheap_llm_import_guard";
  }
  part def PinMapIngestMod {
    attribute path : String = "parts/common/memnet/memnet/pin_map_ingest.py";
    attribute pyName : String = "memnet.pin_map_ingest";
  }
  part def PinMapExportMod {
    attribute path : String = "parts/common/memnet/memnet/pin_map_export.py";
    attribute pyName : String = "memnet.pin_map_export";
  }
  part def CatalogSnapMod {
    attribute path : String = "parts/common/memnet/memnet/catalog_snap.py";
    attribute pyName : String = "memnet.catalog_snap";
  }
  part def AgensGraphAdapterMod {
    attribute path : String = "parts/common/memnet/memnet/durable/agensgraph.py";
    attribute pyName : String = "memnet.durable.agensgraph";
  }
  part def RagHostHookMod {
    attribute path : String = "parts/common/memnet/memnet/rag_host_hook.py";
    attribute pyName : String = "memnet.rag_host_hook";
  }
  part def SchemaRegistryMod {
    attribute path : String = "parts/common/memnet/memnet/schema_registry.py";
    attribute pyName : String = "memnet.schema_registry";
  }
  part def SnapshotStoreMod {
    attribute path : String = "parts/common/memnet/memnet/snapshot_store.py";
    attribute pyName : String = "memnet.snapshot_store";
  }
  part def HousekeepSettleMod {
    attribute path : String = "parts/common/memnet/memnet/housekeep_settle.py";
    attribute pyName : String = "memnet.housekeep_settle";
  }

  // ----- MCP surface modules -----

  part def McpFacadeMod {
    attribute path : String = "parts/memnet-mcp/software/memnet_mcp/mcp_facade.py";
    attribute pyName : String = "memnet_mcp.mcp_facade";
  }
  part def McpServeBridgeMod {
    attribute path : String = "parts/memnet-mcp/software/memnet_mcp/serve_bridge.py";
    attribute pyName : String = "memnet_mcp.serve_bridge";
  }
  part def LawSeedHelperMod {
    attribute path : String = "parts/memnet-mcp/software/memnet_mcp/law_seed_helper.py";
    attribute pyName : String = "memnet_mcp.law_seed_helper";
  }
  part def McpHttpTransportMod {
    doc /* Opt-in streamable-http; Multitask shared store with TCP. */
    attribute path : String = "parts/memnet-mcp/software/memnet_mcp/http_transport.py";
    attribute pyName : String = "memnet_mcp.http_transport";
  }

  // ----- Cousin product face: NOT in this repo -----

  part def CousinSysMLEdgeNotInRepo {
    doc /*
      Product invent face is sysmledge (cousin). This MemNet checkout
      MUST NOT allocate or invent that upload/bind path.
    */
    attribute pyName : String = "sysmledge";
    attribute implemented : Boolean = false;
    attribute inThisRepo : Boolean = false;
    attribute track : Boolean = false;
    attribute mustNotInventUploadBind : Boolean = true;
  }

  // ----- Usages -----

  part wheel : MemNetLlmWheel;
  part inProcessMod : InProcessEngineMod;
  part ipcMod : LocalIpcGatewayMod;
  part tcpMod : TcpServeBridgeMod;
  part serveDaemonMod : ServeDaemonMod;
  part cliMod : CliFacadeMod;
  part sessionsMod : SessionLifecycleMod;
  part storeMod : GraphStoreMod;
  part memStoreMod : MemStoreMod;
  part capsMod : CapsPolicyMod;
  part capsAclMod : CapsAclMod;
  part gqlMod : GqlCodecMod;
  part gqlPyMod : ProductGqlGateMod;
  part parseFrontMod : GraphGlotParseFrontMod;
  part mutateMod : MutateGateMod;
  part pinMapMod : PinMapComposerMod;
  part peakLMod : PeakLMod;
  part rsvMod : NeighbourhoodReserveMod;
  part sameThingMod : SameThingAbsorbMod;
  part absorbMod : ImportAbsorbMod;
  part cheapLlmMod : CheapLlmImportGuardMod;
  part ingestMod : PinMapIngestMod;
  part exportMod : PinMapExportMod;
  part catalogMod : CatalogSnapMod;
  part agensMod : AgensGraphAdapterMod;
  part ragHookMod : RagHostHookMod;
  part schemaMod : SchemaRegistryMod;
  part snapMod : SnapshotStoreMod;
  part housekeepMod : HousekeepSettleMod;
  part mcpFacadeMod : McpFacadeMod;
  part mcpBridgeMod : McpServeBridgeMod;
  part lawSeedMod : LawSeedHelperMod;
  part mcpHttpMod : McpHttpTransportMod;
  part sysmlEdgeAbsent : CousinSysMLEdgeNotInRepo;
  part tracker : ImplementationTracker;

  // ----- Allocations (SSOT → code) -----

  allocation coreToWheel : SoftwareAllocate {
    end logical ::> memNetSystem.core;
    end code ::> wheel.core;
  }
  allocation mcpToWheel : SoftwareAllocate {
    doc /* Fleet MemNet MCP = tip/ops module; not sysmledge. */
    end logical ::> memNetSystem.mcp;
    end code ::> wheel.mcp;
  }
  allocation fleetToWheel : SoftwareAllocate {
    doc /* One wheel, many hosts (droplet + devices). */
    end logical ::> opsFleet;
    end code ::> wheel;
  }
  allocation dropletServiceToCore : SoftwareAllocate {
    end logical ::> opsFleet.droplet.memnet.core;
    end code ::> wheel.core;
  }
  allocation dropletMcpToTip : SoftwareAllocate {
    end logical ::> opsFleet.droplet.memnet.mcp;
    end code ::> wheel.mcp;
  }
  allocation deviceServiceToCore : SoftwareAllocate {
    end logical ::> opsFleet.devices.service;
    end code ::> wheel.core;
  }

  allocation inProcessToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess;
    end code ::> inProcessMod;
  }
  allocation ipcToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.ipc;
    end code ::> ipcMod;
  }
  allocation tcpToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.tcp;
    end code ::> tcpMod;
  }
  allocation tcpDaemonToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.tcp;
    end code ::> serveDaemonMod;
  }
  allocation cliToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.cli;
    end code ::> cliMod;
  }
  allocation sessionsToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions;
    end code ::> sessionsMod;
  }
  allocation storeToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.store;
    end code ::> storeMod;
  }
  allocation memStoreToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.store;
    end code ::> memStoreMod;
  }
  allocation capsToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.caps;
    end code ::> capsMod;
  }
  allocation capsAclToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.caps;
    end code ::> capsAclMod;
  }
  allocation gqlToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.gqlWire;
    end code ::> gqlMod;
  }
  allocation parseFrontToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.gqlWire.parseFront;
    end code ::> parseFrontMod;
  }
  allocation productGateToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.gqlWire.productGate;
    end code ::> gqlPyMod;
  }
  allocation schemaToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.schema;
    end code ::> schemaMod;
  }
  allocation snapToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.snap;
    end code ::> snapMod;
  }
  allocation housekeepToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.housekeep;
    end code ::> housekeepMod;
  }
  allocation mutateToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.recallCommit.commit.mutate;
    end code ::> mutateMod;
  }
  allocation rsvToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.recallCommit.commit.reserve;
    end code ::> rsvMod;
  }
  allocation sameThingToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.recallCommit.commit.sameThing;
    end code ::> sameThingMod;
  }
  allocation pinMapToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.recallCommit.recall.shapedRead.pinMap;
    end code ::> pinMapMod;
  }
  allocation findToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.recallCommit.recall.shapedRead.find;
    end code ::> pinMapMod;
  }
  allocation peakLToMod : SoftwareAllocate {
    end logical ::> memNetSystem.core.transport.inProcess.memory.sessions.recallCommit.recall.seed.peak;
    end code ::> peakLMod;
  }
  allocation absorbToMod : SoftwareAllocate {
    end logical ::> memNetSystem.multitask.coordinator.importReceive.absorb;
    end code ::> absorbMod;
  }
  allocation cheapLlmToMod : SoftwareAllocate {
    end logical ::> memNetSystem.multitask.coordinator.importReceive.guard.cheapLlm;
    end code ::> cheapLlmMod;
  }
  allocation ingestToMod : SoftwareAllocate {
    end logical ::> memNetSystem.pinMaps;
    end code ::> ingestMod;
  }
  allocation exportToMod : SoftwareAllocate {
    end logical ::> memNetSystem.pinMaps.export;
    end code ::> exportMod;
  }
  allocation catalogToMod : SoftwareAllocate {
    end logical ::> memNetSystem.pinMaps.catalog;
    end code ::> catalogMod;
  }
  allocation agensToMod : SoftwareAllocate {
    end logical ::> memNetSystem.durable.agens;
    end code ::> agensMod;
  }
  allocation ragHookToMod : SoftwareAllocate {
    end logical ::> hostSearch.hook;
    end code ::> ragHookMod;
  }
  allocation mcpToolsToMod : SoftwareAllocate {
    end logical ::> memNetSystem.mcp.tools;
    end code ::> mcpFacadeMod;
  }
  allocation mcpToolsToServer : SoftwareAllocate {
    end logical ::> memNetSystem.mcp.tools;
    end code ::> wheel.mcp;
  }
  allocation mcpBridgeToMod : SoftwareAllocate {
    end logical ::> memNetSystem.mcp.bridge;
    end code ::> mcpBridgeMod;
  }
  allocation mcpHttpToMod : SoftwareAllocate {
    doc /* Streamable-http sibling of ServeBridge; Multitask shared store. */
    end logical ::> memNetSystem.multitask.sharedStore;
    end code ::> mcpHttpMod;
  }
  allocation lawSeedToMod : SoftwareAllocate {
    end logical ::> memNetSystem.mcp.seed;
    end code ::> lawSeedMod;
  }

  // CousinSysMLEdge has no SoftwareAllocate in this package.
}
