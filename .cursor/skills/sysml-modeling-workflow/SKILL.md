---
name: sysml-modeling-workflow
description: >-
  Primary SysML workflow in this MemNet repo: MemNet-first turn, model-first
  .sysml edits, validate, outputs sync. Triggers: modeling workflow, memnet sysml,
  6-step turn, sysml-models.
metadata:
  pattern: pipeline
  domain: sysml-v2
  version: "1.6"
  product: memnet-llm==0.19.3
  pairs_with: [sysml-memnet-cache, sysml-memnet-documentation, sysml-gql, sysml-modeling-session-checklist, mcp-memnet, memnet-nested-sessions, sysml-ssot-to-code]
token_guardrails: |
  - Follow the turn table. This checkout is repo-based: .sysml is model SSOT; MemNet is relatives.
  - Downstream SysMLEdge-based: bound desk hosts the model graph (playbook host mode).
  - pin_map from a cue before edit; mutate after validate.
  - Nested interiors: memnet-nested-sessions (not N maps in one generate).
---

# SysML modeling workflow

This **MemNet product** checkout is **repo-based**: **`sysml-models/`** is model SSOT here. Downstream packs may use `sysml-v2-models/projects/<slug>/` or a **SysMLEdge-based** bound desk — copy the host from that repo’s operator README / `AGENTS.md`. MemNet stays campaign working memory.

## Turn sequence

| Step | Action | MemNet |
|------|--------|--------|
| **1** | In-process: skip serve probe. TCP: `serve_status`; if down → `.sysml` only | — |
| **2** | `pin_map(kind='TSK', locators=['goal=TSK_model_<short>'], …)` leftover `anchor=` / `id=` named leftover | READ |
| **3** | Narrow `Read` at `SYM.line`; edit `sysml-models/models/*.sysml` | — |
| **4** | Validate the textual model (project SysML MCP / CLI if present) | — |
| **5** | Sync `sysml-models/outputs/` iff structure changed | — |
| **6** | `mutate` delta + `SYM.line` refresh; settle the turn | WRITE |

**Warm miss** → [sysml-memnet-snap.md](../sysml-memnet-documentation/references/sysml-memnet-snap.md), then step 3.

**Look loop** (catalog / interiors) is **not** a seventh table step: [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md) and `docs/application-notes/system/llm-sysml-v2-modeling.md`.

Skip step 6: comment-only; MemNet down; question with no edit.

### Read budget

Pin map first. At most two `Read` windows at `SYM.line`. Do not re-read whole `deploy.sysml` on a warm hit. Policy: [sysml-memnet-read-policy.md](../sysml-memnet-documentation/references/sysml-memnet-read-policy.md).

### Model-first

1. Edit **`sysml-models/models/*.sysml`**.
2. Validate; sync **`sysml-models/outputs/`**.
3. Align engine/MCP code only when the model says so. Which file realises a part: [sysml-ssot-to-code](../sysml-ssot-to-code/SKILL.md) (allocate map; MUST NOT invent `sysmledge`).

## Routing (this checkout)

| Need | Path |
|------|------|
| Relatives cache | [sysml-memnet-cache](../sysml-memnet-cache/SKILL.md) |
| Snap / patterns | [sysml-memnet-documentation](../sysml-memnet-documentation/SKILL.md) |
| Thin GQL bridge | [sysml-gql](../sysml-gql/SKILL.md) |
| SSOT → code tracker | [sysml-ssot-to-code](../sysml-ssot-to-code/SKILL.md) |
| Preflight | [sysml-modeling-session-checklist](../sysml-modeling-session-checklist/SKILL.md) |
| MCP tools | [mcp-memnet](../mcp-memnet/SKILL.md) |

Hardware generators, Mermaid, `mcp-sysml-v2`, and pack-only `sysml-*` skills are **not** vendored here. Do not invent those paths.

## See also

- [AGENTS.md](../../../AGENTS.md)
- `docs/application-notes/system/llm-sysml-v2-modeling.md`
