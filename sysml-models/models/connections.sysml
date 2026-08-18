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
      Absorb (Path-B ImportAbsorb only). Realised by AgentMemory +
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

  item def SessionImportRequest {
    doc /*
      Lead-owned path B request to ImportAbsorb a member WorkingMemorySlice
      into the mission session. idPolicy: keep | reject | remint
      (keep = MERGE-by-id upsert into lead SSOT — not append / not a second
      copy). Distinct from micro merge=true (in-session re-id). Product
      types are SessionImport* only — no SessionMerge*.
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
      Online durable property-graph store (AgensGraph-class) behind MemNet.
      Hydrate into / flush from the live session via the M2.5 client adapter
      seam (DurableStoreAdapter / Fake / optional AgensGraph client;
      SessionLifecycle hydrate/flush). Live cabinet is external — not
      vendored; 0.7 hydrate/flush proven. LLM ↔ store direct is out of
      default teach. MN-REQ-06.4.
    */
  }

  // =====================================================================
  // Property-graph ontology (first-class conceptual model)
  // =====================================================================

  item def PropertyGraphNode {
    doc /*
      First-class GQL/property-graph node. Kind → primary Label; id → stable
      key/property; fields → Property map. Constitutive law (if any) lives on
      the node as property `law` (and linked port structure), never on an edge.
    */
  }

  item def PropertyGraphEdge {
    doc /*
      First-class GQL relationship (edge). Relationship type + Property map +
      direction. Dual grain (bind vs relation) is encoded in GQL-compatible
      terms — see BindRelationship vs RelationRelationship — not a second
      agent dialect.
    */
  }

  item def PropertyGraphProperty {
    doc /*
      First-class key=value property on a node or relationship.
      Omit defaults on agent wire; no nested graph-valued properties.
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
      Dual-EDGE grain: relation. Both ends bare node ids.
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
      Primary agent-facing wire (1.x teach): openCypher-shaped GQL mutate
      patterns (CREATE/MERGE/SET/DELETE under MemNet gates). Same family as
      AgensGraph. Not an unbounded DBA RETURN table.
    */
  }

  item def ShapedSubgraph {
    doc /*
      Redefined Write = display emit: bounded ego/view subgraph as
      openCypher-family graph text (nodes + relationships), produced by a
      pin_map-class tool that wraps GQL internally. Primary goldfish read.
      SHALL NOT be a raw tabular MATCH/RETURN dump.
    */
  }

  item def GraphRecordBatch {
    doc /*
      Internal Node|Edge record batch after parse / before emit.
      Conceptual kinds remain exactly Node and Edge (property graph).
    */
  }

  item def AssignedIdMap {
    doc /*
      Engine-allocated ids returned after mint of NEW on create.
      LLM must copy these thereafter (MN-REQ-10.4).
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
    */
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
      relations. Distinct from MN-REQ-11 pin-map projections.
    */
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

  // =====================================================================
  // Ports — GQL primary + Multitask / durable; internal records
  // (Retired TierA / LegacyPipe ports: see RETIRED archive section below)
  // =====================================================================

  port def GqlWireOutPort {
    doc /* Emit openCypher-shaped GQL agent wire. */
    out item payload : GqlWireBatch;
  }
  port def GqlWireInPort {
    doc /* Consume openCypher-shaped GQL agent wire. */
    in item payload : GqlWireBatch;
  }

  port def ShapedSubgraphOutPort {
    doc /* Emit bounded shaped subgraph (pin_map Write = display). */
    out item slice : ShapedSubgraph;
  }
  port def ShapedSubgraphInPort {
    doc /* Accept shaped subgraph. */
    in item slice : ShapedSubgraph;
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
    doc /* ROADMAP M2.5: hydrate subgraph from DurableGraphStore into session. */
    out item store : DurableGraphStore;
  }
  port def DurableHydrateInPort {
    doc /* ROADMAP M2.5: session accepts hydrate from DurableGraphStore. */
    in item store : DurableGraphStore;
  }
  port def DurableFlushOutPort {
    doc /* ROADMAP M2.5: flush settled subgraph from session toward store. */
    out item store : DurableGraphStore;
  }
  port def DurableFlushInPort {
    doc /* ROADMAP M2.5: DurableGraphStore accepts flush from session. */
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
    doc /* Emit engine-assigned ids after NEW mint. */
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

  // =====================================================================
  // Connection defs
  // =====================================================================

  connection def GqlWireFlow {
    doc /* Primary agent GQL wire between codec, facades, and mutate. */
    end port source : GqlWireOutPort;
    end port sink : GqlWireInPort;
  }

  connection def ShapedSubgraphFlow {
    doc /* Bounded shaped subgraph from PinMapShapedRead to consumer. */
    end port source : ShapedSubgraphOutPort;
    end port sink : ShapedSubgraphInPort;
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
      ROADMAP M2.5: DurableBuffer / AgensGraphAdapter → SessionLifecycle /
      GraphStore. LLM does not connect to DurableBuffer as primary.
    */
    end port source : DurableHydrateOutPort;
    end port sink : DurableHydrateInPort;
  }

  connection def DurableFlushFlow {
    doc /*
      ROADMAP M2.5: SessionLifecycle / GraphStore → DurableBuffer.
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
    doc /* Engine id allocation results after NEW mint. */
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
      PinMapIngest commits (Commit id-mint). Skip is valid. MUST NOT call
      this absorb (ImportAbsorb is Path-B slice + id_policy only). MUST
      NOT Snap-on-session. Design only — no rag_query MCP. Product math
      sits above this research: docs/grammar/math-skeleton.md. See
      grammar/memnet-host-search-nest.md.
    */
  }

  // =====================================================================
  // RETIRED / ARCHIVE — as-is traceability only (MUST NOT nest on product path)
  // TierA / Layer accept retired (ADR-001 M2 done). Keep defs for archive/
  // tests / historical wiring; do not compete with GQL item zoo as first-class.
  // =====================================================================

  item def LegacyLayerBatch {
    doc /*
      RETIRED archive — former Layer / Tier A NODE|EDGE ASCII (MemNetLayer.g4 /
      tier_a). Product accept REJECTED (M2 done; legacy_dialect_retired).
      MUST NOT be agent teach or nested on product path. Alias: TierABatch.
      Modules may remain for archive/tests only.
    */
  }

  item def LegacyPipeBatch {
    doc /*
      RETIRED archive — one-shot import of historical @TAG pipe session blobs.
      Not a standing store codec or agent dialect. MUST NOT nest on product path.
    */
  }

  port def TierAOutPort {
    doc /* RETIRED archive: former Tier A emit — MUST NOT nest on product path. */
    out item payload : LegacyLayerBatch;
  }
  port def TierAInPort {
    doc /* RETIRED archive: former Tier A consume — MUST NOT nest on product path. */
    in item payload : LegacyLayerBatch;
  }

  port def LegacyPipeOutPort {
    doc /* RETIRED archive: legacy pipe emit — MUST NOT nest on product path. */
    out item payload : LegacyPipeBatch;
  }
  port def LegacyPipeInPort {
    doc /* RETIRED archive: legacy pipe consume — MUST NOT nest on product path. */
    in item payload : LegacyPipeBatch;
  }

  connection def TierAFlow {
    doc /* RETIRED archive flow — MUST NOT nest on product path (M2 done). */
    end port source : TierAOutPort;
    end port sink : TierAInPort;
  }

  connection def LegacyPipeFlow {
    doc /* RETIRED archive: one-shot legacy pipe import — MUST NOT nest on product path. */
    end port source : LegacyPipeOutPort;
    end port sink : LegacyPipeInPort;
  }

}
