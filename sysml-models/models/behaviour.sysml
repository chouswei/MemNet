/*
  MemNet behaviours - target architecture.
  Session lifecycle; goldfish loop (RelativeSeed → ShapeWalk → Commit);
  TARGET mutate is pattern Commit (CREATE () legal; MERGE/SET/DELETE
  by labels+props); leftover_NEW_mint is leftover 0.9 only;
  pin-map ingest roadmap;
  SessionHandoffById (pass session id, not graph dump);
  SessionImportReceive (lead imports member working memory; ImportGuard);
  Multitask Mode for relevant tasks only (MN-REQ-12);
  optional DurableBuffer hydrate/flush (landed client; M2.5 seam).
  Empty-q GoldfishLoop: SessionOutline census of S (0.11 TARGET);
  leftover EvEmptySeedSkip is leftover 0.10 only.
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
  attribute def EvCue {
    doc /* Goldfish cue q: codebook tokens into RelativeSeed. */
  }
  attribute def EvSeedReady {
    doc /* RelativeSeed produced non-empty Q of graph elements. */
  }
  attribute def EvCueConflict {
    doc /*
      Recall shaped emit when |Q| > 1: Q listed, cardinality visible,
      CueConflict mark. SHALL NOT pick one root. Not a product command.
    */
  }
  attribute def EvEmptySeedSkip {
    doc /*
      leftover 0.10 empty Q skip ShapeWalk; do not invent a node.
      Not TARGET. TARGET empty q is EvSessionOutline. productCommand=false.
    */
  }
  attribute def EvEmptyCue {
    doc /*
      Empty codebook token q: dark session asks S, not a node.
      TARGET Recall branch = session outline (not skip, not ShapeWalk).
    */
  }
  attribute def EvSessionOutline {
    doc /*
      Teach name = outline. Recall of S with empty q: kinds that exist
      plus a few real nodes of each (actual labels and properties)
      under one hard LIMIT. Browser-shaped. SHALL NOT MATCH a seed
      node, dump edges, absorb, or treat view=shell as this census.
    */
  }
  attribute def EvPeakL {
    doc /*
      Last-resort residual Peak_L cue after a non-empty codebook miss.
      Not empty-q outline. Not default goldfish. Not a third operator.
    */
  }
  attribute def EvShapeWalk {
    doc /* ShapeWalk k-hop from Q under one M; emit shaped subgraph. */
  }
  attribute def EvPinMapRead {
    doc /*
      Fetch shaped pin_map (Recall = RelativeSeed then ShapeWalk, or
      empty-q SessionOutline, or Peak_L last-resort on codebook miss). SHALL NOT require a store-key --anchor
      (leftover_require_anchor is leftover engine). Goldfish IN: X̃ from
      Q, or outline census when q is empty. Same Recall operator as
      BoundedMatchFind MATCH_L. Legacy alias: query_warm.
    */
  }
  attribute def EvWalkRead {
    doc /* query_walk hop lines. */
  }
  attribute def EvMutateGraph {
    doc /*
      add/update become one Commit of GQL (TARGET). GraphElement identity;
      CREATE () legal. leftover_NEW_mint / AssignedIdMap is 0.9 leftover
      engine, not a TARGET product verb. Goldfish OUT: sparse Δ (MUST NOT echo
      the fetched slice; not ImportAbsorb). SameThingAbsorb MAY run as a
      Commit rule after the agent sees CueConflict on find / pin_map emit
      — not inside Recall. Ingest locators are
      properties, not leftover_ingestIsIdRule TARGET. Layer / Tier A
      accept retired (ADR-001 M2).
    */
  }
  attribute def EvSaveSnapshot {
    doc /* session_save to SessionSnapshotBlob. */
  }
  attribute def EvExpireTtl {
    doc /*
      Sliding TTL elapsed. RAM drop unless expire-save is on and the
      snapshot cannot be written: then RAM stays, counts against the
      session cap, and retries warn expire_snapshot_failed until an
      explicit successful save or close. Optional SnapshotStore file
      only when saveOnExpire is configured (MEMNET_SAVE_ON_EXPIRE).
      File stays until the user deletes it. Not Neo4j.
    */
  }
  attribute def EvEvictForCap {
    doc /*
      MN-REQ-05.5 (shipped, unreleased): session cap full on open or
      load, after purge_expired; this live session is the oldest-touched
      evictable victim. The victim lock is taken at pick and held through
      save, drop and registry removal. Save first, then drop from RAM.
    */
  }
  attribute def EvEvictSaved {
    doc /*
      MN-REQ-05.5 (shipped, unreleased): the victim's snapshot is complete
      (temp file, fsync, rename, fsync dir). Only this event drops the victim
      from RAM. Runtime check: tests/test_session_evict.py.
    */
  }
  attribute def EvCloseOrExpire {
    doc /* session_close or TTL purge after optional expire save. */
  }
  attribute def EvSettleRecycle {
    doc /* housekeep settle / mark recyclable / prune. */
  }
  attribute def EvError {
    doc /* Hard @ERR; command aborts without necessarily closing session. */
  }
  attribute def EvIdsAssigned {
    doc /* leftover_NEW_mint finished (0.9 leftover; not TARGET identity). */
  }
  attribute def EvParseOk {
    doc /* GqlCodec accepted batch (target). */
  }
  attribute def EvCommitOk {
    doc /* GraphStore create/replace succeeded. */
  }
  attribute def EvSameThingAbsorb {
    doc /*
      Agent-gated Commit collapse of two live elements judged the same
      world-thing. Pattern match labels+properties. Not Recall. Distinct
      from ImportAbsorb. Same name is a candidate only.
    */
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
  attribute def EvCatalogSnap {
    doc /*
      0.15 Snap(model): mint catalog + package interiors; Commit locators.
      Look remains pin_map. Join remains Path-B Absorb slice. Not Layer.
      Pre-check session and ingest budgets before mint (MN-REQ-11.17.3).
      Grain is package / kind-band / nested package (MN-REQ-11.17.2).
      Same root replaces after commit (MN-REQ-11.17.5).
    */
  }
  attribute def EvCallerGone {
    doc /*
      Serve or IPC peer closed, or client wait exceeded, while Catalog
      Snap is still minting. Stop; roll back sessions this call created
      (MN-REQ-11.17.4). Named refuse: caller_gone on serve, serve_timeout
      on the client envelope.
    */
  }
  attribute def EvHandoffSessionId {
    doc /*
      Parent delivers SessionHandoff (SessionCapability sessionId + CallerId;
      optional anchors / writeScope) to a peer. Pass-by-reference for
      MissionWorkingSet SSOT. sessionId MUST NOT dump in chat/queue.
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
      Lead issues SessionImportRequest (path B separate sessions). Product
      verb = import — not micro merge=true, not SessionMerge*.
    */
  }
  attribute def EvExportWorkingMemorySlice {
    doc /*
      Member WorkingMemorySliceExport: bounded slice (anchors required,
      budget, LAW excluded). MUST NOT be a whole-store dump. LLM MAY choose
      anchors.
    */
  }
  attribute def EvGuardReviewSlice {
    doc /*
      ImportGuard soft-reviews WorkingMemorySlice before ImportAbsorb:
      scope fit, junk trim (subtractive), invented ids, size/settle noise,
      optional keep-vs-remint advice.
    */
  }
  attribute def EvGuardAllow {
    doc /* ImportGuardDecision outcome=allow; proceed to ImportAbsorb. */
  }
  attribute def EvGuardTrim {
    doc /*
      ImportGuardDecision outcome=trim (subtractive keep_ids); ImportAbsorb
      imports reduced slice. Decision atoms — not guard chat as SSOT.
    */
  }
  attribute def EvGuardReject {
    doc /* ImportGuardDecision outcome=reject; no lead mutate. */
  }
  attribute def EvGuardSkip {
    doc /*
      Host disables ImportGuard (GuardPassthrough); slice proceeds to
      ImportAbsorb without ImportGuardDecision. Path A never uses this.
    */
  }
  attribute def EvImportWorkingMemorySlice {
    doc /*
      Lead ImportAbsorb under id_policy keep|reject|remint (TARGET keep =
      labels+props / type+ends MERGE; leftover_MERGE_by_id leftover;
      reject = labels+props match conflict, no mutate; leftover 0.9
      store-key id_conflict named leftover only; remint = leftover_NEW_mint,
      lead old stay, edges retarget); nodes then edges.
      After ImportGuard allow/trim or EvGuardSkip.
    */
  }
  attribute def EvSharedSessionRepin {
    doc /*
      Path A: shared mission sessionId; lead receives member WM by
      pin_map only — no WorkingMemorySlice, no ImportGuard, no ImportAbsorb.
    */
  }
  attribute def EvHydrateFromDurable {
    doc /*
      Landed client: hydrate an ego slice from DurableGraphStore into the
      live session under pin budget. Not on Commit. Not on TTL. No MCP
      or CLI caller.
    */
  }
  attribute def EvFlushToDurable {
    doc /*
      Landed client: flush an ego slice from the session into
      DurableGraphStore. One sync owner. Not on Commit. Not on TTL.
      No MCP or CLI caller.
    */
  }
  attribute def EvHostSearchCue {
    doc /*
      Extra 0.17: cue the outside RagHostHook (corpus Snap). SHALL NOT
      pass session S. SHALL NOT ANN-index S.
    */
  }
  attribute def EvHostSearchSkip {
    doc /*
      Extra 0.17: hook unset, host miss, timeout, or parse — skip is
      valid. Goldfish continues with pin_map / grep / existing pins.
    */
  }
  attribute def EvHostSearchLocators {
    doc /*
      Extra 0.17: locators only. Commit via existing MutateGate /
      PinMapIngest. MUST NOT absorb. MUST NOT emit chunk bodies.
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
      session ids, or serial dispatch. The shipped CapsPolicy ACL
      hard-rejects an individual out-of-scope mutate when session ACL is
      enabled; overlapping writers still require doctrine-level
      serialisation because no neighbourhood reserve is shipped.
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
      doc /*
        No session id; open or load required. An evicted session (MN-REQ-05.5)
        returns here; closed_to_loading via EvLoadSnapshot restores it from
        its snapshot: same ACL, no lease carried over.
      */
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
    transition active_to_expire_save
      first active
      accept EvExpireTtl
      then expireSaving;
    transition active_expire_drop
      first active
      accept EvExpireTtl
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

    state expireSaving {
      doc /*
        Configurable expire session_save. RAM then closed. File remains
        until user drop. Load from closed via EvLoadSnapshot.
      */
    }
    transition expire_save_to_closed
      first expireSaving
      accept EvCloseOrExpire
      then closed;

    state evictSaving {
      doc /*
        MN-REQ-05.5 (shipped): cap eviction of the oldest-touched saveable
        session. Write its snapshot first (fsync, atomic 0600, @SNAP v2);
        save ok drops RAM to closed, save failure keeps the session active.
        Never entered for the session being opened or loaded, or for a
        session holding an active write lock or an open bind. The victim is
        marked evicting under the cap lock; its victim lock is held from pick
        through save, drop and registry removal. Save runs outside the cap lock;
        the victim keeps its slot until dropped, and the open that picked it
        waits for this save.
        Atomic write: temp file in the same dir, fsync file, rename, fsync dir.
      */
    }
    transition active_to_evict_saving
      first active
      accept EvEvictForCap
      then evictSaving;
    transition evict_saving_to_closed
      first evictSaving
      accept EvEvictSaved
      then closed;
    transition evict_saving_to_active
      first evictSaving
      accept EvError
      then active;
  }

  // --- 2. Goldfish loop (engine side of turn) ---

  state def GoldfishLoop {
    doc /*
      TARGET goldfish: cue q → RelativeSeed → ShapeWalk → LLM sees X̃ →
      sparse Commit Δ (CREATE () legal; MERGE by labels+props; no NEW
      as TARGET). Empty q → SessionOutline census of S, then the agent
      picks a seen cue and pin_maps. Codebook miss → Peak_L last-resort
      then ShapeWalk (never default goldfish). leftover MutateWithNew is leftover
      0.9 only. leftover EvEmptySeedSkip is leftover 0.10 only.
    */
    entry;
    then awaitingCue;

    state awaitingCue {
      doc /* Idle between turns; next action is cue q into RelativeSeed. */
    }
    transition cue_to_seed
      first awaitingCue
      accept EvCue
      then seeding;
    transition cue_empty_outline
      first awaitingCue
      accept EvEmptyCue
      then outlining;
    transition leftover_pin_as_cue
      first awaitingCue
      accept EvPinMapRead
      then seeding;

    state seeding {
      doc /*
        RelativeSeed MATCH_L → Q of graph elements (not store-key ids).
        SHALL emit Q honestly when |Q| > 1. SHALL NOT absorb.
      */
    }
    transition seed_to_walk
      first seeding
      accept EvSeedReady
      then walking;
    transition leftover_seed_empty_skip
      first seeding
      accept EvEmptySeedSkip
      then awaitingCue;
    transition seed_miss_to_peak
      first seeding
      accept EvPeakL
      then peaking;
    transition seed_empty_to_outline
      first seeding
      accept EvEmptyCue
      then outlining;
    transition seed_error
      first seeding
      accept EvError
      then awaitingCue;

    state peaking {
      doc /*
        Peak_L typed residual local max of ρ* inside one S after MATCH_L
        miss. Not outline. Not default goldfish. Two peaks → CueConflict.
      */
    }
    transition peak_to_walk
      first peaking
      accept EvSeedReady
      then walking;
    transition peak_cue_conflict
      first peaking
      accept EvCueConflict
      then presenting;
    transition peak_empty_skip
      first peaking
      accept EvEmptySeedSkip
      then awaitingCue;
    transition peak_error
      first peaking
      accept EvError
      then awaitingCue;

    state walking {
      doc /*
        ShapeWalk k-hop from Q under one M; leftover require_anchor not TARGET.
        |Q| > 1 carries CueConflict on the emit.
      */
    }
    transition walk_to_present
      first walking
      accept EvShapeWalk
      then presenting;
    transition walk_cue_conflict
      first walking
      accept EvCueConflict
      then presenting;
    transition walk_via_pin_map
      first walking
      accept EvPinMapRead
      then presenting;
    transition walk_error
      first walking
      accept EvError
      then awaitingCue;

    state outlining {
      doc /*
        TARGET empty-q Recall of S: kinds catalog + LIMIT exemplars.
        Ask the session, not a node. SHALL NOT MATCH a seed, dump
        edges, absorb, or treat view=shell as this census.
      */
    }
    transition outline_to_present
      first outlining
      accept EvSessionOutline
      then presenting;
    transition outline_cue_conflict
      first outlining
      accept EvCueConflict
      then presenting;
    transition outline_error
      first outlining
      accept EvError
      then awaitingCue;

    state presenting {
      doc /*
        LLM sees X̃ (shaped subgraph) or the session outline census;
        may reason. After outline, pick one seen cue and pin_map.
        Same-name hits are candidates pointed out as CueConflict (two
        roots, not one merged node); agent MAY later Commit SameThingAbsorb.
      */
    }
    transition present_to_commit
      first presenting
      accept EvMutateGraph
      then applyingMutate;
    transition present_to_same_thing
      first presenting
      accept EvSameThingAbsorb
      then applyingMutate;
    transition present_to_settle_only
      first presenting
      accept EvSettleRecycle
      then settling;
    transition present_repeat_cue
      first presenting
      accept EvCue
      then seeding;
    transition present_error
      first presenting
      accept EvError
      then awaitingCue;

    state applyingMutate {
      doc /*
        TARGET Commit (no NEW). leftover MutateWithNew is leftover 0.9.
        SameThingAbsorb is a Commit rule here, not Recall.
      */
    }
    transition mutate_to_settle
      first applyingMutate
      accept EvSettleRecycle
      then settling;
    transition mutate_to_await_cue
      first applyingMutate
      accept EvCommitOk
      then awaitingCue;
    transition mutate_error
      first applyingMutate
      accept EvError
      then awaitingCue;

    state settling {
      doc /* HousekeepSettle recycle/prune; recyclable hidden on next ShapeWalk. */
    }
    transition settle_done
      first settling
      accept EvCue
      then seeding;
    transition settle_idle
      first settling
      accept EvCommitOk
      then awaitingCue;
  }

  // --- 3. leftover_NEW_mint (0.9 leftover; not TARGET GraphElement) ---

  state def MutateWithNew {
    doc /*
      Leftover 0.9 invented store path: GraphGlot parse -> product gate ->
      leftover lower -> leftover_NEW_mint (if any) -> schema check ->
      strict commit -> emit AssignedIdMap. TARGET create is CREATE () /
      CREATE (:Label {props}) with no mint law. Aligns leftover MN-REQ-03 /
      10.4 as-is engine. When the batch has no NEW / [NEW], minting is a
      no-op. TierA / Layer line codec parse is RETIRED on product path
      (M2 done).
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
      doc /* GraphGlot parse then MemNet product gate; reject invalid wire. */
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
        leftover_NEW_mint / leftover_by_id: IdAllocator replaces NEW /
        [NEW] with engine ids. TARGET has no this mint law. If the batch
        has no NEW tokens, skip allocation and emit an empty AssignedIdMap
        (EvIdsAssigned) then commit GraphElement only.
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

  // --- 4. Pin-map ingest (as-is domains) ---

  state def PinMapIngestCycle {
    doc /*
      Path-B MN-REQ-11 selective pin ingest. As-is: Sysml / Codebase /
      Path-B MN-REQ-11 selective pin ingest. As-is: Sysml / Codebase /
      PcbaAto / SkillsRules (#31 / #64). Catalog Snap (0.15) is a sibling
      transition from pinIdle (EvCatalogSnap → projecting); it SHALL NOT
      replace EvPinMapSelect → selectingPins. Not SnapshotStore. Pin-map
      export (0.19 / #66) is a separate cue GQL write-out — not this ingest
      cycle. MN-REQ-11.1 SysML file reverse remains later.
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
    transition pin_catalog
      first pinIdle
      accept EvCatalogSnap
      then projecting;

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
        TARGET Path-B: Commit create of GraphElement; locators (refdes, net,
        pin, path, qname, skill_id) are properties, not PK. Pattern match
        by labels+properties. leftover_allocate_from_locator / MERGE-by-id
        is leftover 0.9 engine, not a TARGET command (MN-REQ-07.5 / 11.16).
        Reject client NEW / [NEW] for source elements.
        Catalog Snap: plan interiors, pre-check budgets, then mint;
        on EvError or EvCallerGone close every session this call minted.
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
    transition project_caller_gone
      first projecting
      accept EvCallerGone
      then pinIdle;
  }

  // --- 5. Parent-owned MissionTaskPin lifecycle (TSK_*; MN-REQ-12.3) ---

  state def ParentTaskLifecycle {
    doc /*
      Lifecycle of one parent-owned MissionTaskPin (TSK_*) under Multitask.
      Applies only to relevant tasks (MN-REQ-12.8). Parent settles from
      shared-session pin map; workers do not own settle. Hosted by
      MultitaskCoordinator. As-is: CapsPolicy ACL who / pin_map-vs-mutate /
      WorkerWriteScope hard reject / optional SessionBind is shipped when
      session ACL is enabled (CapsPolicy.engineAclShipped=true; MN-REQ-12.7
      ACL cut). Neighbourhood reserve remains not shipped.
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
        CapsPolicy hard-rejects out-of-scope mutate when session ACL is
        enabled. Reserve/overlap coordination remains host doctrine
        (MN-REQ-12.7 — reserve is not shipped).
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
      Hosted by MultitaskOperatingModel. The shipped CapsPolicy ACL enforces
      who/permission/scope/bind when session ACL is enabled; RSV and
      all Path-B PinMapIngest_* domains shipped. Full ACL modes deferred.
      Trivial one-shots take
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
      SessionHandoff (SessionCapability sessionId + CallerId; optional
      missionId / lease / anchors / writeScope) → sink pin_map → mutate
      still hits the shipped CapsPolicy ACL when session ACL is enabled
      (who / pin_map-vs-mutate / scope / optional bind; engineAclShipped=true).
      Shared session = same id; else worker session → lead import_slice.
      sessionId MUST NOT dump in
      chat/queue. Contrasts forbidden EvDumpGraphInChat. Composes with
      EvDelegateWorker / MultitaskMissionCycle. Hosted by MultitaskOperatingModel.
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
        Source delivers SessionHandoff only — SessionCapability sessionId +
        CallerId (optional missionId / lease / anchors / writeScope).
        MUST NOT attach a graph dump; MUST NOT dump sessionId in chat/queue,
        MissionDock, or HTTP body.
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
      Path B: lead ImportAbsorb of member WorkingMemorySlice (optional
      ImportGuard nest: ImportGuardHook shipped; CheapLlmImportGuard shipped
      #63 → engine hard). Path A: EvSharedSessionRepin only — this import
      nest skipped. Product verb = import (SessionImport*). Chat never
      payload; whole-store dump forbidden. Hosted by MultitaskOperatingModel.
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
        Path A: shared mission sessionId. Lead pin_map only; member facts
        already in SSOT. No SessionImportRequest, no ImportGuard, no
        ImportAbsorb.
      */
    }
    transition path_a_pin_map
      first pathASharedRepin
      accept EvPinMapRead
      then pathASharedRepin;
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
        WorkingMemorySliceExport (engine hard): anchors required, slice
        budget, LAW/vocab excluded — not whole store. LLM MAY choose anchors.
      */
    }
    transition export_to_guard
      first pathBExporting
      accept EvGuardReviewSlice
      then pathBGuarding;
    transition export_to_absorb_skip_guard
      first pathBExporting
      accept EvGuardSkip
      then pathBImporting;
    transition export_fail
      first pathBExporting
      accept EvError
      then importIdle;

    state pathBGuarding {
      doc /*
        ImportGuard nest soft: ImportGuardHook (shipped) and/or optional
        CheapLlmImportGuard (shipped #63; env-gated). SoftScopeFit /
        SoftJunkTrim (subtractive) / SoftInventedId / SoftSizeNoise /
        SoftIdPolicyAdvice → SoftDecisionEmit. MUST NOT replace engine
        hard gates. Decision = structured atoms. EvGuardSkip →
        GuardPassthrough (skipping is valid).
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
        ImportAbsorb engine hard: DistinctSessionGate → AclConsultAbsorb →
        SchemaValidateImport → IdPolicyApply (keep|reject|remint) →
        NodesThenEdgesCommit; optional GuardDecisionAtomRecord.
        TARGET keep = labels+props / type+ends MERGE (pattern match);
        leftover_MERGE_by_id leftover, not a TARGET command; reject =
        labels+props match conflict, no mutate (leftover store-key
        id_conflict named leftover only); remint = leftover_NEW_mint, lead
        old stay, edges retarget — leftover engine, not TARGET command
        (MN-REQ-07.5 / 12.9).
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
        EvImportFromChat / graph-dump / ImportGuard reject / labels+props
        match conflict (leftover store-key id_conflict named leftover only).
        Recover via path A repin or path B bounded slice + allow/trim/skip.
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

  // --- 10. Durable buffer hydrate/flush (M2.5 client landed; live cabinet external) ---

  state def DurableHydrateFlushRoadmap {
    doc /*
      Landed client (name kept): SessionLifecycle.hydrate_from_durable /
      flush_to_durable via DurableSyncOwner and DurableStoreAdapter
      (FakeDurableAdapter always; optional AgensGraphAdapter client with
      liveCabinetClaimed). MemNet remains sole agent-facing
      memory; LLM ↔ DurableGraphStore direct (Bolt) is out of default
      teach. Client seam landed. 0.7 claim is adapter + operator round
      trip (no runtime caller) (MN-REQ-06.4). Neo4j cabinet is archived
      (#187). Do not wire a new hydrate/flush caller.
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

  // Neo4jLibraryLocatorRoadmap: models/archive.sysml (#187).

  // --- Extra 0.17: host Snap locators (outside MemNetSystem) ---

  state def HostSearchLocatorRoadmap {
    doc /*
      RagHostHook outside MemNetSystem. Cue → locators or skip.
      Commit via existing MutateGate / ingest. MUST NOT absorb.
      MUST NOT rag_query. MUST NOT Snap-on-session.
    */
    entry;
    then hostIdle;

    state hostIdle {
      doc /* Hook waiting; skip is the default when unset. */
    }
    transition idle_skip
      first hostIdle
      accept EvHostSearchSkip
      then hostIdle;
    transition idle_to_cue
      first hostIdle
      accept EvHostSearchCue
      then proposingLocators;

    state proposingLocators {
      doc /* Locator-only Snap of the library. Not pin_map. */
    }
    transition propose_skip
      first proposingLocators
      accept EvHostSearchSkip
      then hostIdle;
    transition propose_locators
      first proposingLocators
      accept EvHostSearchLocators
      then committingLocators;

    state committingLocators {
      doc /* Existing MutateGate / PinMapIngest. Not ImportAbsorb. */
    }
    transition commit_ok
      first committingLocators
      accept EvCommitOk
      then hostIdle;
    transition commit_fail
      first committingLocators
      accept EvError
      then hostIdle;
  }

  // ----- Atelier-board asks (MN-REQ-14; 14.9, 14.10, 14.11 implemented; others PROPOSAL) -----

  action def BoardWakeRead {
    doc /*
      PROPOSAL (MN-REQ-14.1 / 14.2 / 14.4; verify MN-VER-14-S01, S02). Board wake: MATCH rows WHERE
      toBot = $me AND rowRev > $since, ordered by rowRev, one page of at
      most the read cap (50, config.py:68). Today refused at gql.py:249-251
      (range) and by the cap (paging); the caller code path over internal
      indexes is outside the GQL contract. Steps: (1) parse range predicate
      (14.1); (2) resolve rows through the property/id index, not a full
      scan (14.4); (3) emit one page and, if more remain, a resume point
      (cursor or last rowRev; PARKED, 14.2); (4) caller repeats with the
      resume point until none. Typed directed walk to the ask (14.3,
      PARKED) is a separate optional step and is not part of the wake.
    */
    in item since : String;
    in item page : String;
    out item rows : String;
    out item resume : String;
  }

  action def SessionLoadLinear {
    doc /*
      PROPOSAL (MN-REQ-14.4 / 14.5; verify MN-VER-14-S04, S05). Snapshot load builds the record
      index once and resolves each edge end by lookup, so time is linear in
      records (today a hid set per edge end, mem_store.py:60, quadratic;
      31k records 34.9 s). The record cap (5,000 default, config.py:121)
      is raisable only after this action holds (14.5 depends on 14.4).
    */
    in item snapshotText : String;
    out item session : String;
  }

  action def IdMintAndRetire {
    doc /*
      PROPOSAL (MN-REQ-14.6; verify MN-VER-14-S06; target only). Write:
      mint a UUIDv7 (RFC 9562; no saved counter or pool; unique with high
      probability, not by construction); the id index refuses an id that is
      existing or tombstoned. Delete: tombstone the id (id-only entry),
      never reuse it. Lookup of a
      tombstoned id returns "deleted". Save, load and restore never mint
      or rewrite ids; id-less legacy links stay id-less.
    */
    in item record : String;
    out item id : String;
  }

  action def HandleResolve {
    doc /*
      PROPOSAL (MN-REQ-14.7; verify MN-VER-14-S07; target only). MCP-surface (LLM-facing) replies
      carry a handle, never the real id. Resolve maps handle to real id inside the
      engine; a bad, stale or deleted handle returns a clear error, never
      another record.
    */
    in item handle : String;
    out item record : String;
  }

  action def DeveloperIdLookup {
    doc /*
      PROPOSAL (MN-REQ-14.8; verify MN-VER-14-S08; target only). Developer / tool-integration
      surface, separate from the MCP surface: replies carry the stable real
      id, usable as an outside reference. Lookup of a retired id returns
      "deleted", never not_found and never another record.
    */
    in item id : String;
    out item record : String;
  }

  action def RangeWhereCompare {
    doc /*
      PROPOSAL (MN-REQ-14.1; verify MN-VER-14-S01; target only). WHERE
      p < | > | <= | >= $param. The comparison type comes from the
      parameter: string or number only (int and float compare as numbers;
      strings by code point); no coercion. A boolean or null operand, or a
      property whose type differs from the parameter, refuses the WHOLE
      statement with the new code type_mismatch (not
      unsupported_predicate) before any SET or DELETE write; nothing is
      written. A row without the property does not match. Literals only
      off the agent wire. rowRev is a 6-digit string, bounded at 999,999.
    */
    in item predicate : String;
    in item param : String;
    out item matched : String;
  }

  action def ValueLineCapEnforce {
    doc /*
      Implemented for the mutate gate (MN-REQ-14.9 / 14.10; verify
      MN-VER-14-S09, S10; tests tests/test_session_bytes_budget.py).
      Bypass paths: BypassPathCapEnforce. Fixed interface (owner t1443s8385). Caps: value cap
      MEMNET_MAX_VALUE_BYTES default 32,768 bytes; line cap
      MEMNET_MAX_LINE_BYTES default 4 x 32,768 + 4,096 = 135,168 bytes,
      because the worst-case wire escape is 4x (\x1c, \x1d, \x1e each
      become 4 bytes, wire.py _SPLITLINES_ESC) plus 4,096 bytes of
      framing. On write (mutate time), before storing: (1) a value over
      the value cap is refused limit_exceeded, message
      value_bytes|{n}/{max} (unchanged); (2) the escaped wire size
      (wire.py escape rules) of the whole record line as it would be saved,
      all fields (tag, field names, separators and every value after the
      write), is checked against the line cap, and over it the write is
      refused limit_exceeded, message line_bytes|{n}/{max}; a record whose
      fields each fit can still be refused here (tag_map.py:282-289 caps
      the whole physical line); the per-record bound is the line cap; (3) a write
      over the per-session byte budget (14.10) is refused
      limit_exceeded|session_bytes (event EvSessionBytesRefused). A refused write stores nothing, so no
      accepted write makes a snapshot unsaveable. On load: a snapshot with
      a value over the configured value cap is refused clearly (value_bytes);
      an older host (default 4,096) must raise MEMNET_MAX_VALUE_BYTES and
      MEMNET_MAX_LINE_BYTES before loading a newer snapshot.
    */
    in item record : String;
    out item accepted : String;
  }

  action def BypassPathCapEnforce {
    doc /*
      Implemented (MN-REQ-14.11; verify MN-VER-14-S11; tests
      tests/test_bypass_paths_caps.py). A write path that bypasses the
      mutate gate runs the same caps as ValueLineCapEnforce, with the same
      limit_exceeded codes, and is atomic. Paths and order:
      (1) snapshot import (import_absorb): value cap on the incoming
      records first, then the write under a checkpoint, then field cap,
      whole-line cap (record, edge and SCHEMA lines) and session byte
      budget on the result; (2) durable hydrate (durable/sync.py): same
      checks; a hydrate that leaves the session over budget, including a
      session already over a lowered MEMNET_MAX_SESSION_BYTES, is refused
      limit_exceeded|session_bytes, loads nothing, leaves durable data
      untouched, and the error names the setting to raise; (3) CLI delete
      and housekeep prune: no byte-budget check (a delete shrinks the
      session, as mutate deletes always go through), but every rewritten
      edge and SCHEMA line must pass the line cap, else the whole delete or
      prune is refused and nothing is removed; (4) snapshot load keeps the
      loader refusal of an over-cap value or line and refuses a snapshot
      over budget; snapshot save refuses an over-budget session and writes
      no file; ingest commits through the mutate gate. On any refusal the
      store, relations and indexes are restored to the entry state.
    */
    in item records : String;
    out item accepted : String;
  }

  action def WhereSetRefusalFix {
    doc /*
      Implemented (defect D02 fixed; verify MN-VER-14-D02; per MN-REQ-03.4
      honour-or-refuse). A WHERE on a relationship pattern combined with
      SET is honoured: the WHERE takes the same predicates as a node WHERE
      (=, AND, OR, NOT, parentheses) and the SET applies to exactly the
      relationships that match the pattern and the WHERE; nothing is
      deleted and non-matching relationships are unchanged. A shape that
      stays unsupported (for example a range comparison) is refused
      unsupported_predicate with a message naming the clause used (SET /
      WHERE, never DELETE), with no partial write.
    */
    in item statement : String;
    out item reply : String;
  }

  attribute def EvIdMinted {
    doc /* A UUIDv7 id accepted by the id index (MN-REQ-14.6). */
  }
  attribute def EvIdDeleted {
    doc /* Record deleted; its id becomes an id-only tombstone. */
  }
  attribute def EvIdRetired {
    doc /* Tombstone sealed in a saved snapshot; id retired forever. */
  }
  attribute def EvBytesWrite {
    doc /*
      An accepted write that changes the session's escaped snapshot line
      bytes: any write whose new total, after the whole mutate, is at or
      under the budget (newTotal <= budget; the code refuses only
      newTotal > budget). A refused write stores nothing and raises no
      EvBytesWrite. The guards on the state def pick the target state.
    */
    attribute newTotal : Integer;
  }
  attribute def EvBytesReachBudget {
    doc /*
      The total reaches the budget without a write. A load or hydrate over
      the budget is refused, so this event fires only when a load or hydrate
      lands exactly at the budget, or when MEMNET_MAX_SESSION_BYTES is
      lowered under a loaded total. EvBytesWrite and EvBytesReachBudget are
      disjoint by cause: a write is always EvBytesWrite, never this event.
    */
    attribute newTotal : Integer;
  }
  attribute def EvBytesFree {
    doc /* Bytes released (value shrunk or record deleted). */
    attribute newTotal : Integer;
  }
  attribute def EvSessionBytesRefused {
    doc /*
      A refusal limit_exceeded|session_bytes (MN-REQ-14.10). It is an
      observation only: atBudget is a function of the byte total, not of
      this event. Other refusals (type_mismatch, line_bytes, value_bytes;
      generic EvError) say nothing about the total.
    */
  }

  state def IdLifecycle {
    doc /*
      PROPOSAL (MN-REQ-14.6 / 14.4; verify MN-VER-14-S06; target only).
      Life of one real id: live -> tombstoned (deleted) -> retired. Ids
      are never reused: no transition leads back to live, and the id index
      refuses a write that names an existing or tombstoned id. Lookup of a
      tombstoned or retired id returns "deleted", never not_found and
      never another record. Save, load and restore never mint or rewrite
      ids.
    */
    entry;
    then live;

    state live {
      doc /* Record present; id in the id index. */
    }
    transition delete_to_tombstone
      first live
      accept EvIdDeleted
      then tombstoned;

    state tombstoned {
      doc /*
        Deleted: id-only tombstone (id + deleted marker) in the index and
        snapshot. Not counted against the record cap (14.5); counted toward
        the per-session byte budget (14.10).
      */
    }
    transition tombstone_to_retired
      first tombstoned
      accept EvIdRetired
      then retired;

    state retired {
      doc /* Terminal. The id is never reused or changed. */
    }
  }

  state def SessionByteBudgetStates {
    doc /*
      Implemented (MN-REQ-14.10, 14.11; verify MN-VER-14-S10, S11; tests
      tests/test_session_bytes_budget.py, tests/test_bypass_paths_caps.py).
      Per-session byte budget over escaped snapshot line bytes. Default
      163,840,000 bytes (DEFAULT_MAX_SESSION_BYTES). Setting:
      MEMNET_MAX_SESSION_BYTES. A write, load, import, hydrate or save that
      would put the total over the budget is refused
      limit_exceeded|session_bytes {n}/{max} and changes nothing. atBudget
      means the total is at or over the budget (a lowered setting can leave
      a loaded session over it); it does not mean that a refusal happened.
      One rule in every state: a delete skips only the budget check; the
      field and line caps still run. A write is accepted only if the new
      total ends at or under the budget (newTotal <= budget), otherwise it
      is refused session_bytes and nothing is stored. So a write passes only
      if its new total ends at or under the budget, even while the total is
      at or over the budget. A mutate that both deletes and writes is
      checked once, on the total after both: it is accepted if that
      total is at or under the budget, else the whole mutate is refused
      and neither the delete nor the write is stored. A write that lands
      exactly on the budget is accepted and leaves the session atBudget.
      newTotal is the total after the event; budget is the setting.
      The total is maintained incrementally (MN-REQ-14.12; verify
      MN-VER-14-S12).
    */
    attribute newTotal : Integer;
    attribute budget : Integer;

    entry;
    then underBudget;

    state underBudget {
      doc /* Total bytes < budget. */
    }
    transition write_within
      first underBudget
      accept EvBytesWrite
      if newTotal < budget
      then underBudget;
    transition write_lands_on_budget
      first underBudget
      accept EvBytesWrite
      if newTotal >= budget
      then atBudget;
    transition free_within
      first underBudget
      accept EvBytesFree
      then underBudget;
    transition write_reaches_budget
      first underBudget
      accept EvBytesReachBudget
      then atBudget;

    state atBudget {
      doc /*
        Total bytes >= budget. A delete skips only the budget check; the
        field and line caps still run. A write is accepted only if the new
        total ends at or under the budget, else it is
        refused session_bytes and stores nothing. The state returns to
        underBudget only when the new total is below the budget; a free or
        write that leaves the total at or over it stays atBudget.
      */
    }
    transition free_bytes
      first atBudget
      accept EvBytesFree
      if newTotal < budget
      then underBudget;
    transition write_fits
      first atBudget
      accept EvBytesWrite
      if newTotal < budget
      then underBudget;
    transition stay_at_budget
      first atBudget
      accept EvBytesFree
      if newTotal >= budget
      then atBudget;
    transition write_stays_at_budget
      first atBudget
      accept EvBytesWrite
      if newTotal >= budget
      then atBudget;
  }
}
