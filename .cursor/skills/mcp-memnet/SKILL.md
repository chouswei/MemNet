---
name: mcp-memnet
description: >-
  MemNet MCP — in-memory graph via shaped pin_map, session tools, and
  openCypher-shaped mutate (add/update). Triggers: memnet mcp, pin_map,
  query_warm, pin map, session_open, GQL wire, shaped subgraph, MutateGate,
  sysml memnet tools, find, ingest_sysml, reserve, RSV.
metadata:
  pattern: tool-wrapper
  version: "6.0"
  domain: memnet
  product: memnet-llm==0.9.0
token_guardrails: |
  - Primary read is pin_map (shaped subgraph); parse envelope stdout — not JSON keys as grammar.
  - Mutate with openCypher-shaped wire_lines; mint creates with NEW; copy ids from pin_map.
  - Wire shapes SSOT: memnet-format; product wire: docs/grammar/gql-wire-profile.md.
---

# MemNet MCP (generic)

**This checkout:** skills live under `.cursor/skills/`. Doctrine SSOT is this repo’s `docs/`. In-process MCP for a **single** agent; TCP `:18765` or streamable-http when **sharing** a graph (Multitask). leftover `add`/`update` / `id:'NEW'` / `--anchor` are leftover-named; product Commit is MCP/CLI **`mutate`**; `liveNeo4jClaimed=true` (extra **0.14**). User-pack Pi `10.0.0.10` is **optional** on a human machine — not this VM.

Product **`memnet-llm` 0.9.0** (CLI `memnet`). Engine + generic MCP only — **novel-writer is out of scope**. PyPI `memnet-llm` is still **0.4.6**; install from this repo for 0.9. **1.0** = claim of 0.5–0.8. Version map: `docs/ROADMAP.md`. Shape: `docs/SHAPE.md`.

MemNet is mission working memory between LLM call pipelines and data search — not RAG. Agents **cue** then read a bounded **shaped subgraph** via **`pin_map`**, and write with **openCypher-shaped** mutate — the **GQL wire**. Detail: [memnet-format](../memnet-format/SKILL.md).

## Transport (this repo)

| Role | Where |
|------|--------|
| Single agent | In-process `memnet-mcp` (stdio); no serve |
| Shared graph / Multitask | `memnet serve` TCP `:18765` or streamable-http; `MEMNET_MCP_TRANSPORT=tcp` |
| Optional user-pack Pi | HTTP `memnet-pi` on a human machine — not required here |

Always pass MCP arg **`session`** (not `session_id`). Cue then pin_map: if the ego is unknown, **`find`** (required `limit`) then `pin_map` a copied id. Prefer **one live `TSK`**.

## Doctrine (must)

| Idea | Meaning |
|------|---------|
| Shaped subgraph | pin_map emits a bounded neighbourhood (nodes + relationships), not a dump |
| GQL wire | openCypher-shaped mutate in `wire_lines`; general GQL in sibling skills |
| Live pin map | Primary **read**; optional `view=shell\|interior` for budget |
| NEW vs locators | LLM creates: mint with NEW; ingest pins use stable locators (`path`, `qname`, …) |
| BIND vs relation | Port-port -> `BIND`; node-node -> typed rel labels |
| Transport | In-process single agent; TCP/HTTP when sharing |
| Durable cabinet | Live AgensGraph hydrate/flush **claimed (0.7)** when `MEMNET_AGENSGRAPH_URL` is set. Optional Neo4j client **`memnet-llm[neo4j]`**; extra **0.14** claims `liveNeo4jClaimed=true`. Agents MUST NOT talk Bolt. |

**Tool gloss:** Primary pin-map read is MCP `pin_map` / CLI `query pin-map`. leftover `--anchor` / `anchor=` named leftover. `query_warm` / `query warm` are **deprecated aliases**. Formal shapes: [memnet-format](../memnet-format/SKILL.md) + `docs/grammar/`.

## How MCP tools fit the wire

