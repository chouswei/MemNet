---
name: memnet-format
description: >-
  MemNet GQL wire: GraphElement node/edge/property, shaped subgraph emit,
  BIND vs relation, openCypher-shaped Commit. Triggers: memnet format, GQL
  wire, GraphElement, shaped subgraph, BIND vs relation, openCypher mutate.
metadata:
  pattern: tool-wrapper
  version: "5.3"
  domain: data-formats,memnet
  product: memnet-llm==0.19.1
token_guardrails: |
  - Wire SSOT: docs/grammar/gql-wire-profile.md. This skill is MemNet-specific only.
  - pin_map from a cue; leftover anchor= is leftover. Do not dump S.
  - Product Commit is GraphElement CREATE / MATCH SET DELETE — not leftover id:'NEW'.
---

# MemNet formats

Pair with [mcp-memnet](../mcp-memnet/SKILL.md). Formal SSOT: `docs/grammar/gql-wire-profile.md`. Hatch **0.19.1**.

**GQL only.** Node / edge / property. Do not teach Layer, Tier A, pipe `@TAG`, or TOON/TRON. leftover `id:'NEW'` / leftover `anchor=` are leftover.

## Shaped pin_map

MCP `pin_map` / CLI `query pin-map` emits a bounded neighbourhood. Parse envelope **`stdout`**.

| Control | Product use |
|---------|-------------|
| `kind` / `locators` / `keyword` / `cue` / `session` | Cue \(q\). Empty \(q\) = 0.11 outline |
| `depth` / `max_rows` | Hard bound. Raise depth only if the slice is too thin. Over \(M\): cut a nested session — do not clip and call it Shape |
| `view` | Grain on a **seed** (`shell` / `interior`). Not the outline |
| leftover `anchor` / `anchors` | leftover nicknames |

If ego unknown: `find(limit=…)` then `pin_map` from labels+props. CueConflict when \(|Q|>1\). `query_warm` is a leftover alias.

Loop: cue → `pin_map` → reason → `mutate` → `pin_map`. Drop the prior map next turn.

## Mutate

Product tool: MCP/CLI **`mutate`**. leftover `add`/`update` wrap the same envelope — do not teach them as TARGET.

```cypher
CREATE (t:TSK {goal:'Clear warehouse', status:'in_progress'})
MATCH (n:NPC {role:'helper'}), (t:TSK {goal:'Clear warehouse'})
CREATE (n)-[:helps {note:'labour'}]->(t)
MATCH (t:TSK {goal:'Clear warehouse'}) SET t.status = 'settled', t.recycle = 'delete_on_settle'
```

| Intent | Shape |
|--------|-------|
| Create | `CREATE (:Kind {props})` — GraphElement identity; no required `id` |
| Patch / settle | `MATCH` by labels+props; `SET` / `DELETE` |
| Rel | typed label on ends; port-port **`BIND`** (`fromPort` / `toPort` as needed) |
| Schema | `SCHEMA Kind ; fields=…` on `session_open` only |

Properties: short atoms. Membership = edges, not id-lists. Ingest pins: locators (`path`, `qname`), never leftover NEW.

Field notes: [references/memnet-wire-format.md](references/memnet-wire-format.md). Atomise: [../mcp-memnet/references/atomisation.md](../mcp-memnet/references/atomisation.md).

## SysML kinds

Do not invent labels here. Map SSOT: [sysml-memnet-patterns.md](../sysml-memnet-documentation/references/sysml-memnet-patterns.md). Thin loop: [sysml-gql](../sysml-gql/SKILL.md). Nest cuts: [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md).

## MUST NOT

- Unbounded `MATCH`…`RETURN` as goldfish read.
- leftover NEW on patch. Client NEW for artefact locators.
- Duplicate the SysML construct table in this file.
