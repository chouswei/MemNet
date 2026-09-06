# Skill graph (this MemNet checkout)

**Audience:** model. Wire SSOT: [memnet-format](memnet-format/SKILL.md) and `docs/grammar/gql-wire-profile.md`. Do **not** treat this file as the session graph.

This folder **vendors** the MemNet stack. Hatch **0.19.5**; last published PyPI is **`memnet-llm==0.19.4`** until upload. Cue then `pin_map`; `find` if ego unknown. **GQL only.** Package SemVer `a.b.c` (claim / usage-method revision / same-method cut): `docs/ROADMAP.md`. Do not invent 0.20.

## Routing

1. Extract keywords from the request.
2. Match **Core** first, then specialists (at most two passes).
3. Open that folder’s `SKILL.md`. Lazy-load `references/` only when a step needs them.
4. Still unclear → repo `AGENTS.md`.

Default **one** skill per turn. Hub [`memnet-use`](memnet-use/SKILL.md) unless a specialist trigger is a better match. Hub descriptions do **not** list MCP tool names, GQL BIND, nested `session=`, or Multitask transport — those live on the matching core skill.

### Core

| Intent | Skill |
|--------|--------|
| How to use MemNet (goldfish, chat never SSOT) | `memnet-use` |
| MCP tools, session, ingest, RSV, export | `mcp-memnet` |
| GQL wire / shaped `pin_map` | `memnet-format` |
| Nested sessions / look loop / already-built interior | `memnet-nested-sessions` |
| Multitask / Task workers / shared session | `memnet-multitask` |

### Specialists

| Intent | Skill |
|--------|--------|
| Code MOD/SYM snap | `memnet-codebase-snap` |
| SysML 6-step mission turn | `sysml-modeling-workflow` |
| SysML session checklist | `sysml-modeling-session-checklist` |
| SysML cache defer | `sysml-memnet-cache` |
| SysML snap / read policy | `sysml-memnet-documentation` |
| SysML × GQL bridge | `sysml-gql` |
| SysML token laws / Snap stack | `docs/application-notes/system/llm-sysml-v2-modeling.md` |

### Build

| Intent | Skill |
|--------|--------|
| Develop MemNet engine / MCP / grammar | `memnet-reference` |

## Core stack (edges)

```cypher
(:SKL {name: 'memnet-use'})-[:DEFAULT_STACK {note: 'tools'}]->(:SKL {name: 'mcp-memnet'})
(:SKL {name: 'memnet-use'})-[:DEFAULT_STACK {note: 'wire'}]->(:SKL {name: 'memnet-format'})
(:SKL {name: 'memnet-use'})-[:COMPLEMENTS {note: 'nested'}]->(:SKL {name: 'memnet-nested-sessions'})
(:SKL {name: 'memnet-multitask'})-[:REQUIRES {note: 'shared'}]->(:SKL {name: 'mcp-memnet'})
(:SKL {name: 'sysml-modeling-session-checklist'})-[:DEFAULT_STACK]->(:SKL {name: 'sysml-modeling-workflow'})
(:SKL {name: 'sysml-modeling-workflow'})-[:DEFAULT_STACK]->(:SKL {name: 'sysml-memnet-documentation'})
(:SKL {name: 'sysml-gql'})-[:COMPLEMENTS]->(:SKL {name: 'memnet-format'})
```

Load `memnet-reference` only when **building** this product. Multitask ops: `docs/operations/multi-agent-sessions.md`. Shape: `docs/SHAPE.md`.
