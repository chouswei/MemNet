/*
  MemNet behaviours - target architecture.
  Session lifecycle; goldfish loop (pin map->mutate->settle);
  mutate with NEW mint; pin-map ingest roadmap;
  Multitask Mode for relevant tasks only (MN-REQ-12): parent task
  lifecycle, worker scoped turns, mission cycle -- not trivial one-shots.
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
    doc /*
      Fetch shaped pin_map (PinMapShapedRead wraps GQL; emits ShapedSubgraph).
      Legacy alias: query_warm / PinMapComposer.
    */
  }
  attribute def EvWalkRead {
    doc /* query_walk hop lines. */
  }
  attribute def EvMutateGraph {
    doc /*
      add/update openCypher-shaped GQL batch (primary; may include NEW).
      Legacy Layer / Tier A accept until M4.
    */
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
    doc /* GqlCodec (or legacy TierACodec) accepted batch. */
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
  attribute def EvMintParentTask {
    doc /*
      Parent creates MissionTaskPin (TSK_*) / USR_* in the shared session
      (status=active). Relevant Multitask tasks only (MN-REQ-12.8).
    */
  }
  attribute def EvAssignWorkerScope {
    doc /*
      Parent binds WorkerWriteScope (anchors + relation types) for a worker
      on a parent-owned MissionTaskPin (MN-REQ-12.4 / 12.5).
    */
  }
  attribute def EvDelegateWorker {
    doc /*
      Parent spawns a background worker with shared session id, anchors,
      and write scope (MN-REQ-12); then ends the turn (MN-REQ-12.6).
    */
  }
  attribute def EvWorkerReturn {
    doc /*
      Worker durable facts are visible in the shared session; parent may
      re-pin_map on the next coordinator turn (no same-turn poll).
    */
  }
  attribute def EvSettleMissionTask {
    doc /*
      Parent settles owned MissionTaskPin (TSK_*) / USR_* from shared-session
      pin-map facts (MN-REQ-12.3); not from worker chat prose.
    */
  }
  attribute def EvTrivialSingleAgent {
    doc /*
      Work is a trivial one-shot; Multitask Mode does not apply
      (MN-REQ-12.8). Use GoldfishLoop only; shared TCP not required.
    */
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

  // --- 5. Parent-owned MissionTaskPin lifecycle (TSK_*; MN-REQ-12.3) ---

  state def ParentTaskLifecycle {
    doc /*
      Lifecycle of one parent-owned MissionTaskPin (TSK_*) under Multitask.
      Applies only to relevant tasks (MN-REQ-12.8). Parent settles from
      shared-session pin map; workers do not own settle. Hosted by
      MultitaskCoordinator. As-is: no ACL/reserve enforcement.
    */
    entry;
    then taskAbsent;

    state taskAbsent {
      doc /* No MissionTaskPin yet; trivial work stays here via EvTrivialSingleAgent. */
    }
    transition absent_trivial
      first taskAbsent
      accept EvTrivialSingleAgent
      then taskAbsent;
    transition absent_to_minting
      first taskAbsent
      accept EvMintParentTask
      then taskMinted;

    state taskMinted {
      doc /* TSK_* created (status=active) in shared session; not yet delegated. */
    }
    transition minted_pin_map
      first taskMinted
      accept EvPinMapRead
      then taskMinted;
    transition minted_assign_scope
      first taskMinted
      accept EvAssignWorkerScope
      then taskScoped;
    transition minted_settle_early
      first taskMinted
      accept EvSettleMissionTask
      then taskSettled;

    state taskScoped {
      doc /* WorkerWriteScope assigned; ready to EvDelegateWorker. */
    }
    transition scoped_to_delegated
      first taskScoped
      accept EvDelegateWorker
      then taskDelegated;
    transition scoped_reassign
      first taskScoped
      accept EvAssignWorkerScope
      then taskScoped;

    state taskDelegated {
      doc /*
        Worker(s) running under assigned scope. Parent ended turn
        (MN-REQ-12.6). Parallel only if disjoint scopes (MN-REQ-12.5).
      */
    }
    transition delegated_worker_return
      first taskDelegated
      accept EvWorkerReturn
      then taskReconciling;
    transition delegated_parent_repin
      first taskDelegated
      accept EvPinMapRead
      then taskReconciling;

    state taskReconciling {
      doc /*
        Parent next turn: pin_map first; act from shared slice; settle or
        re-delegate. Chat is never SSOT (MN-REQ-12.1).
      */
    }
    transition parent_reconcile_pin_map
      first taskReconciling
      accept EvPinMapRead
      then taskReconciling;
    transition parent_reconcile_mutate
      first taskReconciling
      accept EvMutateGraph
      then taskReconciling;
    transition parent_reconcile_settle
      first taskReconciling
      accept EvSettleMissionTask
      then taskSettled;
    transition parent_reconcile_redelegate
      first taskReconciling
      accept EvDelegateWorker
      then taskDelegated;

    state taskSettled {
      doc /* status=settled; optional led_to_success edges; recyclable. */
    }
    transition settled_to_absent
      first taskSettled
      accept EvSettleRecycle
      then taskAbsent;
    transition settled_new_task
      first taskSettled
      accept EvMintParentTask
      then taskMinted;
  }

  // --- 6. Worker scoped turn (assigned MissionTaskPin subgraph) ---

  state def WorkerScopedTurn {
    doc /*
      One MultitaskWorker turn on a parent-assigned WorkerWriteScope.
      MUST pin_map first; mutate only under scope; durable facts in session
      not chat (MN-REQ-12.4). Reuses engine GoldfishLoop / MutateWithNew
      under the shared store (MN-REQ-12.2). Hosted by MultitaskWorker.
    */
    entry;
    then workerAwaitingPinMap;

    state workerAwaitingPinMap {
      doc /* Idle; next action MUST be live pin map on shared session. */
    }
    transition worker_pin_map_start
      first workerAwaitingPinMap
      accept EvPinMapRead
      then workerPresentingPinMap;
    transition worker_wrong_session
      first workerAwaitingPinMap
      accept EvError
      then workerAwaitingPinMap;

    state workerPresentingPinMap {
      doc /* Copy assigned ids from pin map; reason outside MemNet. */
    }
    transition worker_to_mutate
      first workerPresentingPinMap
      accept EvMutateGraph
      then workerApplyingScopedMutate;
    transition worker_pin_map_repeat
      first workerPresentingPinMap
      accept EvPinMapRead
      then workerPresentingPinMap;
    transition worker_return_readonly
      first workerPresentingPinMap
      accept EvWorkerReturn
      then workerTurnDone;

    state workerApplyingScopedMutate {
      doc /*
        Mutate under WorkerWriteScope only. MUST NOT invent parent-minted
        ids; MUST NOT settle parent TSK_* / USR_* unless delegated.
      */
    }
    transition worker_mutate_ok
      first workerApplyingScopedMutate
      accept EvCommitOk
      then workerTurnDone;
    transition worker_mutate_to_return
      first workerApplyingScopedMutate
      accept EvWorkerReturn
      then workerTurnDone;
    transition worker_mutate_error
      first workerApplyingScopedMutate
      accept EvError
      then workerAwaitingPinMap;

    state workerTurnDone {
      doc /* Facts in shared session; concise return to parent; no parent poll. */
    }
    transition worker_next_turn
      first workerTurnDone
      accept EvPinMapRead
      then workerPresentingPinMap;
  }

  // --- 7. Multitask mission cycle (relevant tasks; MN-REQ-12) ---

  state def MultitaskMissionCycle {
    doc /*
      Coordinator mission over one shared session for relevant tasks only
      (MN-REQ-12.8): multi-step, delegated, or parallelisable work.
      Composes ParentTaskLifecycle + WorkerScopedTurn. Hosted by
      MultitaskOperatingModel. Engine does not enforce ACL/reserve.
      Trivial one-shots take EvTrivialSingleAgent and stay on GoldfishLoop.
    */
    entry;
    then missionIdle;

    state missionIdle {
      doc /* No Multitask mission; single-agent GoldfishLoop may still run. */
    }
    transition idle_trivial
      first missionIdle
      accept EvTrivialSingleAgent
      then missionIdle;
    transition idle_to_opening_mission
      first missionIdle
      accept EvOpenSession
      then parentPreparing;
    transition idle_to_loading_mission
      first missionIdle
      accept EvLoadSnapshot
      then parentPreparing;

    state parentPreparing {
      doc /*
        Shared store transport (MN-REQ-12.2); pin_map; mint MissionTaskPin /
        USR_* (EvMintParentTask); assign WorkerWriteScope; self-contained
        worker prompt. Aligns ParentTaskLifecycle taskMinted/taskScoped.
      */
    }
    transition prepare_pin_map
      first parentPreparing
      accept EvPinMapRead
      then parentPreparing;
    transition prepare_mint_task
      first parentPreparing
      accept EvMintParentTask
      then parentPreparing;
    transition prepare_assign_scope
      first parentPreparing
      accept EvAssignWorkerScope
      then parentPreparing;
    transition prepare_mutate
      first parentPreparing
      accept EvMutateGraph
      then parentPreparing;
    transition prepare_to_delegated
      first parentPreparing
      accept EvDelegateWorker
      then workersDelegated;
    transition prepare_abort
      first parentPreparing
      accept EvError
      then missionIdle;

    state workersDelegated {
      doc /*
        Parent ended turn after spawn (MN-REQ-12.6). Each worker runs
        WorkerScopedTurn on the shared session. Prefer one worker;
        parallel only if disjoint scopes (MN-REQ-12.5). No same-turn poll.
      */
    }
    transition delegated_worker_facts
      first workersDelegated
      accept EvWorkerReturn
      then parentReconciling;
    transition delegated_parent_next_turn
      first workersDelegated
      accept EvPinMapRead
      then parentReconciling;
    transition delegated_error
      first workersDelegated
      accept EvError
      then parentReconciling;

    state parentReconciling {
      doc /*
        Next coordinator turn: pin_map first; act from shared-session slice;
        EvSettleMissionTask on parent-owned TSK_* (MN-REQ-12.3); do not redo
        worker investigation from chat.
      */
    }
    transition mission_reconcile_pin_map
      first parentReconciling
      accept EvPinMapRead
      then parentReconciling;
    transition mission_reconcile_mutate
      first parentReconciling
      accept EvMutateGraph
      then parentReconciling;
    transition mission_reconcile_settle
      first parentReconciling
      accept EvSettleMissionTask
      then missionComplete;
    transition mission_reconcile_redelegate
      first parentReconciling
      accept EvDelegateWorker
      then workersDelegated;
    transition mission_reconcile_error
      first parentReconciling
      accept EvError
      then parentReconciling;

    state missionComplete {
      doc /* Parent tasks settled; session may remain open for further work. */
    }
    transition complete_to_idle
      first missionComplete
      accept EvCloseOrExpire
      then missionIdle;
    transition complete_new_wave
      first missionComplete
      accept EvMintParentTask
      then parentPreparing;
  }
}
