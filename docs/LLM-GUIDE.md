# MemNet — Agent Playbook (for LLMs)

**Class:** developers — MemNet engine / MCP / GQL wire / agent operating doctrine. Index: [`docs/README.md`](README.md). Product shape: [`SHAPE.md`](SHAPE.md). **Product 0.19.3.** **1.0** = 0.5–0.8 claimed (unclaimed). Last PyPI **`memnet-llm==0.19.0`** until 0.19.3 upload.

**Dialect teach = GQL only** — [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md). ADR: [`adr/ADR-001-gql-agent-wire.md`](adr/ADR-001-gql-agent-wire.md).  
**M2 shipped:** engine/MCP accept openCypher-shaped GQL and emit shaped `pin_map`. Do **not** teach Layer / Tier A / `@TAG` pipe as agent wire.

**You are a goldfish.** Your working memory is unreliable. MemNet is the mission session graph — durable state lives there, not in chat, and not in a RAG index. Host search MAY propose locators; you commit them with mutate or ingest. In-session recall is **serial**: codebook-token cue (kind / properties / keyword / `find`), then ShapeWalk `pin_map`. Do not expect `rag_query`, embeddings, or GraphRAG on `memnet-mcp`.

---

## Essentials (read this first)

### Core contract

- Everything you need for the current task lives in the MemNet graph for this session.
- You **mutate** with openCypher-shaped GQL under MemNet gates; you **read** a bounded shaped subgraph via **`pin_map`**.
- Each turn you re-inject only the live slice via **`pin_map`** (MCP) or **`query pin-map`** (CLI).
- When a sub-task is done, **settle** it (`status` / recycle policy) so it disappears from future pin maps.
- Never rely on your own previous messages for durable ids or facts.
- Handoff between agents = **session id** (+ write scope). Re-`pin_map` from a cue. Prefer **import** for absorbing a member slice — chat is never SSOT.

### Non-negotiable rules

> **Always read from a seed set \(Q\)** — cue/`find` (RelativeSeed MATCH_L) then `pin_map(q)` (ShapeWalk from those graph elements). leftover 0.9 `pin_map(anchor=…)` / `--anchor` / copy-id is leftover engine, not TARGET law. Empty \(q\) is **session outline** (0.11). Do not dump the whole session. Do not stuff prior maps. Do not treat raw tabular `RETURN` as the goldfish read.

> **Atomise** — GQL elements: **node** (vertex), **edge** (relationship), **property**. One idea per property; wire relations as edges. No prose blobs in a property value.

### GQL wire (Write = display redefined)

**Product teach (0.8) = GQL** — primary label ≈ kind (`:TSK`, `:CST`, …); bind = `:bind` + `fromPort`/`toPort`; chart links = other rel types on bare node ids; law = node property `law`. Profile: [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md). Case study: [`application-notes/examples/inverting-amplifier-gql-case-study.md`](application-notes/examples/inverting-amplifier-gql-case-study.md).

**Mutate sketch:**

```cypher
CREATE (t:TSK {goal:'Clear warehouse', status:'in_progress'})
MATCH (n:NPC {role:'helper'}), (t:TSK {goal:'Clear warehouse'})
CREATE (n)-[:helps {note:'labour'}]->(t)
MATCH (t:TSK {goal:'Clear warehouse'}) SET t.status = 'settled', t.recycle = 'delete_on_settle'
```

After **CueConflict** (\(|Q|>1\) on find/`pin_map`), SameThingAbsorb is a **Commit rule** (not a third operator): `MATCH (a:TSK {goal:'alpha'}), (b:TSK {goal:'beta'}) SET a += b`. Two same-name nodes stay two until that Commit. ImportAbsorb does not entity-resolve.

**Shaped `pin_map` out** (properties the node actually has; nickname `id` only if set):

```cypher
(:TSK {goal:'Clear warehouse', status:'in_progress'})
(:NPC {role:'helper', status:'active'})
(:NPC {role:'helper'})-[:helps {note:'labour'}]->(:TSK {goal:'Clear warehouse'})
```

Circuit / law-leaf sketch:

```cypher
(:CST {id:'CST_R', R:50, ports:{a:{direc:'inout', V:'@va', I:'@ia'}, b:{direc:'inout', V:'@vb', I:'@ib'}}, law:'$@va-@vb=@ia*R$,$@ia=-@ib$'})
(:CST {id:'CST_Src'})-[:bind {id:'E_1', fromPort:'p', toPort:'a', carries:'I'}]->(:CST {id:'CST_R'})
```