MCP is a **thin CLI adapter**. Tools do **not** invent a second dialect: pin-map and mutate payloads live in the JSON envelope's **`stdout` / `wire_lines`** as GQL / openCypher-shaped text (or engine-rendered shaped subgraph).

| MCP tool | Role | What goes on the wire |
|----------|------|------------------------|
| `session_open` | Session lifecycle + schema map | `map_lines` = `SCHEMA Kind ; fields=id …` (registry). Optional `seed_lines` = openCypher-shaped seed (LAW auto-seeded). |
| `session_current` | Session lifecycle | Metadata only |
| `session_save` / `session_load` | Snapshot persist / resume | File path; next pin_map is still a shaped subgraph |
| `pin_map` | **Live shaped-subgraph read** | `stdout` = neighbourhood (+ LAW). Optional `view`, `anchors`. |
| `query_warm` | Deprecated alias for `pin_map` | Same as `pin_map` (including `view` / `anchors`) |
| `find` | Bounded seed lookup (0.5) | Required `limit`; `--kind` / locators / `keyword`; then `pin_map` a copied id. Not RAG. |
| `query_walk` | Hop debug (not primary pin map) | Walk lines for topology debug |
| `add` | Mutate **create** | `wire_lines` = openCypher-shaped creates with NEW as needed; pass `llm_id` under RSV |
| `update` | Mutate **patch / drop** | `wire_lines` = MATCH/SET/DELETE on known ids; pass `llm_id` under RSV |
| `read_get` / `read_list` | Lookup / enumerate | Single-row or label list — use to avoid inventing ids |
| `ingest_sysml` / `ingest_codebase` / `ingest_pcba` / `ingest_skills` | Path-B pin ingest (shipped) | Deterministic locator ids; **no** client NEW for source pins |
| `import_slice` | Path-B session import | `keep` / `reject` / `remint`; optional CheapLlmImportGuard |
| `reserve` / `extend` / `release` | Neighbourhood RSV (shipped) | Holder `llm_id` + TTL; MutateGate rejects foreign holder |
| `session_acl_grant` / `session_acl_bind` / `session_acl_enable` | CapsPolicy ACL (opt-in) | Off until `session_acl_enable`; not full ACL modes |
| `housekeep_stats` | Caps / counts | Envelope stats |
| `serve_status` | Transport probe | `{running,host,port}` — TCP-oriented |

**Agent loop <-> wire:** `pin_map` emits **shaped subgraph**; `add`/`update` accept **openCypher-shaped** mutate. Same property / label conventions.

**Not weird dialect — transport envelope:** every tool except `serve_status` returns JSON `{exit_code, stdout, stderr, session_id, errors}`. Parse **`stdout`** for pin-map / row text. Do not treat the JSON keys as the MemNet grammar.

**Misfits (gloss, do not invent tools):**

| Looks odd | Why | Agent action |
|-----------|-----|--------------|
| Name `query_warm` | Legacy alias | Use **`pin_map`** |
| Name `add` / `update` | CLI verbs | Put Cypher ops **inside** `wire_lines` |
| `serve_status` | Sounds optional | TCP probe only; skip under in-process |
| No tool named `mutate` in leftover gloss | Product write is **`mutate`**; leftover `add`/`update` remain leftover-named | Prefer `mutate` in this repo; leftover tools may still wrap CLI |
| No novel-writer tools | Dropped from product | Do not expect them |

## Agent loop

```text
pin_map -> reason -> mutate -> pin_map
```

1. Cue — known ego, or `find(limit=…, kind=…)` then copy an id. Prefer one live `TSK`.
2. Pin map — `pin_map(anchor=…, depth<=2)` — shaped subgraph; optional `view=shell` (tight) or `view=interior`; optional `anchors` for multi-ego under one `max_rows`.
3. Reason; copy assigned ids from the map.
4. `add` / `update` with **openCypher-shaped** statements (sparse Δ only).
5. `session_save` when durability is needed (offered file durable; live cabinet is optional 0.7+).

**MCP missing:** if MemNet tools are not in the session catalog, skip this loop — plain Markdown scratch only (no TOON/TRON). Do not invent tool calls. Wire shapes: [memnet-format](../memnet-format/SKILL.md).

