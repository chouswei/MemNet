/*
  MemNet deploy — TARGET architecture after ADR-001.

  Product framing (2026-08-13): MemNet = shared LLM memory (SharedLlmMemory);
  session id = pass-by-reference handle for a MissionWorkingSet; durable GQL
  store (DurableBuffer / AgensGraphAdapter) planned M2.5 behind MemNet.

  Nesting (coarse → fine):
    MemNetSystem                    // SharedLlmMemory product
    ├── AgentMemory                 // session-scoped working set + GQL wire
    │   └── SessionLifecycle        // usage: sessions.recallCommit
    │       ├── GraphStore
    │       ├── GqlWire             // 1.x primary codec (openCypher-shaped)
    │       ├── RecallCommit        // 0.5 cut: TWO operators only
    │       │   ├── Recall          // seed(q)+k-hop expand; empty seed ⇒ skip
    │       │   │   └── AgentShapedRead // honesty nest (pin_map vs find flags)
    │       │   │       ├── PinMapShapedRead    // implemented=true — goldfish
    │       │   │       └── BoundedMatchFind    // implemented=false — leftover #73
    │       │   └── Commit          // ONE gate; mutate/ingest/absorb = id rules
    │       │       ├── MutateGate
    │       │       └── NeighbourhoodReserve // RSV lease — not a third API
    │       ├── Schema / Caps (size + shipped ACL) / …
    │       └── (TierACodec RETIRED/REJECTED — leftover retire-from-wheel; not nested)
    ├── TransportBoundary           // InProcess / LocalIpc / TcpServe
    ├── MemNetMcpServer             // LLM ↔ MemNet (GQL/MCP)
    ├── DurableBuffer               // AgensGraphAdapter planned M2.5
    ├── PinMapRoadmap               // all PinMapIngest_* domains shipped (#64)
    └── MultitaskOperatingModel
        ├── MultitaskCoordinator          // team lead
        │   ├── SessionHandoffEmit        // session id + scope handoff
        │   ├── AsyncTaskDispatch         // spawn N workers; end turn
        │   └── SessionImportReceive      // path B only (path A never enters)
        │       ├── ImportGuard           // OPTIONAL soft nest (like PinMapRoadmap)
        │       │   ├── ImportGuardHook   // shipped #49 (set_import_guard)
        │       │   ├── CheapLlmImportGuard // shipped #63 / 12.11 (env-gated)
        │       │   └── Soft* leaves      // allow|trim|reject; trim subtractive
        │       └── ImportAbsorb          // engine SHALL hard
        │           ├── DistinctSession / SliceBudget / LawVocabExclude / Acl
        │           ├── IdPolicyKeep|Reject|Remint
        │           └── NodesThenEdgesCommit (+ optional decision atom)
        ├── WorkerPool
        │   └── MultitaskWorker[1..*]     // + WorkingMemorySliceExport (hard)
        └── MultitaskSharedStoreBinding
  Path A: shared mission sessionId → pin_map only (no import nest).
  Path B: bounded WorkingMemorySlice → optional ImportGuard → ImportAbsorb
  (id_policy keep|reject|remint). Not append. Not N-server federation.
  Hook shipped ≠ cheap LLM shipped. Module cite: memnet.import_absorb.

  APPLICATION (not in MemNetSystem): HostSearchBridge — optional host
  locators into existing MutateGate / ingest. No ImportGuard leaf copy.
  Design only. Grammar: docs/grammar/memnet-host-search-nest.md

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
      Tier A NODE|EDGE ASCII (MemNetLayer.g4 / memnet.tier_a / memnet.layer).
      MutateGate rejects with legacy_dialect_retired. MUST NOT be nested as
      accept or 1.x teach. Hierarchical reconstruct (Recall k-hop) is NOT
      Layer dialect. Leftover retire-from-wheel: modules may remain on disk
      for archive/tests; MUST NOT silently delete in the math-skeleton PR.
      Primary wire is GqlCodec.
    */
    port tierAIn : TierAInPort;
    port tierAOut : TierAOutPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port errOut : ErrorSignalOutPort;
    attribute productPathRetired : Boolean = true;
    attribute mustNotNestOnProductPath : Boolean = true;
    attribute leftoverIssue : String = "retire-from-wheel";
    attribute deleteThisPr : Boolean = false;
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
      (2) PinMapIngest_* domains (Sysml/Codebase/PcbaAto/SkillsRules) --
      deterministic id from locator key. As-is: memnet.id_allocator.
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
      Default agent goldfish read when an ego/anchor id is known.
      Nested under Recall / AgentShapedRead beside BoundedMatchFind —
      pin_map implemented=true MUST NOT be misread as find shipped.
      Same Recall operator as leftover BoundedMatchFind; seed rule differs
      (known id vs bounded MATCH).
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
    attribute implemented : Boolean = true;
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

  part def BoundedMatchFind {
    doc /*
      Bounded MATCH find when there is no ego/anchor id, or when pin_map
      caps dropped a needed row (#13). Inputs: label and/or property /
      locator predicates; LIMIT required (hard). Optional max_rows aligned
      with MN-REQ-04.3. Emit the same shaped subgraph family as pin_map /
      mutate (MN-REQ-08.9) — not a binding-table RETURN.
      MUST NOT: missing LIMIT; unbounded MATCH; variable-length path as
      default; full openCypher (WITH / UNWIND / CALL / subqueries / ORDER BY)
      as agent teach. Cite openCypher.bnf for MATCH spelling only.
      Distinct from mutate MATCH (n {id}) SET — this leaf is a read.
      Nested under Recall / AgentShapedRead beside PinMapShapedRead —
      same Recall operator; seed = bounded MATCH (hard LIMIT L), not ego id.
      Modelled; not shipped (implemented=false; leftover #73). MUST NOT
      claim find shipped because pin_map shipped.
    */
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;
    attribute implemented : Boolean = false;
    attribute leftoverIssue : String = "#73";
    attribute limitRequired : Boolean = true;
    attribute emitShapedSubgraph : Boolean = true;
    attribute allowTabularReturn : Boolean = false;
    attribute variableLengthPathDefault : Boolean = false;
    attribute doctrineAsIs : Boolean = false;
    part caps : CapsPolicy;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_6_BoundedMatchFind;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_9_PinMapEmitSameAsMutate;
  }

  part def AgentShapedRead {
    doc /*
      Honesty nest under Recall so pin_map shipped cannot be misread as
      find shipped. Children: PinMapShapedRead (implemented=true; default
      goldfish when anchored) and BoundedMatchFind (implemented=false;
      leftover #73). Parent has no single implemented=true — that flag
      lives on children only. WalkQuery remains a sibling under
      SessionLifecycle (relation hop lines), not this nest.
    */
    port pinMapOut : LivePinMapOutPort;
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;
    part pinMap : PinMapShapedRead;
    part find : BoundedMatchFind;
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
      docs/grammar/memnet-neighbourhood-reserve.md.
      As-is: implemented (MN-REQ-12.13).
    */
    attribute implemented : Boolean = true;
    attribute holderField : String = "llm_id";
    attribute ttlField : String = "ttl_s";
    attribute displayKind : String = "RSV";
    attribute doctrineAsIs : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_13_NeighbourhoodReserve;
  }

  part def Recall {
    doc /*
      Operator Recall(q) over session graph S (MN-REQ-13). Cue q is a
      discrete codebook token (id ∪ kind ∪ locator ∪ keyword).
      seed(q,S) = {q} if q is already a node id; else bounded MATCH on
      label/property/locator with HARD LIMIT L (BoundedMatchFind; #73).
      Empty seed ⇒ skip (do not invent a node). Reconstruct X̃ = k-hop
      ego from the seed, diameter ≤ k, |X̃| ≤ M (max_rows); hide recycled
      rows. Emit the same shaped GQL subgraph family as mutate (not tabular
      RETURN). Information bottleneck: X̃ compresses S given q. Metric is
      hops, not cosine. Hierarchical reconstruct ≠ Layer dialect.
      Grammar SSOT: docs/grammar/math-skeleton.md. Engine cut not this PR.
    */
    port shapedOut : ShapedSubgraphOutPort;
    port gqlOut : GqlWireOutPort;
    port errOut : ErrorSignalOutPort;
    attribute emptySeedSkip : Boolean = true;
    attribute hopMetric : String = "hops";
    attribute cosineMetric : Boolean = false;
    part shapedRead : AgentShapedRead;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_1_AnchoredPinMap;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_3_PinMapDepthAndRowCaps;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
  }

  part def Commit {
    doc /*
      Operator Commit(Δ) — ONE gate. mutate / ingest / absorb are id-mint
      rules, not three product verbs. Default: client NEW → engine id
      (MutateGate / IdAllocator). Ingest: deterministic locator id from
      artefact (PinMapIngest_* under PinMapRoadmap — not a second gate).
      Absorb: Path-B only (ImportAbsorb + WorkingMemorySlice + id_policy
      keep|reject|remint). Optional ImportGuard / CheapLlmImportGuard stay
      Path-B soft, fail-open. RSV is a lease nested here, not a third API.
      HostSearchBridge stays OUTSIDE MemNetSystem. Engine cut not this PR.
    */
    port gqlIn : GqlWireInPort;
    port recordsOut : GraphRecordOutPort;
    port recordsIn : GraphRecordInPort;
    port idsOut : AssignedIdOutPort;
    port errOut : ErrorSignalOutPort;
    attribute oneGate : Boolean = true;
    attribute productVerbs : String = "Commit";
    attribute ingestIsIdRule : Boolean = true;
    attribute absorbPathBOnly : Boolean = true;
    part mutate : MutateGate;
    part reserve : NeighbourhoodReserve;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_9_LeadOwnsSessionImport;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_13_NeighbourhoodReserve;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;
  }

  part def RecallCommit {
    doc /*
      0.5 mechanism parent under SessionLifecycle: TWO operators only —
      Recall(q) and Commit(Δ). Existing PinMapShapedRead / BoundedMatchFind
      nest under Recall; MutateGate / NeighbourhoodReserve nest under
      Commit. PinMapIngest_* and ImportAbsorb remain in PinMapRoadmap /
      SessionImportReceive as id-mint rules of Commit, not extra operators.
      HostSearchBridge MUST NOT nest here. Modelled math skeleton; no
      engine cut in this PR. Docs: docs/grammar/math-skeleton.md.
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
      GraphStore + SchemaRegistry + RecallCommit (Recall + Commit) facades.
      Each session id is the pass-by-reference handle for a MissionWorkingSet
      (SOMETHING). Nested under AgentMemory (SharedLlmMemory). As-is:
      memnet.registry + session. M2.5 hydrate/flush ports to DurableBuffer —
      client landed; live cabinet external. RSV lease lives under Commit.
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
      GqlCodec, RecallCommit (Recall / AgentShapedRead / PinMapShapedRead +
      BoundedMatchFind; Commit / MutateGate + NeighbourhoodReserve).
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
      operator-proven — not vendored in-repo and not claimed verified.
      MUST NOT dual-write without a single sync owner. MUST NOT be the LLM
      primary path (LLM ↔ MemNet only). MN-REQ-06.4.
    */
    port hydrateOut : DurableHydrateOutPort;
    port flushIn : DurableFlushInPort;
    port gqlIn : GqlWireInPort;
    port gqlOut : GqlWireOutPort;
    // Client hydrate/flush adapter seam (Fake + optional AgensGraph client).
    attribute implemented : Boolean = true;
    // Live external AgensGraph cabinet — not claimed; needs operator proof.
    attribute liveCabinetClaimed : Boolean = false;
    attribute phase : String = "M2.5";
  }

  part def DurableBuffer {
    doc /*
      Optional durable property-graph buffer behind MemNet SharedLlmMemory.
      Connects to GraphStore / SessionLifecycle via hydrate/flush — not to
      LLM agents as primary. M2.5 client hydrate/flush landed; live
      external cabinet deferred (not claimed). MN-REQ-06.4.
    */
    part agens : AgensGraphAdapter;
    port hydrateOut : DurableHydrateOutPort;
    port flushIn : DurableFlushInPort;
    attribute clientLanded : Boolean = true;
    attribute liveCabinetClaimed : Boolean = false;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_4_DurableStoreBehindMemNet;
  }

  // =====================================================================
  // MN-REQ-11 Path-B PinMapIngest (selective external artefact → pins)
  // Domains shipped: Sysml, Codebase, PcbaAto, SkillsRules (#31 / #64).
  // Export / round-trip (MN-REQ-11.1–11.5) is separate (#66) — not claimed.
  // Module: memnet.pin_map_ingest. Distinct from SnapshotStore + live
  // PinMapShapedRead. MUST NOT invent N-server federation.
  // =====================================================================

  part def PinMapIngestBase {
    doc /*
      Shared Path-B ingest interface: project a bounded NODE|EDGE pin map from
      an external artefact using stable locators (path=, qname=, refdes=, …).
      Deterministic MemNet ids via IdAllocator.allocate_from_locator
      (MN-REQ-11.16). Client NEW / [NEW] illegal for source pins. Wire = GQL
      only (MERGE/CREATE ground ids). Commit into session GraphStore via
      MutateGate. As-is module: memnet.pin_map_ingest.
    */
    attribute domainVariant : String;
    attribute implemented : Boolean = false;
    attribute roadmapOnly : Boolean = true;
    attribute rejectsClientNew : Boolean = true;
    attribute wireDialect : String = "gql";
    port pinOut : PinMapOutPort;
    port recordsOut : GraphRecordOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapIngest_Sysml {
    doc /*
      FIRST Path-B engine (ship order). Selective SysML v2 .sysml → PKG / PRT /
      REQ (+ optional POR) pins with path= + qname= (+ requirementId=).
      Bounded (max_nodes / file caps). As-is: implemented (MN-REQ-11.1–11.5,
      11.13, 11.16; issue #31). Module: memnet.pin_map_ingest.PinMapIngest_Sysml.
    */
    attribute domainVariant : String = "sysml";
    attribute implemented : Boolean = true;
    attribute roadmapOnly : Boolean = false;
    attribute firstEngine : Boolean = true;
    attribute rejectsClientNew : Boolean = true;
    attribute wireDialect : String = "gql";
    attribute nodeKinds : String = "PKG,PRT,REQ,POR";
    attribute edgeRelations : String = "contains,satisfies";
    port pinOut : PinMapOutPort;
    port recordsOut : GraphRecordOutPort;

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
    port pinOut : PinMapOutPort;
    port recordsOut : GraphRecordOutPort;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_10_SnapshotSkillsAndRulesIntoGraph;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_11_SkillsAndRulesAreNodes;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_12_SkillsRulesEdgesAreRelations;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;
  }

  part def PinMapRoadmap {
    doc /*
      Path-B PinMapIngest nest. Ship order complete for domains: Sysml,
      Codebase, PcbaAto, SkillsRules (all implemented). Id-mint rule of
      Commit (deterministic locator ids) — not a second product operator.
      Not N-server federation. Export / round-trip (MN-REQ-11.1–11.5)
      remains separate (#66). As-is module: memnet.pin_map_ingest.
    */
    attribute firstDomain : String = "sysml";
    attribute roadmapOnly : Boolean = false;
    attribute allDomainsImplemented : Boolean = true;
    part interface : PinMapIngestBase;
    part sysml : PinMapIngest_Sysml;
    part codebase : PinMapIngest_Codebase;
    part pcbaAto : PinMapIngest_PcbaAto;
    part skillsRules : PinMapIngest_SkillsRules;
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
      id_policy=keep: engine SHALL MERGE-by-id upsert into the lead session
      SSOT (store.upsert). Not a second copy. Not append. Not product name
      "merge". Distinct from micro merge=true re-id.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute idPolicy : String = "keep";
  }

  part def IdPolicyReject {
    doc /*
      id_policy=reject: engine SHALL raise id_conflict and MUST NOT mutate
      the lead session when any slice id already exists in lead.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute idPolicy : String = "reject";

    satisfy MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
  }

  part def IdPolicyRemint {
    doc /*
      id_policy=remint: engine SHALL mint NEW ids for conflicts; lead old
      rows stay; edge src/dist retarget via id map. Non-conflict ids kept.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute idPolicy : String = "remint";
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
      GuardDecisionAtomRecord. Path-B id-mint rule of Commit (keep|reject|
      remint) — not a second product operator beside Recall/Commit.
      Product verb = import. Path A never enters.
      When ImportGuard skipped/disabled, absorb after SessionImportRequest
      + slice alone. Module: memnet.import_absorb.
    */
    attribute gateKind : String = "hard";
    attribute actor : String = "engine";
    attribute doctrineAsIs : Boolean = false;
    attribute implemented : Boolean = true;
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
      merge=true ≠ this; keep = MERGE-by-id upsert mechanics inside
      IdPolicyKeep only. MN-REQ-12.11 is satisfied by CheapLlmImportGuard
      (not the hook / not this parent alone).
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
      (M2.5) + PinMapRoadmap (PinMapIngest_* = Commit id-mint rules) +
      MultitaskOperatingModel (Coordinator → HandoffEmit /
      AsyncTaskDispatch / SessionImportReceive; WorkerPool).
      TierACodec / LegacyPipeImport RETIRED — leftover retire-from-wheel;
      MUST NOT nest on product path. HostSearchBridge / EvidenceCentre
      MUST NOT nest here. Only MN-REQ-00 satisfied here.
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

  // =====================================================================
  // APPLICATION NEST — HostSearchBridge (MUST NOT instantiate under
  // MemNetSystem). Optional locators into existing MutateGate. Design only.
  // Grammar: docs/grammar/memnet-host-search-nest.md
  // =====================================================================

  part def RagHostHook {
    doc /*
      Optional host corpus plug-in (Cursor index / sibling RAG MCP).
      Locator-only, fail-open, MUST NOT mutate the session, MUST NOT
      appear as memnet-mcp rag_query. Skip is valid (pin_map + grep).
      Design only.
    */
    attribute implemented : Boolean = false;
    attribute designOnly : Boolean = true;
    attribute failOpen : Boolean = true;
    attribute locatorOnly : Boolean = true;
  }

  part def HostSearchBridgePart {
    doc /*
      APPLICATION NEST root (item HostSearchBridge in connections).
      MUST NOT be a part of MemNetSystem. Hard commit is existing
      MutateGate / PinMapIngest — no LocatorCommit wrapper.
    */
    attribute designOnly : Boolean = true;
    part hook : RagHostHook;

    satisfy MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
  }
}
