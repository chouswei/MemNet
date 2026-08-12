# Outputs

Derived views from `sysml-models/models/`. Model-first; sync here after structural changes.

## Architecture notes

- [system-design-notes.md](system-design-notes.md) — SharedLlmMemory, handoff, nested import + ImportGuard, M2.5, CIP/oC9

## Case studies

| Study | Story | Patterns |
|-------|--------|----------|
| [multitask-case-study.md](multitask-case-study.md) | Parent/worker shared session; GQL pins; optional path B import | MN-VER-12 S01…S09; goldfish Multitask |
| [session-import-case-study.md](session-import-case-study.md) | Lead **imports** member WM; ImportGuard cheap soft gate | S10…S12; librarian analogy |
| [company-memory-case-study.md](company-memory-case-study.md) | Company analytical SSOT on SharedLlmMemory (`COM_*`) | Investor Role D; dual SSOT; analyse loop |
| [prose-rpg-session-case-study.md](prose-rpg-session-case-study.md) | One RPG beat: pin_map → option → validate → mutate → re-pin_map | Novel-cut goldfish / beat pipeline (GQL only) |

**Wire for all studies:** openCypher-shaped GQL + shaped `pin_map` (ADR-001). No Layer / md_triple teach.
