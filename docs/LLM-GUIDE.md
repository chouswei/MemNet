# MemNet — Agent Playbook (for LLMs)

**Class:** developers — MemNet engine / MCP / GQL wire / agent operating doctrine. Index: [`docs/README.md`](README.md).

**Dialect teach = GQL only** — [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md). ADR: [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md).  
**As-is note:** 0.4.x engine may still accept an older line dialect until **M2**; do **not** teach Layer / Tier A.

**You are a goldfish.** Your working memory is unreliable. MemNet is external structured scratch space — durable state lives in the graph for this session, not in chat.

---

## Essentials (read this first)

### Core contract

- Everything you need for the current task lives in the MemNet graph for this session.
- You **mutate** with openCypher-shaped GQL under MemNet gates; you **read** a bounded shaped subgraph via **`pin_map`**.
- Each turn you re-inject only the live slice via **`pin_map`** (MCP) or **`query pin-map`** (CLI).
- When a sub-task is done, **settle** it (`status` / recycle policy) so it disappears from future pin maps.
- Never rely on your own previous messages for durable ids or facts.

### Non-negotiable rules

> **Always read with an anchor** — `pin_map(anchor=…)` or `query pin-map --anchor …`. Do not dump the whole session. Do not treat raw tabular `RETURN` as the goldfish read.

> **Atomise** — one idea per node/edge; wire relationships as relationships. No prose blobs in properties.

### GQL wire (Write = display redefined)

**1.x teach = GQL** — primary label ≈ kind (`:TSK`, `:CST`, …); bind = `:bind` + `fromPort`/`toPort`; chart links = other rel types on bare node ids; law = node property `law`. Profile: [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md). Case study: [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md).

**Mutate sketch:**

```cypher
CREATE (t:TSK {id:'NEW', goal:'Clear warehouse', status:'in_progress'})
MATCH (n:NPC {id:'NPC_03'}), (t:TSK {id:'TSK_42'})
CREATE (n)-[:helps {id:'NEW', note:'labour'}]->(t)
MATCH (t:TSK {id:'TSK_42'}) SET t.status = 'settled'
```

**Shaped `pin_map` out** (copy ids from here):

```cypher
(:TSK {id:'TSK_42', goal:'Clear warehouse', status:'in_progress'})
(:NPC {id:'NPC_03', role:'helper', status:'active'})
(:NPC {id:'NPC_03'})-[:helps {id:'E_77', note:'labour'}]->(:TSK {id:'TSK_42'})
```

Electrical / law-leaf sketch:

```cypher
(:CST {id:'CST_R', R:50, ports:{a:{direc:'inout', V:'@va', I:'@ia'}, b:{direc:'inout', V:'@vb', I:'@ib'}}, law:'$@va-@vb=@ia*R$,$@ia=-@ib$'})
(:CST {id:'CST_Src'})-[:bind {id:'E_1', fromPort:'p', toPort:'a', carries:'I'}]->(:CST {id:'CST_R'})
```

- **Create:** `id: 'NEW'` — engine mints; copy from the next pin map.
- **Update / settle:** known ids only; `NEW` illegal on patch.
- **External artefact pins** (SysML, `.ato`, codebase, skills): deterministic ground ids + locators — **no** client `NEW`.

Formal wire: [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md).

### Transport (default: in-process MCP)

| Mode | When | Setup |
|------|------|-------|
| **MCP in-process** | Cursor / local agents (**primary**) | Register `memnet-mcp` in `.cursor/mcp.json`; `pip install memnet-llm[mcp]` — **no** `memnet serve` |
| **CLI + serve** | Scripts, TCP shared process | Terminal 1: `memnet serve`; Terminal 2: CLI with `MEMNET_SESSION` |
| **MCP streamable-http** | Remote shared graph | `memnet-mcp --transport streamable-http` on `:18766/mcp` |

`serve_status` probes TCP serve — optional under in-process. Do not block on serve when MCP is in-process.

### Goldfish loop (every turn)

1. **Think** what you need to remember or act on.
2. **Mutate** (batch preferred; atomise):

   MCP: `add(wire_lines=[…])` / `update(wire_lines=[…])`  
   CLI: `memnet add --stdin` / `memnet update --stdin`

3. **Read the live slice** (always anchored):

   MCP: `pin_map(anchor=T42, depth=2)`  
   CLI: `memnet query pin-map --anchor T42 --depth 2`