## Graph about a node or relationship

| Want | Tool | Why |
|------|------|-----|
| Neighbourhood / ego slice (primary) | `pin_map` | Live **shaped subgraph** in `stdout` |
| Hop listing only | `query_walk` | Debug topology; not the reason loop |
| One known id | `read_get` | Single row; not a full neighbourhood |
| Find ids by label / field | `read_list` | Enumerate first; then pin_map on a real id |

**Recipe (node):** resolve id if needed (`read_list` / prior pin_map) -> `pin_map(anchor=<node_id>, depth=2, max_rows=50, session=…)` -> parse envelope **`stdout`**. Raise `depth` only if the slice is too thin; keep `max_rows` bounded.

**Recipe (relationship -> its two node ids):** there is **no** separate "get nodes of edge" tool. Endpoints are **on the relationship**.

1. Obtain the rel line: `read_get(id=<edge_id>)`, or copy it from pin_map `stdout`.
2. **Parse endpoints** (copy those values — they *are* the node ids):
   - **GQL / shaped present:** `(a)-[:TYPE {id: …}]->(b)` or engine present form with from/to brackets — first endpoint = source, second = destination.
   - **Legacy pipe** (`read_get` / `read_list` may still emit `@EDG:…`): columns `src` and `dist` — treat as from/to; do not teach pipe as agent mutate format.
3. Optional: `read_get(id=<node>)` for each full node; or `pin_map(anchor=<endpoint>, …)`. Do **not** use the edge id as a pin_map anchor. Do not invent ids.

## When ids must match model / schematic

**Decision:** pin into SysML / `.ato` / codebase / skill -> **stable locator** (deterministic ground id + locator props). New MemNet-only fact -> **NEW**. Do not conflate ingest with goldfish mutate.

| Need | Tool |
|------|------|
| Find by schematic field | `read_list(tag=…, where=["refdes=R1"])` (or `net=`, `qname=`, `path=`) |
| Confirm one ground id | `read_get(id=ATO_R1)` |
| Neighbourhood | `pin_map(anchor=ATO_R1, …)` |
| First materialise pin | `add` with **explicit** id + locators (not NEW) |
| Annotate about a pin | `add` with NEW `:CLM` then rel to the **copied** pin id |

```cypher
CREATE (c:CMP {id: 'ATO_R1', refdes: 'R1', path: 'boards/pdu/pdu.ato', recycle: 'persistent'})
MATCH (c {id: 'ATO_R1'}) SET c.value = '10k', c.recycle = 'persistent'
CREATE (clm:CLM {id: 'NEW', type: 'decision', code: 'keep R1 10k', recycle: 'persistent'})
```

**Forbidden:** client NEW for R1/U2/nets/SysML qnames/paths; inventing `C_rand_99`; NEW on patch. **Pitfall:** `add` fails if id exists — look up first. Path-B ingest is **shipped** (`ingest_sysml` / `ingest_codebase` / `ingest_pcba` / `ingest_skills`) — use it for artefact pins; seed via `seed_lines` / explicit-id `add` only when ingest does not cover the artefact. Ingest is **not** pin-map export / round-trip.

**Re-id (wrong ground id):** `update` with MATCH old id SET `id=NewId` (optional merge when NewId exists; nodes only; retarget rels; drop OldId). Self id=OldId is a no-op.

```cypher
MATCH (n {id: 'C_rand_99'}) SET n.id = 'ATO_R1', n.recycle = 'persistent' /* merge=true when engine supports fold */
```

## Neighbourhood reserve (shipped)

Neighbourhood **reserve** with holder **`llm_id`** + **TTL** prevents same-session write races. MCP:

```text
reserve(anchor, llm_id, depth=2, ttl_s=120, session=…) -> rid, until
extend(llm_id, rid|anchor, ttl_s=120, session=…) -> until
release(llm_id, rid|anchor, session=…) -> ok
```

Pin map may show intersecting leases as shaped present:

