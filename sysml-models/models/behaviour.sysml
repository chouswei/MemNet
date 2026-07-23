/*
  MemNet behaviours - target architecture.
  Session lifecycle; goldfish loop (pin map->mutate->settle);
  mutate with NEW mint; pin-map ingest roadmap.
*/
package MemNetBehaviour {
  private import ScalarValues::*;

  // --- Events: session lifecycle ---

  attribute def EvOpenSession {
    doc /* session_open with SchemaSpec / TagMap lines. */
  }
  attribute def EvLoadSnapshot {
    doc /* session_load from SessionSnapshotBlob (MN-REQ-01). */
  }
  attribute def EvPinMapRead {
    doc /* Fetch live pin map (PinMapComposer). Legacy alias: query_warm. */
  }
  attribute def EvWalkRead {
    doc /* query_walk hop lines. */
  }
  attribute def EvMutateGraph {
    doc /* add/update Tier A batch (may include NEW). */
  }
  attribute def EvSaveSnapshot {
    doc /* session_save to SessionSnapshotBlob. */
  }
  attribute def EvCloseOrExpire {
    doc /* session_close or TTL purge. */
  }
  attribute def EvSettleRecycle {
    doc /* housekeep settle / mark recyclable / prune. */
  }
  attribute def EvError {
    doc /* Hard @ERR; command aborts without necessarily closing session. */
  }
  attribute def EvIdsAssigned {
    doc /* IdAllocator finished minting NEW -> real ids. */
  }
  attribute def EvParseOk {
    doc /* TierACodec accepted batch. */
  }
  attribute def EvCommitOk {
    doc /* GraphStore create/replace succeeded. */
  }
  attribute def EvPinMapSelect {
    doc /* Begin selective pin projection (MN-REQ-11). */
  }
  attribute def EvPinMapCommit {
    doc /* Commit projected NODE|EDGE pins into GraphStore. */
  }
  attribute def EvPinMapDone {
    doc /* Pin-map ingest/export finished or cancelled. */
  }

  // --- 1. Session lifecycle ---

  state def SessionLifecycleStates {
    doc /*
      Logical lifecycle of one named session in SessionLifecycle /
      InProcessEngine (primary) or via LocalIpcGateway / TcpServeBridge.
      Hosted by SessionLifecycle part. Aligns MN-REQ-01.
    */
    entry;
    then closed;

    state closed {
      doc /* No session id; open or load required. */
    }
    transition closed_to_opening
      first closed
      accept EvOpenSession
      then opening;
    transition closed_to_loading
      first closed
      accept EvLoadSnapshot
      then loading;

    state opening {
      doc /* SchemaRegistry merge, GraphStore create, optional LAW seed. */
    }
    transition opening_to_active
      first opening
      accept EvPinMapRead
      then active;
    transition opening_to_active_after_seed
      first opening
      accept EvMutateGraph
      then active;
    transition opening_to_closed_fail
      first opening
      accept EvError
      then closed;

    state loading {
      doc /* Restore SessionSnapshotBlob into schema + records. */
    }
    transition loading_to_active
      first loading
      accept EvPinMapRead
      then active;
    transition loading_to_closed_fail
      first loading
      accept EvError
      then closed;

    state active {
      doc /* Session usable: pin map/walk, mutate, housekeep, save. */
    }
    transition active_pin_map
      first active
      accept EvPinMapRead
      then active;
    transition active_walk
      first active
      accept EvWalkRead
      then active;
    transition active_mutate
      first active
      accept EvMutateGraph
      then active;
    transition active_settle
      first active
      accept EvSettleRecycle
      then active;
    transition active_to_saving
      first active
      accept EvSaveSnapshot
      then saving;
    transition active_to_closed
      first active
      accept EvCloseOrExpire
      then closed;
    transition active_error_stay
      first active
      accept EvError
      then active;

    state saving {
      doc /* Write SessionSnapshotBlob; session remains open. */
    }
    transition saving_to_active
      first saving
      accept EvPinMapRead
      then active;
    transition saving_to_active_done
      first saving
      accept EvMutateGraph
      then active;
    transition saving_to_closed
      first saving
      accept EvCloseOrExpire
      then closed;
  }

  // --- 2. Goldfish loop (engine side of turn) ---

  state def GoldfishLoop {
    doc /*
      Engine-visible goldfish turn: live pin map -> (LLM reasons outside) ->
      mutate -> settle/recycle -> ready for next pin map.
      Reason is external to MemNet; presentingPinMap covers that gap.
    */
    entry;
    then awaitingPinMap;

    state awaitingPinMap {
      doc /* Idle between turns; next action is live pin map read. */
    }
    transition pin_map_start
      first awaitingPinMap
      accept EvPinMapRead
      then presentingPinMap;

    state presentingPinMap {
      doc /* PinMapComposer emitted Tier A live pin map; LLM may reason. */
    }
    transition pin_map_to_await_mutate
      first presentingPinMap
      accept EvMutateGraph
      then applyingMutate;
    transition pin_map_to_settle_only
      first presentingPinMap
      accept EvSettleRecycle
      then settling;
    transition pin_map_repeat
      first presentingPinMap
      accept EvPinMapRead
      then presentingPinMap;
    transition pin_map_error
      first presentingPinMap
      accept EvError
      then awaitingPinMap;

    state applyingMutate {
      doc /* MutateGate in progress (see MutateWithNew for detail). */
    }
    transition mutate_to_settle
      first applyingMutate
      accept EvSettleRecycle
      then settling;
    transition mutate_to_await_pin_map
      first applyingMutate
      accept EvCommitOk
      then awaitingPinMap;
    transition mutate_error
      first applyingMutate
      accept EvError
      then awaitingPinMap;

    state settling {
      doc /* HousekeepSettle recycle/prune; recyclable hidden on next live pin map. */
    }
    transition settle_done
      first settling
      accept EvPinMapRead
      then presentingPinMap;
    transition settle_idle
      first settling
      accept EvCommitOk
      then awaitingPinMap;
  }

  // --- 3. Mutate with NEW mint ---

  state def MutateWithNew {
    doc /*
      Single mutate batch: parse Tier A -> mint NEW (if any) -> schema check
      -> strict commit -> emit AssignedIdMap. Aligns MN-REQ-03 and 10.4.
      When the batch has no NEW / [NEW], minting is a no-op (empty id map)
      and the path proceeds to committing without inventing ids.
    */
    entry;
    then idle;

    state idle {
      doc /* Waiting for mutate batch. */
    }
    transition idle_to_parsing
      first idle
      accept EvMutateGraph
      then parsing;

    state parsing {
      doc /* TierACodec parse; reject invalid wire. */
    }
    transition parsing_to_minting
      first parsing
      accept EvParseOk
      then minting;
    transition parsing_fail
      first parsing
      accept EvError
      then idle;

    state minting {
      doc /*
        IdAllocator replaces NEW / [NEW] with engine ids. If the batch has
        no NEW tokens, skip allocation and emit an empty AssignedIdMap
        (EvIdsAssigned) then commit ground ids only.
      */
    }
    transition minting_to_committing
      first minting
      accept EvIdsAssigned
      then committing;
    transition minting_fail
      first minting
      accept EvError
      then idle;

    state committing {
      doc /* GraphStore add fails if exists; update fails if absent. */
    }
    transition committing_ok
      first committing
      accept EvCommitOk
      then idle;
    transition committing_fail
      first committing
      accept EvError
      then idle;
  }

  // --- 4. Pin-map ingest (roadmap) ---

  state def PinMapIngestCycle {
    doc /*
      ROADMAP behaviour for MN-REQ-11 selective pin ingest/export.
      Applies to PinMapIngest_* stubs; not session file SnapshotStore.
    */
    entry;
    then pinIdle;

    state pinIdle {
      doc /* No pin-map job running. */
    }
    transition pin_start
      first pinIdle
      accept EvPinMapSelect
      then selectingPins;

    state selectingPins {
      doc /* Choose short anchors/locators - not corpus dump. */
    }
    transition pins_to_project
      first selectingPins
      accept EvPinMapCommit
      then projecting;
    transition pins_cancel
      first selectingPins
      accept EvPinMapDone
      then pinIdle;
    transition pins_error
      first selectingPins
      accept EvError
      then pinIdle;

    state projecting {
      doc /*
        Project selected artefacts to NODE|EDGE pins. Assign MemNet ids from
        deterministic locator keys (refdes, net, pin, path, qname, skill_id)
        or engine key plus required locator fields (MN-REQ-11.16). Reject
        client NEW / [NEW] for source elements (PCBA R1/U2, SysML qnames,
        module paths, …). LLM NEW remains only for later goldfish annotations.
      */
    }
    transition project_commit
      first projecting
      accept EvCommitOk
      then pinIdle;
    transition project_done
      first projecting
      accept EvPinMapDone
      then pinIdle;
    transition project_error
      first projecting
      accept EvError
      then pinIdle;
  }
}
