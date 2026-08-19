# SysML modeling relatives — MemNet cache map

**Authority:** [sysml-memnet-cache](../../sysml-memnet-cache/SKILL.md). Specialist skills **write** these tags after `mcp-sysml-v2` validate; **read** via `pin_map(TSK_model_<short>)`.

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

| Skill id | MemNet rows to add/update |
|----------|---------------------------|
| sysml-hardware-part-generator | `@PRT`, `@POR`, `@SYM`, `hasPort`, `declaredIn`, `inFile` |
| sysml-software-part-generator | same as hardware |
| sysml-physical-port-generator | `@POR` (port def), `@SYM`, `typedBy` |
| sysml-software-port-generator | same |
| sysml-item-generator | `@ITM`, `@SYM`, `flowOf` |
| sysml-connections | `@CON`, `@SYM`, connection `@EDG` ends |
| sysml-nested-structure-modeling | `@PRT` tree, `@SYM`, composition `@EDG` |
| sysml-requirements-generator | `@REQ`, `@SYM` |
| sysml-traceability | `@EDG` `satisfies`, `allocates` |
| sysml-behaviour-generator | `@BEH`, `@SYM`, owner `@EDG` |
| sysml-allocate-generator | `@EDG` `allocates` |
| sysml-refactorer | batch `@SYM.line` refresh; rename `@PRT`/`@POR`/`@CON`; `@CLM` refactor note |
| sysml-requirements-audit | `@ISSUE`, `@CLM` finding |
| sysml-part-reviewer | `@DEC`, `@CLM` maturity |
| sysml-view-doc-sync | `@CLM` key claims; report `@ART`/`@SEC` if pack |
| sysml-interconnection-mermaid | `@TSK` `TSK_diagram_*`, figure `@EDG` |
| sysml-new-project | `@TSK`, `@MOD`, `owns` `@EDG` |
| sysml-root-config | `@MOD` load-order note `@CLM` |
| sysml-common-lib-contribution | `@PRT`/`@POR` in lib + `@CONV` if naming rule |
| sysml-pcba-de-facto-alignment | `@PRT` de-facto attrs `@CLM` |
| sysml-pcba-de-facto-alignment | `@CLM` netlist / de-facto bridge status (no full netlist in MemNet) |

Skills not listed: if they touch `.sysml` structure, use the matching row above or hub [sysml-memnet-snap.md](sysml-memnet-snap.md) §Delta write.

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
