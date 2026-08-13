/*
  MemNet behaviours - target architecture.
  Session lifecycle; goldfish loop (pin map->mutate->settle);
  mutate with NEW mint; pin-map ingest roadmap;
  SessionHandoffById (pass session id, not graph dump);
  SessionImportReceive (lead imports member working memory; ImportGuard);
  Multitask Mode for relevant tasks only (MN-REQ-12);
  optional DurableBuffer hydrate/flush roadmap (M2.5).
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
      Layer / Tier A accept retired (ADR-001 M2).
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
    doc /* GqlCodec accepted batch (target). */
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
  attribute def EvHandoffSessionId {
    doc /*
      Parent delivers SessionHandoff (session id + optional anchors /
      writeScope) to a peer. Pass-by-reference for MissionWorkingSet SSOT.
    */
  }
  attribute def EvDumpGraphInChat {
    doc /*
      FORBIDDEN anti-pattern: hand off a full graph dump (or mission SSOT)
      via chat / tool prose instead of session id + re-pin_map.
    */
  }
  attribute def EvImportFromChat {
    doc /*
      FORBIDDEN anti-pattern: import member working memory from chat or tool
      transcripts instead of shared pin_map or WorkingMemorySlice.
    */
  }
  attribute def EvRequestSessionImport {
    doc /*
      Lead issues SessionImportRequest (path B separate sessions). Macro
      session import — not micro in-session node re-id (merge=true), and not
      Cypher MERGE (upsert-by-id) as the product verb.
    */
  }
  attribute def EvExportWorkingMemorySlice {
    doc /*
      Member exports bounded WorkingMemorySlice (anchors, depth/view, pins).
      MUST NOT be a whole-store dump.
    */
  }
  attribute def EvGuardReviewSlice {
    doc /*
      ImportGuard (cheap LLM) soft-reviews WorkingMemorySlice before lead
      mutate: scope fit, junk/off-mission, invented ids, size/settle noise.
    */
  }
  attribute def EvGuardAllow {
    doc /* ImportGuardDecision outcome=allow; proceed to import mutate. */
  }
  attribute def EvGuardTrim {
    doc /*
      ImportGuardDecision outcome=trim; lead imports reduced slice (reason
      recorded as structured atoms — not guard chat as SSOT).
    */
  }
  attribute def EvGuardReject {
    doc /* ImportGuardDecision outcome=reject; do not mutate lead session. */
  }
  attribute def EvImportWorkingMemorySlice {
    doc /*
      Lead imports WorkingMemorySlice into mission session under id policy
      (Cypher MERGE same id / reject conflict / remint NEW); edges after nodes.
      Runs only after ImportGuard allow/trim (path B) or skip when disabled.
    */
  }
  attribute def EvSharedSessionRepin {
    doc /*
      Path A: lead and member already share one session; lead "receives"
      member WM by re-pin_map only — no WorkingMemorySlice import.
    */
  }
  attribute def EvHydrateFromDurable {
    doc /*
      ROADMAP M2.5: hydrate a subgraph from DurableGraphStore into the live
      session under pin budget. Not claimed shipped.
    */
  }
  attribute def EvFlushToDurable {
    doc /*
      ROADMAP M2.5: flush settled / durable pins from the session into
      DurableGraphStore. One sync owner. Not claimed shipped.
    */
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
      Parent spawns one background worker with SessionHandoff (shared
      session id or separate assigned session, anchors, write scope)
      (MN-REQ-12). May fire once per worker in a parallel wave. Parent
      MUST follow with EvEndCoordinatorTurn (MN-REQ-12.6 / 12.12) — no
      same-turn poll. Uses SessionHandoffById — not EvDumpGraphInChat.
    */
  }
  attribute def EvEndCoordinatorTurn {
    doc /*
      Parent ends the Multitask coordinator turn after AsyncTaskDispatch
      (MN-REQ-12.6 / 12.12). MUST NOT poll or await EvWorkerReturn in the
      same turn. Next coordinator turn: pin_map first.
    */
  }
  attribute def EvOverlapScopeForbidden {
    doc /*
      Two workers would mutate overlapping WorkerWriteScope anchors on one
      shared session without serialisation (MN-REQ-12.5 / 12.12). MUST NOT
      dual-write in parallel; prefer one worker, disjoint anchors, separate
      session ids, or serial dispatch. Engine does not enforce (doctrineAsIs;
      0.4.x last-write-wins if violated).
    */
  }
  attribute def EvWorkerReturn {
    doc /*
      Host-driven asynchronous completion: worker durable facts are visible
      in the shared (or exportable) session; the agent host may revive the
      parent on a later turn. NOT a blocking await on the spawn turn
      (MN-REQ-12.12). Parent then pin_map / optional SessionImportReceive.
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
      doc /* PinMapShapedRead emitted shaped pin_map; LLM may reason. */
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
      Single mutate batch: parse GQL (GqlCodec target) -> mint NEW (if any) ->
      schema check -> strict commit -> emit AssignedIdMap. Aligns MN-REQ-03
      and 10.4. When the batch has no NEW / [NEW], minting is a no-op (empty
      id map) and the path proceeds to committing without inventing ids.
      TierA / Layer line codec parse is RETIRED on product path (M2 done).
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
      doc /* GqlCodec parse (target); reject invalid wire. */
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
      Applies to PinMapIngest roadmap stubs (domainVariant); not SnapshotStore.
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
        Worker(s) running under assigned scope after EvEndCoordinatorTurn
        (MN-REQ-12.6 / 12.12). Parallel only if disjoint scopes or separate
        sessions (MN-REQ-12.5). EvWorkerReturn is host-driven async revival.
      */
    }
    transition delegated_end_turn
      first taskDelegated
      accept EvEndCoordinatorTurn
      then taskDelegated;
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
      doc /*
        Facts in session; concise return. EvWorkerReturn is raised by the
        agent host when the worker finishes (async), not by parent poll.
      */
    }
    transition worker_next_turn
      first workerTurnDone
      accept EvPinMapRead
      then workerPresentingPinMap;
  }

  // --- 7. Multitask mission cycle (relevant tasks; MN-REQ-12) ---

  state def MultitaskMissionCycle {
    doc /*
      Coordinator mission over one shared session (or explicitly separate
      sessions) for relevant tasks only (MN-REQ-12.8): multi-step,
      delegated, or asynchronous parallel work. Composes
      ParentTaskLifecycle + WorkerScopedTurn + AsyncTaskDispatch.
      Hosted by MultitaskOperatingModel. Engine does not enforce
      ACL/reserve/WorkerWriteScope. Trivial one-shots take
      EvTrivialSingleAgent and stay on GoldfishLoop.
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
        USR_* (EvMintParentTask); assign WorkerWriteScope; SessionHandoffEmit;
        self-contained worker prompts. Aligns ParentTaskLifecycle
        taskMinted/taskScoped. Overlapping scopes → EvOverlapScopeForbidden.
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
    transition prepare_handoff
      first parentPreparing
      accept EvHandoffSessionId
      then parentPreparing;
    transition prepare_mutate
      first parentPreparing
      accept EvMutateGraph
      then parentPreparing;
    transition prepare_overlap_forbidden
      first parentPreparing
      accept EvOverlapScopeForbidden
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
        AsyncTaskDispatch: parent spawned one or more background workers
        then EvEndCoordinatorTurn (MN-REQ-12.6 / 12.12). Each member runs
        WorkerScopedTurn asynchronously. Prefer one worker; parallel only
        if disjoint scopes or separate session ids (MN-REQ-12.5). No
        same-turn poll/await of EvWorkerReturn.
      */
    }
    transition delegated_end_turn
      first workersDelegated
      accept EvEndCoordinatorTurn
      then workersDelegated;
    transition delegated_spawn_more
      first workersDelegated
      accept EvDelegateWorker
      then workersDelegated;
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
        Next coordinator turn (host revival after async workers): pin_map
        first; optional SessionImportReceive if separate sessions; act from
        shared-session slice; EvSettleMissionTask on parent-owned TSK_*
        (MN-REQ-12.3); do not redo worker investigation from chat.
      */
    }
    transition mission_reconcile_pin_map
      first parentReconciling
      accept EvPinMapRead
      then parentReconciling;
    transition mission_reconcile_shared_repin
      first parentReconciling
      accept EvSharedSessionRepin
      then parentReconciling;
    transition mission_reconcile_import
      first parentReconciling
      accept EvRequestSessionImport
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

  // --- 8. Session handoff by id (pass-by-reference; MN-REQ-01 / 12) ---

  state def SessionHandoffById {
    doc /*
      Explicit handoff of a MissionWorkingSet whose SSOT is the session
      (inter-module A → B pipe as well as parent → worker): source emits
      SessionHandoff (sessionId + caller; optional missionId / lease /
      anchors / writeScope) → sink pin_map → mutate still hits CapsPolicy.
      Shared session = same id; else worker session → lead import_slice.
      Contrasts forbidden EvDumpGraphInChat. Composes with EvDelegateWorker /
      MultitaskMissionCycle. Hosted by MultitaskOperatingModel.
    */
    entry;
    then handoffIdle;

    state handoffIdle {
      doc /* No handoff in flight. */
    }
    transition idle_to_delivering
      first handoffIdle
      accept EvHandoffSessionId
      then deliveringSessionId;
    transition idle_via_delegate
      first handoffIdle
      accept EvDelegateWorker
      then deliveringSessionId;
    transition idle_reject_dump
      first handoffIdle
      accept EvDumpGraphInChat
      then handoffRejected;

    state deliveringSessionId {
      doc /*
        Source delivers SessionHandoff only — sessionId + caller (optional
        missionId / lease / anchors / writeScope). MUST NOT attach a graph
        dump in chat, MissionDock, or HTTP body.
      */
    }
    transition deliver_to_worker_open
      first deliveringSessionId
      accept EvOpenSession
      then workerOpeningSession;
    transition deliver_reuse_session
      first deliveringSessionId
      accept EvPinMapRead
      then workerPinMapping;
    transition deliver_reject_dump
      first deliveringSessionId
      accept EvDumpGraphInChat
      then handoffRejected;

    state workerOpeningSession {
      doc /* Worker binds to the same shared session id (MN-REQ-12.2 / 12.4). */
    }
    transition open_to_pin_map
      first workerOpeningSession
      accept EvPinMapRead
      then workerPinMapping;
    transition open_fail
      first workerOpeningSession
      accept EvError
      then handoffIdle;

    state workerPinMapping {
      doc /* Worker goldfish: pin_map first on shared session; copy ids. */
    }
    transition pin_to_scoped_mutate
      first workerPinMapping
      accept EvMutateGraph
      then workerScopedMutate;
    transition pin_repeat
      first workerPinMapping
      accept EvPinMapRead
      then workerPinMapping;
    transition pin_return_readonly
      first workerPinMapping
      accept EvWorkerReturn
      then handoffComplete;

    state workerScopedMutate {
      doc /* Mutate under WorkerWriteScope; facts stay in session. */
    }
    transition mutate_ok
      first workerScopedMutate
      accept EvCommitOk
      then handoffComplete;
    transition mutate_return
      first workerScopedMutate
      accept EvWorkerReturn
      then handoffComplete;
    transition mutate_fail
      first workerScopedMutate
      accept EvError
      then workerPinMapping;

    state handoffComplete {
      doc /* Handoff done; parent may re-pin_map on next coordinator turn. */
    }
    transition complete_to_idle
      first handoffComplete
      accept EvSettleMissionTask
      then handoffIdle;
    transition complete_rehandoff
      first handoffComplete
      accept EvHandoffSessionId
      then deliveringSessionId;

    state handoffRejected {
      doc /*
        EvDumpGraphInChat (or equivalent graph-dump chat handoff) rejected.
        Recover by delivering session id only.
      */
    }
    transition rejected_retry_id
      first handoffRejected
      accept EvHandoffSessionId
      then deliveringSessionId;
    transition rejected_to_idle
      first handoffRejected
      accept EvError
      then handoffIdle;
  }

  // --- 9. Session import receive (team lead imports member WM) ---

  state def SessionImportReceive {
    doc /*
      Team lead imports a team member's working memory into the mission
      session (product verb = import; colloquial "session merge" means this
      import only — no SessionMerge* type names). Parent mission session =
      lead WM (SSOT). Worker session or scoped slice = member WM.
      Happy path A (preferred Multitask default): already shared session →
      EvSharedSessionRepin (lead re-pin_map; no second store; import nest
      skipped; ImportGuard not used). Path B: separate sessions → export
      WorkingMemorySlice → optional ImportGuard (cheap LLM soft policy) →
      owner-gated id policy (reject/remint/Cypher MERGE upsert) →
      ImportAbsorb → settle TSK_* in lead session.
      Chat is never the import payload (EvImportFromChat forbidden).
      Whole-store dump and dual-writer during import forbidden. Distinct
      from micro in-session node re-id (merge=true) and from naming this
      behaviour after Cypher MERGE. Hosted by MultitaskOperatingModel.
      Case study: outputs/session-import-case-study.md.
    */
    entry;
    then importIdle;

    state importIdle {
      doc /* No import in flight; Multitask or single-agent goldfish may run. */
    }
    transition idle_path_a_repin
      first importIdle
      accept EvSharedSessionRepin
      then pathASharedRepin;
    transition idle_path_b_request
      first importIdle
      accept EvRequestSessionImport
      then pathBRequesting;
    transition idle_reject_chat_import
      first importIdle
      accept EvImportFromChat
      then importRejected;

    state pathASharedRepin {
      doc /*
        Path A happy path: whiteboard already shared. Lead re-pin_map on
        mission session; member facts already visible. No SessionImportRequest.
        ImportGuard is OPTIONAL soft policy — unused on this path unless an
        audit slice is explicitly exported.
      */
    }
    transition path_a_pin_map
      first pathASharedRepin
      accept EvPinMapRead
      then pathASharedRepin;
    transition path_a_optional_guard
      first pathASharedRepin
      accept EvGuardReviewSlice
      then pathBGuarding;
    transition path_a_settle
      first pathASharedRepin
      accept EvSettleMissionTask
      then importComplete;
    transition path_a_done
      first pathASharedRepin
      accept EvCommitOk
      then importComplete;

    state pathBRequesting {
      doc /* Lead SessionImportRequest; freeze dual-writer on target slice. */
    }
    transition path_b_to_export
      first pathBRequesting
      accept EvExportWorkingMemorySlice
      then pathBExporting;
    transition path_b_reject_dump
      first pathBRequesting
      accept EvDumpGraphInChat
      then importRejected;
    transition path_b_reject_chat
      first pathBRequesting
      accept EvImportFromChat
      then importRejected;

    state pathBExporting {
      doc /*
        Member exports bounded WorkingMemorySlice (sessionId, anchors,
        depth/view, shaped pins) — not whole store.
      */
    }
    transition export_to_guard
      first pathBExporting
      accept EvGuardReviewSlice
      then pathBGuarding;
    transition export_fail
      first pathBExporting
      accept EvError
      then importIdle;

    state pathBGuarding {
      doc /*
        ImportGuard (cheap LLM) soft-reviews slice before lead mutate.
        Soft checks only: assigned scope?, junk/off-mission?, invented ids?,
        oversized/settle noise?. MUST NOT replace schema/caps/id-policy/owner
        hard gates. Decision recorded as ImportGuardDecision atoms.
      */
    }
    transition guard_allow
      first pathBGuarding
      accept EvGuardAllow
      then pathBImporting;
    transition guard_trim
      first pathBGuarding
      accept EvGuardTrim
      then pathBImporting;
    transition guard_reject
      first pathBGuarding
      accept EvGuardReject
      then importRejected;
    transition guard_fail
      first pathBGuarding
      accept EvError
      then importIdle;

    state pathBImporting {
      doc /*
        Lead imports (after allow/trim): id policy may apply Cypher MERGE
        same id / reject conflict / remint NEW; commit nodes then edges into
        mission GraphStore.
      */
    }
    transition import_ok
      first pathBImporting
      accept EvCommitOk
      then pathBSettling;
    transition import_via_event
      first pathBImporting
      accept EvImportWorkingMemorySlice
      then pathBSettling;
    transition import_fail
      first pathBImporting
      accept EvError
      then importIdle;

    state pathBSettling {
      doc /* Lead settles parent-owned TSK_* from mission session pin map. */
    }
    transition path_b_settle
      first pathBSettling
      accept EvSettleMissionTask
      then importComplete;
    transition path_b_repin
      first pathBSettling
      accept EvPinMapRead
      then pathBSettling;

    state importComplete {
      doc /* Lead session holds imported durable pins; chat was never SSOT. */
    }
    transition complete_to_idle
      first importComplete
      accept EvSettleRecycle
      then importIdle;
    transition complete_path_a_again
      first importComplete
      accept EvSharedSessionRepin
      then pathASharedRepin;
    transition complete_path_b_again
      first importComplete
      accept EvRequestSessionImport
      then pathBRequesting;

    state importRejected {
      doc /*
        EvImportFromChat / graph-dump / dual-writer / ImportGuard reject.
        Recover via path A repin or path B bounded slice + guard allow/trim.
      */
    }
    transition rejected_to_path_a
      first importRejected
      accept EvSharedSessionRepin
      then pathASharedRepin;
    transition rejected_to_path_b
      first importRejected
      accept EvRequestSessionImport
      then pathBRequesting;
    transition rejected_to_idle
      first importRejected
      accept EvError
      then importIdle;
  }

  // --- 10. Durable buffer hydrate/flush (roadmap M2.5; not shipped) ---

  state def DurableHydrateFlushRoadmap {
    doc /*
      ROADMAP M2.5 behaviour: DurableBuffer / AgensGraphAdapter hydrate into
      session and flush settled subgraph out. MemNet remains sole agent-facing
      memory; LLM ↔ DurableGraphStore direct is out of default teach.
      Not claimed shipped.
    */
    entry;
    then durableIdle;

    state durableIdle {
      doc /* No hydrate/flush job; live session uses GraphStore only. */
    }
    transition idle_to_hydrating
      first durableIdle
      accept EvHydrateFromDurable
      then hydrating;
    transition idle_to_flushing
      first durableIdle
      accept EvFlushToDurable
      then flushing;

    state hydrating {
      doc /* Pull durable subgraph into session under pin / depth budget. */
    }
    transition hydrate_ok
      first hydrating
      accept EvCommitOk
      then durableIdle;
    transition hydrate_fail
      first hydrating
      accept EvError
      then durableIdle;

    state flushing {
      doc /* Push settled / durable pins from session to DurableGraphStore. */
    }
    transition flush_ok
      first flushing
      accept EvCommitOk
      then durableIdle;
    transition flush_fail
      first flushing
      accept EvError
      then durableIdle;
  }
}
