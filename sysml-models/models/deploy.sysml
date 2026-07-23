/*
  MemNet deploy — software parts for core engine (parts/common/memnet) and
  MCP server (parts/memnet-mcp). Novel-writer is out of scope.

  Satisfy: MN-REQ-00 on MemNetSystem only; leaves on implementing parts.
  Nested requirement paths: MN_REQ_00_MissionBridge::Group::Leaf.
*/
package MemNet {
  private import ScalarValues::*;
  private import MemNetConnections::*;
  private import MemNetRequirements::*;

  // --- Caps / configuration ---

  part def CapsConfig {
    doc /*
      Environment-overridable limits (MEMNET_MAX_*): rows, law, relations, tags,
      fields, value/line/batch bytes, sessions, depth, fanout, lock timeout.
      Implementation: memnet.config.Caps.
    */
    attribute maxRows : Integer = 5000;
    attribute maxLaw : Integer = 100;
    attribute maxRelations : Integer = 200;
    attribute maxSessions : Integer = 64;
    attribute maxDepth : Integer = 4;
    attribute defaultQueryMaxRows : Integer = 50;
    attribute defaultQueryDepth : Integer = 2;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_1_StoreResourceCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_2_QueryFanoutCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_2_WarmMustFitContext;
  }

  // --- Core library subsystems ---

  part def WireCodec {
    doc /*
      Split/join pipe fields; parse_tag_line; emit_record_line.
      Canonical SSOT parse/emit for agent grammar and human-faithful render.
      Implementation: memnet.wire + tag_map.parse_line + sanitiser.
    */
    port wireIn : WirePayloadInPort;
    port wireOut : WirePayloadOutPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_1_ExactlyNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_2_NodesHoldAtomisedFacts;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_3_EdgesAreFirstClass;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_5_GrammarExpressesNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_6_ParserRecoversNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_1_LlmFriendlyStdio;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_3_NoHostilePositionalDump;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_4_BoundaryFriendlyIfInternalDiffers;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_5_IoActorIsLlm;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_6_FollowPromptRules;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_8_TemplateCopyableShapes;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_5_GrammarMustBeLlmLearnable;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_6_PreferTemplateFriendlyPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_1_CanonicalParserSsot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_2_RejectInvalidWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_4_NoAdHocConsumerSplits;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_7_HumanVerifyViaParser;
  }

  part def TagMapService {
    doc /*
      Fixed + user tag defs; field validation; EDG coerce; merge_fixed.
      Implementation: memnet.tag_map, fixed_tags.
    */
    port mapSpecIn : WirePayloadInPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
  }

  part def MemStoreEngine {
    doc /*
      In-memory by_id indexes, edge adjacency, add_row / update_row (no upsert),
      query warm (LAW prepend) and walk, recycle filtering.
      Implementation: memnet.mem_store.MemStore.
    */
    port ingestIn : WirePayloadInPort;
    port warmOut : WarmSliceOutPort;
    port wireOut : WirePayloadOutPort;
    port errOut : ErrorSignalOutPort;
    attribute lawPrepend : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_1_ExactlyNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_2_NodesHoldAtomisedFacts;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_3_EdgesAreFirstClass;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_2_UpdateFailsIfAbsent;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_1_AnchoredWarmSlice;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_2_RecycleHiddenFromWarm;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_3_WarmDepthAndRowCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_4_EngineLawPrepend;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_5_AnchoredWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_2_WarmMustFitContext;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_4_ExternalGroundTruthRequired;
    doc /*
      Stats, stale/orphan/dangling/recyclable classification and prune.
      Implementation: memnet.housekeep.
    */
    port statsOut : WirePayloadOutPort;
  }

  part def SnapshotService {
    doc /*
      snapshot_text / write_snapshot / load_snapshot.
      Implementation: memnet.snapshot.
    */
    port snapOut : SnapshotOutPort;
    port snapIn : SnapshotInPort;
    port wireOut : WirePayloadOutPort;
  }

  part def SessionRegistryService {
    doc /*
      Process-wide registry of SessionStore entries with TTL purge.
      Implementation: memnet.registry + session.open_session/get_session.
    */
    port sessionOut : SessionIdOutPort;
    port sessionIn : SessionIdInPort;
    port errOut : ErrorSignalOutPort;
    part caps : CapsConfig;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_1_NamedSessions;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_3_SessionTtlAndCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_BoundaryServe::MN_REQ_06_1_SharedSessionRegistry;
  }

  part def SessionStoreFacade {
    doc /*
      Per-session handle: TagMap + MemStore + relations set + meta/TTL.
      Implementation: memnet.session.SessionStore.
    */
    part tagMap : TagMapService;
    part store : MemStoreEngine;
    part housekeep : HousekeepService;
    part snapshot : SnapshotService;
    port sessionId : SessionIdInPort;
    port wireIn : WirePayloadInPort;
    port warmOut : WarmSliceOutPort;
    port snapOut : SnapshotOutPort;
    port snapIn : SnapshotInPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_1_NamedSessions;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_2_SessionLifecycleOps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_1_NoChatAsDurableStore;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_4_ExternalGroundTruthRequired;
    doc /*
      Typer CLI: session_*, query_*, add/update, read_*, housekeep_*, serve.
      Implementation: memnet.cli. Routes via serve_client when serve is up.
    */
    port cmdOut : ServeCommandOutPort;
    port wireIn : WirePayloadInPort;
    port wireOut : WirePayloadOutPort;
    port sessionOut : SessionIdOutPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_1_LlmFriendlyStdio;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_3_NoHostilePositionalDump;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_5_IoActorIsLlm;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_6_FollowPromptRules;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_3_ParseFaithfulInspect;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_3_MinimiseTokenRoundTrips;
  }

  part def MemNetServeDaemon {
    doc /*
      Threading TCP server; length-prefixed JSON {args, stdin} -> CLI dispatch
      with MEMNET_SERVE_INTERNAL. Holds live SessionRegistryService.
      Implementation: memnet.serve.
    */
    port cmdIn : ServeCommandInPort;
    port envelopeOut : JsonEnvelopeOutPort;
    attribute host : String = "127.0.0.1";
    attribute listenPort : Integer = 18765;
    part registry : SessionRegistryService;
    part sessionFacade : SessionStoreFacade;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_BoundaryServe::MN_REQ_06_1_SharedSessionRegistry;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_BoundaryServe::MN_REQ_06_2_LocalServeEndpoint;
  }

  part def MemNetCoreLibrary {
    doc /*
      Shared Python package allocated to parts/common/memnet.
      Composite of engine services used by CLI and serve.
    */
    part codec : WireCodec;
    part cli : MemNetCliApp;
    part serve : MemNetServeDaemon;
  }

  // --- MCP server ---

  part def MemNetServeClient {
    doc /*
      Probe + run_memnet: TCP to serve or optional test inline.
      Implementation: memnet_mcp.client + memnet.serve_client.
    */
    port cmdOut : ServeCommandOutPort;
    port envelopeIn : JsonEnvelopeInPort;
    port sessionOut : SessionIdOutPort;
  }

  part def MemNetSeedHelper {
    doc /*
      Prepends LAW01-LAW05 when missing from seed_lines (session_open).
      Implementation: memnet_mcp.seed.supplement_seed_lines.
    */
    port seedOut : WirePayloadOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_4_McpLawSeedOnOpen;
  }

  part def MemNetMcpToolSurface {
    doc /*
      FastMCP stdio tools: serve_status, session_open/current/load/save,
      query_warm/walk, add, update, read_get, read_list, housekeep_stats.
      Each tool returns JsonEnvelope string to the host.
      Implementation: memnet_mcp.server. Invokes MemNetServeClient in-process.
    */
    port hostOut : JsonEnvelopeOutPort;
    port fromHost : WirePayloadInPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_1_GenericToolSurface;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_2_StructuredToolEnvelope;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_3_NoDomainProductTools;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_2_LlmFriendlyMcp;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_3_NoHostilePositionalDump;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_5_IoActorIsLlm;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_6_FollowPromptRules;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_8_TemplateCopyableShapes;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_5_GrammarExpressesNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_3_ParseFaithfulInspect;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_5_GrammarMustBeLlmLearnable;
  }

  part def MemNetMcpServer {
    doc /*
      Product surface parts/memnet-mcp/software/memnet_mcp.
      Binds MCP host to memnet serve via MemNetServeClient.
      Host-facing JSON results are on tools.hostOut (stdio tool return).
    */
    part tools : MemNetMcpToolSurface;
    part client : MemNetServeClient;
    part seed : MemNetSeedHelper;
    port fromHost : WirePayloadInPort;
  }

  // --- System composite ---

  part def MemNetSystem {
    doc /*
      MemNet software system: core library + MCP server over serve TCP.
      Novel-writer is out of scope for this system — not nested here.
      Only MN-REQ-00 is satisfied here; leaves are on implementing parts.
    */
    part core : MemNetCoreLibrary;
    part mcp : MemNetMcpServer;

    // Serve client -> serve daemon (production path)
    connection clientToServe : ServeCommandFlow {
      end port source ::> mcp.client.cmdOut;
      end port sink ::> core.serve.cmdIn;
    }
    // Serve JSON envelope back to MCP client
    connection serveToMcp : JsonEnvelopeFlow {
      end port source ::> core.serve.envelopeOut;
      end port sink ::> mcp.client.envelopeIn;
    }
    // CLI optional parallel path to same serve
    connection cliToServe : ServeCommandFlow {
      end port source ::> core.cli.cmdOut;
      end port sink ::> core.serve.cmdIn;
    }

    satisfy MN_REQ_00_MissionBridge;
  }

  // Convenience alias for deployment root usage
  part memNetSystem : MemNetSystem;
}
