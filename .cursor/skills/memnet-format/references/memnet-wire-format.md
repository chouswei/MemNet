# MemNet GQL wire — field notes

**Audience:** model. Agent I/O is **GQL / openCypher-shaped** via the MCP envelope. See [../SKILL.md](../SKILL.md). Wire SSOT: `docs/grammar/gql-wire-profile.md`.

Do **not** emit `@TAG: field|field|…` pipe rows as agent format.

## Mutate sketch

```cypher
CREATE (c:CLM {type: 'decision', code: 'bitrate cap 2000 bps', recycle: 'persistent'})
MATCH (t {id: $tid}) SET t.status = 'in_progress', t.recycle = 'persistent'
CREATE (a)-[:HELPS {note: 'labour', recycle: 'persistent'}]->(b)
MATCH ()-[e {id: $eid}]->() SET e.recycle = 'delete_on_settle'
MATCH ()-[e {id: $eid}]->() DELETE e
```

Patch nodes by id only — do not invent a second id for the same ground atom. Re-id: `MATCH (n {id: $old}) SET n.id = $new` (optional merge when `$new` exists; nodes only).

## Pin_map (shaped subgraph)

Primary read returns a bounded neighbourhood. Cue with `kind` / `locators` / `keyword`. leftover `anchor`/`anchors` are leftover nicknames. Empty cue = outline. `find` then `pin_map` from labels+props — `find` is not goldfish read.

Session schema (`session_open` map — not graph rows):

```text
SCHEMA MOD ; fields=id path summary status recycle
```

## Properties (atoms-only)

- Short keys: `type`, `code`, `status`, `path`, `line`, `recycle`, …
- Numeric patches: prefer explicit SET arithmetic on known number props
- Values: bare atoms, numbers, or quoted strings (paths with `\` or spaces)
- No nested lists/maps in one property — use relationships for membership

## Recycle

- `persistent` — enduring structure and facts
- `delete_on_settle` — drop when owning task settles
- `delete_on_expire` — time-based (rare in agent flows)

## Common labels

| Label | Typical props |
|-------|----------------|
| `CLM` | `type`, `code`, `status`, `recycle` |
| `TSK` | `goal`, `phase`, `status`, `recycle` |
| `USR` | `topic`, `content`, `status`, `recycle` |
| `RUL` | `kind`, `code`, `priority`, `recycle` |
| `MOD` | `path`, `lang`, `role`, `loc`, `recycle` |
| `SYM` | `name`, `kind`, `path`, `line`, `sig`, `vis`, `recycle` |
| `PKG` / `PRT` / `POR` / `CON` / `BEH` / `ITM` / `REQ` | SysML atoms — see [sysml-memnet-patterns](../../sysml-memnet-documentation/references/sysml-memnet-patterns.md) |
| Rel types | `BIND` (port-port); else English verb / snake / upper token — copy from pin_map |

## Design principles

| Principle | Why |
|-----------|-----|
| Atomisation | pin_map returns only connected atoms |
| Short props | ids, codes, paths, numbers — no prose |
| Explicit relationships | Filterable; BIND vs typed relation |
| Recycle / settle | Finished work drops out of pin maps |
| Batch mutate | One `mutate` with many statements |
| View budget | `view=shell` / `max_rows` keep slices small |

Cross-ref: MemNet `README.md` · `docs/grammar/` · [mcp-memnet](../../mcp-memnet/SKILL.md)
