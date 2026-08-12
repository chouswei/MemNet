# Outputs

Derived views from `sysml-models/models/`. Model-first; sync here after structural changes.

## Architecture notes

- [system-design-notes.md](system-design-notes.md) - SharedLlmMemory, handoff, nested import + ImportGuard, AsyncTaskDispatch / WorkerPool, M2.5, CIP/oC9

## Case studies

| Study | Story | Patterns |
|-------|--------|----------|
| [multitask-case-study.md](multitask-case-study.md) | Parent/worker shared session; GQL pins; optional path B import | MN-VER-12 S01...S09; goldfish Multitask |
| [session-import-case-study.md](session-import-case-study.md) | Lead **imports** member WM; ImportGuard cheap soft gate (pass/trim/reject) | S10...S12; SessionImportReceive; librarian analogy |
| [async-parallel-conflict-case-study.md](async-parallel-conflict-case-study.md) | Two workers disjoint (happy) vs overlapping dual-write (anti); end-turn; host `EvWorkerReturn` | S13; AsyncTaskDispatch / WorkerPool; MN-REQ-12.5/12.6/12.12 |
| [durable-hydrate-flush-case-study.md](durable-hydrate-flush-case-study.md) | Process death -> flush -> hydrate new session under budget | M2.5 `DurableBuffer`; MN-REQ-06.4; LLM not store-direct |
| [snapshot-passport-case-study.md](snapshot-passport-case-study.md) | `session_save` / `session_load` cold-start without chat dump | `SnapshotStore`; MN-REQ-01.4/01.5; vs durable / import |
| [sysml-modeling-goldfish-case-study.md](sysml-modeling-goldfish-case-study.md) | `TSK_model_memnet` pin_map -> edit -> validate -> MemNet delta | `GoldfishLoop` + SharedLlmMemory; serve_down skip |
| [company-memory-case-study.md](company-memory-case-study.md) | Company analytical SSOT on SharedLlmMemory (`COM_*`) | Investor Role D; dual SSOT; analyse loop |
| [prose-rpg-session-case-study.md](prose-rpg-session-case-study.md) | One RPG beat: pin_map -> option -> validate -> mutate -> re-pin_map | Novel-cut goldfish / beat pipeline (GQL only) |
| [inverting-amp-bind-relation-case-study.md](inverting-amp-bind-relation-case-study.md) | Dual-EDGE `:bind`+ports vs bare relation; law on node; ego `CST_U1` | `BindRelationship` / `LawOnNode` / `PinMapShapedRead` |
| [tech-docs-scpi-case-study.md](tech-docs-scpi-case-study.md) | Atomise SCPI manual; pin_map one subsection | SharedLlmMemory doc working set; GQL `:precedes` |
| [tcp-shared-multitask-case-study.md](tcp-shared-multitask-case-study.md) | Parent+worker on TCP / streamable-http; in-process anti | MN-VER-12-S02; `TcpServeBridge` / handoff |
| [new-mint-batch-case-study.md](new-mint-batch-case-study.md) | `id: 'NEW'` create → response ids → rels; NEW illegal on settle | `IdAllocator` / `MutateWithNew`; wire §2.2 |
| [goldfish-chat-desync-case-study.md](goldfish-chat-desync-case-study.md) | Chat trusted over pin_map; recover by re-pin | MN-REQ-10.1; Write=display |

**Wire for all studies:** openCypher-shaped GQL + shaped `pin_map` (ADR-001). No Layer / md_triple teach.
