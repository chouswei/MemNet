# Outputs

Derived views from `sysml-models/models/`. Model-first; sync here after structural changes.

## Architecture notes

- [system-design-notes.md](system-design-notes.md) - SharedLlmMemory, handoff, nested import + ImportGuard, AsyncTaskDispatch / WorkerPool, M2.5, CIP/oC9

## Principles (once)

chat ≠ SSOT · session = handle · GQL gated · write = display · MemNet = buffer · budgeted ego · lead owns mission memory.

**Wire for all studies:** openCypher-shaped GQL + shaped `pin_map` (ADR-001). No Layer / md_triple teach.

## Case studies — two shelves

Keep **all** studies. **Product canon** = MemNet mechanism / principles. **Application examples** = patterns on SharedLlmMemory (not extra product cores). See each file's `**Shelf:**` line.

### Product canon

| Study | Story | Patterns |
|-------|--------|----------|
| [goldfish-chat-desync-case-study.md](goldfish-chat-desync-case-study.md) | Chat trusted over pin_map; recover by re-pin | MN-REQ-10.1; Write=display |
| [multitask-case-study.md](multitask-case-study.md) | Parent/worker shared session; GQL pins; optional path B import | MN-VER-12 S01…S09; goldfish Multitask |
| [async-parallel-conflict-case-study.md](async-parallel-conflict-case-study.md) | Canon companion: two workers disjoint vs overlapping dual-write; end-turn; host `EvWorkerReturn` | S13; AsyncTaskDispatch / WorkerPool |
| [tcp-shared-multitask-case-study.md](tcp-shared-multitask-case-study.md) | Transport under Multitask: TCP / streamable-http shared store; in-process anti | MN-VER-12-S02; `TcpServeBridge` / handoff |
| [session-import-case-study.md](session-import-case-study.md) | Lead **imports** member WM; ImportGuard cheap soft gate (optional path B detail) | S10…S12; SessionImportReceive |
| [snapshot-passport-case-study.md](snapshot-passport-case-study.md) | `session_save` / `session_load` cold-start without chat dump | `SnapshotStore`; MN-REQ-01.4/01.5 |
| [durable-hydrate-flush-case-study.md](durable-hydrate-flush-case-study.md) | Process death → flush → hydrate new session under budget | M2.5 `DurableBuffer`; MN-REQ-06.4 |
| [new-mint-batch-case-study.md](new-mint-batch-case-study.md) | Canon mutate discipline: `id: 'NEW'` → response ids → rels; NEW illegal on settle | `IdAllocator` / `MutateWithNew`; wire §2.2 |

### Application examples (on SharedLlmMemory)

| Study | Story | Patterns |
|-------|--------|----------|
| [company-memory-case-study.md](company-memory-case-study.md) | Company analytical SSOT (`COM_*`) | Investor Role D; dual SSOT; analyse loop |
| [evidence-centre-case-study.md](evidence-centre-case-study.md) | ai-investor EvidenceCentre librarian / MissionDock on SharedLlmMemory | Library / Wanted / Requisition / DelayQueue; soft librarian vs MutateGate |
| [prose-rpg-session-case-study.md](prose-rpg-session-case-study.md) | One RPG beat: pin_map → option → validate → mutate → re-pin_map | Novel-cut goldfish / beat pipeline (GQL only) |
| [inverting-amp-bind-relation-case-study.md](inverting-amp-bind-relation-case-study.md) | Dual-EDGE `:bind`+ports vs bare relation; law on node; ego `CST_U1` | `BindRelationship` / `LawOnNode` / `PinMapShapedRead` |
| [tech-docs-scpi-case-study.md](tech-docs-scpi-case-study.md) | Atomise SCPI manual; pin_map one subsection | Doc working set; GQL `:precedes` |
| [sysml-modeling-goldfish-case-study.md](sysml-modeling-goldfish-case-study.md) | Meta: MemNet as MBSE agent design memory (`TSK_model_memnet`) | `GoldfishLoop`; serve_down skip |
