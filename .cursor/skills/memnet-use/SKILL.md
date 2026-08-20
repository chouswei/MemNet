---
name: memnet-use
description: >-
  How to use MemNet as mission working memory: goldfish loop, chat never
  SSOT, drop prior maps. Triggers: use memnet, how to use memnet, memnet
  goldfish, mission working memory, chat never SSOT, session graph.
metadata:
  pattern: pipeline
  version: "1.3"
  domain: memnet
  product: "0.19.3"
---

# How to use MemNet

**Using** MemNet — not building the engine. This checkout **vendors** the stack under `.cursor/skills/`. Doctrine: `docs/SHAPE.md`, `docs/grammar/gql-wire-profile.md`, `docs/LLM-GUIDE.md`. Open **one** specialist; do not paste those files here.

Hatch **0.19.3**. Chat is never SSOT. Novel-writer is out of scope. **GQL only.**

## Goldfish loop

1. **Open** — `session_open` with a SCHEMA map (`map_file` / `map_lines`) covering every kind you will mutate. Missing kind → `unknown_tag`. Bundled maps: `parts/common/memnet/memnet/examples/schema.*.example.txt`.
2. **Transport** — single agent: in-process MCP. Multitask / Task workers: TCP or streamable-http; load [memnet-multitask](../memnet-multitask/SKILL.md). Shared serve down: files only; plain Markdown.
3. **Cue** — `kind` + labels+properties (`goal` / `name` / `qname` / `path` / `requirementId`) / keyword. Ego unknown: `find(limit=…)` then `pin_map` from that pattern. Prefer one live `TSK_*`. leftover `anchor=` is leftover. Empty cue = session outline (0.11). CueConflict when \(|Q|>1\) — do not pick one root.
4. **`pin_map`** — one \(S\) per generate; complete Shape of **this** cue. **Drop** the prior map next turn.
5. **Act** from that Shape plus the current request. Narrow-Read files at `SYM.line` / `SYM.path`.
6. **Sparse Commit** — MCP/CLI **`mutate`** (`CREATE` / `MATCH`…`SET`/`DELETE`). leftover `add`/`update` / `id:'NEW'` are leftover-named.
7. **Settle** finished `TSK_*` (`status=settled`; `recycle=delete_on_settle` when done).

## Core specialists (open on need)

| Need | Skill |
|------|--------|
| MCP tools, ingest, RSV, export | [mcp-memnet](../mcp-memnet/SKILL.md) |
| GQL / shaped `pin_map` | [memnet-format](../memnet-format/SKILL.md) |
| Nested sessions / look loop | [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md) |
| Multitask / shared session | [memnet-multitask](../memnet-multitask/SKILL.md) |

Code `:MOD`/`:SYM`: [memnet-codebase-snap](../memnet-codebase-snap/SKILL.md). SysML: `docs/application-notes/system/llm-sysml-v2-modeling.md` and `sysml-*`.

## MUST NOT

- Dump \(S\) or a fat `.sysml` into chat.
- Stack \(N\) nested `pin_map`s in one generate — re-anchor with MCP `session=` / locator `session=`.
- Treat chat as ids / paths / mission state.
- `rag_query` / ANN of the session.
- Load [memnet-reference](../memnet-reference/SKILL.md) unless **building** this product.
