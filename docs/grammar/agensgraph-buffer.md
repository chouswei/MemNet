# AgensGraph buffer — durable graph behind shared LLM memory

**Status:** version map SSOT [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md). 0.7 live cabinet **shipped**. 0.8 is teach/shape, not a second cabinet claim. Server not vendored. Fake + skip unless `MEMNET_AGENSGRAPH_URL` is set.  
**Audience:** product developers.  
**Promotion (historical):** durable adapter was the notch after M2 (named M2.5). **Done in 0.7.** M3 playbook GQL rewrite is **done in 0.8**. See [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md).

**Product framing (2026-08-13):** MemNet is **mission working memory for LLMs** — not the search corpus, not GraphRAG. Multi-agent / Multitask sessions; goldfish re-read via shaped `pin_map`; gated mutate. In-session recall is serial cue then neighbourhood. A MemNet **session** can be SSOT for a mission / that shared memory (“SOMETHING”): handoff between LLMs = deliver **session id** (+ anchors / write scope); peers **re-pin_map** — do **not** receive a graph dump in chat. Chat is never SSOT ([`../multi-agent-sessions.md`](../multi-agent-sessions.md)). [AgensGraph](https://github.com/skaiworldwide-oss/agensgraph) (Postgres + property graph / openCypher / partial GQL) is the **durable / backing** graph **behind** sessions — it does **not** replace the session handle for agent handoff, and is not the default agent teach surface. **MUST NOT** reframe MemNet as a Cypher proxy to AgensGraph.

**Wire:** agent teach = **GQL only** ([`gql-wire-profile.md`](gql-wire-profile.md)). No Layer / Tier A path.

| Question | Answer |
|----------|--------|
| **Can** GQL be the LLM wire? | **Yes.** |
| **Should** it be the only agent dialect? | **Yes** (ADR-001 + supersession). |
| MemNet role | **Shared working memory** for LLMs (sessions, budgets, Multitask, mint/`NEW`, MutateGate). |
| Session role | Mission / shared-memory **SSOT handle**; handoff = session id (+ anchors / scope); peers re-`pin_map`. |
| AgensGraph role | **Durable backing** behind sessions; hydrate into / flush from MemNet (**M2.5**) — not the handoff handle. |

---

## Architecture

```text
  LLM(s)  <-->  MemNet = shared working memory
                  (GQL wire: shaped pin_map / gated mutate)
                    |
                    |  hydrate / flush (one sync owner)
                    v
               AgensGraph = durable backing graph
```

| Path | Role |
|------|------|
| **LLM ↔ MemNet** | Shared memory via **session**; goldfish `pin_map`; GQL teach; gated mutate |
| **LLM → LLM handoff** | Pass **session id** (+ anchors / write scope); peer re-`pin_map` — not a chat graph dump |
| **MemNet → AgensGraph** | Flush settled / durable subgraphs out of the session buffer |
| **AgensGraph → MemNet** | Hydrate into a session pin budget (ego-bounded) |
| **LLM ↔ AgensGraph (direct)** | **Out of default MemNet teach** (no agent Bolt / driver as goldfish or handoff path) |

---

## M2.5 scope (sketch)

| Concern | Plan |
|---------|------|
| **Hydrate** | Pull a durable subgraph into the live session under pin / depth / view budget |
| **Flush** | Push settled or explicitly durable pins from MemNet into AgensGraph |
| **Connection** | Store URL / credentials via env (e.g. `MEMNET_AGENSGRAPH_*` placeholders) — not hardcoded secrets |
| **Sync owner** | **One** owner process (MemNet serve / adapter) owns hydrate+flush — **MUST NOT** dual-write |
| **Dialect** | Same openCypher-family GQL as agent wire (CIP / oC9 family; MemNet-gated subset); no Layer revival |

### Out of M2.5 scope

| MUST NOT | Why |
|----------|-----|
| Teach **LLM ↔ AgensGraph direct** (agent Bolt / raw driver) as default | Breaks shared MemNet memory / goldfish / Multitask owner |
| Use durable store (or chat dump) as agent **handoff** instead of session id | Session is the SSOT handle; peers re-`pin_map` |
| Thin Cypher-relay-only (drop MemNet; “just a proxy”) | Collapses product value — MemNet is the shared memory |
| Dual-write without a single sync owner | Two writers → split brain |
| Claim adapter shipped before M2.5 lands | Historical — **0.7** live path is the claim |
| Revive Layer / Tier A | ADR-001 supersession |


---

## Implementation status (client slice)

**M2.5 live path proven (0.7).** Client/adapter hydrate+flush is implemented against an **external** AgensGraph; Fake remains the always-on CI path. The live mark still **skips** unless `MEMNET_AGENSGRAPH_URL` is set. This repo does **not** vendor or host the server.

| Piece | Status |
|-------|--------|
| `DurableStoreAdapter` ABC (`hydrate` / `flush` + `HydrateBudget`) | Landed |
| `DurableSyncOwner` (one process owner; rejects dual bind) | Landed |
| `FakeDurableAdapter` + hydrate → live session → shaped `pin_map` tests | Landed (always-on CI path) |
| `AgensGraphAdapter` env config (`MEMNET_AGENSGRAPH_*`) | Landed |
| `AgensGraphAdapter.hydrate` / `flush` via `psycopg` + openCypher | Landed (client only) |
| Optional extra `memnet-llm[agensgraph]` (`psycopg`, not the DB server) | Landed |
| serve / MCP bind `get_sync_owner(make_adapter_from_env())` once | Landed |
| Live integration test | Skip unless `MEMNET_AGENSGRAPH_URL` set |
| Claim adapter / M2.5 shipped | **0.7** — live hydrate/flush proven; still not a hosted cabinet service |

Agents continue to use MemNet GQL `pin_map` / mutate only. Durable calls go through `DurableSyncOwner` / `SessionLifecycle.hydrate_from_durable` — never as the LLM primary path.

### Pointing MemNet at an external cabinet

```bash
# Client driver only (does not install AgensGraph server):
pip install 'memnet-llm[agensgraph]'

export MEMNET_AGENSGRAPH_URL='postgresql://host:5432/memnet'
export MEMNET_AGENSGRAPH_USER='agens'          # optional if in URL
export MEMNET_AGENSGRAPH_PASSWORD='…'         # optional if in URL
export MEMNET_AGENSGRAPH_GRAPH='memnet'       # optional; default memnet

# Force Fake seam even when URL is set (CI / local spike):
export MEMNET_DURABLE_FAKE=1
```

Factory / startup semantics:

| Env | Adapter bound by `get_sync_owner()` |
|-----|-------------------------------------|
| `MEMNET_DURABLE_FAKE` truthy | `FakeDurableAdapter` |
| else `MEMNET_AGENSGRAPH_URL` set | `AgensGraphAdapter` (client) |
| else | `FakeDurableAdapter` (dev/test seam — not a production cabinet) |

`memnet serve` and `memnet-mcp` bind the owner once at process start using those rules.

### Hydrate / flush Cypher (sketch)

- **Hydrate nodes:** `MATCH (ego {id}) OPTIONAL MATCH (ego)-[*0..depth]-(n) RETURN label(n), properties(n) LIMIT max_nodes`
- **Hydrate edges:** among nodes in that ego ball, `MATCH (a)-[r]->(b) RETURN label(r), properties(r), a.id, b.id LIMIT max_edges`
- **Flush nodes:** `MERGE (n:TAG {id}) SET n.field = …, n._memnet_tag = 'TAG'`
- **Flush edges:** `MATCH (a {id: src}), (b {id: dist}) MERGE (a)-[r:REL {id}]->(b) SET …`

MemNet tags become vertex labels; `EDG.relation` becomes the edge label. Mapping back uses `_memnet_tag` when present.

### Developer note: optional local AgensGraph (docs only)

This repo does **not** vendor AgensGraph or require docker-compose for tests. Developers who want a local cabinet can run any upstream AgensGraph image themselves and export `MEMNET_AGENSGRAPH_URL`. Example (illustrative — not a product dependency):

```bash
# Operator-owned; not started by MemNet tests/CI:
docker run --rm -p 5432:5432 <your-agensgraph-image>
export MEMNET_AGENSGRAPH_URL='postgresql://agens:agens@127.0.0.1:5432/memnet'
pytest -m agensgraph_live
```

---

## Related

| Path | Role |
|------|------|
| [`gql-wire-profile.md`](gql-wire-profile.md) | M1 wire SSOT; M2.5 boundary in §6 |
| [`../adr/ADR-001-gql-agent-wire.md`](../adr/ADR-001-gql-agent-wire.md) | Decision; M2.5 in migration plan |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | Phase order: M2 → M2.5 → M3 |
| [`../multi-agent-sessions.md`](../multi-agent-sessions.md) | Session SSOT; handoff by session id; chat never SSOT |
