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
    │   ├── MutateGate / SessionLifecycle / Schema / Caps (size + shipped ACL) / …
    │   └── (TierACodec RETIRED/REJECTED on product path — M2 done; not nested)
    ├── TransportBoundary           // InProcess / LocalIpc / TcpServe
    ├── MemNetMcpServer             // LLM ↔ MemNet (GQL/MCP)
    ├── DurableBuffer               // AgensGraphAdapter planned M2.5
    ├── PinMapRoadmap               // ROADMAP-ONLY stub nest (PinMapIngest variants)
    └── MultitaskOperatingModel
        ├── MultitaskCoordinator          // team lead
        │   ├── SessionHandoffEmit        // session id + scope handoff
        │   ├── AsyncTaskDispatch         // spawn N workers; end turn
        │   └── SessionImportReceive      // path B only
        │       ├── ImportGuard           // OPTIONAL cheap LLM soft policy
        │       └── ImportAbsorb          // hard gates + import + settle
        ├── WorkerPool                    // logical parallel members
        │   └── MultitaskWorker[1..*]     // async; WorkerScopedTurn host
        └── MultitaskSharedStoreBinding
  Happy path Multitask: Path A shared session → re-pin_map (no ImportGuard).

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
      Size caps plus the shipped CapsPolicy ACL cut:
        As-is NOW (0.4.x engine): memnet.config.Caps supplies resource/query
          size limits (rows, law, relations, kinds/fields, value/line/batch
          bytes, sessions, depth, fanout), and memnet.acl enforces, when
          session ACL is enabled, (1) who-check (CallerId), (2) pin_map
          (read) versus mutate permission, (3) WorkerWriteScope HARD reject
          on out-of-scope mutate, and (4) optional SessionBind (missionId +
          lease). ACL is off by default for the legacy-green path.
      In-process MAY skip bind under MEMNET_SERVE_INTERNAL; an
      InvestorApi-style boundary with require_bind=true enforces it when
      configured. sessionId is a secret capability and never waives mutate.
      engineAclShipped=true. MutateGate and PinMapShapedRead apply the
      engine ACL cut; SessionHandoff carries the capability and scope.
      Neighbourhood reserve (RSV), Path-B PinMapIngest, and full
      private/shared/open session_token modes WAIT — not this cut. No
      EvidenceCentre / MissionDock / CompanyMemory nest under MemNetSystem.
    */
    attribute maxRows : Integer = 5000;
    attribute maxLaw : Integer = 100;
    attribute maxRelations : Integer = 200;
    attribute maxSessions : Integer = 64;
    attribute maxDepth : Integer = 4;
    attribute defaultQueryMaxRows : Integer = 50;
    attribute defaultQueryDepth : Integer = 2;
    // Shipped CapsPolicy ACL flags; ACL is enabled per session.
    attribute aclWhoCheck : Boolean = true;
    attribute aclPinMapVsMutate : Boolean = true;
    attribute aclWorkerWriteScopeHardReject : Boolean = true;
    attribute aclOptionalBindMatch : Boolean = true;
    attribute engineAclShipped : Boolean = true;
    attribute doctrineAsIs : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_1_StoreResourceCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_2_QueryFanoutCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_2_PinMapMustFitContext;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
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
      GQL under MemNet gates. External dialect authority:
        - openCypher CIP tree (github.com/opencypher/openCypher/tree/main/cip)
        - oC9 baseline under cip/0.baseline (adopted/testable CIPs)
        - ISO/IEC 39075 for GQL-native features
      Agent surface remains MemNet-gated (pin_map + mutate subset) — not full
      openCypher / every CIP. Mutate accepts GQL patterns; pin_map emit is a
      shaped subgraph (Write = display). MUST NOT treat raw tabular RETURN as
      primary goldfish read. Engine accept path = ADR migration M2 (**shipped**).
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
      RETIRED / REJECTED on product path (ADR-001 M2 **done**): former Layer /
      Tier A NODE|EDGE ASCII (MemNetLayer.g4 / memnet.tier_a). MutateGate
      rejects with legacy_dialect_retired. MUST NOT be nested as accept or
      1.x teach. Kept for archive/tests / as-is traceability only — not a
      “remove in M2” TODO. Primary wire is GqlCodec.
    */
    port tierAIn : TierAInPort;
    port tierAOut : TierAOutPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port errOut : ErrorSignalOutPort;
    attribute productPathRetired : Boolean = true;
    attribute mustNotNestOnProductPath : Boolean = true;
  }

  part def LegacyPipeImport {
    doc /*
      RETIRED archive — MUST NOT nest on product path. One-shot import of
      historical @TAG pipe session blobs; convert then discard. Kept for
      as-is traceability only (not first-class product).
    */
    port legacyIn : LegacyPipeInPort;
    port recordsOut : GraphRecordOutPort;
    port errOut : ErrorSignalOutPort;
    attribute implemented : Boolean = false;
  }

  part def IdAllocator {
    doc /*
      Two mint paths: (1) LLM goldfish mutate -- NEW -> engine id;
      (2) PinMapIngest (roadmap) -- deterministic id from locator key.
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
      wiring. Layer/Tier A accept retired (M2). Consults CapsPolicy: size
      caps (as-is) plus the shipped CapsPolicy ACL cut when session ACL is
      enabled: who-check, mutate permission (distinct from pin_map read),
      WorkerWriteScope HARD reject, and optional SessionBind match. ACL is
      off by default for the legacy-green path. As-is module:
      memnet.mutate_gate + memnet.acl (GQL primary; @TAG pipe import-once).
    */
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port idsOut : AssignedIdOutPort;
    port errOut : ErrorSignalOutPort;
    part allocator : IdAllocator;
    part caps : CapsPolicy;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_2_UpdateFailsIfAbsent;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
  }

  part def PinMapShapedRead {
    doc /*
      pin_map-class tool (ADR-001 recommendation B+A): wraps graph walk;
      emits bounded shaped openCypher-family subgraph (ShapedSubgraph /
      LivePinMap) — redefined Write = display. Hide recyclable rows;
      depth/row/view caps; prepend engine-law rows.
      Consults CapsPolicy: size/depth/row caps plus the shipped ACL cut when
      session ACL is enabled — who-check, pin_map read permission distinct
      from mutate, and optional SessionBind match. MUST NOT emit raw
      unbounded RETURN tables as primary agent read.
      As-is: memnet.pin_map_composer.PinMapComposer / query pin-map (M2).
      ACL is off by default; engineAclShipped=true.
    */
    port pinMapOut : LivePinMapOutPort;
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;
    attribute lawPrepend : Boolean = true;
    part caps : CapsPolicy;

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
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
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
      Agent/human CLI. Presents GQL wire on stdio (target / product path).
      TierA / Layer line codecs are RETIRED on product path (M2 done) — not
      target accept doctrine. As-is: memnet.cli (+ serve_client).
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
  // MN-REQ-11 pin-map roadmap (stubs only — not product accept spine)
  // =====================================================================

  part def PinMapIngest {
    doc /*
      ROADMAP-ONLY stub: selective pin-map ingest/export as Node|Edge.
      Variants (domain attribute): sysml | codebase | pcbaAto | skillsRules.
      Collapses former PinMapIngest_* four-part zoo — not shipped engines.
      Seed external locators via seed_lines / explicit add until implemented.
      Distinct from session SnapshotStore and from live PinMapShapedRead.
    */
    attribute domainVariant : String = "sysml";
    // Allowed domainVariant values (doc only): "sysml", "codebase",
    // "pcbaAto", "skillsRules".
    port pinOut : PinMapOutPort;
    port pinIn : PinMapInPort;
    port recordsOut : GraphRecordOutPort;
    attribute implemented : Boolean = false;
    attribute roadmapOnly : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_1_ExportGraphToSysmlV2;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_2_NodeMapsToSysmlStructure;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_3_EdgeMapsToSysmlConnection;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_5_SysmlRoundTripShould;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_6_SnapshotCodebaseIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_7_CodebaseNodesAreModulesSymbols;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_8_CodebaseEdgesAreRelations;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_9_SnapshotAtoIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_10_SnapshotSkillsAndRulesIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_11_SkillsAndRulesAreNodes;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_12_SkillsRulesEdgesAreRelations;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_14_PcbaAtoNodesAreNetsComponentsPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_15_PcbaAtoEdgesAreConnectivity;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapRoadmap {
    doc /*
      ROADMAP-ONLY minimal nest for MN-REQ-11 PinMapIngest stubs.
      Not a product accept spine; do not treat as shipped ingest engines.
      One PinMapIngest usage; domainVariant selects sysml/codebase/pcba/skills.
    */
    attribute roadmapOnly : Boolean = true;
    part ingest : PinMapIngest;
  }

  // =====================================================================
  // Multitask Mode (MN-REQ-12) — nested until clear
  // Team lead imports member working memory (SessionImportReceive).
  // Colloquial "session merge" means this import — no SessionMerge* types.
  // =====================================================================

  part def ImportAbsorb {
    doc /*
      Hard-gate absorb of an allowed/trimmed WorkingMemorySlice into the
      lead/mission session: schema, caps, owner-gated id policy (Cypher
      MERGE upsert / reject / remint NEW), nodes then edges, then lead may
      settle TSK_*. Product verb = import. Cypher MERGE mechanics and micro
      merge=true are not this part. Runs after ImportGuard soft allow/trim
      when guard is enabled; when guard skipped/disabled, absorb after
      SessionImportRequest alone (path B). Path A never enters this part.
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
      OPTIONAL soft policy (cheap LLM) nested under SessionImportReceive
      path B, before ImportAbsorb — librarian-class soft gate. Happy path =
      Path A shared session re-pin_map **without** this guard (no second
      store, no ImportGuardDecision). Soft checks when enabled: assigned
      scope?, junk/off-mission?, invented ids vs copy-from-pin_map?,
      oversized / settle noise?. Outcomes: allow / trim / reject + short
      reason (ImportGuardDecision). MUST NOT replace engine hard gates.
      MUST NOT make guard chat the SSOT. costTier = cost/latency class only
      (no vendor model id). Host MAY skip/disable; doctrine nested, not
      claimed shipped as hard engine capability.
    */
    attribute optionalSoftPolicy : Boolean = true;
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
      session. Happy path A (preferred): shared session → re-pin_map only —
      this nest skipped; ImportGuard not used. Path B spine: optional
      ImportGuard (cheap LLM soft policy) → ImportAbsorb (hard) → settle.
      Slice enters at guard.sliceIn when guard enabled; decision+slice pass
      to absorb. Hosts behaviour SessionImportReceive states.
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

  part def SessionHandoffEmit {
    doc /*
      Lead / module-A stage: emit SessionHandoff (SessionCapability sessionId
      + CallerId; optional missionId / lease / anchors / WorkerWriteScope).
      Hosts SessionHandoffById. Consults the shipped CapsPolicy ACL (who /
      optional SessionBind) before emit; sessionId MUST NOT dump in chat,
      queue, MissionDock, or HTTP body (EvDumpGraphInChat forbidden).
      As-is NOW: the CapsPolicy ACL cut is shipped for the downstream
      pin_map/mutate and WorkerWriteScope hard-reject gates when session ACL
      is enabled; reserve/lease remains doctrine. engineAclShipped=true.
    */
    attribute doctrineAsIs : Boolean = true;
    port handoffOut : SessionHandoffOutPort;
    part caps : CapsPolicy;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_7_SessionAsSsotHandle;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_8_NoGraphDumpHandoff;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_1_SharedSessionMissionSsot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
  }

  part def AsyncTaskDispatch {
    doc /*
      Lead stage: spawn N background MultitaskWorker members via
      EvDelegateWorker after WorkerWriteScope assignment; then MUST
      EvEndCoordinatorTurn (no same-turn poll/await). Asynchronous
      parallel only when scopes are disjoint anchors OR separate session
      ids (MN-REQ-12.5 / 12.12). Overlapping shared-session scopes →
      serial / single writer (MUST NOT dual-write).
      As-is NOW: CapsPolicy.aclWorkerWriteScopeHardReject is shipped and
      hard-rejects out-of-scope mutate when session ACL is enabled. The
      neighbourhood reserve and overlap-coordination doctrine remain
      host-controlled; no RSV engine is claimed.
      EvWorkerReturn is host-driven async completion on a later turn.
    */
    attribute doctrineAsIs : Boolean = true;
    attribute allowsParallelWhenDisjointOrSeparate : Boolean = true;
    port handoffIn : SessionHandoffInPort;
    port handoffOut : SessionHandoffOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_5_PreferOneWorkerOrDisjoint;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_6_ParentEndTurnNoPoll;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_12_HostDrivenAsyncParallel;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
  }

  part def MultitaskCoordinator {
    doc /*
      Team lead. Nest: SessionHandoffEmit → AsyncTaskDispatch → (workers
      run async) → next turn pin_map. Happy path A shared session: re-pin_map
      only (import nest + ImportGuard skipped). Path B: SessionImportReceive
      (optional ImportGuard soft + ImportAbsorb hard). Owns parent TSK_* /
      USR_* settle.
    */
    attribute doctrineAsIs : Boolean = true;
    port sessionOut : SessionIdOutPort;
    port handoffOut : SessionHandoffOutPort;
    port importReqOut : SessionImportRequestOutPort;
    port gqlOut : GqlWireOutPort;
    port pinIn : PinMapInPort;
    part handoffEmit : SessionHandoffEmit;
    part dispatch : AsyncTaskDispatch;
    part importReceive : SessionImportReceive;

    connection emitToDispatch : SessionHandoffFlow {
      end port source ::> handoffEmit.handoffOut;
      end port sink ::> dispatch.handoffIn;
    }
    // Lead handoffOut is the mission-facing SessionHandoff emit (same
    // doctrine as handoffEmit / dispatch); OperatingModel wires it to
    // WorkerPool.handoffIn.
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
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_12_HostDrivenAsyncParallel;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_7_SessionAsSsotHandle;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_8_NoGraphDumpHandoff;
  }

  part def MultitaskWorker {
    doc /*
      Team member. Accepts SessionHandoff; hosts WorkerScopedTurn
      (pin_map first → mutate under WorkerWriteScope). Path B exports
      WorkingMemorySlice for lead import. MUST NOT settle parent TSK_*
      unless delegated; chat is not SSOT.
      CapsPolicy ACL is shipped: out-of-scope mutate is a hard reject when
      session ACL is enabled. Reserve and import-path policy remain doctrine;
      this is not a claim that RSV or Path-B PinMapIngest is shipped.
    */
    attribute doctrineAsIs : Boolean = true;
    port sessionIn : SessionIdInPort;
    port handoffIn : SessionHandoffInPort;
    port sliceOut : WorkingMemorySliceOutPort;
    port pinIn : PinMapInPort;
    port gqlOut : GqlWireOutPort;
    // Behavioural host marker for WorkerScopedTurn (see behaviour.sysml).
    attribute hostsWorkerScopedTurn : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_1_SharedSessionMissionSsot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_4_WorkerPinMapAndScopedWrite;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_8_AppliesToRelevantTasks;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_12_HostDrivenAsyncParallel;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_7_SessionAsSsotHandle;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_8_NoGraphDumpHandoff;
  }

  part def WorkerPool {
    doc /*
      Logical pool of MultitaskWorker[1..*] under MultitaskOperatingModel.
      Members run asynchronously in parallel when WorkerWriteScope anchors
      are disjoint OR each has a separate session id; otherwise serial /
      single writer (MN-REQ-12.5 / 12.12). Fan-in WorkingMemorySlice for
      path B lead import.
      CapsPolicy WorkerWriteScope hard reject is shipped when session ACL is
      enabled. Pool coordination for reserve/overlap remains doctrineAsIs;
      no neighbourhood reserve or Path-B PinMapIngest is claimed shipped.
    */
    attribute doctrineAsIs : Boolean = true;
    port handoffIn : SessionHandoffInPort;
    port sliceOut : WorkingMemorySliceOutPort;
    part members : MultitaskWorker[1..*];

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_5_PreferOneWorkerOrDisjoint;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_12_HostDrivenAsyncParallel;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
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
      Nested Multitask spine (MN-REQ-12) — asynchronous parallel doctrine:
        coordinator (lead)
          ├── handoffEmit     // SessionHandoff by id
          ├── dispatch        // spawn N; EvEndCoordinatorTurn
          └── importReceive
                ├── guard     // cheap LLM soft review
                └── absorb    // hard gates + import + settle
        workerPool
          └── members[1..*]   // MultitaskWorker; WorkerScopedTurn each
        sharedStore
      Story: SessionHandoffById → AsyncTaskDispatch (end turn) → workers
      async → host EvWorkerReturn → lead pin_map / optional ImportReceive.
      Parallel only if disjoint scopes or separate sessions.
    */
    part coordinator : MultitaskCoordinator;
    part workerPool : WorkerPool;
    part sharedStore : MultitaskSharedStoreBinding;

    connection sessionHandoff : SessionHandoffFlow {
      end port source ::> coordinator.handoffOut;
      end port sink ::> workerPool.handoffIn;
    }
    connection memberSliceToLeadImport : WorkingMemorySliceFlow {
      end port source ::> workerPool.sliceOut;
      end port sink ::> coordinator.importReceive.guard.sliceIn;
    }
  }

  // =====================================================================
  // System composite
  // =====================================================================

  part def MemNetSystem {
    doc /*
      SharedLlmMemory product. Nest: AgentMemory (via core) + Transport + MCP
      (LLM ↔ MemNet) + DurableBuffer (M2.5) + PinMapRoadmap (roadmap-only
      PinMapIngest stub) + MultitaskOperatingModel (Coordinator → HandoffEmit /
      AsyncTaskDispatch / SessionImportReceive; WorkerPool MultitaskWorker[1..*]).
      TierACodec / LegacyPipeImport RETIRED — MUST NOT nest on product path
      (M2 done). Only MN-REQ-00 satisfied here.
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
