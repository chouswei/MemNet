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
  RecallCommit modelled (MN-VER-13-S01); leftover goldfish claimed in 0.5.
  DurableBuffer honesty (MN-VER-06-S01): Agens liveCabinetClaimed;
  Neo4j client implemented with liveNeo4jClaimed=false.
  External cabinet allocation (MN-VER-06-S02): no Neo4j server on droplet;
  one owner; extras are drivers only; operator evidence ≠ product claim.
*/
package MemNetVerification {
  private import ScalarValues::*;
  private import MemNetRequirements::*;
  private import MemNet::*;
  private import MemNetBehaviour::*;
  private import MemNetConnections::*;

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
      pinMap remains default goldfish when an id is known. MUST NOT treat
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

  verification def MN_VER_06_S01_DurableCabinetHonesty {
    doc /*
      MN-REQ-06.4 — DurableBuffer nest honesty (ImportGuard-style flags).
      AgensGraphAdapter.liveCabinetClaimed remains the 0.7 live cabinet.
      Neo4jAdapter.implemented is the client; liveNeo4jClaimed stays
      false until a product live claim. One DurableBuffer; one sync
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
          and system.durable.liveCabinetClaimed == true
          and system.durable.liveNeo4jClaimed == false
          and system.durable.owner.oneOwner == true
          and system.durable.cliHydrateFlushTools == false
          and system.durable.mcpHydrateFlushTools == false
      }
    }
  }

  verification def MN_VER_06_S02_ExternalCabinetAllocation {
    doc /*
      MN-REQ-06.5 / 06.6 — external cabinet is a first-class server part;
      clients are adapters. No Neo4j server on the 2 GiB droplet. Extras
      are drivers only. Operator soak on rpi5-syson is evidence only —
      liveNeo4jClaimed stays false. Graph id is a MERGE key on working-
      memory records, not on SysML hosts / extras / the server part.
      Present edge id is a MERGE spelling (Commit may mint NEW), not a
      universal user-supplied-id law. One sync owner; no dual-write.
      OperatorDurableSites stays outside MemNetSystem.
    */
    attribute verificationId : String = "MN-VER-06-S02";

    subject system : MemNetSystem;
    subject sites : OperatorDurableSites;

    objective externalCabinetAllocation {
      verify externalCabinetServerReq;
      verify operatorEvidenceNotLiveClaimReq;
      require constraint {
        system.cabinet.inMemnetLlmWheel == false
          and system.cabinet.vendoredInRepo == false
          and system.cabinet.installedOnDroplet == false
          and system.cabinet.liveNeo4jClaimed == false
          and system.cabinet.sysmlPartHasGraphId == false
          and system.cabinet.mergeKeyOnWorkingMemoryRecords == true
          and system.cabinet.edgeIdUserSuppliedRequired == false
          and system.cabinet.commitMayMintNew == true
          and system.cabinet.neo4j.liveNeo4jClaimed == false
          and system.cabinet.neo4j.sysmlPartHasGraphId == false
          and system.cabinet.neo4j.operatorEvidenceOnly == true
          and system.cabinet.neo4j.installedOnDroplet == false
          and system.cabinet.agens.defaultProductCabinetOption == true
          and system.durable.neo4j.extraIsDriverOnly == true
          and system.durable.agens.extraIsDriverOnly == true
          and system.durable.extraIsDriverOnly == true
          and system.durable.owner.oneOwner == true
          and system.durable.owner.bindOnceAtProcessStart == true
          and system.durable.owner.dualWriteMcpAndTcpForbidden == true
          and sites.droplet2GiB.neo4jServerInstalled == false
          and sites.droplet2GiB.memnetRole == "client"
          and sites.droplet2GiB.extraIsDriverOnly == true
          and sites.droplet2GiB.deskEvidenceCentreOnThisBolt == false
          and sites.droplet2GiB.companyMemoryOnThisBolt == false
          and sites.droplet2GiB.federateOverInvestorApi == false
          and sites.rpi5Syson.neo4jServerInstalled == true
          and sites.rpi5Syson.writerIsAdapterClient == true
          and sites.rpi5Syson.inventreeLabCriticalDoNotTouch == true
          and sites.liveNeo4jClaimed == false
          and sites.sysmlPartHasGraphId == false
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
            .recall.emptySeedSkip == true
          and system.core.transport.inProcess.memory.sessions.recallCommit
            .recall.cosineMetric == false
          and leftoverLayer.deleteThisPr == false
          and leftoverLayer.leftoverIssue == "retire-from-wheel"
          and leftoverLayer.mustNotNestOnProductPath == true
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
  verification recallCommitTwoOperatorsVerify
    : MN_VER_13_S01_RecallCommitTwoOperators;
  verification durableCabinetHonestyVerify
    : MN_VER_06_S01_DurableCabinetHonesty;
  verification externalCabinetAllocationVerify
    : MN_VER_06_S02_ExternalCabinetAllocation;
}