4. **Act / reason** using only pin-map data + the current user request.
5. **Settle** finished work via `update` (`~` lines).
6. (Occasionally) prune recyclable rows.

Repeat. Each new turn starts with `pin_map` / `query pin-map`.

### MCP quick reference (primary)

| Tool | Role |
|------|------|
| `session_open` | Open session; optional `seed_lines`; auto-seeds LAW01–LAW05 |
| `session_save` / `session_load` | Snapshot durability |
| `pin_map` | **Live pin map** — primary read (`query_warm` = legacy alias) |
| `add` / `update` | Mutate — GQL / wire lines (M2: openCypher-shaped) |
| `read_get` / `read_list` | Lookup / enumerate |
| `housekeep_stats` | Caps and row counts |
| `serve_status` | TCP serve probe (optional in-process) |

Always pass the same `session` id across tools in one job.

### Add vs update

| Intent | MCP | CLI | Wrong-way signal |
|--------|-----|-----|------------------|
| **New** row | `add` | `add` | `id_exists` → use `update` |
| **Change** row | `update` | `update` | `not_found` → fix id or `add` |

Copy ids from pin map output — never retype from memory. There is no upsert.

### IDs

- IDs are **global within a session** and unique per kind.
- **Reuse** the same id for the same thing forever.
- **Never mint a duplicate** for something already in the graph.
- Unsure? `read_get` or `pin_map` first.

### `recycle` field

- `persistent` (default) → stays in pin map reads.
- `delete_on_settle` → hidden after settle (tasks, settled edges).
- `delete_on_expire` → hidden (transient edges).

**Settlement pattern:**

```text
~ TSK [T01] ; status=settled ; recycle=delete_on_settle
~ E01 [N01] --(seeks_help)--> [PLR01] ; recycle=delete_on_settle
```

Next turn: `pin_map` with a new anchor — settled rows absent. Optionally `housekeep prune recyclable --apply`.

### Reading strategy

- **Normal turn:** `pin_map(anchor=<focus>, depth=2, max_rows=50)`.
- Pin map includes engine LAW rows (prepended).
- Excludes rows with `recycle=delete_on_settle` or `delete_on_expire` (unless anchor touches endpoints per LAW01).
- `read_list(active_only=True)` or `read_list(tag=TSK, where=[...])` for flat lists.
- `query_walk` — hop debug only, not the primary read.
- `query context` — audit only; do not use every turn.

### Session lifecycle

- One big job → one session id.
- `session_open` at start; `MEMNET_SESSION` env for CLI follow-ups.
- Milestones: `session_save` / `session_load` (MCP or CLI).
- Default TTL 60 minutes; override with `ttl` on open/load.
- After `session_load`, existing ids need `update` not `add`.

### Path B ingest (deferred in 0.4.x)

**PinMapIngest_*** (SysML, codebase, PCBA `.ato`, skills) are **stubs** — not shippable. Do not wait for ingest tools. Bootstrap external pins with explicit ids + locators via `seed_lines` or `add`. See `docs/grammar/memnet-grammar-design.md` §4.2.1.

### Multi-agent / Multitask

**MUST** follow `docs/multi-agent-sessions.md` when Multitask Mode or Task sub-agents are in play. One shared session id; parent settles `TSK_*` / `USR_*`; workers re-`pin_map` each turn. **MUST NOT** use default in-process MCP for shared Multitask graphs — use TCP serve or streamable-http.

### Not implemented (design only)

- Session ACL, roles, `session_token`
- Neighbourhood reserve (`RSV` rows)
- Full `view=` grain filters (shell/interior caps exist; flowchart/parts/statechart soft-deferred)
- LocalIpcGateway transport
- Field-formula auto-emit from law nodes

See `docs/grammar/` for targets.

### Common failure modes

| Mistake | Fix |
|---------|-----|
| Whole-session read | Anchor `pin_map` only |
| `add` when id exists | `update` with id from pin map |
| `update` with typo id | Copy id from pin map |
| Settled but `recycle=persistent` | Set `delete_on_settle` on settle |
| Ignoring stderr `@WRN:` | Read warnings (caps, staleness) |
| Teaching `@TAG` pipe to users | Shared dialect only for agent I/O |

### Minimal complete turn (MCP)

