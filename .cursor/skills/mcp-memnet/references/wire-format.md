# Wire format — MemNet GQL / shaped subgraph

Agent I/O: shaped `pin_map` + openCypher-shaped **`mutate`**. SSOT: `docs/grammar/gql-wire-profile.md`. Conventions: [memnet-format](../../memnet-format/SKILL.md).

Do not use TOON/TRON. Do not teach pipe `@TAG`. leftover `id:'NEW'` is leftover.

MCP envelopes: parse **`stdout`**. Mutate in **`wire_lines`**.

## Principles

| Principle | Why |
|-----------|-----|
| Atomisation | Small nodes + edges; pin_map pulls neighbours |
| Cue then Shape | `kind` / locators / keyword — leftover `anchor=` is leftover |
| Short props | ids, codes, paths, numbers — no sentences |
| BIND vs typed rel | Port-port `BIND`; node-node typed labels |
| Recycle | Settled work drops out of maps |
| Batch | One `mutate` with many statements |

Atomisation: [atomisation.md](atomisation.md).

## Mutate sketch (product)

```cypher
CREATE (s:SYM {name: 'pin_map', kind: 'fn', path: 'parts/memnet-mcp/software/memnet_mcp/server.py', recycle: 'persistent'})
CREATE (m:MOD {path: 'parts/memnet-mcp/software/memnet_mcp/server.py'})-[:defines]->(s)
```

## Pin map economics

- Cue narrowly (`TSK_*`, `qname=`, one interior `session=`)
- Cap `max_rows`. Do not clip and call it Shape — cut a nested session instead
- `view=shell` is grain on a seed, not 0.11 outline
- Prefer `housekeep_stats` + settle over stuffing old maps

## MCP mapping

| CLI | MCP |
|-----|-----|
| `memnet mutate --stdin` | `mutate(wire_lines=[…])` |
| `memnet query pin-map` + cue flags | `pin_map(kind=…, locators=…)` |
| leftover `query pin-map --anchor` | leftover nickname |

## Checklist

- [ ] Cue, not leftover copy-id `--anchor` as law
- [ ] Props short; edges not id-lists
- [ ] Drop prior map before the next generate
