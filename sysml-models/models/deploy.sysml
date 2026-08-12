/*
  MemNet deploy — TARGET architecture after ADR-001.

  Product framing (2026-08-13): MemNet = shared LLM memory (SharedLlmMemory);
  session id = pass-by-reference handle for a MissionWorkingSet; durable GQL
  store (DurableBuffer / AgensGraphAdapter) planned M2.5 behind MemNet.

  Nesting (coarse → fine):
    MemNetSystem                    // SharedLlmMemory product
    ├── AgentMemory                 // session-scoped working set + GQL wire
    │   ├── GraphStore
    │   ├── GqlWire                 // 1.x primary codec (openCypher-shaped)
    │   ├── PinMapShapedRead        // shaped pin_map (Write = display)
    │   ├── MutateGate / SessionLifecycle / Schema / Caps / …
    │   └── (TierACodec quarantined — remove in M2; not nested accept)
    ├── TransportBoundary           // InProcess / LocalIpc / TcpServe
    ├── MemNetMcpServer             // LLM ↔ MemNet (GQL/MCP)
    ├── DurableBuffer               // AgensGraphAdapter planned M2.5
    ├── PinMapRoadmap
    └── MultitaskOperatingModel
        ├── MultitaskCoordinator          // team lead
        │   └── SessionImportReceive
        │       ├── ImportGuard           // cheap LLM soft review
        │       └── ImportAbsorb          // hard gates + import + settle
        ├── MultitaskWorker               // team member (handoff in + slice export)
        └── MultitaskSharedStoreBinding

  Satisfy: MN-REQ-00 on MemNetSystem only; leaves on implementing parts.
*/
package MemNet {
  private import ScalarValues::*;
  private import MemNetConnections::*;
  private import MemNetRequirements::*;

  // =====================================================================
  // Caps / schema / identity (leaves under AgentMemory)
  // =====================================================================

  part def CapsPolicy {
    doc /*
      Hard resource and query caps (env-overridable): rows, law, relations,
      kinds/fields, value/line/batch bytes, sessions, depth, fanout.
      As-is: memnet.config.Caps.
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
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_2_PinMapMustFitContext;
  }

  part def SchemaRegistry {
    doc /*
      Session schema: node Labels and Properties; relationship-type set;
      validate ingest; reject unknown/reserved kinds.
      As-is: memnet.tag_map + fixed_tags (positional TagMap is legacy surface).
    */
    port schemaIn : SchemaInPort;
    port schemaOut : SchemaOutPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
  }

  part def GqlCodec {
    doc /*
      Primary agent wire SSOT (1.x teach, ADR-001): parse/emit openCypher-shaped
      GQL under MemNet gates. External dialect authority = openCypher CIP tree
      + oC9 baseline (adopted/testable CIPs); ISO/IEC 39075 for GQL-native
      features — agent surface remains MemNet-gated (pin_map + mutate subset),
      not full openCypher / every CIP. Mutate accepts GQL patterns; pin_map
      emit is a shaped subgraph (same graph family — redefined Write = display).
      MUST NOT treat raw tabular RETURN as primary goldfish read.
      Target; engine accept path lands in ADR migration M2.
      Detail: docs/grammar/gql-wire-profile.md (External dialect authority).
    */
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    port shapedOut : ShapedSubgraphOutPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_1_ExactlyNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_2_NodesHoldAtomisedFacts;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_3_EdgesAreFirstClass;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_5_GrammarExpressesNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_6_ParserRecoversNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_1_LlmFriendlyStdio;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_3_NoHostilePositionalDump;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_4_BoundaryFriendlyIfInternalDiffers;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_5_IoActorIsLlm;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_6_FollowPromptRules;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_8_TemplateCopyableShapes;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_9_PinMapEmitSameAsMutate;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_1_CanonicalParserSsot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_2_RejectInvalidWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_4_NoAdHocConsumerSplits;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_5_GrammarMustBeLlmLearnable;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_6_PreferTemplateFriendlyPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_7_HumanVerifyViaParser;
  }

  part def TierACodec {
    doc /*
      QUARANTINED — as-is engine lag (memnet.tier_a). Former Layer / Tier A
      NODE|EDGE ASCII. MUST NOT be nested as target accept or 1.x teach.
      Remove from product path in M2. Primary wire is GqlCodec.
    */
    port tierAIn : TierAInPort;
    port tierAOut : TierAOutPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port errOut : ErrorSignalOutPort;
    attribute quarantineRemoveInM2 : Boolean = true;
  }

  part def LegacyPipeImport {
    doc /*
      DEPRECATED — not in MemNetSystem target composition. One-shot import
      of historical @TAG pipe session blobs; convert then discard.
    */
    port legacyIn : LegacyPipeInPort;
    port recordsOut : GraphRecordOutPort;
    port errOut : ErrorSignalOutPort;
    attribute implemented : Boolean = false;
  }

  part def IdAllocator {
    doc /*
      Two mint paths: (1) LLM goldfish mutate -- NEW -> engine id;
      (2) PinMapIngest_* -- deterministic id from locator key.
      As-is: memnet.id_allocator.
    */
    port recordsIn : GraphRecordInPort;
    port recordsOut : GraphRecordOutPort;
    port idsOut : AssignedIdOutPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_4_ExternalGroundTruthRequired;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  // =====================================================================
  // Graph store / shaped read / mutate
  // =====================================================================

  part def GraphStore {
    doc /*
      In-memory Net of Memory: property-graph working set with Node and
      Edge indexes, adjacency, properties, labels; strict create/replace.
      Dual EDGE: bind vs relation as relationship types / endpoint grain.
      Law-on-node as node properties (+ port structure). Agent wire is GQL
      via GqlCodec. Realises session-scoped SharedLlmMemory content.
      As-is: memnet.mem_store.MemStore (+ models).
    */
    port recordsIn : GraphRecordInPort;
    port recordsOut : GraphRecordOutPort;
    port errOut : ErrorSignalOutPort;
    part caps : CapsPolicy;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_1_ExactlyNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_2_NodesHoldAtomisedFacts;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_3_EdgesAreFirstClass;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_2_UpdateFailsIfAbsent;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_1_NoChatAsDurableStore;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_4_ExternalGroundTruthRequired;
  }

  part def MutateGate {
    doc /*
      Orchestrates GQL parse -> schema validate -> NEW mint -> strict
      add/update into GraphStore -> assigned ids + ack. Owns IdAllocator;
      uses sibling SchemaRegistry / GqlCodec / GraphStore via AgentMemory
      wiring. As-is may still parse line codecs until M2 remove — not target
      accept doctrine.
    */
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port idsOut : AssignedIdOutPort;
    port errOut : ErrorSignalOutPort;
    part allocator : IdAllocator;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_2_UpdateFailsIfAbsent;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
  }

  part def PinMapShapedRead {
    doc /*
      pin_map-class tool (ADR-001 recommendation B+A): wraps GQL internally;
      emits bounded shaped subgraph (ShapedSubgraph / LivePinMap) — redefined
      Write = display. Hide recyclable rows; depth/row/view caps; prepend
      engine-law rows. As-is name: PinMapComposer / query pin-map.
      MUST NOT emit raw unbounded RETURN tables as primary agent read.
    */
    port pinMapOut : LivePinMapOutPort;
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;
    attribute lawPrepend : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_1_AnchoredPinMap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_2_RecycleHiddenFromPinMap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_3_PinMapDepthAndRowCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_4_EngineLawPrepend;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_9_PinMapEmitSameAsMutate;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_2_PinMapMustFitContext;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_3_MinimiseTokenRoundTrips;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
  }

  part def WalkQuery {
    doc /*
      Anchored walk hop lines over Node|Edge without loading whole graph.
      As-is: mem_store query walk.
    */
    port walkOut : WalkSliceOutPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_5_AnchoredWalk;
  }

  part def HousekeepSettle {
    doc /*
      Stats, stale/orphan/dangling/recyclable classification, settle/prune.
      Recycle policy feeds PinMapShapedRead hide rules.
    */
    port statsOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_2_RecycleHiddenFromPinMap;
  }

  part def SnapshotStore {
    doc /*
      Named-session durable file: save/load schema + records + relations
      (MN-REQ-01.4--01.6). MUST NOT be taken as MN-REQ-11 pin-map export.
    */
    port snapOut : SessionSnapshotOutPort;
    port snapIn : SessionSnapshotInPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_4_SaveSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_5_LoadSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_6_OptionalKeepSessionId;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
  }

  // =====================================================================
  // AgentMemory — nested working-memory product heart
  // =====================================================================

  part def SessionLifecycle {
    doc /*
      Process-wide registry of named sessions with TTL purge; per-session
      GraphStore + SchemaRegistry + query/mutate facades. Each session id is
      the pass-by-reference handle for a MissionWorkingSet (SOMETHING).
      Nested under AgentMemory (SharedLlmMemory). As-is: memnet.registry +
      session. Optional M2.5 hydrate/flush ports to DurableBuffer.
    */
    port sessionOut : SessionIdOutPort;
    port sessionIn : SessionIdInPort;
    port schemaIn : SchemaInPort;
    port snapOut : SessionSnapshotOutPort;
    port snapIn : SessionSnapshotInPort;
    port hydrateIn : DurableHydrateInPort;
    port flushOut : DurableFlushOutPort;
    port importReqIn : SessionImportRequestInPort;
    port sliceIn : WorkingMemorySliceInPort;
    port errOut : ErrorSignalOutPort;
    part caps : CapsPolicy;
    part schema : SchemaRegistry;
    part gqlWire : GqlCodec;
    part store : GraphStore;
    part mutate : MutateGate;
    part shapedRead : PinMapShapedRead;
    part walk : WalkQuery;
    part housekeep : HousekeepSettle;
    part snap : SnapshotStore;

    connection gqlParseToMutate : GraphRecordFlow {
      end port source ::> gqlWire.recordsOut;
      end port sink ::> mutate.recordsIn;
    }
    connection mutateToStore : GraphRecordFlow {
      end port source ::> mutate.recordsOut;
      end port sink ::> store.recordsIn;
    }

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_1_NamedSessions;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_2_SessionLifecycleOps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_3_SessionTtlAndCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_5_LoadSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_6_OptionalKeepSessionId;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_7_SessionAsSsotHandle;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_8_NoGraphDumpHandoff;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_1_InProcessPrimary;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_1_NoChatAsDurableStore;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_9_LeadOwnsSessionImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
  }

  part def AgentMemory {
    doc /*
      SharedLlmMemory realisation: session-scoped property-graph working
      memory with GQL wire. Nested GraphStore, GqlCodec, PinMapShapedRead,
      MutateGate, SessionLifecycle. Brand = MemNet. TierACodec not nested.
    */
    part sessions : SessionLifecycle;
    port sessionOut : SessionIdOutPort;
    port gqlIn : GqlWireInPort;
    port shapedOut : ShapedSubgraphOutPort;
    port pinMapOut : LivePinMapOutPort;
    port hydrateIn : DurableHydrateInPort;
    port flushOut : DurableFlushOutPort;
  }

  // =====================================================================
  // Transport boundary
  // =====================================================================

  part def InProcessEngine {
    doc /*
      Primary binding: AgentMemory / SessionLifecycle in the same process
      as the caller (MCP or library). Lowest latency; no serialised hop.
    */
    port apiIn : InProcessInPort;
    port envelopeOut : JsonEnvelopeOutPort;
    part memory : AgentMemory;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_1_InProcessPrimary;
  }

  part def LocalIpcGateway {
    doc /*
      Secondary: share one session registry across CLI + MCP processes via
      named pipe (Windows) or AF_UNIX (POSIX). As-is: not implemented.
    */
    port ipcIn : LocalIpcInPort;
    port envelopeOut : JsonEnvelopeOutPort;
    attribute implemented : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_2_LocalIpcShare;
  }

  part def TcpServeBridge {
    doc /*
      Migration / multi-process fallback: length-prefixed JSON over TCP
      localhost. Under Multitask this path (or streamable-http / LocalIpc)
      is the shared-store binding (MN-REQ-12.2).
    */
    port cmdIn : ServeCommandInPort;
    port envelopeOut : JsonEnvelopeOutPort;
    attribute host : String = "127.0.0.1";
    attribute listenPort : Integer = 18765;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_3_TcpServeMigration;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_2_SharedStoreTransport;
  }

  part def TransportBoundary {
    doc /*
      How clients bind to AgentMemory: in-process primary, local IPC,
      TCP/http for shared Multitask.
    */
    part inProcess : InProcessEngine;
    part ipc : LocalIpcGateway;
    part tcp : TcpServeBridge;
  }

  // =====================================================================
  // Facades / MCP
  // =====================================================================

  part def CliFacade {
    doc /*
      Agent/human CLI. Presents GQL wire on stdio (target). As-is may still
      speak line codecs until M2 remove — not target accept doctrine.
      As-is: memnet.cli (+ serve_client).
    */
    port apiOut : InProcessOutPort;
    port ipcOut : LocalIpcOutPort;
    port cmdOut : ServeCommandOutPort;
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    port sessionOut : SessionIdOutPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_2_SessionLifecycleOps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_4_SaveSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_5_LoadSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_6_OptionalKeepSessionId;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_1_LlmFriendlyStdio;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_3_NoHostilePositionalDump;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_4_BoundaryFriendlyIfInternalDiffers;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_5_IoActorIsLlm;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_6_FollowPromptRules;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_3_ParseFaithfulInspect;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_3_MinimiseTokenRoundTrips;
  }

  part def ServeBridge {
    doc /*
      Optional TCP client to TcpServeBridge (Multitask shared store).
    */
    port cmdOut : ServeCommandOutPort;
    port envelopeIn : JsonEnvelopeInPort;
    port sessionOut : SessionIdOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_2_SharedStoreTransport;
  }

  part def LawSeedHelper {
    doc /*
      On MCP session_open, auto-seed engine-law rows when missing.
      Target emit via GQL/shaped path.
    */
    port gqlOut : GqlWireOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_4_McpLawSeedOnOpen;
  }

  part def McpFacade {
    doc /*
      Generic FastMCP tools. Agent memory payloads: GQL mutate + shaped
      pin_map (target). Structured JSON envelopes. No domain-product tools.
      LLM agents connect here to MemNet — not to DurableBuffer.
    */
    port apiOut : InProcessOutPort;
    port hostOut : JsonEnvelopeOutPort;
    port fromHost : GqlWireInPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_4_SaveSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_5_LoadSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_6_OptionalKeepSessionId;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_1_InProcessPrimary;
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

  part def MemNetCoreLibrary {
    doc /*
      Target core composite allocated to parts/common/memnet.
      Nest: TransportBoundary (InProcessEngine owns AgentMemory) + CliFacade.
      AgentMemory lives under transport.inProcess.memory — one instance.
    */
    part transport : TransportBoundary;
    part cli : CliFacade;
  }

  part def MemNetMcpServer {
    doc /*
      Product surface parts/memnet-mcp — generic tools only.
    */
    part tools : McpFacade;
    part bridge : ServeBridge;
    part seed : LawSeedHelper;
    port fromHost : GqlWireInPort;
  }

  // =====================================================================
  // Durable buffer (planned M2.5) — AgensGraph behind SharedLlmMemory
  // =====================================================================

  part def AgensGraphAdapter {
    doc /*
      PLANNED M2.5: hydrate/flush between SessionLifecycle / GraphStore and
      DurableGraphStore (AgensGraph-class). Same GQL family. Not shipped.
      MUST NOT dual-write without a single sync owner. MUST NOT be the LLM
      primary path (LLM ↔ MemNet only).
    */
    port hydrateOut : DurableHydrateOutPort;
    port flushIn : DurableFlushInPort;
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    attribute implemented : Boolean = false;
    attribute phase : String = "M2.5";
  }

  part def DurableBuffer {
    doc /*
      Optional durable property-graph buffer behind MemNet SharedLlmMemory.
      Connects to GraphStore / SessionLifecycle via hydrate/flush — not to
      LLM agents as primary. Planned M2.5 after engine GQL (M2).
    */
    part agens : AgensGraphAdapter;
    port hydrateOut : DurableHydrateOutPort;
    port flushIn : DurableFlushInPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_4_DurableStoreBehindMemNet;
  }

  // =====================================================================
  // MN-REQ-11 pin-map roadmap stubs
  // =====================================================================

  part def PinMapIngest_Sysml {
    doc /*
      ROADMAP stub: export/import selective SysML v2 pin maps as Node|Edge.
    */
    port pinOut : PinMapOutPort;
    port pinIn : PinMapInPort;
    port recordsOut : GraphRecordOutPort;
    attribute implemented : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_1_ExportGraphToSysmlV2;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_2_NodeMapsToSysmlStructure;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_3_EdgeMapsToSysmlConnection;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_5_SysmlRoundTripShould;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapIngest_Codebase {
    doc /*
      ROADMAP stub: ingest selective codebase pins (modules/symbols).
    */
    port pinIn : PinMapInPort;
    port recordsOut : GraphRecordOutPort;
    attribute implemented : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_6_SnapshotCodebaseIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_7_CodebaseNodesAreModulesSymbols;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_8_CodebaseEdgesAreRelations;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapIngest_PcbaAto {
    doc /*
      ROADMAP stub: PCBA schematic (.ato) pins + connectivity.
    */
    port pinIn : PinMapInPort;
    port recordsOut : GraphRecordOutPort;
    attribute implemented : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_9_SnapshotAtoIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_14_PcbaAtoNodesAreNetsComponentsPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_15_PcbaAtoEdgesAreConnectivity;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapIngest_SkillsRules {
    doc /*
      ROADMAP stub: agent skills/rules pin maps.
    */
    port pinIn : PinMapInPort;
    port recordsOut : GraphRecordOutPort;
    attribute implemented : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_10_SnapshotSkillsAndRulesIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_11_SkillsAndRulesAreNodes;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_12_SkillsRulesEdgesAreRelations;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapRoadmap {
    doc /* Composite of MN-REQ-11 roadmap stubs. */
    part sysml : PinMapIngest_Sysml;
    part codebase : PinMapIngest_Codebase;
    part pcbaAto : PinMapIngest_PcbaAto;
    part skillsRules : PinMapIngest_SkillsRules;
  }

  // =====================================================================
  // Multitask Mode (MN-REQ-12) — nested until clear
  // Team lead imports member working memory (not "session merge").
  // =====================================================================

  part def ImportAbsorb {
    doc /*
      Hard-gate absorb of an allowed/trimmed WorkingMemorySlice into the
      lead/mission session: schema, caps, id policy (Cypher MERGE upsert /
      reject / remint NEW), nodes then edges, then lead may settle TSK_*.
      Product verb = import. Cypher MERGE and micro merge=true are not this
      part. Runs after ImportGuard soft allow/trim.
    */
    attribute doctrineAsIs : Boolean = true;
    port sliceIn : WorkingMemorySliceInPort;
    port decisionIn : ImportGuardDecisionInPort;
    port importReqIn : SessionImportRequestInPort;
    port gqlOut : GqlWireOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_9_LeadOwnsSessionImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
  }

  part def ImportGuard {
    doc /*
      Cheap-LLM soft reviewer nested under SessionImportReceive, before
      ImportAbsorb. Soft checks: assigned scope?, junk/off-mission?, invented
      ids vs copy-from-pin_map?, oversized / settle noise?. Outcomes: allow /
      trim / reject + short reason (ImportGuardDecision). MUST NOT replace
      engine hard gates. MUST NOT make guard chat the SSOT. costTier =
      cost/latency class only (no vendor model id).
    */
    attribute doctrineAsIs : Boolean = true;
    attribute costTier : String = "cheap";
    attribute implemented : Boolean = false;
    port sliceIn : WorkingMemorySliceInPort;
    port sliceOut : WorkingMemorySliceOutPort;
    port decisionOut : ImportGuardDecisionOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_11_CheapLlmImportGuardSoft;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
  }

  part def SessionImportReceive {
    doc /*
      Team-lead nest: import a member's working memory into the mission
      session. Path B spine: ImportGuard (soft) → ImportAbsorb (hard) →
      settle. Path A shared-session skips this nest (re-pin_map only).
      Slice enters at guard.sliceIn; decision+slice pass to absorb.
      Hosts behaviour SessionImportReceive states.
    */
    part guard : ImportGuard;
    part absorb : ImportAbsorb;

    connection guardSliceToAbsorb : WorkingMemorySliceFlow {
      end port source ::> guard.sliceOut;
      end port sink ::> absorb.sliceIn;
    }
    connection guardDecisionToAbsorb : ImportGuardDecisionFlow {
      end port source ::> guard.decisionOut;
      end port sink ::> absorb.decisionIn;
    }

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_9_LeadOwnsSessionImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_11_CheapLlmImportGuardSoft;
  }

  part def MultitaskCoordinator {
    doc /*
      Team lead. Delivers SessionHandoff (session id only). Owns nested
      SessionImportReceive (ImportGuard + ImportAbsorb) for path B import.
      Path A: re-pin_map on shared session — import nest skipped.
    */
    attribute doctrineAsIs : Boolean = true;
    port sessionOut : SessionIdOutPort;
    port handoffOut : SessionHandoffOutPort;
    port importReqOut : SessionImportRequestOutPort;
    port gqlOut : GqlWireOutPort;
    port pinIn : PinMapInPort;
    part importReceive : SessionImportReceive;

    connection leadImportReqToAbsorb : SessionImportRequestFlow {
      end port source ::> importReqOut;
      end port sink ::> importReceive.absorb.importReqIn;
    }

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_1_SharedSessionMissionSsot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_3_ParentOwnsTaskLifecycle;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_5_PreferOneWorkerOrDisjoint;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_6_ParentEndTurnNoPoll;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_8_AppliesToRelevantTasks;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_9_LeadOwnsSessionImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_7_SessionAsSsotHandle;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_8_NoGraphDumpHandoff;
  }

  part def MultitaskWorker {
    doc /*
      Team member. Accepts SessionHandoff; pin_map first; mutate under
      WorkerWriteScope; path B exports WorkingMemorySlice for lead import.
      MUST NOT settle parent TSK_* unless delegated; chat is not SSOT.
    */
    attribute doctrineAsIs : Boolean = true;
    port sessionIn : SessionIdInPort;
    port handoffIn : SessionHandoffInPort;
    port sliceOut : WorkingMemorySliceOutPort;
    port pinIn : PinMapInPort;
    port gqlOut : GqlWireOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_1_SharedSessionMissionSsot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_4_WorkerPinMapAndScopedWrite;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_8_AppliesToRelevantTasks;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_7_SessionAsSsotHandle;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_8_NoGraphDumpHandoff;
  }

  part def MultitaskSharedStoreBinding {
    doc /*
      Multitask MUST bind to one shared store (TCP / streamable-http / IPC).
    */
    attribute doctrineAsIs : Boolean = true;
    attribute prefersTcpOrHttp : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_2_SharedStoreTransport;
  }

  part def MultitaskOperatingModel {
    doc /*
      Nested Multitask spine (MN-REQ-12):
        coordinator (lead)
          └── importReceive
                ├── guard     // cheap LLM soft review
                └── absorb    // hard gates + import + settle
        worker (member) — handoff in + WorkingMemorySlice export
        sharedStore
      Story: SessionHandoffById → (shared re-pin_map | ImportReceive →
      Guard → Absorb → Settle).
    */
    part coordinator : MultitaskCoordinator;
    part worker : MultitaskWorker;
    part sharedStore : MultitaskSharedStoreBinding;

    connection sessionHandoff : SessionHandoffFlow {
      end port source ::> coordinator.handoffOut;
      end port sink ::> worker.handoffIn;
    }
    connection memberSliceToLeadImport : WorkingMemorySliceFlow {
      end port source ::> worker.sliceOut;
      end port sink ::> coordinator.importReceive.guard.sliceIn;
    }
  }

  // =====================================================================
  // System composite
  // =====================================================================

  part def MemNetSystem {
    doc /*
      SharedLlmMemory product: MemNet software system — nested until clear.
      AgentMemory (via core) + Transport + MCP (LLM ↔ MemNet) + DurableBuffer
      (M2.5 behind sessions) + pin-map roadmap + Multitask (session-id handoff).
      Novel-writer out of scope. LegacyPipeImport / TierACodec not nested.
      Only MN-REQ-00 satisfied here.
    */
    part core : MemNetCoreLibrary;
    part mcp : MemNetMcpServer;
    part durable : DurableBuffer;
    part pinMaps : PinMapRoadmap;
    part multitask : MultitaskOperatingModel;

    connection mcpInProcess : InProcessFlow {
      end port source ::> mcp.tools.apiOut;
      end port sink ::> core.transport.inProcess.apiIn;
    }
    connection cliInProcess : InProcessFlow {
      end port source ::> core.cli.apiOut;
      end port sink ::> core.transport.inProcess.apiIn;
    }
    connection mcpTcpFallback : ServeCommandFlow {
      end port source ::> mcp.bridge.cmdOut;
      end port sink ::> core.transport.tcp.cmdIn;
    }
    connection tcpToMcp : JsonEnvelopeFlow {
      end port source ::> core.transport.tcp.envelopeOut;
      end port sink ::> mcp.bridge.envelopeIn;
    }
    connection cliTcpFallback : ServeCommandFlow {
      end port source ::> core.cli.cmdOut;
      end port sink ::> core.transport.tcp.cmdIn;
    }
    connection durableHydrate : DurableHydrateFlow {
      end port source ::> durable.agens.hydrateOut;
      end port sink ::> core.transport.inProcess.memory.sessions.hydrateIn;
    }
    connection durableFlush : DurableFlushFlow {
      end port source ::> core.transport.inProcess.memory.sessions.flushOut;
      end port sink ::> durable.agens.flushIn;
    }

    satisfy MN_REQ_00_MissionBridge;
  }

  part memNetSystem : MemNetSystem;
}