```cypher
(:RSV {id: 'R7', llm_id: 'coder_a', anchor: 'ATO_R1', depth: 2, until: '2026-07-24T08:15:00Z', left_s: 87})
```

**Never** `@RSV:` pipe. SSOT: MemNet `docs/grammar/memnet-neighbourhood-reserve.md`. Mutate on reserved ids requires matching `llm_id` on `add` / `update`. Full session ACL modes / roles / `session_token` remain **design**; CapsPolicy ACL is opt-in (`session_acl_enable`).

## Essential tools (quick)

| Tool | When | Notes |
|------|------|-------|
| `serve_status` | Reachability / probe | TCP serve `:18765` when HTTP MCP bridges; Cursor entry is `:18766/mcp` |
| `session_open` | New session | `map_lines` (or `map_file`) + optional `seed_lines`; `allow_new_relation=true` for custom rel types |
| `session_save` / `session_load` | Persist / resume | Snapshot file path |
| `session_current` | Session metadata | |
| `pin_map` | **Primary read** = shaped subgraph | `anchor` and/or `anchors`; `depth`/`max_rows`; optional `view` |
| `find` | Seed ids when ego unknown | `limit` required; then pin_map |
| `query_warm` | Legacy alias for `pin_map` | Same params |
| `query_walk` | Hop debug | |
| `add` / `update` | Mutate | `wire_lines`: openCypher-shaped; `llm_id` under RSV |
| `ingest_sysml` / `ingest_codebase` / `ingest_pcba` / `ingest_skills` | Path-B artefact pins | Locator ids; no client NEW |
| `import_slice` | Import a bounded slice | Optional ImportGuard |
| `reserve` / `extend` / `release` | RSV leases | `llm_id` + TTL |
| `read_get` / `read_list` | Single id / enumerate | Prefer over inventing ids |
| `housekeep_stats` | Caps / counts | |

Args detail: [references/tool-parameters.md](references/tool-parameters.md). Policy: [references/mcp-policy.md](references/mcp-policy.md). Full map: [references/tool-grammar.md](references/tool-grammar.md).

## GQL wire (shapes)

Line shapes, mutate ops, BIND vs relation, and examples: [memnet-format](../memnet-format/SKILL.md). Formal SSOT: `docs/grammar/gql-wire-profile.md`.

## SysML v2 modeling (relatives cache)

**Policy skill:** [sysml-memnet-cache](../sysml-memnet-cache/SKILL.md).

| Turn phase | Tool |
|------------|------|
| Preflight | MemNet MCP in catalog? Then optional `serve_status` (TCP only) |
| Read cache | pin_map — `pin_map(anchor=TSK_model_<short>, depth=2, max_rows=50)` |
| Bootstrap | `session_open` + `map_file` / `map_lines` + `seed_lines`; `allow_new_relation=true` for `owns`. Prefer `ingest_sysml` for `.sysml` pins. |
| Write delta | `add` / `update` (openCypher-shaped); `llm_id` if RSV held |
| Persist | `session_save` -> project `.memnet/` snap |
| Resume | `session_load` or `MEMNET_SESSION` |

Tag vocabulary: [sysml-memnet-documentation](../sysml-memnet-documentation/SKILL.md).

**Do not** use chat or `AGENT-CONTEXT.md` for topology when a live session is available.

## MUSTNOT

- Invent ids already present on the pin map — copy them.
- Emit pipe `@TAG:...` rows as agent I/O — GQL / shaped wire only. Includes `@RSV:` — use `:RSV` present forms instead.
- Recommend TOON/TRON for handoffs — prefer GQL wire or plain Markdown.
- Restore or depend on novel-writer MCP extras.

## Related

| Path | Role |
|------|------|
| [memnet-format](../memnet-format/SKILL.md) | MemNet GQL wire conventions |
| [references/atomisation.md](references/atomisation.md) | One fact per row |
| [references/tool-grammar.md](references/tool-grammar.md) | MCP tool <-> wire map |
| MemNet `docs/grammar/gql-wire-profile.md` | Product wire SSOT |
