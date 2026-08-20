# SysML MemNet — cookbook bridge (this vendor)

Links in-repo MemNet skills to the upstream SysML v2 modeling cookbook. **Do not copy the full cookbook here** — use this bridge for policy and pointers.

## Upstream source

**Path (this repo):** [`docs/application-notes/system/llm-sysml-v2-modeling.md`](../../../../docs/application-notes/system/llm-sysml-v2-modeling.md)  
**Evidence:** [`sysml-models/outputs/sysml-session-nest-cuts-case-study.md`](../../../../sysml-models/outputs/sysml-session-nest-cuts-case-study.md)

**Package:** Hatch **0.19.3** (last PyPI **`memnet-llm==0.19.0`** until upload). Do not use the old root path `application-notes/` (part-based layout: `docs/application-notes/`).

The cookbook is the **agent loop** (two token laws, Snap stack, look loop). In-repo skills **MUST** follow the canonical tag map in [sysml-memnet-patterns.md](sysml-memnet-patterns.md) — not leftover alias tags. Agent I/O is **GQL**; leftover pipe `@TAG` names in the map are leftover nicknames for kinds.

## Unified-tag policy (fixed)

| Rule | Detail |
|------|--------|
| Part / port / behaviour | Single tags `@PRT`, `@POR`, `@BEH` with **`kind`** field |
| **MUST NOT** write | `@PARTD`, `@PORTD`, `@BEHD`, `@TASK` in new rows |
| Warm miss over legacy graph | Re-snap into unified tags (full §Initial snap in [sysml-memnet-snap.md](sysml-memnet-snap.md)) |
| satisfy / allocate | **`@EDG` only** (`satisfies`, `allocates`); `@SYM` kind=`satisfy`/`allocate` only when line locator needed |

## Load order (agents)

1. [sysml-memnet-snap.md](sysml-memnet-snap.md) — mandatory 6-step turn sequence
2. [sysml-memnet-read-policy.md](sysml-memnet-read-policy.md) — when to read `.sysml` vs warm
3. [sysml-memnet-pipeline.md](sysml-memnet-pipeline.md) — pipeline wire (`@CLM` type=`pipe`)
4. [sysml-memnet-patterns.md](sysml-memnet-patterns.md) — canonical map, construct table, EDG list
5. **This file** — upstream pointer + legacy ban
6. Cookbook (upstream) — loop + look loop when snap.md is the mission `TSK` only

## What stays in this vendor vs cookbook

| Topic | This vendor | Cookbook |
|-------|-----------|----------|
| Turn sequence, warm miss, line drift | snap.md | — |
| Read budget, anti-patterns (no deploy re-read) | read-policy.md | — |
| Pipeline step wire (`@CLM` type=`pipe`) | pipeline.md | — |
| 19-tag map, id rules, kind enums | patterns.md | aligned |
| Per-file grep, delta matrix | snap.md | examples |
| Multi-turn evidence | — | nest-cuts case study (Turns A–I) |
| MemNet CLI / MCP tool params | mcp-memnet skill | `docs/LLM-GUIDE.md` |

## Reconciliation checklist

When cookbook and this vendor disagree:

1. **Kind names** — vendor patterns win (`POR` not `PORT`; no `PARTD`)
2. **Field order** — canonical map in patterns.md wins
3. **Batch EDG rules** — patterns construct table wins
4. **Worked examples** — cookbook for narrative; rewrite examples to unified tags when copying into MemNet

## Session persistence

Session `.snap` file: [sysml-memnet-snap.md](sysml-memnet-snap.md). Never paste snap file contents into chat. Model Snap (`snap_model`) is a different operator — see the cookbook.

## Related skills

- [sysml-memnet-documentation/SKILL.md](../SKILL.md) — hub
- [memnet-format](../../memnet-format/SKILL.md) — wire-format cheat sheet
- [sysml-new-project](../../sysml-new-project/SKILL.md) — step 12 session_open map
