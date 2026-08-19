---
name: sysml-memnet-cache
description: >-
  MemNet MCP is the single cache for SysML modeling relatives — topology, locators, requirements,
  traceability, decisions, audit findings, diagram scope, report atoms. Specialist sysml-* skills
  read via pin_map and write deltas here; never duplicate in chat or AGENT-CONTEXT. Triggers:
  sysml cache, memnet cache, modeling relatives, warm read sysml, cache topology, defer memnet,
  specialist post-edit, avoid re-read deploy.
metadata:
  pattern: tool-wrapper
  domain: sysml-v2,memnet
  version: "1.4"
  pairs_with: [sysml-memnet-documentation, mcp-memnet, sysml-modeling-workflow, sysml-modeling-session-checklist, memnet-format, sysml-gql]
token_guardrails: |
  - MemNet is the cache; .sysml is source of truth for structure; AGENT-CONTEXT is session+anchor only.
  - pin_map(TSK_model_<short>) before substantive edit; add/update delta after mcp-sysml-v2 validate.
  - Atomise only — one fact per GQL/shaped graph row; never store full .sysml or paragraph prose.
  - Skip cache write: comment-only edit, serve down / MCP missing, question-only turn (see sysml-memnet-snap.md).
---

# SysML MemNet cache (modeling relatives)

**Role:** MemNet is the **cache** for everything SysML modeling needs between turns that is **not** already authoritative in project `models/*.sysml`.

Specialist **`sysml-*`** skills (generators, reviewers, refactorers) **do not** keep their own parallel memory. They **read** from and **write** to this cache via **`mcp-memnet`** tools.

## Model root layouts

| Layout | Model root | Typical snap dir | Example anchor |
|--------|------------|------------------|----------------|
| Multi-project pack | `sysml-v2-models/projects/<slug>/` | `…/projects/<slug>/.memnet/` | `TSK_model_<short>` |
| System repo (`modelbasedPrj-*`) | `sysml-models/` (+ optional `parts/*/model/`) | `sysml-models/.memnet/` | e.g. NCU-LEO: `TSK_model_leo_cubesat` |

**MUST** copy the live repo root from `AGENTS.md` / `AGENT-CONTEXT.md`. **MUST NOT** invent `sysml-v2-models/…` paths when the workspace only has `sysml-models/`. Stale `path=` fields in an old `.memnet` wire/snap are not SSOT — re-snap or fix locators before trusting them.

## Three stores

| Store | Holds | Agent rule |
|-------|-------|------------|
| Project `models/*.sysml` | Structure, syntax, satisfy | Edit first; validate |
| **MemNet** | Relatives (below) | `pin_map` -> act -> GQL/openCypher-shaped delta |
| `AGENT-CONTEXT.md` | Session id + anchor + short summary | Never topology/backlog |

## What counts as a “relative”

Atomised rows the warm graph must carry so the next turn avoids re-reading deploy:

| Kind | Relative kind | Typical source skill |
|-----|---------------|---------------------|
| `PRT` / `POR` | Parts, ports | hardware/software part generators, nested-structure |
| `CON` | Connection defs/usages | sysml-connections |
| `BEH` | States, events | sysml-behaviour-generator |
| `REQ` | Requirement defs | sysml-requirements-generator |
| `ITM` | Flow items | sysml-item-generator |
| `SYM` | File + line locators | **every** substantive edit |
| `MOD` | Model file registry | sysml-new-project, root-config |
| Typed rels | satisfies, allocates, hasPort, declaredIn | traceability, refactorer |
| `DEC` / `ISSUE` | Open choices, backlog | part-reviewer, requirements-audit |
| `CONV` | Site conventions | common-lib-contribution |
| `ART` / `SEC` / `CLM` | Report atoms | view-doc-sync, system-design-report |
| `TSK` | Campaign + pipe steps | modeling-workflow |
| `USR` | User constraints that must persist | any turn |

