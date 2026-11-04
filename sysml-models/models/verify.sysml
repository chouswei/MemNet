/*
  MemNet verification cases — MN-REQ-12 Multitask Mode + session import +
  async parallel; MN-REQ-04.6 bounded MATCH find honesty; MN-REQ-13
  Recall/Commit two-operator cut. Aligned to
  outputs/multitask-case-study.md, outputs/session-import-case-study.md,
  outputs/async-parallel-conflict-case-study.md.
  Group parent MN-REQ-12: MN-VER-12-G00; leaves: S01–S14.
  Inspection / scenario verification against behaviour states and deploy
  doctrine parts; verifies the shipped CapsPolicy ACL cut while retaining
  no-assume checks for full ACL modes. CheapLlmImportGuard shipped
  (#63 / S14; env-gated). Path-B ingest domains + RSV are shipped.
  BoundedMatchFind shipped seed-only (MN-VER-04-S01 / #73).
  RelativeSeed codebook tokens then ShapeWalk (MN-VER-04-S02).
  Empty-q session outline is Recall census of S (MN-VER-04-S03).
  Peak_L last-resort residual cue (MN-VER-04-S04); never default goldfish.
  pin_map order from Shape observables, not hid (MN-VER-04-S05).
  GraphGlot parse front + product gate (MN-VER-09-S01).
  RecallCommit modelled (MN-VER-13-S01); leftover goldfish claimed in 0.5.
  SameThingAbsorb is a Commit rule (MN-VER-13-S02); Recall SHALL NOT absorb.
  DurableBuffer honesty (MN-VER-06-S01): Agens liveCabinetClaimed
  is adapter + operator round trip (no runtime caller);
  bindsExactlyOneOf=fake|agensgraph; Neo4j cabinet archived (#187);
  MEMNET_NEO4J_* ignored; RagHostHook.implemented=true required
  outside MemNetSystem (hostSearchInsideSystem stays false).
  Human usage look (MN-VER-06-S02): MemNetUsageDashboard look-only
  outside MemNetSystem; HTTP/UI parked; no manage/mutate ports.
  Device fleet (MN-VER-06-S03): MemNetOpsFleet outside MemNetSystem;
  device MemNetCoreLibrary services; one MemNet MCP (tip/ops) at the
  droplet (tip≠face); product invent face is sysmledge;
  nServerFederation=false (#47).
  SSOT-to-code allocate (MN-VER-06-S04): SoftwareAllocate maps
  logical parts to live modules; one Hatch wheel many hosts;
  sysmlEdgeInWheel=false; CousinSysMLEdge not in this repo.
  Tip access portal (MN-VER-06-S05): TipMemNetAccessPortal outside
  MemNetSystem; admin invite (Szu-Wei); Google login; Bearer for
  keyed tip MCP; unauthenticated WWW MemNet refused; tip≠face;
  not a sysmledge product; portal sidecar (portalWebImplemented=true;
  sellsInvent2Green=false).
  LAN MCP front (MN-VER-06-S07): MemNetLanMcpFront outside
  MemNetSystem; inventOnly #191; ClusterRoute (where the session
  lives); registry owner; one owner per session; pin_map / find
  SHALL NOT span backends; distinct from SliceHandCarry; no SemVer;
  tip≠face.
  ClusterRoute vs SliceHandCarry (MN-VER-06-S08): MemNetTwoMoves
  outside MemNetSystem; two named moves; slice is explicit copy
  not a live hop; import_slice same-serve only; inventOnly.
  Admin serve usage report (MN-VER-06-S09): AdminUsageReport on
  TcpServeBridge; admin credential; opaque alias; not agent MCP.
  Product gateway (MN-VER-06-S10): MemNetProductGateway on
  memnet-mcp; per-product sha256 credential; one owning serve;
  no mn_tip_ reuse; pass-through; implemented. Parent #191
  catalogue stays inventOnly.
  Safe serve upgrade (MN-VER-06-S12): SafeServeUpgrade on
  TcpServeBridge; admin drain; manifest; startup restore;
  retire after a clean restore (audit mark; a later restart
  still restores); no client retry; no silent session loss;
  no SemVer bump.
  Restart restore (MN-VER-06-S15): SafeUpgradeMod; newest valid
  set of checkpoint and upgrade-prepare, tie to upgrade; retired
  stays a candidate; pre-flight; @WARN: restore_fallback; none
  valid exits 3; @STAT: restore_source. Runtime:
  tests/test_restart_restore.py.
  memnet-mcp extra (MN-VER-06-S16): McpServerMod; console
  memnet_mcp.entry:main; one line mcp_extra_missing, exit 2, every
  transport and --help. Runtime: tests/test_mcp_extra_missing.py.
  Atelier-board asks (MN-VER-14-S01..S12; S01, S03, S04 and S09 to S12 implemented with
  runtime tests, the rest PROPOSAL, target only, model-level, never
  counted as verified):
    MN-REQ-14.1 WHERE range, never on id, implemented (S01)
    14.2 paged reads, PARKED (S02)
    14.3 typed directed walks (query typed-walk), implemented (S03)
    14.4 nickname id index + linear load, implemented (S04)
    14.5 raisable record cap, depends on 14.4 (S05)
    14.6 id design (S06)
    14.7 MCP surface handles only (S07)
    14.8 developer surface real ids (S08)
    14.9 value cap 32,768 bytes + line cap 135,168 (S09)
    14.10 per-session total-bytes cap (S10)
    14.11 bypass-path caps: import, hydrate; CLI delete/prune line cap only (S11)
    14.12 incremental byte-budget check, total equal to a full recount (S12)
  Defect records:
    MN-VER-14-D01 two-step walk up to about 42% slower, ee36a95 to bb4a4dc
    MN-VER-14-D02 WHERE on a relationship with SET refused with a DELETE message (FIXED)
  Session cap LRU evict (MN-VER-05-S03..S09, shipped, unreleased):
  MN-REQ-05.5 — oldest-touch pick; save first then drop; skip
  unsaveable; none evictable refuses limit_exceeded (all sessions are in
  use); self, write-locked and open-bind exempt; name not mn_ id on admin
  serve_status only; later load restores: same ACL, no lease carried over
  (@SNAP v2). Runtime: tests/test_session_evict.py (no xfail).
  Serve checkpoint (MN-VER-06-S13): ServeCheckpoint on
  TcpServeBridge; admin credential; per-session lock; lossless
  atomic snaps; skip unsaveable; no drain; no live load; no
  SemVer bump.
  Snapshot ACL (MN-VER-06-S14): SnapshotStore / SnapshotAcl; #@ACL:
  line after @SNAP version 2; version 2 without the line fails
  bad_snapshot; version 1 loads ACL off with @ACL: absent|off;
  malformed fails closed; bind stores a SHA-256 digest only; bind lease
  not printed; snapshot and manifest files mode 0600; first v2 write
  over v1 keeps <file>.v1.bak once (0600), no dual write; no SemVer bump.
  Optional id nickname TARGET (MN-VER-02-S01): GraphElement identity;
  CREATE () legal; HiddenStoreHandle off-wire; 0.9 leftover_by_id store.
  TARGET command list cue/pattern only (MN-VER-07-S01): no required-id
  tools on McpFacade / CliFacade; leftover id commands stay leftover_*.
  Cousin pointing contrast (MN-VER-02-S02): TARGET vs eight cousins
  (including SysMLEdge as a distinct pin_map / desk, not MemNet strata;
  overlay family SysMLEdgePrj-*; git sysml-models/ is SSOT);
  operatorCount stays 2; cousin nest cousinNestOwnsLiveNeo4jClaim stays false.
  Catalog model Snap (MN-VER-11-S17): package interiors; look = pin_map;
  grain not per-leaf; budget pre-check; caller-gone rollback; replace.
  Expire session_save (MN-VER-01-S03): configurable; default off; RAM
  drops; file until user drop; load restores; not Neo4j.
  Snapshot lossless round-trip (MN-VER-01-S04): emit escapes LF/CR;
  fail-closed save; 0.19.18 snapshots still load; mutate field cap.
  Session save/load/close ACL who (MN-VER-01-S05) when session ACL on.
  Honour WHERE or refuse (MN-VER-03-S01).
  Consistent decoded value_bytes cap (MN-VER-05-S01).
  Consistent effective-field cap (MN-VER-05-S02): default 64;
  mutate refuses over-cap; save uses the same helper.
*/
package MemNetVerification {
  private import ScalarValues::*;
  private import MemNetRequirements::*;
  private import MemNet::*;
  private import MemNetBehaviour::*;
  private import MemNetConnections::*;
  private import MemNetCousinContrast::*;
  private import MemNetImplementation::*;

  // --- MN-REQ-12 verification (group G00 + case-study steps S01–S09) ---

  verification def MN_VER_12_G00_MultitaskModeGroup {
    doc /*
      Organisational parent MN-REQ-12 — Multitask Mode group.
      Composite inspection: MultitaskOperatingModel (coordinator,
      workerPool, sharedStore) carries doctrineAsIs; deploy satisfy covers
      leaves 12.1–12.12; behaviour hosts ParentTaskLifecycle,
      WorkerScopedTurn, MultitaskMissionCycle, AsyncTaskDispatch.
      Step-level leaf coverage: MN-VER-12-S01…S14.
      CapsPolicy ACL is shipped when session ACL is enabled; RSV and
      all Path-B PinMapIngest_* domains shipped (12.7; see S09). Full
      private/shared/open + session_token modes deferred. ImportGuardHook
      shipped (S12); CheapLlmImportGuard adapter shipped (S14 / #63) —
      env-gated; hook alone was never 12.11 done.
    */
    attribute verificationId : String = "MN-VER-12-G00";

    subject multitask : MultitaskOperatingModel;

    objective groupMultitaskMode {
      verify multitaskModeReq;
      require constraint {
        multitask.coordinator.doctrineAsIs == true
          and multitask.workerPool.doctrineAsIs == true
          and multitask.sharedStore.doctrineAsIs == true
          and multitask.sharedStore.prefersTcpOrHttp == true
      }
    }
  }

  verification def MN_VER_12_S01_RelevanceGate {
    doc /*
      Case-study step 1 — Relevance (MN-REQ-12.8).
      Parent judges work multi-step and delegated; Multitask applies.
      MultitaskMissionCycle: missionIdle → parentPreparing via EvOpenSession
      or EvLoadSnapshot; SHALL NOT rely on EvTrivialSingleAgent (contrast
      GoldfishLoop for trivial one-shots).
    */
    attribute verificationId : String = "MN-VER-12-S01";

    subject multitask : MultitaskOperatingModel;

    objective step01Relevance {
      verify appliesToRelevantTasksReq;
      require constraint {
        true
      }
    }
  }

  verification def MN_VER_12_S02_SharedStoreTransport {
    doc /*
      Case-study step 2 — Shared store (MN-REQ-12.2).
      Parent and worker bind MCP via TcpServeBridge / ServeBridge
      (MEMNET_MCP_TRANSPORT=tcp) or streamable-http — not isolated
      in-process. MultitaskMissionCycle.parentPreparing; subject
      MultitaskSharedStoreBinding.prefersTcpOrHttp.
    */
    attribute verificationId : String = "MN-VER-12-S02";

    subject sharedStore : MultitaskSharedStoreBinding;

    objective step02SharedStore {
      verify sharedStoreTransportReq;
      require constraint {
        sharedStore.prefersTcpOrHttp == true
      }
    }
  }

  verification def MN_VER_12_S03_SharedSessionPinMap {
    doc /*
      Case-study step 3 — Shared session + pin_map (MN-REQ-12.1, MN-REQ-04.1).
      session_open / load one mission session; parent EvPinMapRead in
      parentPreparing. Chat is not mission SSOT (extends MN-REQ-10.1).
      Nickname id as pin_map anchor remains optional (MN-REQ-02.8 / 04.1).
    */
    attribute verificationId : String = "MN-VER-12-S03";

    subject coordinator : MultitaskCoordinator;

    objective step03SessionPinMap {
      verify sharedSessionMissionSsotReq;
      verify anchoredPinMapReq;
      require constraint {
        coordinator.doctrineAsIs == true
      }
    }
  }

  verification def MN_VER_12_S04_MintParentTask {
    doc /*
      Case-study step 4 — Mint parent task (MN-REQ-12.3).
      Parent EvMintParentTask → ParentTaskLifecycle.taskMinted;
      MissionTaskPin (TSK_*) status=active in shared session.
    */
    attribute verificationId : String = "MN-VER-12-S04";

    subject coordinator : MultitaskCoordinator;
    item taskPin : MissionTaskPin;

    objective step04MintTask {
      verify parentOwnsTaskLifecycleReq;
      require constraint {
        true
      }
    }
  }

  verification def MN_VER_12_S05_ScopeDelegateEndTurn {
    doc /*
      Case-study step 5 — Assign scope, delegate, end turn
      (MN-REQ-12.4, MN-REQ-12.5, MN-REQ-12.6, MN-REQ-12.12).
      EvAssignWorkerScope → taskScoped; EvDelegateWorker → taskDelegated /
      workersDelegated; EvEndCoordinatorTurn (AsyncTaskDispatch); parent
      ends turn (no same-turn poll). Prefer one worker; parallel only with
      disjoint WorkerWriteScope or separate sessions.
    */
    attribute verificationId : String = "MN-VER-12-S05";

    subject multitask : MultitaskOperatingModel;
    item writeScope : WorkerWriteScope;

    objective step05ScopeDelegate {
      verify workerPinMapAndScopedWriteReq;
      verify preferOneWorkerOrDisjointReq;
      verify parentEndTurnNoPollReq;
      require constraint {
        true
      }
    }
  }

  verification def MN_VER_12_S06_WorkerScopedTurn {
    doc /*
      Case-study step 6 — Worker turn (MN-REQ-12.4).
      WorkerScopedTurn: workerAwaitingPinMap → workerPresentingPinMap →
      workerApplyingScopedMutate → workerTurnDone; same session id;
      pin_map first; mutate under WorkerWriteScope; no parent TSK settle.
    */
    attribute verificationId : String = "MN-VER-12-S06";

    subject worker : MultitaskWorker;
    item writeScope : WorkerWriteScope;

    objective step06WorkerTurn {
      verify workerPinMapAndScopedWriteReq;
      require constraint {
        worker.doctrineAsIs == true
      }
    }
  }

  verification def MN_VER_12_S07_ParentReconcile {
    doc /*
      Case-study step 7 — Parent reconcile (MN-REQ-12.1, MN-REQ-12.6).
      workersDelegated → parentReconciling via EvPinMapRead / EvWorkerReturn;
      ParentTaskLifecycle.taskReconciling; act from shared-session slice;
      no redo of worker investigation from chat.
    */
    attribute verificationId : String = "MN-VER-12-S07";

    subject coordinator : MultitaskCoordinator;

    objective step07ParentReconcile {
      verify sharedSessionMissionSsotReq;
      verify parentEndTurnNoPollReq;
      require constraint {
        true
      }
    }
  }

  verification def MN_VER_12_S08_SettleMissionTask {
    doc /*
      Case-study step 8 — Settle (MN-REQ-12.3).
      Parent EvSettleMissionTask → taskSettled / missionComplete from
      shared-session pin-map facts; worker MUST NOT settle parent TSK_*
      unless explicitly delegated.
    */
    attribute verificationId : String = "MN-VER-12-S08";

    subject coordinator : MultitaskCoordinator;
    item taskPin : MissionTaskPin;

    objective step08Settle {
      verify parentOwnsTaskLifecycleReq;
      require constraint {
        true
      }
    }
  }

  verification def MN_VER_12_S09_NoAssumeReserveIngest {
    doc /*
      MN-REQ-12.7 gate — CapsPolicy ACL, NeighbourhoodReserve (RSV), and
      all Path-B PinMapIngest_* domains (Sysml/Codebase/PcbaAto/SkillsRules)
      are shipped. Agents must not assume full private/shared/open
      session_token modes, nor treat ingest as export/round-trip (#66).
      Inspection: RSV implemented == true; PinMapRoadmap domain engines
      implemented == true / roadmapOnly == false. Counter-example: treating
      full ACL modes or export as available violates MN-REQ-12.7.
    */
    attribute verificationId : String = "MN-VER-12-S09";

    subject multitask : MultitaskOperatingModel;

    objective step09NoAssumeShipped {
      verify noAssumeAclReserveIngestReq;
      require constraint {
        multitask.coordinator.doctrineAsIs == true
          and multitask.workerPool.doctrineAsIs == true
          and multitask.coordinator.dispatch.doctrineAsIs == true
          and multitask.coordinator.handoffEmit.caps.engineAclShipped == true
          and multitask.coordinator.handoffEmit.caps.doctrineAsIs == false
      }
    }
  }

  verification def MN_VER_12_S10_SharedSessionReceive {
    doc /*
      Path A (MN-REQ-12.9): shared mission sessionId → lead pin_map only
      (EvSharedSessionRepin / pathASharedRepin). No WorkingMemorySlice, no
      ImportGuard, no ImportAbsorb.
    */
    attribute verificationId : String = "MN-VER-12-S10";

    subject coordinator : MultitaskCoordinator;

    objective step10SharedReceive {
      verify leadOwnsSessionImportReq;
      verify sharedSessionMissionSsotReq;
      require constraint {
        coordinator.doctrineAsIs == true
      }
    }
  }

  verification def MN_VER_12_S11_SeparateSessionImport {
    doc /*
      Path B — separate sessions → ImportAbsorb (MN-REQ-12.9 / 12.10).
      Lead SessionImportRequest; WorkingMemorySliceExport; optional
      ImportGuard; ImportAbsorb IdPolicyApply keep|reject|remint; settle
      TSK_*. Forbidden EvImportFromChat / whole-store dump. Nested hard
      leaves: DistinctSessionGate, AclConsultAbsorb, SchemaValidateImport,
      LawVocabExclude, NodesThenEdgesCommit.
    */
    attribute verificationId : String = "MN-VER-12-S11";

    subject multitask : MultitaskOperatingModel;
    item importReq : SessionImportRequest;
    item slice : WorkingMemorySlice;

    objective step11SeparateImport {
      verify leadOwnsSessionImportReq;
      verify noChatOrWholeStoreImportReq;
      require constraint {
        multitask.coordinator.doctrineAsIs == true
          and multitask.coordinator.importReceive.absorb.gateKind == "hard"
          and multitask.coordinator.importReceive.absorb.'actor' == "engine"
          and multitask.coordinator.importReceive.absorb.implemented == true
          and multitask.coordinator.importReceive.absorb.idPolicy.keep.idPolicy
            == "keep"
          and multitask.coordinator.importReceive.absorb.idPolicy.reject.idPolicy
            == "reject"
          and multitask.coordinator.importReceive.absorb.idPolicy.remint.idPolicy
            == "remint"
      }
    }
  }

  verification def MN_VER_12_S12_ImportGuardHook {
    doc /*
      ImportGuardHook under SessionImportReceive / ImportGuard — shipped
      host plug-in (#49): set_import_guard / --no-guard / enable_guard;
      GuardPassthrough when skipped (skipping is valid); soft nest before
      ImportAbsorb hard. Soft vocabulary leaves present (subtractive trim).
      MUST NOT replace hard gates. This case PASSES the hook only.
      CheapLlmImportGuard / MN-REQ-12.11 adapter is verified separately
      by MN-VER-12-S14 (#63). Subject:
      MultitaskOperatingModel.coordinator.importReceive.guard.
    */
    attribute verificationId : String = "MN-VER-12-S12";

    subject multitask : MultitaskOperatingModel;
    item decision : ImportGuardDecision;

    objective step12ImportGuardHook {
      verify noChatOrWholeStoreImportReq;
      require constraint {
        multitask.coordinator.importReceive.guard.costTier == "cheap"
          and multitask.coordinator.importReceive.guard.gateKind == "soft"
          and multitask.coordinator.importReceive.guard.hook.implemented
            == true
          and multitask.coordinator.importReceive.guard.hook.passthrough
            .skipped == true
          and multitask.coordinator.importReceive.guard.junkTrim.trimMode
            == "subtractive"
          and multitask.coordinator.importReceive.absorb.gateKind == "hard"
          and multitask.coordinator.importReceive.absorb.implemented == true
      }
    }
  }

  verification def MN_VER_12_S14_CheapLlmImportGuard {
    doc /*
      MN-REQ-12.11 — CheapLlmImportGuard optional default adapter inside
      memnet-llm (GitHub issue #63). Honesty gate: cheapLlm.implemented
      == true after adapter ship. OPTIONAL / host MAY skip (--no-guard /
      GuardPassthrough / no API key); does not vendor a model; returns
      ImportGuardDecision only; engine MUST still hard-gate. Hook shipped
      (#49 / S12) is separate from this adapter. Cite #63.
    */
    attribute verificationId : String = "MN-VER-12-S14";

    subject multitask : MultitaskOperatingModel;
    item decision : ImportGuardDecision;

    objective step14CheapLlmImportGuard {
      verify cheapLlmImportGuardSoftReq;
      require constraint {
        multitask.coordinator.importReceive.guard.cheapLlm.implemented
          == true
          and multitask.coordinator.importReceive.guard.cheapLlm
            .optionalSoftPolicy == true
          and multitask.coordinator.importReceive.guard.cheapLlm
            .offUnlessEnvSet == true
          and multitask.coordinator.importReceive.guard.cheapLlm
            .vendorsModel == false
          and multitask.coordinator.importReceive.guard.cheapLlm.costTier
            == "cheap"
          and multitask.coordinator.importReceive.guard.hook.implemented
            == true
          and multitask.coordinator.importReceive.absorb.gateKind == "hard"
      }
    }
  }

  verification def MN_VER_12_S13_AsyncParallelDisjoint {
    doc /*
      Async-parallel case study — happy path + anti (MN-REQ-12.5 / 12.6 /
      12.12). Happy: two WorkerPool members with disjoint WorkerWriteScope
      (or separate sessions); EvDelegateWorker x2; EvEndCoordinatorTurn;
      both EvWorkerReturn (host-driven); lead EvPinMapRead / optional
      SessionImportReceive. Anti: overlapping anchors on one session —
      EvOverlapScopeForbidden / MUST NOT dual-write. The shipped CapsPolicy
      ACL hard-rejects an individual out-of-scope mutate when session ACL is
      enabled; no neighbourhood reserve coordinates overlapping writers.
      Subjects: AsyncTaskDispatch, WorkerPool. See
      outputs/async-parallel-conflict-case-study.md.
    */
    attribute verificationId : String = "MN-VER-12-S13";

    subject multitask : MultitaskOperatingModel;
    item writeScope : WorkerWriteScope;

    objective step13AsyncParallel {
      verify preferOneWorkerOrDisjointReq;
      verify parentEndTurnNoPollReq;
      verify hostDrivenAsyncParallelReq;
      require constraint {
        multitask.coordinator.dispatch.allowsParallelWhenDisjointOrSeparate
          == true
          and multitask.coordinator.dispatch.doctrineAsIs == true
          and multitask.workerPool.doctrineAsIs == true
      }
    }
  }

  verification def MN_VER_09_S01_GraphGlotParseThenGate {
    doc /*
      MN-REQ-09.5 — GraphGlot is the official-grammar parse front (implemented
      only because Python calls graphglot). ProductGqlGate is a separate part
      after parse (WITH / UNWIND / CALL / unbounded RETURN / Layer). No TCK
      claim. Product gate still after parse. Neo4j cabinet stays
      archived (#187); this cut does not restore it. Recall/Commit still
      two operators. RagHostHook stays outside MemNetSystem. Peak_L stays
      last-resort under RelativeSeed only. Hid / elementId /
      _memnet_hid stay off CLI/MCP/GQL emit.
    */
    attribute verificationId : String = "MN-VER-09-S01";

    subject system : MemNetSystem;
    subject ragHostHook : RagHostHook;

    objective parseFrontThenGate {
      verify graphglotParseThenProductGateReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.gqlWire.parseFront
          .implemented == true
          and system.core.transport.inProcess.memory.sessions.gqlWire
            .productGate.implemented == true
          and system.core.transport.inProcess.memory.sessions.gqlWire
            .productGate.rejectFreeWith == true
          and system.core.transport.inProcess.memory.sessions.gqlWire
            .productGate.rejectUnwind == true
          and system.core.transport.inProcess.memory.sessions.gqlWire
            .productGate.rejectCall == true
          and system.core.transport.inProcess.memory.sessions.gqlWire
            .productGate.rejectUnboundedReturn == true
          and system.core.transport.inProcess.memory.sessions.gqlWire
            .productGate.rejectLayer == true
          and system.durable.retiredNeo4jEnvIgnored == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .operatorCount == 2
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .hostSearchInsideSystem == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.lastResort == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.defaultGoldfish == false
          and ragHostHook.implemented == true
          and ragHostHook.locatorOnly == true
      }
    }
  }

  // --- MN-REQ-04.6 bounded MATCH find honesty (#73) ---

  verification def MN_VER_04_S01_BoundedMatchFindNotShipped {
    doc /*
      MN-REQ-04.6 — BoundedMatchFind is shipped as seed-only find
      (CLI query find / MCP find; hard LIMIT; shaped nodes, no RETURN).
      pinMap remains default goldfish after a cue/pattern seed; nickname
      id as --anchor is leftover 0.9 (MN-REQ-02.8). MUST NOT treat
      find as pin_map k-hop. Pin-map Multitask verify MN-VER-12-S03 is
      unchanged.
    */
    attribute verificationId : String = "MN-VER-04-S01";

    subject system : MemNetSystem;

    objective findNotShipped {
      verify boundedMatchFindReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.recallCommit
          .recall.shapedRead.find.implemented == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.find.limitRequired == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.find.allowTabularReturn == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.find.variableLengthPathDefault == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.implemented == true
      }
    }
  }

  verification def MN_VER_04_S02_RelativeSeedWalksFromQ {
    doc /*
      MN-REQ-04.7 — RelativeSeed MATCH_L yields walk-root graph elements
      Q; ShapeWalk walks from Q under one M. requireStoreKeyAnchor=false;
      inventOnEmpty=false. Empty q is SessionOutline (emptyCueIsOutline);
      leftover_empty_seed_skip is leftover, not TARGET.       leftover copy-id /
      require_anchor is leftover. operatorCount stays 2. Neo4j cabinet
      stays archived (#187; not this RelativeSeed cut).
    */
    attribute verificationId : String = "MN-VER-04-S02";

    subject system : MemNetSystem;

    objective relativeSeedThenShapeWalk {
      verify relativeSeedThenShapeWalkReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.recallCommit
          .recall.seed.seedsAreWalkRoots == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.requireStoreKeyAnchor == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.inventOnEmpty == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.emptySeedSkip == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.emptyCueIsOutline == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.leftoverEmptySkipProductCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.cueByLabelsAndProps == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.cueByKeyword == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.hardLimit == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.notStoreKey == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.notEmbedding == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.queryIsTokens == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.tokenKind == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.tokenProps == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.tokenKeyword == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.tokenNicknameOptional == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peakLDefault == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.defaultGoldfish == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.implemented == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.defaultGoldfish == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.notAThirdOperator == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.seed.seedsAreWalkRoots == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.seed.requireStoreKeyAnchor == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.walk.requireStoreKeyAnchor == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.walk.unionUnderOneM == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.walk.goldfishBudgetTimesAnchors == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.find.seed.seedsAreWalkRoots == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.walk.requireStoreKeyAnchor == false
          and system.core.cli.find.seed.requireStoreKeyAnchor == false
          and system.core.cli.pinMap.walk.requireStoreKeyAnchor == false
          and system.mcp.tools.find.seed.requireStoreKeyAnchor == false
          and system.mcp.tools.pinMap.walk.requireStoreKeyAnchor == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .operatorCount == 2
          and system.durable.retiredNeo4jEnvIgnored == true
      }
    }
  }

  verification def MN_VER_04_S03_SessionOutlineEmptyCue {
    doc /*
      MN-REQ-04.9 — empty q is Recall census of S (teach name outline).
      Join session id; ask the session, not a node. kinds + LIMIT
      exemplars; Browser-shaped. leftover skip is leftover
      (productCommand=false). MUST NOT: MATCH seed node; dump edges;
      absorb; view=shell as outline; MATCH-all; RAG/HostSearch;
      getAllPages; Pattern C/D; required property id; elementId on
      wire; third operator; SameThingAbsorb this cut; Layer.
      Outline SHALL NOT own the live Neo4j claim (0.14 product flag
      is separate). Engine not claimed (implemented=false).
    */
    attribute verificationId : String = "MN-VER-04-S03";

    subject system : MemNetSystem;

    objective emptyCueIsOutlineCensus {
      verify sessionOutlineEmptyCueReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.recallCommit
          .operatorCount == 2
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.emptyCueIsOutline == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.emptySeedSkip == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.implemented == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.notAThirdOperator == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.asksSessionNotNode == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.noMatchSeedNode == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.kindsCatalog == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.realExemplars == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.actualLabelsAndProps == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.oneHardLimit == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.dumpEdges == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.dumpS == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.absorbOnOutline == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.viewShellIsOutline == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.matchAll == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.ragSearch == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.hostSearch == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.getAllPages == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.patternCPrecomputedTour == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.patternDSeededRag == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.requiredPropertyId == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.elementIdOnWire == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.cueConflictIfExemplarNameCollides == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.twoRootsStayTwo == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.afterOutlinePickCueThenPinMap == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.leftoverEmptySkipProductCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.leftoverEmptySkipTargetImplemented == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.emptyCueIsOutline == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.viewShellIsOutline == false
          and system.core.cli.pinMap.emptyCueIsOutline == true
          and system.core.cli.pinMap.viewShellIsOutline == false
          and system.core.cli.emptyCueIsOutline == true
          and system.core.cli.leftoverEmptySeedSkipCommandNested == false
          and system.mcp.tools.emptyCueIsOutline == true
          and system.mcp.tools.leftoverEmptySeedSkipCommandNested == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.implemented == false
          and system.durable.retiredNeo4jEnvIgnored == true
      }
    }
  }

  verification def MN_VER_04_S04_PeakLLastResort {
    doc /*
      MN-REQ-04.10 — Peak_L last-resort residual cue under RelativeSeed
      only (not a sibling under Recall / AgentShapedRead /
      PinMapShapedRead). implemented=true (engine path).
      defaultGoldfish=false. Codebook miss only; empty q stays outline.
      ρ* not raw contains degree. Two peaks CueConflict. Not a third
      operator. operatorCount stays 2. Neo4j cabinet stays archived
      (#187; not this Peak cut). Peak_L is this verification's subject,
      not HostSearch. RagHostHook.implemented=true outside MemNetSystem
      (0.17 law); hostSearchInsideSystem=false.
    */
    attribute verificationId : String = "MN-VER-04-S04";

    subject system : MemNetSystem;

    objective peakLIsLastResortCue {
      verify peakLLastResortReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.recallCommit
          .operatorCount == 2
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .hostSearchInsideSystem == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.implemented == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.notAThirdOperator == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.lastResort == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.codebookMissOnly == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.emptyQIsOutline == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.defaultGoldfish == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.residualRhoStar == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.notRawContainsDegree == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.notNestFix == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.notDensityPeakCluster == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.notLeidenFromPeaks == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.notGlobalTopKDegree == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.cueConflictOnTwoPeaks == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.absorbs == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.silentMergeByName == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peak.elementIdOnWire == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.peakLDefault == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.defaultGoldfish == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.emptyCueIsOutline == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.defaultGoldfish == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.codebookMissOnly == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.defaultGoldfish == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.codebookMissOnly == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.defaultGoldfish == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.codebookMissOnly == true
          and system.durable.retiredNeo4jEnvIgnored == true
      }
    }
  }

  verification def MN_VER_04_S05_PinMapOrderFromObservables {
    doc /*
      MN-REQ-04.11 — pin_map sequence is a function of Shape observables
      (kind + payload). HiddenStoreHandle is not a ranking key and stays
      off the wire. Nickname id is not a ranking key. CREATE order is not
      a ranking key. Still two operators; do not raise M; no rag_query.
      Pytest: isomorphic sessions (shuffled CREATE / shuffled nicknames)
      cue by kind + locator slug; canonicalised pin_map sequences match.
    */
    attribute verificationId : String = "MN-VER-04-S05";

    subject system : MemNetSystem;

    objective pinMapOrderFromObservables {
      verify pinMapOrderFromObservablesReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.store
          .hiddenHandleIsRankingKey == false
          and system.core.transport.inProcess.memory.sessions.store
            .nicknameIdIsRankingKey == false
          and system.core.transport.inProcess.memory.sessions.store
            .createOrderIsRankingKey == false
          and system.core.transport.inProcess.memory.sessions.store
            .hiddenHandleOnWire == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.rankingIndependentOfHid == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.rankingIndependentOfNicknameId == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.rankingIndependentOfCreateOrder == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.hiddenHandleIsRankingKey == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.nicknameIdIsRankingKey == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.walk.rankingIndependentOfHid == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .operatorCount == 2
      }
    }
  }

  verification def MN_VER_02_S01_IdNotRequiredOnWire {
    doc /*
      MN-REQ-02.8 — GraphElement is identity. CREATE () is legal;
      properties() MAY be empty. MATCH/MERGE = labels + properties;
      edge = type + end elements. NicknameIdProperty optional.
      HiddenStoreHandle is not a property, not on the wire, not a
      business key. SHALL NOT invent a replacement application store key.
      TARGET flags: graphElementIsIdentity; emptyCreateLegal;
      propertiesMayBeEmpty; hiddenHandleIsProperty=false;
      hiddenHandleOnWire=false; hiddenHandleIsBusinessKey=false;
      noReplacementStoreKey; mergeIsPerWriteLookup; requiredIdProperty=false;
      requireAnchorId=false; createRequiresId=false; idFirstRequired=false;
      IdAllocator.implemented=false. Honesty leftover: leftoverByIdIndex
      (leftover_by_id), leftoverRequireAnchor, leftoverIdFirst,
      leftoverNewMint, leftover_ingestIsIdRule. Neo4j cabinet stays
      archived (#187). No IdentityHandle nest —
      leftover named parts beside flags. Recall/Commit nest not
      thickened. Hid stays off the wire.
    */
    attribute verificationId : String = "MN-VER-02-S01";

    subject system : MemNetSystem;

    objective idNotRequired {
      verify idNotRequiredOnWireReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.store
          .requiredIdProperty == false
          and system.core.transport.inProcess.memory.sessions.store
            .graphElementIsIdentity == true
          and system.core.transport.inProcess.memory.sessions.store
            .emptyCreateLegal == true
          and system.core.transport.inProcess.memory.sessions.store
            .propertiesMayBeEmpty == true
          and system.core.transport.inProcess.memory.sessions.store
            .hiddenHandleIsProperty == false
          and system.core.transport.inProcess.memory.sessions.store
            .hiddenHandleOnWire == false
          and system.core.transport.inProcess.memory.sessions.store
            .hiddenHandleIsBusinessKey == false
          and system.core.transport.inProcess.memory.sessions.store
            .noReplacementStoreKey == true
          and system.core.transport.inProcess.memory.sessions.store
            .mergeIsPerWriteLookup == true
          and system.core.transport.inProcess.memory.sessions.store
            .leftoverByIdIndex == true
          and system.core.transport.inProcess.memory.sessions.schema
            .idFirstRequired == false
          and system.core.transport.inProcess.memory.sessions.schema
            .leftoverIdFirst == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.requireAnchorId == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.leftoverRequireAnchor == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.createRequiresId == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mergeByLabelsAndProps == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.leftoverNewMint == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.ingestIsIdRule == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.leftoverIngestIdRule == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.implemented == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.leftoverAsIsEngine == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.teachHiddenStorageHandle == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mergeIsPerWriteLookup == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.noReplacementStoreKey == true
          and system.durable.mergeIsPerWriteLookup == true
          and system.durable.noReplacementStoreKey == true
          and system.durable.retiredNeo4jEnvIgnored == true
          and system.pinMaps.'interface'.leftoverLocatorMint == true
          and system.multitask.coordinator.importReceive.absorb.idPolicy
            .remint.leftoverInventedMint == true
      }
    }
  }

  verification def MN_VER_02_S02_CousinPointingContrast {
    doc /*
      MN-REQ-02.9 / MN-REQ-04.8 — cousin pointing contrast nest.
      Chosen TARGET: cue → RelativeSeed → ShapeWalk → pin_map emit.
      MUST NOT copy minted block id, vid-on-wire, unique page-name law,
          unique-name MERGE as identity, silent LLM merge of same-name
          nodes into the store, content-hash ids, typed path-ids,
      vector indexes as identity, or GraphLite as product. MAY copy
      cue-without-store-key and neighbourhood emit. Cue |Q|>1 stays
      RelativeSeed bounded + honest; no third operator. operatorCount
      stays 2. Cousin nest cousinNestOwnsLiveNeo4jClaim stays false
      (product Neo4j claim is archived, #187; this nest does not own it).
      Catalog Snap SHALL NOT ANN-rank sessions,
      Absorb a whole S, or mint one session per REQ.
      Contrast MUST NOT nest under MemNetSystem.
    */
    attribute verificationId : String = "MN-VER-02-S02";

    subject contrast : CousinPointingContrast;

    objective cousinPointingConfirmsTarget {
      verify noCopyCousinStoreKeyReq;
      verify cueMultiRootHonestReq;
      require constraint {
        contrast.mustNotNestUnderMemNetSystem == true
          and contrast.productSwitchForbidden == true
          and contrast.copyCueWithoutStoreKey == true
          and contrast.copyNeighbourhoodEmit == true
          and contrast.mustNotCopyMintedBlockId == true
          and contrast.mustNotCopyVidOnWire == true
          and contrast.mustNotCopyUniquePageNameLaw == true
          and contrast.mustNotCopyEmbeddingsAsRecall == true
          and contrast.mustNotCopyGraphLiteAsProduct == true
          and contrast.mustNotCopyGqlEngine == true
          and contrast.mustNotCopyContentHashIdentity == true
          and contrast.mustNotCopyUniqueNameMergeAsIdentity == true
          and contrast.mustNotCopySilentLlmSameNameMerge == true
          and contrast.mustNotCopyTypedPathIdsAsAgentLanguage == true
          and contrast.mustNotCopyVectorIndexAsIdentity == true
          and contrast.operatorCountUnchanged == 2
          and contrast.cousinNestOwnsLiveNeo4jClaim == false
          and contrast.inventThirdOperatorOnAmbiguity == false
          and contrast.chosen.storeKeyOnWire == false
          and contrast.chosen.requiredUniqueName == false
          and contrast.chosen.cueThenRelativeSeedThenShapeWalk == true
          and contrast.chosen.cueMayHitSeveralRoots == true
          and contrast.chosen.relativeSeedHardLimitHolds == true
          and contrast.chosen.unionWalkUnderOneM == true
          and contrast.chosen.inventThirdOperatorOnAmbiguity == false
          and contrast.chosen.nameRequired == false
          and contrast.chosen.emptyCueIsSessionOutline == true
          and contrast.chosen.viewShellIsNotOutline == true
          and contrast.chosen.mustNotDumpSOnEmptyCue == true
          and contrast.chosen.mustNotSkipEmptyCueAsTarget == true
          and contrast.chosen.catalogAnnRank == false
          and contrast.chosen.catalogAbsorbWholeS == false
          and contrast.chosen.oneSessionPerReq == false
          and contrast.mustNotCopyGetAllPages == true
          and contrast.mustNotCopyPatternCTour == true
          and contrast.mustNotCopyPatternDSeededRag == true
          and contrast.mustNotCopyViewShellAsOutline == true
          and contrast.nl2gql.storeKeyOnWire == true
          and contrast.nl2gql.productJob == "nl2gql_translator"
          and contrast.graphlite.storeKeyOnWire == false
          and contrast.graphlite.patternCueByLabelAndProps == true
          and contrast.graphlite.grammarHasMerge == false
          and contrast.graphlite.contentHashNodeId == true
          and contrast.graphlite.docsPointWithIdFunction == false
          and contrast.graphlite.productJob == "embedded_graph_store"
          and contrast.graphlite.productSwapForbidden == true
          and contrast.graphlite.sessionVsVault == "durable_cabinet"
          and contrast.textToSqlGraphRag.storeKeyOnWire == false
          and contrast.textToSqlGraphRag.requiredUniqueName == true
          and contrast.textToSqlGraphRag.mergeByUniqueName == true
          and contrast.textToSqlGraphRag.retrieverReturnsName == true
          and contrast.textToSqlGraphRag.elementIdWritebackOnly == true
          and contrast.textToSqlGraphRag.mustNotCopy == true
          and contrast.graphify.storeKeyOnWire == false
          and contrast.graphify.humanCueByLabel == true
          and contrast.graphify.neighbourhoodEmitLikePinMap == true
          and contrast.graphify.gqlOnAgentPath == false
          and contrast.understandAnything.storeKeyOnWire == false
          and contrast.understandAnything.cueIsNameText == true
          and contrast.understandAnything.typedCompositeStoreId == true
          and contrast.understandAnything.ingestThenGraphThenQuery == true
          and contrast.understandAnything.goldfishPinMapEmit == false
          and contrast.logseq.requiredUniqueName == true
          and contrast.logseq.closestHumanNameCousin == true
          and contrast.siyuan.mintedBlockIdOnWire == true
          and contrast.siyuan.leftoverZeroNineAnchorPath == true
          and contrast.mustNotSubstituteSysmledgePinMap == true
          and contrast.mustNotCopySysmledgeAsMemNetStrata == true
          and contrast.sysmledge.distinctPinMapFromMemNet == true
          and contrast.sysmledge.graphIsNotSsot == true
          and contrast.sysmledge.mustNotSubstituteMemNetPinMap == true
          and contrast.sysmledge.thisRepoHasProductFace == false
          and contrast.sysmledge.downstreamRepoPrefix == "SysMLEdgePrj-"
          and contrast.sysmledge.downstreamRepoFamily == "SysMLEdgePrj-*"
          and contrast.sysmledge.gitModelPathIsSsot == true
          and contrast.sysmledge.memnetIsMissionWorkingMemory == true
          and contrast.sysmledge.modelbasedPrjRepoBased == true
          and contrast.sysmledge.modelbasedPrjSysmlEdgeIsModelSsot == false
          and contrast.sysmledge.operatorReadmeStatesHost == true
          and contrast.sysmledge.downstreamBoundDeskIsWorkingModelSsot == true
          and contrast.sysmledge.mustNotInventUploadBind == true
      }
    }
  }

  verification def MN_VER_07_S01_TargetCommandListNoRequiredId {
    doc /*
      MN-REQ-07.5 / 07.1 — TARGET CLI/MCP command list is cue/pattern
      only. Session handle is not a store key. find / pin_map / mutate /
      Path-B ingest / Path-B import SHALL NOT require a store-key id.
      leftover_read_get, NEW, AssignedIdMap, by_id, MERGE-by-id,
      require_anchor, allocate_from_locator, and id_policy keyed on
      store-key MUST NOT nest as product commands (leftover_* engine
      honesty; TARGET implemented=false). Neo4j cabinet stays archived
      (#187; not this command-list cut). No Layer revival.
    */
    attribute verificationId : String = "MN-VER-07-S01";

    subject system : MemNetSystem;

    objective targetCommandsCuePatternOnly {
      verify noStoreKeyToolSurfaceReq;
      require constraint {
        system.mcp.tools.noRequiredIdTools == true
          and system.core.cli.noRequiredIdTools == true
          and system.mcp.tools.sessionOpen.requiresStoreKeyId == false
          and system.mcp.tools.sessionCurrent.requiresStoreKeyId == false
          and system.mcp.tools.sessionSave.requiresStoreKeyId == false
          and system.mcp.tools.sessionLoad.requiresStoreKeyId == false
          and system.mcp.tools.find.requiresStoreKeyId == false
          and system.mcp.tools.pinMap.requiresStoreKeyId == false
          and system.mcp.tools.pinMap.requireAnchorId == false
          and system.mcp.tools.mutate.requiresStoreKeyId == false
          and system.mcp.tools.mutate.createRequiresId == false
          and system.mcp.tools.mutate.noNewVerb == true
          and system.mcp.tools.mutate.noAssignedIdMapRequired == true
          and system.mcp.tools.ingest.requiresStoreKeyId == false
          and system.mcp.tools.ingest.matchByLabelsAndProps == true
          and system.mcp.tools.ingest.leftoverAllocateIsProductCommand == false
          and system.mcp.tools.importSlice.requiresStoreKeyId == false
          and system.mcp.tools.importSlice.matchByLabelsAndProps == true
          and system.mcp.tools.importSlice.leftoverIdPolicyIsProductCommand
            == false
          and system.mcp.tools.catalogSnap.requiresStoreKeyId == false
          and system.core.cli.catalogSnap.requiresStoreKeyId == false
          and system.mcp.tools.sessionList.requiresStoreKeyId == false
          and system.core.cli.sessionList.requiresStoreKeyId == false
          and system.mcp.tools.sessionList.listsCatalogSessionPins == true
          and system.core.cli.sessionList.listsCatalogSessionPins == true
          and system.mcp.tools.sessionList.annRankSessions == false
          and system.core.cli.sessionList.annRankSessions == false
          and system.mcp.tools.leftoverReadGetNested == false
          and system.mcp.tools.leftoverNewNested == false
          and system.mcp.tools.leftoverAssignedIdMapNested == false
          and system.mcp.tools.leftoverByIdNested == false
          and system.mcp.tools.leftoverMergeByIdNested == false
          and system.mcp.tools.leftoverRequireAnchorNested == false
          and system.mcp.tools.leftoverAllocateFromLocatorNested == false
          and system.mcp.tools.leftoverIdPolicyCommandNested == false
          and system.mcp.tools.leftoverNameConflictCommandNested == false
          and system.mcp.tools.leftoverMergeCommandNested == false
          and system.mcp.tools.leftoverAbsorbCommandNested == false
          and system.mcp.tools.leftoverElementIdOnWire == false
          and system.mcp.tools.leftoverEmptySeedSkipCommandNested == false
          and system.core.cli.leftoverReadGetNested == false
          and system.core.cli.leftoverNewNested == false
          and system.core.cli.leftoverAssignedIdMapNested == false
          and system.core.cli.leftoverByIdNested == false
          and system.core.cli.leftoverMergeByIdNested == false
          and system.core.cli.leftoverRequireAnchorNested == false
          and system.core.cli.leftoverAllocateFromLocatorNested == false
          and system.core.cli.leftoverIdPolicyCommandNested == false
          and system.core.cli.leftoverNameConflictCommandNested == false
          and system.core.cli.leftoverMergeCommandNested == false
          and system.core.cli.leftoverAbsorbCommandNested == false
          and system.core.cli.leftoverElementIdOnWire == false
          and system.core.cli.leftoverEmptySeedSkipCommandNested == false
          and system.core.cli.find.requiresStoreKeyId == false
          and system.core.cli.pinMap.requireAnchorId == false
          and system.core.cli.mutate.createRequiresId == false
          and system.core.transport.inProcess.memory.sessions.store
            .leftoverReadGetProductCommand == false
          and system.core.transport.inProcess.memory.sessions.store
            .leftoverReadGetTargetImplemented == false
          and system.core.transport.inProcess.memory.sessions.store
            .leftoverByIdProductCommand == false
          and system.core.transport.inProcess.memory.sessions.store
            .leftoverMergeByIdProductCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.implemented == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.productCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.targetImplemented == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.leftoverNewMintProductCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.leftoverAssignedIdMapProductCommand
            == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.leftoverRequireAnchorProductCommand
            == false
          and system.pinMaps.'interface'.matchByLabelsAndProps == true
          and system.pinMaps.'interface'.leftoverAllocateIsProductCommand
            == false
          and system.pinMaps.'interface'.leftoverAllocateFromLocatorProductCommand
            == false
          and system.multitask.coordinator.importReceive.absorb
            .leftoverIdPolicyIsProductCommand == false
          and system.multitask.coordinator.importReceive.absorb
            .matchByLabelsAndProps == true
          and system.multitask.coordinator.importReceive.absorb.idPolicy
            .leftoverIdPolicyIsProductCommand == false
          and system.multitask.coordinator.importReceive.absorb.idPolicy
            .remint.productCommand == false
          and system.durable.retiredNeo4jEnvIgnored == true
      }
    }
  }

  verification def MN_VER_06_S01_DurableCabinetHonesty {
    doc /*
      MN-REQ-06.4 — DurableBuffer nest honesty (ImportGuard-style flags).
      AgensGraphAdapter.liveCabinetClaimed is the 0.7 claim: adapter +
      operator round trip (no runtime caller). Factory binds exactly
      one of fake or AgensGraph. Neo4jAdapter / Neo4jLibraryPort /
      liveNeo4jClaimed are on MemNetArchive (#187). MEMNET_NEO4J_* is
      ignored (retiredNeo4jEnvIgnored). One DurableBuffer; one sync
      owner. HostSearchBridge stays outside MemNetSystem;
      RagHostHook.implemented=true (0.17) with fail-open locators;
      hostSearchInsideSystem stays false. Server not vendored.
      hydrateFlushCallers="tests": no non-test caller. serve, IPC, and
      MCP bind the owner and do not invoke it. Do not wire a new caller.
    */
    attribute verificationId : String = "MN-VER-06-S01";

    subject system : MemNetSystem;
    subject ragHostHook : RagHostHook;

    objective cabinetHonesty {
      verify durableStoreBehindMemNetReq;
      require constraint {
        system.durable.agens.implemented == true
          and system.durable.agens.liveCabinetClaimed == true
          and system.durable.hydrateFlushCallers == "tests"
          and system.durable.bindsExactlyOneOf == "fake|agensgraph"
          and system.durable.liveCabinetClaimed == true
          and system.durable.retiredNeo4jEnvIgnored == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.libraryIngestThisCut == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .hostSearchInsideSystem == false
          and ragHostHook.implemented == true
          and ragHostHook.designOnly == false
          and ragHostHook.failOpen == true
          and ragHostHook.locatorOnly == true
          and ragHostHook.snapOnSession == false
          and ragHostHook.mcpRagQuery == false
      }
    }
  }

  verification def MN_VER_06_S02_HumanUsageLookOnly {
    doc /*
      MN-REQ-06.5 — MemNetUsageDashboard is a human look, not manage.
      Outside MemNetSystem (usageDashboardInsideSystem=false;
      insideMemNetSystem=false). lookOnly; httpImplemented=false (HTTP/UI
      parked). agentWire=false; foamProductMcp=false; tipIsFace=false.
      No session_close / mutate / import_slice / key-entry / reproject
      ports. Does not own SessionLifecycle. Manage owners remain
      Memnetor+Devicor; lookActor=human. Nested looks are display-only.
    */
    attribute verificationId : String = "MN-VER-06-S02";

    subject system : MemNetSystem;
    subject dashboard : MemNetUsageDashboard;

    objective usageLookOnly {
      verify humanUsageLookReq;
      require constraint {
        system.usageDashboardInsideSystem == false
          and dashboard.insideMemNetSystem == false
          and dashboard.lookOnly == true
          and dashboard.httpImplemented == false
          and dashboard.agentWire == false
          and dashboard.foamProductMcp == false
          and dashboard.tipIsFace == false
          and dashboard.localBindDefault == true
          and dashboard.manageViaPage == false
          and dashboard.sessionClosePort == false
          and dashboard.mutatePort == false
          and dashboard.importSlicePort == false
          and dashboard.keyEntryPort == false
          and dashboard.reprojectPort == false
          and dashboard.ownsSessionLifecycle == false
          and dashboard.manageOwners == "Memnetor+Devicor"
          and dashboard.lookActor == "human"
          and dashboard.serveStatus.lookOnly == true
          and dashboard.sessionCensus.lookOnly == true
          and dashboard.sessionCensus.sessionClose == false
          and dashboard.housekeep.lookOnly == true
          and dashboard.housekeep.pruneFromPage == false
          and dashboard.importGuardArmed.lookOnly == true
          and dashboard.importGuardArmed.keyOnPage == false
          and dashboard.importGuardArmed.writable == false
      }
    }
  }

  verification def MN_VER_06_S03_DeviceFleetOneDropletMcp {
    doc /*
      MN-REQ-06.6 — ops fleet: device MemNet services; one MemNet MCP
      (tip/ops) at droplet; product invent face is sysmledge (tip≠face).
      Outside MemNetSystem (opsFleetInsideSystem=false;
      insideMemNetSystem=false). mcpCount=1; fleetMcpHost=droplet.
      Device hosts mcpNested=false / productMcpNested=false (no product
      MCP nested; tipMcpLegal=true). nServerFederation=false (#47).
      MemNetMcpServer.fleetSingleton=true; tipIsFace=false.
      productInventFace=sysmledge; mustNotInventUploadBind.
      CoreLibrary.deviceHostLegal.
    */
    attribute verificationId : String = "MN-VER-06-S03";

    subject system : MemNetSystem;
    subject fleet : MemNetOpsFleet;
    subject mcp : MemNetMcpServer;
    subject core : MemNetCoreLibrary;

    objective deviceFleetOneDropletMcp {
      verify deviceServicesOneDropletMcpReq;
      require constraint {
        system.opsFleetInsideSystem == false
          and fleet.insideMemNetSystem == false
          and fleet.mcpCount == 1
          and fleet.nServerFederation == false
          and fleet.fleetMcpHost == "droplet"
          and fleet.productInventFace == "sysmledge"
          and fleet.mustNotInventUploadBind == true
          and fleet.droplet.hostKind == "droplet"
          and fleet.droplet.mcpCount == 1
          and fleet.devices.hostKind == "device"
          and fleet.devices.mcpNested == false
          and fleet.devices.productMcpNested == false
          and fleet.devices.tipMcpLegal == true
          and fleet.devices.nServerPeer == false
          and mcp.fleetSingleton == true
          and mcp.defaultHostKind == "droplet"
          and mcp.tipIsFace == false
          and core.deviceHostLegal == true
      }
    }
  }

  verification def MN_VER_06_S04_SsotToCodeAllocate {
    doc /*
      MN-REQ-06.7 — SSOT parts allocate to live code in this checkout.
      One Hatch wheel (memnet-llm) for many hosts. MemNet MCP module
      is tip/ops (tipIsFace=false). Cousin sysmledge is not in the
      wheel and not in this repo (mustNotInventUploadBind).
      nServerFederation stays false (#47). ImplementationTracker
      watches allocate rows (trackAllocateRows; missingPathFailsCi);
      sysmlEdgeTracked=false. Engine/MCP behaviour unchanged;
      honesty c only.
    */
    attribute verificationId : String = "MN-VER-06-S04";

    subject wheel : MemNetLlmWheel;
    subject mcpMod : McpServerMod;
    subject absent : CousinSysMLEdgeNotInRepo;
    subject fleet : MemNetOpsFleet;
    subject tracker : ImplementationTracker;

    objective ssotToCodeAllocate {
      verify ssotToCodeAllocateReq;
      require constraint {
        wheel.oneWheelManyHosts == true
          and wheel.sysmlEdgeInWheel == false
          and wheel.track == true
          and wheel.hatchPackage == "memnet-llm"
          and wheel.hatchCorePackage == "parts/common/memnet/memnet"
          and wheel.hatchMcpPackage == "parts/memnet-mcp/software/memnet_mcp"
          and wheel.consoleMemnet == "memnet.cli:main"
          and wheel.consoleMemnetMcp == "memnet_mcp.entry:main"
          and mcpMod.tipIsFace == false
          and mcpMod.track == true
          and mcpMod.implemented == true
          and absent.inThisRepo == false
          and absent.implemented == false
          and absent.track == false
          and absent.mustNotInventUploadBind == true
          and fleet.nServerFederation == false
          and fleet.mustNotInventUploadBind == true
          and tracker.trackAllocateRows == true
          and tracker.sysmlEdgeTracked == false
          and tracker.missingPathFailsCi == true
      }
    }
  }

  verification def MN_VER_06_S05_TipMemNetAccessPortal {
    doc /*
      MN-REQ-06.8 — tip MemNet access portal. Outside MemNetSystem
      (tipAccessPortalInsideSystem=false; insideMemNetSystem=false).
      Admin display name Szu-Wei mints invites. Google login. Bearer
      shown after login. TipMcpGate requires Bearer and refuses
      unauthenticated WWW MemNet; forward host is the Pi tip; URL is
      the droplet WWW tip MCP. tipIsFace=false. Not a sysmledge
      product (isSysmlEdgeProduct=false; openProjectKeyPage=false;
      gatesSysmlEdge=false). grantsOpenMemNet=false. inventOnly=false;
      portalWebImplemented=true; sellsInvent2Green=false.
      Status look of services/clients is look-only
      (statusLookOnly=true) and MUST NOT unpark
      MemNetUsageDashboard HTTP (unparksUsageDashboard=false;
      dashboard httpImplemented stays false).
    */
    attribute verificationId : String = "MN-VER-06-S05";

    subject system : MemNetSystem;
    subject portal : TipMemNetAccessPortal;

    objective tipMemNetAccessPortal {
      verify tipMemNetAccessPortalReq;
      require constraint {
        system.tipAccessPortalInsideSystem == false
          and portal.insideMemNetSystem == false
          and portal.tipIsFace == false
          and portal.isSysmlEdgeProduct == false
          and portal.openProjectKeyPage == false
          and portal.grantsOpenMemNet == false
          and portal.unauthenticatedWwwMcp == false
          and portal.keyedWwwMcp == true
          and portal.inventOnly == false
          and portal.portalWebImplemented == true
          and portal.sellsInvent2Green == false
          and portal.gatesTipMcpOnly == true
          and portal.admin.displayName == "Szu-Wei"
          and portal.admin.role == "admin"
          and portal.invites.adminMintOnly == true
          and portal.user.allowlistRedeem == true
          and portal.google.provider == "google"
          and portal.keys.bearerShownAfterLogin == true
          and portal.keys.revokeSupported == true
          and portal.portal.portalWebImplemented == true
          and portal.portal.serviceLookImplemented == true
          and portal.portal.clientLookImplemented == true
          and portal.portal.statusLookOnly == true
          and portal.portal.unparksUsageDashboard == false
          and portal.serviceLookImplemented == true
          and portal.clientLookImplemented == true
          and portal.statusLookOnly == true
          and portal.unparksUsageDashboard == false
          and portal.keys.lastUsedTracked == true
          and portal.keys.useCountTracked == true
          and portal.gate.keyedAuthRequired == true
          and portal.gate.unauthenticatedAllowed == false
          and portal.gate.gatesSysmlEdge == false
          and portal.gate.forwardHost == "pi-tip"
          and portal.gate.authorizationScheme == "Bearer"
          and portal.gate.wwwUrl == "https://memnet.139-59-255-181.nip.io/mcp"
          and portal.piTip.tipIsFace == false
          and portal.piTip.unauthenticatedPublic == false
          and portal.piTip.hostKind == "pi-tip"
          and portal.freeStrangerPath == "sysmledge-free-tier-or-memnet-llm-self-host"
      }
    }
  }

  verification def MN_VER_06_S07_LanMcpFrontSeveralServes {
    doc /*
      MN-REQ-06.9 — LAN MCP front over several serves (#191).
      Outside MemNetSystem (lanMcpFrontInsideSystem=false;
      insideMemNetSystem=false). tipIsFace=false;
      isSysmlEdgeProduct=false; inventOnly=true;
      implemented=false; codeApproved=false; noSemVerBump.
      Registry is owner (registryPreferred; silentHashRouting=
      false; explicitPinAllowed; oneOwnerPerSession). pin_map /
      find SHALL NOT span backends. Truncation flags survive.
      Incomplete if any backend clipped or unreachable. Owner
      down is loud. Snapshot dir per backend. No silent migrate.
      No import_slice(from_url). Cousin of #47
      (nServerPeerHandoff=false; cousinIssue47). Shared graph DB
      false. Rate cap per-session. Unauthenticated public MCP
      refused. One serve already hosts many sessions
      (worthBuildingVisible).
    */
    attribute verificationId : String = "MN-VER-06-S07";

    subject system : MemNetSystem;
    subject front : MemNetLanMcpFront;

    objective lanMcpFrontSeveralServes {
      verify lanMcpFrontSeveralServesReq;
      require constraint {
        system.lanMcpFrontInsideSystem == false
          and front.insideMemNetSystem == false
          and front.tipIsFace == false
          and front.isSysmlEdgeProduct == false
          and front.inventOnly == true
          and front.implemented == false
          and front.codeApproved == false
          and front.noSemVerBump == true
          and front.nServerPeerHandoff == false
          and front.sharedGraphDb == false
          and front.pinMapSpansBackends == false
          and front.findSpansBackends == false
          and front.truncationFlagsSurviveRouting == true
          and front.incompleteIfAnyClippedOrUnreachable == true
          and front.loudFailOwnerDown == true
          and front.silentMigrate == false
          and front.snapshotDirPerBackend == true
          and front.sessionAclFollowsSession == true
          and front.rateCapPerSession == true
          and front.rateCapPerBackendOptional == true
          and front.importSliceFromUrl == false
          and front.cousinIssue47 == true
          and front.singleServeHostsManySessions == true
          and front.worthBuildingVisible == true
          and front.unauthenticatedPublicMcp == false
          and front.registry.registryPreferred == true
          and front.registry.silentHashRouting == false
          and front.registry.explicitPinAllowed == true
          and front.registry.oneOwnerPerSession == true
          and front.auth.lanAuthRequired == true
          and front.auth.openPort == false
          and front.auth.unauthenticatedPublicMcp == false
          and front.clusterRoute.isWhereSessionLives == true
          and front.clusterRoute.isExplicitCopy == false
          and front.clusterRoute.pinMapSpansBackends == false
          and front.clusterRoute.openRoute.writesRegistry == true
          and front.clusterRoute.openRoute.explicitPinFirst == true
          and front.clusterRoute.openRoute.silentHashSolePolicy == false
          and front.clusterRoute.listUnion.ownerTagged == true
          and front.clusterRoute.listUnion.incompleteIfAnyClippedOrUnreachable == true
          and front.clusterRoute.currentBind.oneCurrentSid == true
          and front.clusterRoute.currentBind.oneOwner == true
          and front.clusterRoute.currentBind.loudFailOwnerDown == true
          and front.handCarry.silentMigrate == false
          and front.handCarry.saveThenLoad == true
          and front.handCarry.importSliceFromUrl == false
          and front.handCarry.isClusterRelocate == true
          and front.handCarry.isSliceCopy == false
          and front.backends.hostKind == "lan-serve"
          and front.backends.snapshotDirPerBackend == true
          and front.backends.sharedNfsRequired == false
          and front.backends.commitGateLocal == true
      }
    }
  }

  verification def MN_VER_06_S08_ClusterRouteVsSliceHandCarry {
    doc /*
      MN-REQ-06.9 + MN-REQ-06.10 — two named moves in one nest.
      ClusterRoute is where the session lives (not an explicit
      copy). SliceHandCarry is an explicit copy into another
      session (not a live hop; import_slice same-serve only).
      Outside MemNetSystem. inventOnly; implemented=false.
      Caps / truncation survive both. No import_slice(from_url).
      No shared graph DB. Commit stays on the owning serve.
    */
    attribute verificationId : String = "MN-VER-06-S08";

    subject system : MemNetSystem;
    subject twoMoves : MemNetTwoMoves;
    subject slice : SliceHandCarry;
    subject cluster : ClusterRoute;

    objective clusterRouteVsSliceHandCarry {
      verify lanMcpFrontSeveralServesReq;
      verify sliceHandCarryAcrossServesReq;
      require constraint {
        system.twoMovesInsideSystem == false
          and system.lanMcpFrontInsideSystem == false
          and twoMoves.insideMemNetSystem == false
          and twoMoves.tipIsFace == false
          and twoMoves.isSysmlEdgeProduct == false
          and twoMoves.inventOnly == true
          and twoMoves.implemented == false
          and twoMoves.codeApproved == false
          and twoMoves.noSemVerBump == true
          and twoMoves.clusterIsWhereSessionLives == true
          and twoMoves.sliceIsExplicitCopy == true
          and twoMoves.liveHop == false
          and twoMoves.importSliceAcrossHosts == false
          and twoMoves.importSliceFromUrl == false
          and twoMoves.sharedGraphDb == false
          and twoMoves.truncationFlagsSurviveBothMoves == true
          and twoMoves.clippedMustNotLookComplete == true
          and twoMoves.commitGateOnOwningServe == true
          and cluster.isWhereSessionLives == true
          and cluster.isExplicitCopy == false
          and cluster.isLiveHop == false
          and cluster.pinMapSpansBackends == false
          and cluster.findSpansBackends == false
          and cluster.realisedByLanFront == true
          and slice.insideMemNetSystem == false
          and slice.isWhereSessionLives == false
          and slice.isExplicitCopy == true
          and slice.isLiveHop == false
          and slice.isClusterRoute == false
          and slice.importSliceSameServeOnly == true
          and slice.importSliceAcrossHosts == false
          and slice.importSliceFromUrl == false
          and slice.destIsDifferentSession == true
          and slice.sourceSessionStays == true
          and slice.truncationFlagsSurvive == true
          and slice.clippedMustNotLookComplete == true
          and slice.sharedGraphDb == false
          and slice.commitGateOnOwningServe == true
          and slice.inventOnly == true
          and slice.implemented == false
          and slice.lanCopy.isLiveHop == false
          and slice.lanCopy.importSliceFromUrl == false
          and slice.lanCopy.isClusterRoute == false
          and slice.destAbsorb.importSliceSameServeOnly == true
          and slice.destAbsorb.importSliceAcrossHosts == false
          and slice.exportCarry.clippedMustNotLookComplete == true
      }
    }
  }

  verification def MN_VER_06_S09_AdminServeUsageReport {
    doc /*
      MN-REQ-06.11 — AdminUsageReport on TcpServeBridge (memnet-serve).
      Admin credential MEMNET_ADMIN_TOKEN; unset refuses
      admin_unconfigured with no report body. Peek only; no mn_*
      ids; no graph content; not on agent MCP. CLI optional
      --product; MCP session_open MUST NOT grow that arg
      (mcpProductLabelOpen remains an open question).
    */
    attribute verificationId : String = "MN-VER-06-S09";

    subject system : MemNetSystem;
    subject tcp : TcpServeBridge;
    subject report : AdminUsageReport;
    subject mcp : McpFacade;
    subject cli : CliFacade;
    subject openCmd : CmdSessionOpen;

    objective adminServeUsageReport {
      verify adminServeUsageReportReq;
      require constraint {
        system.adminUsageOnAgentMcp == false
          and tcp.adminUsage.lookOnly == true
          and tcp.adminUsage.onAgentMcp == false
          and tcp.adminUsage.emitsRealSessionId == false
          and tcp.adminUsage.emitsGraphContent == false
          and tcp.adminUsage.emitsLocators == false
          and tcp.adminUsage.peekOnly == true
          and tcp.adminUsage.slidesTtl == false
          and tcp.adminUsage.purgesOnLook == false
          and tcp.adminUsage.jsonStdout == true
          and tcp.adminUsage.mcpProductLabelOpen == true
          and tcp.adminUsage.productLabelOnMcpSessionOpen == false
          and tcp.adminUsage.productLabelOnCliSessionOpen == true
          and tcp.adminUsage.implemented == true
          and tcp.adminUsage.noSemVerBump == true
          and report.cred.envName == "MEMNET_ADMIN_TOKEN"
          and report.cred.isAgentAcl == false
          and report.cred.refuseUnconfigured == true
          and report.cred.errUnconfigured == "admin_unconfigured"
          and report.cred.errDenied == "admin_denied"
          and report.tally.sinceServeStart == true
          and report.tally.leftoverSilentClipCountsAsTruncation == false
          and mcp.adminUsageToolNested == false
          and mcp.productLabelOnSessionOpen == false
          and cli.adminUsageOnAgentMcp == false
          and openCmd.productLabelOnMcp == false
          and openCmd.optionalProductLabel == true
      }
    }
  }

  verification def MN_VER_06_S10_ProductGateway {
    doc /*
      MN-REQ-06.12 — MemNetProductGateway on memnet-mcp.
      Outside MemNetSystem. tip≠face. Hashed per-product
      credentials, not mn_tip_. One owner. No silent move.
      Pass-through of GQL and stdin. No caps below the
      backend. Body ceiling declared. Version pin. Filtered
      list. Loopback or tailnet by default. Admin counts omit
      content and session ids. Single-backend memnet-mcp
      unchanged when no registry is configured. No SemVer bump.
    */
    attribute verificationId : String = "MN-VER-06-S10";

    subject gateway : MemNetProductGateway;

    objective productGateway {
      verify productGatewayReq;
      require constraint {
        gateway.insideMemNetSystem == false
          and gateway.tipIsFace == false
          and gateway.isSysmlEdgeProduct == false
          and gateway.inventOnly == false
          and gateway.implemented == true
          and gateway.codeApproved == true
          and gateway.noSemVerBump == true
          and gateway.reusesTipBearer == false
          and gateway.hashedCredentials == true
          and gateway.credentialScopedToProductBackends == true
          and gateway.rotateAndRevoke == true
          and gateway.oneOwnerPerSession == true
          and gateway.silentCrossBackendMove == false
          and gateway.failoverOnlyForNewSession == true
          and gateway.passThroughGql == true
          and gateway.passThroughStdin == true
          and gateway.verbatimEngineControlLines == true
          and gateway.gatewayCapsBelowBackend == false
          and gateway.bodyCeilingDeclared == true
          and gateway.versionPinPerProduct == true
          and gateway.listFilteredByProduct == true
          and gateway.foreignSessionGatewayErr == true
          and gateway.publicBindDefault == false
          and gateway.loopbackOrTailnetOnly == true
          and gateway.adminCountsOmitContent == true
          and gateway.adminCountsOmitSessionId == true
          and gateway.singleBackendUnchanged == true
          and gateway.hardcodedHost == false
      }
    }
  }

  verification def MN_VER_06_S12_SafeServeUpgrade {
    doc /*
      MN-REQ-06.14 — drain, manifest, and startup restore
      inside memnet serve. Admin credential. Quiesce refuses
      new commands with serve_draining. Unsaveable sessions
      block ready_to_stop unless allow-unsaved. Restore checks
      counts and checksums. Corrupt snapshots stay on disk.
      A clean restore retires the manifest in that startup.
      Retire is an audit mark ("retired", "retired_at"): it no
      longer stops a later restore, and a later start restores
      again (MN-REQ-06.17, MN-VER-06-S15).
      Same session id, ACL, TTL clock, and house. Not an
      agent MCP tool. No client retry. No SemVer bump.
      Tests: tests/test_safe_upgrade.py::test_clean_restore_retires_and_a_later_start_still_restores
      (renamed from ..._so_a_later_start_does_not_replay; the second
      start restores again and the manifest stays retired);
      ::test_tcp_restart_restores_same_sessions (the third start
      finds the kept fact).
    */
    attribute verificationId : String = "MN-VER-06-S12";

    subject tcp : TcpServeBridge;
    subject cli : CliFacade;
    subject upgradeMod : SafeUpgradeMod;

    objective safeServeUpgrade {
      verify safeServeUpgradeReq;
      require constraint {
        tcp.safeUpgrade.implemented == true
          and tcp.safeUpgrade.noSemVerBump == true
          and tcp.safeUpgrade.onAgentMcp == false
          and tcp.safeUpgrade.adminCredEnv == "MEMNET_ADMIN_TOKEN"
          and tcp.safeUpgrade.refusesNewSessionOpen == true
          and tcp.safeUpgrade.errDraining == "serve_draining"
          and tcp.safeUpgrade.finishesInFlight == true
          and tcp.safeUpgrade.usesLosslessSnapshot == true
          and tcp.safeUpgrade.manifestBeforeStop == true
          and tcp.safeUpgrade.blocksOnUnsaveable == true
          and tcp.safeUpgrade.allowUnsavedOverride == true
          and tcp.safeUpgrade.silentSessionLoss == false
          and tcp.safeUpgrade.restoreVerifiesChecksum == true
          and tcp.safeUpgrade.restoreVerifiesCounts == true
          and tcp.safeUpgrade.keepsFilesUntilVerified == true
          and tcp.safeUpgrade.olderPatchSnapshotLoads == true
          and tcp.safeUpgrade.corruptFailsLoud == true
          and tcp.safeUpgrade.corruptDeletesSnapshots == false
          and tcp.safeUpgrade.preservesSessionId == true
          and tcp.safeUpgrade.preservesAcl == true
          and tcp.safeUpgrade.preservesTtlClock == true
          and tcp.safeUpgrade.preservesHouse == true
          and tcp.safeUpgrade.retiresAfterCleanRestore == true
          and upgradeMod.retiredStaysCandidate == true
          and upgradeMod.laterRestartRestores == true
          and tcp.safeUpgrade.statUpgradeRestore == "upgrade_restore"
          and cli.upgradePrepareOnAgentMcp == false
          and cli.upgradePrepare.onAgentMcp == false
      }
    }
  }

  verification def MN_VER_06_S13_ServeCheckpoint {
    doc /*
      MN-REQ-06.15 — checkpoint every loaded session without
      draining or refusing traffic. Per-session lock only.
      Lossless atomic snapshot. Unsaveable sessions are named
      and skipped. Exit is non-zero when any were skipped.
      TTL, id, ACL, and live state stay put. A checkpoint does
      not retire or load. checkpoint-verify checks a restored
      directory. Not an agent MCP tool. No SemVer bump.
    */
    attribute verificationId : String = "MN-VER-06-S13";

    subject tcp : TcpServeBridge;
    subject cli : CliFacade;

    objective serveCheckpoint {
      verify serveCheckpointReq;
      require constraint {
        tcp.serveCheckpoint.implemented == true
          and tcp.serveCheckpoint.noSemVerBump == true
          and tcp.serveCheckpoint.onAgentMcp == false
          and tcp.serveCheckpoint.adminCredEnv == "MEMNET_ADMIN_TOKEN"
          and tcp.serveCheckpoint.refusesNewSessionOpen == false
          and tcp.serveCheckpoint.drainsServe == false
          and tcp.serveCheckpoint.sessionLockOnly == true
          and tcp.serveCheckpoint.usesLosslessSnapshot == true
          and tcp.serveCheckpoint.atomicWrite == true
          and tcp.serveCheckpoint.skipsUnsaveable == true
          and tcp.serveCheckpoint.unsaveableFatal == false
          and tcp.serveCheckpoint.exitNonZeroWhenSkipped == true
          and tcp.serveCheckpoint.removesStale == true
          and tcp.serveCheckpoint.preservesSessionId == true
          and tcp.serveCheckpoint.preservesAcl == true
          and tcp.serveCheckpoint.preservesTtlClock == true
          and tcp.serveCheckpoint.retiresOrLoads == false
          and tcp.serveCheckpoint.statCheckpoint == "checkpoint"
          and tcp.serveCheckpoint.statCheckpointVerify == "checkpoint_verify"
          and cli.checkpointOnAgentMcp == false
          and cli.checkpoint.onAgentMcp == false
          and cli.checkpointVerify.onAgentMcp == false
      }
    }
  }

  verification def MN_VER_06_S15_RestartRestoreNewestSet {
    doc /*
      MN-REQ-06.17 — every serve start restores the newest valid
      snapshot set, checkpoint or upgrade-prepare.
      Field case and mtime: tests/test_restart_restore.py::test_field_case_retired_legacy_prepare_and_newer_checkpoint_restores_checkpoint
      (retired legacy prepare manifest with no timestamp, older mtime,
      plus a newer checkpoint: the checkpoint is restored with ids, ACL,
      product and expires_at kept);
      ::test_legacy_prepare_alone_restores_by_mtime_and_again_when_retired.
      Tie: ::test_tie_goes_to_upgrade.
      Fallback: ::test_corrupt_newest_checkpoint_falls_back_to_upgrade_loudly
      (@WARN: restore_fallback|checkpoint|upgrade_checksum|... on stdout
      and stderr, report "rejected").
      None valid: ::test_no_valid_set_exits_3_with_the_newest_code.
      No files: ::test_no_candidate_files_is_skipped.
      Real process (SIGKILL and SIGTERM; same session id set and
      per-session rows, edges and node ids; second restart again):
      ::test_real_restart_restores_checkpoint_and_again_on_the_next_restart;
      precedence: ::test_real_restart_newer_checkpoint_beats_older_prepare,
      ::test_real_restart_newer_prepare_beats_older_checkpoint.
      Retire no longer stops a later restore:
      tests/test_safe_upgrade.py::test_clean_restore_retires_and_a_later_start_still_restores.
      Behaviour: RestartRestoreChoice. Part: SafeUpgradeMod.
    */
    attribute verificationId : String = "MN-VER-06-S15";

    subject upgradeMod : SafeUpgradeMod;
    subject tcp : TcpServeBridge;

    objective restartRestoreNewestSet {
      doc /* Implemented: tests/test_restart_restore.py asserts the restore choice in process and in a real serve. */
      verify requirement restartRestoreNewestSetReq : MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_17_RestartRestoreNewestSet;
      require constraint {
        upgradeMod.implemented == true
          and upgradeMod.restoresCheckpointSet == true
          and upgradeMod.restoresUpgradeSet == true
          and upgradeMod.tieGoesToUpgrade == true
          and upgradeMod.retiredStaysCandidate == true
          and upgradeMod.laterRestartRestores == true
          and upgradeMod.preflightBeforeLoad == true
          and upgradeMod.fallbackIsLoud == true
          and upgradeMod.printsRestoreSource == true
          and upgradeMod.noneValidExit == 3
          and upgradeMod.noCandidateSkipped == true
          and upgradeMod.loadFailureFallsBack == false
          and upgradeMod.emptyNewestSetWins == true
          and upgradeMod.retireOnlyUpgradeSource == true
          and upgradeMod.writesCheckpointManifest == false
          and tcp.safeUpgrade.retiresAfterCleanRestore == true
          and tcp.serveCheckpoint.retiresOrLoads == false
      }
    }
  }

  verification def MN_VER_06_S16_McpExtraFailFast {
    doc /*
      MN-REQ-06.18 — memnet-mcp without the [mcp] extra writes one
      stderr line, @ERR: mcp_extra_missing|memnet-mcp needs the mcp
      extra (missing module: <mcp|uvicorn>); install with: pip install
      'memnet-llm[mcp]', nothing on stdout, no traceback, exit 2, for
      --transport stdio, streamable-http, gateway and --help, with mcp
      or uvicorn missing:
      tests/test_mcp_extra_missing.py::test_missing_extra_one_line_exit_2;
      entry interface (MCP_EXTRA_HINT, require_mcp_extra, main):
      ::test_entry_module_interface; console script
      memnet_mcp.entry:main: ::test_console_script_points_at_entry;
      with the extra, --help still works:
      ::test_with_extra_help_still_works.
    */
    attribute verificationId : String = "MN-VER-06-S16";

    subject mcpMod : McpServerMod;
    subject wheel : MemNetLlmWheel;

    objective mcpExtraFailFast {
      doc /* Implemented: tests/test_mcp_extra_missing.py runs memnet_mcp with the extra blocked. */
      verify requirement mcpExtraFailFastReq : MN_REQ_00_MissionBridge::MN_REQ_06_ProcessBoundary::MN_REQ_06_18_McpExtraFailFast;
      require constraint {
        mcpMod.implemented == true
          and mcpMod.mcpExtraMissingExit == 2
          and mcpMod.extraCheckBeforeArgs == true
          and mcpMod.everyTransportNeedsExtra == true
          and wheel.track == true
      }
    }
  }

  verification def MN_VER_06_S14_SnapshotAcl {
    doc /*
      MN-REQ-06.16 — the session ACL persists in the snapshot as one
      comment line (#@ACL:) after @SNAP, and session_load restores it
      (including keep_id). @SNAP is version 2. A version 2 snapshot with
      no ACL line fails bad_snapshot. A version 1 snapshot loads ACL off
      and says so (@ACL: absent|off). A malformed ACL line fails the load.
      The bind stores a SHA-256 digest of the lease only, and the lease
      is never printed. Snapshot and manifest files are mode 0600 and are
      written atomically. A v1 file is backed up once to <file>.v1.bak
      (0600) before the first v2 write; the backup is never overwritten;
      v2 over v2 and first writes make no backup. No dual write. Rollback
      to 0.19.23 restores the .v1.bak files: writes after the upgrade are
      lost. A malformed bind (no lease digest, non-dict, no mission_id)
      fails bad_snapshot. No SemVer bump.
      Tests: tests/test_acl_snapshot.py::test_round_trip_keeps_enable_flag_grants_and_bind;
      ::test_format_1_snapshot_loads_with_acl_off;
      ::test_format_2_missing_acl_line_fails_bad_snapshot;
      ::test_snapshot_files_are_mode_0600_and_replace_loose_modes;
      ::test_bind_stores_only_a_digest_of_the_lease;
      ::test_reader_only_caller_is_refused_after_reload;
      ::test_keep_id_reload_restores_acl_and_fresh_id_does_too;
      ::test_malformed_acl_line_fails_closed;
      ::test_v1_file_is_backed_up_once_before_first_v2_write;
      ::test_v2_over_v2_and_first_write_create_no_backup;
      ::test_malformed_bind_in_file_fails_closed_bad_snapshot;
      tests/test_safe_upgrade.py::test_round_trip_keeps_id_acl_ttl_and_near_cap (manifest mode, no raw lease).
      tests/test_safe_upgrade.py::test_rollback_restore_rewrites_original_bytes_atomically (restore writes 0600, original bytes).
      Model: tests/test_sysml_acl_snapshot.py.
    */
    attribute verificationId : String = "MN-VER-06-S14";

    subject snap : SnapshotStore;

    objective snapshotAcl {
      verify snapshotAclReq;
      require constraint {
        snap.snapshotAcl.aclLinePersisted == true
          and snap.snapshotAcl.aclLineCommentPrefix == "#@ACL:"
          and snap.snapshotAcl.snapshotFormatVersion == 2
          and snap.snapshotAcl.snapshotFormatV1Loads == true
          and snap.snapshotAcl.aclRestoredOnLoad == true
          and snap.snapshotAcl.aclRestoredOnKeepIdLoad == true
          and snap.snapshotAcl.aclAbsentLoadsOff == true
          and snap.snapshotAcl.aclAbsentStat == "@ACL: absent|off"
          and snap.snapshotAcl.v2MissingAclFailsBadSnapshot == true
          and snap.snapshotAcl.aclMalformedFailsClosed == true
          and snap.snapshotAcl.aclLeaseNotPrinted == true
          and snap.snapshotAcl.bindStoresLeaseDigestOnly == true
          and snap.snapshotAcl.leaseDigestAlgorithm == "sha256"
          and snap.snapshotAcl.snapshotFileMode == "0600"
          and snap.snapshotAcl.atomicPrivateWrite == true
          and snap.snapshotAcl.v1BackupBeforeFirstV2Write == true
          and snap.snapshotAcl.v1BackupOnlyWhenFormat1 == true
          and snap.snapshotAcl.v1BackupName == ".v1.bak"
          and snap.snapshotAcl.v1BackupMode == "0600"
          and snap.snapshotAcl.v1BackupNeverOverwritten == true
          and snap.snapshotAcl.dualWriteV1 == false
          and snap.snapshotAcl.rollbackRestoresV1Backup == true
          and snap.snapshotAcl.rollbackLosesPostUpgradeWrites == true
          and snap.snapshotAcl.v2RefusedByOldBuild == true
          and snap.snapshotAcl.noSemVerBump == true
      }
    }
  }

  verification def MN_VER_04_S06_HousekeepEndpointIdentity {
    doc /*
      MN-REQ-04.12 — housekeep resolves edge endpoints by hid and
      nickname. prune orphans / prune stale --apply recomputes and
      refuses a referenced node. Nothing runs prune --apply by itself.
    */
    attribute verificationId : String = "MN-VER-04-S06";

    subject housekeep : HousekeepSettle;

    objective housekeepEndpointIdentity {
      verify housekeepEndpointIdentityReq;
      require constraint {
        housekeep.endpointIdentityResolvesHid == true
          and housekeep.pruneApplyRefusesReferenced == true
          and housekeep.autoPruneApply == false
      }
    }
  }

  verification def MN_VER_06_S11_ServeRequestIsolation {
    doc /*
      MN-REQ-06.13 — each memnet serve command keeps its own
      stdout, stderr, and exit_code. TCP and the product gateway
      (which forwards to that serve) share this rule. Capture is
      per request. Different sessions MAY run together
      (serialisesRequests=false).
    */
    attribute verificationId : String = "MN-VER-06-S11";

    subject tcp : TcpServeBridge;

    objective serveRequestIsolation {
      verify serveRequestIsolationReq;
      require constraint {
        tcp.requestOutputIsolated == true
          and tcp.serialisesRequests == false
      }
    }
  }

  verification def MN_VER_13_S01_RecallCommitTwoOperators {
    doc /*
      MN-REQ-13.1 — two-operator cut (math skeleton; leftover goldfish).
      Honesty: operatorCount == 2; hostSearchInsideSystem == false;
      Commit.oneGate == true; RSV nested under Commit (implemented);
      PinMapShapedRead true / BoundedMatchFind true (#73 seed-only find);
      Layer leftover retire-from-wheel (leftoverLayerDeleteThisPr == false;
      leftoverFogNested == false; leftoverArchiveOffLoad; ProductGqlGate
      rejectLayer). leftover_* parts live on MemNetArchive, off this load.
      All examination/test is paradox (pytest, MN-VER). Math: docs/grammar/math-skeleton.md.
    */
    attribute verificationId : String = "MN-VER-13-S01";

    subject system : MemNetSystem;

    objective twoOperators {
      verify twoOperatorsReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.recallCommit
          .operatorCount == 2
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .hostSearchInsideSystem == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.oneGate == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.absorbPathBOnly == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.reserve.implemented == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.implemented == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.find.implemented == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.emptySeedSkip == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.emptyCueIsOutline == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.outline.notAThirdOperator == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.cosineMetric == false
          and system.core.transport.inProcess.memory.sessions.gqlWire
            .productGate.rejectLayer == true
          and system.leftoverLayerDeleteThisPr == false
          and system.leftoverLayerMustNotNestOnProductPath == true
          and system.leftoverFogNested == false
          and system.leftoverArchiveOffLoad == true
      }
    }
  }

  verification def MN_VER_13_S02_RecallDoesNotAbsorb {
    doc /*
      MN-REQ-13.2 / MN-REQ-04.8 — Recall SHALL NOT absorb. RelativeSeed /
      find emit Q honestly; CueConflict on shaped emit when |Q|>1 (Q listed,
      cardinality visible; not a product command). Same name is a candidate
      only. SameThingAbsorb MAY collapse under Commit after that mark,
      distinct from ImportAbsorb. operatorCount stays 2. Neo4j cabinet
      stays archived (#187; not this absorb cut).
    */
    attribute verificationId : String = "MN-VER-13-S02";

    subject system : MemNetSystem;

    objective recallDoesNotAbsorbCommitMay {
      verify sameThingAbsorbReq;
      verify twoOperatorsReq;
      verify cueMultiRootHonestReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.recallCommit
          .operatorCount == 2
          and system.durable.retiredNeo4jEnvIgnored == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.absorbs == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.silentMergeByName == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.llmCollapseInsideRecall == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.sameNameIsCandidateOnly == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.absorbs == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.silentMergeByName == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.llmCollapseInsideRecall == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.sameNameIsCandidateOnly == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.emitQHonestWhenMulti == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.seed.silentPickOneRoot == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.cueConflictOnMultiRoot == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.walk.cueConflict.productCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.walk.cueConflict.qListed == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.walk.cueConflict.cardinalityVisible == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.walk.cueConflict.silentPickOneRoot == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.walk.cueConflict.differentWorldThingsStayTwoRoots
            == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.find.cueConflict.productCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.cueConflict.productCommand == false
          and system.mcp.tools.leftoverNameConflictCommandNested == false
          and system.mcp.tools.leftoverMergeCommandNested == false
          and system.mcp.tools.leftoverAbsorbCommandNested == false
          and system.core.cli.leftoverNameConflictCommandNested == false
          and system.core.cli.find.cueConflict.productCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.afterCueConflictVisible == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.notAProductCommand == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThingAbsorbIsCommitRule == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.absorbPathBOnly == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.notRecall == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.distinctFromImportAbsorb == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.matchByLabelsAndProps == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.leftoverMergeByIdForbidden == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.sameNameIsCandidateOnly == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.differentWorldThingsRemainTwo == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.mintSecondNodeOnRename == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.akaOnSameNode == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.goldfishWritebackNaming == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.sameThing.implemented == false
      }
    }
  }

  verification def MN_VER_11_S17_CatalogModelSnap {
    doc /*
      MN-REQ-11.17 — Snap(one model) → catalog + package interiors.
      Look = pin_map; join = Absorb slice. MUST NOT ANN-rank sessions;
      Absorb whole S; dump one model into one session; Layer; one session
      per REQ; invent a store key; hid on the wire. operatorCount stays 2.
      Catalog Snap SHALL NOT restore the retired Neo4j cabinet
      (#187; this cut's fence).
      Cross-cut satisfy locators on the catalog (MN-REQ-11.17.1);
      interiors have no dangling dest; SysMLEdge pin_map is not this catalog.
      Session grain bounded (MN-REQ-11.17.2); budget pre-check and
      all-or-nothing mint (MN-REQ-11.17.3); caller gone rolls back
      (MN-REQ-11.17.4); repeat same root replaces (MN-REQ-11.17.5).
    */
    attribute verificationId : String = "MN-VER-11-S17";

    subject system : MemNetSystem;

    objective catalogSnapPackageGrain {
      verify catalogModelSnapReq;
      verify crossCutSatisfyLocatorsReq;
      verify snapSessionGrainReq;
      verify snapBudgetPrecheckReq;
      verify snapCallerGoneRollbackReq;
      verify snapReplaceByModelIdentityReq;
      require constraint {
        system.pinMaps.catalog.implemented == true
          and system.pinMaps.catalog.packageGrain == true
          and system.pinMaps.catalog.lookIsPinMap == true
          and system.pinMaps.catalog.joinIsAbsorbSlice == true
          and system.pinMaps.catalog.absorbWholeS == false
          and system.pinMaps.catalog.dumpModelIntoOneSession == false
          and system.pinMaps.catalog.oneSessionPerReq == false
          and system.pinMaps.catalog.oneSessionPerPart == false
          and system.pinMaps.catalog.oneSessionPerTsk == false
          and system.pinMaps.catalog.twoSegmentChildPackage == false
          and system.pinMaps.catalog.nestedPackageGrain == true
          and system.pinMaps.catalog.singleLeafInterior == false
          and system.pinMaps.catalog.sessionBudgetPrecheck == true
          and system.pinMaps.catalog.allOrNothingMint == true
          and system.pinMaps.catalog.replaceByModelIdentity == true
          and system.pinMaps.catalog.callerGoneRollback == true
          and system.pinMaps.catalog.serveTimeoutNamed == true
          and system.pinMaps.catalog.layerProperty == false
          and system.pinMaps.catalog.annRankSessions == false
          and system.pinMaps.catalog.hiddenHandleOnWire == false
          and system.pinMaps.catalog.locatorsAreProperties == true
          and system.pinMaps.catalog.notAThirdOperator == true
          and system.pinMaps.catalog.crossCutSatisfyOnCatalog == true
          and system.pinMaps.catalog.danglingDestInInterior == false
          and system.pinMaps.catalog.endLocatorsBoundedByM == true
          and system.pinMaps.catalog.packagePairWhenOverM == true
          and system.pinMaps.catalog.foreignProductPinMap == false
          and system.core.cli.catalogSnap.crossCutSatisfyOnCatalog == true
          and system.core.cli.catalogSnap.danglingDestInInterior == false
          and system.core.cli.catalogSnap.foreignProductPinMap == false
          and system.core.cli.catalogSnap.oneSessionPerPart == false
          and system.core.cli.catalogSnap.twoSegmentChildPackage == false
          and system.core.cli.catalogSnap.nestedPackageGrain == true
          and system.core.cli.catalogSnap.singleLeafInterior == false
          and system.core.cli.catalogSnap.sessionBudgetPrecheck == true
          and system.core.cli.catalogSnap.allOrNothingMint == true
          and system.core.cli.catalogSnap.replaceByModelIdentity == true
          and system.core.cli.catalogSnap.callerGoneRollback == true
          and system.core.cli.catalogSnap.serveTimeoutNamed == true
          and system.core.cli.catalogSnap.implemented == true
          and system.mcp.tools.catalogSnap.implemented == true
          and system.core.cli.sessionList.listsCatalogSessionPins == true
          and system.mcp.tools.sessionList.listsCatalogSessionPins == true
          and system.core.cli.sessionList.requiresStoreKeyId == false
          and system.mcp.tools.sessionList.requiresStoreKeyId == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .operatorCount == 2
          and system.durable.retiredNeo4jEnvIgnored == true
      }
    }
  }

  verification def MN_VER_01_S03_ExpireSaveConfigurable {
    doc /*
      MN-REQ-01.3 / 01.4 / 01.5 — TTL drops RAM. Expire session_save is
      configurable (default off). Explicit save and expire-save are one
      blob. File until user drop; session_load restores RAM, including
      loadByKnownSid; not Neo4j. Leftover fog stays off ProjectMemNet load.
      Dashboard remains look-only.
    */
    attribute verificationId : String = "MN-VER-01-S03";

    subject system : MemNetSystem;
    subject dashboard : MemNetUsageDashboard;

    objective expireSaveConfigurable {
      verify sessionTtlAndCapsReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.slidingTtl == true
          and system.core.transport.inProcess.memory.sessions.ramDropsOnTtl
            == true
          and system.core.transport.inProcess.memory.sessions.snap
            .saveOnExpireDefault == false
          and system.core.transport.inProcess.memory.sessions.snap
            .saveOnExpireConfigurable == true
          and system.core.transport.inProcess.memory.sessions.snap
            .fileUntilUserDrop == true
          and system.core.transport.inProcess.memory.sessions.snap
            .loadRestoresRam == true
          and system.core.transport.inProcess.memory.sessions.snap
            .notNeo4j == true
          and system.core.transport.inProcess.memory.sessions.snap
            .loadByKnownSid == true
          and system.core.transport.inProcess.memory.sessions.snap
            .expireMissHonest == true
          and system.core.transport.inProcess.memory.sessions.snap
            .explicitSaveAndExpireSaveOneBlob == true
          and system.core.cli.sessionLoad.loadByKnownSid == true
          and system.mcp.tools.sessionLoad.loadByKnownSid == true
          and system.core.transport.inProcess.memory.sessions.caps
            .saveOnExpireDefault == false
          and system.core.transport.inProcess.memory.sessions.caps
            .saveOnExpireConfigurable == true
          and system.core.cli.sessionSave.saveOnExpireDefault == false
          and system.core.cli.sessionSave.saveOnExpireConfigurable == true
          and system.core.cli.sessionSave.ramDropsAfterExpireSave == true
          and system.mcp.tools.sessionSave.saveOnExpireDefault == false
          and system.core.cli.sessionLoad.newIdDefault == true
          and system.core.cli.sessionLoad.keepIdOptional == true
          and system.core.cli.sessionLoad.ttlResetsOnLoad == true
          and system.leftoverFogNested == false
          and system.leftoverArchiveOffLoad == true
          and dashboard.httpImplemented == false
          and dashboard.tipIsFace == false
          and dashboard.agentWire == false
      }
    }
  }

  verification def MN_VER_01_S04_SnapshotLosslessRoundTrip {
    doc /*
      MN-REQ-01.9 / MN-REQ-05.3 / MN-REQ-05.4 — snapshot emit escapes
      splitlines separators (LF/CR/VT/FF/FS/GS/RS/NEL/LS/PS) plus
      pipe/backslash losslessly; undeclared RAM properties persist by
      snapshot SCHEMA widen; line_bytes is the escaped emitted line at
      save and load; mutate refuses a tag whose effective fields
      exceed max_fields (limit_exceeded|fields n/max) so save is never
      stricter than write; save fails closed; expire-save writes no
      unloadable file and keeps RAM on any save failure until explicit
      save or close; 0.19.18 snapshots still load; value_bytes is
      decoded raw UTF-8.
    */
    attribute verificationId : String = "MN-VER-01-S04";

    subject system : MemNetSystem;

    objective snapshotLosslessRoundTrip {
      verify snapshotLosslessRoundTripReq;
      verify consistentValueByteCapReq;
      verify consistentFieldCapReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.snap
            .losslessPropertyRoundTrip == true
          and system.core.transport.inProcess.memory.sessions.snap
            .failClosedUnsaveable == true
          and system.core.transport.inProcess.memory.sessions.snap
            .expireSaveUnsaveableNoFile == true
          and system.core.transport.inProcess.memory.sessions.snap
            .expireSaveFailureKeepsRam == true
          and system.core.transport.inProcess.memory.sessions.snap
            .expireSaveFailureCountsCap == true
          and system.core.transport.inProcess.memory.sessions.snap
            .expireSaveFailureWarnRetry == true
          and system.core.transport.inProcess.memory.sessions.snap
            .expireSaveFailureOverdueAccess == true
          and system.core.transport.inProcess.memory.sessions.snap
            .expireSaveFailureClearedBySaveOrClose == true
          and system.core.transport.inProcess.memory.sessions.snap
            .expireSaveOffDropsRam == true
          and system.core.cli.sessionSave.expireSaveFailureKeepsRam
            == true
          and system.core.transport.inProcess.memory.sessions.snap
            .legacy01918Load == true
          and system.core.transport.inProcess.memory.sessions.snap
            .escapeLfCrPipeBackslash == true
          and system.core.transport.inProcess.memory.sessions.snap
            .splitlinesSeparatorsEscaped == true
          and system.core.transport.inProcess.memory.sessions.snap
            .recordSplitLfOnly == true
          and system.core.transport.inProcess.memory.sessions.snap
            .persistUndeclaredProperties == true
          and system.core.transport.inProcess.memory.sessions.snap
            .idColumnWidenedWhenAbsent == true
          and system.core.transport.inProcess.memory.sessions.snap
            .lineBytesOnEmittedLine == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.statementSplitLfOnly == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.labelMatchCaseFold == true
          and system.core.cli.sessionSave.failClosedUnsaveable == true
          and system.core.cli.sessionLoad.legacy01918Load == true
          and system.core.transport.inProcess.memory.sessions.caps
            .valueBytesOnDecodedRaw == true
          and system.core.transport.inProcess.memory.sessions.caps
            .gqlMutateEnforcesValueBytes == true
          and system.core.transport.inProcess.memory.sessions.caps
            .gqlMutateEnforcesMaxFields == true
          and system.core.transport.inProcess.memory.sessions.caps
            .saveUsesSameFieldCountAsMutate == true
          and system.core.transport.inProcess.memory.sessions.snap
            .saveNeverStricterThanMutate == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.gqlFieldsHardCap == true
      }
    }
  }

  verification def MN_VER_01_S05_SessionLifecycleAclWho {
    doc /*
      MN-REQ-01.10 — session save / load-into-ACL / close who-check when
      session ACL is enabled. --caller / MEMNET_CALLER. Same codes.
    */
    attribute verificationId : String = "MN-VER-01-S05";

    subject system : MemNetSystem;

    objective sessionLifecycleAclWho {
      verify sessionLifecycleAclWhoReq;
      require constraint {
        system.core.cli.sessionSave.acceptsCaller == true
          and system.core.cli.sessionSave.aclWhoWhenEnabled == true
          and system.core.cli.sessionLoad.acceptsCaller == true
          and system.core.cli.sessionLoad.aclWhoWhenEnabled == true
          and system.core.cli.sessionClose.acceptsCaller == true
          and system.core.cli.sessionClose.aclWhoWhenEnabled == true
          and system.core.transport.inProcess.memory.sessions.caps
            .sessionSaveLoadCloseAclWho == true
      }
    }
  }

  verification def MN_VER_03_S01_HonourWherePredicate {
    doc /*
      MN-REQ-03.4 — MATCH WHERE SET/DELETE honours the predicate or
      refuses unsupported_predicate with nothing applied.
    */
    attribute verificationId : String = "MN-VER-03-S01";

    subject system : MemNetSystem;

    objective honourWherePredicate {
      verify honourWherePredicateReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.honourWhereOrRefuse == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.whereTrueEdgeDeleteKept == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.matchMapEqualityKept == true
      }
    }
  }

  verification def MN_VER_05_S01_ConsistentValueByteCap {
    doc /*
      MN-REQ-05.3 — one decoded value_bytes cap; knob MEMNET_MAX_VALUE_BYTES;
      default 32768 (#238); GQL mutate refuses over-cap.
    */
    attribute verificationId : String = "MN-VER-05-S01";

    subject system : MemNetSystem;

    objective consistentValueByteCap {
      verify consistentValueByteCapReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .envMaxValueBytes == "MEMNET_MAX_VALUE_BYTES"
          and system.core.transport.inProcess.memory.sessions.caps
            .maxValueBytesDefault == 32768
          and system.core.transport.inProcess.memory.sessions.caps
            .valueBytesOnDecodedRaw == true
          and system.core.transport.inProcess.memory.sessions.caps
            .gqlMutateEnforcesValueBytes == true
          and system.core.transport.inProcess.memory.sessions.caps
            .lineBytesOnEmittedLine == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.gqlValueBytesHardCap == true
      }
    }
  }

  verification def MN_VER_05_S02_ConsistentFieldCap {
    doc /*
      MN-REQ-05.4 / MN-REQ-01.9 — one effective-field cap; default 64;
      knob MEMNET_MAX_FIELDS; mutate refuses over-cap with
      limit_exceeded|fields n/max and writes nothing; save uses the
      same helper (save never stricter than write); snapshot load of
      a SCHEMA over the cap refuses loudly; snapshot_unsaveable stays
      the save backstop. Tests: tests/test_field_cap.py.
    */
    attribute verificationId : String = "MN-VER-05-S02";

    subject system : MemNetSystem;

    objective consistentFieldCap {
      verify consistentFieldCapReq;
      verify snapshotLosslessRoundTripReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .envMaxFields == "MEMNET_MAX_FIELDS"
          and system.core.transport.inProcess.memory.sessions.caps
            .maxFieldsDefault == 64
          and system.core.transport.inProcess.memory.sessions.caps
            .gqlMutateEnforcesMaxFields == true
          and system.core.transport.inProcess.memory.sessions.caps
            .saveUsesSameFieldCountAsMutate == true
          and system.core.transport.inProcess.memory.sessions.snap
            .saveNeverStricterThanMutate == true
          and system.core.transport.inProcess.memory.sessions.snap
            .sharedEffectiveFieldCount == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.gqlFieldsHardCap == true
      }
    }
  }

  verification def MN_VER_05_S03_SessionCapEvictOldestTouch {
    doc /*
      MN-REQ-05.5 R1 (shipped, unreleased) — at MEMNET_MAX_SESSIONS on open
      or load, after purge_expired, evict the live session with the oldest
      last touch, ordered by (modified_at, touch_seq). Any caller read in
      READ-SURFACES and any write is a touch; reads in NON-TOUCH-READS and
      saves in MAINTENANCE-SAVES are not. Open is the first touch.
      Runtime checks:
      tests/test_session_evict.py::test_evicts_oldest_touched_first,
      ::test_reads_and_writes_are_touches,
      ::test_non_touch_reads_do_not_touch (parametrized over NON_TOUCH_READS),
      ::test_maintenance_save_is_not_a_touch (parametrized over the saves
      reachable from tests),
      ::test_never_read_earliest_open_is_victim,
      ::test_caller_read_is_a_touch_and_moves_lru_pick (parametrized over
      READ_SURFACES),
      ::test_tie_touch_order_a_then_b_evicts_a,
      ::test_tie_touch_order_b_then_a_evicts_b,
      ::test_open_assigns_touch_seq,
      ::test_victim_order_compares_modified_at_as_instant.
      Open as first touch (read-touch regression):
      tests/test_read_touch_regression.py::test_open_stamps_first_touch.
      Presence and surface-list sync: the sysml session-evict sync module
      in tests/ (not an xfail runtime file).
    */
    attribute verificationId : String = "MN-VER-05-S03";

    subject system : MemNetSystem;

    objective sessionCapEvictOldestTouch {
      doc /*
        Runtime: tests/test_session_evict.py (oldest-touch order, touch
        semantics, admin reads not touches). Status guard only below.
      */
      verify sessionCapEvictLruReq;
      verify sessionTtlAndCapsReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .evictShipped == true
      }
    }
  }

  verification def MN_VER_05_S04_SessionCapEvictSaveFirst {
    doc /*
      MN-REQ-05.5 R2 (shipped) — the victim is saved to its snapshot first
      (temp file, fsync, rename, fsync dir; 0600; @SNAP v2 with the ACL),
      then dropped from RAM. The victim lock is held from pick through
      save, drop and registry removal. A crash after fsync and before drop
      leaves a complete snapshot. A failed save never drops RAM. Runtime checks
      : tests/test_session_evict.py::
      test_victim_saved_before_drop_atomic_fsync,
      ::test_victim_lock_held_from_pick_through_drop,
      ::test_crash_after_fsync_before_drop_is_restorable,
      ::test_failed_save_never_drops_ram,
      ::test_failed_evict_save_is_not_a_touch,
      ::test_mutate_waiting_on_dropped_victim_is_refused_not_lost,
      ::test_dir_fsync_io_failure_keeps_victim_live,
      ::test_eio_on_evict_save_keeps_victim_live_via_real_write,
      ::test_unsupported_dir_fsync_errno_save_succeeds,
      ::test_real_dir_fsync_io_error_raises,
      ::test_session_save_eio_is_clean_err_not_internal.
    */
    attribute verificationId : String = "MN-VER-05-S04";

    subject system : MemNetSystem;

    objective sessionCapEvictSaveFirst {
      doc /*
        Runtime: tests/test_session_evict.py (save before drop, victim lock,
        crash safety, failed save keeps RAM). Status guard only below.
      */
      verify sessionCapEvictLruReq;
      verify saveSessionSnapshotReq;
      verify snapshotLosslessRoundTripReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .evictShipped == true
      }
    }
  }

  verification def MN_VER_05_S05_SessionCapEvictSkipUnsaveable {
    doc /*
      MN-REQ-05.5 R3 (shipped) — an unsaveable candidate (snapshot_unsaveable,
      over cap, write error) stays live and the next-oldest is tried. No
      auto-drop; the count is reported as sessions_unsaveable_held on
      serve_status and surfaced to admin. Runtime checks:
      tests/test_session_evict.py::test_unsaveable_victim_skipped_next_oldest_tried,
      ::test_unsaveable_held_counted_on_serve_status,
      ::test_unsaveable_held_count_returns_to_zero_after_save,
      ::test_unsaveable_held_count_returns_to_zero_after_close.
    */
    attribute verificationId : String = "MN-VER-05-S05";

    subject system : MemNetSystem;

    objective sessionCapEvictSkipUnsaveable {
      doc /*
        Runtime: tests/test_session_evict.py (skip and count). Status guard
        only below.
      */
      verify sessionCapEvictLruReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .evictShipped == true
      }
    }
  }

  verification def MN_VER_05_S06_SessionCapEvictNoneEvictable {
    doc /*
      MN-REQ-05.5 R4 (shipped) — cap full and no evictable candidate: refuse
      with code limit_exceeded and the message "all sessions are in use";
      nothing is dropped. No snapshot dir means refuse, no eviction; with the
      dir set the same full cap evicts (positive control). The snapshot dir
      and its alias must agree or start refuses (config_conflict). Concurrent
      opens at cap=2: the two opens that pick a victim each succeed, late
      opens are refused while the victims are mid-save, count <= cap throughout.
      Runtime checks : tests/test_session_evict.py::
      test_all_in_use_refusal_drops_nothing,
      ::test_cap_full_with_snapshot_dir_evicts_oldest,
      ::test_no_snapshot_dir_refuses_without_eviction,
      ::test_snapshot_dir_alias_conflict_refuses,
      ::test_cap_two_concurrent_opens_one_victim_per_slot,
      ::test_claim_released_when_open_fails_after_claim,
      ::test_claim_released_when_load_fails_after_claim,
      ::test_serve_status_reports_config_conflict_by_code_only.
    */
    attribute verificationId : String = "MN-VER-05-S06";

    subject system : MemNetSystem;

    objective sessionCapEvictNoneEvictable {
      doc /*
        Runtime: tests/test_session_evict.py (refusal, no snapshot dir,
        concurrent opens). Status guard only below.
      */
      verify sessionCapEvictLruReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .evictShipped == true
      }
    }
  }

  verification def MN_VER_05_S07_SessionCapEvictExemptSelfAndLocked {
    doc /*
      MN-REQ-05.5 R5 (shipped) — exempt from eviction: the session being
      opened or loaded; a session with an open bind; a session with live
      writes (session lock held by an in-flight mutate or commit). A reserve
      (RSV) lease alone does not exempt. No touch window (LATER, not modelled).
      Runtime checks : tests/test_session_evict.py::
      test_session_being_loaded_is_not_evicted,
      ::test_write_locked_session_exempt, ::test_open_bind_exempt,
      ::test_reserve_lease_is_not_an_exemption.
    */
    attribute verificationId : String = "MN-VER-05-S07";

    subject system : MemNetSystem;

    objective sessionCapEvictExemptSelfAndLocked {
      doc /*
        Runtime: tests/test_session_evict.py (exemption set). Status guard
        only below.
      */
      verify sessionCapEvictLruReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .evictShipped == true
      }
    }
  }

  verification def MN_VER_05_S08_SessionCapEvictReportNameNotId {
    doc /*
      MN-REQ-05.5 R6 (shipped) — the caller result carries no cap and no
      eviction field. Admin serve_status reports the evicted session by name
      or tag only, never a real mn_ id, plus the sessions_evicted counter
      (ServeStatusLook on MemNetUsageDashboard, outside MemNetSystem; the
      counter is checked by its deploy attribute, not here). Runtime checks
      : tests/test_session_evict.py::
      test_caller_result_has_no_eviction_field,
      ::test_open_and_load_results_carry_no_cap_fields,
      ::test_admin_report_names_victim_never_mn_id.
    */
    attribute verificationId : String = "MN-VER-05-S08";

    subject system : MemNetSystem;

    objective sessionCapEvictReportNameNotId {
      doc /*
        Runtime: tests/test_session_evict.py (caller silence, admin naming).
        Status guard only below.
      */
      verify sessionCapEvictLruReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .evictShipped == true
      }
    }
  }

  verification def MN_VER_05_S09_SessionCapEvictLoadRestores {
    doc /*
      MN-REQ-05.5 R7 (shipped) — a later session_load restores the evicted
      session from its snapshot: same ACL, no lease carried over (reserve
      leases dropped; the restored session has no bind). The load is a
      touch with a fresh TTL; the reopened session returns restored=true and
      emits no alerts. Rows and edges survive. A commit that names the dropped
      lease (mutate rid=, llm_id) is refused lease_lost: row, field, row count,
      snapshot bytes and mtime, and last touch (SessionMeta.modified_at) are
      all unchanged; the refused commit is not a touch. A rid naming a live
      lease held by another llm_id is refused reserved (existing code). A
      commit with no rid after eviction and reload succeeds. Gated by deploy
      caps.commitRefusesLostLease (= evictShipped). Runtime checks: tests/test_session_evict.py::
      test_restore_keeps_rows_edges_and_acl,
      ::test_restore_carries_no_lease,
      ::test_restore_lease_commit_fails_cleanly,
      ::test_no_rid_commit_after_evict_and_reload_succeeds,
      ::test_rid_held_by_other_llm_refused_reserved,
      ::test_reopen_restored_true_no_alerts,
      ::test_load_is_touch_with_fresh_ttl,
      ::test_touch_seq_not_in_snapshot_fresh_on_load.
    */
    attribute verificationId : String = "MN-VER-05-S09";

    subject system : MemNetSystem;

    objective sessionCapEvictLoadRestores {
      doc /*
        Runtime: tests/test_session_evict.py (restore fidelity, ACL, no lease,
        restored flag, fresh TTL, lost-lease refusal). Status guards only below.
      */
      verify sessionCapEvictLruReq;
      verify loadSessionSnapshotReq;
      verify snapshotAclReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .evictShipped == true
      }
      require constraint {
        system.core.transport.inProcess.memory.sessions.caps
            .commitRefusesLostLease == true
      }
    }
  }

  verification def MN_VER_06_S06_StorageRoles {
    doc /*
      storageRole only where bytes outlive the call: working_memory,
      file_snapshot, cabinet_ego. Explicit save and expire-save are one
      blob. Factory binds exactly one of fake or AgensGraph.
      hydrateFlushCallers="tests": no non-test caller of hydrate/flush.
      serve, IPC, and MCP bind the owner and do not invoke it. The 0.7
      claim is adapter + operator round trip (no runtime caller).
      Neo4j cabinet is archived. MEMNET_NEO4J_* is ignored.
      Archive stays off load.
    */
    attribute verificationId : String = "MN-VER-06-S06";

    subject system : MemNetSystem;

    objective storageRolesPinned {
      verify inProcessPrimaryReq;
      verify durableStoreBehindMemNetReq;
      verify saveSessionSnapshotReq;
      verify sessionTtlAndCapsReq;
      require constraint {
        system.core.transport.inProcess.memory.sessions.store
            .storageRole == "working_memory"
          and system.core.transport.inProcess.memory.sessions.snap
            .storageRole == "file_snapshot"
          and system.core.transport.inProcess.memory.sessions.snap
            .explicitSaveAndExpireSaveOneBlob == true
          and system.durable.storageRole == "cabinet_ego"
          and system.durable.agens.storageRole == "cabinet_ego"
          and system.durable.bindsExactlyOneOf == "fake|agensgraph"
          and system.durable.hydrateFlushCallers == "tests"
          and system.durable.retiredNeo4jEnvIgnored == true
          and system.leftoverArchiveOffLoad == true
      }
    }
  }

  // --- Verification usages (traceability anchors) ---

  verification multitaskModeGroupVerify : MN_VER_12_G00_MultitaskModeGroup;
  verification relevanceGateVerify : MN_VER_12_S01_RelevanceGate;
  verification sharedStoreTransportVerify : MN_VER_12_S02_SharedStoreTransport;
  verification sharedSessionPinMapVerify : MN_VER_12_S03_SharedSessionPinMap;
  verification mintParentTaskVerify : MN_VER_12_S04_MintParentTask;
  verification scopeDelegateEndTurnVerify : MN_VER_12_S05_ScopeDelegateEndTurn;
  verification workerScopedTurnVerify : MN_VER_12_S06_WorkerScopedTurn;
  verification parentReconcileVerify : MN_VER_12_S07_ParentReconcile;
  verification settleMissionTaskVerify : MN_VER_12_S08_SettleMissionTask;
  verification noAssumeReserveVerify : MN_VER_12_S09_NoAssumeReserveIngest;
  verification sharedSessionReceiveVerify : MN_VER_12_S10_SharedSessionReceive;
  verification separateSessionImportVerify : MN_VER_12_S11_SeparateSessionImport;
  verification importGuardHookVerify : MN_VER_12_S12_ImportGuardHook;
  verification asyncParallelDisjointVerify : MN_VER_12_S13_AsyncParallelDisjoint;
  verification cheapLlmImportGuardVerify
    : MN_VER_12_S14_CheapLlmImportGuard;
  verification graphglotParseThenGateVerify
    : MN_VER_09_S01_GraphGlotParseThenGate;
  verification boundedMatchFindNotShippedVerify
    : MN_VER_04_S01_BoundedMatchFindNotShipped;
  verification relativeSeedWalksFromQVerify
    : MN_VER_04_S02_RelativeSeedWalksFromQ;
  verification sessionOutlineEmptyCueVerify
    : MN_VER_04_S03_SessionOutlineEmptyCue;
  verification peakLLastResortVerify
    : MN_VER_04_S04_PeakLLastResort;
  verification pinMapOrderFromObservablesVerify
    : MN_VER_04_S05_PinMapOrderFromObservables;
  verification idNotRequiredOnWireVerify
    : MN_VER_02_S01_IdNotRequiredOnWire;
  verification cousinPointingContrastVerify
    : MN_VER_02_S02_CousinPointingContrast;
  verification targetCommandListNoRequiredIdVerify
    : MN_VER_07_S01_TargetCommandListNoRequiredId;
  verification recallCommitTwoOperatorsVerify
    : MN_VER_13_S01_RecallCommitTwoOperators;
  verification def MN_VER_14_S01_WhereRangeComparison {
    doc /*
      MN-REQ-14.1 (implemented) — < > <= >= in a node WHERE (bare or
      inline) and in a relationship WHERE, with SET and with DELETE, touch
      exactly the matching records and no others
      (tests/test_range_where.py::test_node_range_set_one_match,
      ::test_node_range_delete_one_match,
      ::test_relationship_range_set_updates_every_match,
      ::test_relationship_range_delete_one_match); a node WHERE that
      matches none is refused not_found, more than one cue_conflict
      (::test_node_range_zero_hits_not_found,
      ::test_node_range_many_hits_cue_conflict); a relationship WHERE ...
      DELETE that matches none is refused not_found, more than one
      cue_conflict (::test_relationship_range_delete_cardinality); a right
      operand that is a property, a $param, a boolean, null or a bare word,
      a literal on the left, or a relationship DELETE WHERE on a.* / b.*
      is refused unsupported_predicate (::test_range_bad_operand_refused,
      ::test_range_literal_on_left_refused,
      ::test_relationship_range_refused_unsupported); a range on id (n.id,
      r.id), number or string operand, bare or under AND / OR / NOT, is
      refused unsupported_predicate with rows and session text unchanged
      apart from the #@IDHW: line, while equality on id and a range on
      another field still work
      (tests/test_id_opaque_range.py::test_node_id_range_refused_unchanged,
      ::test_relationship_id_range_refused_unchanged,
      ::test_id_equality_still_works,
      ::test_range_on_non_id_field_still_honoured); a field is numeric iff
      it fully reads as a number; numbers compare as numbers, strings by
      code point; a missing property, an empty value, or a number literal
      against an odd field (1e999, NaN, "-", " 5") does not match
      (tests/test_range_where.py::test_range_no_match_is_not_found);
      NOT over a no-match stays no match; nothing is written on a refusal.
      Type refusal (where_type_mismatch, exit 1, nothing written): a
      quoted number operand is refused at parse, also with no numeric
      data, nested, inline and on a relationship, while a range on id
      stays unsupported_predicate and '' / ' 5' stay strings
      (tests/test_range_type_refusal.py::test_quoted_number_operand_refused,
      ::test_quoted_number_refused_without_numeric_data,
      ::test_quoted_number_refused_nested,
      ::test_quoted_number_refused_inline_where,
      ::test_quoted_number_cli_exact_line,
      ::test_range_on_id_stays_unsupported_predicate,
      ::test_empty_and_space_operands_stay_strings,
      ::test_relationship_quoted_number_refused;
      tests/test_range_where.py::test_range_quoted_number_operand_refused);
      a quoted string against a stored number is refused when evaluated,
      whatever the sibling order, and one numeric row refuses the whole
      statement (tests/test_range_type_refusal.py::test_quoted_string_vs_stored_number_refused,
      ::test_one_numeric_row_refuses_whole_statement,
      ::test_mismatch_refused_whatever_sibling_order,
      ::test_mismatch_refused_inline_where, ::test_mismatch_cli_exact_line,
      ::test_relationship_mismatch_refused;
      tests/test_range_where.py::test_range_string_vs_numeric_field_refused);
      the kept no-match cases stay not_found, a number literal skips
      placeholders and equality stays exact text
      (tests/test_range_type_refusal.py::test_kept_unknown_is_not_found,
      ::test_number_literal_skips_placeholders,
      ::test_equality_is_exact_text); typed-walk --where refuses the same
      way (tests/test_range_type_refusal.py::test_typed_walk_quoted_number_refused,
      ::test_typed_walk_mismatch_refused;
      tests/test_typed_walk_where.py::test_three_valued_string_vs_numeric_field_refused);
      agent MATCH ... RETURN stays product-gated
      (tests/test_range_where.py::test_range_return_refused_product_gate); the CLI mutate path
      honours a range (::test_run_argv_mutate_range_where). A stored rowRev
      such as '000124' is numeric, so it compares with a number literal
      (n.rowRev > 123); a quoted operand is refused where_type_mismatch
      (tests/test_typed_walk_where.py::test_main_use_row_rev_number_operand,
      ::test_main_use_row_rev_quoted_operand_is_refused). A non-finite
      field still matches through a true OR sibling and never under AND
      (tests/test_range_where_nonfinite_or.py::test_non_finite_hit_through_true_or_sibling,
      ::test_non_finite_under_and_with_true_sibling_no_match).
      Behaviour: BoardWakeRead, RangeWhereCompare.
      Before (bb4a4dc) the statement was refused unsupported_predicate.
      Runtime tests: tests/test_range_where.py, tests/test_id_opaque_range.py,
      tests/test_range_type_refusal.py.
    */
    attribute verificationId : String = "MN-VER-14-S01";

    subject system : MemNetSystem;

    objective atelierBoardS01 {
      doc /* Implemented: tests/test_range_where.py and tests/test_id_opaque_range.py assert the range WHERE rules. */
      verify whereRangeComparisonReq;
      verify honourWherePredicateReq;
    }
  }

  verification def MN_VER_14_S02_PagedReadsPastCap {
    doc /*
      MN-REQ-14.2 (PROPOSAL, PARKED for Elon's review) — on a session of
      more than 50 matching rows, repeated reads by cursor or since-filter
      return every row once, in order, each page at most the cap
      (config.py:71), with agent RETURN still forbidden
      (gql_parse_front.py:34). Not accepted; shape only until reviewed.
      Elon's since-filter (keyset paging on 14.1, more-rows flag, unique
      increasing key) is a NOTE on the leaf, not yet this case.
      Behaviour: BoardWakeRead.
    */
    attribute verificationId : String = "MN-VER-14-S02";

    subject system : MemNetSystem;

    objective atelierBoardS02 {
      doc /* PROPOSAL: no runtime test yet; model-level trace only. */
      verify pagedReadsPastCapReq;
    }
  }

  verification def MN_VER_14_S03_TypedDirectedWalks {
    doc /*
      MN-REQ-14.3 (implemented; owner issue #247 items 1-3) — memnet query
      typed-walk / typed_walk.typed_walk walks one edge type from a start
      node in direction out, in or both, 1..k hops (k <= 10), with a
      WHERE on the end node, in a stated order, every bound enforced, over
      an adjacency index kept across every write, rollback and load.
      Behaviour: TypedWalk. Part: TypedWalk.
      Start lookup by the id index: tests/test_typed_walk.py::test_start_not_found,
      ::test_start_cue_conflict, ::test_start_no_anchor,
      ::test_start_edge_nickname_is_not_a_start,
      ::test_start_hid_is_not_accepted, ::test_start_uses_id_index,
      ::test_no_hid_in_output_and_anon_node_shows_no_id.
      Fold: tests/test_typed_walk.py::test_spelling_folds,
      ::test_in_session_stored_folded_and_walked,
      ::test_snake_lower_is_not_folded, ::test_unknown_valid_type_zero_rows,
      ::test_invalid_relation_refused;
      tests/test_walk_index.py::test_legacy_raw_relation_spelling_is_indexed_standard.
      Out / in / both: tests/test_typed_walk.py::test_one_hop_in_far_nodes_with_id_and_every_property,
      ::test_one_hop_out_and_engine_result, ::test_one_hop_in_backward_step_flag,
      ::test_one_hop_both_merges_by_edge_insert_order,
      ::test_default_direction_is_out, ::test_other_types_not_followed,
      ::test_self_loop_gives_no_row, ::test_parallel_edges_one_row_first_edge,
      ::test_edge_to_missing_endpoint_is_skipped.
      WHERE: tests/test_typed_walk_where.py::test_where_operators,
      ::test_leading_where_keyword_is_stripped, ::test_three_valued,
      ::test_non_finite_field_is_unknown,
      ::test_non_finite_matches_through_true_or_sibling,
      ::test_non_finite_and_true_sibling_does_not_match,
      ::test_range_on_id_refused, ::test_other_variable_refused,
      ::test_bad_where_refused_not_internal,
      ::test_where_filters_rows_not_traversal,
      ::test_limit_counts_matching_rows,
      ::test_main_use_row_rev_number_operand,
      ::test_main_use_row_rev_quoted_operand_is_refused,
      ::test_three_valued_string_vs_numeric_field_refused.
      1..k and cycles: tests/test_typed_walk.py::test_chain_of_12_at_max_10,
      ::test_chain_walked_backwards, ::test_cycle_ends,
      ::test_min_hops_skips_rows_but_expands, ::test_shortest_path_wins_bfs.
      Order and rollback: tests/test_typed_walk.py::test_order_is_insertion_not_id,
      ::test_order_follows_edge_insert_not_node_insert,
      ::test_order_survives_rename, ::test_order_ignores_property_values,
      ::test_order_hop_major_then_parent_order, ::test_save_load_keeps_output,
      ::test_cli_session_save_load_keeps_output;
      tests/test_walk_index.py::test_refused_batch_rollback_is_order_exact,
      ::test_refused_batch_rollback_keeps_walk_rows_from_both_ends.
      Each bound: tests/test_typed_walk.py::test_hops_out_of_range,
      ::test_max_hops_ten_is_allowed, ::test_invalid_direction,
      ::test_limit_out_of_range, ::test_limit_500_is_allowed,
      ::test_limit_exact_is_not_truncated,
      ::test_limit_one_short_is_truncated_prefix,
      ::test_examined_budget_truncates_to_prefix, ::test_reply_bytes_truncates;
      tests/test_typed_walk_perf.py::test_default_caps_never_trip_the_budget.
      Reply and surface: tests/test_typed_walk.py::test_reply_lines_exact,
      ::test_reply_forward_two_hops_shape,
      ::test_intermediate_nodes_are_kind_and_id_only,
      ::test_result_cursor_is_none, ::test_empty_walk_reply,
      ::test_return_still_product_gated_beside_the_verb,
      ::test_no_mcp_typed_walk_tool, ::test_leftover_query_walk_unchanged.
      Index and examined: tests/test_walk_index.py::test_typed_edges_by_type_and_direction,
      ::test_adj_after_create_delete_and_relationship_set,
      ::test_adj_after_detach_delete, ::test_adj_after_rename_and_rename_merge,
      ::test_adj_after_same_thing_absorb,
      ::test_verify_flags_in_place_endpoint_edit_and_reindex_repairs,
      ::test_adj_after_snapshot_save_load, ::test_adj_after_checkpoint_restore,
      ::test_adj_after_bypass_import_over_line_cap,
      ::test_adj_after_bypass_guard_rollback,
      ::test_adj_survives_copy_deepcopy_pickle,
      ::test_index_is_never_written_to_a_snapshot,
      ::test_seeded_random_op_sequence_keeps_adjacency;
      tests/test_typed_walk.py::test_examined_reads_only_typed_edges;
      tests/test_typed_walk_perf.py::test_examined_is_exact_for_one_hop,
      ::test_examined_never_exceeds_type_bucket_at_default_limit,
      ::test_walk_never_scans_other_edges, ::test_ten_hop_chain_examined_bound,
      ::test_one_hop_walk_is_linear_in_matching_edges.
      Before (4b8ed16) there was no typed walk: neighbors was untyped and
      undirected.
      Runtime tests: tests/test_typed_walk.py, tests/test_typed_walk_where.py,
      tests/test_walk_index.py, tests/test_typed_walk_perf.py.
    */
    attribute verificationId : String = "MN-VER-14-S03";

    subject system : MemNetSystem;

    objective atelierBoardS03 {
      doc /* Implemented: tests/test_typed_walk.py, tests/test_typed_walk_where.py, tests/test_walk_index.py and tests/test_typed_walk_perf.py assert the typed-walk rules. */
      verify typedDirectedWalksReq;
    }
  }

  verification def MN_VER_14_S04_IdIndexAndLinearLoad {
    doc /*
      MN-REQ-14.4 (implemented) — MemStore keeps a nickname index
      (RecordTable, mem_store.py:34), kept on every write, rollback,
      rename, save / load and checkpoint restore, never stored, with
      verify_indexes() empty after each
      (tests/test_id_index.py::test_index_after_create through
      ::test_seeded_random_op_sequence_keeps_index); a lookup through it
      returns the same rows in the same order as a full scan, duplicate
      nicknames included, and find by an id locator gives the same result
      as the old walk (::test_find_by_id_locator_uses_index); the field
      cap is decided without a row walk
      (::test_single_line_mutate_does_not_walk_rows_for_field_cap,
      ::test_over_cap_write_still_refused_on_large_session); minted ids
      are only checked to be unique among live rows and never minted
      again after a delete, a refused batch, save / load or restore
      (::test_mint_does_not_reuse_deleted_edge_id,
      ::test_mint_never_reuses_across_snapshot_save_load,
      ::test_mint_never_reuses_across_checkpoint_restore,
      ::test_mint_after_refused_bypass_and_gate_batches,
      ::test_mint_skips_live_chosen_ids); no value or order of an id is
      asserted. Pass bars (tests/test_id_index_perf.py): resolve_one and
      match_nickname at most 0.02 ms per call at 5,000 rows
      (::test_resolve_one_is_constant_time,
      ::test_match_nickname_is_constant_time); snapshot load of 8,000
      rows at most 8 x the 2,000-row time, linear not quadratic
      (::test_snapshot_load_is_linear); every loaded edge end resolves
      (::test_loaded_snapshot_edges_resolve). Before (bb4a4dc): lookup
      scanned every row, 1.2-1.7 ms at 31k; 31k load 34.9 s, quadratic.
      Results, order and evict/restore fidelity (MN-VER-05-S09)
      unchanged. Runtime tests: tests/test_id_index.py,
      tests/test_id_index_perf.py.
      Behaviour: SessionLoadLinear.
    */
    attribute verificationId : String = "MN-VER-14-S04";

    subject system : MemNetSystem;

    objective atelierBoardS04 {
      doc /* Implemented: tests/test_id_index.py and tests/test_id_index_perf.py assert the index and linear load. */
      verify idIndexAndLinearLoadReq;
      verify loadSessionSnapshotReq;
    }
  }

  verification def MN_VER_14_S05_RaisableSessionRecordCap {
    doc /*
      MN-REQ-14.5 (PROPOSAL; DEPENDS ON MN-VER-14-S04) — with the cap
      raised above 5,000 (config.py:125) a 7.8k and a 31k record session
      mutate, save and load without rows|n/max refusal, and the default cap
      still refuses at 5,001; tombstones do not count against it. 14.4
      has landed (S04); this case has no runtime test yet. Behaviour: SessionLoadLinear.
    */
    attribute verificationId : String = "MN-VER-14-S05";

    subject system : MemNetSystem;

    objective atelierBoardS05 {
      doc /* PROPOSAL: no runtime test yet; model-level trace only. */
      verify raisableSessionRecordCapReq;
      verify idIndexAndLinearLoadReq;
    }
  }

  verification def MN_VER_14_S06_IdDesign {
    doc /*
      MN-REQ-14.6 (PROPOSAL; traced to 14.4), model-level cases:
      (a) index-vs-scan parity: every id lookup through the index equals a
      full scan; (b) byte-identical save/reload round-trip, no id minted
      or rewritten; (c) concurrent writes plus crash and restore leave zero
      duplicate ids; (d) delete then lookup returns "deleted", never
      not_found and never another record; (e) a write that reuses an
      existing or tombstoned id is refused; (f) a tombstone is an id-only
      entry, does not count against the record cap and counts toward the
      total-bytes cap (14.10); a legacy snapshot loads with an empty
      tombstone set; (g) pin-ingested elements are created by Commit and
      get a minted UUIDv7 like any write, and their locators stay
      properties, not identity (pinIngestDeterministicIdsReq, MN-REQ-11.16).
      Behaviour: IdMintAndRetire;
      state machine IdLifecycle (live, tombstoned, retired).
    */
    attribute verificationId : String = "MN-VER-14-S06";

    subject system : MemNetSystem;

    objective atelierBoardS06 {
      doc /* PROPOSAL: no runtime test yet; model-level trace only. */
      verify idDesignReq;
      verify idIndexAndLinearLoadReq;
      verify idNotRequiredOnWireReq;
      verify noCopyCousinStoreKeyReq;
      verify pinIngestDeterministicIdsReq;
    }
  }

  verification def MN_VER_14_S07_AgentHandlesNotIds {
    doc /*
      MN-REQ-14.7 (PROPOSAL; traced to 14.6), MCP surface only,
      model-level cases:
      (a) no reply of any MCP tool (find, read, walk, error text, pin_map,
      export_pin_map, snap_model, import_slice, session_save, session_load)
      contains a real id; existing MCP reply cases (for example
      MN-VER-07-S01) are re-read as the migration check; (b) a valid handle resolves to its record; (c) a bad or
      stale handle, or one of a deleted record, is refused with a clear
      error, never a different record; (d) snapshots keep real ids and a
      save/reload round-trip is byte-identical; (e) a handle stays valid
      across evict, restore, save and load, and is never reused within the
      process; (f) a foreign handle: a handle minted in session A and
      presented to session B is refused (stale/foreign), even when session
      B holds a record under a handle of the same shape; it never resolves.
      Behaviour: HandleResolve.
    */
    attribute verificationId : String = "MN-VER-14-S07";

    subject system : MemNetSystem;

    objective atelierBoardS07 {
      doc /* PROPOSAL: no runtime test yet; model-level trace only. */
      verify agentHandlesNotIdsReq;
      verify idDesignReq;
    }
  }

  verification def MN_VER_14_S08_DeveloperSurfaceRealIds {
    doc /*
      MN-REQ-14.8 (PROPOSAL; traced to 14.6), developer surface only,
      model-level cases: (a) replies carry the real id; (b) the real id is
      stable across save/reload/restore and usable as an outside
      reference; (c) lookup of a deleted real id returns "deleted", never
      not_found and never another record; (d) the surface is separate:
      the same call through the MCP surface still returns handles only
      (MN-VER-14-S07); (e) the MCP credential is refused on this surface, and a caller without
      the developer credential is refused; the surface is a separate
      listener or transport. Behaviour: DeveloperIdLookup.
    */
    attribute verificationId : String = "MN-VER-14-S08";

    subject system : MemNetSystem;

    objective atelierBoardS08 {
      doc /* PROPOSAL: no runtime test yet; model-level trace only. */
      verify developerSurfaceRealIdsReq;
      verify idDesignReq;
    }
  }

  verification def MN_VER_14_S09_ValueCap32k {
    doc /*
      MN-REQ-14.9 (implemented; runtime tests tests/test_value_cap_32k.py,
      tests/test_line_cap_whole_line.py, tests/test_line_cap_edge_schema.py),
      cases: (a) a value of 32768 bytes is accepted; (b) a value of 32769 bytes is
      refused with a clear error; (c) the cap counts bytes, not characters
      (multi-byte UTF-8); (d) a snapshot written with values of 4096 bytes
      or less still loads; (e) MEMNET_MAX_VALUE_BYTES still overrides the
      default; (f) a 32,768-byte value made only of pipes and backslashes
      (65,536 escaped bytes) is accepted, saves and reloads byte-identical
      under the raised line cap of 135,168 = 4 x 32,768 + 4,096
      (MEMNET_MAX_LINE_BYTES); (g) a snapshot whose values exceed the
      configured cap is refused on load with limit_exceeded value_bytes
      (loader refusal test kept); (h) a 32,768-byte value of \x1c (4x escape,
      131,072 escaped bytes) saves and reloads under the defaults; (i) with
      the line cap lowered below a value's escaped size, the mutate is
      refused limit_exceeded line_bytes|{n}/{max} and nothing is stored;
      (j) multi-field record: a record whose fields each fit the value cap
      but whose whole escaped line exceeds 135,168 bytes (for example two
      32,768-byte values of \x1c, 262,144 escaped bytes) is refused at
      mutate with limit_exceeded line_bytes|{n}/{max} and nothing stored
      (code PR fix/line-cap-whole-line). Behaviour: ValueLineCapEnforce.
    */
    attribute verificationId : String = "MN-VER-14-S09";

    subject system : MemNetSystem;

    objective atelierBoardS09 {
      doc /* Implemented: tests/test_value_cap_32k.py, tests/test_line_cap_whole_line.py, tests/test_line_cap_edge_schema.py. */
      verify valueCap32kReq;
      verify consistentValueByteCapReq;
      verify storeResourceCapsReq;
    }
  }

  verification def MN_VER_14_S10_SessionTotalBytesCap {
    doc /*
      MN-REQ-14.10 (default 163,840,000 bytes, DEFAULT_MAX_SESSION_BYTES),
      cases, run by tests/test_session_bytes_budget.py and
      tests/test_bypass_paths_caps.py: (a) a write that would take the
      escaped snapshot line bytes over the cap is refused with
      limit_exceeded|session_bytes {n}/{max} and writes nothing (session
      byte-identical), through GQL and the pipe protocol; (b) a session
      under the cap is unaffected; (c) MEMNET_MAX_SESSION_BYTES sets the
      cap; (d) deletes skip the check (spy: the budget helper is not
      called); (e) load, save, import, hydrate and ingest apply the same
      check. The default is a deliberate cap, not a floor of what loads.
      Behaviour: ValueLineCapEnforce; state machine SessionByteBudgetStates.
    */
    attribute verificationId : String = "MN-VER-14-S10";

    subject system : MemNetSystem;

    objective atelierBoardS10 {
      doc /* Implemented: tests/test_session_bytes_budget.py, tests/test_bypass_paths_caps.py. */
      verify sessionTotalBytesCapReq;
    }
  }

  verification def MN_VER_14_S11_BypassPathCaps {
    doc /*
      MN-REQ-14.11, run by tests/test_bypass_paths_caps.py. Scope: (a)
      value cap and (c) byte budget apply to snapshot import and durable
      hydrate only; (b) line cap applies to snapshot import, durable hydrate
      and CLI delete/prune. Cases: (a) a record over the value cap is
      refused value_bytes|{n}/{max}; (b) a record, edge
      or SCHEMA line over the line cap is refused line_bytes|{n}/{max};
      (c) a result over the byte budget is refused session_bytes|{n}/{max};
      in every case the session (lines, relations, write order) is
      unchanged and a batch is all-or-nothing; (d) the same input at exactly
      the cap is accepted; (e) hydrate into a session already over a lowered
      budget is refused session_bytes, loads nothing and leaves the durable
      data untouched; (f) CLI delete and prune are never refused by the
      byte budget (spy) but are refused, and remove nothing, when a
      rewritten edge line would pass the line cap; (g) snapshot load refuses
      an over-budget snapshot and registers nothing; save refuses an
      over-budget session and writes no file; (h) ingest commit over budget
      is refused and leaves the session unchanged. Behaviour:
      BypassPathCapEnforce.
    */
    attribute verificationId : String = "MN-VER-14-S11";

    subject system : MemNetSystem;

    objective atelierBoardS11 {
      doc /* Implemented: tests/test_bypass_paths_caps.py. */
      verify bypassPathCapsReq;
    }
  }

  verification def MN_VER_14_S12_IncrementalByteBudget {
    doc /*
      MN-REQ-14.12, run by tests/test_session_bytes_incremental.py and
      tests/test_join_payload_vectorised.py. Cases: (a) after every create,
      update, delete, import, hydrate and load the incremental total
      equals full_recount_total (MEMNET_DEBUG_SESSION_BYTES=1 asserts it);
      (b) a write re-encodes only changed nodes plus the incident edges of
      changed nodes, with one full rebuild only after load, hydrate, a
      store swap (MemStore replaced), a SCHEMA change, a rollback, a
      row-count check mismatch (row count differs from rows seen) or a
      leftover-nick collision; (c) SCHEMA widening by an undeclared key, a
      node rename (edge lines carry endpoint nicks) and relation folding
      are accounted exactly; (d) a bypass_guard rollback, or a failure
      inside the sync, invalidates the ledger and the next check rebuilds
      it equal to a full recount; (e) the refusal text stays
      session_bytes|{total}/{budget} with {total} the partial sum in write
      order; (f) join_payload (str.translate) is byte-identical to the
      former per-character loop (no complexity bound is claimed for
      join_payload); (g) the ledger is dropped on expire and on
      save-on-expire and the next load rebuilds a total equal to a full
      recount, run by
      tests/test_d02_followups.py::test_ledger_dropped_on_expire*.
      Behaviour: SessionByteBudgetStates.
    */
    attribute verificationId : String = "MN-VER-14-S12";

    subject system : MemNetSystem;

    objective atelierBoardS12 {
      doc /* Implemented: tests/test_session_bytes_incremental.py, tests/test_join_payload_vectorised.py; (g) tests/test_d02_followups.py::test_ledger_dropped_on_expire*. */
      verify incrementalByteBudgetReq;
    }
  }

  verification def MN_VER_14_D01_TwoStepWalkRegression {
    doc /*
      DEFECT record (not a requirement; no fix claimed). The two-step walk
      (neighbors from the ask) is up to about 42% slower (235 -> 333 ms is
      +41.7%) from ee36a95 (235 ms) to
      bb4a4dc (333 ms) for the same 19,593 elements, in every run of
      bench/memnet-engine.py (platform-plan repo, not this one). Cause not investigated; #230 changed only the write
      side and match_nodes (now mem_store.py:523). Open until a run
      identifies the change.
    */
    attribute verificationId : String = "MN-VER-14-D01";

    subject system : MemNetSystem;

    objective atelierBoardD01 {
      doc /* PROPOSAL: no runtime test yet; model-level trace only. */
      verify anchoredWalkReq;
      verify queryFanoutCapsReq;
    }
  }

  verification def MN_VER_14_D02_WhereRelationSetRefusedAsDelete {
    doc /*
      DEFECT record, FIXED (not a requirement). A WHERE on a relationship
      pattern combined with SET was refused with a DELETE message (wrong
      refusal text, SET named as DELETE); MN-REQ-03.4 requires
      honour-or-refuse with an accurate code. Fixed: the SET applies to
      exactly the matching relationships, nothing is deleted, and an
      unsupported relationship WHERE shape is refused
      unsupported_predicate naming the clause used, with the session
      unchanged. Follow-ups (PR #246 review): (B1) a relationship
      WHERE+SET that matches nothing, or whose end id does not resolve,
      is refused not_found with no write; (B2) SET on a protected
      relationship field (id, merge, src, dist, relation) is refused
      invalid_field with no write; (B3) a relationship SET with no WHERE
      and no id pattern is refused unsupported_predicate naming SET /
      WHERE (never DELETE) with no write, while a SET whose relationship
      pattern carries an id ([r {id:…}]) needs no WHERE; an end-node id
      alone does not exempt it (refused unsupported_predicate); quoted
      literals in WHERE or SET are never scanned as SET targets. tests/test_d02_where_set_refusal.py
      and tests/test_d02_followups.py assert the fix; the end-node id case
      is tests/test_d02_followups.py::test_b3_set_with_only_end_node_id_is_refused
      and ::test_b3_refusal_names_relationship_id_pattern.
      Behaviour: WhereSetRefusalFix (implemented).
    */
    attribute verificationId : String = "MN-VER-14-D02";

    subject system : MemNetSystem;

    objective atelierBoardD02 {
      doc /* Implemented: tests/test_d02_where_set_refusal.py and tests/test_d02_followups.py assert the fix. */
      verify honourWherePredicateReq;
    }
  }

  verification recallDoesNotAbsorbVerify
    : MN_VER_13_S02_RecallDoesNotAbsorb;
  verification catalogModelSnapVerify
    : MN_VER_11_S17_CatalogModelSnap;
  verification durableCabinetHonestyVerify
    : MN_VER_06_S01_DurableCabinetHonesty;
  verification humanUsageLookOnlyVerify
    : MN_VER_06_S02_HumanUsageLookOnly;
  verification deviceFleetOneDropletMcpVerify
    : MN_VER_06_S03_DeviceFleetOneDropletMcp;
  verification ssotToCodeAllocateVerify
    : MN_VER_06_S04_SsotToCodeAllocate;
  verification expireSaveConfigurableVerify
    : MN_VER_01_S03_ExpireSaveConfigurable;
  verification snapshotLosslessRoundTripVerify
    : MN_VER_01_S04_SnapshotLosslessRoundTrip;
  verification sessionLifecycleAclWhoVerify
    : MN_VER_01_S05_SessionLifecycleAclWho;
  verification honourWherePredicateVerify
    : MN_VER_03_S01_HonourWherePredicate;
  verification consistentValueByteCapVerify
    : MN_VER_05_S01_ConsistentValueByteCap;
  verification consistentFieldCapVerify
    : MN_VER_05_S02_ConsistentFieldCap;
  verification sessionCapEvictOldestTouchVerify
    : MN_VER_05_S03_SessionCapEvictOldestTouch;
  verification sessionCapEvictSaveFirstVerify
    : MN_VER_05_S04_SessionCapEvictSaveFirst;
  verification sessionCapEvictSkipUnsaveableVerify
    : MN_VER_05_S05_SessionCapEvictSkipUnsaveable;
  verification sessionCapEvictNoneEvictableVerify
    : MN_VER_05_S06_SessionCapEvictNoneEvictable;
  verification sessionCapEvictExemptSelfAndLockedVerify
    : MN_VER_05_S07_SessionCapEvictExemptSelfAndLocked;
  verification sessionCapEvictReportNameNotIdVerify
    : MN_VER_05_S08_SessionCapEvictReportNameNotId;
  verification sessionCapEvictLoadRestoresVerify
    : MN_VER_05_S09_SessionCapEvictLoadRestores;
  verification storageRolesVerify : MN_VER_06_S06_StorageRoles;
  verification lanMcpFrontSeveralServesVerify
    : MN_VER_06_S07_LanMcpFrontSeveralServes;
  verification clusterRouteVsSliceHandCarryVerify
    : MN_VER_06_S08_ClusterRouteVsSliceHandCarry;
  verification serveRequestIsolationVerify
    : MN_VER_06_S11_ServeRequestIsolation;
  verification safeServeUpgradeVerify
    : MN_VER_06_S12_SafeServeUpgrade;
  verification serveCheckpointVerify
    : MN_VER_06_S13_ServeCheckpoint;
  verification snapshotAclVerify
    : MN_VER_06_S14_SnapshotAcl;
  verification restartRestoreNewestSetVerify
    : MN_VER_06_S15_RestartRestoreNewestSet;
  verification mcpExtraFailFastVerify
    : MN_VER_06_S16_McpExtraFailFast;
  verification housekeepEndpointIdentityVerify
    : MN_VER_04_S06_HousekeepEndpointIdentity;
  verification whereRangeComparisonVerify
    : MN_VER_14_S01_WhereRangeComparison;
  verification pagedReadsPastCapVerify
    : MN_VER_14_S02_PagedReadsPastCap;
  verification typedDirectedWalksVerify
    : MN_VER_14_S03_TypedDirectedWalks;
  verification idIndexAndLinearLoadVerify
    : MN_VER_14_S04_IdIndexAndLinearLoad;
  verification raisableSessionRecordCapVerify
    : MN_VER_14_S05_RaisableSessionRecordCap;
  verification idDesignVerify
    : MN_VER_14_S06_IdDesign;
  verification agentHandlesNotIdsVerify
    : MN_VER_14_S07_AgentHandlesNotIds;
  verification developerSurfaceRealIdsVerify
    : MN_VER_14_S08_DeveloperSurfaceRealIds;
  verification valueCap32kVerify
    : MN_VER_14_S09_ValueCap32k;
  verification sessionTotalBytesCapVerify
    : MN_VER_14_S10_SessionTotalBytesCap;
  verification bypassPathCapsVerify
    : MN_VER_14_S11_BypassPathCaps;
  verification incrementalByteBudgetVerify
    : MN_VER_14_S12_IncrementalByteBudget;
  verification twoStepWalkRegressionVerify
    : MN_VER_14_D01_TwoStepWalkRegression;
  verification whereRelationSetRefusedAsDeleteVerify
    : MN_VER_14_D02_WhereRelationSetRefusedAsDelete;
}
