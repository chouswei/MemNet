# Case study: Session merge — lead receives member working memory

Evidence walk against the on-disk SysML under `sysml-models/models/`.  
Companion: [system-design-notes.md](system-design-notes.md), [multitask-case-study.md](multitask-case-study.md).  
Operational doctrine: `docs/multi-agent-sessions.md`.

## 1. Metaphor (binding)

**Session merge = team lead receives the working memory of a team member.**

| Role | MemNet locus |
|------|----------------|
| Lead | Parent / mission session = lead's working memory (mission SSOT) |
| Member | Worker session or scoped slice = member's working memory |
| Receive | Absorb durable pins into lead session — **not** chat/transcript merge |

**Macro** vs **micro:** this study is **macro** session∪session (or shared-session re-pin). Micro in-session node re-id (`merge=true` security design) is out of scope here.

## 2. Model examination

| Concern | Model locus |
|---------|-------------|
| Shared LLM memory | `SharedLlmMemory`; `AgentMemory` / `SessionLifecycle` |
| Handoff by session id | `SessionHandoff`, `SessionHandoffById`; MN-REQ-01.7 / 01.8 / 12.1 |
| Merge / receive | `SessionMergeRequest`, `WorkingMemorySlice`, `SessionMergeReceive`; MN-REQ-12.9 / 12.10 |
| Lead owns merge | `MultitaskCoordinator`; MN-VER-12-S10 / S11 |
| Forbidden | `EvMergeFromChat`, `EvDumpGraphInChat`; whole-store dump; dual-writer during merge |
| Wire | GQL / shaped pins only (`GqlCodec` CIP/oC9 authority) — no Layer |

### Packages

| File | Merge-relevant content |
|------|------------------------|
| `connections.sysml` | `WorkingMemorySlice`, `SessionMergeRequest`, `SessionHandoff` |
| `behaviour.sysml` | `SessionMergeReceive` (path A / path B) |
| `deploy.sysml` | `MultitaskCoordinator` / `MultitaskWorker` merge ports + slice flow |
| `requirements.sysml` | MN-REQ-12.9, MN-REQ-12.10 (+ 01.7 / 01.8) |
| `verify.sysml` | MN-VER-12-S10 (path A), MN-VER-12-S11 (path B) |

## 3. Fake mission (concrete)

**Mission:** Inventory three pins for an inverting-amplifier note and settle the parent task.

Lead session id: `ses_mission_amp`  
Lead task: `TSK_mission_amp_inventory` (`status=active`)

Member-authored subgraph (GQL-shaped; illustrative):

```text
CREATE (n:Mod {id: 'MOD_amp_note', path: 'docs/application-notes/examples/inverting-amplifier-gql-case-study.md'})
CREATE (s:Sym {id: 'SYM_Rin', kind: 'resistor', refdes: 'Rin'})
CREATE (s2:Sym {id: 'SYM_Rf', kind: 'resistor', refdes: 'Rf'})
CREATE (n)-[:mentions]->(s)
CREATE (n)-[:mentions]->(s2)
CREATE (t:Tsk {id: 'TSK_mission_amp_inventory'})-[:about]->(n)
```

---

## 4. Scenario A — Shared session (no macro-merge)

**Premise:** Lead and member already share `ses_mission_amp` (SessionHandoffById delivered the same id). Whiteboard already shared.

| Step | What happens | Behaviour / event | Requirement |
|------|----------------|-------------------|-------------|
| **A1** | Lead mints `TSK_mission_amp_inventory`; hands off session id + scope | `SessionHandoffById`; `EvDelegateWorker` | MN-REQ-12.1, 12.3, 01.7 |
| **A2** | Member `pin_map` first; mutates MOD/SYM/EDGE under `WorkerWriteScope` | `WorkerScopedTurn` | MN-REQ-12.4 |
| **A3** | Lead **receives** via `EvSharedSessionRepin` / re-`pin_map` only | `SessionMergeReceive.pathASharedRepin` | **MN-REQ-12.9** path A |
| **A4** | Lead settles `TSK_mission_amp_inventory` from session facts | `EvSettleMissionTask` | MN-REQ-12.3 |
| **A5** | No `SessionMergeRequest` / no `WorkingMemorySlice` import | — | MN-REQ-12.10 (no chat merge) |

**Verdict A:** Prefer path A whenever Multitask already shares one session — receive is goldfish re-read, not a merge engine.

---

## 5. Scenario B — Separate sessions → receive at settle

**Premise:** Member worked in `ses_member_amp` (separate). Lead mission remains `ses_mission_amp`. At settle, lead receives a **bounded** slice.

| Step | What happens | Behaviour / event | Requirement |
|------|----------------|-------------------|-------------|
| **B1** | Lead issues `SessionMergeRequest` (lead=`ses_mission_amp`, member=`ses_member_amp`, idPolicy=`MERGE_OR_REJECT`) | `EvRequestSessionMerge` → `pathBRequesting` | **MN-REQ-12.9** |
| **B2** | Member exports `WorkingMemorySlice` (anchors `MOD_amp_note`, depth=2, shaped pins) — not whole store | `EvExportWorkingMemorySlice` → `pathBExporting` | MN-REQ-12.10, 04.1 spirit |
| **B3** | Lead absorbs: nodes then edges; conflict ids rejected or reminted per policy | `EvAbsorbWorkingMemorySlice` → `pathBAbsorbing` | MN-REQ-12.9 |
| **B4** | Lead `pin_map` on mission session; settles `TSK_mission_amp_inventory` | `pathBSettling` → `EvSettleMissionTask` | MN-REQ-12.3 |
| **B5** | Chat / transcript merge rejected if attempted | `EvMergeFromChat` → `mergeRejected` | **MN-REQ-12.10** |

**Illustrative slice header (not a dump):**

```text
WorkingMemorySlice {
  sourceSessionId: ses_member_amp
  anchors: MOD_amp_note
  depth: 2
  view: ego
  // payload = shaped subgraph of MOD_amp_note + SYM_Rin + SYM_Rf + mentions
}
```

**Verdict B:** Macro merge is lead-owned, bounded, id-policy gated; chat is never SSOT.

---

## 6. Anti-patterns

| Anti-pattern | Violates |
|--------------|----------|
| Paste member tool transcript into lead chat as "merge" | MN-REQ-12.10 (`EvMergeFromChat`) |
| Export entire member session as handoff | MN-REQ-12.10 / 01.8 |
| Member settles `TSK_mission_*` | MN-REQ-12.3 / 12.9 |
| Dual-writer on same anchors during absorb | MN-REQ-12.5 / 12.7 / 12.10 |
| Treat micro `merge=true` node re-id as this macro receive | Scope error (security design ≠ SessionMergeReceive) |

---

## 7. Verify coverage

| Verify id | Scenario | Verifies |
|-----------|----------|----------|
| MN-VER-12-S10 | A Shared receive | MN-REQ-12.9 path A, 12.1 |
| MN-VER-12-S11 | B Separate merge | MN-REQ-12.9, 12.10 |

Related Multitask steps S01–S09 remain in [multitask-case-study.md](multitask-case-study.md).

## 8. Validation note

Prefer Cursor SysML v2 MCP `validate` on project load (`sysml-models/config.yaml`). Cloud agent run: MemNet serve and mcp-sysml-v2 were unavailable (`serve_down`); syntax checked by review against existing package style.
