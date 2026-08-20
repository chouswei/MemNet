# Skill graph (this MemNet checkout)

**Audience:** model. Wire SSOT: [memnet-format](memnet-format/SKILL.md) and `docs/grammar/gql-wire-profile.md`. Do **not** treat this file as the session graph.

Product **0.9.0** (PyPI `memnet-llm` still 0.4.6). Cue then `pin_map`; `find` if ego unknown.

This is the **in-repo** MemNet stack only. The full personal pack graph stays in [cursor-user-skills](https://github.com/chouswei/cursor-user-skills) `SKILL-GRAPH.md`.

## Routing

1. Extract keywords from the request.
2. Match the table (at most two passes).
3. Open that folder’s `SKILL.md`.
4. Still unclear → repo `AGENTS.md`.

| Intent | Skill |
|--------|--------|
| Develop MemNet engine / MCP / grammar | `memnet-reference` |
| MCP tools, session, pin_map, ingest | `mcp-memnet` |
| GQL wire / shaped pin_map | `memnet-format` |
| Multitask / Task workers / shared session | `memnet-multitask` |
| Code MOD/SYM snap | `memnet-codebase-snap` |
| SysML 6-step mission turn | `sysml-modeling-workflow` |
| SysML session checklist | `sysml-modeling-session-checklist` |
| SysML cache defer | `sysml-memnet-cache` |
| SysML snap / read policy | `sysml-memnet-documentation` |
| SysML × GQL bridge | `sysml-gql` |
| SysML token laws / Snap stack | `docs/application-notes/llm-sysml-v2-modeling.md` |

## MemNet stack (edges)

```cypher
(:SKL {id: 'mcp-memnet'})-[:COMPLEMENTS {note: 'wire'}]->(:SKL {id: 'memnet-format'})
(:SKL {id: 'memnet-multitask'})-[:COMPLEMENTS {note: 'multitask'}]->(:SKL {id: 'mcp-memnet'})
(:SKL {id: 'memnet-multitask'})-[:COMPLEMENTS {note: 'multitask'}]->(:SKL {id: 'memnet-format'})
(:SKL {id: 'sysml-gql'})-[:COMPLEMENTS {note: 'sysml_bridge'}]->(:SKL {id: 'memnet-format'})
(:SKL {id: 'sysml-modeling-session-checklist'})-[:DEFAULT_STACK {note: 'hub'}]->(:SKL {id: 'sysml-modeling-workflow'})
(:SKL {id: 'sysml-modeling-workflow'})-[:DEFAULT_STACK {note: 'memnet'}]->(:SKL {id: 'sysml-memnet-documentation'})
```

Load `memnet-multitask` when Multitask Mode or Task sub-agents run. Ops: `docs/multi-agent-sessions.md`. Shape: `docs/SHAPE.md`.
