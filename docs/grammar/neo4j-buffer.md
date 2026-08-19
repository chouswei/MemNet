# Neo4j cabinet client — second durable adapter behind shared LLM memory

**Status:** client landed; **live Neo4j round-trip not claimed** (`liveNeo4jClaimed=false`). Skip live pytest unless `MEMNET_NEO4J_URL` is set. Server not vendored.  
**Audience:** product developers.  
**Sibling:** AgensGraph 0.7 live cabinet [`agensgraph-buffer.md`](agensgraph-buffer.md). Same MUST NOTs.

Neo4j is a second **external durable cabinet**, not goldfish, not agent wire, not a GraphQL facade, and not a vendored server. SysML first-class server: `DurableCabinet` / `Neo4jCabinetServer` (clients stay `DurableBuffer` adapters). Operator soak ≠ `liveNeo4jClaimed`. MemNet stays mission working memory. Agents talk GQL `pin_map` / mutate to MemNet. Only `DurableSyncOwner` / `SessionLifecycle` call `hydrate` / `flush`. **MUST NOT** teach LLM ↔ Bolt as the goldfish path or reframe MemNet as a Cypher proxy.

Same ABC as AgensGraph: `DurableStoreAdapter.hydrate` / `flush` (`memnet/durable/adapter.py`). Same ego `HydrateBudget`. Same Record shape. Factory binds **one** adapter (see below). Recall/Commit is unchanged.

| Piece | Status |
|-------|--------|
| `Neo4jAdapter.from_env()` + hydrate/flush (official `neo4j` driver) | Landed (client) |
| Optional extra `memnet-llm[neo4j]` | Landed (driver only — not the DB server) |
| Unit tests / recorded Bolt stub | Always-on CI |
| `pytest -m neo4j_live` | Skip unless `MEMNET_NEO4J_URL` |
| Live round-trip claim | **Leftover** — `liveNeo4jClaimed=false` |

### Pointing MemNet at an external Neo4j cabinet

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

Cypher is **Neo4j** (`labels(n)`, `type(rel)`, Bolt parameters) — not the AgensGraph SQL/openCypher mix. Hydrate is an ego k-hop under budget. Flush MERGEs nodes then relationships; each `session.run` auto-commits so a later hydrate error cannot roll back a successful flush.

### MUST NOT

| MUST NOT | Why |
|----------|-----|
| Teach **LLM ↔ Neo4j / Bolt** as goldfish or handoff | Breaks shared MemNet memory / Multitask owner |
| Dual-write / silently pick when both cabinet URLs are set | Two writers → split brain |
| Claim live Neo4j from Fake or unit stubs | Mirror 0.7 honesty; leftover until a live round-trip |
| Vendor a Neo4j server in this repo | Client extra only |

## Related

| Path | Role |
|------|------|
| [`agensgraph-buffer.md`](agensgraph-buffer.md) | First cabinet client; 0.7 live claim |
| [`gql-wire-profile.md`](gql-wire-profile.md) | Agent wire SSOT (not Bolt) |
| [`../ROADMAP-0.5.md`](../ROADMAP-0.5.md) | Version map; this is not a 1.0 bump |
