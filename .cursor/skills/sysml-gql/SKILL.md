---
name: sysml-gql
description: >-
  Thin SysML v2 × MemNet GQL bridge: campaign TSK, cue pin_map, narrow .sysml
  edit, then mutate deltas. Triggers: sysml gql, modeling pin_map, TSK_model GQL,
  hasPort satisfies allocates.
metadata:
  pattern: pipeline
  domain: sysml,memnet
  version: "1.3"
  product: memnet-llm==0.19.1
  pairs_with: [mcp-memnet, memnet-format, sysml-memnet-cache, sysml-memnet-documentation, sysml-modeling-workflow, memnet-nested-sessions]
token_guardrails: |
  - GQL only. No Layer / pipe @TAG. leftover NEW / leftover anchor= named leftover.
  - .sysml is structure; MemNet holds relatives. Kind map: sysml-memnet-patterns.md.
---

# SysML × MemNet GQL

**Stores:** `.sysml` = structure and satisfy. MemNet = atomised relatives for the next turn.

## Turn loop

| Step | Action |
|------|--------|
| 1 | Cue `TSK_model_<short>` (`find` if unknown). Warm miss → mint via `mutate` |
| 2 | `pin_map(kind='TSK', locators=['goal=TSK_model_<short>'], depth=2, max_rows=50)` |
| 3 | `Read` at `SYM.line`; edit `sysml-models/models/*.sysml` (or the live root) |
| 4 | Validate until pass |
| 5 | `mutate` deltas + refresh `SYM.line` |

Six-step snap: [sysml-memnet-snap.md](../sysml-memnet-documentation/references/sysml-memnet-snap.md). Nest cuts: [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md).

## Construct map (abbrev)

Closed enums: [sysml-memnet-patterns.md](../sysml-memnet-documentation/references/sysml-memnet-patterns.md).

| SysML v2 | Node | Typical rels |
|----------|------|--------------|
| part | `:PRT` | `:declaredIn`, `:hasPort` |
| port | `:POR` | `:typedBy`, port-port `:BIND` |
| connection | `:CON` | `:connects` |
| requirement | `:REQ` | — |
| item | `:ITM` | `:flowOf` |
| state / action | `:BEH` | `:declaredIn` |
| satisfy / allocate | rel only | `:satisfies` / `:allocates` |
| file / line | `:MOD` / `:SYM` | `:inFile` |

```cypher
MATCH (t:TSK {goal: $goal})
CREATE (p:PRT {name: 'Pdu', kind: 'partUsage'})-[:hasPort]->(por:POR {name: 'pwr_in', kind: 'portUsage', dir: 'in'})
CREATE (p)-[:satisfies]->(:REQ {requirementId: $req})
```

Cue and MATCH by labels+properties (`goal`, `name`, `qname`, `path`, `requirementId`). leftover nickname `id` / `locators=['id=…']` are leftover.

## Related

[mcp-memnet](../mcp-memnet/SKILL.md) · [memnet-format](../memnet-format/SKILL.md) · [sysml-memnet-cache](../sysml-memnet-cache/SKILL.md)
