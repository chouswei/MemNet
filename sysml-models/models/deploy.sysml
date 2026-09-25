/*
  MemNet deploy — TARGET architecture after ADR-001.

  Product framing (2026-08-13): MemNet = shared LLM memory (SharedLlmMemory);
  session id = pass-by-reference handle for a MissionWorkingSet; durable GQL
  store (DurableBuffer / AgensGraphAdapter + optional Neo4jAdapter cabinet
  + optional Neo4jLibraryPort) behind MemNet.

  Nesting (coarse → fine):
    MemNetSystem                    // SharedLlmMemory product
    ├── AgentMemory                 // session-scoped working set + GQL wire
    │   └── SessionLifecycle        // usage: sessions.recallCommit
    │       ├── GraphStore
    │       ├── GqlWire             // GraphGlot parse front + product gate
    │       │   ├── GraphGlotParseFront  // implemented=true — PyPI graphglot
    │       │   └── ProductGqlGate       // implemented=true — after parse
    │       ├── RecallCommit        // 0.5 cut: TWO operators only
    │       │   ├── Recall          // TWO-operator child: seed then Shape
    │       │   │   ├── RelativeSeed     // MATCH_L → Q walk roots; Peak_L last-resort cue
    │       │   │   │     └── Peak_L     // ρ* residual local max; never default goldfish
    │       │   │   ├── SessionOutline   // empty q = census of S (0.11 TARGET)
    │       │   │   └── AgentShapedRead
    │       │   │       ├── RelativeSeed + ShapeWalk  // seedToWalk: Q → k-hop
    │       │   │       ├── PinMapShapedRead    // ShapeWalk emit; CueConflict when |Q|>1
    │       │   │       └── BoundedMatchFind    // RelativeSeed MATCH_L; CueConflict on emit
    │       │   └── Commit          // ONE gate; TARGET GraphElement identity
    │       │       ├── MutateGate
    │       │       ├── IdAllocator // leftover mint honesty flags; leftover_* parts off this nest
    │       │       ├── NeighbourhoodReserve // RSV lease — not a third API
    │       │       └── SameThingAbsorb // in-session collapse; not ImportAbsorb
    │       └── Schema / Caps (size + shipped ACL) / …
    // leftover_* / TierACodec / LegacyPipe* : models/archive.sysml (off ProjectMemNet load)
    ├── TransportBoundary           // InProcess / LocalIpc / TcpServe
    ├── MemNetMcpServer             // MemNet tip/ops MCP (GQL); fleet: one at droplet; tip≠face
    │   └── McpFacade               // TARGET cue/pattern commands only
    ├── DurableBuffer               // AgensGraphAdapter + Neo4jAdapter cabinet
    │                                 // + optional Neo4jLibraryPort (0.16; skip unless name)
    ├── PinMapRoadmap               // PinMapIngest_* + CatalogSnap (0.15) + PinMapExport (0.19)
    └── MultitaskOperatingModel
        ├── MultitaskCoordinator          // team lead
        │   ├── SessionHandoffEmit        // session id + scope handoff
        │   ├── AsyncTaskDispatch         // spawn N workers; end turn
        │   └── SessionImportReceive      // path B only (path A never enters)
        │       ├── ImportGuard           // OPTIONAL soft nest (like PinMapRoadmap)
        │       │   ├── ImportGuardHook   // shipped #49 (set_import_guard)
        │       │   ├── CheapLlmImportGuard // shipped #63 / 12.11 (env-gated)
        │       │   └── Soft* leaves      // allow|trim|reject; trim subtractive
        │       └── ImportAbsorb          // Path-B slice; not SameThingAbsorb
        │           ├── DistinctSession / SliceBudget / LawVocabExclude / Acl
        │           ├── IdPolicyKeep|Reject|Remint
        │           └── NodesThenEdgesCommit (+ optional decision atom)
        ├── WorkerPool
        │   └── MultitaskWorker[1..*]     // + WorkingMemorySliceExport (hard)
        └── MultitaskSharedStoreBinding
  Path A: shared mission sessionId → pin_map only (no import nest).
  Path B: bounded WorkingMemorySlice → optional ImportGuard → ImportAbsorb
  (id_policy keep|reject|remint). Not append. Not N-server federation.
  SameThingAbsorb is a distinct Commit rule (in-session same-thing collapse);
  ImportAbsorb SHALL NOT do entity resolution. Goldfish writeback is still
  not called Absorb.
  Hook shipped ≠ cheap LLM shipped. Module cite: memnet.import_absorb.

  APPLICATION (not in MemNetSystem): HostSearchBridge — optional host
  locators into existing MutateGate / ingest. No ImportGuard leaf copy.
  Extra 0.17: RagHostHook.implemented=true outside MemNetSystem; skip
  is valid. Grammar: docs/extras/memnet-host-search-nest.md
  APPLICATION / OPS LOOK (not in MemNetSystem): MemNetUsageDashboard —
  human read-only usage look (serve_status, sessions n/max, housekeep,
  ImportGuard armed display). MUST NOT nest manage/mutate ports.
  HTTP/UI parked (httpImplemented=false). tip is not face; not Foam
  product MCP. Manage = Memnetor + Devicor.
  APPLICATION / OPS FLEET (not in MemNetSystem): MemNetOpsFleet —
  device hosts run MemNetCoreLibrary services; the droplet hosts
  the one MemNet MCP (tip/ops engine face; tip≠face). Product invent
  face is cousin SysMLEdge (`sysmledge`; mustNotInventUploadBind).
  Device MAY run tip memnet-mcp for ops; MUST NOT nest a second
  product MCP / SysMLEdge-as-product. Not N-server federation (#47).
  APPLICATION / OPS ACCESS (not in MemNetSystem): TipMemNetAccessPortal —
  Szu-Wei mints invites; invited users Google-login and fetch a Bearer
  for the keyed tip MemNet MCP on droplet WWW
  (https://memnet.139-59-255-181.nip.io/mcp). TipMcpGate refuses
  unauthenticated WWW MemNet and forwards to the Pi tip. tip≠face.
  Not a sysmledge product and not an openProject key page. Portal web
  is the ops sidecar (portalWebImplemented=true; inventOnly=false).
  sellsInvent2Green=false. Status look of services and Bearer
  clients is look-only and MUST NOT unpark MemNetUsageDashboard
  HTTP. Free strangers stay on the SysMLEdge free tier or
  memnet-llm self-host.
  APPLICATION (not in MemNetSystem): CousinPointingContrast — TARGET vs
  eight cousin pointing/identity designs (sysml-models/models/cousins.sysml),
  including SysMLEdge (distinct pin_map / desk; not MemNet session strata;
  SysMLEdge graph is not MemNet SSOT; this engine repo and modelbasedPrj-*
  are repo-based — MUST NOT use SysMLEdge as model SSOT; SysMLEdgePrj-*
  bound desk is working model SSOT). MUST NOT thicken Recall/Commit; operatorCount stays 2.

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
          session ACL is enabled, (1) who-check (CallerId ≈ role/user),
          (2) pin_map (≈ TRAVERSE/MATCH) versus mutate (≈ WRITE),
          (3) WorkerWriteScope HARD reject (≈ label/id GRANT, cumulative OR),
          and (4) optional SessionBind (missionId + lease — MemNet-only).
          ACL is off by default for the legacy-green path.
      Expected live session payload: tens of MiB typical, hundreds of MiB
      still in role; not a GB RAG index.
      Privilege grain steals Neo4j/AgensGraph-class RBAC shape only —
      MUST NOT Bolt agent wire, LLM↔Neo4j teach, or MemNet-as-Cypher-proxy.
      Analogy table once: outputs/system-design-notes.md (CapsPolicy ACL).
      In-process MAY skip bind under MEMNET_SERVE_INTERNAL; an
      InvestorApi-style boundary with require_bind=true enforces it when
      configured. sessionId is a secret capability and never waives mutate.
      engineAclShipped=true. MutateGate and PinMapShapedRead apply the
      engine ACL cut; SessionHandoff carries the capability and scope.
      NeighbourhoodReserve (RSV, llm_id + TTL) is a lease nested under
      Commit / SessionLifecycle (MN-REQ-12.13) — not a third operator.
      Path-B PinMapIngest_* domains shipped; full private/shared/open
      session_token modes WAIT. No EvidenceCentre / MissionDock /
      CompanyMemory / HostSearchBridge nest under MemNetSystem.
      Expire session_save: Caps.save_on_expire from MEMNET_SAVE_ON_EXPIRE
      (default off). File dir MEMNET_EXPIRE_SNAPSHOT_DIR. Not Neo4j.
    */
    attribute maxRows : Integer = 5000;
    attribute maxLaw : Integer = 100;
    attribute maxRelations : Integer = 200;
    attribute maxSessions : Integer = 1024;
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
    attribute saveOnExpireDefault : Boolean = false;
    attribute saveOnExpireConfigurable : Boolean = true;
    attribute envSaveOnExpire : String = "MEMNET_SAVE_ON_EXPIRE";
    attribute envExpireSnapshotDir : String = "MEMNET_EXPIRE_SNAPSHOT_DIR";

    satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_1_StoreResourceCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_2_QueryFanoutCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_2_PinMapMustFitContext;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
  }

  part def SchemaRegistry {
    doc /*
      Session schema: node Labels and Properties; relationship-type set;
      validate ingest; reject unknown/reserved kinds.
      TARGET: SHALL NOT put id first as a required field (MN-REQ-02.8).
      leftover_id_first is leftover invented store, not grammar. Positional
      TagMap is legacy surface. 0.9 leftover: memnet.tag_map id_first /
      validate_id (leftoverIdFirst=true).
    */
    port schemaIn : SchemaInPort;
    port schemaOut : SchemaOutPort;
    port errOut : ErrorSignalOutPort;
    attribute leftoverIdFirstProductCommand : Boolean = false;
    attribute idFirstRequired : Boolean = false;
    attribute leftoverIdFirst : Boolean = true;
    attribute leftoverIssue : String = "id_first";

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
  }

  part def GraphGlotParseFront {
    doc /*
      Official-grammar parse front. As-is Python calls PyPI graphglot>=0.14.2
      (Apache-2.0; NOTICE attribution; MemNet stays MIT; do not vendor source).
      GraphGlot dialect id neo4j is the registered dialect that parses CREATE ()
      and CREATE (:TSK {goal:'…'}); ISO fullgql rejects CREATE (INSERT spelling).
      Package dialect name only — MemNet is not Cypher. No TCK compliance claim.
      Grammar spelling SSOT: vendored docs/grammar/openCypher.bnf
      (Apache-2.0; NOTICE-openCypher.md). Not TCK; not a second accept path.
      Module: memnet.gql_parse_front. Does not invent a store key.
    */
    port gqlIn : GqlWireInPort;
    port astOut : ParsedGqlProgramOutPort;
    port errOut : ErrorSignalOutPort;
    attribute implemented : Boolean = true;
    attribute packageName : String = "graphglot";
    attribute minVersion : String = "0.14.2";
    attribute dialectName : String = "neo4j";

    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_1_CanonicalParserSsot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_5_GraphGlotParseThenProductGate;
  }

  part def ProductGqlGate {
    doc /*
      MemNet product gate AFTER a successful GraphGlot parse. Rejects Layer /
      Tier A and free WITH / UNWIND / CALL / unbounded MATCH…RETURN even when
      GraphGlot accepts them. Goldfish bounds stay (pin_map + mutate / bounded
      find). MUST NOT invent a store key. Module: memnet.gql_parse_front
      gate_programs + memnet.gql._accept_parse.
    */
    port astIn : ParsedGqlProgramInPort;
    port errOut : ErrorSignalOutPort;
    attribute implemented : Boolean = true;
    attribute rejectFreeWith : Boolean = true;
    attribute rejectUnwind : Boolean = true;
    attribute rejectCall : Boolean = true;
    attribute rejectUnboundedReturn : Boolean = true;
    attribute rejectLayer : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_5_GrammarExpressesNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_6_BoundedMatchFind;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_2_RejectInvalidWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_5_GraphGlotParseThenProductGate;
  }

  part def GqlCodec {
    doc /*
      Primary agent wire SSOT (1.x teach, ADR-001): GraphGlot parse front,
      then ProductGqlGate, then leftover lowering/emit. Grammar
      spelling/identity SSOT is the vendored official BNF
      docs/grammar/openCypher.bnf (Apache-2.0;
      docs/grammar/NOTICE-openCypher.md) -- not a MemNet-invented id law.
      MUST NOT generate a parser/visitor from that BNF as a second accept
      path. MUST NOT claim TCK compliance or describe MemNet as Cypher /
      openCypher. External dialect authority:
        - vendored grammar/openCypher.bnf (this repo: docs/grammar/openCypher.bnf)
        - openCypher CIP tree (github.com/opencypher/openCypher/tree/main/cip)
        - oC9 baseline under cip/0.baseline (adopted/testable CIPs)
        - ISO/IEC 39075 for GQL-native features
      Agent surface remains MemNet-gated (pin_map + mutate subset) — not full
      language / WITH / UNWIND / CALL / unbounded MATCH…RETURN. Mutate
      accepts gated GQL patterns; pin_map emit is a shaped subgraph
      (Write = display). MUST NOT treat raw tabular RETURN as primary goldfish
      read. Engine accept path = ADR migration M2 (**shipped**) with GraphGlot
      wired on parse. TARGET: GraphElement is identity; CREATE () is legal;
      properties() MAY be empty. NicknameIdProperty MAY be omitted.
      leftover_NEW_mint is leftover sugar. HiddenStoreHandle stays in the
      store, off the wire -- not a property, not a business key. SHALL NOT
      invent a replacement application store key. leftover by_id / id_first /
      NEW stay leftover honesty. Detail: docs/grammar/gql-wire-profile.md.
    */
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    port shapedOut : ShapedSubgraphOutPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port errOut : ErrorSignalOutPort;
    part parseFront : GraphGlotParseFront;
    part productGate : ProductGqlGate;
    connection parseThenGate : ParsedGqlProgramFlow {
      end port source ::> parseFront.astOut;
      end port sink ::> productGate.astIn;
    }

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
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_1_CanonicalParserSsot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_2_RejectInvalidWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_4_NoAdHocConsumerSplits;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_5_GraphGlotParseThenProductGate;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_5_GrammarMustBeLlmLearnable;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_6_PreferTemplateFriendlyPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_7_HumanVerifyViaParser;
  }

  // leftover_* / TierACodec / LegacyPipeImport part defs: models/archive.sysml
  // (MemNetArchive; off ProjectMemNet load). Product nest uses flags only.

  part def liveNeo4jClaimed {
    doc /*
      Honesty nest so find/pin_map see liveNeo4jClaimed. Product claim
      is extra 0.14 (operator proof rpi5-syson): live round-trip yes;
      hid flush; leftover-nickname hydrate after hid miss. That claim
      is the adapter plus the 0.14 operator round trip only, not a
      runtime path. serve, IPC, and MCP bind the owner at startup and
      do not invoke it. Callers are DurableBuffer.hydrateFlushCallers.
      Not leftover mint. Not a 1.0 gate. Hid stays off the wire.
    */
    attribute claimed : Boolean = true;
  }

  part def IdAllocator {
    doc /*
      Leftover 0.9 invented store: leftover_NEW_mint and leftover_by_id.
      (1) LLM goldfish mutate -- NEW -> engine id keyed in by_id;
      (2) PinMapIngest_* leftover_allocate_from_locator. TARGET:
      GraphElement is identity; locators remain properties, not a
      replacement store key. NicknameIdProperty only. HiddenStoreHandle
      stays inside the store, off the wire. Honesty: memnet.id_allocator
      / validate_id still run; TARGET required-id mint is NOT claimed
      (implemented=false).
    */
    port recordsIn : GraphRecordInPort;
    port recordsOut : GraphRecordOutPort;
    port idsOut : AssignedIdOutPort;
    port errOut : ErrorSignalOutPort;
    attribute leftoverNewMintProductCommand : Boolean = false;
    attribute leftoverAssignedIdMapProductCommand : Boolean = false;
    attribute implemented : Boolean = false;
    attribute targetImplemented : Boolean = false;
    attribute productCommand : Boolean = false;
    attribute leftoverAsIsEngine : Boolean = true;
    attribute leftoverIssue : String = "NEW-by_id";
    attribute teachHiddenStorageHandle : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
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
      TARGET: GraphElement is identity (graphElementIsIdentity=true).
      CREATE () is legal (emptyCreateLegal=true). properties() MAY be
      empty (propertiesMayBeEmpty=true). NicknameIdProperty is optional
      (requiredIdProperty=false). HiddenStoreHandle is NOT a property,
      NOT on the wire, NOT a business key. Later MATCH/MERGE = labels +
      properties; edge = type + end elements (mergeIsPerWriteLookup=true).
      SHALL NOT invent a replacement application store key
      (noReplacementStoreKey=true). 0.9 leftover invented store:
      leftover_by_id / leftover_MERGE_by_id (leftoverByIdIndex). As-is
      module: memnet.mem_store.MemStore.
    */
    port recordsIn : GraphRecordInPort;
    port recordsOut : GraphRecordOutPort;
    port errOut : ErrorSignalOutPort;
    part caps : CapsPolicy;
    attribute leftoverByIdProductCommand : Boolean = false;
    attribute leftoverMergeByIdProductCommand : Boolean = false;
    attribute leftoverReadGetProductCommand : Boolean = false;
    attribute leftoverReadGetTargetImplemented : Boolean = false;
    attribute requiredIdProperty : Boolean = false;
    attribute leftoverByIdIndex : Boolean = true;
    attribute leftoverIssue : String = "by_id";
    attribute mergeByLabelsAndProps : Boolean = true;
    attribute graphElementIsIdentity : Boolean = true;
    attribute mergeIsPerWriteLookup : Boolean = true;
    attribute noReplacementStoreKey : Boolean = true;
    attribute emptyCreateLegal : Boolean = true;
    attribute propertiesMayBeEmpty : Boolean = true;
    attribute hiddenHandleIsProperty : Boolean = false;
    attribute hiddenHandleOnWire : Boolean = false;
    attribute hiddenHandleIsBusinessKey : Boolean = false;
    attribute hiddenHandleIsRankingKey : Boolean = false;
    attribute nicknameIdOptional : Boolean = true;
    attribute nicknameIdIsRankingKey : Boolean = false;
    attribute createOrderIsRankingKey : Boolean = false;
    attribute storageRole : String = "working_memory";

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_1_ExactlyNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_2_NodesHoldAtomisedFacts;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_3_EdgesAreFirstClass;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_11_PinMapOrderFromObservables;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_2_UpdateFailsIfAbsent;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_1_NoChatAsDurableStore;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_4_ExternalGroundTruthRequired;
  }

  part def MutateGate {
    doc /*
      Orchestrates GQL parse -> schema validate -> leftover_NEW_mint ->
      strict add/update into GraphStore -> ack.
      TARGET create: CREATE () is legal; CREATE (:Label {props}) with no
      required id; properties MAY be empty. MERGE is a per-write lookup
      of labels + properties, not a primary key. Ends MATCH by label +
      properties. Edge = type + end elements. Goldfish OUT Δ lands here
      (current session) — not ImportAbsorb. Owns leftover IdAllocator
      (implemented=false TARGET). Layer/Tier A accept retired (M2).
      0.9 leftover invented store: leftover_by_id / leftover_NEW_mint.
      Extra 0.17: library / host locators MAY arrive on libraryLocatorIn
      (properties, not leftover allocate_from_locator-as-PK). Host
      search MUST NOT absorb. Skip the hop when the hook is unset or
      the host misses.
    */
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port idsOut : AssignedIdOutPort;
    port errOut : ErrorSignalOutPort;
    port libraryLocatorIn : LibraryLocatorInPort;
    attribute libraryIngestThisCut : Boolean = true;
    part allocator : IdAllocator;
    part caps : CapsPolicy;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_2_UpdateFailsIfAbsent;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
  }

  part def RelativeSeed {
    doc /*
      TARGET algorithm under ONE Recall — not a third operator.
      Query is discrete codebook tokens (not a store-key id, not a
      prose/embedding sentence): kind / primary label, properties
      (locators as properties), keyword, optional nickname id only if
      the agent already set one. NOT tokens: leftover store-key,
      elementId/handle, free MATCH RETURN, rag_query / cosine / ANN.
      q + S → Q. MATCH_L on those tokens (hard LIMIT L) yields seed
      set Q of graph elements (relative nodes). Those Q elements ARE
      the walk roots. Empty token / empty q ⇒ SessionOutline (census
      of S); inventOnEmpty=false. leftover_empty_seed_skip is leftover
      0.10, not TARGET. Peak_L is a last-resort residual cue (0.18) when
      MATCH_L is empty and q is a non-empty codebook token — not a third
      operator, not empty-q outline, not default goldfish. leftover 0.9:
      seed = {node id}; copy find id then pin_map(anchor=id); require_anchor.
      BoundedMatchFind / CmdFind realize this part.
      SHALL emit Q honestly when |Q| > 1. SHALL NOT absorb, SHALL NOT
      silent MERGE-by-name, SHALL NOT call an LLM to collapse inside Recall.
      Same name is a candidate only. The find / pin_map emit SHALL carry
      CueConflict (Q listed, cardinality visible). SHALL NOT silently
      pick one root.
    */
    port cueIn : CueInPort;
    port seedOut : SeedSetOutPort;
    port emptySkip : EmptySkipOutPort;
    attribute cueByLabelsAndProps : Boolean = true;
    attribute cueByKeyword : Boolean = true;
    attribute hardLimit : Boolean = true;
    attribute seedsAreWalkRoots : Boolean = true;
    attribute requireStoreKeyAnchor : Boolean = false;
    attribute inventOnEmpty : Boolean = false;
    attribute emptySeedSkip : Boolean = false;
    attribute emptyCueIsOutline : Boolean = true;
    attribute peakLDefault : Boolean = false;
    attribute defaultGoldfish : Boolean = false;
    attribute leftoverCopiedIdThenAnchor : Boolean = false;
    attribute leftoverIssue : String = "copy-id-anchor";
    attribute queryIsTokens : Boolean = true;
    attribute tokenKind : Boolean = true;
    attribute tokenProps : Boolean = true;
    attribute tokenKeyword : Boolean = true;
    attribute tokenNicknameOptional : Boolean = true;
    attribute notEmbedding : Boolean = true;
    attribute notStoreKey : Boolean = true;
    attribute absorbs : Boolean = false;
    attribute silentMergeByName : Boolean = false;
    attribute llmCollapseInsideRecall : Boolean = false;
    attribute sameNameIsCandidateOnly : Boolean = true;
    attribute emitQHonestWhenMulti : Boolean = true;
    attribute silentPickOneRoot : Boolean = false;
    attribute leftoverEmptySkipProductCommand : Boolean = false;
    attribute leftoverEmptySkipTargetImplemented : Boolean = false;
    part peak : Peak_L;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_9_SessionOutlineEmptyCue;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_6_BoundedMatchFind;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_10_PeakLLastResort;
  }

  part def Peak_L {
    doc /*
      Last-resort residual topology cue under RelativeSeed — not a third
      operator. Fires only when codebook tokens are present and MATCH_L
      is empty. Empty q stays SessionOutline (0.11). ρ* = incident edges
      except hierarchical contains (hide recycled); Peak_L is the typed
      residual local max of ρ* inside one S. Not raw contains-tree
      degree. Not a nest fix. CueConflict if two peaks / two roots.
      SHALL NOT absorb in Recall. SHALL NOT silent MERGE-by-name.
      defaultGoldfish=false. MUST NOT density-peak cluster assignment,
      Leiden from peaks, or global top-k degree as goldfish.
      As-is: memnet.peak_l.peak_l (0.18 extra; package 0.19.0).
    */
    port cueIn : CueInPort;
    port seedOut : SeedSetOutPort;
    port emptySkip : EmptySkipOutPort;
    attribute implemented : Boolean = true;
    attribute notAThirdOperator : Boolean = true;
    attribute lastResort : Boolean = true;
    attribute codebookMissOnly : Boolean = true;
    attribute emptyQIsOutline : Boolean = true;
    attribute defaultGoldfish : Boolean = false;
    attribute residualRhoStar : Boolean = true;
    attribute notRawContainsDegree : Boolean = true;
    attribute notNestFix : Boolean = true;
    attribute notDensityPeakCluster : Boolean = true;
    attribute notLeidenFromPeaks : Boolean = true;
    attribute notGlobalTopKDegree : Boolean = true;
    attribute cueConflictOnTwoPeaks : Boolean = true;
    attribute absorbs : Boolean = false;
    attribute silentMergeByName : Boolean = false;
    attribute elementIdOnWire : Boolean = false;
    part cueConflict : CueConflict;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_9_SessionOutlineEmptyCue;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_10_PeakLLastResort;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
  }

  part def SessionOutline {
    doc /*
      Teach name = outline. TARGET empty-q branch of ONE Recall —
      not a third operator. Join the handed session id; ask the
      session, not a node. Empty q → census of S: kinds that exist
      plus a few real nodes of each, with their actual labels and
      properties, under one hard LIMIT. Browser-shaped (Neo4j
      Browser / db.labels / AGE ag_label + LIMIT exemplars).
      SHALL NOT MATCH a seed node (no leftover id, no --anchor).
      SHALL NOT skip empty seed as TARGET. SHALL NOT dump edges,
      dump S, absorb, MATCH-all, RAG/HostSearch, getAllPages,
      Pattern C tour, or Pattern D seeded RAG. view=shell is grain
      on an already-seeded walk — not this census. Leftover ids
      are not the next law; after outline the agent picks one seen
      cue and pin_maps. CueConflict if exemplars collide on a name
      cue (two roots stay two). Modelled; engine cut not this PR
      (implemented=false). leftover_empty_seed_skip honesty nested.
    */
    port cueIn : CueInPort;
    port censusOut : OutlineCensusOutPort;
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    attribute implemented : Boolean = false;
    attribute notAThirdOperator : Boolean = true;
    attribute emptyCue : Boolean = true;
    attribute asksSessionNotNode : Boolean = true;
    attribute noMatchSeedNode : Boolean = true;
    attribute noLeftoverAnchor : Boolean = true;
    attribute kindsCatalog : Boolean = true;
    attribute realExemplars : Boolean = true;
    attribute actualLabelsAndProps : Boolean = true;
    attribute oneHardLimit : Boolean = true;
    attribute dumpEdges : Boolean = false;
    attribute dumpS : Boolean = false;
    attribute absorbOnOutline : Boolean = false;
    attribute leftoverIdsAreNextLaw : Boolean = false;
    attribute afterOutlinePickCueThenPinMap : Boolean = true;
    attribute viewShellIsOutline : Boolean = false;
    attribute matchAll : Boolean = false;
    attribute ragSearch : Boolean = false;
    attribute hostSearch : Boolean = false;
    attribute getAllPages : Boolean = false;
    attribute patternCPrecomputedTour : Boolean = false;
    attribute patternDSeededRag : Boolean = false;
    attribute browserShaped : Boolean = true;
    attribute dbLabelsStyle : Boolean = true;
    attribute ageAgLabelStyle : Boolean = true;
    attribute requiredPropertyId : Boolean = false;
    attribute elementIdOnWire : Boolean = false;
    attribute cueConflictIfExemplarNameCollides : Boolean = true;
    attribute twoRootsStayTwo : Boolean = true;
    attribute leftoverEmptySkipProductCommand : Boolean = false;
    attribute leftoverEmptySkipTargetImplemented : Boolean = false;
    part cueConflict : CueConflict;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_9_SessionOutlineEmptyCue;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
  }

  part def ShapeWalk {
    doc /*
      TARGET pin_map reconstruct under ONE Recall — not a third operator.
      Q → X̃: k-hop from every seed in Q, diameter ≤ k, |X̃| ≤ one M
      (not M×|Q|). Hide recycled. Emit shaped subgraph (GQL family).
      leftover 0.9 require_anchor / by_id / copied-id is leftover, not
      this mechanism. PinMapShapedRead / CmdPinMap realize this part.
      When |Q| > 1 the shaped emit SHALL carry CueConflict. SHALL NOT
      silently pick one root.
    */
    port seedIn : SeedSetInPort;
    port shapedOut : ShapedSubgraphOutPort;
    port pinMapOut : LivePinMapOutPort;
    attribute unionUnderOneM : Boolean = true;
    attribute goldfishBudgetTimesAnchors : Boolean = false;
    attribute hideRecycled : Boolean = true;
    attribute requireStoreKeyAnchor : Boolean = false;
    attribute leftoverRequireAnchor : Boolean = false;
    attribute leftoverIssue : String = "require_anchor";
    attribute rankingIndependentOfHid : Boolean = true;
    attribute rankingIndependentOfNicknameId : Boolean = true;
    attribute rankingIndependentOfCreateOrder : Boolean = true;
    attribute hiddenHandleIsRankingKey : Boolean = false;
    attribute nicknameIdIsRankingKey : Boolean = false;
    part cueConflict : CueConflict;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_1_AnchoredPinMap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_2_RecycleHiddenFromPinMap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_3_PinMapDepthAndRowCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_11_PinMapOrderFromObservables;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_9_PinMapEmitSameAsMutate;
  }

  part def PinMapShapedRead {
    doc /*
      Realizes ShapeWalk: k-hop from seed set Q; emits bounded shaped
      openCypher-family subgraph (ShapedSubgraph / LivePinMap) —
      redefined Write = display. Hide recyclable rows; depth/row/view
      caps; prepend engine-law rows. Recall window only: not a store.
      SHALL NOT require a store-key
      anchor. Emit MAY omit {id:'…'}. Product compression = Shape
      (Recall X̃ of session S) — not host Snap. Nested under Recall /
      AgentShapedRead beside BoundedMatchFind.
      0.10: PinMapComposer pin_map from cue; leftoverRequireAnchor=false.
      leftover --anchor remains a nickname cue. MUST NOT emit raw unbounded RETURN tables as primary agent read.
      As-is: memnet.pin_map_composer.PinMapComposer / query pin-map (M2).
      Empty q SHALL emit SessionOutline, not view=shell grain and not
      leftover require_anchor. view=shell remains grain on a seeded walk.
      Codebook miss MAY use RelativeSeed.Peak_L last-resort (0.18);
      this part SHALL NOT re-own Peak_L. defaultGoldfish=false.
      Ranking key = kind + observable payload (MN-REQ-04.11). Hid and
      nickname id are not ranking keys. CREATE order is not a ranking key.
      Hid stays off the emit. When a hard cap clips the neighbourhood
      the shaped emit SHALL carry Truncation (visible; not a command);
      caps stay hard. As-is: memnet.observable_rank +
      PinMapComposer / MemStore neighbors / context_pack / BoundedMatchFind.
    */
    port seedIn : SeedSetInPort;
    port pinMapOut : LivePinMapOutPort;
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;
    attribute lawPrepend : Boolean = true;
    attribute implemented : Boolean = true;
    attribute compressionKind : String = "shape";
    attribute requireAnchorId : Boolean = false;
    attribute requireStoreKeyAnchor : Boolean = false;
    attribute leftoverRequireAnchor : Boolean = false;
    attribute leftoverIssue : String = "require_anchor";
    attribute unionUnderOneM : Boolean = true;
    attribute goldfishBudgetTimesAnchors : Boolean = false;
    attribute emptyCueIsOutline : Boolean = true;
    attribute viewShellIsOutline : Boolean = false;
    attribute defaultGoldfish : Boolean = false;
    attribute codebookMissOnly : Boolean = true;
    attribute rankingIndependentOfHid : Boolean = true;
    attribute rankingIndependentOfNicknameId : Boolean = true;
    attribute rankingIndependentOfCreateOrder : Boolean = true;
    attribute hiddenHandleIsRankingKey : Boolean = false;
    attribute nicknameIdIsRankingKey : Boolean = false;
    attribute leftoverRequireAnchorProductCommand : Boolean = false;
    part walk : ShapeWalk;
    part outline : SessionOutline;
    part caps : CapsPolicy;
    part cueConflict : CueConflict;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_1_AnchoredPinMap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_2_RecycleHiddenFromPinMap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_3_PinMapDepthAndRowCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_4_EngineLawPrepend;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_9_SessionOutlineEmptyCue;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_10_PeakLLastResort;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_11_PinMapOrderFromObservables;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_9_PinMapEmitSameAsMutate;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_2_PinMapMustFitContext;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_3_MinimiseTokenRoundTrips;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
  }

  part def BoundedMatchFind {
    doc /*
      Realizes RelativeSeed: MATCH_L cue/pattern (labels + properties +
      keyword, hard LIMIT L) → Q of graph elements. SHALL NOT copy a
      store-key id into pin_map --anchor. Distinct from leftover mutate
      MATCH (n {id}) SET. Nested under Recall / AgentShapedRead beside
      PinMapShapedRead. Shipped: CLI query find / MCP find (#73).
      MUST NOT claim find is pin_map or a k-hop walk.
      When |Q| > 1 SHALL emit CueConflict (Q listed, cardinality visible).
      SHALL NOT silently pick one root. SHALL NOT be a name_conflict command.
    */
    port cueIn : CueInPort;
    port seedOut : SeedSetOutPort;
    port emptySkip : EmptySkipOutPort;
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;
    attribute implemented : Boolean = true;
    attribute leftoverIssue : String = "#73";
    attribute limitRequired : Boolean = true;
    attribute emitShapedSubgraph : Boolean = true;
    attribute allowTabularReturn : Boolean = false;
    attribute variableLengthPathDefault : Boolean = false;
    attribute doctrineAsIs : Boolean = false;
    part seed : RelativeSeed;
    part caps : CapsPolicy;
    part cueConflict : CueConflict;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_6_BoundedMatchFind;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_11_PinMapOrderFromObservables;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_9_PinMapEmitSameAsMutate;
  }

  part def AgentShapedRead {
    doc /*
      Honesty nest under Recall so pin_map shipped cannot be misread as
      find shipped.       Mechanism: RelativeSeed (Q) → seedToWalk → ShapeWalk
      (X̃); empty q → SessionOutline (census of S); codebook miss →
      RelativeSeed.Peak_L last-resort then ShapeWalk (never default
      goldfish). Peak_L lives only under RelativeSeed — this nest uses
      that cue (defaultGoldfish=false; codebookMissOnly) and SHALL NOT
      re-own Peak_L. Children: PinMapShapedRead realizes ShapeWalk and
      empty-q outline; BoundedMatchFind realizes RelativeSeed MATCH_L
      (not Peak). Parent has no single implemented=true — that flag lives
      on children only. WalkQuery remains a sibling under SessionLifecycle.
      MUST NOT add a third operator beside Recall and Commit.
    */
    port cueIn : CueInPort;
    port pinMapOut : LivePinMapOutPort;
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;
    attribute defaultGoldfish : Boolean = false;
    attribute codebookMissOnly : Boolean = true;
    part seed : RelativeSeed;
    part walk : ShapeWalk;
    part outline : SessionOutline;
    part pinMap : PinMapShapedRead;
    part find : BoundedMatchFind;
    connection seedToWalk : SeedSetFlow {
      end port source ::> seed.seedOut;
      end port sink ::> walk.seedIn;
    }
    connection seedToPinMap : SeedSetFlow {
      end port source ::> seed.seedOut;
      end port sink ::> pinMap.seedIn;
    }
  }

  part def NeighbourhoodReserve {
    doc /*
      Control-plane ego lease inside an authorised session (after ACL).
      Nested under Commit / SessionLifecycle — a lease, not a third
      operator beside Recall and Commit. Holder = llm_id; lease = ttl_s
      (wall-clock until); scope = pin_map neighbourhood (anchor + depth).
      Pin map may surface RSV present lines. Mutate on reserved ids
      requires matching llm_id. Expired leases auto-release. Module:
      memnet.neighbourhood_reserve. Design:
      docs/extras/memnet-neighbourhood-reserve.md.
      As-is: implemented (MN-REQ-12.13).
    */
    attribute implemented : Boolean = true;
    attribute holderField : String = "llm_id";
    attribute ttlField : String = "ttl_s";
    attribute displayKind : String = "RSV";
    attribute doctrineAsIs : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_13_NeighbourhoodReserve;
  }

  part def CueConflict {
    doc /*
      Emit mark on the existing find / pin_map shaped subgraph when a
      cue yields |Q| > 1. Usual case: shared name. Any shared cue with
      several roots is the same signal — including two Peak_L residual
      local maxima. Q listed; cardinality visible.
      SHALL NOT silently pick one root. Two different world-things that
      share a name stay two roots. NOT a product command (no
      name_conflict / merge / absorb tool). Not a third operator.
      SameThingAbsorb remains a Commit rule after the agent sees this.
    */
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = false;
    attribute qListed : Boolean = true;
    attribute cardinalityVisible : Boolean = true;
    attribute silentPickOneRoot : Boolean = false;
    attribute usualCaseSharedName : Boolean = true;
    attribute anySharedCue : Boolean = true;
    attribute differentWorldThingsStayTwoRoots : Boolean = true;
    attribute notAThirdOperator : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
  }

  part def SameThingAbsorb {
    doc /*
      In-session collapse of two live elements the agent judged as one
      world-thing. Commit rule — not a product verb, not Recall, not
      RelativeSeed / ShapeWalk / pin_map. Distinct from ImportAbsorb
      (Path-B WorkingMemorySlice + leftover id_policy). Agent-gated;
      pattern match labels+properties (rel type+ends). SHALL NOT leftover
      MERGE-by-id / store-key / elementId. Same name is a candidate only.
      Two same-name nodes that are different world-things remain two.
      Name-change: optional aka on the same node; SHALL NOT mint a second
      thing-node. CHANGED between two thing-nodes only if the world split.
      Collapse SHALL wait until Recall has pointed CueConflict out on
      find / pin_map emit. SHALL NOT be a product command.
      Modelled; engine cut not this PR.
    */
    attribute implemented : Boolean = false;
    attribute gateKind : String = "agent";
    attribute actor : String = "llm_then_commit";
    attribute notAProductVerb : Boolean = true;
    attribute notRecall : Boolean = true;
    attribute distinctFromImportAbsorb : Boolean = true;
    attribute matchByLabelsAndProps : Boolean = true;
    attribute leftoverMergeByIdForbidden : Boolean = true;
    attribute sameNameIsCandidateOnly : Boolean = true;
    attribute differentWorldThingsRemainTwo : Boolean = true;
    attribute akaOnSameNode : Boolean = true;
    attribute mintSecondNodeOnRename : Boolean = false;
    attribute nameTokenHistoryRequired : Boolean = false;
    attribute changedEdgeOnlyIfWorldSplit : Boolean = true;
    attribute goldfishWritebackNaming : Boolean = false;
    attribute afterCueConflictVisible : Boolean = true;
    attribute notAProductCommand : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_9_MustNotCopyCousinStoreKey;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_2_SameThingAbsorb;
  }

  part def Recall {
    doc /*
      Operator Recall(q) over session graph S (MN-REQ-13). ONE operator:
      RelativeSeed then ShapeWalk. Cue q is labels + properties + keyword
      (optional nickname id if already set). Peak_L is a last-resort
      residual cue when MATCH_L misses a non-empty codebook token — not a
      third operator and not default goldfish. seed(q,S) = MATCH_L → Q of
      graph elements; empty q ⇒ SessionOutline census of S
      (inventOnEmpty=false; leftover skip is leftover_empty_seed_skip);
      codebook miss ⇒ Peak_L then ShapeWalk. Reconstruct X̃ = k-hop from Q
      (|Q|≤L) under ONE M. Hide recycled. Goldfish IN = that slice (or the
      outline census when q is empty).
      leftover 0.9 copy-id then require_anchor is leftover, not TARGET.
      Grammar SSOT: docs/grammar/math-skeleton.md. Extra 0.18 engine cut:
      Peak_L last-resort residual cue is implemented (memnet.peak_l);
      empty q stays SessionOutline; Peak_L is not a third operator and
      not default goldfish. HostSearch locators remain extra 0.17 outside
      MemNetSystem (not this Peak cut). Do not claim 1.0.
      Cousin pointing contrast lives outside MemNetSystem
      (CousinPointingContrast); this nest is not thickened.
      SHALL NOT absorb / MERGE-by-name / LLM-collapse Q. Same name is a
      candidate only; agent may later SameThingAbsorb under Commit
      after CueConflict is visible on the emit.
    */
    port cueIn : CueInPort;
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;
    attribute emptySeedSkip : Boolean = false;
    attribute emptyCueIsOutline : Boolean = true;
    attribute hopMetric : String = "hops";
    attribute cosineMetric : Boolean = false;
    attribute compressionKind : String = "shape";
    attribute snapOnSession : Boolean = false;
    attribute unionUnderOneM : Boolean = true;
    attribute goldfishBudgetTimesAnchors : Boolean = false;
    attribute absorbs : Boolean = false;
    attribute silentMergeByName : Boolean = false;
    attribute llmCollapseInsideRecall : Boolean = false;
    attribute sameNameIsCandidateOnly : Boolean = true;
    attribute cueConflictOnMultiRoot : Boolean = true;
    attribute defaultGoldfish : Boolean = false;
    attribute codebookMissOnly : Boolean = true;
    part seed : RelativeSeed;
    part outline : SessionOutline;
    attribute leftoverEmptySkipProductCommand : Boolean = false;
    attribute leftoverEmptySkipTargetImplemented : Boolean = false;
    part shapedRead : AgentShapedRead;
    connection seedToWalk : SeedSetFlow {
      end port source ::> seed.seedOut;
      end port sink ::> shapedRead.walk.seedIn;
    }

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_1_AnchoredPinMap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_3_PinMapDepthAndRowCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_9_SessionOutlineEmptyCue;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_10_PeakLLastResort;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
  }

  part def Commit {
    doc /*
      Operator Commit(Δ) — ONE gate. TARGET: GraphElement is identity;
      CREATE () legal; createRequiresId=false; properties MAY be empty.
      MERGE is a per-write lookup of labels + properties / rel type+ends
      (mergeIsPerWriteLookup=true). SHALL NOT invent a replacement store
      key. leftover_MERGE_by_id is leftover when a nickname exists.
      Leftover 0.9 invented store: leftover_NEW_mint → leftover_by_id
      (IdAllocator.implemented=false TARGET; leftoverNewMint=true).
      Ingest locators remain properties, not PK (ingestIsIdRule=false;
      leftover_ingestIsIdRule as-is). Two absorb *rules* under Commit (not
      extra operators): ImportAbsorb stays Path-B WorkingMemorySlice +
      leftover id_policy (absorbPathBOnly — goldfish writeback is still
      not called Absorb; ImportAbsorb SHALL NOT entity-resolve); SameThingAbsorb
      is in-session collapse, nested here. Python cut not this PR.
      Recall/Commit operatorCount stays 2.
    */
    port gqlIn : GqlWireInPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port idsOut : AssignedIdOutPort;
    port errOut : ErrorSignalOutPort;
    attribute oneGate : Boolean = true;
    attribute productVerbs : String = "Commit";
    attribute ingestIsIdRule : Boolean = false;
    attribute leftoverIngestIdRule : Boolean = true;
    attribute absorbPathBOnly : Boolean = true;
    attribute goldfishWriteback : String = "commit";
    attribute sparseDelta : Boolean = true;
    attribute echoFetchedSlice : Boolean = false;
    attribute createRequiresId : Boolean = false;
    attribute leftoverNewMint : Boolean = true;
    attribute mergeByLabelsAndProps : Boolean = true;
    attribute leftoverMergeById : Boolean = true;
    attribute mergeIsPerWriteLookup : Boolean = true;
    attribute noReplacementStoreKey : Boolean = true;
    attribute sameThingAbsorbIsCommitRule : Boolean = true;
    part mutate : MutateGate;
    part reserve : NeighbourhoodReserve;
    part sameThing : SameThingAbsorb;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_9_LeadOwnsSessionImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_13_NeighbourhoodReserve;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_2_SameThingAbsorb;
  }

  part def RecallCommit {
    doc /*
      0.5 mechanism parent under SessionLifecycle: TWO operators only —
      Recall(q) and Commit(Δ). Existing PinMapShapedRead / BoundedMatchFind
      nest under Recall; MutateGate / NeighbourhoodReserve / SameThingAbsorb
      nest under Commit. PinMapIngest_* and ImportAbsorb remain in PinMapRoadmap /
      SessionImportReceive as Commit rules, not extra operators (ImportAbsorb
      is Path-B only; SameThingAbsorb is the in-session collapse).
      HostSearchBridge MUST NOT nest here. Two compressions: Snap (host
      corpus, outside; 0.17 RagHostHook locators) vs Shape (Recall X̃).
      Goldfish I/O: slice in (Recall), Δ out (Commit); pin topics then
      fetch slices. Extra 0.18: Peak_L last-resort residual cue is
      implemented under RelativeSeed (not a third operator; empty q stays
      outline; never default goldfish). operatorCount stays 2. HostSearch
      stays outside MemNetSystem. Do not claim 1.0. Docs:
      docs/grammar/math-skeleton.md.
    */
    port shapedOut : ShapedSubgraphOutPort;
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port errOut : ErrorSignalOutPort;
    attribute operatorCount : Integer = 2;
    attribute hostSearchInsideSystem : Boolean = false;
    part recall : Recall;
    part commit : Commit;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
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
      This part deletes classified rows. recycle=delete_on_settle and
      recycle=delete_on_expire hide a row from pin_map. That mark is
      not TTL expire-save and not a second store.
      usageLookOut is a read-only stats snapshot for MemNetUsageDashboard
      — not a manage/prune command from the page.
    */
    port statsOut : GqlWireOutPort;
    port usageLookOut : ServeUsageLookOutPort;
    port errOut : ErrorSignalOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_2_RecycleHiddenFromPinMap;
  }

  part def SnapshotStore {
    doc /*
      Named-session durable file: save/load schema + records + relations
      (MN-REQ-01.4--01.6). MUST NOT be taken as MN-REQ-11 pin-map export.
      Expire-time save is configurable (MEMNET_SAVE_ON_EXPIRE default
      off). When on, TTL drops RAM and MAY write a file
      (MEMNET_EXPIRE_SNAPSHOT_DIR and/or session save --file). The file
      remains until the user deletes it. session_load restores a live
      session. Explicit session_save and expire-save write one blob
      (explicitSaveAndExpireSaveOneBlob). MUST NOT treat this as Neo4j
      cabinet dump. storageRole file_snapshot.
    */
    port snapOut : SessionSnapshotOutPort;
    port snapIn : SessionSnapshotInPort;
    port errOut : ErrorSignalOutPort;
    attribute saveOnExpireDefault : Boolean = false;
    attribute saveOnExpireConfigurable : Boolean = true;
    attribute envSaveOnExpire : String = "MEMNET_SAVE_ON_EXPIRE";
    attribute envExpireSnapshotDir : String = "MEMNET_EXPIRE_SNAPSHOT_DIR";
    attribute ramDropsOnTtl : Boolean = true;
    attribute fileUntilUserDrop : Boolean = true;
    attribute loadRestoresRam : Boolean = true;
    attribute storageRole : String = "file_snapshot";
    attribute explicitSaveAndExpireSaveOneBlob : Boolean = true;
    attribute notNeo4j : Boolean = true;
    attribute notWholeCabinetDump : Boolean = true;
    attribute loadByKnownSid : Boolean = true;
    attribute expireMissHonest : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_4_SaveSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_5_LoadSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_6_OptionalKeepSessionId;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_3_SessionTtlAndCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
  }

  // =====================================================================
  // AgentMemory — nested working-memory product heart
  // =====================================================================

  part def SessionLifecycle {
    doc /*
      Process-wide registry of named sessions with TTL purge; per-session
      GraphStore + SchemaRegistry + RecallCommit (Recall + Commit) facades.
      Each session id is the pass-by-reference handle for a MissionWorkingSet
      (SOMETHING). Nested under AgentMemory (SharedLlmMemory). As-is:
      memnet.registry + session. M2.5 hydrate/flush ports to DurableBuffer —
      client landed; live cabinet external. RSV lease lives under Commit.
      Sliding TTL; expire save via nested SnapshotStore (configurable).
      The session id is the mission working-set handle, not the model
      SSOT and not a second graph.
    */
    port sessionOut : SessionIdOutPort;
    port sessionIn : SessionIdInPort;
    port schemaIn : SchemaInPort;
    port snapOut : SessionSnapshotOutPort;
    port snapIn : SessionSnapshotInPort;
    port hydrateIn : DurableHydrateInPort;
    port flushOut : DurableFlushOutPort;
    // Path B import entry ports live on SessionImportReceive / ImportAbsorb
    // only — do not dual-name slice/importReq here.
    port errOut : ErrorSignalOutPort;
    part caps : CapsPolicy;
    part schema : SchemaRegistry;
    part gqlWire : GqlCodec;
    part store : GraphStore;
    part recallCommit : RecallCommit;
    part walk : WalkQuery;
    part housekeep : HousekeepSettle;
    part snap : SnapshotStore;
    attribute slidingTtl : Boolean = true;
    attribute ramDropsOnTtl : Boolean = true;

    connection gqlParseToMutate : GraphRecordFlow {
      end port source ::> gqlWire.recordsOut;
      end port sink ::> recallCommit.commit.mutate.recordsIn;
    }
    connection mutateToStore : GraphRecordFlow {
      end port source ::> recallCommit.commit.mutate.recordsOut;
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
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_13_NeighbourhoodReserve;
  }

  part def AgentMemory {
    doc /*
      SharedLlmMemory realisation: session-scoped property-graph working
      memory with GQL wire. Nested SessionLifecycle holds GraphStore,
      GqlCodec (GraphGlotParseFront + ProductGqlGate), RecallCommit (Recall /
      AgentShapedRead / PinMapShapedRead + BoundedMatchFind; Commit /
      MutateGate + NeighbourhoodReserve).
      Brand = MemNet. TierACodec not nested (retire-from-wheel leftover).
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
      Hosts GraphStore. Not a second graph.
    */
    port apiIn : InProcessInPort;
    port envelopeOut : JsonEnvelopeOutPort;
    part memory : AgentMemory;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_1_InProcessPrimary;
  }

  part def LocalIpcGateway {
    doc /*
      Secondary: share one session registry across CLI + MCP processes via
      AF_UNIX (POSIX; same length-prefixed JSON as TcpServeBridge).
      Env: MEMNET_IPC_SOCKET. CLI: memnet serve --ipc / --ipc-path.
      As-is: implemented (MN-REQ-06.2).
    */
    port ipcIn : LocalIpcInPort;
    port envelopeOut : JsonEnvelopeOutPort;
    attribute implemented : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_2_LocalIpcShare;
  }

  part def TcpServeBridge {
    doc /*
      Migration / multi-process fallback: length-prefixed JSON over TCP
      localhost. Under Multitask this path (or streamable-http / LocalIpc)
      is the shared-store binding (MN-REQ-12.2).
      usageLookOut = serve_status (up/host/port + expire-save booleans;
      path redacted) for MemNetUsageDashboard.
      Many mn_* sessions in one registry. Not a projectId map.
      Not a second graph.
    */
    port cmdIn : ServeCommandInPort;
    port envelopeOut : JsonEnvelopeOutPort;
    port usageLookOut : ServeUsageLookOutPort;
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

  // =====================================================================
  // TARGET agent/CLI/MCP commands (cue/pattern; no store-key id)
  // Leftover 0.9 id tools live under engine leftover_* — not here.
  // =====================================================================

  part def CmdSessionOpen {
    doc /* TARGET: session_open. Session handle is not a graph store key. */
    attribute requiresStoreKeyId : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
  }

  part def CmdSessionCurrent {
    doc /* TARGET: session current. Session handle is not a graph store key. */
    attribute requiresStoreKeyId : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
  }

  part def CmdSessionList {
    doc /*
      TARGET: CLI session list / MCP session_list. Lists catalog session=
      pins (MN-REQ-11.17). Emits header sessions|n/max then ids.
      Session handle is not a graph store key.
      SHALL NOT ANN-rank sessions. Look remains pin_map of a listed id.
      usageLookOut repeats n/max + ids for the human dashboard (look
      only — SHALL NOT session_close from that surface).
    */
    port locatorIn : CatalogSessionLocatorInPort;
    port usageLookOut : ServeUsageLookOutPort;
    attribute requiresStoreKeyId : Boolean = false;
    attribute listsCatalogSessionPins : Boolean = true;
    attribute annRankSessions : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_17_CatalogModelSnap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
  }

  part def CmdSessionClose {
    doc /*
      TARGET: CLI session close / MCP session_close. SessionLifecycle.close
      of that id. SHALL NOT dump S. Not a third operator (Recall + Commit).
    */
    attribute requiresStoreKeyId : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
    attribute dumpsS : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_2_SessionLifecycleOps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
  }

  part def CmdSessionSave {
    doc /*
      TARGET: session save. Session handle is not a graph store key.
      After TTL, save only if MEMNET_SAVE_ON_EXPIRE; then RAM id drops.
    */
    attribute requiresStoreKeyId : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
    attribute saveOnExpireConfigurable : Boolean = true;
    attribute saveOnExpireDefault : Boolean = false;
    attribute ramDropsAfterExpireSave : Boolean = true;
  }

  part def CmdSessionLoad {
    doc /*
      TARGET: session load. Session handle is not a graph store key.
      Restores RAM from file; new id unless keep_id; TTL window resets.
      Load-by-known-sid (no client file path) resolves
      MEMNET_EXPIRE_SNAPSHOT_DIR/{sid}.snap with keep_id. Honest miss:
      snap_available / snap_missing / unknown session. MUST NOT echo sid.
    */
    attribute requiresStoreKeyId : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
    attribute newIdDefault : Boolean = true;
    attribute keepIdOptional : Boolean = true;
    attribute ttlResetsOnLoad : Boolean = true;
    attribute loadByKnownSid : Boolean = true;
    attribute expireSnapKeepId : Boolean = true;
    attribute mustNotEchoSid : Boolean = true;
  }

  part def CmdFind {
    doc /*
      TARGET command realizing RelativeSeed: MATCH_L by kind / labels /
      properties / keyword (hard LIMIT). SHALL NOT require a store-key
      id. SHALL NOT teach copy-id then pin_map(anchor=id).
      When |Q| > 1 the emit SHALL carry CueConflict. SHALL NOT nest
      name_conflict / merge / absorb as a product command.
    */
    port cueIn : CueInPort;
    port seedOut : SeedSetOutPort;
    attribute requiresStoreKeyId : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
    attribute limitRequired : Boolean = true;
    attribute cueByLabelsAndProps : Boolean = true;
    attribute cueByKeyword : Boolean = true;
    attribute hardLimit : Boolean = true;
    part seed : RelativeSeed;
    part cueConflict : CueConflict;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
  }

  part def CmdPinMap {
    doc /*
      TARGET command realizing ShapeWalk from seed set Q (not a required
      store-key --anchor). Empty q SHALL emit SessionOutline (census of
      S), not leftover skip and not view=shell. leftover_require_anchor
      is leftover engine. When |Q| > 1 the emit SHALL carry CueConflict.
      SHALL NOT nest name_conflict / merge / absorb as a product command.
    */
    port seedIn : SeedSetInPort;
    attribute requiresStoreKeyId : Boolean = false;
    attribute requireAnchorId : Boolean = false;
    attribute requireStoreKeyAnchor : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
    attribute emptyCueIsOutline : Boolean = true;
    attribute viewShellIsOutline : Boolean = false;
    part walk : ShapeWalk;
    part outline : SessionOutline;
    part cueConflict : CueConflict;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_7_RelativeSeedThenShapeWalk;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_8_CueMultiRootHonest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_9_SessionOutlineEmptyCue;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
  }

  part def CmdPinMapExport {
    doc /*
      0.19 product command: write out a cue pin_map (or empty-q outline)
      as shaped GQL. Ingest is not export. Empty q is SessionOutline, not
      a dump of S. Hard bounds stay. CueConflict if |Q|>1. Distinct from
      session save/load. MUST NOT Absorb, MERGE-by-id, rag_query, or treat
      leftover ids as law. Hidden handle off the wire. Re-ingest later.
      MN-REQ-11.1 SysML v2 model representation is not this cut.
    */
    attribute requiresStoreKeyId : Boolean = false;
    attribute requireAnchorId : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
    attribute emptyCueIsOutline : Boolean = true;
    attribute dumpsWholeS : Boolean = false;
    attribute absorb : Boolean = false;
    attribute sysmlFileGeneration : Boolean = false;
    attribute hiddenHandleOnWire : Boolean = false;
    attribute elementIdOnWire : Boolean = false;
    part cueConflict : CueConflict;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
  }

  part def CmdMutate {
    doc /*
      TARGET Commit of GQL: CREATE () legal; MERGE/SET/DELETE by
      labels+properties; edge = type + two end elements. No NEW.
      No AssignedIdMap. SHALL NOT fail for missing store-key id.
      leftover add/update-by-id remains engine honesty.
    */
    attribute requiresStoreKeyId : Boolean = false;
    attribute createRequiresId : Boolean = false;
    attribute mergeByLabelsAndProps : Boolean = true;
    attribute noNewVerb : Boolean = true;
    attribute noAssignedIdMapRequired : Boolean = true;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
  }

  part def CmdPathBIngest {
    doc /*
      TARGET Path-B ingest: locators are properties, not PK. No client
      NEW. leftover_allocate_from_locator is leftover engine, not a
      TARGET command.
    */
    attribute requiresStoreKeyId : Boolean = false;
    attribute locatorsAreProperties : Boolean = true;
    attribute matchByLabelsAndProps : Boolean = true;
    attribute leftoverAllocateIsProductCommand : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
  }

  part def CmdPathBImport {
    doc /*
      TARGET Path-B import: match by labels+properties. leftover
      import_slice id_policy keep|reject|remint keyed on store-key is
      leftover engine, not a TARGET command.
    */
    attribute requiresStoreKeyId : Boolean = false;
    attribute matchByLabelsAndProps : Boolean = true;
    attribute leftoverIdPolicyIsProductCommand : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
  }

  part def CmdCatalogSnap {
    doc /*
      TARGET 0.15: Snap(model) → catalog + interiors. List session= ids;
      look = pin_map; join = ImportAbsorb slice. Locators are properties.
      SHALL NOT require a store-key id. Not a third operator.
      Cross-cut satisfy: catalog locators (MN-REQ-11.17.1); not SysMLEdge.
    */
    attribute requiresStoreKeyId : Boolean = false;
    attribute locatorsAreProperties : Boolean = true;
    attribute packageGrain : Boolean = true;
    attribute lookIsPinMap : Boolean = true;
    attribute joinIsAbsorbSlice : Boolean = true;
    attribute absorbWholeS : Boolean = false;
    attribute oneSessionPerReq : Boolean = false;
    attribute layerProperty : Boolean = false;
    attribute annRankSessions : Boolean = false;
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
    attribute notAThirdOperator : Boolean = true;
    attribute crossCutSatisfyOnCatalog : Boolean = true;
    attribute danglingDestInInterior : Boolean = false;
    attribute foreignProductPinMap : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_17_CatalogModelSnap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_17_CatalogModelSnap::MN_REQ_11_17_1_CrossCutSatisfyLocators;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
  }

  part def CliFacade {
    doc /*
      Agent/human CLI. Presents GQL wire on stdio (target / product path).
      TARGET commands are cue/pattern only (MN-REQ-07.1 / 07.5): session
      open/current/save/load, session list, session close, find, pin_map, mutate/Commit,
      Path-B ingest, pin-map export, Path-B import, catalog Snap. MUST NOT nest
      leftover_read_get, leftover_NEW_mint,
      leftover_AssignedIdMap, leftover_by_id, leftover_MERGE_by_id,
      leftover_require_anchor, leftover_allocate_from_locator, or
      leftover id_policy as product commands. MUST NOT nest name_conflict /
      merge / absorb as product commands (CueConflict is an emit mark;
      SameThingAbsorb is a Commit rule). TierA / Layer line codecs
      are RETIRED on product path (M2 done). As-is: memnet.cli
      (+ serve_client). Python rewrite out of scope.
    */
    port apiOut : InProcessOutPort;
    port ipcOut : LocalIpcOutPort;
    port cmdOut : ServeCommandOutPort;
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    port sessionOut : SessionIdOutPort;
    port errOut : ErrorSignalOutPort;
    part sessionOpen : CmdSessionOpen;
    part sessionCurrent : CmdSessionCurrent;
    part sessionSave : CmdSessionSave;
    part sessionLoad : CmdSessionLoad;
    part sessionList : CmdSessionList;
    part sessionClose : CmdSessionClose;
    part find : CmdFind;
    part pinMap : CmdPinMap;
    part mutate : CmdMutate;
    part ingest : CmdPathBIngest;
    part exportPinMap : CmdPinMapExport;
    part importSlice : CmdPathBImport;
    part catalogSnap : CmdCatalogSnap;
    attribute leftoverReadGetNested : Boolean = false;
    attribute leftoverNewNested : Boolean = false;
    attribute leftoverAssignedIdMapNested : Boolean = false;
    attribute leftoverByIdNested : Boolean = false;
    attribute leftoverMergeByIdNested : Boolean = false;
    attribute leftoverRequireAnchorNested : Boolean = false;
    attribute leftoverAllocateFromLocatorNested : Boolean = false;
    attribute leftoverIdPolicyCommandNested : Boolean = false;
    attribute leftoverNameConflictCommandNested : Boolean = false;
    attribute leftoverMergeCommandNested : Boolean = false;
    attribute leftoverAbsorbCommandNested : Boolean = false;
    attribute leftoverElementIdOnWire : Boolean = false;
    attribute leftoverEmptySeedSkipCommandNested : Boolean = false;
    attribute emptyCueIsOutline : Boolean = true;
    attribute noRequiredIdTools : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_2_SessionLifecycleOps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_4_SaveSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_5_LoadSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_6_OptionalKeepSessionId;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_1_GenericToolSurface;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_1_LlmFriendlyStdio;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_3_NoHostilePositionalDump;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_4_BoundaryFriendlyIfInternalDiffers;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_5_IoActorIsLlm;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_6_FollowPromptRules;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_9_SessionOutlineEmptyCue;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_17_CatalogModelSnap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_17_CatalogModelSnap::MN_REQ_11_17_1_CrossCutSatisfyLocators;
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
      Generic FastMCP tools. TARGET commands are cue/pattern only
      (MN-REQ-07.1 / 07.5): session_open / current / save / load,
      session_list, session_close, find, pin_map, mutate/Commit, Path-B ingest,
      pin-map export, Path-B import, catalog Snap. MUST NOT nest
      leftover_read_get, leftover_NEW_mint, leftover_AssignedIdMap,
      leftover_by_id, leftover_MERGE_by_id, leftover_require_anchor,
      leftover_allocate_from_locator, or leftover id_policy as product
      commands. MUST NOT nest name_conflict / merge / absorb as product
      commands (CueConflict is an emit mark; SameThingAbsorb is a Commit
      rule). Agent memory payloads: GQL mutate + shaped pin_map.
      Structured JSON envelopes. No domain-product tools. LLM agents
      connect here to MemNet — not to DurableBuffer. Python rewrite
      out of scope.
    */
    port apiOut : InProcessOutPort;
    port hostOut : JsonEnvelopeOutPort;
    port fromHost : GqlWireInPort;
    port errOut : ErrorSignalOutPort;
    part sessionOpen : CmdSessionOpen;
    part sessionCurrent : CmdSessionCurrent;
    part sessionSave : CmdSessionSave;
    part sessionLoad : CmdSessionLoad;
    part sessionList : CmdSessionList;
    part sessionClose : CmdSessionClose;
    part find : CmdFind;
    part pinMap : CmdPinMap;
    part mutate : CmdMutate;
    part ingest : CmdPathBIngest;
    part exportPinMap : CmdPinMapExport;
    part importSlice : CmdPathBImport;
    part catalogSnap : CmdCatalogSnap;
    attribute leftoverReadGetNested : Boolean = false;
    attribute leftoverNewNested : Boolean = false;
    attribute leftoverAssignedIdMapNested : Boolean = false;
    attribute leftoverByIdNested : Boolean = false;
    attribute leftoverMergeByIdNested : Boolean = false;
    attribute leftoverRequireAnchorNested : Boolean = false;
    attribute leftoverAllocateFromLocatorNested : Boolean = false;
    attribute leftoverIdPolicyCommandNested : Boolean = false;
    attribute leftoverNameConflictCommandNested : Boolean = false;
    attribute leftoverMergeCommandNested : Boolean = false;
    attribute leftoverAbsorbCommandNested : Boolean = false;
    attribute leftoverElementIdOnWire : Boolean = false;
    attribute leftoverEmptySeedSkipCommandNested : Boolean = false;
    attribute emptyCueIsOutline : Boolean = true;
    attribute noRequiredIdTools : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_4_SaveSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_5_LoadSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_6_OptionalKeepSessionId;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_1_InProcessPrimary;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_1_GenericToolSurface;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_2_StructuredToolEnvelope;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_3_NoDomainProductTools;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_2_LlmFriendlyMcp;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_3_NoHostilePositionalDump;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_5_IoActorIsLlm;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_6_FollowPromptRules;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_8_TemplateCopyableShapes;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_5_GrammarExpressesNodeAndEdge;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_3_ParseFaithfulInspect;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_5_GrammarMustBeLlmLearnable;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_9_SessionOutlineEmptyCue;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_17_CatalogModelSnap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_17_CatalogModelSnap::MN_REQ_11_17_1_CrossCutSatisfyLocators;
  }

  part def MemNetCoreLibrary {
    doc /*
      Target core composite allocated to parts/common/memnet.
      Nest: TransportBoundary (InProcessEngine owns AgentMemory) + CliFacade.
      AgentMemory lives under transport.inProcess.memory — one instance.
      Legal on a device host as a MemNet service without nesting a
      product MCP (MN-REQ-06.6). Tip memnet-mcp on the device for
      engine ops is allowed and remains tip≠face. The fleet MemNet
      MCP (tip/ops) sits on the droplet; product invent face is
      sysmledge (cousin; mustNotInventUploadBind).
    */
    part transport : TransportBoundary;
    part cli : CliFacade;
    attribute deviceHostLegal : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_6_DeviceServicesOneDropletMcp;
  }

  part def MemNetMcpServer {
    doc /*
      parts/memnet-mcp — generic MemNet tools only. This is the MemNet
      tip/ops MCP (CompanyMemory / engine tool face). NOT the product invent face
      (tip≠face; tipIsFace=false). Product LLM face is
      cousin SysMLEdge (`sysmledge`; mustNotInventUploadBind).
      Ops fleet: at most one fleet MemNet MCP, on the droplet host
      (MN-REQ-06.6; mcpCount=1). Device hosts SHALL NOT nest a second
      product MCP / SysMLEdge-as-product; a Pi MAY run tip memnet-mcp
      for engine ops (still tip≠face; not sold as product).
    */
    part tools : McpFacade;
    part bridge : ServeBridge;
    part seed : LawSeedHelper;
    port fromHost : GqlWireInPort;
    attribute fleetSingleton : Boolean = true;
    attribute defaultHostKind : String = "droplet";
    attribute tipIsFace : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_6_DeviceServicesOneDropletMcp;
  }

  // =====================================================================
  // Durable buffer (M2.5) — client hydrate/flush behind SharedLlmMemory
  // =====================================================================

  part def AgensGraphAdapter {
    doc /*
      M2.5 client adapter: hydrate/flush between SessionLifecycle /
      GraphStore and an external DurableGraphStore (AgensGraph-class)
      via DurableStoreAdapter. Same GQL family. Client seam landed
      (memnet.durable: FakeDurableAdapter always; optional AgensGraphAdapter
      under memnet-llm[agensgraph]; SessionLifecycle.hydrate_from_durable /
      flush_to_durable; one DurableSyncOwner). Live cabinet is external /
      operator-proven (0.7 hydrate/flush) — not vendored in-repo.
      MUST NOT dual-write without a single sync owner. MUST NOT be the LLM
      primary path (LLM ↔ MemNet only). Ego slice, not a full copy of
      S. storageRole cabinet_ego. Callers are
      DurableBuffer.hydrateFlushCallers. MN-REQ-06.4.
    */
    port hydrateOut : DurableHydrateOutPort;
    port flushIn : DurableFlushInPort;
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    // Client hydrate/flush adapter seam (Fake + optional AgensGraph client).
    attribute storageRole : String = "cabinet_ego";
    attribute implemented : Boolean = true;
    // liveCabinetClaimed: 0.7 hydrate/flush proof. The claim is the
    // adapter plus the operator round trip only, not a runtime path.
    // serve, IPC, and MCP bind the owner at startup and do not invoke
    // it. Callers are DurableBuffer.hydrateFlushCallers.
    attribute liveCabinetClaimed : Boolean = true;
    attribute phase : String = "M2.5";
  }

  part def Neo4jAdapter {
    doc /*
      Alternative cabinet client beside AgensGraphAdapter. Ego
      hydrate/flush only. Opt-in via MEMNET_NEO4J_URL (extra
      memnet-llm[neo4j]; official driver only). Factory binds exactly
      one of fake, AgensGraph, or Neo4j (one DurableSyncOwner;
      bindsExactlyOneOf). Not the session file snapshot. Not
      Neo4jLibraryPort. Does not run on Commit. Does not run on TTL
      (MN-REQ-01.3). Cabinet is external; this repo does not vendor a
      Neo4j server. Callers are DurableBuffer.hydrateFlushCallers.
      liveNeo4jClaimed=true (extra 0.14): live round-trip yes; hid
      flush; leftover-nickname hydrate after hid miss.
      Hydrate-by-hid is not live-proven. pytest.mark.neo4j_live skips
      unless MEMNET_NEO4J_URL. Agents MUST NOT talk Bolt.
      Cabinet namespace = MEMNET_NEO4J_DATABASE (default neo4j).
      Extra 0.16 library is a sibling port, not this adapter.
      MUST NOT bind the library database name as the cabinet.
      MN-REQ-06.4.
    */
    port hydrateOut : DurableHydrateOutPort;
    port flushIn : DurableFlushInPort;
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    part honesty : liveNeo4jClaimed;
    attribute implemented : Boolean = true;
    // liveNeo4jClaimed: extra 0.14 operator round trip only, not a
    // runtime path. serve, IPC, and MCP bind the owner at startup and
    // do not invoke it. Callers are DurableBuffer.hydrateFlushCallers.
    attribute liveNeo4jClaimed : Boolean = true;
    attribute storageRole : String = "cabinet_ego";
    attribute hydrateByHidLiveProven : Boolean = false;
    attribute serverVendored : Boolean = false;
    attribute namespace : String = "cabinet";
    attribute phase : String = "M2.5";
  }

  part def Neo4jLibraryPort {
    doc /*
      Extra 0.16: second named Neo4j database on the SAME process as
      Neo4jAdapter (same MEMNET_NEO4J_URL). Library = corpus graph.
      Skip unless MEMNET_NEO4J_LIBRARY_DATABASE is set (no second bind).
      Locator-only read (LibraryLocator). generate=false. MUST NOT
      hydrate session S, MUST NOT flush session pins into the library
      database, MUST NOT fuse RRF / PPR / Leiden / ANN into pin_map,
      MUST NOT Snap-on-session. Not a DurableStoreAdapter. Extra 0.17
      MAY consume these locators via RagHostHook outside MemNetSystem;
      this port stays locators-only / generate=false (not goldfish).
      Hid / elementId / _memnet_hid stay off the emit.
      Engine-real: reject when MEMNET_NEO4J_LIBRARY_DATABASE equals the
      cabinet database name (same process, two names).
    */
    port locatorOut : LibraryLocatorOutPort;
    attribute implemented : Boolean = true;
    attribute generate : Boolean = false;
    attribute skipUnlessNameSet : Boolean = true;
    attribute hydrateSession : Boolean = false;
    attribute flushSessionPins : Boolean = false;
    attribute snapOnSession : Boolean = false;
    attribute fuseRetrieveIntoPinMap : Boolean = false;
    attribute storageRole : String = "library_locators";
    attribute rejectSameNameAsCabinet : Boolean = true;
    attribute namespace : String = "library";
    attribute sameProcessAsCabinet : Boolean = true;
  }

  part def DurableBuffer {
    doc /*
      Optional durable property-graph buffer behind MemNet SharedLlmMemory.
      Connects to GraphStore / SessionLifecycle via hydrate/flush — not to
      LLM agents as primary. Children are alternative cabinet clients;
      factory binds exactly one adapter (one sync owner). AgensGraph live
      cabinet proven (0.7). Neo4j live claimed (0.14): live round-trip
      yes; hid flush; leftover-nickname hydrate after hid miss. TARGET:
      no grammar store key; MERGE is a per-write lookup of labels
      + props / rel type+ends, not a primary key. leftoverMergeById=true
      records 0.9 nickname MERGE and invented by_id. elementId stays in
      the cabinet, off the wire. Cabinets stay external / not vendored.
      Skip live Neo4j pytest unless MEMNET_NEO4J_URL. Extra 0.16:
      optional library namespace is a second database name on the same
      Neo4j URL (Neo4jLibraryPort); skip unless that name is set. Two
      cabinet URLs still require MEMNET_DURABLE_BACKEND. Factory SHALL
      NOT treat two database names as two URLs. Factory binds exactly
      one of fake, AgensGraph, or Neo4j (bindsExactlyOneOf). An
      unconfigured URL binds FakeDurableAdapter. hydrateFlushCallers
      names who calls hydrate/flush. MN-REQ-06.4.
    */
    part agens : AgensGraphAdapter;
    part neo4j : Neo4jAdapter;
    part library : Neo4jLibraryPort;
    port hydrateOut : DurableHydrateOutPort;
    port flushIn : DurableFlushInPort;
    attribute storageRole : String = "cabinet_ego";
    attribute hydrateFlushCallers : String = "tests";
    attribute bindsExactlyOneOf : String = "fake|agensgraph|neo4j";
    attribute clientLanded : Boolean = true;
    // liveCabinetClaimed: 0.7 operator round trip only, not a runtime
    // path. serve, IPC, and MCP bind the owner at startup and do not
    // invoke it. Callers are hydrateFlushCallers.
    attribute liveCabinetClaimed : Boolean = true;
    // liveNeo4jClaimed: 0.14 operator round trip only, not a runtime
    // path. serve, IPC, and MCP bind the owner at startup and do not
    // invoke it. Callers are hydrateFlushCallers.
    attribute liveNeo4jClaimed : Boolean = true;
    attribute twoNamespaces : Boolean = true;
    attribute sameNeo4jProcess : Boolean = true;
    attribute twoUrlsStillNeedBackendPick : Boolean = true;
    attribute mergeByLabelsAndProps : Boolean = true;
    attribute leftoverMergeById : Boolean = true;
    attribute mergeIsPerWriteLookup : Boolean = true;
    attribute noReplacementStoreKey : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_4_DurableStoreBehindMemNet;
  }

  // =====================================================================
  // MN-REQ-11 Path-B PinMapIngest (selective external artefact → pins)
  // Domains shipped: Sysml, Codebase, PcbaAto, SkillsRules (#31 / #64).
  // PinMapExport (0.19 / #66) is the cue pin_map GQL write-out — not ingest.
  // Module: memnet.pin_map_ingest. Distinct from SnapshotStore + live
  // PinMapShapedRead. MUST NOT invent N-server federation.
  // =====================================================================

  part def PinMapIngestBase {
    doc /*
      Shared Path-B ingest interface: project a bounded NODE|EDGE pin map from
      an external artefact using locator properties (path=, qname=, refdes=,
      …). TARGET: Commit create of GraphElement; CREATE () legal; no
      required id; locators are properties, not a mint law or store key.
      Leftover 0.9: leftover_allocate_from_locator / leftover_by_id
      (leftoverLocatorMint) and leftover_ingestIsIdRule. leftover_NEW_mint
      is leftover sugar, not TARGET. Wire = GQL family. Commit via
      MutateGate. As-is module: memnet.pin_map_ingest.
    */
    attribute domainVariant : String;
    attribute implemented : Boolean = false;
    attribute roadmapOnly : Boolean = true;
    attribute rejectsClientNew : Boolean = true;
    attribute wireDialect : String = "gql";
    attribute leftoverAllocateFromLocatorProductCommand : Boolean = false;
    attribute leftoverIngestIsIdRuleProductCommand : Boolean = false;
    attribute leftoverLocatorMint : Boolean = true;
    attribute leftoverIssue : String = "locator-as-PK";
    attribute leftoverAllocateIsProductCommand : Boolean = false;
    attribute matchByLabelsAndProps : Boolean = true;
    attribute locatorsAreProperties : Boolean = true;
    port pinOut : PinMapOutPort;
    port recordsOut : GraphRecordOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
  }

  part def PinMapIngest_Sysml {
    doc /*
      FIRST Path-B engine (ship order). Selective SysML v2 .sysml → PKG / PRT /
      REQ / POR / CON pins with path= + qname= (+ requirementId=).
      Bounded (max_nodes / file caps). As-is: implemented (MN-REQ-11.13,
      11.16; issue #31). MUST NOT satisfy MN-REQ-11.1–11.5 (ingest is not
      export). Module: memnet.pin_map_ingest.PinMapIngest_Sysml.
      Path-B is a keyword and brace walk that Commits GQL pins; it is not a
      SysML v2 parser and has no grammar.
    */
    attribute domainVariant : String = "sysml";
    attribute implemented : Boolean = true;
    attribute roadmapOnly : Boolean = false;
    attribute firstEngine : Boolean = true;
    attribute rejectsClientNew : Boolean = true;
    attribute wireDialect : String = "gql";
    attribute nodeKinds : String = "PKG,PRT,REQ,POR,CON";
    attribute edgeRelations : String = "contains,satisfies,typedBy,hasPort,connects";
    attribute leftoverLocatorMint : Boolean = true;
    attribute leftoverIssue : String = "locator-as-PK";
    attribute leftoverAllocateIsProductCommand : Boolean = false;
    attribute matchByLabelsAndProps : Boolean = true;
    attribute locatorsAreProperties : Boolean = true;
    port pinOut : PinMapOutPort;
    port recordsOut : GraphRecordOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapIngest_Codebase {
    doc /*
      Path-B codebase pin map (MOD / SYM; path=, line=, signature=).
      As-is: implemented (MN-REQ-11.6–11.8, 11.13, 11.16; issue #64).
      Module: memnet.pin_map_ingest.PinMapIngest_Codebase.
      CLI: memnet ingest codebase; MCP: ingest_codebase.
    */
    attribute domainVariant : String = "codebase";
    attribute implemented : Boolean = true;
    attribute roadmapOnly : Boolean = false;
    attribute rejectsClientNew : Boolean = true;
    attribute wireDialect : String = "gql";
    attribute nodeKinds : String = "MOD,SYM";
    attribute edgeRelations : String = "defines,calls,includes,owns,uses";
    attribute leftoverLocatorMint : Boolean = true;
    attribute leftoverIssue : String = "locator-as-PK";
    attribute leftoverAllocateIsProductCommand : Boolean = false;
    attribute matchByLabelsAndProps : Boolean = true;
    attribute locatorsAreProperties : Boolean = true;
    port pinOut : PinMapOutPort;
    port recordsOut : GraphRecordOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_6_SnapshotCodebaseIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_7_CodebaseNodesAreModulesSymbols;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_8_CodebaseEdgesAreRelations;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapIngest_PcbaAto {
    doc /*
      Path-B PCBA Atopile .ato pin map (CMP / NET / PIN; refdes=, net=, pin=,
      path=). As-is: implemented (MN-REQ-11.9, 11.14–11.15, 11.13, 11.16;
      issue #64). Module: memnet.pin_map_ingest.PinMapIngest_PcbaAto.
      CLI: memnet ingest pcba; MCP: ingest_pcba.
    */
    attribute domainVariant : String = "pcbaAto";
    attribute implemented : Boolean = true;
    attribute roadmapOnly : Boolean = false;
    attribute rejectsClientNew : Boolean = true;
    attribute wireDialect : String = "gql";
    attribute nodeKinds : String = "CMP,NET,PIN";
    attribute edgeRelations : String = "owns,on_net,uses";
    attribute leftoverLocatorMint : Boolean = true;
    attribute leftoverIssue : String = "locator-as-PK";
    attribute leftoverAllocateIsProductCommand : Boolean = false;
    attribute matchByLabelsAndProps : Boolean = true;
    attribute locatorsAreProperties : Boolean = true;
    port pinOut : PinMapOutPort;
    port recordsOut : GraphRecordOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_9_SnapshotAtoIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_14_PcbaAtoNodesAreNetsComponentsPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_15_PcbaAtoEdgesAreConnectivity;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapIngest_SkillsRules {
    doc /*
      Path-B agent skills/rules pin map (SKL / RUL; skill_id=, phrase=).
      As-is: implemented (MN-REQ-11.10–11.12, 11.13, 11.16; issue #64).
      Module: memnet.pin_map_ingest.PinMapIngest_SkillsRules.
      CLI: memnet ingest skills; MCP: ingest_skills.
    */
    attribute domainVariant : String = "skillsRules";
    attribute implemented : Boolean = true;
    attribute roadmapOnly : Boolean = false;
    attribute rejectsClientNew : Boolean = true;
    attribute wireDialect : String = "gql";
    attribute nodeKinds : String = "SKL,RUL";
    attribute edgeRelations : String = "paired_with,triggers,governs,uses";
    attribute leftoverLocatorMint : Boolean = true;
    attribute leftoverIssue : String = "locator-as-PK";
    attribute leftoverAllocateIsProductCommand : Boolean = false;
    attribute matchByLabelsAndProps : Boolean = true;
    attribute locatorsAreProperties : Boolean = true;
    port pinOut : PinMapOutPort;
    port recordsOut : GraphRecordOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_10_SnapshotSkillsAndRulesIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_11_SkillsAndRulesAreNodes;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_12_SkillsRulesEdgesAreRelations;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapExport {
    doc /*
      0.19 product command. Write out a cue pin_map (or empty-q outline) as
      shaped GQL. Ingest ≠ export. Distinct from SnapshotStore (MN-REQ-11.4)
      and from ImportAbsorb / WorkingMemorySliceExport (MUST NOT treat export
      as Absorb). Chat dump is not export. Hard bounds stay. CueConflict if
      |Q|>1. Hidden handle off the wire. leftover ids are not law.
      Re-ingest / MERGE-by-id identity merge is later (MN-REQ-11.5 SHOULD;
      roundTripClaimed=false). MN-REQ-11.1 SysML v2 model representation
      is not this cut (sysmlFileGeneration=false).
      Module: memnet.pin_map_export. CLI: memnet export pin-map.
      MCP: export_pin_map.
    */
    attribute implemented : Boolean = true;
    attribute productCommand : Boolean = true;
    attribute emptyCueIsOutline : Boolean = true;
    attribute dumpsWholeS : Boolean = false;
    attribute absorb : Boolean = false;
    attribute leftoverIdsAsLaw : Boolean = false;
    attribute mergeByIdOnExport : Boolean = false;
    attribute ragQuery : Boolean = false;
    attribute roundTripClaimed : Boolean = false;
    attribute sysmlFileGeneration : Boolean = false;
    attribute hiddenHandleOnWire : Boolean = false;
    attribute elementIdOnWire : Boolean = false;
    attribute wireDialect : String = "gql";
    port gqlOut : GqlWireOutPort;
    part cueConflict : CueConflict;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
  }

  part def CatalogSnap {
    doc /*
      0.15: Snap(one SysML load tree) → catalog S_cat plus package interiors.
      Catalog holds session= + qname= locators (properties). Look = pin_map
      of one interior. Join = ImportAbsorb a slice. Module:
      memnet.catalog_snap.snap_model. CLI memnet snap model / session list;
      MCP snap_model / session_list. Locator item is CatalogSessionLocator
      (session= + qname=), not PinMapProjection.
      SHALL NOT ANN-rank sessions; Absorb whole S; dump the model into one
      session; Layer; one session per REQ; invent a store key; emit hid.
      Not a third operator (Commit of locators into named sessions).
      Cross-cut satisfy lives on the catalog as locators (session= +
      qname= / requirementId=) when unique ends fit M; else package-pair
      + cross_cut warn. Interiors have no dangling dest. SysMLEdge
      pin_map is a different tool — not this catalog (MN-REQ-11.17.1).
    */
    attribute implemented : Boolean = true;
    attribute packageGrain : Boolean = true;
    attribute lookIsPinMap : Boolean = true;
    attribute joinIsAbsorbSlice : Boolean = true;
    attribute absorbWholeS : Boolean = false;
    attribute dumpModelIntoOneSession : Boolean = false;
    attribute oneSessionPerReq : Boolean = false;
    attribute oneSessionPerTsk : Boolean = false;
    attribute layerProperty : Boolean = false;
    attribute annRankSessions : Boolean = false;
    attribute hiddenHandleOnWire : Boolean = false;
    attribute locatorsAreProperties : Boolean = true;
    attribute notAThirdOperator : Boolean = true;
    attribute leftoverIngestOnePath : Boolean = true;
    attribute crossCutSatisfyOnCatalog : Boolean = true;
    attribute danglingDestInInterior : Boolean = false;
    attribute endLocatorsBoundedByM : Boolean = true;
    attribute packagePairWhenOverM : Boolean = true;
    attribute foreignProductPinMap : Boolean = false;
    port locatorOut : CatalogSessionLocatorOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_17_CatalogModelSnap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_17_CatalogModelSnap::MN_REQ_11_17_1_CrossCutSatisfyLocators;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_8_IdNotRequiredOnWire;
  }

  part def PinMapRoadmap {
    doc /*
      Path-B PinMapIngest nest plus 0.19 PinMapExport and 0.15 CatalogSnap.
      Ingest domains: Sysml, Codebase, PcbaAto, SkillsRules (all implemented).
      Commit create of elements (locators as properties, not a store key) —
      not a second product operator. 0.9 leftover may still mint by_id from
      locator strings. Not N-server federation. Export is cue pin_map GQL
      write-out (#66); MUST NOT treat ingest as export. Re-ingest later.
      CatalogSnap (0.15) nests here: one model → catalog + interiors.
      As-is modules: memnet.pin_map_ingest + memnet.pin_map_export +
      memnet.catalog_snap.
    */
    attribute firstDomain : String = "sysml";
    attribute roadmapOnly : Boolean = false;
    attribute allDomainsImplemented : Boolean = true;
    part interface : PinMapIngestBase;
    part sysml : PinMapIngest_Sysml;
    part codebase : PinMapIngest_Codebase;
    part pcbaAto : PinMapIngest_PcbaAto;
    part skillsRules : PinMapIngest_SkillsRules;
    part export : PinMapExport;
    part catalog : CatalogSnap;
  }

  // =====================================================================
  // Multitask Mode (MN-REQ-12) — nested until clear
  // Path B product verb = import (SessionImport*). No SessionMerge* types.
  // micro merge=true = in-session re-id only — not this nest.
  // Module: memnet.import_absorb (export_working_memory_slice / absorb /
  // import_slice / set_import_guard).
  // =====================================================================

  // --- Path B export (member side; engine hard + LLM MAY choose anchors) ---

  part def WorkingMemorySliceExport {
    doc /*
      Engine SHALL export a bounded WorkingMemorySlice from a member session
      (export_working_memory_slice). In: anchors[+], depth, view, caps.
      Out: WorkingMemorySlice (nodes then edges). SHALL require ≥1 anchor;
      SHALL enforce slice budget (max_rows × anchors); SHALL exclude LAW /
      vocab rows; SHALL NOT dump the whole store. LLM MAY choose anchors /
      depth / view. Not N-server federation.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute doctrineAsIs : Boolean = true;
    port sliceOut : WorkingMemorySliceOutPort;
    part requireAnchors : SliceAnchorsRequired;
    part enforceBudget : SliceBudgetGate;
    part excludeLawVocab : LawVocabExclude;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
  }

  part def SliceAnchorsRequired {
    doc /*
      Engine SHALL: WorkingMemorySlice export fails (no_anchor) when anchors
      are empty. Who: engine. In: anchor list. Out: validated anchors.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
  }

  part def SliceBudgetGate {
    doc /*
      Engine SHALL: reject slice_budget when record count exceeds
      max_rows × anchors. Caps whole-store dump. Who: engine.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
  }

  part def LawVocabExclude {
    doc /*
      Engine SHALL: LAW / session-local vocabulary rows do not import (and
      are skipped on export). Who: engine. Soft guard MUST NOT reintroduce
      LAW as payload.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
  }

  // --- Path B ImportAbsorb (lead side; engine SHALL hard) ---

  part def DistinctSessionGate {
    doc /*
      Engine SHALL: path B absorb requires lead sessionId ≠ member
      sourceSessionId (same_session_import → use path A re-pin_map).
      Who: engine. Path A never enters ImportAbsorb.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_9_LeadOwnsSessionImport;
  }

  part def AclConsultAbsorb {
    doc /*
      Engine SHALL: consult CapsPolicy ACL on lead mutate path (who /
      mutate permission / optional SessionBind / WorkerWriteScope) before
      commit. Who: engine. Soft ImportGuard MUST NOT waive ACL.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    part caps : CapsPolicy;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
  }

  part def SchemaValidateImport {
    doc /*
      Engine SHALL: schema-validate each imported record against lead
      session schema (unknown/reserved kinds fail). Who: engine.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
  }

  part def IdPolicyKeep {
    doc /*
      id_policy=keep: TARGET MERGE = labels+props / rel type+ends into
      lead SSOT (GraphElement lookup). Not a store key. leftover_MERGE_by_id
      is 0.9 leftover, not this keep, not a TARGET product command.
      Not a second copy. Not append. Not product name "merge". Distinct from
      micro merge=true re-id.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute idPolicy : String = "keep";
    attribute matchByLabelsAndProps : Boolean = true;
    attribute leftoverKeyedOnStoreKey : Boolean = true;
    attribute leftoverIdPolicyIsProductCommand : Boolean = false;
    attribute leftoverMergeByIdProductCommand : Boolean = false;
  }

  part def IdPolicyReject {
    doc /*
      leftover id_policy=reject (not a TARGET product command): engine
      SHALL raise conflict and MUST NOT mutate the lead session when a
      Path-B import pattern already matches in lead (labels+props /
      type+ends). SHALL NOT teach reject as store-key id conflict.
      leftoverKeyedOnStoreKey records 0.9 honesty.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute idPolicy : String = "reject";
    attribute productCommand : Boolean = false;
    attribute leftoverIdPolicyIsProductCommand : Boolean = false;
    attribute matchByLabelsAndProps : Boolean = true;
    attribute leftoverKeyedOnStoreKey : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
  }

  part def IdPolicyRemint {
    doc /*
      id_policy=remint leftover: leftover_NEW_mint / leftover_by_id for
      conflicts; lead old rows stay; edges retarget. TARGET: no NEW mint
      law; GraphElement is identity; NicknameIdProperty only.
      leftoverInventedMint=true. Not TARGET store-key law.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute idPolicy : String = "remint";
    attribute leftoverInventedMint : Boolean = true;
    attribute leftoverIssue : String = "NEW-by_id";
    attribute productCommand : Boolean = false;
    attribute leftoverIdPolicyIsProductCommand : Boolean = false;
    part allocator : IdAllocator;
  }

  part def IdPolicyApply {
    doc /*
      Engine SHALL apply owner-gated id_policy from SessionImportRequest:
      keep | reject | remint (aliases merge/upsert → keep only at normalise).
      Who: engine. LLM MAY propose keep vs remint via ImportGuard soft
      judgment; engine still applies the chosen policy hard.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    part keep : IdPolicyKeep;
    part reject : IdPolicyReject;
    part remint : IdPolicyRemint;
    attribute leftoverKeyedOnStoreKey : Boolean = true;
    attribute leftoverIdPolicyIsProductCommand : Boolean = false;
    attribute matchByLabelsAndProps : Boolean = true;
  }

  part def NodesThenEdgesCommit {
    doc /*
      Engine SHALL commit imported nodes then edges into lead GraphStore
      under the active id policy. Who: engine. Out: lead SSOT updated.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
  }

  part def GuardDecisionAtomRecord {
    doc /*
      Engine MAY record ImportGuardDecision as a structured atom (IGD/SYS)
      in the lead session when a soft decision exists. MUST NOT treat guard
      chat as SSOT. Who: engine (optional write).
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute optional : Boolean = true;
  }

  part def ImportAbsorb {
    doc /*
      Engine SHALL hard-gate absorb of an allowed/trimmed WorkingMemorySlice
      into the lead/mission session (absorb_working_memory_slice /
      import_slice). Composition of DistinctSessionGate, SliceBudget (on
      export), LawVocabExclude, AclConsultAbsorb, SchemaValidateImport,
      IdPolicyApply (keep|reject|remint), NodesThenEdgesCommit, optional
      GuardDecisionAtomRecord. Path-B Commit create of elements
      (keep|reject|remint) — not a third operator beside Recall/Commit.
      keep = MERGE per-write lookup (labels+props / type+ends), not a
      store key; leftover_MERGE_by_id is leftover. remint is leftover
      leftover_NEW_mint / leftover_by_id.
      leftover id_policy keep|reject|remint keyed on store-key is NOT a
      TARGET product command (MN-REQ-07.5). TARGET Path-B import is
      pattern match (labels+properties).
      Product verb = import. Path A never enters.
      Distinct from SameThingAbsorb: this nest SHALL NOT entity-resolve
      two live mission-session nodes that share a name.
      When ImportGuard skipped/disabled, absorb after SessionImportRequest
      + slice alone. Module: memnet.import_absorb.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute doctrineAsIs : Boolean = false;
    attribute implemented : Boolean = true;
    attribute leftoverIdPolicyIsProductCommand : Boolean = false;
    attribute matchByLabelsAndProps : Boolean = true;
    port sliceIn : WorkingMemorySliceInPort;
    port decisionIn : ImportGuardDecisionInPort;
    port importReqIn : SessionImportRequestInPort;

    part distinctSession : DistinctSessionGate;
    part excludeLawVocab : LawVocabExclude;
    part acl : AclConsultAbsorb;
    part schema : SchemaValidateImport;
    part idPolicy : IdPolicyApply;
    part nodesThenEdges : NodesThenEdgesCommit;
    part decisionAtom : GuardDecisionAtomRecord;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_9_LeadOwnsSessionImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_5_NoStoreKeyToolSurface;
  }

  // --- Path B ImportGuard nest (OPTIONAL soft; PinMapIngest-style split) ---
  // ImportGuardHook = shipped #49. CheapLlmImportGuard = shipped #63 / 12.11
  // (env-gated; off without MEMNET_IMPORT_GUARD_API_KEY). Soft* = soft vocab.

  part def SoftScopeFitReview {
    doc /*
      LLM MAY soft-check: does the slice fit assigned WorkerWriteScope /
      mission anchors? Outcome feeds ImportGuardDecision. MUST NOT replace
      engine ACL / write-scope hard reject.
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "llm_or_host";
  }

  part def SoftJunkTrim {
    doc /*
      LLM MAY soft-trim junk / off-mission / settle noise. Trim is
      subtractive only (keep_ids); MUST NOT invent new rows. Engine then
      drops edges whose endpoints were trimmed.
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "llm_or_host";
    attribute trimMode : String = "subtractive";
  }

  part def SoftInventedIdReview {
    doc /*
      LLM MAY soft-check invented ids vs copy-from-member-pin_map. Reject
      soft when ids look fabricated. Engine hard gates still apply after.
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "llm_or_host";
  }

  part def SoftSizeNoiseReview {
    doc /*
      LLM MAY soft-flag oversized / settle-noise slices before absorb.
      Engine SliceBudgetGate remains the hard budget.
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "llm_or_host";
  }

  part def SoftIdPolicyAdvice {
    doc /*
      LLM MAY advise keep vs remint judgment (soft only). Engine IdPolicyApply
      still executes the owner-gated id_policy hard. MUST NOT rename product
      import to SessionMerge.
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "llm_or_host";
  }

  part def SoftDecisionEmit {
    doc /*
      Emit ImportGuardDecision on parent ImportGuard.decisionOut: outcome
      allow|trim|reject + short reason (+ keep_ids when trim). Structured
      atoms only — never chat SSOT. allow/trim → ImportAbsorb; reject → no
      lead mutate. Used when a guard ran (host hook or cheap-LLM adapter).
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "llm_or_host";
  }

  part def GuardPassthrough {
    doc /*
      When ImportGuardHook is skipped/disabled (host enable_guard=false,
      --no-guard, or no set_import_guard function): identity passthrough of
      WorkingMemorySlice to ImportAbsorb; no ImportGuardDecision. Skipping
      the guard is valid. Path A never uses this nest.
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "host";
    attribute skipped : Boolean = true;
  }

  part def ImportGuardHook {
    doc /*
      Host plug-in for Path B soft ImportGuard — shipped in 0.4.4 / #49.
      Surfaces: set_import_guard / --no-guard / enable_guard. GuardPassthrough
      when no function or skipped (skipping is valid). When a guard ran,
      ImportGuardDecision allow|trim|reject atoms only. MUST NOT replace
      ImportAbsorb hard gates. Path A never enters. Hook shipped ≠ cheap LLM
      adapter shipped (see CheapLlmImportGuard / issue #63).
      Module: memnet.import_absorb.
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "host";
    attribute implemented : Boolean = true;
    attribute optionalSoftPolicy : Boolean = true;
    attribute doctrineAsIs : Boolean = false;
    part passthrough : GuardPassthrough;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
  }

  part def CheapLlmImportGuard {
    doc /*
      OPTIONAL default cheap-LLM ImportGuard adapter inside memnet-llm
      (MN-REQ-12.11; GitHub issue #63). Off unless env set
      (MEMNET_IMPORT_GUARD_API_KEY required; optional
      MEMNET_IMPORT_GUARD_BASE_URL / MEMNET_IMPORT_GUARD_MODEL —
      OpenAI-compatible HTTP; default gpt-4.1-mini). Does not vendor a
      model. Returns only ImportGuardDecision; guard chat is not SSOT.
      Host MAY skip via ImportGuardHook / GuardPassthrough / --no-guard.
      Transport/parse failure soft-skips (passthrough + @WRN). LLM MAY
      soft-review; engine MUST still hard-gate ImportAbsorb.
      implemented=true after adapter ship (#63). costTier = cost/latency
      class only (no vendor model id).
      armedLookOut = env-presence armed flag for MemNetUsageDashboard
      (display only; MUST NOT carry MEMNET_IMPORT_GUARD_API_KEY).
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "llm";
    attribute costTier : String = "cheap";
    attribute implemented : Boolean = true;
    attribute optionalSoftPolicy : Boolean = true;
    attribute offUnlessEnvSet : Boolean = true;
    attribute vendorsModel : Boolean = false;
    attribute doctrineAsIs : Boolean = false;
    attribute leftoverIssue : String = "#63";
    port armedLookOut : ImportGuardArmedLookOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_11_CheapLlmImportGuardSoft;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
  }

  part def ImportGuard {
    doc /*
      OPTIONAL soft-policy nest under SessionImportReceive path B before
      ImportAbsorb — PinMapIngest-style parent (hook vs cheap LLM must not
      be misread as one flag). Children: ImportGuardHook (implemented=true;
      #49) and CheapLlmImportGuard (implemented=true; #63 / MN-REQ-12.11).
      Soft* leaves = shared soft vocabulary (LLM MAY / host MAY).
      GuardPassthrough lives under the hook. Happy path A = shared session
      re-pin_map without this nest. MUST NOT replace engine hard gates
      (schema, ACL, slice budget, id_policy, LAW exclude). Parent has no
      single implemented=true — that flag lives on children only.
    */
    attribute gateKind : String = "soft";
    attribute actor : String = "llm_or_host";
    attribute optionalSoftPolicy : Boolean = true;
    attribute doctrineAsIs : Boolean = false;
    attribute costTier : String = "cheap";
    port sliceIn : WorkingMemorySliceInPort;
    port sliceOut : WorkingMemorySliceOutPort;
    port decisionOut : ImportGuardDecisionOutPort;

    part hook : ImportGuardHook;
    part cheapLlm : CheapLlmImportGuard;

    part scopeFit : SoftScopeFitReview;
    part junkTrim : SoftJunkTrim;
    part inventedIds : SoftInventedIdReview;
    part sizeNoise : SoftSizeNoiseReview;
    part idAdvice : SoftIdPolicyAdvice;
    part decide : SoftDecisionEmit;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
  }

  part def SessionImportReceive {
    doc /*
      Path B only: lead imports a member's WorkingMemorySlice into the
      mission session. Spine: optional ImportGuard nest (ImportGuardHook
      shipped; CheapLlmImportGuard shipped #63) → ImportAbsorb (engine
      SHALL hard) → lead may settle TSK_*. Path A (shared mission sessionId
      → pin_map only) never enters this nest — no ImportGuard, no
      ImportAbsorb. Single entry ports (no dual proxy): guard.sliceIn
      (member slice), absorb.importReqIn (lead request); guard → absorb for
      trimmed slice + decision. Hosts behaviour SessionImportReceive states.
      Disambiguation (once): product verb = import (SessionImport*); micro
      merge=true ≠ this; keep = MERGE per-write lookup (labels+props /
      type+ends) inside IdPolicyKeep; leftover 0.9 may still key by_id.
      MN-REQ-12.11 is satisfied by CheapLlmImportGuard (not the hook /
      not this parent alone).
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
      run async) → next turn pin_map. Path A shared sessionId: pin_map only
      (SessionImportReceive skipped). Path B: SessionImportReceive
      (ImportGuard nest + ImportAbsorb hard). Owns parent TSK_* / USR_* settle.
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
      (pin_map first → mutate under WorkerWriteScope). Path B: nested
      WorkingMemorySliceExport (engine hard) emits slice for lead
      ImportAbsorb. MUST NOT settle parent TSK_* unless delegated; chat
      is not SSOT. CapsPolicy ACL: out-of-scope mutate hard-rejects when
      session ACL is enabled. NeighbourhoodReserve shipped; Path-B
      PinMapIngest_* domains shipped (Sysml/Codebase/PcbaAto/SkillsRules).
      Full private/shared/open + session_token modes not claimed.
    */
    attribute doctrineAsIs : Boolean = true;
    port sessionIn : SessionIdInPort;
    port handoffIn : SessionHandoffInPort;
    port sliceOut : WorkingMemorySliceOutPort;
    port pinIn : PinMapInPort;
    port gqlOut : GqlWireOutPort;
    // Behavioural host marker for WorkerScopedTurn (see behaviour.sysml).
    attribute hostsWorkerScopedTurn : Boolean = true;
    part wmExport : WorkingMemorySliceExport;

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
      SharedLlmMemory product. Nest: AgentMemory (via core; RecallCommit
      two-operator cut) + Transport + MCP (LLM ↔ MemNet) + DurableBuffer
      (cabinet hydrate/flush + optional 0.16 library locator port)
      PinMapRoadmap (PinMapIngest_* + CatalogSnap 0.15 + PinMapExport 0.19) +
      MultitaskOperatingModel (Coordinator → HandoffEmit /
      AsyncTaskDispatch / SessionImportReceive; WorkerPool).
      leftover_* / TierACodec / LegacyPipeImport live on MemNetArchive
      (models/archive.sysml; off ProjectMemNet load). MUST NOT nest
      here.
      HostSearchBridge / EvidenceCentre / CousinPointingContrast /
      MemNetUsageDashboard / MemNetOpsFleet MUST NOT nest here.
      TipMemNetAccessPortal MUST NOT nest here.
      Only MN-REQ-00 satisfied here.
      usageDashboardInsideSystem=false (ops look is outside; not MCP face).
      opsFleetInsideSystem=false (device services + one droplet MemNet
      MCP tip/ops is outside; product face is sysmledge).
      tipAccessPortalInsideSystem=false (keyed tip access is outside;
      tip≠face; not a sysmledge product).
    */
    part core : MemNetCoreLibrary;
    part mcp : MemNetMcpServer;
    part durable : DurableBuffer;
    part pinMaps : PinMapRoadmap;
    part multitask : MultitaskOperatingModel;
    attribute usageDashboardInsideSystem : Boolean = false;
    attribute opsFleetInsideSystem : Boolean = false;
    attribute tipAccessPortalInsideSystem : Boolean = false;
    attribute leftoverFogNested : Boolean = false;
    attribute leftoverArchiveOffLoad : Boolean = true;
    attribute leftoverLayerDeleteThisPr : Boolean = false;
    attribute leftoverLayerMustNotNestOnProductPath : Boolean = true;

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
      end port source ::> durable.hydrateOut;
      end port sink ::> core.transport.inProcess.memory.sessions.hydrateIn;
    }
    connection durableFlush : DurableFlushFlow {
      end port source ::> core.transport.inProcess.memory.sessions.flushOut;
      end port sink ::> durable.flushIn;
    }
    connection catalogLocatorToMcpList : CatalogSessionLocatorFlow {
      end port source ::> pinMaps.catalog.locatorOut;
      end port sink ::> mcp.tools.sessionList.locatorIn;
    }
    connection catalogLocatorToCliList : CatalogSessionLocatorFlow {
      end port source ::> pinMaps.catalog.locatorOut;
      end port sink ::> core.cli.sessionList.locatorIn;
    }

    satisfy MN_REQ_00_MissionBridge;
  }

  part memNetSystem : MemNetSystem;

  // =====================================================================
  // APPLICATION NEST — HostSearchBridge (MUST NOT instantiate under
  // MemNetSystem). Optional locators into existing MutateGate / ingest.
  // Extra 0.17: RagHostHook.implemented=true; skip is valid.
  // Grammar: docs/extras/memnet-host-search-nest.md
  // =====================================================================

  part def RagHostHook {
    doc /*
      Optional host corpus plug-in (grep / docs MCP / optional 0.16
      library locators / fail-open URL). Product compression = Snap
      (topics / locators from the library haystack). Locator-only,
      fail-open, MUST NOT mutate the session, MUST NOT appear as
      memnet-mcp rag_query, MUST NOT ANN-index session S
      (Snap-on-session forbidden). Skip is valid (pin_map Shape + grep).
      Extra 0.17 ships the hook outside MemNetSystem. Module:
      memnet.rag_host_hook.
    */
    port locatorIn : LibraryLocatorInPort;
    port locatorOut : LibraryLocatorOutPort;
    attribute implemented : Boolean = true;
    attribute designOnly : Boolean = false;
    attribute failOpen : Boolean = true;
    attribute locatorOnly : Boolean = true;
    attribute compressionKind : String = "snap";
    attribute snapOnSession : Boolean = false;
    attribute mcpRagQuery : Boolean = false;
  }

  part def HostSearchBridgePart {
    doc /*
      APPLICATION NEST root (item HostSearchBridge in connections).
      MUST NOT be a part of MemNetSystem. Snap = RagHostHook locators;
      Shape stays PinMapShapedRead. Hard commit is existing MutateGate /
      PinMapIngest — no LocatorCommit wrapper. MUST NOT Snap-on-session.
      Extra 0.16 library locators MAY feed locatorIn; hook consumes
      them as locators only (library generate stays false).
    */
    attribute designOnly : Boolean = false;
    part hook : RagHostHook;
    port locatorIn : LibraryLocatorInPort;
    port locatorOut : LibraryLocatorOutPort;

    connection hookIn : LibraryLocatorFlow {
      end port source ::> locatorIn;
      end port sink ::> hook.locatorIn;
    }
    connection hookEmit : LibraryLocatorFlow {
      end port source ::> hook.locatorOut;
      end port sink ::> locatorOut;
    }

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
  }

  part hostSearch : HostSearchBridgePart;

  connection libraryToHostSearch : LibraryLocatorFlow {
    doc /* Extra 0.16 library locators MAY feed the outside hook. */
    end port source ::> memNetSystem.durable.library.locatorOut;
    end port sink ::> hostSearch.locatorIn;
  }

  connection hostSearchToMutate : LibraryLocatorFlow {
    doc /*
      Host locators into existing MutateGate. MUST NOT absorb
      (ImportAbsorb is Path-B only). Skip is valid when the hook
      emits nothing.
    */
    end port source ::> hostSearch.locatorOut;
    end port sink ::> memNetSystem.core.transport.inProcess.memory.sessions.recallCommit.commit.mutate.libraryLocatorIn;
  }

  // =====================================================================
  // OPS LOOK — MemNetUsageDashboard (MUST NOT instantiate under
  // MemNetSystem). Human read-only usage; manage = Memnetor + Devicor.
  // HTTP/UI parked (httpImplemented=false) until Core GO.
  // =====================================================================

  part def ServeStatusLook {
    doc /*
      Display serve_status: up / host / port plus expire-save booleans
      (save_on_expire, expire_snapshot_dir_set). Path redacted. Look only.
    */
    attribute lookOnly : Boolean = true;
    attribute saveOnExpireFlag : Boolean = true;
    attribute expireSnapshotDirSetFlag : Boolean = true;
    attribute pathRedacted : Boolean = true;
  }

  part def SessionCensusLook {
    doc /*
      Display @STAT sessions|n/max and listed session ids (cheap row
      counts when available). Look only — SHALL NOT session_close.
    */
    attribute lookOnly : Boolean = true;
    attribute sessionClose : Boolean = false;
  }

  part def HousekeepLook {
    doc /*
      Display housekeep_stats caps / row counts. Look only —
      SHALL NOT prune / settle from the page.
    */
    attribute lookOnly : Boolean = true;
    attribute pruneFromPage : Boolean = false;
  }

  part def ImportGuardArmedDisplay {
    doc /*
      Display ImportGuard armed/disarmed from env presence.
      MUST NOT show or accept the API key. MUST NOT enable/disable.
    */
    attribute lookOnly : Boolean = true;
    attribute keyOnPage : Boolean = false;
    attribute writable : Boolean = false;
  }

  part def MemNetUsageDashboard {
    doc /*
      Human look surface for MemNet serve usage (MN-REQ-06.5).
      Observes TcpServeBridge / CmdSessionList / HousekeepSettle /
      CheapLlmImportGuard armed flag and MultitaskSharedStoreBinding
      (shared registry). SHALL NOT own SessionLifecycle. SHALL NOT nest
      under MemNetSystem (not MCP/CLI face; tip is not face; not Foam
      product MCP). Manage of serve / MCP / roll / housekeep /
      ImportGuard env = Memnetor + Devicor.
      HTTP/UI parked: httpImplemented=false until Core GO.
      MUST NOT ports: session_close, mutate, import_slice, key entry,
      reproject.
    */
    port serveLookIn : ServeUsageLookInPort;
    port sessionLookIn : ServeUsageLookInPort;
    port housekeepLookIn : ServeUsageLookInPort;
    port armedLookIn : ImportGuardArmedLookInPort;
    port pageOut : HumanLookOutPort;
    part serveStatus : ServeStatusLook;
    part sessionCensus : SessionCensusLook;
    part housekeep : HousekeepLook;
    part importGuardArmed : ImportGuardArmedDisplay;
    attribute lookOnly : Boolean = true;
    attribute httpImplemented : Boolean = false;
    attribute agentWire : Boolean = false;
    attribute foamProductMcp : Boolean = false;
    attribute tipIsFace : Boolean = false;
    attribute localBindDefault : Boolean = true;
    attribute manageViaPage : Boolean = false;
    attribute sessionClosePort : Boolean = false;
    attribute mutatePort : Boolean = false;
    attribute importSlicePort : Boolean = false;
    attribute keyEntryPort : Boolean = false;
    attribute reprojectPort : Boolean = false;
    attribute ownsSessionLifecycle : Boolean = false;
    attribute insideMemNetSystem : Boolean = false;
    attribute manageOwners : String = "Memnetor+Devicor";
    attribute lookActor : String = "human";

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_5_HumanUsageLook;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_3_SessionTtlAndCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_1_StoreResourceCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_3_NoDomainProductTools;
  }

  part usageDashboard : MemNetUsageDashboard;

  connection tcpStatusToDashboard : ServeUsageLookFlow {
    doc /* serve_status observe; dashboard does not send ServeCommand. */
    end port source ::> memNetSystem.core.transport.tcp.usageLookOut;
    end port sink ::> usageDashboard.serveLookIn;
  }

  connection sessionListToDashboard : ServeUsageLookFlow {
    doc /* sessions|n/max + ids from MCP session_list (look only). */
    end port source ::> memNetSystem.mcp.tools.sessionList.usageLookOut;
    end port sink ::> usageDashboard.sessionLookIn;
  }

  connection housekeepStatsToDashboard : ServeUsageLookFlow {
    doc /* housekeep_stats observe; no prune from the page. */
    end port source ::> memNetSystem.core.transport.inProcess.memory.sessions.housekeep.usageLookOut;
    end port sink ::> usageDashboard.housekeepLookIn;
  }

  connection importGuardArmedToDashboard : ImportGuardArmedLookFlow {
    doc /* Armed display from env presence; no key; no write toggle. */
    end port source ::> memNetSystem.multitask.coordinator.importReceive.guard.cheapLlm.armedLookOut;
    end port sink ::> usageDashboard.armedLookIn;
  }

  // =====================================================================
  // OPS FLEET — MemNetOpsFleet (MUST NOT instantiate under MemNetSystem).
  // Multiple device MemNet services; one MemNet MCP (tip/ops) at droplet.
  // Product invent face = cousin sysmledge (tip≠face). Not #47.
  // =====================================================================

  part def DropletHost {
    doc /*
      DigitalOcean droplet. Hosts the fleet's one MemNetSystem, hence
      the one MemNetMcpServer (MemNet tip/ops engine face; tip≠face)
      plus local core / CompanyMemory. mcpCount=1 counts that MemNet
      MCP, not the product invent face. The product LLM face on this
      host is cousin SysMLEdge (`sysmledge`; MUST NOT nest under
      MemNetSystem; mustNotInventUploadBind). MUST NOT add a second
      product MCP on this host.
    */
    part memnet : MemNetSystem;
    attribute hostKind : String = "droplet";
    attribute mcpCount : Integer = 1;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_6_DeviceServicesOneDropletMcp;
  }

  part def MemNetDeviceHost {
    doc /*
      Compute device (Pi, workstation, SBC). Hosts a MemNet service
      (engine + serve + CLI) as a local notepad / device working set.
      MUST NOT nest a second product MCP. MUST NOT nest
      SysMLEdge-as-product on the device. mcpNested=false /
      productMcpNested=false mean no product MCP nested — not a ban
      on ops tip. A tip MemNet MCP (memnet-mcp) MAY run here for
      engine ops and remains tip≠face (tipMcpLegal=true; not sold
      as product). Session registry is this host's own; MUST NOT
      mash handles with the droplet. Software-only host (no ISQ/SI).
      Illustrative first device: rpi5-syson.
    */
    part service : MemNetCoreLibrary;
    attribute hostKind : String = "device";
    attribute mcpNested : Boolean = false;
    attribute productMcpNested : Boolean = false;
    attribute tipMcpLegal : Boolean = true;
    attribute nServerPeer : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_6_DeviceServicesOneDropletMcp;
  }

  part def MemNetOpsFleet {
    doc /*
      OPS nest outside MemNetSystem (MN-REQ-06.6). Device hosts run
      MemNetCoreLibrary services; the droplet hosts the one MemNet
      MCP (tip/ops engine face; tip≠face; mcpCount=1). Product invent
      face is cousin SysMLEdge (`sysmledge`; mustNotInventUploadBind).
      Dual-MCP remeter: product questions → sysmledge only; MemNet
      tip/ops → droplet MemNet MCP and/or Pi tip. MUST NOT answer
      product questions on the MemNet tip path. Each service keeps
      its own session handles. Handoff remains session id; optional
      Path-B ImportAbsorb is not a live-server MERGE.
      nServerFederation=false (#47 stays research).
    */
    part droplet : DropletHost;
    part devices : MemNetDeviceHost[1..*];
    attribute mcpCount : Integer = 1;
    attribute nServerFederation : Boolean = false;
    attribute insideMemNetSystem : Boolean = false;
    attribute fleetMcpHost : String = "droplet";
    attribute productInventFace : String = "sysmledge";
    attribute mustNotInventUploadBind : Boolean = true;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_6_DeviceServicesOneDropletMcp;
  }

  part opsFleet : MemNetOpsFleet;

  // =====================================================================
  // OPS ACCESS — TipMemNetAccessPortal (MUST NOT instantiate under
  // MemNetSystem). Gated keys for tip MemNet MCP only. tip≠face.
  // Not a sysmledge product. Portal web is the ops sidecar
  // (ops/tip_access_portal). sellsInvent2Green=false.
  // =====================================================================

  part def TipAccessAdmin {
    doc /*
      Portal admin. Display name Szu-Wei. Mints invite links and
      revokes Bearers. Not a SysMLEdge product owner screen.
    */
    attribute displayName : String = "Szu-Wei";
    attribute role : String = "admin";
    port mintOut : InviteMintOutPort;
    port revokeOut : TipBearerOutPort;
  }

  part def InvitedTipUser {
    doc /*
      User who redeemed an invite. Signs in with Google, then fetches
      and sees their tip MCP Bearer. Strangers without an invite get
      no key.
    */
    attribute allowlistRedeem : Boolean = true;
    port loginOut : GoogleLoginOutPort;
    port keyViewIn : TipBearerInPort;
  }

  part def GoogleIdP {
    doc /*
      Google OAuth identity provider for the portal. Asserts a
      signed-in subject. MUST NOT gate the sysmledge product face.
    */
    attribute provider : String = "google";
    port loginIn : GoogleLoginInPort;
    port assertOut : GoogleAssertOutPort;
  }

  part def InviteStore {
    doc /*
      Stores admin-minted invites and the allowlist redeem. Mint is
      admin-only.
    */
    attribute adminMintOnly : Boolean = true;
    port mintIn : InviteMintInPort;
    port redeemOut : InviteMintOutPort;
  }

  part def KeyStore {
    doc /*
      Issues, shows, and revokes Bearer keys for the tip MCP.
      Shown only after invite redeem and Google login. Tracks last
      used time and call count for the portal look page (hashed
      keys only; plaintext never stored).
    */
    attribute bearerShownAfterLogin : Boolean = true;
    attribute revokeSupported : Boolean = true;
    attribute lastUsedTracked : Boolean = true;
    attribute useCountTracked : Boolean = true;
    port issueIn : TipBearerInPort;
    port bearerOut : TipBearerOutPort;
    port showOut : TipBearerOutPort;
    port revokeIn : BearerRevokeInPort;
  }

  part def PortalWeb {
    doc /*
      Droplet WWW page: Google login, invite redeem, show Bearer,
      and look-only status of configured MemNet listeners plus
      Bearer client last-used. Implemented as the ops sidecar
      ops/tip_access_portal (portalWebImplemented=true). Google
      client secrets stay in the environment, not in this model.
      Not an openProject key page. Status look MUST NOT unpark
      MemNetUsageDashboard HTTP (unparksUsageDashboard=false;
      dashboard httpImplemented stays false). MUST NOT restart,
      mutate, or session_close from the page.
    */
    attribute portalWebImplemented : Boolean = true;
    attribute serviceLookImplemented : Boolean = true;
    attribute clientLookImplemented : Boolean = true;
    attribute statusLookOnly : Boolean = true;
    attribute unparksUsageDashboard : Boolean = false;
    port googleIn : GoogleAssertInPort;
    port inviteIn : InviteMintInPort;
    port keyFetchOut : TipBearerOutPort;
    port showIn : TipBearerInPort;
    port showOut : TipBearerOutPort;
  }

  part def TipMcpGate {
    doc /*
      nginx/auth forward on droplet WWW in front of tip MemNet MCP
      only: https://memnet.139-59-255-181.nip.io/mcp.
      Requires Authorization: Bearer. Refuses unauthenticated MemNet
      on that URL. Forwards to the Pi tip. Does not gate sysmledge.
      Keyed tip MemNet on WWW stays; free/unauthenticated MemNet on
      WWW does not.
    */
    attribute wwwUrl : String = "https://memnet.139-59-255-181.nip.io/mcp";
    attribute authorizationScheme : String = "Bearer";
    attribute keyedAuthRequired : Boolean = true;
    attribute unauthenticatedAllowed : Boolean = false;
    attribute forwardHost : String = "pi-tip";
    attribute gatesSysmlEdge : Boolean = false;
    attribute nginxAuthForward : Boolean = true;
    port bearerIn : TipBearerInPort;
    port forwardOut : TipForwardOutPort;
  }

  part def PiTipMemNetMcp {
    doc /*
      Forward target: tip memnet-mcp on the Pi. tip≠face. Not the
      public WWW listener and not a nested MemNetSystem. Public
      callers reach it only through TipMcpGate.
    */
    attribute hostKind : String = "pi-tip";
    attribute tipIsFace : Boolean = false;
    attribute unauthenticatedPublic : Boolean = false;
    port mcpIn : TipForwardInPort;
  }

  part def TipMemNetAccessPortal {
    doc /*
      OPS nest outside MemNetSystem (MN-REQ-06.8). Admin (Szu-Wei)
      mints invites. Invited user signs in with Google, then the
      portal shows their Bearer for the tip MemNet MCP. TipMcpGate
      checks that Bearer and forwards to the Pi tip. tip≠face.
      isSysmlEdgeProduct=false; openProjectKeyPage=false;
      grantsOpenMemNet=false. Free for strangers is the SysMLEdge
      free tier or memnet-llm self-host (freeStrangerPath). The
      portal web is implemented (inventOnly=false;
      portalWebImplemented=true) and MUST NOT be sold as
      invent_2_green (sellsInvent2Green=false). Status look of
      services and Bearer clients is look-only
      (statusLookOnly=true; serviceLookImplemented=true;
      clientLookImplemented=true) and MUST NOT unpark the
      usage dashboard HTTP (unparksUsageDashboard=false).
    */
    part admin : TipAccessAdmin;
    part user : InvitedTipUser;
    part google : GoogleIdP;
    part portal : PortalWeb;
    part invites : InviteStore;
    part keys : KeyStore;
    part gate : TipMcpGate;
    part piTip : PiTipMemNetMcp;
    attribute insideMemNetSystem : Boolean = false;
    attribute tipIsFace : Boolean = false;
    attribute isSysmlEdgeProduct : Boolean = false;
    attribute openProjectKeyPage : Boolean = false;
    attribute grantsOpenMemNet : Boolean = false;
    attribute unauthenticatedWwwMcp : Boolean = false;
    attribute keyedWwwMcp : Boolean = true;
    attribute inventOnly : Boolean = false;
    attribute portalWebImplemented : Boolean = true;
    attribute sellsInvent2Green : Boolean = false;
    attribute serviceLookImplemented : Boolean = true;
    attribute clientLookImplemented : Boolean = true;
    attribute statusLookOnly : Boolean = true;
    attribute unparksUsageDashboard : Boolean = false;
    attribute gatesTipMcpOnly : Boolean = true;
    attribute freeStrangerPath : String = "sysmledge-free-tier-or-memnet-llm-self-host";

    connection adminMintsInvite : InviteMintFlow {
      doc /* Admin → Invite. */
      end port source ::> admin.mintOut;
      end port sink ::> invites.mintIn;
    }
    connection inviteRedeem : InviteMintFlow {
      doc /* Allowlist redeem into the portal. */
      end port source ::> invites.redeemOut;
      end port sink ::> portal.inviteIn;
    }
    connection userToGoogle : GoogleLoginFlow {
      doc /* User → Google. */
      end port source ::> user.loginOut;
      end port sink ::> google.loginIn;
    }
    connection googleToPortal : GoogleAssertFlow {
      doc /* Google → Portal. */
      end port source ::> google.assertOut;
      end port sink ::> portal.googleIn;
    }
    connection portalToKey : TipBearerFlow {
      doc /* Portal → Key. */
      end port source ::> portal.keyFetchOut;
      end port sink ::> keys.issueIn;
    }
    connection keyToPortalShow : TipBearerFlow {
      doc /* Key store returns the Bearer to the portal for display. */
      end port source ::> keys.showOut;
      end port sink ::> portal.showIn;
    }
    connection portalShowsKey : TipBearerFlow {
      doc /* Portal shows the Bearer to the invited user. */
      end port source ::> portal.showOut;
      end port sink ::> user.keyViewIn;
    }
    connection adminRevokesKey : BearerRevokeFlow {
      doc /* Admin revoke into the key store. */
      end port source ::> admin.revokeOut;
      end port sink ::> keys.revokeIn;
    }
    connection keyToGate : TipBearerFlow {
      doc /* Key → TipMcpGate. */
      end port source ::> keys.bearerOut;
      end port sink ::> gate.bearerIn;
    }
    connection gateToPiTip : TipForwardFlow {
      doc /* TipMcpGate → Pi tip MemNet MCP. */
      end port source ::> gate.forwardOut;
      end port sink ::> piTip.mcpIn;
    }

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_8_TipMemNetAccessPortal;
  }

  part tipAccessPortal : TipMemNetAccessPortal;
}