- **Create:** `CREATE (:Kind {props})` — GraphElement identity; no required `id`. leftover `id:'NEW'` mint is leftover, not product.
- **Update / settle:** MATCH by labels+properties; SET/DELETE. When \(|Q|>1\), CueConflict — do not pick one root.
- **External artefact pins:** locators are properties, not a PK. **no** client `NEW`.

Formal wire: [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md).

### Transport (default: in-process MCP)

| Mode | When | Setup |
|------|------|-------|
| **MCP in-process** | Cursor / local agents (**primary**) | Register `memnet-mcp` in `.cursor/mcp.json`; extra `[mcp]`. `pip install 'memnet-llm[mcp]'` (Hatch **0.19.3**; last PyPI **0.19.0** until upload). **No** `memnet serve` |
| **CLI + serve** | Scripts, TCP shared process | Terminal 1: `memnet serve`; Terminal 2: CLI with `MEMNET_SESSION` |
| **MCP streamable-http** | Remote shared graph | `memnet-mcp --transport streamable-http` on `:18766/mcp` |

`serve_status` probes TCP serve — optional under in-process. Do not block on serve when MCP is in-process.

### Goldfish loop (every turn)

Interact only with **relevant slices** of the session — never dump the graph. Default **one** `pin_map(q)` (or skip). **Drop** prior map rows from the prompt before the next generate — stuffing MCP JSON into a growing chat list is a fail (`stuffed_maps`). Commit a **sparse** Δ (`add`/`update` of what changed only). Env blobs (pytest logs, screenshots) stay in the outer harness. That writeback is not Path-B absorb.

1. **Seed relative nodes** — cue \(q\) (kind / labels+props / keyword). `find(kind='TSK', limit=L)` / `memnet query find --kind TSK --limit L` yields \(Q\). Empty \(q\) (no cue) ⇒ **session outline** (0.11: kinds + LIMIT exemplars of \(S\)); then pick one seen cue. Empty \(Q\) on a *kind* cue ⇒ skip (do not invent). leftover 0.9: copy an id then `--anchor` is leftover, not this loop.
2. **ShapeWalk one slice** from \(Q\) (one \(M\), not \(M\times|Q|\)):

   MCP: `pin_map` from the cue/pattern (`kind` / `locators` / `keyword`)  
   CLI: `memnet query pin-map --kind … --locator … --keyword …`

   leftover engine may still take `--anchor` as a **nickname** cue — not TARGET law.

   Blocked on a topic hub: at most one extra `pin_map(..., view=shell)` **on that seed**, then interior on the live `TSK`. `view=shell` is grain on a seed — **not** session outline (0.11). Do **not** issue \(N\) full maps (duplicate LAW / overlap). Do not fuse ranks.
3. **Act / reason** using only the **live** pin-map slice + the current user request. Do not keep turn-\(n-1\) maps in the pack.
4. **Commit sparse Δ** — CREATE / SET on changed elements only. Do not echo the fetched map. leftover `id_exists` / NEW mint is leftover.

   MCP: `mutate(wire_lines=[…])`  
   CLI: `memnet mutate --stdin`  
   leftover `add` / `update` names remain leftover façades (do not mint NEW; not TARGET).
5. **Settle** finished work (`status=settled`, `recycle=delete_on_settle`) — HiAgent replace of the old subgoal.
6. (Occasionally) prune recyclable rows.

Process death: `session save` / `session load` (snapshot) is the offered file durable. Fake hydrate/flush is always-on CI. Live AgensGraph hydrate/flush is **0.7** when `MEMNET_AGENSGRAPH_URL` points at an operator cabinet — not required for default in-process work. Optional Neo4j client (`memnet-llm[neo4j]`) uses the same hydrate/flush owner; extra **0.14** claims live (`liveNeo4jClaimed=true`; live round-trip yes; hid flush; leftover-nickname hydrate after hid miss; skip unless `MEMNET_NEO4J_URL`). Extra **0.16** optional `MEMNET_NEO4J_LIBRARY_DATABASE` is locator-only on the same process. Agents still MUST NOT talk Bolt. **0.8** teach: product shape [`SHAPE.md`](SHAPE.md); version map [`ROADMAP.md`](ROADMAP.md).

