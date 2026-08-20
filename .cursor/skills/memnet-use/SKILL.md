---
name: memnet-use
description: >-
  How to use MemNet as mission working memory: cue then pin_map, sparse
  mutate, drop prior maps. Triggers: use memnet, how to use memnet, memnet
  goldfish, pin_map, session graph, memnet MCP, GQL wire, shaped pin map,
  memnet-format, mcp-memnet, memnet-multitask.
metadata:
  pattern: pipeline
  version: "1.0"
  domain: memnet
  product: "0.9.0"
---

# How to use MemNet

Reference skill for **agents using** MemNet — not for building the engine. Doctrine SSOT: `docs/SHAPE.md`, `docs/grammar/gql-wire-profile.md`, `docs/LLM-GUIDE.md`. Open one specialist below; do not paste those files here.

**Product:** Hatch **0.9.0** (PyPI `memnet-llm` still 0.4.6). Chat is never SSOT. Novel-writer is out of scope.

## Goldfish loop

1. **Transport** — in-process MCP for a single agent. If Multitask or Task workers: TCP serve or streamable-http; load [memnet-multitask](../memnet-multitask/SKILL.md). If TCP and serve is down: edit files only; plain Markdown scratch (no TOON/TRON).
2. **Cue** — kind / labels+properties / keyword. If ego unknown: `find` then copy an id. Prefer one live `TSK_*`. leftover `anchor=` is leftover.
3. **`pin_map`** — one session per generate; complete Shape of **this** cue. Drop the prior map next turn.
4. **Act** from that Shape plus the current request. Narrow-Read files at `SYM.line` / `SYM.path`.
5. **Sparse Commit** — MCP/CLI **`mutate`** (GraphElement CREATE / MATCH…SET). leftover `add`/`update` / `id:'NEW'` are leftover-named.
6. **Settle** finished `TSK_*` (`status=settled`; `recycle=delete_on_settle` when done).

## Specialists (open on need)

| Need | Skill |
|------|--------|
| MCP tools, session, ingest | [mcp-memnet](../mcp-memnet/SKILL.md) |
| GQL / shaped `pin_map` wire | [memnet-format](../memnet-format/SKILL.md) |
| Multitask / shared session | [memnet-multitask](../memnet-multitask/SKILL.md) |
| Code `MOD`/`SYM` snap | [memnet-codebase-snap](../memnet-codebase-snap/SKILL.md) |
| SysML SSOT (relatives + sub-unit sessions) | `docs/application-notes/llm-sysml-v2-modeling.md` and `sysml-*` skills |

## MUST NOT

- Dump \(S\), the load tree, or a fat `.sysml` into chat.
- Stack \(N\) nested `pin_map`s in one generate — re-anchor next turn (`session=`).
- Treat chat as ids / paths / mission state.
- `rag_query` / ANN of the session.
- Load [memnet-reference](../memnet-reference/SKILL.md) unless you are **building** this product.
