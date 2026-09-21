# SysML modeling relatives — MemNet cache map

**Authority:** [sysml-memnet-cache](../../sysml-memnet-cache/SKILL.md). Specialists **write** after validate; **read** via cue `pin_map` on `TSK_model_<short>`.

## Read (before edit)

| Need | Warm anchor / tag |
|------|-------------------|
| Project scope | `@TSK` `TSK_model_<short>` |
| Where to edit | `@SYM` → `path\|line` |
| Topology without deploy read | `@PRT`, `@POR`, `@CON` + `@EDG` |
| Requirement audit | `@REQ` |
| Pending decision | `@DEC`, `@ISSUE` |
| Report section | `@ART`, `@SEC`, `@CLM` |
| Interconnection figure | `@TSK` `TSK_diagram_<figureId>` |

## Write (after validate) — by skill

This checkout **vendors** only the skills in [`SKILL-GRAPH.md`](../../SKILL-GRAPH.md). Pack-only generator ids (`sysml-hardware-part-generator`, `sysml-allocate-generator`, mermaid, PCBA, …) are **not** here — MUST NOT invent those folders.

| Skill id | MemNet rows to add/update |
|----------|---------------------------|
| sysml-modeling-workflow | campaign `@TSK`; structure `@PRT`/`@REQ`/`@CON` + `@SYM`; `satisfies` |
| sysml-ssot-to-code | `SoftwareAllocate` relatives; cue `goal=TSK_model_alloc`; ledger path on `@PRT` / `@MOD` |
| sysml-gql | `satisfies` / `allocates` edges; `hasPort`; no pack-only allocate-generator |
| sysml-memnet-documentation | snap / read-policy locators; `@SYM.line` refresh |
| sysml-modeling-session-checklist | campaign `@TSK` only (no structure invent) |
| memnet-reference | product-build claims only; MUST NOT duplicate allocate ledger |

Skills not listed: if they touch `.sysml` structure, use the matching row above or hub [sysml-memnet-snap.md](sysml-memnet-snap.md) §Delta write. MUST NOT load leftover `sysml-allocate-generator`.

## Forbidden in MemNet

- Full `deploy-*.sysml` paste
- Paragraph requirement text (use `@REQ` id + one-line `text` field)
- Duplicate `AGENT-CONTEXT` topology prose
- Chat scrollback as substitute for `pin_map`

## Initial snap (warm_miss)

On first warm hit with zero `@PRT`/`@SYM` for a non-trivial project:

1. `add` `@TSK`, all `@MOD` from `config.yaml`
2. Grep each `part def`, `requirement def`, `connection def` → `@PRT`/`@REQ`/`@CON` + `@SYM`
3. `session_save` → `<model-root>/.memnet/<short>.snap`

Procedure: [sysml-memnet-snap.md](sysml-memnet-snap.md#initial-snap-warm-miss-only).