Repeat. Each new turn starts with `pin_map(q)` (or empty-q outline). Drop the previous map from the pack.

### MCP quick reference (primary)

| Tool | Role |
|------|------|
| `session_open` | Open session; optional `seed_lines`; auto-seeds LAW01–LAW05 |
| `session_list` | Live ids plus `@STAT: sessions|n/max` (named strata; not ANN) |
| `session_close` | Close that id (does not dump \(S\)) |
| `session_save` / `session_load` | Snapshot durability |
| `pin_map` | **Live pin map** — primary read (`query_warm` = leftover alias) |
| `mutate` | **Product Commit** — gated GQL CREATE / MERGE / SET / DELETE |
| leftover `add` / `update` | leftover façades (GQL; no NEW mint). Prefer `mutate` |
| `read_list` | leftover enumeration. Product read is find then `pin_map` |
| leftover `read_get` | **Not** an MCP or product CLI tool |
| `housekeep_stats` | Caps and row counts |
| `serve_status` | TCP serve probe (optional in-process) |
| leftover `query_walk` | leftover hop debug, not goldfish |

Always pass the same `session` id across tools in one job.

### leftover `add` vs `update` vs product `mutate`

| Intent | Product | leftover façade | Wrong-way signal |
|--------|---------|-----------------|------------------|
| **Commit Δ** | `mutate` | leftover `add`/`update` split | leftover NEW mint; pipe as agent wire |
| **New element** | `CREATE` via `mutate` | leftover `add` | `id_exists` on leftover add |
| **Change** | `MATCH…SET` via `mutate` | leftover `update` | `not_found` on leftover update |

Copy ids from pin map output — never retype from memory. There is no upsert.

### IDs

- IDs are **global within a session** and unique per kind.
- **Reuse** the same id for the same thing forever.
- **Never mint a duplicate** for something already in the graph.
- Unsure? cue/`find` then `pin_map`. leftover `read_get` / CLI `read get` are unshipped from the product surface.

### `recycle` field

- `persistent` (default) → stays in pin map reads.
- `delete_on_settle` → hidden after settle (tasks, settled edges).
- `delete_on_expire` → hidden (transient edges).

**Settlement pattern:**

```cypher
MATCH (t:TSK {id:'TSK_01'}) SET t.status = 'settled', t.recycle = 'delete_on_settle'
MATCH ()-[e {id:'E_01'}]->() SET e.recycle = 'delete_on_settle'
```

Next turn: `pin_map(q)` on a live cue — settled rows absent. Optionally `housekeep prune recyclable --apply`.

### Reading strategy

- **Normal turn:** one `pin_map(kind='TSK', locators=[…], depth=2, max_rows=50)` (or skip). Optional `view=shell` on a **seeded** topic hub only when blocked, then interior on the task. leftover `--anchor` / `anchor=` is a leftover nickname alias, not law.
- Pin map includes engine LAW rows (prepended) — that is why \(N\) maps waste tokens.
- Excludes rows with `recycle=delete_on_settle` or `delete_on_expire` (unless leftover nickname cue touches endpoints per LAW01).
- leftover `read_list(active_only=True)` may enumerate; product is `find` then one `pin_map`.
- New facts: sparse GQL `mutate`. Do not echo the fetched slice. Do not call that absorb.
- Switch task: settle the old `TSK`, then `pin_map` the next ego — do not RAG/embed the session.
- leftover `query_walk` — hop debug only, not goldfish.
- leftover `query context` — audit only; empty cue allowed (not `require_anchor` as product law). Do not use every turn.

### Session lifecycle

- One big job → one session id.
- `session_open` at start; `MEMNET_SESSION` env for CLI follow-ups.
- Registry: `session_list` shows `@STAT: sessions|n/max` then ids; `session_close` frees a slot (default cap 256; `MEMNET_MAX_SESSIONS` overrides). `snap_model` mints catalog + interiors, so close unused strata rather than filling the serve registry.
- Milestones: `session_save` / `session_load` (MCP or CLI).
- Default TTL 60 minutes; override with `ttl` on open/load.
- After `session_load`, existing elements need `MATCH…SET` via `mutate` (leftover `update`, not leftover `add`).
- Agent handoff: deliver **session id** (+ anchors / write scope); peers **re-pin_map**. Prefer **import** when absorbing a member working-memory slice.

### Path B ingest

