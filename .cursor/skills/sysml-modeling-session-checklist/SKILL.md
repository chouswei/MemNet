---
name: sysml-modeling-session-checklist
description: >-
  Short preflight before substantive SysML v2 modeling in this MemNet repo.
  Triggers: start modeling session, preflight checklist, memnet sysml.
metadata:
  pattern: pipeline
  domain: sysml-v2
  version: "1.3"
  product: memnet-llm==0.19.3
  pairs_with: [sysml-memnet-documentation, sysml-memnet-cache, sysml-modeling-workflow, mcp-memnet]
token_guardrails: |
  - Thin: do not paste the load tree. MemNet first. leftover anchor= named leftover.
---

# SysML modeling session checklist

Use when about to **edit `.sysml`**. Hub turn: [sysml-modeling-workflow](../sysml-modeling-workflow/SKILL.md).

## After the checklist, state

- **project** — `sysml-models/` (this repo) or the live `AGENTS.md` root
- **campaign** — `TSK_model_<short>` (cue `goal=`; leftover `anchor=` is leftover)
- **warm** — `warm_hit` | `warm_miss`
- **read plan** — symbols from the map only
- **next** — target `models/*.sysml`

## Pipeline

0. **MemNet** — in-process: skip `serve_status`. Cue `pin_map(kind='TSK', locators=['goal=TSK_model_<short>'], …)`. leftover `anchor=` / `id=` named leftover. Warm miss → [initial snap](../sysml-memnet-documentation/references/sysml-memnet-snap.md#initial-snap-warm-miss-only).
1. **Root** — `sysml-models/config.yaml` and files to touch. [read policy](../sysml-memnet-documentation/references/sysml-memnet-read-policy.md).
2. **Ambiguous scope** — confirm with the user; do not invent architecture only in Markdown.
3. **Sequence** — [sysml-modeling-workflow](../sysml-modeling-workflow/SKILL.md). Nest cuts: [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md).
4. **After edits** — validate; outputs if structure changed; **`mutate`** delta unless comment-only or MemNet down.
