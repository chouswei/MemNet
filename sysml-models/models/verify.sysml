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
  RecallCommit modelled (MN-VER-13-S01); leftover goldfish claimed in 0.5.
  SameThingAbsorb is a Commit rule (MN-VER-13-S02); Recall SHALL NOT absorb.
  DurableBuffer honesty (MN-VER-06-S01): Agens liveCabinetClaimed;
  Neo4j client implemented with liveNeo4jClaimed=false.
  Optional id nickname TARGET (MN-VER-02-S01): GraphElement identity;
  CREATE () legal; HiddenStoreHandle off-wire; 0.9 leftover_by_id store.
  TARGET command list cue/pattern only (MN-VER-07-S01): no required-id
  tools on McpFacade / CliFacade; leftover id commands stay leftover_*.
  Cousin pointing contrast (MN-VER-02-S02): TARGET vs seven cousins;
  operatorCount stays 2; liveNeo4jClaimed stays false.
  Catalog model Snap (MN-VER-11-S17): package interiors; look = pin_map.
*/
package MemNetVerification {
  private import ScalarValues::*;
  private import MemNetRequirements::*;
  private import MemNet::*;
  private import MemNetBehaviour::*;
  private import MemNetConnections::*;
  private import MemNetCousinContrast::*;

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
          and multitask.coordinator.importReceive.absorb.actor == "engine"
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
      leftover_empty_seed_skip is leftover, not TARGET. leftover copy-id /
      require_anchor is leftover. operatorCount stays 2. liveNeo4jClaimed
      stays false.
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
            .recall.seed.leftoverEmptySkip.productCommand == false
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
          and system.durable.liveNeo4jClaimed == false
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
      wire; third operator; SameThingAbsorb this cut; Layer;
      flip liveNeo4jClaimed. Engine not claimed (implemented=false).
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
            .recall.leftoverEmptySkip.productCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.leftoverEmptySkip.targetImplemented == false
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
          and system.durable.liveNeo4jClaimed == false
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
      leftoverNewMint, leftover_ingestIsIdRule. liveNeo4jClaimed stays
      false. No IdentityHandle nest — leftover named parts beside flags.
      Recall/Commit nest not thickened.
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
          and system.durable.liveNeo4jClaimed == false
          and system.pinMaps.interface.leftoverLocatorMint == true
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
      stays 2. liveNeo4jClaimed stays false. Contrast MUST NOT nest
      under MemNetSystem.
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
          and contrast.liveNeo4jClaimed == false
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
      honesty; TARGET implemented=false). liveNeo4jClaimed stays false.
      No Layer revival.
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
            .leftover_read_get.productCommand == false
          and system.core.transport.inProcess.memory.sessions.store
            .leftover_read_get.targetImplemented == false
          and system.core.transport.inProcess.memory.sessions.store
            .leftover_by_id.productCommand == false
          and system.core.transport.inProcess.memory.sessions.store
            .leftover_MERGE_by_id.productCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.implemented == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.productCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.targetImplemented == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.leftover_NEW_mint.productCommand == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .commit.mutate.allocator.leftover_AssignedIdMap.productCommand
            == false
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.shapedRead.pinMap.leftover_require_anchor.productCommand
            == false
          and system.pinMaps.interface.matchByLabelsAndProps == true
          and system.pinMaps.interface.leftoverAllocateIsProductCommand
            == false
          and system.pinMaps.interface.leftover_allocate_from_locator
            .productCommand == false
          and system.multitask.coordinator.importReceive.absorb
            .leftoverIdPolicyIsProductCommand == false
          and system.multitask.coordinator.importReceive.absorb
            .matchByLabelsAndProps == true
          and system.multitask.coordinator.importReceive.absorb.idPolicy
            .leftoverIdPolicyIsProductCommand == false
          and system.multitask.coordinator.importReceive.absorb.idPolicy
            .remint.productCommand == false
          and system.durable.liveNeo4jClaimed == false
      }
    }
  }

  verification def MN_VER_06_S01_DurableCabinetHonesty {
    doc /*
      MN-REQ-06.4 — DurableBuffer nest honesty (ImportGuard-style flags).
      AgensGraphAdapter.liveCabinetClaimed remains the 0.7 live cabinet.
      Neo4jAdapter.implemented is the client; liveNeo4jClaimed stays
      false until a live Bolt round-trip. One DurableBuffer; one sync
      owner. HostSearchBridge stays outside MemNetSystem.
    */
    attribute verificationId : String = "MN-VER-06-S01";

    subject system : MemNetSystem;

    objective cabinetHonesty {
      verify durableStoreBehindMemNetReq;
      require constraint {
        system.durable.agens.implemented == true
          and system.durable.agens.liveCabinetClaimed == true
          and system.durable.neo4j.implemented == true
          and system.durable.neo4j.liveNeo4jClaimed == false
          and system.durable.neo4j.honesty.claimed == false
          and system.durable.liveCabinetClaimed == true
          and system.durable.liveNeo4jClaimed == false
      }
    }
  }

  verification def MN_VER_13_S01_RecallCommitTwoOperators {
    doc /*
      MN-REQ-13.1 — two-operator cut (math skeleton; leftover goldfish).
      Honesty: operatorCount == 2; hostSearchInsideSystem == false;
      Commit.oneGate == true; RSV nested under Commit (implemented);
      PinMapShapedRead true / BoundedMatchFind true (#73 seed-only find);
      Layer leftover retire-from-wheel (leftoverLayer.deleteThisPr == false;
      MUST NOT nest under MemNetSystem).
      All examination/test is paradox (docs): outputs/recall-commit-orthodox-plan.md.
    */
    attribute verificationId : String = "MN-VER-13-S01";

    subject system : MemNetSystem;
    subject leftoverLayer : TierACodec;

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
          and leftoverLayer.deleteThisPr == false
          and leftoverLayer.leftoverIssue == "retire-from-wheel"
          and leftoverLayer.mustNotNestOnProductPath == true
      }
    }
  }

  verification def MN_VER_13_S02_RecallDoesNotAbsorb {
    doc /*
      MN-REQ-13.2 / MN-REQ-04.8 — Recall SHALL NOT absorb. RelativeSeed /
      find emit Q honestly; CueConflict on shaped emit when |Q|>1 (Q listed,
      cardinality visible; not a product command). Same name is a candidate
      only. SameThingAbsorb MAY collapse under Commit after that mark,
      distinct from ImportAbsorb. operatorCount stays 2. liveNeo4jClaimed stays false.
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
          and system.durable.liveNeo4jClaimed == false
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
      liveNeo4jClaimed stays false.
    */
    attribute verificationId : String = "MN-VER-11-S17";

    subject system : MemNetSystem;

    objective catalogSnapPackageGrain {
      verify catalogModelSnapReq;
      require constraint {
        system.pinMaps.catalog.implemented == true
          and system.pinMaps.catalog.packageGrain == true
          and system.pinMaps.catalog.lookIsPinMap == true
          and system.pinMaps.catalog.joinIsAbsorbSlice == true
          and system.pinMaps.catalog.absorbWholeS == false
          and system.pinMaps.catalog.dumpModelIntoOneSession == false
          and system.pinMaps.catalog.oneSessionPerReq == false
          and system.pinMaps.catalog.oneSessionPerTsk == false
          and system.pinMaps.catalog.layerProperty == false
          and system.pinMaps.catalog.annRankSessions == false
          and system.pinMaps.catalog.hiddenHandleOnWire == false
          and system.pinMaps.catalog.locatorsAreProperties == true
          and system.pinMaps.catalog.notAThirdOperator == true
          and system.core.cli.catalogSnap.implemented == true
          and system.mcp.tools.catalogSnap.implemented == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .operatorCount == 2
          and system.durable.liveNeo4jClaimed == false
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
  verification boundedMatchFindNotShippedVerify
    : MN_VER_04_S01_BoundedMatchFindNotShipped;
  verification relativeSeedWalksFromQVerify
    : MN_VER_04_S02_RelativeSeedWalksFromQ;
  verification sessionOutlineEmptyCueVerify
    : MN_VER_04_S03_SessionOutlineEmptyCue;
  verification idNotRequiredOnWireVerify
    : MN_VER_02_S01_IdNotRequiredOnWire;
  verification cousinPointingContrastVerify
    : MN_VER_02_S02_CousinPointingContrast;
  verification targetCommandListNoRequiredIdVerify
    : MN_VER_07_S01_TargetCommandListNoRequiredId;
  verification recallCommitTwoOperatorsVerify
    : MN_VER_13_S01_RecallCommitTwoOperators;
  verification recallDoesNotAbsorbVerify
    : MN_VER_13_S02_RecallDoesNotAbsorb;
  verification catalogModelSnapVerify
    : MN_VER_11_S17_CatalogModelSnap;
  verification durableCabinetHonestyVerify
    : MN_VER_06_S01_DurableCabinetHonesty;
}
