# Wire format — MemNet GQL / shaped subgraph

**Agent I/O:** **GQL wire** — shaped `pin_map` read + openCypher-shaped mutate. See MemNet `docs/grammar/gql-wire-profile.md`, [memnet-format](../../memnet-format/SKILL.md).

Do **not** use TOON/TRON. Do **not** teach pipe `@TAG:…` as agent format.

MCP tools return JSON **envelopes**; parse **`stdout`** for pin-map content. Mutate statements travel in **`wire_lines`**.

## Design principles

| Principle | Why |
|-----------|-----|
| Atomisation | Many small atoms -> pin_map pulls only connected ones |
| Shaped pin_map | Active slice + LAW; not the whole graph |
| Short props | ids, codes, keys, numbers — no sentences |
| Explicit relationships | BIND for port-port; typed rels for node-node |
| Recycle / settle | Finished work drops out of pin maps |
| Batch mutate | One `add`/`update` with many statements — fewer round trips |

Atomisation: [atomisation.md](atomisation.md).

## Mutate sketch

```cypher
CREATE (s:SYM {id: 'NEW', name: 'send_command', kind: 'fn', path: 'src/memnet/serve.py', line: 96, recycle: 'persistent'})
CREATE (m)-[:DEFINES {id: 'NEW', note: 'handler', recycle: 'persistent'}]->(s)
```

Bad (token-heavy prose blob):

```cypher
CREATE (n:NOTE {id: 'NEW', code: 'send_command lives in source and handles TCP stdin …', recycle: 'persistent'})
```

## Pin map economics

Every pin-map read (`pin_map`) returns a bounded shaped subgraph (LAW + anchor + neighbours to `depth` / `max_rows`).

- Increase **`depth`** only when needed
- Cap with **`max_rows`** (default 50)
- Optional **`view=shell`** for a tight budget
- Anchor narrowly (`SYM_*`, `TSK_*`)

Prefer **`housekeep_stats`** + settlement over re-injecting unchanged pin-map output.

## What not to put on the wire

| Avoid | Do instead |
|-------|------------|
| Paragraphs, markdown blobs | Codes / short props; prose stays in the agent turn |
| Whole file contents | Module path + symbol signatures |
| Duplicate facts in chat + graph | Graph is source of truth; cite ids |
| JSON blobs inside props | Split into nodes + relationships |
| TOON / TRON handoffs | GQL wire or plain Markdown |

## MCP mapping

| CLI | MCP |
|-----|-----|
| `memnet add --stdin` | `add(wire_lines=[...])` |
| `memnet query pin-map --anchor X` | `pin_map(anchor="X", depth=2)` (`query_warm` alias) |
| stdout pin map | `envelope.stdout` |

Tool args: [tool-parameters.md](tool-parameters.md).

## Handoff

| Mechanism | Role |
|-----------|------|
| **GQL wire / pin_map** | Agent read + mutate |
| **Plain Markdown** | Ephemeral same-turn scratch when no session |

## Checklist

- [ ] Props short and structured?
- [ ] Could this statement be split for a smaller pin-map slice?
- [ ] pin_map with a tight anchor / view budget?
- [ ] Settling transient rows so the map stays lean?

Cross-ref: MemNet `README.md` · `docs/grammar/` · [mcp-policy.md](mcp-policy.md)
