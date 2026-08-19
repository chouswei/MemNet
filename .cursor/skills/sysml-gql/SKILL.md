---
name: sysml-gql
description: >-
  Thin bridge when SysML v2 modeling uses MemNet GQL working memory: campaign task,
  shaped pin_map, narrow .sysml edit, validate, then openCypher-shaped mutate deltas.
  Triggers: sysml gql, sysml memnet gql, SysML GQL, modeling pin_map, TSK_model GQL,
  SysML node labels, hasPort satisfies allocates, MemNet SysML mapping.
metadata:
  pattern: pipeline
  secondary: tool-wrapper
  domain: sysml,memnet
  version: "1.1"
  pairs_with: [graph-query-language, gql-path-patterns, mcp-memnet, memnet-format, sysml-memnet-cache, sysml-memnet-documentation, sysml-modeling-workflow]
token_guardrails: |
  - GQL wire only: shaped pin_map read + openCypher-shaped mutate. No Layer / NODE|EDGE line dialect; no pipe @TAG agent I/O.
  - .sysml is structural SSOT; MemNet holds atomised modeling relatives between turns.
  - Construct map SSOT: sysml-memnet-patterns.md -- do not invent labels or rel spellings.
  - Keep this skill thin: link siblings for tools, wire, and full snap procedure.
---

# SysML x MemNet GQL (thin bridge)

**When:** SysML v2 modeling with MemNet as goldfish working memory.

**Stores:** `.sysml` = structure and satisfy links. MemNet GQL = atomised relatives (parts, ports, locators, claims) for the next turn.

**MUST NOT** teach Layer / `NODE|EDGE` line dialect or pipe `@TAG` agent I/O.

## Turn loop

| Step | Action |
|------|--------|
| 1 | Anchor on `TSK_model_<short>` (mint if warm miss; `find` then pin_map if id unknown) |
| 2 | `pin_map(anchor=TSK_model_<short>, depth=2, max_rows=50)` -- shaped subgraph |
| 3 | Narrow `Read` at `SYM.line`; edit project `models/*.sysml` |
| 4 | Validate (`mcp-sysml-v2`) until pass |
| 5 | Mutate deltas only (new/changed atoms + refresh `SYM.line`) |

Full six-step snap (serve probe, outputs sync, settle): [sysml-memnet-snap.md](../sysml-memnet-documentation/references/sysml-memnet-snap.md). Cache defer: [sysml-memnet-cache](../sysml-memnet-cache/SKILL.md). Hub sequence: [sysml-modeling-workflow](../sysml-modeling-workflow/SKILL.md).

## Construct map (abbrev)

| SysML v2 | Node label | Typical rels |
|----------|------------|--------------|
| part def/usage | `:PRT` | `:declaredIn`, `:inFile`, `:hasPort` |
| port def/usage | `:POR` | `:typedBy`, port-port `:BIND` |
| connection / link | `:CON` | `:connects`, `:typedBy` |
| requirement | `:REQ` | -- |
| item / flow item | `:ITM` | `:flowOf` (item node only) |
| state / action / calc | `:BEH` | `:declaredIn` |
| satisfy | rel only | `:satisfies` |
| allocate | rel only | `:allocates` |
| `.sysml` file / locator | `:MOD` / `:SYM` | `:inFile` |

Closed kind enums and batch rules: [sysml-memnet-patterns.md](../sysml-memnet-documentation/references/sysml-memnet-patterns.md).

```cypher
MATCH (t:TSK {id: $tid})
CREATE (p:PRT {id: 'NEW', name: 'Pdu', kind: 'partUsage', recycle: 'persistent'})-[:HASPORT {id: 'NEW', recycle: 'persistent'}]->(por:POR {id: 'NEW', name: 'pwr_in', kind: 'portUsage', dir: 'in', recycle: 'persistent'})
CREATE (p)-[:SATISFIES {id: 'NEW', recycle: 'persistent'}]->(:REQ {id: $req})
```

Copy assigned ids from the pin_map / mutate response. Bound paths: [gql-path-patterns](../gql-path-patterns/SKILL.md).

## Related

| Skill | Role |
|-------|------|
| [graph-query-language](../graph-query-language/SKILL.md) | General GQL read/write shape |
| [gql-path-patterns](../gql-path-patterns/SKILL.md) | Bounded hops / reachability |
| [mcp-memnet](../mcp-memnet/SKILL.md) | MCP tools and session loop |
| [memnet-format](../memnet-format/SKILL.md) | MemNet GQL wire conventions |
| [sysml-memnet-documentation](../sysml-memnet-documentation/SKILL.md) | Snap, read policy, pattern SSOT |
| [sysml-memnet-cache](../sysml-memnet-cache/SKILL.md) | Specialist read/write defer |