```text
# 1. Add (first time)
add(wire_lines=[
  "+ TSK [NEW] ; goal=Negotiate with the guild ; status=in_progress ; recycle=persistent",
  "+ E19 [B01] --(seeks_help)--> [T07] ; note=terms ; recycle=persistent",
])

# 2. Read
pin_map(anchor=T07, depth=2, max_rows=30)

# 3. Later — settle
update(wire_lines=[
  "~ TSK [T07] ; status=settled ; recycle=delete_on_settle",
  "~ E19 [B01] --(seeks_help)--> [T07] ; recycle=delete_on_settle",
])

# 4. Next turn — T07 absent from pin map
pin_map(anchor=PLR01, depth=2)
```

### Application notes

**Class:** applications. Full index: [`docs/README.md`](README.md).

Under `docs/application-notes/` — domain examples (**GQL teach**; note bodies migrate in M3; prefer GQL case study):

| # | Note | Summary |
|---|------|---------|
| 0 | `llm-system-dev-multitask.md` | Multitask in `modelbasedPrj-*` repos (mission + SysML two-store) |
| 1 | `llm-software-development.md` | Multi-turn coding in Cursor |
| 2 | `llm-daily-news.md` | Batch RSS digest |
| 3 | `llm-tech-docs-decomposition.md` | Manual / SCPI decomposition |
| 4 | `llm-sysml-v2-modeling.md` | SysML v2 modeling |
| 5 | `llm-circuit-schematic.md` | Circuit schematic / s-domain (see GQL case study for wire) |
| 5b | `llm-nodal-analysis-formulas.md` | Nodal method ↔ NODE `law=` + binds |
| 5c | `examples/inverting-amplifier-gql-case-study.md` | InvAmp GQL-wire case study |
| 6 | `llm-mud.md` | Multiplayer MUD (shared serve) |
| 7 | `llm-build-on-memnet.md` | Builder guide for custom MCP |

Operational Multitask MUST/MUSTNOT (developers): [`multi-agent-sessions.md`](multi-agent-sessions.md).

---

## Appendix A — Legacy `@TAG` pipe dialect

**Historical.** Still accepted on `add`/`update` and in snapshots until M2 cleanup. **Do not use for new agent work** — teach GQL ([`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)).

Pipe shape: `@TAG: id|field|field|…` (pipes escaped as `\|` inside values).

Example mutate batch:

```powershell
memnet add --stdin @"
@TSK: T42|Clear the warehouse|2|in_progress|persistent
@NPC: N03|helper|labour|1|0|0|active|persistent
@EDG: E77|N03|helps|T42|labour|persistent
"@
```

Relations use `@EDG: E99|src|relation|dist||recycle`.

### Legacy goldfish loop (CLI + serve)

1. **Terminal 1:** `memnet serve` (or use in-process MCP instead).
2. **Terminal 2:** `memnet session open --map-file …`; set `MEMNET_SESSION`.
3. Mutate with `add` / `update` (pipe or shared dialect).
4. Read: `memnet query pin-map --anchor T42 --depth 2` (alias: `query warm`).
5. Settle with `update` and `recycle=delete_on_*`.

### Legacy CLI quick reference

- `memnet serve` — TCP daemon (`127.0.0.1:18765`); required for CLI unless `MEMNET_TEST_INLINE=1`
- `memnet query pin-map --anchor <id>` — live pin map (`query warm` = deprecated alias)
- `memnet query warm` — same as pin-map (deprecated)
- `memnet tagmap fields` / `memnet examples map` — schema discovery
- `memnet housekeep stale` · `memnet housekeep prune recyclable --apply`
- `memnet guide --loose` — short cheat sheet

### Legacy MCP note

Older docs said "Production use requires `memnet serve`". **0.4.x default:** in-process stdio needs no serve. Use serve or streamable-http when you need a **shared** graph across processes.

### Legacy warnings (stderr)

`@WRN:` lines (caps, `stale_in_store`, `mission_settled`, `ttl_expiring`) apply to both dialects. Read them.

---

## Appendix B — Schema discovery

```powershell
memnet examples map
memnet tagmap fields
memnet tagmap show
memnet relations list
```

Never guess field order. Session maps may use shared-dialect `SCHEMA` lines or legacy `@TAG` headers.

---

Stay disciplined with **atomisation**, ids, `add` vs `update`, settlement `recycle`, and **anchored pin map** reads. Everything else follows.
