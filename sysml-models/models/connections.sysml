/*
  MemNet logical ports, connection defs, and conveyed items.

  Target (ADR-001): property-graph / openCypher-shaped GQL agent memory.
  First-class constructs: Node, Edge (relationship), Property, Label.
  pin_map = shaped subgraph read wrapping GQL (Write = display redefined).
  Layer / Tier A = legacy migration accept only — not 1.x teach.
*/
package MemNetConnections {
  private import ScalarValues::*;

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
      terms — see BindRelationship vs RelationRelationship — not as a second
      Layer teach surface.
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
      MUST NOT place law on a relationship. Replaces Layer-era law-on-NODE
      without keeping Layer ASCII as primary teach.
    */
  }

  item def PortIncidence {
    doc /*
      Port grain on a node (qualified endpoint for bind). Modelled as node
      properties / nested structure — not a third conceptual kind beside
      Node and Edge. Open detail in GQL wire profile (ADR-001 M1).
    */
  }

  // =====================================================================
  // Agent wire batches (GQL primary; Layer legacy)
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

  item def LegacyLayerBatch {
    doc /*
      LEGACY / migration only: former Layer / Tier A NODE|EDGE ASCII lines
      (MemNetLayer.g4 / tier_a). Accept path until M4; MUST NOT be 1.x teach.
      Alias names in code: TierABatch, shared dialect (0.4.x).
    */
  }

  item def GraphRecordBatch {
    doc /*
      Internal Node|Edge record batch after parse / before emit.
      Conceptual kinds remain exactly Node and Edge (property graph).
    */
  }

  item def LegacyPipeBatch {
    doc /*
      DEPRECATED: one-shot import of historical @TAG pipe session blobs.
      Not a standing store codec or agent dialect. Import once then gone.
    */
  }

  item def AssignedIdMap {
    doc /*
      Engine-allocated ids returned after mint of NEW on create.
      LLM must copy these thereafter (MN-REQ-10.4).
    */
  }

  item def SessionId {
    doc /* Opaque session identifier from open/load. */
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
      Parent-assigned anchors and relation scope for one MultitaskWorker.
      Parallel workers require disjoint scopes or separate sessions
      (MN-REQ-12.5). As-is: doctrine only; no engine ACL/reserve.
    */
  }
  item def HousekeepStats {
    doc /* Row counts and cap utilisation from housekeep stats. */
  }

  // =====================================================================
  // Ports — GQL primary, Layer legacy, internal records
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

  port def TierAOutPort {
    doc /* LEGACY: emit Layer / Tier A batch (migration accept). */
    out item payload : LegacyLayerBatch;
  }
  port def TierAInPort {
    doc /* LEGACY: consume Layer / Tier A batch (migration accept). */
    in item payload : LegacyLayerBatch;
  }

  port def GraphRecordOutPort {
    doc /* Emit internal Node|Edge records. */
    out item records : GraphRecordBatch;
  }
  port def GraphRecordInPort {
    doc /* Consume internal Node|Edge records. */
    in item records : GraphRecordBatch;
  }

  port def LegacyPipeOutPort {
    doc /* DEPRECATED: emit legacy pipe batch for one-shot import. */
    out item payload : LegacyPipeBatch;
  }
  port def LegacyPipeInPort {
    doc /* DEPRECATED: consume legacy pipe for one-shot import. */
    in item payload : LegacyPipeBatch;
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

  connection def TierAFlow {
    doc /* LEGACY Layer / Tier A flow (migration accept only). */
    end port source : TierAOutPort;
    end port sink : TierAInPort;
  }

  connection def GraphRecordFlow {
    doc /* Internal Node|Edge records between codec, mutate, store. */
    end port source : GraphRecordOutPort;
    end port sink : GraphRecordInPort;
  }

  connection def LegacyPipeFlow {
    doc /* DEPRECATED: one-shot legacy pipe import path. */
    end port source : LegacyPipeOutPort;
    end port sink : LegacyPipeInPort;
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
    doc /* Session id hand-off after open/load. */
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
}
