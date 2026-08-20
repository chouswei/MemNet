---
name: sysml-memnet-documentation
description: >-
  SysML design memory and model snap: pin_map before edit, mutate after
  validate. Triggers: memnet sysml, model snap, TSK_model, avoid re-read deploy.
metadata:
  pattern: pipeline
  domain: sysml,memnet
  version: "1.11"
  product: memnet-llm==0.19.2
  pairs_with: [sysml-memnet-cache, sysml-modeling-workflow, mcp-memnet, memnet-format, sysml-gql, memnet-nested-sessions]
token_guardrails: |
  - 6-step snap in sysml-memnet-snap.md. Read policy: topology from pin_map.
  - Unified labels PRT/POR/BEH. leftover NEW / leftover anchor= named leftover.
---

# SysML MemNet (design memory)

**Cache defer:** [sysml-memnet-cache](../sysml-memnet-cache/SKILL.md). Tools: [mcp-memnet](../mcp-memnet/SKILL.md). Wire: [memnet-format](../memnet-format/SKILL.md). Nest: [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md).

`.sysml` is structure. MemNet holds locators, claims, backlog. **Do not** re-read whole `deploy.sysml` on a warm hit.

## Load order

1. [sysml-memnet-snap.md](references/sysml-memnet-snap.md)
2. [sysml-memnet-read-policy.md](references/sysml-memnet-read-policy.md)
3. [sysml-memnet-pipeline.md](references/sysml-memnet-pipeline.md)
4. [sysml-memnet-patterns.md](references/sysml-memnet-patterns.md)
5. [relatives-cache-map.md](references/relatives-cache-map.md)
6. [sysml-memnet-cookbook-bridge.md](references/sysml-memnet-cookbook-bridge.md)
7. `docs/application-notes/system/llm-sysml-v2-modeling.md`

## Prerequisites

1. Install **0.19**: `pip install 'memnet-llm[mcp]'` (Hatch **0.19.2**; pin `==0.19.2` after PyPI upload, else last wheel is **0.19.0**). Optional `[neo4j]` (live claimed 0.14; drivers only). Contributors: `pip install -e ".[mcp]"`.
2. MemNet tools in the catalog. If absent: edit `.sysml` only.
3. SysML map: `parts/common/memnet/memnet/examples/schema.sysml.example.txt`.

## When

- This repo: `sysml-models/` + `TSK_model_<short>`
- Decisions / locators / outputs atoms (`ART` / `SEC` / `CLM`)
- Skip: one-shot question; comment-only; MCP missing

## Cues

Campaign `goal=TSK_model_<short>`. Structure by `name` / `qname` / `path` / `requirementId`. leftover nickname `id` is leftover.

satisfy / allocate = relationships only.
