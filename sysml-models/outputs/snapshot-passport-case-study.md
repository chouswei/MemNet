# Case study: snapshot passport (session save / load)

Evidence walk against SysML under `sysml-models/models/`.  
Companions: [durable-hydrate-flush-case-study.md](durable-hydrate-flush-case-study.md), [session-import-case-study.md](session-import-case-study.md).

**Wire:** GQL / shaped `pin_map` only. Snapshot is a **named session file**, not a chat transcript.

## 1. Purpose

Lead or host B **cold-starts** a mission without pasting graph dumps into chat: `session_save` / `session_load` (or a bounded `WorkingMemorySlice` export) carries schema + records + relations. Session id remains the handoff handle after load (optional keep-id per MN-REQ-01.6).

## 2. Model locus

| Concern | Model element |
|---------|----------------|
| Parts | `SnapshotStore` nested under `SessionLifecycle` |
| Ports / flows | `SessionSnapshotOutPort` / `SessionSnapshotInPort` |
| Behaviour | `SessionLifecycleStates` - save/load transitions (`EvLoadSnapshot`, etc.) |
| Requirements | MN-REQ-01.4 SaveSessionSnapshot; 01.5 Load; 01.6 OptionalKeepSessionId; 01.7 / 01.8 handoff |
| Distinct from | MN-REQ-11 pin-map export (`PinMapIngest_*`); M2.5 `DurableBuffer` |

## 3. Scenario

**Title:** Host B resumes modelling without chat dump

**Premise:** Host A finishes a Multitask wave on session `sess_model_7`, settles some `TSK_*`, saves a snapshot passport. Host B (new machine / process) loads the passport and continues via `pin_map` - no `EvDumpGraphInChat`.

### Steps

| Step | Action | Model |
|------|--------|--------|
| 1 | Host A works; facts in session | `GraphStore` + GQL mutate |
| 2 | `session_save` -> snapshot file | `SnapshotStore` / MN-REQ-01.4 |
| 3 | Deliver **session id + snapshot locator** (or load path) | `SessionHandoff` spirit - not prose dump |
| 4 | Host B `session_load` | MN-REQ-01.5; optional keep session id (01.6) |
| 5 | `pin_map` first | `GoldfishLoop` / MN-REQ-04 |
| 6 | Continue mutate / Multitask | Same dialect; ids preserved **or** reminted per load policy |

### Illustrative GQL after load

```cypher
// Ids preserved under keep-id policy (illustrative)
CREATE (t:Task {id: 'TSK_model_memnet', status: 'active'})
CREATE (m:Module {id: 'MOD_deploy', path: 'sysml-models/models/deploy.sysml'})
CREATE (t)-[:TOUCHES]->(m)
```

If policy remints ids, host B copies new ids from the first `pin_map` only - chat must not invent the old ids.

### Optional path B slice

When only a **bounded** subgraph should move (separate sessions, Multitask import): export `WorkingMemorySlice` -> lead `SessionImportReceive` / `ImportGuard` - see [session-import-case-study.md](session-import-case-study.md). That is **import**, not full session snapshot.

## 4. Gates

| MUST | MUST NOT |
|------|----------|
| Treat snapshot as structured session passport | Treat chat / tool transcript as the save |
| Distinguish session snapshot from MN-REQ-11 pin ingest | Confuse `SnapshotStore` with `PinMapIngest_*` |
| pin_map after load before mutate | Assume ids without reading the live slice |
| Handoff by session id (+ locator) | `EvDumpGraphInChat` |

## 5. Snapshot vs durable vs import

| Mechanism | Role | Shipped claim |
|-----------|------|----------------|
| `SnapshotStore` save/load | Process/file passport for a named session | As-is session save/load capability (product); model traces 01.4/01.5 |
| `DurableBuffer` hydrate/flush | Online GQL store behind MemNet | M2.5 roadmap only |
| `WorkingMemorySlice` import | Lead imports member WM (path B) | Doctrine + ImportGuard nest |

## 6. Related

| Study | Link |
|-------|------|
| Durable M2.5 | [durable-hydrate-flush-case-study.md](durable-hydrate-flush-case-study.md) |
| Session import | [session-import-case-study.md](session-import-case-study.md) |
| SysML goldfish | [sysml-modeling-goldfish-case-study.md](sysml-modeling-goldfish-case-study.md) |
