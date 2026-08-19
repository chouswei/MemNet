/*
  MemNet requirements -- nested + atomic baseline (2026-07).

  ID scheme:
    MN-REQ-00          mission root (sole parent)
    MN-REQ-NN          group requirement (organisational; short framing doc)
    MN-REQ-NN.M        atomic leaf (one SHALL/SHOULD idea)
    MN-REQ-10          LLM assumed properties + limitation leaves
    MN-REQ-11          Snapshot / interoperability (map of pins)
    MN-REQ-12          Multitask Mode (parent/worker; shared session as-is)
    MN-REQ-13          0.5 Recall/Commit (thin; math skeleton; no engine cut)

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
  system, programme, software, firmware, hardware, and documentation
  development; save time and tokens; high factual accuracy; LLM-friendly
  grammar on stdio/MCP; canonical parser for human inspection. GQL elements:
  node (vertex), edge (relationship), property.

  Current realisation notes (not eternal identity):
    Target agent wire is openCypher-shaped GQL (ADR-001); Write = display
    redefined as bounded shaped pin_map subgraph wrapping GQL.
    Layer / Tier A = archived historical only (not product accept; M2
    retired MutateGate accept; MemNetLayer.g4 under docs/grammar/archive/).
    Legacy @TAG pipe may still appear in old session files (import once).
    Store is in-memory Node|Edge property-graph records; process binding
    prefers in-process, then local IPC, TCP as fallback; fixed engine laws
    often LAW01-LAW05. Durable store behind MemNet = client adapters
    (M2.5) plus external cabinet server (not in-wheel; 0.7 Agens claimed;
    Neo4j liveNeo4jClaimed=false). Requirements state behavioural contracts;
    surface spellings may change if the boundary still meets the contract.

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
      LLM for system, programme, software, firmware, hardware, and
      documentation development, with the aims of saving wall-clock time and
      token usage while keeping high accuracy when presenting facts.
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
          SHALL support open, resume, and close for each named session.
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

      requirement def MN_REQ_01_4_SaveSessionSnapshot {
        doc /*
          SHALL persist a named session to a durable snapshot so working-memory
          state can outlive the process (schema, records, relations).
        */
        attribute requirementId : String = "MN-REQ-01.4";
      }

      requirement def MN_REQ_01_5_LoadSessionSnapshot {
        doc /*
          SHALL restore a named session from a durable snapshot into an active
          working-memory session.
        */
        attribute requirementId : String = "MN-REQ-01.5";
      }

      requirement def MN_REQ_01_6_OptionalKeepSessionId {
        doc /*
          On load, SHALL allow the caller to optionally keep the session id
          from the snapshot (keep_id); otherwise assign a new id.
        */
        attribute requirementId : String = "MN-REQ-01.6";
      }

      requirement def MN_REQ_01_7_SessionAsSsotHandle {
        doc /*
          A named session MAY be the SSOT for a mission SOMETHING
          (MissionWorkingSet). When so, an LLM SHALL pass that SOMETHING by
          delivering the session id only (SessionHandoff; module A → B pipe).
          Peers SHALL re-pin_map; chat, MissionDock payloads, and HTTP bodies
          SHALL NOT be treated as SSOT (extends MN-REQ-10.1; Multitask
          MN-REQ-12.1).
        */
        attribute requirementId : String = "MN-REQ-01.7";
      }

      requirement def MN_REQ_01_8_NoGraphDumpHandoff {
        doc /*
          Session handoff SHALL NOT carry a full graph dump (or mission SSOT
          prose blob) as the handoff payload. SessionHandoff carries sessionId
          and caller, plus optional missionId, lease, anchors, and writeScope.
          Chat, MissionDock, and HTTP bodies SHALL NOT carry the graph.
          Mutate still hits CapsPolicy (who / what / bind).
        */
        attribute requirementId : String = "MN-REQ-01.8";
      }
    }

    // ----- Memory net information model: GQL node, edge, property -----

    requirement def MN_REQ_02_MemoryNetGraph {
      doc /*
        Group: the Net of Memory is a GQL property graph whose three elements
        are node (ISO synonym vertex), edge (ISO synonym relationship), and
        property (ADR-001; gql-wire-profile). Labels name kinds; they are not
        a fourth element. MUST NOT invent PORT (or nested graph) as a
        graph-element kind — those facts live as property values. Agent wire
        is openCypher-shaped GQL; primary read is shaped pin_map (not raw
        MATCH/RETURN tables). Layer / Tier A are archived (not product
        accept); @TAG pipe remains import-once only.
      */
      attribute requirementId : String = "MN-REQ-02";

      requirement def MN_REQ_02_1_ExactlyNodeAndEdge {
        doc /*
          SHALL model the Net of Memory as a GQL property graph with three
          elements: node (vertex), edge (relationship), and property. Topology
          is node--edge--node; property values attach to nodes and to edges.
          SHALL NOT add a fourth graph-element kind (PORT nodes, nested graphs,
          prose blobs).
        */
        attribute requirementId : String = "MN-REQ-02.1";
      }

      requirement def MN_REQ_02_2_NodesHoldAtomisedFacts {
        doc /*
          Nodes SHALL hold atomised facts as property values --
          one idea per property -- not free-form prose or merged
          multi-idea blobs.
        */
        attribute requirementId : String = "MN-REQ-02.2";
      }

      requirement def MN_REQ_02_3_EdgesAreFirstClass {
        doc /*
          Edges (relationships) SHALL be first-class links between nodes,
          not buried in node property values or narrative.
        */
        attribute requirementId : String = "MN-REQ-02.3";
      }

      requirement def MN_REQ_02_4_QueryOverNodeEdgeGraph {
        doc /*
          Pin map, walk, bounded MATCH find, and query SHALL operate over the
          node/edge graph (property values included). Primary agent read when an ego/anchor id is
          known is bounded shaped pin_map wrapping GQL (Recall seed = id).
          When unanchored (no id) or pin_map caps dropped a needed row,
          bounded MATCH find (hard LIMIT; shaped subgraph emit) MAY apply
          (Recall seed = MATCH; leftover #73) — still not unbounded raw
          MATCH/RETURN dumps as goldfish. Both seeds are one Recall operator
          (MN-REQ-13).
        */
        attribute requirementId : String = "MN-REQ-02.4";
      }

      requirement def MN_REQ_02_5_GrammarExpressesNodeAndEdge {
        doc /*
          Agent-facing grammar and I/O SHALL express node, edge, and property as
          openCypher-shaped GQL (labels, edge/relationship types, property maps).
          Write = display means shaped subgraph emit matches mutate family.
          Layer / Tier A SHALL NOT be accepted on the product mutate path.
        */
        attribute requirementId : String = "MN-REQ-02.5";
      }

      requirement def MN_REQ_02_6_ParserRecoversNodeAndEdge {
        doc /*
          The canonical parser SHALL recover node, edge, and property structure for
          human inspection.
        */
        attribute requirementId : String = "MN-REQ-02.6";
      }

      requirement def MN_REQ_02_7_SchemaValidatedIngest {
        doc /*
          SHALL validate ingest against the session schema and reject unknown
          or reserved surface kinds. Tags MAY realise node labels; GQL
          elements remain node (vertex), edge (relationship), and property.
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

    // ----- Slice economy (pin map / recycle / walk) -----

    requirement def MN_REQ_04_SliceEconomy {
      doc /*
        Group: bounded live pin map for LLM turns (not the whole net);
        hide recyclable rows; optional relation walk; modelled bounded
        MATCH find when unanchored (MN-REQ-04.6; not shipped). 0.5 names
        this family Recall(q) (MN-REQ-13); pin_map and leftover find are
        the same operator with different seed rules. Engine
        fixed-law rows (often LAW01-LAW05) are a current realisation, not
        the contract identity. Legacy name "warm" = live pin map
        (deprecated alias).
      */
      attribute requirementId : String = "MN-REQ-04";

      requirement def MN_REQ_04_1_AnchoredPinMap {
        doc /*
          SHALL return an anchored live pin map for each turn -- a bounded
          ego/anchor digest of pins -- not the full session or a raw search
          dump.
        */
        attribute requirementId : String = "MN-REQ-04.1";
      }

      requirement def MN_REQ_04_2_RecycleHiddenFromPinMap {
        doc /*
          SHALL hide rows marked for settle or expire recycle from the live
          pin map.
        */
        attribute requirementId : String = "MN-REQ-04.2";
      }

      requirement def MN_REQ_04_3_PinMapDepthAndRowCaps {
        doc /*
          SHALL cap live pin map depth and row count.
        */
        attribute requirementId : String = "MN-REQ-04.3";
      }

      requirement def MN_REQ_04_4_EngineLawPrepend {
        doc /*
          SHALL prepend session engine-law rows to the live pin map when
          those rows are present in the store.
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

      requirement def MN_REQ_04_6_BoundedMatchFind {
        doc /*
          When no ego/anchor id is known, or when pin_map caps dropped a
          needed row, the agent surface SHOULD offer a bounded MATCH find:
          label and/or property/locator predicates with LIMIT required
          (hard); optional max_rows aligned with MN-REQ-04.3; emit the same
          shaped subgraph family as pin_map / mutate (MN-REQ-08.9).
          SHALL NOT: binding-table RETURN as primary emit; missing LIMIT;
          unbounded MATCH; variable-length path as default; teach full
          openCypher (WITH / UNWIND / CALL / subqueries / ORDER BY).
          Distinct from mutate MATCH … SET. Shipped as BoundedMatchFind
          (implemented=true; #73) — seed nodes only, not pin_map k-hop.
        */
        attribute requirementId : String = "MN-REQ-04.6";
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
          SHALL enforce hard caps on pin-map/walk depth and fanout so token
          cost stays bounded under misuse.
        */
        attribute requirementId : String = "MN-REQ-05.2";
      }
    }

    // ----- Process / transport boundary -----

    requirement def MN_REQ_06_ProcessBoundary {
      doc /*
        Group: how clients bind to GraphStore and the session registry.
        Locked preference: in-process primary, local IPC for multi-process
        share, TCP localhost only as migration / fallback (not the core).
      */
      attribute requirementId : String = "MN-REQ-06";

      requirement def MN_REQ_06_1_InProcessPrimary {
        doc /*
          SHALL provide in-process GraphStore and session APIs as the primary
          binding for MCP and library users (lowest latency; no network hop).
        */
        attribute requirementId : String = "MN-REQ-06.1";
      }

      requirement def MN_REQ_06_2_LocalIpcShare {
        doc /*
          SHALL support a local IPC gateway when CLI and MCP must share one
          session registry across processes (prefer named pipe on Windows /
          AF_UNIX on POSIX).
        */
        attribute requirementId : String = "MN-REQ-06.2";
      }

      requirement def MN_REQ_06_3_TcpServeMigration {
        doc /*
          MAY expose TCP localhost length-prefixed serve as a migration or
          multi-process fallback; it SHALL NOT be treated as the conceptual
          core binding.
        */
        attribute requirementId : String = "MN-REQ-06.3";
      }

      requirement def MN_REQ_06_4_DurableStoreBehindMemNet {
        doc /*
          When a durable online GQL store (AgensGraph-class or Neo4j-class)
          is present, MemNet SHALL remain the sole agent-facing shared
          memory. The store SHALL sit behind MemNet (hydrate/flush). LLM ↔
          store direct (Bolt / driver) SHALL NOT be the default teach path.
          M2.5 client hydrate/flush adapter seam IS landed (Fake always;
          optional AgensGraph client with liveCabinetClaimed; optional
          Neo4j client with liveNeo4jClaimed=false until a product live
          claim; one DurableSyncOwner). Live external cabinet SHALL NOT be
          claimed shipped until operator-proven. Neither AgensGraph nor
          Neo4j servers SHALL be vendored in-repo. Two cabinet URLs SHALL
          require an explicit backend pick (MUST NOT silently bind two
          owners). As-is factory footgun: MEMNET_DURABLE_BACKEND is
          consulted only when both URLs are set; otherwise the single URL
          wins. CLI/MCP SHALL NOT expose hydrate/flush tools in this cut
          (proof port = Python adapter from_env).
        */
        attribute requirementId : String = "MN-REQ-06.4";
      }

      requirement def MN_REQ_06_5_ExternalCabinetServer {
        doc /*
          The durable cabinet SHALL be an external database process: not
          packaged in memnet-llm, not installed on the 2 GiB droplet MemNet
          host. Optional extras SHALL ship drivers only (neo4j>=5.14 /
          psycopg). Two possible server kinds: AgensGraph (default product
          cabinet option; 0.7 live claim) and Neo4j (operator Pi server).
          Clients (Pi writer, droplet MCP) SHALL be adapters, not the
          database. Graph id SHALL apply only to addressable working-memory
          records and cabinet MERGE keys (ego, pin anchors, mutate targets,
          reserved ids). SHALL NOT require a SysML `id` on hosts, extras,
          ports, honesty flags, or the cabinet server. Present edge MERGE
          MAY use a relationship id when the engine record has one; that
          SHALL NOT be a law that every relationship needs a user-supplied
          id (Commit may mint NEW). Desk EvidenceCentre / CompanyMemory
          SHALL NOT bind this Bolt; MUST NOT federate over InvestorApi.
          Lab-critical InvenTree ports on the Pi (:80/:443) SHALL NOT be
          disturbed.
        */
        attribute requirementId : String = "MN-REQ-06.5";
      }

      requirement def MN_REQ_06_6_OperatorEvidenceNotLiveClaim {
        doc /*
          Operator soak / Bolt reachability SHALL NOT set liveNeo4jClaimed.
          AgensGraph remains the default product live-cabinet claim (0.7).
          Per-ego live proof SHALL NOT be claimed green while
          company_ego_fixture neighbour/edge ids are global (not namespaced
          per ego); Bolt-client reachability is not isolation. One
          DurableSyncOwner per process; serve/MCP SHALL call
          get_sync_owner() once at start. MUST NOT dual-write in-process
          MCP and TCP serve.
        */
        attribute requirementId : String = "MN-REQ-06.6";
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
          SHALL expose generic MCP tools for engine/status probe, session
          open/current/load/save, live pin map and walk, add, update, read
          get/list, and housekeep stats (in-process by default).
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
        (stdio pin-map emit; MCP tool args/results that carry memory language)
        is produced and consumed by an LLM, so presentation SHALL follow
        prompt rules. One agent dialect teach = openCypher-shaped GQL
        (ADR-001); Write = display = shaped pin_map subgraph both ways.
        Layer / Tier A are archived (not product accept); @TAG pipe remains
        import-once only.
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
          Internal store records MAY differ; legacy pipe import-once is allowed. Pipe
          SHALL NOT appear as a standing agent-facing dialect on pin-map read
          or mutate/write.
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
          presentation; template-copyable shapes; write equals display.
          Named constraint family -- examples include WDC and novel-cut
          prompt-rule doctrines; not a novel-writer product dependency.
        */
        attribute requirementId : String = "MN-REQ-08.6";
      }

      requirement def MN_REQ_08_7_WriteApproxDisplay {
        doc /*
          Agent-facing emit and accept shapes SHALL be the same dialect:
          what the LLM writes is what it (and humans) read back -- Write =
          display -- so prompts need not teach a second grammar.
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

      requirement def MN_REQ_08_9_PinMapEmitSameAsMutate {
        doc /*
          Live pin map emit SHALL be a shaped subgraph in the same GQL /
          property-graph family as accepted mutate input (redefined Write =
          display). SHALL NOT present raw tabular RETURN as primary read, nor
          a second peer dialect on read vs GQL on write.
        */
        attribute requirementId : String = "MN-REQ-08.9";
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

      requirement def MN_REQ_10_2_PinMapMustFitContext {
        doc /*
          Re-injected live pin maps SHALL be sized to fit a finite context
          window.
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

    // ----- Snapshot / interoperability: map of pins -----
    // Distinct from MN-REQ-01.4--01.6 (session file save/load).

    requirement def MN_REQ_11_SnapshotInterop {
      doc /*
        Group: a map of pins -- short accurate anchors and locators into
        SysML v2, codebase, PCBA schematics (Atopile .ato), and agent
        skills/rules, linked as NODE and EDGE so the LLM can navigate without
        swallowing the whole source. Selective projection means pin map, not
        a bulky corpus dump. Not session-file persistence (see MN-REQ-01.4
        through MN-REQ-01.6).
      */
      attribute requirementId : String = "MN-REQ-11";

      requirement def MN_REQ_11_13_MapOfPins {
        doc /*
          Every MN-REQ-11 snapshot or export SHALL be a map of pins: short
          accurate anchors and locators linked as NODE and EDGE, sufficient
          for LLM navigation. SHALL NOT be a complete copy of the source
          artefact or a bulky corpus dump (same spirit as pin-map economy).
        */
        attribute requirementId : String = "MN-REQ-11.13";
      }

      requirement def MN_REQ_11_1_ExportGraphToSysmlV2 {
        doc /*
          SHALL support exporting a pin map of in-memory NODE and EDGE facts
          into a SysML v2 model representation for the in-repo model-based
          workflow (sysml-models). SHALL NOT require dumping the entire
          session graph.
        */
        attribute requirementId : String = "MN-REQ-11.1";
      }

      requirement def MN_REQ_11_2_NodeMapsToSysmlStructure {
        doc /*
          On SysML export, each MemNet NODE included in the pin map SHALL map
          to a SysML v2 structural element analogue (e.g. part, item, or
          attribute usage) -- an isomorphic projection of the pins, not a
          claim that the SysML metamodel defines literal NODE types, and not
          a requirement to export every store row.
        */
        attribute requirementId : String = "MN-REQ-11.2";
      }

      requirement def MN_REQ_11_3_EdgeMapsToSysmlConnection {
        doc /*
          On SysML export, each MemNet EDGE included in the pin map SHALL map
          to a SysML v2 connection or relationship analogue between the
          mapped structural elements -- projection of the pins only, not
          literal EDGE metamodel types.
        */
        attribute requirementId : String = "MN-REQ-11.3";
      }

      requirement def MN_REQ_11_4_DistinctFromSessionSnapshot {
        doc /*
          Pin maps (SysML export, codebase, PCBA schematics via Atopile .ato,
          skills/rules) SHALL be distinct from named-session file save and
          load (MN-REQ-01.4 through MN-REQ-01.6), which persist
          working-memory session state. Session save/load MUST NOT be taken
          as satisfying these projections, and these projections MUST NOT be
          taken as a full-fidelity session backup or corpus dump.
        */
        attribute requirementId : String = "MN-REQ-11.4";
      }

      requirement def MN_REQ_11_5_SysmlRoundTripShould {
        doc /*
          Round-trip of the SysML pin map back into MemNet NODE and EDGE form
          SHOULD be supported where practical. Full-fidelity recovery of
          original SysML sources from the pins SHALL NOT be required; lossy
          cases SHALL be documented.
        */
        attribute requirementId : String = "MN-REQ-11.5";
      }

      requirement def MN_REQ_11_6_SnapshotCodebaseIntoGraph {
        doc /*
          SHALL support ingesting a pin map of a codebase into the Net of
          Memory as NODE and EDGE locators so agents can fetch a pin map, walk, and
          navigate purpose-relevant structure without swallowing the tree.
          SHALL NOT require indexing every file, symbol, or line.
        */
        attribute requirementId : String = "MN-REQ-11.6";
      }

      requirement def MN_REQ_11_7_CodebaseNodesAreModulesSymbols {
        doc /*
          A codebase pin map SHALL represent selected files or modules and
          symbols (functions, variables, types, and similar) as NODE pins --
          short anchors, not free prose blobs or an exhaustive inventory.
        */
        attribute requirementId : String = "MN-REQ-11.7";
      }

      requirement def MN_REQ_11_8_CodebaseEdgesAreRelations {
        doc /*
          A codebase pin map SHALL represent selected relations among those
          pins (defines, calls, includes, owns, uses, and similar) as
          first-class EDGEs -- not every possible edge in the corpus.
        */
        attribute requirementId : String = "MN-REQ-11.8";
      }

      requirement def MN_REQ_11_9_SnapshotAtoIntoGraph {
        doc /*
          SHALL support ingesting a pin map of PCBA schematics from Atopile
          (.ato projects or files) into the Net of Memory as NODE and EDGE
          locators so agents can fetch a pin map, walk, and navigate purpose-relevant
          connectivity without swallowing the drawing. Atopile .ato is the
          PCBA schematic source for this pin map -- not a separate ingest
          pipeline. SHALL NOT require a complete schematic dump or a copy of
          every .ato artefact.
        */
        attribute requirementId : String = "MN-REQ-11.9";
      }

      requirement def MN_REQ_11_10_SnapshotSkillsAndRulesIntoGraph {
        doc /*
          SHALL support ingesting a pin map of agent skills and rules
          (Cursor/agent SKILL.md packs, .mdc rules, and similar) into the Net
          of Memory as NODE and EDGE locators. SHALL NOT require copying
          every skill body or rule file verbatim into the graph.
        */
        attribute requirementId : String = "MN-REQ-11.10";
      }

      requirement def MN_REQ_11_11_SkillsAndRulesAreNodes {
        doc /*
          A skills/rules pin map SHALL represent selected skill packs and
          rules as NODE pins -- short anchors, not free prose blobs or an
          exhaustive catalogue of every installed pack.
        */
        attribute requirementId : String = "MN-REQ-11.11";
      }

      requirement def MN_REQ_11_12_SkillsRulesEdgesAreRelations {
        doc /*
          A skills/rules pin map SHALL represent selected relations among
          those pins (paired_with, triggers, governs, and similar) as
          first-class EDGEs.
        */
        attribute requirementId : String = "MN-REQ-11.12";
      }

      requirement def MN_REQ_11_14_PcbaAtoNodesAreNetsComponentsPins {
        doc /*
          A PCBA schematic (Atopile .ato) pin map SHALL represent selected
          nets, components, and pins as NODE pins -- short anchors into the
          schematic, not free prose blobs or an exhaustive inventory of every
          symbol and wire.
        */
        attribute requirementId : String = "MN-REQ-11.14";
      }

      requirement def MN_REQ_11_15_PcbaAtoEdgesAreConnectivity {
        doc /*
          A PCBA schematic (Atopile .ato) pin map SHALL represent selected
          connectivity among those pins (pin-to-net, component-owns-pin, and
          similar) as first-class EDGEs -- not every possible connection in
          the schematic.
        */
        attribute requirementId : String = "MN-REQ-11.15";
      }

      requirement def MN_REQ_11_16_PinIngestDeterministicIds {
        doc /*
          Pin-map ingest (SysML, codebase, PCBA/.ato, skills) SHALL assign
          MemNet ids from deterministic locator keys derived from the source,
          or an engine key with required locator fields (loc, path, refdes,
          net, pin, qname, skill_id, and similar). The live pin map SHALL emit those
          ground ids and locator fields for copy. Pin-map ingest SHALL NOT
          accept client NEW for source elements. LLM NEW remains only for
          goldfish-authored memory facts that do not yet exist in the net
          (annotations), not for re-creating schematic or source pins.
        */
        attribute requirementId : String = "MN-REQ-11.16";
      }
    }

    // ----- Multitask Mode (as-is 0.4.x agent operating model) -----
    // Enforceable parent/worker doctrine over a shared session.
    // CapsPolicy ACL is shipped when enabled per session. Neighbourhood
    // reserve is shipped. Path-B PinMapIngest_* domains are shipped
    // (Sysml/Codebase/PcbaAto/SkillsRules). Full private/shared/open +
    // session_token modes remain design-only. Export (#66) not claimed.

    requirement def MN_REQ_12_MultitaskMode {
      doc /*
        Group: when Multitask Mode (or Task sub-agents) is active, MemNet
        SHALL be operated as a shared mission store with a parent coordinator
        and scoped workers. Chat is never mission SSOT. As-is product
        constraints for 0.4.x include the shipped, per-session CapsPolicy ACL
        cut; RSV and Path-B PinMapIngest_* domains shipped; full
        private/shared/open + session_token modes deferred.
      */
      attribute requirementId : String = "MN-REQ-12";

      requirement def MN_REQ_12_1_SharedSessionMissionSsot {
        doc /*
          Under Multitask, SHALL use one shared named MemNet session id as the
          mission source of truth for ids, paths, and task state (session as
          SSOT handle for the MissionWorkingSet). Handoff SHALL be by session
          id (SessionHandoff); peers re-pin_map. Chat, tool transcripts, and
          sub-agent prose SHALL NOT be treated as durable mission SSOT
          (extends MN-REQ-10.1 / MN-REQ-01.7 / MN-REQ-01.8).
        */
        attribute requirementId : String = "MN-REQ-12.1";
      }

      requirement def MN_REQ_12_2_SharedStoreTransport {
        doc /*
          Under Multitask, parent and workers SHALL bind to the same shared
          GraphStore/session registry via TCP serve, streamable-http MCP, or
          local IPC when available. Default isolated in-process MCP (one
          graph per host process) SHALL NOT be used for shared Multitask
          missions. Single-agent goldfish MAY still use in-process (MN-REQ-06.1).
        */
        attribute requirementId : String = "MN-REQ-12.2";
      }

      requirement def MN_REQ_12_3_ParentOwnsTaskLifecycle {
        doc /*
          The parent coordinator SHALL mint and own house task and user-
          constraint lifecycle rows (TSK_* / USR_*): create, status=active,
          status=settled, and optional led_to_success edges. Workers SHALL NOT
          settle parent-owned TSK_* / USR_* unless the parent explicitly
          delegated that settle.
        */
        attribute requirementId : String = "MN-REQ-12.3";
      }

      requirement def MN_REQ_12_4_WorkerPinMapAndScopedWrite {
        doc /*
          Each worker turn SHALL begin with a live pin map on the shared
          session, copy assigned ids from that pin map, and mutate only under
          the parent-assigned subgraph (anchors and relation scope). Workers
          SHALL NOT invent ids the parent already minted, and SHALL NOT open a
          different session id unless the parent assigned a separate mission.
        */
        attribute requirementId : String = "MN-REQ-12.4";
      }

      requirement def MN_REQ_12_5_PreferOneWorkerOrDisjoint {
        doc /*
          Multitask missions SHOULD prefer one worker per coherent workstream.
          Asynchronous parallel workers SHALL use disjoint anchor subtrees on
          one shared session OR separate parent-assigned session ids.
          Two writers SHALL NOT mutate the same anchor slice without explicit
          serialisation (MUST NOT dual-write in parallel). CapsPolicy
          hard-rejects mutate outside WorkerWriteScope when session ACL is
          enabled; NeighbourhoodReserve (MN-REQ-12.13) leases ego scopes so
          overlapping writers fail with reserve_conflict rather than
          last-write-wins.
        */
        attribute requirementId : String = "MN-REQ-12.5";
      }

      requirement def MN_REQ_12_6_ParentEndTurnNoPoll {
        doc /*
          After AsyncTaskDispatch (spawning background workers via
          EvDelegateWorker), the parent SHALL EvEndCoordinatorTurn
          (Multitask gate). The parent SHALL NOT poll or await worker
          completion in the same turn, and SHALL NOT redo worker investigation
          from chat memory. On the next coordinator turn the parent SHALL
          pin_map first and act from the refreshed shared-session slice
          (or SessionImportReceive when sessions were separate).
        */
        attribute requirementId : String = "MN-REQ-12.6";
      }

      requirement def MN_REQ_12_7_NoAssumeAclReserveIngest {
        doc /*
          As-is NOW: the CapsPolicy ACL cut IS shipped (engineAclShipped=true)
          when session ACL is enabled. Neighbourhood reserve (RSV, llm_id +
          TTL) IS shipped as NeighbourhoodReserve / MN-REQ-12.13. Path-B
          PinMapIngest_* domains ARE shipped (Sysml / Codebase / PcbaAto /
          SkillsRules; MN-REQ-11.6–11.16; issues #31 / #64; CLI/MCP ingest
          sysml|codebase|pcba|skills). Agents MUST NOT assume the full
          private/shared/open + session_token modes until those ship. Agents
          MUST NOT assume pin-map export / round-trip (MN-REQ-11.1–11.5 / #66)
          from ingest alone.
        */
        attribute requirementId : String = "MN-REQ-12.7";
      }

      requirement def MN_REQ_12_8_AppliesToRelevantTasks {
        doc /*
          Multitask Mode (MN-REQ-12.1 through 12.7) SHALL apply when mission
          work is multi-step, coordinator-delegated to workers, or
          parallelisable across disjoint workers. Trivial one-shot
          single-agent turns SHALL use the ordinary goldfish loop without
          Multitask shared-store or parent/worker obligations.
        */
        attribute requirementId : String = "MN-REQ-12.8";
      }

      requirement def MN_REQ_12_13_NeighbourhoodReserve {
        doc /*
          SHALL provide neighbourhood reserve (RSV) so parallel agents on one
          shared session_id can hold disjoint pin-map ego scopes: required
          llm_id holder, required ttl_s lease, scope = anchor + depth matching
          pin_map. Mutate that touches reserved ids SHALL require matching
          llm_id (else reserved / no_llm_id). Overlap with another holder
          SHALL fail with reserve_conflict. Expired leases SHALL auto-release.
          Pin map MAY surface RSV present lines. Lifecycle via reserve /
          extend / release (MCP/CLI) — not + RSV graph mutate.
        */
        attribute requirementId : String = "MN-REQ-12.13";
      }

      requirement def MN_REQ_12_9_LeadOwnsSessionImport {
        doc /*
          When a team lead imports a member's working memory
          (SessionImportReceive), the lead / parent SHALL own the import into
          the mission session. Path A (prefer shared mission sessionId):
          import is re-pin_map only — no WorkingMemorySlice, no ImportGuard,
          no ImportAbsorb. Path B (separate sessions): lead SHALL
          ImportAbsorb a bounded WorkingMemorySlice under owner-gated
          id_policy keep | reject | remint:
            keep = MERGE-by-id upsert into lead SSOT (not append / not a
              second copy);
            reject = id_conflict, no lead mutate;
            remint = mint NEW ids for conflicts; lead old rows stay; edges
              retarget.
          Edges after nodes; LAW/vocab SHALL NOT import; lead settles parent
          TSK_*. Chat/transcripts SHALL NOT be the payload (MN-REQ-12.10).
          Members SHALL NOT settle parent-owned TSK_* unless delegated.
          Product verb = import (SessionImport* only — no SessionMerge*).
          Distinct from micro merge=true (in-session re-id).
        */
        attribute requirementId : String = "MN-REQ-12.9";
      }

      requirement def MN_REQ_12_10_NoChatOrWholeStoreImport {
        doc /*
          Session import (SessionImportReceive) SHALL NOT use chat or tool
          transcripts as the import payload (EvImportFromChat forbidden).
          Engine SHALL require anchors on WorkingMemorySliceExport, enforce
          slice budget, and SHALL NOT import a whole-store dump. Dual-writer
          on the target slice during import SHALL NOT be assumed safe (0.4.x
          last-write-wins; MN-REQ-12.7).
        */
        attribute requirementId : String = "MN-REQ-12.10";
      }

      requirement def MN_REQ_12_11_CheapLlmImportGuardSoft {
        doc /*
          OPTIONAL soft policy (never mandatory LLM): Path B
          WorkingMemorySlice import SHOULD pass ImportGuard soft review
          before ImportAbsorb (allow / trim / reject + short reason; trim
          subtractive via keep_ids) when the host enables the guard.
          Nest under SessionImportReceive / ImportGuard (PinMapIngest-style):
          ImportGuardHook = host plug-in (set_import_guard / --no-guard /
          enable_guard; GuardPassthrough when skipped — skipping is valid);
          CheapLlmImportGuard = optional default adapter in memnet-llm (off
          unless MEMNET_IMPORT_GUARD_API_KEY set; does not vendor a model;
          shipped #63). Hook shipped ≠ cheap LLM alone. Path A SHALL
          re-pin_map without ImportGuard. LLM MAY: choose anchors, trim
          junk, advise keep vs remint. Soft guard SHALL NOT replace engine
          hard gates (schema, ACL, slice budget, anchors, LAW exclude,
          id_policy). Guard chat SHALL NOT be SSOT — record
          ImportGuardDecision as structured atoms; lead session remains
          SSOT after import. costTier is a cost/latency class, not a
          vendor id. Host MAY skip/disable (GuardPassthrough / --no-guard).
          Satisfied by CheapLlmImportGuard part (not the hook alone).
        */
        attribute requirementId : String = "MN-REQ-12.11";
      }

      requirement def MN_REQ_12_12_HostDrivenAsyncParallel {
        doc /*
          Asynchronous parallel Multitask: parent opens/loads one mission
          session (or explicitly separate sessions), mints TSK_*, assigns
          WorkerWriteScope, emits SessionHandoff, spawns workers via
          AsyncTaskDispatch, then MUST end the turn (EvEndCoordinatorTurn).
          Worker completion SHALL be host-driven EvWorkerReturn / async
          revival on a later coordinator turn — NOT a blocking await on the
          spawn turn. Parallel waves SHALL obey MN-REQ-12.5 (disjoint
          anchors or separate sessions; MUST NOT overlapping dual-write).
          When session ACL is enabled, the shipped CapsPolicy ACL
          hard-rejects mutate outside WorkerWriteScope. RSV lease
          (MN-REQ-12.13) sits under Commit — not a third operator.
        */
        attribute requirementId : String = "MN-REQ-12.12";
      }
    }

    // ----- 0.5 Recall / Commit (math skeleton; engine cut not this PR) -----

    requirement def MN_REQ_13_RecallCommit {
      doc /*
        Group (thin 0.5): agent surface is two operators only — Recall(q)
        and Commit(Δ) — over session graph S with rate cap R. Grammar SSOT:
        docs/grammar/math-skeleton.md. Does not replace MN-REQ-02.4 / 04.*.
        Engine/MCP cut SHALL NOT be claimed from this group alone.
      */
      attribute requirementId : String = "MN-REQ-13";

      requirement def MN_REQ_13_1_TwoOperators {
        doc /*
          SHALL model exactly two product operators: Recall(q) (seed then
          bounded k-hop reconstruct; empty seed ⇒ skip) and Commit(Δ)
          (one gate; mutate / ingest / absorb are id-mint rules). RSV SHALL
          be a lease under Commit / SessionLifecycle, not a third API.
          HostSearchBridge SHALL remain outside MemNetSystem. Layer / Tier A
          remain REJECTED on accept (retire-from-wheel leftover; hierarchical
          reconstruct is not Layer dialect). PinMapShapedRead implemented
          SHALL NOT be read as BoundedMatchFind shipped (#73).
          Goldfish SHALL be Shape: the LLM SHALL NOT receive raw session S
          (pin_map depth/row/fan-out caps; hide recycled). Goldfish SHALL
          interact only with relevant slices. Prefer one pin_map on the
          live TSK (HiAgent current subgoal). Extra topics: at most one
          view=shell survey, then interior on the task — SHALL NOT default
          to N serial full maps (duplicate LAW / overlap). Seed set |Q|≤L
          SHALL union k-hop under one M (not Path-B M×anchors). Goldfish
          SHALL emit a sparse Δ (NEW/SET only; SHALL NOT echo the fetched
          slice); the session SHALL take it via Commit. SHALL NOT call that
          writeback Absorb (ImportAbsorb remains Path-B WorkingMemorySlice +
          id_policy only). Host Snap (corpus locators via RagHostHook) SHALL
          stay outside MemNetSystem and SHALL NOT ANN-index the session.
          In-session task already on S SHALL seed then pin_map (read_list /
          hub / leftover #73) — not Snap-on-session. Switch-task SHALL
          settle the old TSK then Shape a new ego — not Peak_L as default.
          SHALL NOT: rag_query; embeddings; PPR; RRF; GST/Steiner; ANN on
          the session; free MATCH/RETURN as goldfish; new HostSearchBridge
          leaves or HIT/RagDecision envelopes; dual-teach GraphQL /
          LangChain / HiGram as agent wire.
        */
        attribute requirementId : String = "MN-REQ-13.1";
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
  requirement saveSessionSnapshotReq
    : MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_4_SaveSessionSnapshot;
  requirement loadSessionSnapshotReq
    : MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_5_LoadSessionSnapshot;
  requirement optionalKeepSessionIdReq
    : MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_6_OptionalKeepSessionId;
  requirement sessionAsSsotHandleReq
    : MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_7_SessionAsSsotHandle;
  requirement noGraphDumpHandoffReq
    : MN_REQ_00_MissionBridge::MN_REQ_01_SessionLifecycle::MN_REQ_01_8_NoGraphDumpHandoff;

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
  requirement anchoredPinMapReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_1_AnchoredPinMap;
  requirement recycleHiddenFromPinMapReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_2_RecycleHiddenFromPinMap;
  requirement pinMapDepthAndRowCapsReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_3_PinMapDepthAndRowCaps;
  requirement engineLawPrependReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_4_EngineLawPrepend;
  requirement anchoredWalkReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_5_AnchoredWalk;
  requirement boundedMatchFindReq
    : MN_REQ_00_MissionBridge::MN_REQ_04_SliceEconomy::MN_REQ_04_6_BoundedMatchFind;

  requirement hardCapsReq
    : MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps;
  requirement storeResourceCapsReq
    : MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_1_StoreResourceCaps;
  requirement queryFanoutCapsReq
    : MN_REQ_00_MissionBridge::MN_REQ_05_HardCaps::MN_REQ_05_2_QueryFanoutCaps;

  requirement processBoundaryReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary;
  requirement inProcessPrimaryReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_1_InProcessPrimary;
  requirement localIpcShareReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_2_LocalIpcShare;
  requirement tcpServeMigrationReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_3_TcpServeMigration;
  requirement durableStoreBehindMemNetReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_4_DurableStoreBehindMemNet;
  requirement externalCabinetServerReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_5_ExternalCabinetServer;
  requirement operatorEvidenceNotLiveClaimReq
    : MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_6_OperatorEvidenceNotLiveClaim;

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
  requirement pinMapEmitSameAsMutateReq
    : MN_REQ_00_MissionBridge::MN_REQ_08_AgentIoGrammar::MN_REQ_08_9_PinMapEmitSameAsMutate;

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
  requirement pinMapMustFitContextReq
    : MN_REQ_00_MissionBridge::MN_REQ_10_LlmPropertiesAndLimits::MN_REQ_10_2_PinMapMustFitContext;
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

  requirement snapshotInteropReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop;
  requirement exportGraphToSysmlV2Req
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_1_ExportGraphToSysmlV2;
  requirement nodeMapsToSysmlStructureReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_2_NodeMapsToSysmlStructure;
  requirement edgeMapsToSysmlConnectionReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_3_EdgeMapsToSysmlConnection;
  requirement distinctFromSessionSnapshotReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_4_DistinctFromSessionSnapshot;
  requirement sysmlRoundTripShouldReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_5_SysmlRoundTripShould;
  requirement snapshotCodebaseIntoGraphReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_6_SnapshotCodebaseIntoGraph;
  requirement codebaseNodesAreModulesSymbolsReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_7_CodebaseNodesAreModulesSymbols;
  requirement codebaseEdgesAreRelationsReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_8_CodebaseEdgesAreRelations;
  requirement snapshotAtoIntoGraphReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_9_SnapshotAtoIntoGraph;
  requirement snapshotSkillsAndRulesIntoGraphReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_10_SnapshotSkillsAndRulesIntoGraph;
  requirement skillsAndRulesAreNodesReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_11_SkillsAndRulesAreNodes;
  requirement skillsRulesEdgesAreRelationsReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_12_SkillsRulesEdgesAreRelations;
  requirement mapOfPinsReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_13_MapOfPins;
  requirement pcbaAtoNodesAreNetsComponentsPinsReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_14_PcbaAtoNodesAreNetsComponentsPins;
  requirement pcbaAtoEdgesAreConnectivityReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_15_PcbaAtoEdgesAreConnectivity;
  requirement pinIngestDeterministicIdsReq
    : MN_REQ_00_MissionBridge::MN_REQ_11_SnapshotInterop::MN_REQ_11_16_PinIngestDeterministicIds;

  requirement multitaskModeReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode;
  requirement sharedSessionMissionSsotReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_1_SharedSessionMissionSsot;
  requirement sharedStoreTransportReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_2_SharedStoreTransport;
  requirement parentOwnsTaskLifecycleReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_3_ParentOwnsTaskLifecycle;
  requirement workerPinMapAndScopedWriteReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_4_WorkerPinMapAndScopedWrite;
  requirement preferOneWorkerOrDisjointReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_5_PreferOneWorkerOrDisjoint;
  requirement parentEndTurnNoPollReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_6_ParentEndTurnNoPoll;
  requirement noAssumeAclReserveIngestReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_7_NoAssumeAclReserveIngest;
  requirement appliesToRelevantTasksReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_8_AppliesToRelevantTasks;
  requirement leadOwnsSessionImportReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_9_LeadOwnsSessionImport;
  requirement noChatOrWholeStoreImportReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_10_NoChatOrWholeStoreImport;
  requirement cheapLlmImportGuardSoftReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_11_CheapLlmImportGuardSoft;
  requirement hostDrivenAsyncParallelReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_12_HostDrivenAsyncParallel;
  requirement neighbourhoodReserveReq
    : MN_REQ_00_MissionBridge::MN_REQ_12_MultitaskMode::MN_REQ_12_13_NeighbourhoodReserve;

  requirement recallCommitReq
    : MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit;
  requirement twoOperatorsReq
    : MN_REQ_00_MissionBridge::MN_REQ_13_RecallCommit::MN_REQ_13_1_TwoOperators;

  // Groups derive from mission (MN-REQ-00)
  #derivation connection deriveGroupsFromMission {
    end #original ::> missionReq;
    end #derive ::> sessionLifecycleReq;
    end #derive ::> memoryNetGraphReq;
    end #derive ::> strictMutateReq;
    end #derive ::> sliceEconomyReq;
    end #derive ::> hardCapsReq;
    end #derive ::> processBoundaryReq;
    end #derive ::> mcpAgentBoundaryReq;
    end #derive ::> agentIoGrammarReq;
    end #derive ::> humanInspectReq;
    end #derive ::> llmPropertiesAndLimitsReq;
    end #derive ::> snapshotInteropReq;
    end #derive ::> multitaskModeReq;
    end #derive ::> recallCommitReq;
  }

  // Leaves derive from their group
  #derivation connection deriveSessionLeaves {
    end #original ::> sessionLifecycleReq;
    end #derive ::> namedSessionsReq;
    end #derive ::> sessionLifecycleOpsReq;
    end #derive ::> sessionTtlAndCapsReq;
    end #derive ::> saveSessionSnapshotReq;
    end #derive ::> loadSessionSnapshotReq;
    end #derive ::> optionalKeepSessionIdReq;
    end #derive ::> sessionAsSsotHandleReq;
    end #derive ::> noGraphDumpHandoffReq;
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
    end #derive ::> anchoredPinMapReq;
    end #derive ::> recycleHiddenFromPinMapReq;
    end #derive ::> pinMapDepthAndRowCapsReq;
    end #derive ::> engineLawPrependReq;
    end #derive ::> anchoredWalkReq;
    end #derive ::> boundedMatchFindReq;
  }

  #derivation connection deriveHardCapsLeaves {
    end #original ::> hardCapsReq;
    end #derive ::> storeResourceCapsReq;
    end #derive ::> queryFanoutCapsReq;
  }

  #derivation connection deriveProcessBoundaryLeaves {
    end #original ::> processBoundaryReq;
    end #derive ::> inProcessPrimaryReq;
    end #derive ::> localIpcShareReq;
    end #derive ::> tcpServeMigrationReq;
    end #derive ::> durableStoreBehindMemNetReq;
    end #derive ::> externalCabinetServerReq;
    end #derive ::> operatorEvidenceNotLiveClaimReq;
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
    end #derive ::> pinMapEmitSameAsMutateReq;
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
    end #derive ::> pinMapMustFitContextReq;
    end #derive ::> minimiseTokenRoundTripsReq;
    end #derive ::> externalGroundTruthRequiredReq;
    end #derive ::> grammarMustBeLlmLearnableReq;
    end #derive ::> preferTemplateFriendlyPinsReq;
    end #derive ::> humanVerifyViaParserReq;
  }

  #derivation connection deriveSnapshotInteropLeaves {
    end #original ::> snapshotInteropReq;
    end #derive ::> mapOfPinsReq;
    end #derive ::> exportGraphToSysmlV2Req;
    end #derive ::> nodeMapsToSysmlStructureReq;
    end #derive ::> edgeMapsToSysmlConnectionReq;
    end #derive ::> distinctFromSessionSnapshotReq;
    end #derive ::> sysmlRoundTripShouldReq;
    end #derive ::> snapshotCodebaseIntoGraphReq;
    end #derive ::> codebaseNodesAreModulesSymbolsReq;
    end #derive ::> codebaseEdgesAreRelationsReq;
    end #derive ::> snapshotAtoIntoGraphReq;
    end #derive ::> snapshotSkillsAndRulesIntoGraphReq;
    end #derive ::> skillsAndRulesAreNodesReq;
    end #derive ::> skillsRulesEdgesAreRelationsReq;
    end #derive ::> pcbaAtoNodesAreNetsComponentsPinsReq;
    end #derive ::> pcbaAtoEdgesAreConnectivityReq;
    end #derive ::> pinIngestDeterministicIdsReq;
  }

  #derivation connection deriveMultitaskLeaves {
    end #original ::> multitaskModeReq;
    end #derive ::> sharedSessionMissionSsotReq;
    end #derive ::> sharedStoreTransportReq;
    end #derive ::> parentOwnsTaskLifecycleReq;
    end #derive ::> workerPinMapAndScopedWriteReq;
    end #derive ::> preferOneWorkerOrDisjointReq;
    end #derive ::> parentEndTurnNoPollReq;
    end #derive ::> noAssumeAclReserveIngestReq;
    end #derive ::> appliesToRelevantTasksReq;
    end #derive ::> leadOwnsSessionImportReq;
    end #derive ::> noChatOrWholeStoreImportReq;
    end #derive ::> cheapLlmImportGuardSoftReq;
    end #derive ::> hostDrivenAsyncParallelReq;
    end #derive ::> neighbourhoodReserveReq;
  }

  #derivation connection deriveRecallCommitLeaves {
    end #original ::> recallCommitReq;
    end #derive ::> twoOperatorsReq;
  }

  #derivation connection deriveTargetsFromMapOfPins {
    end #original ::> mapOfPinsReq;
    end #derive ::> exportGraphToSysmlV2Req;
    end #derive ::> snapshotCodebaseIntoGraphReq;
    end #derive ::> snapshotAtoIntoGraphReq;
    end #derive ::> snapshotSkillsAndRulesIntoGraphReq;
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
    end #derive ::> pinMapEmitSameAsMutateReq;
    end #derive ::> noHostilePositionalDumpReq;
  }

  #derivation connection derivePromptSurfaceFromPromptRules {
    end #original ::> followPromptRulesReq;
    end #derive ::> llmFriendlyStdioReq;
    end #derive ::> llmFriendlyMcpReq;
    end #derive ::> writeApproxDisplayReq;
    end #derive ::> templateCopyableShapesReq;
    end #derive ::> pinMapEmitSameAsMutateReq;
  }

  #derivation connection deriveSessionFromNoChatStore {
    end #original ::> noChatAsDurableStoreReq;
    end #derive ::> sessionLifecycleReq;
  }

  #derivation connection deriveSaveLoadFromNoChatStore {
    end #original ::> noChatAsDurableStoreReq;
    end #derive ::> saveSessionSnapshotReq;
    end #derive ::> loadSessionSnapshotReq;
  }

  #derivation connection deriveKeepIdFromLoad {
    end #original ::> loadSessionSnapshotReq;
    end #derive ::> optionalKeepSessionIdReq;
  }

  #derivation connection deriveSliceFromContextLimit {
    end #original ::> pinMapMustFitContextReq;
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

  #derivation connection deriveRecallFromSlice {
    end #original ::> queryOverNodeEdgeGraphReq;
    end #original ::> sliceEconomyReq;
    end #derive ::> recallCommitReq;
    end #derive ::> twoOperatorsReq;
  }

  #derivation connection deriveSnapshotFromNodeEdge {
    end #original ::> exactlyNodeAndEdgeReq;
    end #original ::> edgesAreFirstClassReq;
    end #derive ::> snapshotInteropReq;
    end #derive ::> exportGraphToSysmlV2Req;
    end #derive ::> snapshotCodebaseIntoGraphReq;
    end #derive ::> snapshotAtoIntoGraphReq;
    end #derive ::> snapshotSkillsAndRulesIntoGraphReq;
  }

  #derivation connection deriveSysmlMappingFromNodeEdge {
    end #original ::> exactlyNodeAndEdgeReq;
    end #derive ::> nodeMapsToSysmlStructureReq;
    end #derive ::> edgeMapsToSysmlConnectionReq;
  }

  #derivation connection deriveCodebaseShapeFromNodeEdge {
    end #original ::> nodesHoldAtomisedFactsReq;
    end #original ::> edgesAreFirstClassReq;
    end #derive ::> codebaseNodesAreModulesSymbolsReq;
    end #derive ::> codebaseEdgesAreRelationsReq;
  }

  #derivation connection deriveSkillsRulesShapeFromNodeEdge {
    end #original ::> nodesHoldAtomisedFactsReq;
    end #original ::> edgesAreFirstClassReq;
    end #derive ::> skillsAndRulesAreNodesReq;
    end #derive ::> skillsRulesEdgesAreRelationsReq;
  }

  #derivation connection derivePcbaAtoShapeFromNodeEdge {
    end #original ::> nodesHoldAtomisedFactsReq;
    end #original ::> edgesAreFirstClassReq;
    end #derive ::> pcbaAtoNodesAreNetsComponentsPinsReq;
    end #derive ::> pcbaAtoEdgesAreConnectivityReq;
  }

  #derivation connection deriveDistinctFromSessionSave {
    end #original ::> saveSessionSnapshotReq;
    end #original ::> loadSessionSnapshotReq;
    end #derive ::> distinctFromSessionSnapshotReq;
  }

  // Cross-derive: Multitask from no-chat-store, process boundary, pin map
  #derivation connection deriveMultitaskFromNoChatStore {
    end #original ::> noChatAsDurableStoreReq;
    end #derive ::> multitaskModeReq;
    end #derive ::> sharedSessionMissionSsotReq;
    end #derive ::> sessionAsSsotHandleReq;
    end #derive ::> noGraphDumpHandoffReq;
    end #derive ::> leadOwnsSessionImportReq;
    end #derive ::> noChatOrWholeStoreImportReq;
    end #derive ::> cheapLlmImportGuardSoftReq;
  }

  #derivation connection deriveMultitaskFromProcessBoundary {
    end #original ::> processBoundaryReq;
    end #original ::> localIpcShareReq;
    end #original ::> tcpServeMigrationReq;
    end #derive ::> sharedStoreTransportReq;
  }

  #derivation connection deriveWorkerFromPinMap {
    end #original ::> anchoredPinMapReq;
    end #derive ::> workerPinMapAndScopedWriteReq;
  }

  #derivation connection deriveNoAssumeFromIngestRoadmap {
    end #original ::> pinIngestDeterministicIdsReq;
    end #derive ::> noAssumeAclReserveIngestReq;
  }
}
