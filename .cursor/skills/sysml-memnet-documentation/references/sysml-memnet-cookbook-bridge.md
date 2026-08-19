# SysML MemNet — cookbook bridge (user pack)

Links user-pack MemNet skills to the upstream SysML v2 modeling cookbook. **Do not copy the full cookbook here** — use this bridge for policy and pointers.

## Upstream source

**Path:** `C:/Projects/MemNet/application-notes/llm-sysml-v2-modeling.md`

**Package:** `memnet-llm` **0.9.0** (editable install from `C:/Projects/MemNet`; PyPI still 0.4.6)

The cookbook defines worked multi-turn examples, relation vocabulary, and batch sizing. User-pack skills **MUST** follow the canonical tag map in [sysml-memnet-patterns.md](sysml-memnet-patterns.md) — not legacy alias tags from older cookbook drafts.

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
6. Cookbook (upstream) — worked turns when pattern/snap insufficient

## What stays in user pack vs cookbook

| Topic | User pack | Cookbook |
|-------|-----------|----------|
| Turn sequence, warm miss, line drift | snap.md | — |
| Read budget, anti-patterns (no deploy re-read) | read-policy.md | — |
| Pipeline step wire (`@CLM` type=`pipe`) | pipeline.md | — |
| 19-tag map, id rules, kind enums | patterns.md | aligned |
| Per-file grep, delta matrix | snap.md | examples |
| Multi-turn dialogue examples | — | full turns |
| MemNet CLI / MCP tool params | mcp-memnet skill | §Tools |

## Reconciliation checklist

When cookbook and user pack disagree:

1. **Tag names** — user pack wins (`@POR` not `@PORT`; no `@PARTD`)
2. **Field order** — canonical map in patterns.md wins
3. **Batch EDG rules** — patterns construct table wins
4. **Worked examples** — cookbook for narrative; rewrite examples to unified tags when copying into MemNet

## Session persistence

Cookbook §Snapshot → [sysml-memnet-snap.md](sysml-memnet-snap.md) §Session `.snap` file. Never paste snap file contents into chat.

## Related skills

- [sysml-memnet-documentation/SKILL.md](../SKILL.md) — hub
- [memnet-format](../../memnet-format/SKILL.md) — wire-format cheat sheet
- [sysml-new-project](../../sysml-new-project/SKILL.md) — step 12 session_open map
