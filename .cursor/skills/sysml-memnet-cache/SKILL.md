---
name: sysml-memnet-cache
description: >-
  MemNet is the cache for SysML modeling relatives. Specialists read pin_map
  and write mutate deltas; never duplicate in chat. Triggers: sysml cache,
  warm read sysml, defer memnet, avoid re-read deploy.
metadata:
  pattern: tool-wrapper
  domain: sysml-v2,memnet
  version: "1.5"
  product: memnet-llm==0.19.3
  pairs_with: [sysml-memnet-documentation, mcp-memnet, sysml-modeling-workflow, sysml-modeling-session-checklist, memnet-format, sysml-gql]
token_guardrails: |
  - .sysml is structure; MemNet is relatives; AGENT-CONTEXT is session stub.
  - pin_map before edit; mutate after validate. leftover add/update named leftover.
---

# SysML MemNet cache

Specialist `sysml-*` skills **read/write here**. They do not keep a parallel memory.

## Model root (this checkout)

| Layout | Root | Snap |
|--------|------|------|
| **This repo** | `sysml-models/` | `sysml-models/.memnet/` |
| Downstream pack | `sysml-v2-models/projects/<slug>/` | that project’s `.memnet/` |

Copy the live root from `AGENTS.md`. Stale `path=` in an old snap is not SSOT.

## Three stores

| Store | Holds |
|-------|-------|
| `models/*.sysml` | Structure, satisfy — edit first |
| MemNet | Relatives — cue `pin_map` then `mutate` |
| `AGENT-CONTEXT.md` | Session id only |

Kinds: [sysml-memnet-patterns.md](../sysml-memnet-documentation/references/sysml-memnet-patterns.md). Who writes what: [relatives-cache-map.md](../sysml-memnet-documentation/references/relatives-cache-map.md).

## Loop

```text
0. MCP in catalog? If no → .sysml only
1. pin_map cue TSK_model_<short>
   first fill: ingest_sysml or snap_model (catalog) — locators, no leftover NEW
2. edit models/*.sysml
3. validate
4. mutate delta + SYM.line; session_save
```

Nested interiors: [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md). Tools: [mcp-memnet](../mcp-memnet/SKILL.md).

**MUST NOT** call `pin_map` / `mutate` when tools are absent.

## Persistence

`session_save` → `<model-root>/.memnet/<short>.snap`. Resume: `session_load` or `MEMNET_SESSION`.
