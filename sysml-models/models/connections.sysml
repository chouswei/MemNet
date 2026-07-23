/*
  MemNet logical ports, connection defs, and conveyed items.
  Target architecture: Tier A agent grammar, GraphStore NODE|EDGE,
  serve/MCP/CLI transport envelopes, pin-map projections.
*/
package MemNetConnections {
  private import ScalarValues::*;

  // --- Flow items ---

  item def TierABatch {
    doc /*
      Agent-facing Write=display dialect (Tier A): NODE and EDGE lines,
      optional section headers, mint token NEW. Live pin map emit and mutate stdin
      share shapes (MN-REQ-08.7). Not a prose blob or corpus dump.
    */
  }

  item def GraphRecordBatch {
    doc /*
      Internal NODE|EDGE record batch after parse / before emit.
      Conceptual kinds remain exactly NODE and EDGE.
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
      Session schema: allowed NODE kinds (tags) and fields; EDGE relation
      vocabulary. Realises TagMap role without implying positional I/O.
    */
  }

  item def LivePinMap {
    doc /*
      Turn-facing live pin map (MN-REQ-04): ego/anchor digest; engine-law
      rows prepended when present; reachable active pins within
      depth/max_rows. Same Tier A shapes as mutate. Not a full session dump.
      Legacy alias: query_warm.
    */
  }

  item def WalkSlice {
    doc /* Hop lines over NODE|EDGE: src -[relation]-> dst. */
  }

  item def JsonEnvelope {
    doc /*
      Transport envelope: exit_code, stdout (Tier A wire),
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
      Selective NODE|EDGE pin map into/out of SysML, codebase, PCBA
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

  item def HousekeepStats {
    doc /* Row counts and cap utilisation from housekeep stats. */
  }

  // --- Ports ---

  port def TierAOutPort {
    doc /* Emit Tier A agent grammar. */
    out item payload : TierABatch;
  }
  port def TierAInPort {
    doc /* Consume Tier A agent grammar. */
    in item payload : TierABatch;
  }

  port def GraphRecordOutPort {
    doc /* Emit internal NODE|EDGE records. */
    out item records : GraphRecordBatch;
  }
  port def GraphRecordInPort {
    doc /* Consume internal NODE|EDGE records. */
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
    doc /* Emit live pin map (turn-facing). */
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

  // --- Connection defs ---

  connection def TierAFlow {
    doc /* Agent grammar between codec, facades, and live pin map emit. */
    end port source : TierAOutPort;
    end port sink : TierAInPort;
  }

  connection def GraphRecordFlow {
    doc /* Internal NODE|EDGE records between codec, mutate, store. */
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
    doc /* Live pin map from PinMapComposer to consumer. */
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
