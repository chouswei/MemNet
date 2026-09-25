/*
  MemNet logical ports, connection defs, and conveyed items.

  Target (ADR-001): property-graph / openCypher-shaped GQL agent memory.
  Product framing (2026-08-13): MemNet = shared LLM memory; session id =
  pass-by-reference handle for a mission SOMETHING; durable GQL store sits
  behind MemNet (planned M2.5). First-class constructs: Node, Edge
  (relationship), Property, Label. pin_map = shaped subgraph read wrapping
  GQL (Write = display redefined). No Layer / Tier A teach or accept path —
  as-is codecs are implementation lag removed in M2.
*/
package MemNetConnections {
  private import ScalarValues::*;

  // =====================================================================
  // Shared LLM memory / session-as-handle (product framing)
  // =====================================================================

  item def SharedLlmMemory {
    doc /*
      Product concept: MemNet is mission working memory of / for LLMs
      (session-scoped goldfish buffer; multi-agent Multitask) — not the
      search corpus and not GraphRAG. Goldfish pins topic egos, Shapes
      slices (pin_map), Commits Δ; host Snap locators also via MutateGate.
      MUST NOT ANN-index the session. MUST NOT call goldfish writeback
      Absorb (Path-B ImportAbsorb only). SameThingAbsorb is a distinct
      in-session Commit rule, not that writeback naming. Realised by AgentMemory +
      SessionLifecycle in deploy — not by chat and not by direct LLM
      access to the durable store.
    */
  }

  // CompanyAnalyticalSsot lives under Application patterns (not core item zoo).

  item def MissionWorkingSet {
    doc /*
      Team lead / parent mission working memory: opaque mission SOMETHING
      whose SSOT is the named mission session. Thin handle only — content is
      the session graph (Node|Edge) peers re-discover via pin_map. Under
      Multitask this is the lead session the member slice is received into.
    */
  }

  item def CallerId {
    doc /*
      Who identity for CapsPolicy ACL who-check (SessionHandoff.caller /
      llm_id-class attribution) — role/user grain. Not a graph dump; not
      EvidenceCentre / MissionDock nesting. When session ACL is enabled, the
      shipped memnet.acl cut makes MutateGate / PinMapShapedRead consult
      CapsPolicy who before pin_map (≈ TRAVERSE) versus mutate (≈ WRITE).
      ACL is off by default. sessionId remains a secret capability and
      MUST NOT be dumped. Privilege analogy once:
      outputs/system-design-notes.md (CapsPolicy ACL).
    */
    attribute value : String;
  }

  item def SessionBind {
    doc /*
      Optional MemNet-only bind match (missionId + lease) — not a
      Neo4j/AgensGraph privilege. The shipped CapsPolicy ACL cut may require
      the configured missionId + lease on mutate when session ACL is enabled;
      in-process MAY skip bind under MEMNET_SERVE_INTERNAL, while
      require_bind=true boundaries enforce it. Distinct from dual-EDGE
      BindRelationship (port grain). sessionId is a secret capability and
      MUST NOT be dumped.
    */
    attribute caller : String;
    attribute sessionId : String;
    attribute missionId : String;
  }

  item def SessionCapability {
    doc /*
      sessionId as a secret capability token for the MissionWorkingSet.
      Peers who hold the id may re-pin_map / mutate only through the shipped
      CapsPolicy ACL cut when session ACL is enabled: who, pin_map versus
      mutate, WorkerWriteScope hard reject, and optional bind still apply.
      MUST NOT dump sessionId in chat, tool queues, MissionDock payloads,
      or HTTP bodies as casual prose. Pass via SessionHandoff pipe only.
      Full private/shared/open session_token modes remain deferred.
    */
    attribute sessionId : String;
  }

  item def SessionHandoff {
    doc /*
      Inter-module / Multitask pass-by-reference handle. Pipe: module A → B
      SHALL pass sessionId only; B pin_maps. Chat, MissionDock payloads, and
      HTTP bodies SHALL NOT carry the graph (chat is never SSOT). sessionId
      is a SessionCapability (secret) — MUST NOT dump in chat/queue.
      Mutate after handoff still hits the shipped CapsPolicy ACL cut when
      session ACL is enabled (who / pin_map-vs-mutate / WorkerWriteScope
      hard reject / optional bind) — a session id is not a mutate waiver.
      sessionId remains a secret capability and MUST NOT be dumped.
      Shared session = same sessionId (path A pin_map only). Else worker
      session → lead path B WorkingMemorySlice → SessionImportReceive /
      import_slice. MissionDock / EvidenceCentre are application patterns —
      MUST NOT nest under MemNetSystem. GQL only.
      Required: sessionId, caller (CallerId). Optional: missionId, lease
      (reserve design; WAIT / not this ACL cut), anchors,
      writeScope (Multitask WorkerWriteScope). MUST NOT carry a full
      graph dump. Fields already on this item — do not duplicate.
    */
    attribute sessionId : String;
    attribute caller : String;
    attribute missionId : String;
    attribute lease : String;
    attribute anchors : String;
    attribute writeScope : String;
  }

  item def WorkingMemorySlice {
    doc /*
      Bounded member WM export for path B SessionImportReceive. Carries
      sourceSessionId, anchors, depth/view, and shaped pin records (nodes
      then edges). Engine WorkingMemorySliceExport SHALL require anchors,
      enforce slice budget, exclude LAW/vocab, and MUST NOT dump the whole
      store. LLM MAY choose anchors/depth/view. Not N-server federation.
    */
    attribute sourceSessionId : String;
    attribute anchors : String;
    attribute depth : Integer;
    attribute view : String;
  }

  item def CatalogSessionLocator {
    doc /*
      0.15 catalog pin: session= + qname= properties naming an interior
      of one model Snap. Look = pin_map that session. Join = Absorb a
      slice. Not a store key; HiddenStoreHandle stays off the wire.
    */
    attribute session : String;
    attribute qname : String;
    attribute grain : String;
  }

  item def LibraryLocator {
    doc /*
      Extra 0.16: locator properties from the Neo4j library namespace
      (path= / line= / document_id= / qname= / session= / url=). Corpus
      haystack, not session S. generate=false. HiddenStoreHandle /
      _memnet_hid stay off the emit. Extra 0.17 MAY commit these via
      MutateGate / ingest (properties, not leftover locator-as-PK).
      line= is optional; hook emit with line= uses SYM, else MOD.
    */
    attribute path : String;
    attribute line : String;
    attribute document_id : String;
    attribute qname : String;
    attribute session : String;
    attribute url : String;
    attribute generate : Boolean = false;
  }

  item def SessionImportRequest {
    doc /*
      Lead-owned path B request to ImportAbsorb a member WorkingMemorySlice
      into the mission session. idPolicy: keep | reject | remint
      (keep = MERGE as a per-write lookup of labels+props / rel type+ends
      into lead SSOT — not append / not a second copy; not MERGE-by-id as
      a store key; leftover_MERGE_by_id is 0.9 as-is, not this keep).
      remint is leftover_NEW_mint / leftover_by_id. Distinct from
      micro merge=true (in-session re-id). Product types are SessionImport*
      only — no SessionMerge*.
    */
    attribute leadSessionId : String;
    attribute memberSessionId : String;
    attribute idPolicy : String;
  }

  item def ImportGuardDecision {
    doc /*
      OPTIONAL soft outcome from ImportGuard nest on path B only
      (ImportGuardHook when a host guard ran, or future CheapLlmImportGuard):
      allow | trim | reject + short reason. trim is subtractive: keepIds
      lists retained record ids (engine drops dangling edges). Happy path A
      = re-pin_map without this decision. Structured atoms only — MUST NOT
      make guard chat the SSOT. Does not replace engine hard gates. Host
      MAY skip ImportGuard (GuardPassthrough).
    */
    attribute outcome : String;
    attribute reason : String;
    attribute keepIds : String;
  }

  item def DurableGraphStore {
    doc /*
      Online durable property-graph store (AgensGraph-class or Neo4j-class)
      behind MemNet. Landed client: hydrate into / flush from the live
      session an ego slice (DurableStoreAdapter / Fake ci_seam when no
      URL / optional AgensGraph client with liveCabinetClaimed; optional
      Neo4j client with liveNeo4jClaimed=true (0.14); SessionLifecycle
      hydrate/flush). Factory binds exactly one of AgensGraph or Neo4j.
      Not a full copy of S. Not the file snapshot.
      Extra 0.16: one Neo4j process MAY host two named databases —
      cabinet (flushed S) vs library (corpus). Library is not this
      hydrate/flush item. Live cabinet is external — not vendored.
      LLM ↔ store direct (including Bolt) is out of default teach.
      One sync owner. MN-REQ-06.4.
    */
    attribute storageRole : String = "cabinet_ego";
  }

  // =====================================================================
  // Property-graph ontology (first-class conceptual model)
  // =====================================================================

  item def GraphElement {
    doc /*
      TARGET identity: the graph element (node or edge) IS the identity.
      CREATE () is legal. properties() MAY be empty. Later MATCH/MERGE
      looks up labels + properties; an edge is type + end elements.
      SHALL NOT invent a replacement application store key.
    */
    attribute emptyCreateLegal : Boolean = true;
    attribute propertiesMayBeEmpty : Boolean = true;
    attribute isIdentity : Boolean = true;
  }

  item def HiddenStoreHandle {
    doc /*
      TARGET: cabinet-internal elementId-style handle. NOT a property.
      NOT on the agent wire. NOT a business key. SHALL NOT be taught
      as identity or as a nickname.
    */
    attribute isProperty : Boolean = false;
    attribute onWire : Boolean = false;
    attribute isBusinessKey : Boolean = false;
  }

  item def NicknameIdProperty {
    doc /*
      TARGET: optional property id is a nickname only -- not identity,
      not a store key, not a fourth graph element. MAY be omitted.
    */
    attribute optional : Boolean = true;
    attribute isIdentity : Boolean = false;
  }

  item def PropertyGraphNode {
    doc /*
      First-class GQL/property-graph node. Identity is GraphElement
      (CREATE () legal; properties MAY be empty). Kind → primary Label;
      fields → Property map. Optional NicknameIdProperty id is not
      identity and not a store key. Constitutive law (if any) lives on
      the node as property `law` (and linked port structure), never on
      an edge. HiddenStoreHandle stays inside the store, off the wire.
    */
  }

  item def PropertyGraphEdge {
    doc /*
      First-class GQL relationship (edge). Identity is GraphElement.
      Later MATCH: relationship type + end elements. Property map MAY
      be empty. Dual grain (bind vs relation) is encoded in GQL-compatible
      terms — see BindRelationship vs RelationRelationship — not a second
      agent dialect. Optional nickname id only if present.
    */
  }

  item def PropertyGraphProperty {
    doc /*
      First-class key=value property on a node or relationship.
      Omit defaults on agent wire; no nested graph-valued properties.
      NicknameIdProperty is one optional property; HiddenStoreHandle is
      not a property.
    */
  }

  item def PropertyGraphLabel {
    doc /*
      First-class type/tag on a node or relationship type name.
      Prefer a single primary node label; avoid multi-label zoo on teach.
    */
  }

  item def BindRelationship {
    doc /*
      Dual-EDGE grain: bind. Both ends port-qualified (node.port).
      GQL: relationship type `bind` (or equivalent) with port-qualified
      endpoints / properties. Preserves ideal continuity at port incidence.
    */
  }

  item def RelationRelationship {
    doc /*
      Dual-EDGE grain: relation. Ends are GraphElement (type + end
      elements; labels + properties). Optional nickname id only if present.
      GQL: ordinary node–node relationship; type = sense (knows, owns, …).
    */
  }

  item def LawOnNode {
    doc /*
      Constitutive / causal law carried as a node Property (`law`, often
      LaTeX) plus optional linked port bag structure on the same node.
      MUST NOT place law on a relationship.
    */
  }

  item def PortIncidence {
    doc /*
      Port grain on a node (qualified endpoint for bind). Modelled as
      property values (ISO GQL property) — not a fourth graph-element
      kind beside node/vertex and edge/relationship. Wire profile ADR-001.
    */
  }

  // =====================================================================
  // Agent wire batches (GQL only; quarantined as-is codec types)
  // =====================================================================

  item def GqlWireBatch {
    doc /*
      Primary agent-facing wire (1.x teach): gated GQL mutate
      patterns (CREATE/MERGE/SET/DELETE under MemNet gates). Same family as
      the durable GQL store. Not an unbounded DBA RETURN table.
    */
  }

  item def ParsedGqlProgram {
    doc /*
      GraphGlot AST of one program. Not agent teach. Not a store key.
      Conveyed parse-front → product gate only.
    */
  }

  item def ShapedSubgraph {
    doc /*
      Redefined Write = display emit: bounded ego/view subgraph as
      openCypher-family graph text (nodes + relationships), produced by a
      pin_map-class tool that wraps GQL internally. Primary goldfish read.
      SHALL NOT be a raw tabular MATCH/RETURN dump. ShapeWalk emit of X̃.
      When |Q| > 1 the emit SHALL carry CueConflict (Q listed,
      cardinality visible). SHALL NOT silently pick one root.
    */
  }

  item def Cue {
    doc /*
      Recall cue q: a discrete codebook token — kind / primary label,
      properties (locators as properties), keyword; optional nickname
      id only if already set. Empty q is legal: it is the session
      outline (census of S), not a skip and not a node seed.
      A non-empty codebook miss MAY last-resort Peak_L (ρ*); Peak_L is
      not empty q and not default goldfish.
      Not a store-key id, not elementId, not a prose/embedding
      sentence, not AssignedIdMap.
    */
    attribute tokenKind : Boolean = true;
    attribute tokenProps : Boolean = true;
    attribute tokenKeyword : Boolean = true;
    attribute tokenNicknameOptional : Boolean = true;
    attribute emptyCueMeansOutline : Boolean = true;
    attribute notEmbedding : Boolean = true;
    attribute notStoreKey : Boolean = true;
  }

  item def SeedSet {
    doc /*
      Q = MATCH_L(q, S): a set of graph elements (relative nodes).
      Walk roots for ShapeWalk. On codebook miss, Q MAY be Peak_L
      residual local maxima. NOT AssignedIdMap. NOT store-key ids.
      Empty q is not this item — that is SessionOutlineCensus.
      leftover EmptySkip remains 0.10 honesty, not TARGET.
    */
    attribute seedsAreGraphElements : Boolean = true;
    attribute isAssignedIdMap : Boolean = false;
    attribute listAllRoots : Boolean = true;
    attribute cardinalityVisible : Boolean = true;
    attribute silentPickOne : Boolean = false;
  }

  item def CueConflictMark {
    doc /*
      Payload mark on the existing find / pin_map shaped emit when a cue
      yields |Q| > 1. See MemNet::CueConflict. NOT a product command.
    */
    attribute qListed : Boolean = true;
    attribute cardinalityVisible : Boolean = true;
    attribute silentPickOneRoot : Boolean = false;
    attribute productCommand : Boolean = false;
    attribute usualCaseSharedName : Boolean = true;
    attribute anySharedCue : Boolean = true;
    attribute differentWorldThingsStayTwoRoots : Boolean = true;
  }

  item def EmptySkip {
    doc /*
      leftover 0.10 empty Q skip (do not invent a node). Not TARGET.
      TARGET empty q is SessionOutlineCensus. productCommand=false.
    */
    attribute leftoverAsIsEngine : Boolean = true;
    attribute productCommand : Boolean = false;
    attribute targetImplemented : Boolean = false;
  }

  item def SessionOutlineCensus {
    doc /*
      Teach name = outline. Recall of session S with empty q: kinds
      that exist plus a few real nodes of each, with their actual
      labels and properties, under one hard LIMIT. Browser-shaped
      (Neo4j Browser / db.labels / AGE ag_label + LIMIT exemplars).
      Ask the session, not a node. SHALL NOT MATCH a seed node,
      dump edges, dump S, absorb, MATCH-all, RAG/HostSearch,
      getAllPages, Pattern C tour, or Pattern D seeded RAG.
      view=shell is grain on an already-seeded walk — not this census.
      After outline the agent picks one seen cue and pin_maps.
    */
    attribute kindsCatalog : Boolean = true;
    attribute realExemplars : Boolean = true;
    attribute actualLabelsAndProps : Boolean = true;
    attribute oneHardLimit : Boolean = true;
    attribute dumpEdges : Boolean = false;
    attribute dumpS : Boolean = false;
    attribute matchAll : Boolean = false;
    attribute viewShellIsOutline : Boolean = false;
  }

  item def GraphRecordBatch {
    doc /*
      Internal Node|Edge record batch after parse / before emit.
      Conceptual kinds remain exactly Node and Edge (property graph).
    */
  }

  item def AssignedIdMap {
    doc /*
      TARGET: optional nicknames after leftover NEW / by_id. TARGET
      create has no NEW and no required AssignedIdMap emit; the graph
      element is identity. Copy a nickname only if present (MN-REQ-10.4).
      MUST NOT be a product command on McpFacade / CliFacade.
    */
  }

  item def SessionId {
    doc /*
      Opaque session identifier from open/load. Pass-by-reference handle for
      a MissionWorkingSet (SOMETHING) whose SSOT is that session: peers receive
      the id (plus anchors / writeScope) and re-pin_map — no graph dump handoff.
      Treated as SessionCapability (secret): MUST NOT dump in chat/queue.
    */
    attribute value : String;
  }

  item def SchemaSpec {
    doc /*
      Session schema: allowed node Labels and Properties; relationship-type
      vocabulary. Realises TagMap role without GQL DDL teach in first cut.
    */
  }

  item def LivePinMap {
    doc /*
      Turn-facing pin_map-class payload (MN-REQ-04): shaped subgraph
      (ShapedSubgraph) for an ego/anchor within depth/max_rows/view budget;
      engine-law rows prepended when present. Wraps GQL; emit is graph-shaped
      Write = display. Legacy alias: query_warm. Not a full session dump.
      Recall window, not a store.
    */
    attribute storageRole : String = "recall_window";
  }

  item def WalkSlice {
    doc /*
      Hop lines over Node|Edge. Product-ops path enumeration — unbounded
      GQL variable-length algebra stays off the default agent teach surface.
    */
  }

  item def JsonEnvelope {
    doc /*
      Transport envelope: exit_code, stdout (agent wire payload),
      stderr (@ERR/@WRN), optional session_id, errors list.
    */
    attribute exitCode : Integer;
    attribute stdoutText : String;
    attribute stderrText : String;
  }

  item def ErrorSignal {
    doc /* @ERR: code|message|example? on stderr path. */
    attribute errCode : String;
    attribute detailText : String;
  }

  item def SessionSnapshotBlob {
    doc /*
      Durable named-session file (MN-REQ-01.4--01.6): schema + records +
      relations. Distinct from MN-REQ-11 pin-map projections. Optional
      TTL expire write when MEMNET_SAVE_ON_EXPIRE; remains until user
      drop. Explicit save and expire-save are this one blob.
      MUST NOT be treated as Neo4j cabinet dump.
      storageRole file_snapshot.
    */
    attribute storageRole : String = "file_snapshot";
  }

  item def PinMapProjection {
    doc /*
      Selective Node|Edge pin map into/out of SysML, codebase, PCBA
      (.ato), or skills/rules. Short anchors and locators only.
    */
  }

  item def ServeCommand {
    doc /*
      Migration TCP request to TcpServeBridge: JSON { args: string[],
      stdin?: string }. Length-prefixed framing on the wire.
    */
  }

  item def LocalIpcCommand {
    doc /*
      Local IPC request (named pipe on Windows / AF_UNIX on POSIX) carrying
      the same argv+stdin payload shape as ServeCommand, without TCP.
    */
  }

  item def InProcessCall {
    doc /*
      Direct in-process API call into GraphStore / SessionLifecycle (no
      serialised hop). Primary binding for MCP and library users.
    */
  }

  item def MissionTaskPin {
    doc /*
      House task row (TSK_*) in the shared session for Multitask missions.
      Parent mints and settles; workers may mutate under assigned scope but
      SHALL NOT own parent TSK_* settle (MN-REQ-12.3). Chat is not SSOT.
    */
  }
  item def WorkerWriteScope {
    doc /*
      Parent-assigned anchors and relation scope for one MultitaskWorker —
      label/id GRANT grain (cumulative OR hard reject on mutate).
      Asynchronous parallel workers require disjoint scopes or separate
      sessions (MN-REQ-12.5 / 12.12).
      CapsPolicy / MutateGate hard-reject out-of-scope writes when session
      ACL is enabled. pin_map (≈ TRAVERSE) may still see the bounded ego
      under read permission. Reserve/overlap coordination remains doctrine;
      sessionId is a secret capability and MUST NOT be dumped.
      Analogy once: outputs/system-design-notes.md (CapsPolicy ACL).
    */
  }
  item def HousekeepStats {
    doc /* Row counts and cap utilisation from housekeep stats. */
  }

  item def ServeUsageLook {
    doc /*
      Human-facing read-only usage snapshot (not GQL agent wire).
      Carries serve_status (up/host/port), optional sessions|n/max plus
      listed ids, and/or housekeep_stats summary. MUST NOT carry secrets,
      ImportGuard API keys, or mutate payloads. Observed from live serve
      / registry — not a second graph API.
    */
    attribute serveUp : Boolean;
    attribute host : String;
    attribute listenPort : Integer;
    attribute sessionCount : Integer;
    attribute sessionMax : Integer;
    attribute housekeepSummary : String;
  }

  item def ImportGuardArmedLook {
    doc /*
      ImportGuard armed/disarmed from env presence only (display).
      MUST NOT carry the key. MUST NOT enable, disable, or reproject.
    */
    attribute armed : Boolean;
    attribute keyOnPage : Boolean = false;
    attribute writable : Boolean = false;
  }

  item def HumanUsagePage {
    doc /*
      Localhost human look surface (HTML/text). Not agent GQL; not Foam
      product MCP. HTTP/UI parked until Core GO (implemented=false).
    */
    attribute localBindDefault : Boolean = true;
  }

  // =====================================================================
  // Ports — GQL primary + Multitask / durable; internal records
  // (Retired TierA / LegacyPipe ports: models/archive.sysml — off ProjectMemNet load)
  // =====================================================================

  port def GqlWireOutPort {
    doc /* Emit openCypher-shaped GQL agent wire. */
    out item payload : GqlWireBatch;
  }
  port def GqlWireInPort {
    doc /* Consume gated GQL agent wire. */
    in item payload : GqlWireBatch;
  }

  port def ParsedGqlProgramOutPort {
    doc /* GraphGlot parse result toward the MemNet product gate. */
    out item ast : ParsedGqlProgram;
  }
  port def ParsedGqlProgramInPort {
    doc /* Consume a GraphGlot parse result at the product gate. */
    in item ast : ParsedGqlProgram;
  }

  port def ShapedSubgraphOutPort {
    doc /* Emit bounded shaped subgraph (pin_map Write = display). */
    out item slice : ShapedSubgraph;
  }
  port def ShapedSubgraphInPort {
    doc /* Accept shaped subgraph. */
    in item slice : ShapedSubgraph;
  }

  port def CueInPort {
    doc /* Accept Recall cue q (labels+props+keyword). */
    in item cue : Cue;
  }
  port def CueOutPort {
    doc /* Emit Recall cue q. */
    out item cue : Cue;
  }

  port def SeedSetOutPort {
    doc /* Emit seed set Q of graph elements (relative nodes). */
    out item seeds : SeedSet;
  }
  port def SeedSetInPort {
    doc /* Accept seed set Q as ShapeWalk roots. */
    in item seeds : SeedSet;
  }

  port def EmptySkipOutPort {
    doc /* leftover empty Q skip signal (not TARGET product). */
    out item skip : EmptySkip;
  }

  port def OutlineCensusOutPort {
    doc /* Emit session outline census (empty-q Recall of S). */
    out item census : SessionOutlineCensus;
  }

  port def SessionHandoffOutPort {
    doc /* Emit SessionHandoff (sessionId + caller; no graph dump). */
    out item handoff : SessionHandoff;
  }
  port def SessionHandoffInPort {
    doc /* Accept SessionHandoff; sink pin_maps (no graph in the pipe). */
    in item handoff : SessionHandoff;
  }

  port def WorkingMemorySliceOutPort {
    doc /* Emit bounded WorkingMemorySlice (member export for import). */
    out item slice : WorkingMemorySlice;
  }
  port def WorkingMemorySliceInPort {
    doc /* Lead / ImportGuard accepts WorkingMemorySlice for SessionImportReceive. */
    in item slice : WorkingMemorySlice;
  }

  port def CatalogSessionLocatorOutPort {
    doc /*
      Emit catalog session= + qname= locator pins (0.15). Not PinMapProjection.
      Not a store key. HiddenStoreHandle stays off the wire.
    */
    out item locator : CatalogSessionLocator;
  }
  port def CatalogSessionLocatorInPort {
    doc /*
      Accept catalog session= locator pins (list / look). Look remains pin_map
      of that session. SHALL NOT ANN-rank sessions.
    */
    in item locator : CatalogSessionLocator;
  }

  port def LibraryLocatorOutPort {
    doc /*
      Extra 0.16: emit library-namespace locators only. Never generate.
      Never shaped pin_map. Never cabinet hydrate payload.
    */
    out item locator : LibraryLocator;
  }
  port def LibraryLocatorInPort {
    doc /*
      Extra 0.17: accept library / host locators into RagHostHook
      (outside MemNetSystem) and existing MutateGate / PinMapIngest.
      Used this cut. SHALL NOT RRF/PPR. SHALL NOT Snap-on-session.
      Skip is valid when the source emits nothing.
    */
    in item locator : LibraryLocator;
  }

  port def SessionImportRequestOutPort {
    doc /* Emit lead-owned SessionImportRequest. */
    out item importReq : SessionImportRequest;
  }
  port def SessionImportRequestInPort {
    doc /* Accept SessionImportRequest into SessionLifecycle / lead session. */
    in item importReq : SessionImportRequest;
  }

  port def ImportGuardDecisionOutPort {
    doc /* Emit soft ImportGuardDecision (allow / trim / reject + reason). */
    out item decision : ImportGuardDecision;
  }
  port def ImportGuardDecisionInPort {
    doc /* Lead SessionImportReceive consumes ImportGuardDecision. */
    in item decision : ImportGuardDecision;
  }

  port def DurableHydrateOutPort {
    doc /* Landed client: hydrate an ego slice from DurableGraphStore into the session. Not on Commit. Not on TTL. */
    out item store : DurableGraphStore;
  }
  port def DurableHydrateInPort {
    doc /* Landed client: session accepts an ego hydrate from DurableGraphStore. */
    in item store : DurableGraphStore;
  }
  port def DurableFlushOutPort {
    doc /* Landed client: flush an ego slice from the session toward DurableGraphStore. Not on Commit. Not on TTL. */
    out item store : DurableGraphStore;
  }
  port def DurableFlushInPort {
    doc /* Landed client: DurableGraphStore accepts an ego flush from the session. */
    in item store : DurableGraphStore;
  }

  port def GraphRecordOutPort {
    doc /* Emit internal Node|Edge records. */
    out item records : GraphRecordBatch;
  }
  port def GraphRecordInPort {
    doc /* Consume internal Node|Edge records. */
    in item records : GraphRecordBatch;
  }

  port def AssignedIdOutPort {
    doc /* Leftover 0.9 invented mint nicknames (NEW / by_id), not TARGET. */
    out item ids : AssignedIdMap;
  }
  port def AssignedIdInPort {
    doc /* Accept assigned id map. */
    in item ids : AssignedIdMap;
  }

  port def JsonEnvelopeOutPort {
    doc /* Emit MCP/CLI JSON envelope to host. */
    out item envelope : JsonEnvelope;
  }
  port def JsonEnvelopeInPort {
    doc /* Host receives tool/CLI result envelope. */
    in item envelope : JsonEnvelope;
  }

  port def ServeCommandOutPort {
    doc /* Client sends argv+stdin to TcpServeBridge (migration). */
    out item command : ServeCommand;
  }
  port def ServeCommandInPort {
    doc /* TcpServeBridge accepts command request. */
    in item command : ServeCommand;
  }

  port def LocalIpcOutPort {
    doc /* Client sends argv+stdin over local IPC. */
    out item command : LocalIpcCommand;
  }
  port def LocalIpcInPort {
    doc /* LocalIpcGateway accepts IPC command. */
    in item command : LocalIpcCommand;
  }

  port def InProcessOutPort {
    doc /* Facade invokes in-process engine API. */
    out item call : InProcessCall;
  }
  port def InProcessInPort {
    doc /* InProcessEngine accepts direct API call. */
    in item call : InProcessCall;
  }

  port def SessionIdOutPort {
    doc /* Emit session id. */
    out item session : SessionId;
  }
  port def SessionIdInPort {
    doc /* Accept session id. */
    in item session : SessionId;
  }

  port def LivePinMapOutPort {
    doc /* Emit live pin map (shaped subgraph envelope). */
    out item slice : LivePinMap;
  }
  port def LivePinMapInPort {
    doc /* Accept live pin map. */
    in item slice : LivePinMap;
  }

  port def WalkSliceOutPort {
    doc /* Emit walk hop lines. */
    out item slice : WalkSlice;
  }
  port def WalkSliceInPort {
    doc /* Accept walk hop lines. */
    in item slice : WalkSlice;
  }

  port def SessionSnapshotOutPort {
    doc /* Emit session file snapshot. */
    out item snap : SessionSnapshotBlob;
  }
  port def SessionSnapshotInPort {
    doc /* Accept session file snapshot. */
    in item snap : SessionSnapshotBlob;
  }

  port def PinMapOutPort {
    doc /* Emit pin-map projection (MN-REQ-11). */
    out item pins : PinMapProjection;
  }
  port def PinMapInPort {
    doc /* Accept pin-map projection for ingest. */
    in item pins : PinMapProjection;
  }

  port def SchemaOutPort {
    doc /* Emit schema spec. */
    out item schema : SchemaSpec;
  }
  port def SchemaInPort {
    doc /* Accept schema at session open. */
    in item schema : SchemaSpec;
  }

  port def ErrorSignalOutPort {
    doc /* Emit error signal. */
    out item err : ErrorSignal;
  }
  port def ErrorSignalInPort {
    doc /* Accept error signal. */
    in item err : ErrorSignal;
  }

  port def ServeUsageLookOutPort {
    doc /* Emit read-only serve usage snapshot toward the human look. */
    out item look : ServeUsageLook;
  }
  port def ServeUsageLookInPort {
    doc /* Dashboard accepts a usage snapshot (look only). */
    in item look : ServeUsageLook;
  }

  port def ImportGuardArmedLookOutPort {
    doc /* Emit ImportGuard armed flag (env presence; no key). */
    out item armed : ImportGuardArmedLook;
  }
  port def ImportGuardArmedLookInPort {
    doc /* Dashboard accepts ImportGuard armed display (no write). */
    in item armed : ImportGuardArmedLook;
  }

  port def HumanLookOutPort {
    doc /* Emit localhost human usage page (not agent wire). */
    out item page : HumanUsagePage;
  }

  port def InviteMintOutPort {
    doc /* Admin emits an invite link (Szu-Wei only). */
    out item invite : InviteLink;
  }
  port def InviteMintInPort {
    doc /* Invite store accepts an admin-minted invite. */
    in item invite : InviteLink;
  }

  port def GoogleLoginOutPort {
    doc /* Invited user starts Google OAuth. */
    out item login : GoogleLoginAssert;
  }
  port def GoogleLoginInPort {
    doc /* Google IdP accepts the login start. */
    in item login : GoogleLoginAssert;
  }
  port def GoogleAssertOutPort {
    doc /* Google IdP emits a signed-in assertion. */
    out item asserted : GoogleLoginAssert;
  }
  port def GoogleAssertInPort {
    doc /* Portal accepts the Google assertion. */
    in item asserted : GoogleLoginAssert;
  }

  port def TipBearerOutPort {
    doc /* Emit a tip MCP Bearer (issue or show). */
    out item bearer : TipMcpBearer;
  }
  port def TipBearerInPort {
    doc /* Accept a tip MCP Bearer (issue, show, or gate). */
    in item bearer : TipMcpBearer;
  }

  port def BearerRevokeInPort {
    doc /* Key store accepts an admin revoke. */
    in item bearer : TipMcpBearer;
  }

  port def TipForwardOutPort {
    doc /* Gate emits an authenticated forward toward the Pi tip. */
    out item hop : TipMcpForward;
  }
  port def TipForwardInPort {
    doc /* Pi tip accepts an authenticated forward. */
    in item hop : TipMcpForward;
  }

  // =====================================================================
  // Connection defs
  // =====================================================================

  connection def GqlWireFlow {
    doc /* Primary agent GQL wire between codec, facades, and mutate. */
    end port source : GqlWireOutPort;
    end port sink : GqlWireInPort;
  }

  connection def ParsedGqlProgramFlow {
    doc /* GraphGlot parse front → MemNet product gate (after parse). */
    end port source : ParsedGqlProgramOutPort;
    end port sink : ParsedGqlProgramInPort;
  }

  connection def ShapedSubgraphFlow {
    doc /* Bounded shaped subgraph from ShapeWalk / PinMapShapedRead. */
    end port source : ShapedSubgraphOutPort;
    end port sink : ShapedSubgraphInPort;
  }

  connection def CueFlow {
    doc /* Cue q into RelativeSeed (MATCH_L; Peak_L only on codebook miss). */
    end port source : CueOutPort;
    end port sink : CueInPort;
  }

  connection def SeedSetFlow {
    doc /*
      RelativeSeed.seedOut → ShapeWalk.seedIn. Q is graph elements,
      not AssignedIdMap, not store-key ids.
    */
    end port source : SeedSetOutPort;
    end port sink : SeedSetInPort;
  }

  connection def SessionHandoffFlow {
    doc /*
      Inter-module / parent-worker pipe: source delivers SessionHandoff
      (SessionCapability sessionId + CallerId; optional missionId / lease /
      anchors / writeScope). Sink pin_maps. sessionId MUST NOT dump in
      chat/queue. MUST NOT convey a graph dump via chat, MissionDock, or
      HTTP body (EvDumpGraphInChat forbidden). CapsPolicy ACL still applies
      after receive (who / pin_map-vs-mutate / WorkerWriteScope / bind).
    */
    end port source : SessionHandoffOutPort;
    end port sink : SessionHandoffInPort;
  }

  connection def WorkingMemorySliceFlow {
    doc /*
      Macro import path B: member exports bounded WorkingMemorySlice; lead
      imports into mission session (SessionImportReceive). ImportGuard soft
      review is OPTIONAL on path B; happy path A skips this flow (re-pin only).
      Not chat import.
    */
    end port source : WorkingMemorySliceOutPort;
    end port sink : WorkingMemorySliceInPort;
  }

  connection def CatalogSessionLocatorFlow {
    doc /*
      0.15 catalog Snap emits session= + qname= locator pins into the list
      surface (CmdSessionList). Look = pin_map of that session. Join =
      Absorb a slice. SHALL NOT convey PinMapProjection; SHALL NOT ANN-rank;
      SHALL NOT treat session= as a store key.
    */
    end port source : CatalogSessionLocatorOutPort;
    end port sink : CatalogSessionLocatorInPort;
  }

  connection def SessionImportRequestFlow {
    doc /* Lead-owned SessionImportRequest into SessionLifecycle. */
    end port source : SessionImportRequestOutPort;
    end port sink : SessionImportRequestInPort;
  }

  connection def ImportGuardDecisionFlow {
    doc /*
      OPTIONAL soft-policy outcome into SessionImportReceive (path B).
      Happy path A has no this flow. MUST NOT replace schema / caps /
      id-policy / owner gates. Guard chat is not SSOT.
    */
    end port source : ImportGuardDecisionOutPort;
    end port sink : ImportGuardDecisionInPort;
  }

  connection def DurableHydrateFlow {
    doc /*
      Landed client: DurableBuffer ports → SessionLifecycle / GraphStore.
      Factory binds exactly one of AgensGraph or Neo4j. LLM does not
      connect to DurableBuffer as primary.
    */
    end port source : DurableHydrateOutPort;
    end port sink : DurableHydrateInPort;
  }

  connection def LibraryLocatorFlow {
    doc /*
      Extra 0.16: Neo4j library port → locators only. Extra 0.17:
      HostSearch / MutateGate / PinMapIngest MAY consume them (properties,
      not a store key). SHALL NOT bind to PinMapShapedRead. SHALL NOT
      convey generate, RRF, PPR, Leiden, or ANN of S. Skip the source
      when the library database name is unset.
    */
    end port source : LibraryLocatorOutPort;
    end port sink : LibraryLocatorInPort;
  }

  connection def DurableFlushFlow {
    doc /*
      Landed client: SessionLifecycle / GraphStore → DurableBuffer ports.
      Factory binds exactly one of AgensGraph or Neo4j.
      One sync owner; MUST NOT dual-write.
    */
    end port source : DurableFlushOutPort;
    end port sink : DurableFlushInPort;
  }

  connection def GraphRecordFlow {
    doc /* Internal Node|Edge records between codec, mutate, store. */
    end port source : GraphRecordOutPort;
    end port sink : GraphRecordInPort;
  }

  connection def AssignedIdFlow {
    doc /* Leftover 0.9 invented mint results (NEW / by_id). TARGET create has no NEW. */
    end port source : AssignedIdOutPort;
    end port sink : AssignedIdInPort;
  }

  connection def JsonEnvelopeFlow {
    doc /* Tool/CLI result JSON to host agent. */
    end port source : JsonEnvelopeOutPort;
    end port sink : JsonEnvelopeInPort;
  }

  connection def ServeCommandFlow {
    doc /* Length-prefixed TCP command (migration path to TcpServeBridge). */
    end port source : ServeCommandOutPort;
    end port sink : ServeCommandInPort;
  }

  connection def LocalIpcFlow {
    doc /* Named pipe / AF_UNIX command to LocalIpcGateway. */
    end port source : LocalIpcOutPort;
    end port sink : LocalIpcInPort;
  }

  connection def InProcessFlow {
    doc /* Direct in-process API call (primary MCP / library path). */
    end port source : InProcessOutPort;
    end port sink : InProcessInPort;
  }

  connection def SessionIdFlow {
    doc /* Session id as pass-by-reference handle after open/load / handoff. */
    end port source : SessionIdOutPort;
    end port sink : SessionIdInPort;
  }

  connection def LivePinMapFlow {
    doc /* Live pin map from PinMapShapedRead to consumer. */
    end port source : LivePinMapOutPort;
    end port sink : LivePinMapInPort;
  }

  connection def WalkSliceFlow {
    doc /* Walk result from query to consumer. */
    end port source : WalkSliceOutPort;
    end port sink : WalkSliceInPort;
  }

  connection def SessionSnapshotFlow {
    doc /* Named-session file save/load path (MN-REQ-01). */
    end port source : SessionSnapshotOutPort;
    end port sink : SessionSnapshotInPort;
  }

  connection def PinMapFlow {
    doc /* MN-REQ-11 selective pin-map ingest/export. */
    end port source : PinMapOutPort;
    end port sink : PinMapInPort;
  }

  connection def SchemaFlow {
    doc /* Schema at session open / validate ingest. */
    end port source : SchemaOutPort;
    end port sink : SchemaInPort;
  }

  connection def ErrorSignalFlow {
    doc /* Error/warn signalling on stderr path. */
    end port source : ErrorSignalOutPort;
    end port sink : ErrorSignalInPort;
  }

  connection def ServeUsageLookFlow {
    doc /*
      Read-only usage snapshot from serve / session list / housekeep
      toward MemNetUsageDashboard. MUST NOT convey mutate, session_close,
      import_slice, or ImportGuard keys. Dashboard does not own lifecycle.
    */
    end port source : ServeUsageLookOutPort;
    end port sink : ServeUsageLookInPort;
  }

  connection def ImportGuardArmedLookFlow {
    doc /*
      ImportGuard armed display (env presence) toward the dashboard.
      MUST NOT convey the API key or a write toggle.
    */
    end port source : ImportGuardArmedLookOutPort;
    end port sink : ImportGuardArmedLookInPort;
  }

  connection def InviteMintFlow {
    doc /*
      Admin invite mint into the invite store, and redeem onto the
      portal allowlist. Not a product-face credential.
    */
    end port source : InviteMintOutPort;
    end port sink : InviteMintInPort;
  }

  connection def GoogleLoginFlow {
    doc /* Invited user to Google IdP. */
    end port source : GoogleLoginOutPort;
    end port sink : GoogleLoginInPort;
  }

  connection def GoogleAssertFlow {
    doc /* Google IdP assertion into the portal. */
    end port source : GoogleAssertOutPort;
    end port sink : GoogleAssertInPort;
  }

  connection def TipBearerFlow {
    doc /*
      Bearer between portal, key store, invited user, and the tip
      gate. Authorization: Bearer. MUST NOT carry a sysmledge key.
    */
    end port source : TipBearerOutPort;
    end port sink : TipBearerInPort;
  }

  connection def BearerRevokeFlow {
    doc /* Admin revoke into the key store. */
    end port source : TipBearerOutPort;
    end port sink : BearerRevokeInPort;
  }

  connection def TipForwardFlow {
    doc /*
      Authenticated forward from TipMcpGate to the Pi tip MemNet MCP.
      Unauthenticated WWW MemNet is not this flow.
    */
    end port source : TipForwardOutPort;
    end port sink : TipForwardInPort;
  }

  // =====================================================================
  // Application patterns (NOT MemNet core item zoo — case-study only)
  // =====================================================================

  item def CompanyAnalyticalSsot {
    doc /*
      APPLICATION PATTERN only (not a MemNet core / product item):
      SharedLlmMemory hosts a company analytical SSOT ego (e.g. COM_2330_TPE)
      — news, findings, and analyse-loop writes accumulate in-session.
      Dual SSOT: MemNet = agent analytical memory; user ledger / price bars
      stay out of MemNet. MUST NOT nest under MemNetSystem as a peer core.
      See outputs/company-memory-case-study.md.
    */
  }

  item def HostSearchBridge {
    doc /*
      APPLICATION NEST only (MUST NOT nest under MemNetSystem). Optional
      RagHostHook Snaps the corpus to locators; existing MutateGate /
      PinMapIngest commits (Commit creates the element; no id-mint law).
      Extra 0.16 library port MAY feed locators here (0.17 consumes
      them; library stays locators-only / generate=false). Skip is
      valid. MUST NOT call this absorb (ImportAbsorb is Path-B slice +
      id_policy only). MUST NOT Snap-on-session. No rag_query MCP.
      RagHostHook.implemented=true outside MemNetSystem. Product math
      sits above this research: docs/grammar/math-skeleton.md. See
      docs/extras/memnet-host-search-nest.md.
    */
  }

  item def InviteLink {
    doc /*
      Admin-minted invite for the tip MemNet access portal.
      Redeems onto an allowlist. Not a sysmledge product credential
      and not an openProject token.
    */
    attribute mintedByAdmin : Boolean = true;
    attribute adminDisplayName : String = "Szu-Wei";
  }

  item def GoogleLoginAssert {
    doc /*
      Google OAuth assertion for an invited portal user.
      Identity only. MUST NOT authorise the SysMLEdge product face.
    */
    attribute provider : String = "google";
  }

  item def TipMcpBearer {
    doc /*
      Bearer key for the keyed tip MemNet MCP. Shown to the invited
      user after Google login. Sent as Authorization: Bearer.
      Revocable. MUST NOT open unauthenticated MemNet on WWW.
    */
    attribute scheme : String = "Bearer";
    attribute shownToInvitedUser : Boolean = true;
  }

  item def TipMcpForward {
    doc /*
      Auth-forward hop from the droplet WWW gate to the Pi tip
      MemNet MCP. Public URL stays keyed. tip≠face.
    */
    attribute wwwUrl : String = "https://memnet.139-59-255-181.nip.io/mcp";
    attribute authorizationHeader : String = "Authorization: Bearer";
    attribute unauthenticatedAllowed : Boolean = false;
    attribute forwardHost : String = "pi-tip";
  }

  item def TipMemNetAccess {
    doc /*
      OPS ACCESS pattern only (MUST NOT nest under MemNetSystem):
      Szu-Wei mints invites; invited users Google-login and fetch a
      Bearer for the tip MemNet MCP at
      https://memnet.139-59-255-181.nip.io/mcp. TipMcpGate refuses
      unauthenticated WWW MemNet and forwards to the Pi tip. Not the
      sysmledge product, not an openProject key page, not open MemNet
      for strangers (that remains SysMLEdge free tier or memnet-llm
      self-host). Portal web is the ops sidecar (portalWebImplemented=true;
      sellsInvent2Green=false). Status look of services and Bearer
      clients is look-only and MUST NOT unpark the usage dashboard
      HTTP. See
      outputs/tip-memnet-access-portal-case-study.md.
    */
  }

  item def DeviceMemNetFleet {
    doc /*
      APPLICATION / OPS PATTERN only (MUST NOT nest under MemNetSystem):
      multiple device MemNet services (MemNetCoreLibrary on Pi /
      workstation) plus one MemNetMcpServer at the droplet as the
      MemNet tip/ops engine face (tip≠face; mcpCount=1). Product
      invent face is cousin SysMLEdge (`sysmledge`;
      mustNotInventUploadBind). Device MAY run tip memnet-mcp for
      ops; MUST NOT nest a second product MCP / SysMLEdge-as-product.
      Each service keeps its own session registry. Handoff = session id.
      MUST NOT be N-server federation (#47). See
      outputs/device-fleet-one-mcp-case-study.md.
    */
  }

  // Retired Layer / TierA / LegacyPipe item zoo lives in models/archive.sysml
  // (package MemNetArchive). Root MUST NOT import it.

}