Full kind map: [sysml-memnet-patterns.md](../sysml-memnet-documentation/references/sysml-memnet-patterns.md).
Per-skill write map: [relatives-cache-map.md](../sysml-memnet-documentation/references/relatives-cache-map.md).
Thin bridge: [sysml-gql](../sysml-gql/SKILL.md).

## MCP tool loop (every modeling turn)

```text
0. MemNet MCP in catalog? If no → skip 1–2 and 6–7; plain Markdown only (no TOON/TRON)
1. serve_status (TCP / unsure only; skip under in-process default)
2. pin_map(anchor=TSK_model_<short>, depth=2, max_rows=50)   # READ cache; find then pin_map if ego unknown
   # first snap: ingest_sysml(path=models/) then pin_map — locator ids, no client NEW
3. … specialist skill edits project models/*.sysml …
4. mcp-sysml-v2 validate
5. sysml-view-doc-sync (iff outputs + structure changed)
6. add/update openCypher-shaped rows + refresh SYM line + settle CLM/TSK   # WRITE cache
7. session_save → <model-root>/.memnet/<short>.snap
```

Mechanics: [mcp-memnet](../mcp-memnet/SKILL.md). Procedure: [sysml-memnet-snap.md](../sysml-memnet-documentation/references/sysml-memnet-snap.md). Wire detail: [memnet-format](../memnet-format/SKILL.md) (GQL / shaped pin_map) — do not invent a thinner dialect here.

**MCP wire:** EDG `rel` names are **session-registered strings**. SysML closed list: [sysml-memnet-patterns.md](../sysml-memnet-documentation/references/sysml-memnet-patterns.md) (`declaredIn`, `hasPort`, `typedBy`, `inFile`, `satisfies`, `allocates`, …). **Copy exact spellings from the live pin map**; seed unknowns with `allow_new_relation=true`. Engine-generic new edges prefer English verb / snake tokens (MemNet `docs/grammar/`); do not invent a second spelling for an existing link.

## Specialist defer rule

Any **`sysml-*`** skill that changes `.sysml` **MUST**:

1. **Before:** `pin_map` on project anchor (or accept warm_miss → initial snap). If MemNet MCP is missing: edit `.sysml` without cache.
2. **After validate:** emit MemNet delta per [relatives-cache-map.md](../sysml-memnet-documentation/references/relatives-cache-map.md) — do **not** paste topology into chat.

Hub skills own the sequence: [sysml-modeling-workflow](../sysml-modeling-workflow/SKILL.md) step 6.

## Serve down / MCP missing

When MemNet MCP tools are absent from the session catalog, or `serve_status` is false (TCP mode):

- Edit `.sysml` only; note stale/absent graph in one line.
- Ephemeral handoff: plain Markdown tables or short prose (not TOON/TRON).
- **MUST NOT** call `pin_map` / `add` / `update` when tools are unavailable.
- On return: run initial snap or catch-up delta before next substantive edit.

## Session persistence

| Action | When |
|--------|------|
| `session_open` + seed `TSK`/`MOD` | sysml-new-project scaffold |
| `session_save` → `<model-root>/.memnet/<short>.snap` | End of substantive turn or session handoff |
| `session_load` | Resume when `MEMNET_SESSION` unset |

Store snap path in `AGENT-CONTEXT.md` header when used.

## NCU-LEO note (system repo)

Anchor `TSK_model_leo_cubesat`; model root `sysml-models/`. August hybrid ground-test scene lives in the model plus `docs/august-2026-prep-brief.md` — do not treat that brief as MemNet topology.

## References

- [sysml-memnet-documentation](../sysml-memnet-documentation/SKILL.md)
- [sysml-memnet-read-policy.md](../sysml-memnet-documentation/references/sysml-memnet-read-policy.md)
- [memnet-goldfish-loop.mdc](~/.cursor/rules/memnet-goldfish-loop.mdc)
