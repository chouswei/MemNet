/*
  MemNet requirements -- nested + atomic baseline (2026-07).

  ID scheme:
    MN-REQ-00          mission root (sole parent)
    MN-REQ-NN          group requirement (organisational; short framing doc)
    MN-REQ-NN.M        atomic leaf (one SHALL/SHOULD idea)
    MN-REQ-10          LLM assumed properties + limitation leaves

  Nesting: requirement def inside requirement def only (SysML requirements
  tree). Deploy software elements satisfy leaves; they are not the
  requirement structure.

  Formal derivation (SysML v2 idiom for SysML 1.x deriveReqt):
    import RequirementDerivation::*; then
    #derivation connection {
      end #original ::> <parent usage>;
      end #derive ::> <child usage>;
    }
    Groups derive from MN-REQ-00; leaves derive from their group.
    Nesting = structure; #derivation = formal deriveReqt edge.

  Breaking rename: MN-R1...MN-R9 retired. Do not map old numbers 1:1.

  Etymology: MemNet = Net of Memory -- durable facts + relations, not a chat
  notepad and not the search corpus.

  Mission SSOT: Net of Memory between LLM pipelines and data searching; aids
  system, programme, and hardware development, and documentation; save time
  and tokens; high factual accuracy; LLM-friendly grammar on stdio/MCP;
  canonical parser for human inspection. Conceptual data kinds: NODE | EDGE.

  Current realisation notes (not eternal identity):
    Agent grammar today is often @TAG pipe rows; relations often @EDG;
    session schema often TagMap; store often MemStore; serve often
    length-prefixed JSON {args, stdin}; fixed engine laws often LAW01-LAW05.
    Requirements state behavioural contracts; those spellings may change if
    the boundary still meets the contract.

  Stakeholders (comment only -- no structural defs in this file):
    LLM pipelines; data-search steps; MCP host; human inspectors who verify
    what the memory net knows via parse-faithful inspect/render.

  Out of scope: novel-writer product and general application framework.
  Structure (software elements, ports, connections) lives in deploy.sysml
  and connections.sysml.
*/
package MemNetRequirements {
  private import ScalarValues::*;
  private import RequirementDerivation::*;

  // --- Mission root (nested requirement tree only) ---

  requirement def MN_REQ_00_MissionBridge {
    doc /*
      SHALL provide a Net of Memory (MemNet): an in-memory network of durable
      facts and relations -- not a chat notepad and not the search corpus --
      that sits between pipelines of LLM calls and data searching, aiding the
      LLM for system development, programme development, hardware development,
      and documentation, with the aims of saving wall-clock time and token
      usage while keeping high accuracy when presenting facts.
    */
    attribute requirementId : String = "MN-REQ-00";

    // ----- Session lifecycle -----

    requirement def MN_REQ_01_SessionLifecycle {
      doc /*
        Group: durable named session state across pipeline turns.
      */
      attribute requirementId : String = "MN-REQ-01";

      requirement def MN_REQ_01_1_NamedSessions {
        doc /*
          SHALL provide named sessions that retain working-memory state across
          turns so pipeline facts outlive chat context.
        */
        attribute requirementId : String = "MN-REQ-01.1";
      }

      requirement def MN_REQ_01_2_SessionLifecycleOps {
        doc /*
          SHALL support open, resume, save, load, and close for each named
          session.
        */
        attribute requirementId : String = "MN-REQ-01.2";
      }

      requirement def MN_REQ_01_3_SessionTtlAndCaps {
        doc /*
          SHALL apply configurable session TTL and a cap on concurrent
          sessions.
        */
        attribute requirementId : String = "MN-REQ-01.3";
      }
    }

    // ----- Memory net information model: NODE | EDGE -----

    requirement def MN_REQ_02_MemoryNetGraph {
      doc /*
        Group: the Net of Memory information model is exactly two conceptual
        data kinds -- NODE and EDGE. Tags or surface spellings may realise
        node kinds; they are not additional conceptual kinds. Current
        realisation often emits nodes as @TAG pipe rows and edges as @EDG.
      */
      attribute requirementId : String = "MN-REQ-02";

      requirement def MN_REQ_02_1_ExactlyNodeAndEdge {
        doc /*
          SHALL model the Net of Memory as exactly two conceptual data kinds:
          NODE and EDGE (relations between nodes).
        */
        attribute requirementId : String = "MN-REQ-02.1";
      }

      requirement def MN_REQ_02_2_NodesHoldAtomisedFacts {
        doc /*
          NODEs SHALL hold atomised facts and attributes -- one idea per
          field set -- not free-form prose or merged multi-idea blobs.
        */
        attribute requirementId : String = "MN-REQ-02.2";
      }

      requirement def MN_REQ_02_3_EdgesAreFirstClass {
        doc /*
          EDGEs SHALL be first-class relations between nodes, not buried in
          node attribute fields or narrative.
        */
        attribute requirementId : String = "MN-REQ-02.3";
      }

      requirement def MN_REQ_02_4_QueryOverNodeEdgeGraph {
        doc /*
          Warm, walk, and query SHALL operate over the NODE and EDGE graph.
        */
        attribute requirementId : String = "MN-REQ-02.4";
      }

      requirement def MN_REQ_02_5_GrammarExpressesNodeAndEdge {
        doc /*
          Agent-facing grammar and I/O SHALL express both NODE and EDGE.
        */
        attribute requirementId : String = "MN-REQ-02.5";
      }

      requirement def MN_REQ_02_6_ParserRecoversNodeAndEdge {
        doc /*
          The canonical parser SHALL recover both NODE and EDGE structure for
          human inspection.
        */
        attribute requirementId : String = "MN-REQ-02.6";
      }

      requirement def MN_REQ_02_7_SchemaValidatedIngest {
        doc /*
          SHALL validate ingest against the session schema and reject unknown
          or reserved surface kinds. Tags MAY realise NODE kinds; conceptual
          kinds remain NODE and EDGE only.
        */
        attribute requirementId : String = "MN-REQ-02.7";
      }
    }

    // ----- Strict mutate -----

    requirement def MN_REQ_03_StrictMutate {
      doc /*
        Group: explicit create vs replace; no silent upsert.
      */
      attribute requirementId : String = "MN-REQ-03";

      requirement def MN_REQ_03_1_AddFailsIfExists {
        doc /*
          SHALL fail create (add) with an id-exists error when the id is taken.
        */
        attribute requirementId : String = "MN-REQ-03.1";
      }

      requirement def MN_REQ_03_2_UpdateFailsIfAbsent {
        doc /*
          SHALL fail replace (update) with a not-found error when the id is
          absent.
        */
        attribute requirementId : String = "MN-REQ-03.2";
      }

      requirement def MN_REQ_03_3_NoSilentUpsert {
        doc /*
          Silent upsert SHALL NOT be offered.
        */
        attribute requirementId : String = "MN-REQ-03.3";
      }
    }

    // ----- Slice economy (warm / recycle / walk) -----

    requirement def MN_REQ_04_SliceEconomy {
      doc /*
        Group: small accurate live slices for LLM turns; hide recyclable rows;
        optional relation walk. Engine fixed-law rows (often LAW01-LAW05) are
        a current realisation, not the contract identity.
      */
      attribute requirementId : String = "MN-REQ-04";

      requirement def MN_REQ_04_1_AnchoredWarmSlice {
        doc /*
          SHALL return an anchored live neighbourhood for each turn, not the
          full session or a raw search dump.
        */
        attribute requirementId : String = "MN-REQ-04.1";
      }

      requirement def MN_REQ_04_2_RecycleHiddenFromWarm {
        doc /*
          SHALL hide rows marked for settle or expire recycle from the warm
          slice.
        */
        attribute requirementId : String = "MN-REQ-04.2";
      }

      requirement def MN_REQ_04_3_WarmDepthAndRowCaps {
        doc /*
          SHALL cap warm slice depth and row count.
        */
        attribute requirementId : String = "MN-REQ-04.3";
      }

      requirement def MN_REQ_04_4_EngineLawPrepend {
        doc /*
          SHALL prepend session engine-law rows to the warm slice when those
          rows are present in the store.
        */
        attribute requirementId : String = "MN-REQ-04.4";
      }

      requirement def MN_REQ_04_5_AnchoredWalk {
        doc /*
          Anchored walk hop lines over the NODE and EDGE graph SHOULD be
          available for relation enumeration without loading the whole graph.
        */
        attribute requirementId : String = "MN-REQ-04.5";
      }
    }

    // ----- Hard caps -----

    requirement def MN_REQ_05_HardCaps {
      doc /*
        Group: bounded resource use under misuse.
      */
      attribute requirementId : String = "MN-REQ-05";

      requirement def MN_REQ_05_1_StoreResourceCaps {
        doc /*
          SHALL enforce hard caps on rows, law rows, relations, tags, fields,
          and value/line/batch bytes so the store cannot grow unbounded.
        */
        attribute requirementId : String = "MN-REQ-05.1";
      }

      requirement def MN_REQ_05_2_QueryFanoutCaps {
        doc /*
          SHALL enforce hard caps on warm/walk depth and fanout so token cost
          stays bounded under misuse.
        */
        attribute requirementId : String = "MN-REQ-05.2";
      }
    }

    // ----- Serve boundary -----

    requirement def MN_REQ_06_BoundaryServe {
      doc /*
        Group: shared local serve process for concurrent CLI and MCP clients.
        Framing today is often length-prefixed JSON {args, stdin}.
      */
      attribute requirementId : String = "MN-REQ-06";

      requirement def MN_REQ_06_1_SharedSessionRegistry {
        doc /*
          SHALL hold a shared session registry in a production serve process
          usable by concurrent CLI and MCP clients.
        */
        attribute requirementId : String = "MN-REQ-06.1";
      }

      requirement def MN_REQ_06_2_LocalServeEndpoint {
        doc /*
          SHALL expose that serve process over a local network endpoint for
          in-pipeline clients.
        */
        attribute requirementId : String = "MN-REQ-06.2";
      }
    }

    // ----- MCP agent boundary -----

    requirement def MN_REQ_07_McpAgentBoundary {
      doc /*
        Group: generic MCP tool surface for MemNet; no domain-product tools.
      */
      attribute requirementId : String = "MN-REQ-07";

      requirement def MN_REQ_07_1_GenericToolSurface {
        doc /*
          SHALL expose generic MCP tools for serve probe, session
          open/current/load/save, query warm and walk, add, update, read
          get/list, and housekeep stats.
        */
        attribute requirementId : String = "MN-REQ-07.1";
      }

      requirement def MN_REQ_07_2_StructuredToolEnvelope {
        doc /*
          SHALL return each MCP tool result in a structured envelope carrying
          exit status, stdout payload, and stderr/error lines.
        */
        attribute requirementId : String = "MN-REQ-07.2";
      }

      requirement def MN_REQ_07_3_NoDomainProductTools {
        doc /*
          Domain-product tools SHALL NOT be embedded in the generic MemNet MCP
          boundary.
        */
        attribute requirementId : String = "MN-REQ-07.3";
      }

      requirement def MN_REQ_07_4_McpLawSeedOnOpen {
        doc /*
          MCP session_open SHALL auto-seed engine-law rows when they are
          missing from the session.
        */
        attribute requirementId : String = "MN-REQ-07.4";
      }
    }

    // ----- Agent I/O grammar (stdio + MCP) -----

    requirement def MN_REQ_08_AgentIoGrammar {
      doc /*
        Group: LLM-friendly grammar on agent-facing I/O. MemNet agent I/O
        (stdio warm/emit; MCP tool args/results that carry memory language)
        is produced and consumed by an LLM, so presentation SHALL follow
        prompt rules. Grammar is the language; not forever tied to one
        concrete spelling (e.g. @TAG pipe).
      */
      attribute requirementId : String = "MN-REQ-08";

      requirement def MN_REQ_08_1_LlmFriendlyStdio {
        doc /*
          SHALL present an LLM-friendly grammar on CLI/stdio agent I/O:
          low-noise, learnable, and accurate when presenting facts.
        */
        attribute requirementId : String = "MN-REQ-08.1";
      }

      requirement def MN_REQ_08_2_LlmFriendlyMcp {
        doc /*
          SHALL present an LLM-friendly grammar on MCP tool payloads that
          agents read or write.
        */
        attribute requirementId : String = "MN-REQ-08.2";
      }

      requirement def MN_REQ_08_3_NoHostilePositionalDump {
        doc /*
          Agent-facing I/O SHALL NOT rely on hostile positional dumps that
          burn tokens or invite routine field-count and escape errors,
          contradicting MN-REQ-00 token economy and factual accuracy.
        */
        attribute requirementId : String = "MN-REQ-08.3";
      }

      requirement def MN_REQ_08_4_BoundaryFriendlyIfInternalDiffers {
        doc /*
          Store-internal representation MAY differ from the agent grammar only
          if every agent boundary still presents the friendly surface.
        */
        attribute requirementId : String = "MN-REQ-08.4";
      }

      requirement def MN_REQ_08_5_IoActorIsLlm {
        doc /*
          Agent-facing MemNet I/O SHALL be designed as produced and consumed
          by an LLM (not primarily by hand-written UI forms).
        */
        attribute requirementId : String = "MN-REQ-08.5";
      }

      requirement def MN_REQ_08_6_FollowPromptRules {
        doc /*
          Agent-facing I/O grammar and presentation SHALL follow prompt rules:
          low-noise; accurate, precise, consistent, and coherent fact
          presentation; template-copyable shapes; write approximately equals
          display. Named constraint family -- examples include WDC and
          novel-cut prompt-rule doctrines; not a novel-writer product
          dependency.
        */
        attribute requirementId : String = "MN-REQ-08.6";
      }

      requirement def MN_REQ_08_7_WriteApproxDisplay {
        doc /*
          Agent-facing emit shapes SHALL be such that what the LLM writes is
          substantially what it (and humans) read back -- write approximately
          equals display -- so prompts need not teach a second dialect.
        */
        attribute requirementId : String = "MN-REQ-08.7";
      }

      requirement def MN_REQ_08_8_TemplateCopyableShapes {
        doc /*
          Agent-facing records SHALL use template-copyable shapes the LLM can
          imitate from few examples without inventing column order or escape
          tricks.
        */
        attribute requirementId : String = "MN-REQ-08.8";
      }
    }

    // ----- Human inspection (canonical parser) -----

    requirement def MN_REQ_09_HumanInspect {
      doc /*
        Group: humans and tools recover structure from the grammar via one
        canonical parser (grammar = language; parser = structure recovery).
      */
      attribute requirementId : String = "MN-REQ-09";

      requirement def MN_REQ_09_1_CanonicalParserSsot {
        doc /*
          SHALL provide a single canonical parser (one SSOT parse path) that
          recovers NODE and EDGE structure (kind, id, fields, endpoints)
          from the agent-facing grammar, including lawful escape rules.
        */
        attribute requirementId : String = "MN-REQ-09.1";
      }

      requirement def MN_REQ_09_2_RejectInvalidWire {
        doc /*
          The canonical parser SHALL reject invalid wire rather than silently
          mis-split fields.
        */
        attribute requirementId : String = "MN-REQ-09.2";
      }

      requirement def MN_REQ_09_3_ParseFaithfulInspect {
        doc /*
          Humans and tools SHALL be able to inspect what MemNet knows via a
          parse-faithful render or read path that uses the canonical parser.
        */
        attribute requirementId : String = "MN-REQ-09.3";
      }

      requirement def MN_REQ_09_4_NoAdHocConsumerSplits {
        doc /*
          Ad-hoc consumer splits (e.g. naive delimiter split) SHALL NOT be the
          supported inspection or ingest path.
        */
        attribute requirementId : String = "MN-REQ-09.4";
      }
    }

    // ----- LLM properties (assumptions) and MemNet limitations -----

    requirement def MN_REQ_10_LlmPropertiesAndLimits {
      doc /*
        Group: assumed properties of the LLM agents MemNet serves, and the
        MemNet limitations that follow. Attribute values document assumed
        properties (true = property is assumed to hold for design). Nested
        leaves are atomic SHALLs/SHOULDs MemNet must respect or compensate for.
        These underpin MN-REQ-00 token economy and factual accuracy.
      */
      attribute requirementId : String = "MN-REQ-10";

      // Assumed LLM properties (design assumptions -- not product SHALLs)
      attribute unreliableCrossTurnMemory : Boolean = true;
      attribute finiteContextWindow : Boolean = true;
      attribute costlyTokensAndToolRoundTrips : Boolean = true;
      attribute inventsIdsWithoutGroundTruth : Boolean = true;
      attribute weakAtBrittlePositionalFormalism : Boolean = true;
      attribute strongAtEnglishAndLowNoiseTemplates : Boolean = true;

      requirement def MN_REQ_10_1_NoChatAsDurableStore {
        doc /*
          SHALL NOT treat chat context as the durable store of pipeline facts
          (LLMs have unreliable cross-turn working memory).
        */
        attribute requirementId : String = "MN-REQ-10.1";
      }

      requirement def MN_REQ_10_2_WarmMustFitContext {
        doc /*
          Re-injected warm slices SHALL be sized to fit a finite context
          window and token budget.
        */
        attribute requirementId : String = "MN-REQ-10.2";
      }

      requirement def MN_REQ_10_3_MinimiseTokenRoundTrips {
        doc /*
          Agent-facing I/O SHALL minimise unnecessary token burn and tool
          round-trips when re-presenting the same facts.
        */
        attribute requirementId : String = "MN-REQ-10.3";
      }

      requirement def MN_REQ_10_4_ExternalGroundTruthRequired {
        doc /*
          Facts that must stay accurate SHALL be grounded in MemNet (or via
          MemNet from search), not invented ids or claims in chat alone.
        */
        attribute requirementId : String = "MN-REQ-10.4";
      }

      requirement def MN_REQ_10_5_GrammarMustBeLlmLearnable {
        doc /*
          Agent-facing grammar SHALL be LLM-learnable: low noise, not a brittle
          positional or escape-heavy formalism that invites routine errors.
        */
        attribute requirementId : String = "MN-REQ-10.5";
      }

      requirement def MN_REQ_10_6_PreferTemplateFriendlyPins {
        doc /*
          Agent-facing presentation SHOULD favour English or structured
          low-noise pins with clear templates where the LLM is strong.
        */
        attribute requirementId : String = "MN-REQ-10.6";
      }

      requirement def MN_REQ_10_7_HumanVerifyViaParser {
        doc /*
          Humans SHALL be able to verify what MemNet knows via the canonical
          parser path, compensating for LLM invention without ground truth.
        */
        attribute requirementId : String = "MN-REQ-10.7";
      }
    }
  }

  // --- Requirement usages + #derivation (SysML v2 deriveReqt) ---
  // Ends must be requirement *usages*; defs stay nested for structure.

  requirement missionReq : MN_REQ_00_MissionBridge;

  requirement sessionLifecycleReq
    : MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle;
  requirement namedSessionsReq
    : MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_1_NamedSessions;
  requirement sessionLifecycleOpsReq
    : MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_2_SessionLifecycleOps;
  requirement sessionTtlAndCapsReq
    : MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_3_SessionTtlAndCaps;

  requirement memoryNetGraphReq
    : MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph;
  requirement exactlyNodeAndEdgeReq
    : MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_1_ExactlyNodeAndEdge;
  requirement nodesHoldAtomisedFactsReq
    : MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_2_NodesHoldAtomisedFacts;
  requirement edgesAreFirstClassReq
    : MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_3_EdgesAreFirstClass;
  requirement queryOverNodeEdgeGraphReq
    : MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_4_QueryOverNodeEdgeGraph;
  requirement grammarExpressesNodeAndEdgeReq
    : MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_5_GrammarExpressesNodeAndEdge;
  requirement parserRecoversNodeAndEdgeReq
    : MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_6_ParserRecoversNodeAndEdge;
  requirement schemaValidatedIngestReq
    : MN_REQ_00_MissionBridge::MN_REQ_02_MemoryNetGraph::MN_REQ_02_7_SchemaValidatedIngest;

  requirement strictMutateReq
    : MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate;
  requirement addFailsIfExistsReq
    : MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_1_AddFailsIfExists;
  requirement updateFailsIfAbsentReq
    : MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_2_UpdateFailsIfAbsent;
  requirement noSilentUpsertReq
    : MN_REQ_00_MissionBridge::MN_REQ_03_StrictMutate::MN_REQ_03_3_NoSilentUpsert;

  requirement sliceEconomyReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy;
  requirement anchoredWarmSliceReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_1_AnchoredWarmSlice;
  requirement recycleHiddenFromWarmReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_2_RecycleHiddenFromWarm;
  requirement warmDepthAndRowCapsReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_3_WarmDepthAndRowCaps;
  requirement engineLawPrependReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_4_EngineLawPrepend;
  requirement anchoredWalkReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_5_AnchoredWalk;

  requirement hardCapsReq
    : MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps;
  requirement storeResourceCapsReq
    : MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_1_StoreResourceCaps;
  requirement queryFanoutCapsReq
    : MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_2_QueryFanoutCaps;

  requirement boundaryServeReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_BoundaryServe;
  requirement sharedSessionRegistryReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_BoundaryServe::MN_REQ_06_1_SharedSessionRegistry;
  requirement localServeEndpointReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_BoundaryServe::MN_REQ_06_2_LocalServeEndpoint;

  requirement mcpAgentBoundaryReq
    : MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary;
  requirement genericToolSurfaceReq
    : MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_1_GenericToolSurface;
  requirement structuredToolEnvelopeReq
    : MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_2_StructuredToolEnvelope;
  requirement noDomainProductToolsReq
    : MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_3_NoDomainProductTools;
  requirement mcpLawSeedOnOpenReq
    : MN_REQ_00_MissionBridge::MN_REQ_07_McpAgentBoundary::MN_REQ_07_4_McpLawSeedOnOpen;

  requirement agentIoGrammarReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar;
  requirement llmFriendlyStdioReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_1_LlmFriendlyStdio;
  requirement llmFriendlyMcpReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_2_LlmFriendlyMcp;
  requirement noHostilePositionalDumpReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_3_NoHostilePositionalDump;
  requirement boundaryFriendlyIfInternalDiffersReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_4_BoundaryFriendlyIfInternalDiffers;
  requirement ioActorIsLlmReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_5_IoActorIsLlm;
  requirement followPromptRulesReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_6_FollowPromptRules;
  requirement writeApproxDisplayReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_7_WriteApproxDisplay;
  requirement templateCopyableShapesReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_8_TemplateCopyableShapes;

  requirement humanInspectReq
    : MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect;
  requirement canonicalParserSsotReq
    : MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_1_CanonicalParserSsot;
  requirement rejectInvalidWireReq
    : MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_2_RejectInvalidWire;
  requirement parseFaithfulInspectReq
    : MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_3_ParseFaithfulInspect;
  requirement noAdHocConsumerSplitsReq
    : MN_REQ_00_MissionBridge::MN_REQ_09_HumanInspect::MN_REQ_09_4_NoAdHocConsumerSplits;

  requirement llmPropertiesAndLimitsReq
    : MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits;
  requirement noChatAsDurableStoreReq
    : MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_1_NoChatAsDurableStore;
  requirement warmMustFitContextReq
    : MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_2_WarmMustFitContext;
  requirement minimiseTokenRoundTripsReq
    : MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_3_MinimiseTokenRoundTrips;
  requirement externalGroundTruthRequiredReq
    : MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_4_ExternalGroundTruthRequired;
  requirement grammarMustBeLlmLearnableReq
    : MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_5_GrammarMustBeLlmLearnable;
  requirement preferTemplateFriendlyPinsReq
    : MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_6_PreferTemplateFriendlyPins;
  requirement humanVerifyViaParserReq
    : MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_7_HumanVerifyViaParser;

  // Groups derive from mission (MN-REQ-00)
  #derivation connection deriveGroupsFromMission {
    end #original ::> missionReq;
    end #derive ::> sessionLifecycleReq;
    end #derive ::> memoryNetGraphReq;
    end #derive ::> strictMutateReq;
    end #derive ::> sliceEconomyReq;
    end #derive ::> hardCapsReq;
    end #derive ::> boundaryServeReq;
    end #derive ::> mcpAgentBoundaryReq;
    end #derive ::> agentIoGrammarReq;
    end #derive ::> humanInspectReq;
    end #derive ::> llmPropertiesAndLimitsReq;
  }

  // Leaves derive from their group
  #derivation connection deriveSessionLeaves {
    end #original ::> sessionLifecycleReq;
    end #derive ::> namedSessionsReq;
    end #derive ::> sessionLifecycleOpsReq;
    end #derive ::> sessionTtlAndCapsReq;
  }

  #derivation connection deriveMemoryNetGraphLeaves {
    end #original ::> memoryNetGraphReq;
    end #derive ::> exactlyNodeAndEdgeReq;
    end #derive ::> nodesHoldAtomisedFactsReq;
    end #derive ::> edgesAreFirstClassReq;
    end #derive ::> queryOverNodeEdgeGraphReq;
    end #derive ::> grammarExpressesNodeAndEdgeReq;
    end #derive ::> parserRecoversNodeAndEdgeReq;
    end #derive ::> schemaValidatedIngestReq;
  }

  #derivation connection deriveStrictMutateLeaves {
    end #original ::> strictMutateReq;
    end #derive ::> addFailsIfExistsReq;
    end #derive ::> updateFailsIfAbsentReq;
    end #derive ::> noSilentUpsertReq;
  }

  #derivation connection deriveSliceEconomyLeaves {
    end #original ::> sliceEconomyReq;
    end #derive ::> anchoredWarmSliceReq;
    end #derive ::> recycleHiddenFromWarmReq;
    end #derive ::> warmDepthAndRowCapsReq;
    end #derive ::> engineLawPrependReq;
    end #derive ::> anchoredWalkReq;
  }

  #derivation connection deriveHardCapsLeaves {
    end #original ::> hardCapsReq;
    end #derive ::> storeResourceCapsReq;
    end #derive ::> queryFanoutCapsReq;
  }

  #derivation connection deriveBoundaryServeLeaves {
    end #original ::> boundaryServeReq;
    end #derive ::> sharedSessionRegistryReq;
    end #derive ::> localServeEndpointReq;
  }

  #derivation connection deriveMcpLeaves {
    end #original ::> mcpAgentBoundaryReq;
    end #derive ::> genericToolSurfaceReq;
    end #derive ::> structuredToolEnvelopeReq;
    end #derive ::> noDomainProductToolsReq;
    end #derive ::> mcpLawSeedOnOpenReq;
  }

  #derivation connection deriveAgentIoLeaves {
    end #original ::> agentIoGrammarReq;
    end #derive ::> llmFriendlyStdioReq;
    end #derive ::> llmFriendlyMcpReq;
    end #derive ::> noHostilePositionalDumpReq;
    end #derive ::> boundaryFriendlyIfInternalDiffersReq;
    end #derive ::> ioActorIsLlmReq;
    end #derive ::> followPromptRulesReq;
    end #derive ::> writeApproxDisplayReq;
    end #derive ::> templateCopyableShapesReq;
  }

  #derivation connection deriveHumanInspectLeaves {
    end #original ::> humanInspectReq;
    end #derive ::> canonicalParserSsotReq;
    end #derive ::> rejectInvalidWireReq;
    end #derive ::> parseFaithfulInspectReq;
    end #derive ::> noAdHocConsumerSplitsReq;
  }

  #derivation connection deriveLlmLimitLeaves {
    end #original ::> llmPropertiesAndLimitsReq;
    end #derive ::> noChatAsDurableStoreReq;
    end #derive ::> warmMustFitContextReq;
    end #derive ::> minimiseTokenRoundTripsReq;
    end #derive ::> externalGroundTruthRequiredReq;
    end #derive ::> grammarMustBeLlmLearnableReq;
    end #derive ::> preferTemplateFriendlyPinsReq;
    end #derive ::> humanVerifyViaParserReq;
  }

  // Cross-derive: LLM limitations -> AgentIO / inspect / session / slice
  #derivation connection deriveAgentIoFromLlmLimits {
    end #original ::> grammarMustBeLlmLearnableReq;
    end #original ::> preferTemplateFriendlyPinsReq;
    end #original ::> minimiseTokenRoundTripsReq;
    end #derive ::> followPromptRulesReq;
    end #derive ::> ioActorIsLlmReq;
    end #derive ::> writeApproxDisplayReq;
    end #derive ::> templateCopyableShapesReq;
    end #derive ::> noHostilePositionalDumpReq;
  }

  #derivation connection derivePromptSurfaceFromPromptRules {
    end #original ::> followPromptRulesReq;
    end #derive ::> llmFriendlyStdioReq;
    end #derive ::> llmFriendlyMcpReq;
    end #derive ::> writeApproxDisplayReq;
    end #derive ::> templateCopyableShapesReq;
  }

  #derivation connection deriveSessionFromNoChatStore {
    end #original ::> noChatAsDurableStoreReq;
    end #derive ::> sessionLifecycleReq;
  }

  #derivation connection deriveSliceFromContextLimit {
    end #original ::> warmMustFitContextReq;
    end #derive ::> sliceEconomyReq;
    end #derive ::> hardCapsReq;
  }

  #derivation connection deriveFactsFromGroundTruth {
    end #original ::> externalGroundTruthRequiredReq;
    end #derive ::> memoryNetGraphReq;
    end #derive ::> strictMutateReq;
  }

  #derivation connection deriveInspectFromHumanVerify {
    end #original ::> humanVerifyViaParserReq;
    end #derive ::> humanInspectReq;
    end #derive ::> parserRecoversNodeAndEdgeReq;
  }

  #derivation connection deriveIoFromNodeEdgeGrammar {
    end #original ::> grammarExpressesNodeAndEdgeReq;
    end #derive ::> agentIoGrammarReq;
    end #derive ::> followPromptRulesReq;
  }

  #derivation connection deriveSliceFromNodeEdgeQuery {
    end #original ::> queryOverNodeEdgeGraphReq;
    end #derive ::> sliceEconomyReq;
  }
}
