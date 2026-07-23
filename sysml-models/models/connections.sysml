/*
  MemNet logical ports, connection defs, and conveyed items.
  MCP host <-> MCP server <-> memnet serve TCP <-> SessionStore / MemStore.
*/
package MemNetConnections {
  private import ScalarValues::*;

  // --- Flow items (project-local) ---

  item def WireLine {
    doc /*
      One @TAG pipe-delimited record line (e.g. @TSK: id|goal|...).
      Token-efficient atom; never a prose paragraph.
    */
    attribute tagName : String;
    attribute fieldPayload : String;
  }

  item def WireBatch {
    doc /* One or more WireLine rows for add/update --stdin. */
  }

  item def SessionId {
    doc /* Opaque session identifier returned by session open/load. */
    attribute value : String;
  }

  item def TagMapSpec {
    doc /* Tag map lines (@TAG: field defs) supplied at session open. */
  }

  item def WarmSlice {
    doc /*
      Anchored live graph slice (MN-REQ-04): engine LAW01-LAW05 prepended when
      present, then reachable active (non-recyclable) rows within depth/max_rows
      caps. Output of query warm — not a full session dump.
    */
  }

  item def WalkSlice {
    doc /* Hop lines @WALK: src -[relation]-> dst from query walk. */
  }

  item def JsonEnvelope {
    doc /*
      MCP / serve response envelope: exit_code, stdout (wire), stderr (@ERR/@WRN),
      optional session_id, parsed errors list.
    */
    attribute exitCode : Integer;
    attribute stdoutText : String;
    attribute stderrText : String;
  }

  item def ErrorSignal {
    doc /* @ERR: code|message|example? on stderr; MCP surfaces in errors[]. */
    attribute errCode : String;
    attribute detailText : String;
  }

  item def SnapshotBlob {
    doc /* Persistable session snapshot (map + records + relations) for save/load. */
  }

  item def ServeCommand {
    doc /*
      TCP request body to memnet serve: JSON { args: string[], stdin?: string }.
      Length-prefixed framing on the wire.
    */
  }

  item def HousekeepStats {
    doc /* Row counts and cap utilisation from housekeep stats. */
  }

  // --- Software ports ---

  port def WirePayloadOutPort {
    doc /* Emit wire text (stdout records or stdin batch). */
    out item payload : WireBatch;
  }
  port def WirePayloadInPort {
    doc /* Consume wire text. */
    in item payload : WireBatch;
  }

  port def JsonEnvelopeOutPort {
    doc /* Emit MCP JSON envelope to host. */
    out item envelope : JsonEnvelope;
  }
  port def JsonEnvelopeInPort {
    doc /* Host receives MCP tool result. */
    in item envelope : JsonEnvelope;
  }

  port def ServeCommandOutPort {
    doc /* Client sends argv+stdin command to serve. */
    out item command : ServeCommand;
  }
  port def ServeCommandInPort {
    doc /* Serve accepts command request. */
    in item command : ServeCommand;
  }

  port def SessionIdOutPort {
    doc /* Emit session id. */
    out item session : SessionId;
  }
  port def SessionIdInPort {
    doc /* Accept session id. */
    in item session : SessionId;
  }

  port def WarmSliceOutPort {
    doc /* Emit warm slice. */
    out item slice : WarmSlice;
  }
  port def WarmSliceInPort {
    doc /* Accept warm slice. */
    in item slice : WarmSlice;
  }

  port def SnapshotOutPort {
    doc /* Emit snapshot. */
    out item snap : SnapshotBlob;
  }
  port def SnapshotInPort {
    doc /* Accept snapshot. */
    in item snap : SnapshotBlob;
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

  connection def WirePayloadFlow {
    doc /* Wire batch between codec, store ingest, and MCP tools. */
    end port source : WirePayloadOutPort;
    end port sink : WirePayloadInPort;
  }

  connection def JsonEnvelopeFlow {
    doc /* MCP tool result JSON to host agent. */
    end port source : JsonEnvelopeOutPort;
    end port sink : JsonEnvelopeInPort;
  }

  connection def ServeCommandFlow {
    doc /* Length-prefixed TCP command channel (MCP client / CLI -> serve). */
    end port source : ServeCommandOutPort;
    end port sink : ServeCommandInPort;
  }

  connection def SessionIdFlow {
    doc /* Session id hand-off after open/load. */
    end port source : SessionIdOutPort;
    end port sink : SessionIdInPort;
  }

  connection def WarmSliceFlow {
    doc /* Warm read result from query engine to MCP/CLI consumer. */
    end port source : WarmSliceOutPort;
    end port sink : WarmSliceInPort;
  }

  connection def SnapshotFlow {
    doc /* Snapshot save/load path. */
    end port source : SnapshotOutPort;
    end port sink : SnapshotInPort;
  }

  connection def ErrorSignalFlow {
    doc /* Error/warn signalling on stderr path. */
    end port source : ErrorSignalOutPort;
    end port sink : ErrorSignalInPort;
  }
}