**PinMapIngest_*** domains are shipped — selective external artefact → pins with deterministic locator ids (MN-REQ-11.16; #31 / #64):

| Engine | CLI | MCP | Locators (examples) |
|--------|-----|-----|---------------------|
| Sysml | `memnet ingest sysml --path …` | `ingest_sysml` | `path=`, `qname=`, `requirementId=` |
| **Model Snap (0.15)** | `memnet snap model --root …` | `snap_model` | catalog `session=` + `qname=` (cuts that **fit \(M\)**; reuse already-built `session=`; look loop = one `pin_map` per generate). Application: `llm-sysml-v2-modeling.md` |
| Codebase | `memnet ingest codebase --path …` | `ingest_codebase` | `path=`, `line=`, `signature=` |
| PCBA `.ato` | `memnet ingest pcba --path …` | `ingest_pcba` | `refdes=`, `net=`, `pin=`, `path=` |
| Skills/rules | `memnet ingest skills --path …` | `ingest_skills` | `skill_id=`, `phrase=` |

Client `NEW` is rejected for source pins. Bounded (`--max-nodes` / `--max-files`). Ingest is not export. 0.19 pin-map export writes a cue `pin_map` (or empty-q outline) as shaped GQL (`memnet export pin-map` / MCP `export_pin_map`). Re-ingest / `.sysml` reverse (MN-REQ-11.5 SHOULD) remains later (#66).

### Multi-agent / Multitask

**MUST** follow `docs/operations/multi-agent-sessions.md` when Multitask Mode or Task sub-agents are in play. One shared session id; parent settles `TSK_*` / `USR_*`; workers re-`pin_map` each turn. **MUST NOT** use default in-process MCP for shared Multitask graphs — use TCP serve or streamable-http.

### Not implemented (design only)

- Full session ACL modes / roles / `session_token` (CapsPolicy ACL ships when enabled)
- Full `view=` grain filters (shell/interior caps exist; flowchart/parts/statechart soft-deferred)
- Field-formula auto-emit from law nodes
- SysML file reverse / pin-map re-ingest (MN-REQ-11.5 SHOULD / #66) — 0.19 GQL write-out is not identity merge
- Host search / RAG as a MemNet MCP tool — extra **0.17** hook is **outside** `MemNetSystem` only (`docs/extras/memnet-host-search-nest.md`); skip valid; no `rag_query`

### Neighbourhood reserve (MN-REQ-12.13)

```bash
memnet reserve --anchor PLR01 --llm-id coder_a --depth 2 --ttl 120   # leftover --anchor nickname
memnet query pin-map --cue PLR01   # may show ## Reserves / RSV […]
memnet mutate --stdin --llm-id coder_a …
memnet release --rid R1 --llm-id coder_a
```

Design: `docs/extras/memnet-neighbourhood-reserve.md`. After ACL when both are enabled.

### Local IPC (MN-REQ-06.2)

Prefer AF_UNIX over TCP when two processes on one host share one registry:

```bash
export MEMNET_IPC_SOCKET=/tmp/memnet.sock   # same path for server + clients
memnet serve --ipc                          # or: memnet serve --ipc-path "$MEMNET_IPC_SOCKET"
# other terminal (MEMNET_IPC_SOCKET set):
memnet session open --map-file schema.example.txt
memnet query pin-map --cue …
```

TCP `memnet serve` (`127.0.0.1:18765`) remains the Multitask / LAN fallback (MN-REQ-06.3).

See `docs/grammar/` for targets. Durable online GQL store adapter = **M2.5** (0.7: live hydrate/flush proven against an external cabinet; Fake + URL skip in CI).

### Common failure modes

| Mistake | Fix |
|---------|-----|
| Whole-session read | Cue then `pin_map` only |
| leftover `add` when the pattern already matches | leftover `update` / product `MATCH…SET` by labels+properties |
| SET/DELETE when \(|Q|>1\) | CueConflict — do not pick one root; do not absorb on Recall. SameThingAbsorb is a later Commit (`SET a += b`) |
| Settled but `recycle=persistent` | Set `delete_on_settle` on settle |
| Ignoring stderr `@WRN:` | Read warnings (caps, staleness) |
| Teaching Layer / `@TAG` pipe / Tier A | **GQL only** — [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md) |
| Unbounded tabular `MATCH`/`RETURN` as goldfish read | Shaped `pin_map` only |
| Chat / graph dump as handoff | Session id + cue / re-`pin_map` (import for path B) |
| leftover `id:'NEW'` / copy-id `--anchor` as law | Pattern Commit; cue `pin_map` (those are leftover 0.9) |
| Stuffing every `pin_map` into `messages` | Drop prior map rows; env blobs stay in the harness (`stuffed_maps`) |

### Minimal complete turn (MCP)

```text
# 1. Commit (first time) — GQL clauses in wire_lines
mutate(wire_lines=[
  "CREATE (t:TSK {goal:'Negotiate with the guild', status:'in_progress', recycle:'persistent'})",
  "MATCH (b {name:'Guild'}), (t:TSK {goal:'Negotiate with the guild'}) CREATE (b)-[:seeks_help {note:'terms', recycle:'persistent'}]->(t)",
])

# 2. Recall
find(kind='TSK', limit=8)
pin_map(kind='TSK', locators=['goal=Negotiate with the guild'], depth=2, max_rows=30)

# 3. Later — settle
mutate(wire_lines=[
  "MATCH (t:TSK {goal:'Negotiate with the guild'}) SET t.status = 'settled', t.recycle = 'delete_on_settle'",
])

# 4. Next turn — empty cue outlines S (0.11); then pin from a seen cue
pin_map()
pin_map(kind='TSK')
```

leftover 0.9 `id:'NEW'` / leftover `add`/`update` / `pin_map(anchor=…)` / copy-id is leftover engine, not this loop.

### Application notes

**Class:** applications. Full index: [`docs/README.md`](README.md).

Under `docs/application-notes/` — domain examples (**GQL teach**):

| # | Note | Summary |
|---|------|---------|
| 0 | `system/llm-system-dev-multitask.md` | Multitask in `modelbasedPrj-*` repos (mission + SysML two-store) |
| 1 | `system/llm-software-development.md` | Multi-turn coding in Cursor |
| 2 | `domains/llm-daily-news.md` | Batch RSS digest |
| 3 | `domains/llm-tech-docs-decomposition.md` | Manual / SCPI decomposition |
| 4 | `system/llm-sysml-v2-modeling.md` | SysML SSOT; relatives + sub-unit sessions |
| 5 | `domains/llm-circuit-schematic.md` | Circuit schematic / s-domain (see GQL case study for wire) |
| 5b | `domains/llm-nodal-analysis-formulas.md` | Nodal method ↔ node `law` + `:bind` |
| 5c | `examples/inverting-amplifier-gql-case-study.md` | InvAmp GQL-wire case study |
| 6 | `domains/llm-mud.md` | Multiplayer MUD (shared serve) |
| 7 | `system/llm-build-on-memnet.md` | Builder guide for custom MCP |

Operational Multitask MUST/MUSTNOT (developers): [`multi-agent-sessions.md`](operations/multi-agent-sessions.md).

---

## Appendix A — Retired dialects (pointer only)

**Layer / Tier A ASCII and `@TAG` pipe are retired from product accept and teach** (ADR-001 supersession; M2). Do **not** use them for new agent work.

- Wire teach: [`grammar/gql-wire-profile.md`](grammar/gql-wire-profile.md)

Older docs may mention `query warm` — use **`pin_map`** / `query pin-map`. `@WRN:` stderr lines (caps, staleness, TTL) still apply; read them.

### CLI quick reference

- `memnet serve` — TCP daemon (`127.0.0.1:18765`); required for CLI unless `MEMNET_TEST_INLINE=1`
- `memnet query pin-map --kind TSK` — live pin map from a cue (`query warm` = leftover alias). leftover `--anchor` = leftover nickname alias.
- `memnet mutate --stdin` — product GQL Commit. leftover `add`/`update` named leftover.
- `memnet housekeep stale` · `memnet housekeep prune recyclable --apply`
- `memnet guide --loose` — short cheat sheet

**0.8 default (single agent):** in-process stdio MCP needs no serve. Use serve or streamable-http when you need a **shared** graph across processes.

---

## Appendix B — Schema discovery

```powershell
memnet examples map
memnet tagmap fields
memnet tagmap show
memnet relations list
```

Never guess field order. Prefer copying property shapes from shaped `pin_map` / the GQL profile.

---

Stay disciplined with **atomisation**, settlement `recycle`, and **cue then one live pin_map** (drop prior maps). Product write is **GQL Commit** (`mutate`). leftover `add`/`update` named leftover. Everything else follows.
