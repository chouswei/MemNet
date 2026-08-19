# Between MemNet and Neo4j

**Status:** client landed; **live Neo4j round-trip not claimed** (`liveNeo4jClaimed=false`). Skip live pytest unless `MEMNET_NEO4J_URL` is set. Server not vendored.  
**Audience:** product developers.  
**Sibling:** AgensGraph 0.7 live cabinet [`agensgraph-buffer.md`](agensgraph-buffer.md). Same MUST NOTs. Same ABC / owner / budget.  
**Shape:** cabinet **behind** the session, not instead of it ([`../SHAPE.md`](../SHAPE.md) §5).

MemNet sits **between** LLM call pipelines and a durable graph. [Neo4j](https://neo4j.com/) is one **external cabinet** on that far side. It is not goldfish, not agent wire, not GraphRAG, not a GraphQL facade, and not a vendored server. Agents talk GQL `pin_map` / mutate to **MemNet**. Only `DurableSyncOwner` / `SessionLifecycle` call `hydrate` / `flush` over Bolt. **MUST NOT** teach LLM ↔ Bolt as the goldfish path or reframe MemNet as a Cypher proxy.

---

## What talks to what

```text
  LLM(s)  <-->  MemNet = shared working memory
                  (GQL wire: shaped pin_map / gated mutate)
                    |
                    |  hydrate / flush (one sync owner)
                    v
               Neo4j  = durable backing graph (external cabinet)
```

| Path | Role |
|------|------|
| **LLM ↔ MemNet** | Shared memory via **session**; goldfish `pin_map`; GQL teach; gated mutate |
| **LLM → LLM handoff** | Pass **session id** (+ anchors / write scope); peer re-`pin_map` — not a chat dump, not a Bolt URI |
| **MemNet → Neo4j** | Flush settled / durable subgraphs out of the session buffer (`MERGE` nodes, then relationships) |
| **Neo4j → MemNet** | Hydrate into a session pin budget (ego k-hop under `HydrateBudget`) |
| **LLM ↔ Neo4j (direct)** | **Out of default MemNet teach** (no agent Bolt / driver / Browser / GraphQL as goldfish or handoff) |

Recall/Commit is unchanged. The cabinet does not replace \(\mathrm{Recall}(q)\) or \(\mathrm{Commit}(\Delta)\). A new process opens a **new** session id, hydrates an ego under budget, and agents keep talking to MemNet ([durable hydrate/flush case study](../../sysml-models/outputs/durable-hydrate-flush-case-study.md)).

---

## Same seam, different dialect

Neo4j and AgensGraph are **two cabinets**, not two products. Factory binds **one** adapter. Dual-write is an error unless `MEMNET_DURABLE_BACKEND` picks one.

| Shared | Different |
|--------|-----------|
| `DurableStoreAdapter.hydrate` / `flush` | Neo4j Cypher vs AgensGraph SQL/openCypher mix |
| One `DurableSyncOwner` | Bolt (`neo4j` driver) vs `psycopg` |
| Ego `HydrateBudget` (depth, `max_nodes` / `max_edges`) | `labels(n)` (list) vs AgensGraph `label(n)` |
| Record shape; `_memnet_tag` round-trip | Named database (`MEMNET_NEO4J_DATABASE`, default `neo4j`) vs Agens graph name |
| Fake always-on CI; live mark skips unless URL | Live claim: Agens **0.7** proven; Neo4j **unclaimed** |

Cypher sketches (Neo4j; parameterised ids):

- **Hydrate nodes:** `MATCH (ego {id: $ego_id}) OPTIONAL MATCH (ego)-[*0..depth]-(n) RETURN labels(n), properties(n) LIMIT max_nodes`
- **Hydrate edges:** among ids in that ego ball, `MATCH (a)-[r]->(b) … RETURN type(rel), properties, a.id, b.id LIMIT max_edges`
- **Flush nodes:** `MERGE (n:TAG {id: $id}) SET n += $props, n._memnet_tag = 'TAG'`
- **Flush edges:** `MATCH (a {id: $src}), (b {id: $dist}) MERGE (a)-[r:REL {id: $id}]->(b) SET …`

MemNet tags become vertex labels; `EDG.relation` becomes the relationship type. Mapping back prefers `_memnet_tag`, else `first_label`. Identifiers and ids are validated before they reach Bolt (`neo4j_bad_ident` / `neo4j_bad_id`). Each `session.run` auto-commits so a later hydrate error cannot roll back a successful flush.

Engine: `parts/common/memnet/memnet/durable/neo4j.py`.

---

## Steal grain, reject the stack

Neo4j is a **property-graph server**. MemNet is **mission working memory**. Steal questions and privilege grain; do not become Neo4j.

| Neo4j-class move | MemNet |
|------------------|--------|
| TRAVERSE / MATCH | `pin_map` (shaped ego walk) |
| WRITE (CREATE / SET / DELETE) | `mutate` (`add` / `update`) via MutateGate |
| Label / id GRANT | `WorkerWriteScope` (when session ACL is enabled) |
| Bolt / Browser / `@neo4j/graphql` as the LLM tool | **Reject** as goldfish. Wire is GQL `pin_map` / mutate only (ADR-001) |
| GraphRAG / `generate(prompt)` on retrieved nodes | **Reject** as MemNet. Host Snap may propose locators; no `rag_query`, no `pin_map.generate` ([#77](https://github.com/chouswei/MemNet/issues/77), [`memnet-host-search-nest.md`](memnet-host-search-nest.md)) |
| Graphiti-style Neo4j as the agent memory | **Reject**. Graphiti `search` (BM25 \|\| cosine \|\| BFS + RRF) is a cousin of *cue then hop*, not a cabinet substitute |
| Vector / FTS **on** the cabinet | If an operator later enables it, keep it **behind** hydrate budget — not LLM↔store RAG |

ACL grain table (CapsPolicy): [`../../sysml-models/outputs/system-design-notes.md`](../../sysml-models/outputs/system-design-notes.md). Full ACL modes / `session_token` remain to-be.

---

## Pointing MemNet at an external Neo4j cabinet

```bash
# Client driver only (does not install a Neo4j server):
# Until 0.9 is on PyPI, install from this repo (editable). PyPI lag: memnet-llm==0.4.6.
pip install -e ".[neo4j]"
# or: pip install 'memnet-llm[neo4j]'   # currently resolves 0.4.6 on PyPI — not this client

export MEMNET_NEO4J_URL='bolt://127.0.0.1:7687'   # or neo4j://…
export MEMNET_NEO4J_USER='neo4j'                 # optional if in URL
export MEMNET_NEO4J_PASSWORD='…'                 # optional if in URL
export MEMNET_NEO4J_DATABASE='neo4j'             # optional; default neo4j
```

Factory / startup semantics (`make_adapter_from_env`):

| Env | Adapter bound by `get_sync_owner()` |
|-----|-------------------------------------|
| `MEMNET_DURABLE_FAKE` truthy | `FakeDurableAdapter` |
| else both AgensGraph and Neo4j URLs set | **error** unless `MEMNET_DURABLE_BACKEND` is `agensgraph` or `neo4j` |
| else `MEMNET_AGENSGRAPH_URL` set | `AgensGraphAdapter` |
| else `MEMNET_NEO4J_URL` set | `Neo4jAdapter` |
| else | `FakeDurableAdapter` (dev/test seam — not a production cabinet) |

`memnet serve` and `memnet-mcp` bind the owner once at process start using those rules.

| Piece | Status |
|-------|--------|
| `Neo4jAdapter.from_env()` + hydrate/flush (official `neo4j` driver) | Landed (client) |
| Optional extra `memnet-llm[neo4j]` | Landed (driver only — not the DB server) |
| Unit tests / recorded Bolt stub | Always-on CI |
| `pytest -m neo4j_live` | Skip unless `MEMNET_NEO4J_URL` |
| Live round-trip claim | **Leftover** — `liveNeo4jClaimed=false` |

This repo does **not** vendor Neo4j or require docker-compose for tests. Operators who want a local cabinet run any upstream image themselves and export `MEMNET_NEO4J_URL`. Example (illustrative — not a product dependency):

```bash
# Operator-owned; not started by MemNet tests/CI:
docker run --rm -p 7687:7687 neo4j:5
export MEMNET_NEO4J_URL='bolt://127.0.0.1:7687'
pytest -m neo4j_live
```

---

## MUST NOT

| MUST NOT | Why |
|----------|-----|
| Teach **LLM ↔ Neo4j / Bolt / Browser / GraphQL** as goldfish or handoff | Breaks shared MemNet memory / Multitask owner |
| Dual-write / silently pick when both cabinet URLs are set | Two writers → split brain |
| Claim live Neo4j from Fake or unit stubs | Mirror 0.7 honesty; leftover until a live round-trip |
| Vendor a Neo4j server in this repo | Client extra only |
| Treat Neo4j as a MemNet substitute or as the agent handoff handle | Handoff = session id; peers re-`pin_map` |
| Thin Cypher-relay-only (drop MemNet; “just a proxy”) | Collapses product value — MemNet is the shared memory |
| Hold **1.0** for live Neo4j | 1.0 = 0.5–0.8 claimed; live Neo4j is **Later** ([`../ROADMAP-0.5.md`](../ROADMAP-0.5.md)) |

---

## Related

| Path | Role |
|------|------|
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | First cabinet client; 0.7 live claim |
| [`gql-wire-profile.md`](gql-wire-profile.md) | Agent wire SSOT (not Bolt) |
| [`memnet-host-search-nest.md`](memnet-host-search-nest.md) | Host Snap vs session Shape; Neo4j GraphRAG contrast |
| [`../SHAPE.md`](../SHAPE.md) | Cabinet behind, not instead |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | Version map; 0.9 client extra; live Neo4j is Later |
| [`../multi-agent-sessions.md`](../multi-agent-sessions.md) | Session SSOT; handoff by session id |
