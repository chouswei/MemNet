# MemNet

Mission working memory for LLMs. A named session graph (GQL **node**/vertex, **edge**/relationship, **property**) that agents **pin** and **mutate** — not a notepad in chat, and not the search library.

MemNet sits **between** LLM call pipelines and data search (MN-REQ-00). Corpus lookup stays on the host (grep, ingest, optional RAG); it may propose **locators**. In the session, kinds/tags are overlapping **cues**; recall is **serial** — cue, then a bounded `pin_map` neighbourhood. It is not GraphRAG, not a vector store, and not AgensGraph/Neo4j.

This repo ships the engine + generic MCP only. **Product shape:** [`docs/SHAPE.md`](docs/SHAPE.md). **Pinned role:** working set of **a few technical documents** (atoms and locators, not PDF bytes) plus live `TSK`/`USR`/`MOD`, re-read fast. Tens of MiB typical; **hundreds of MiB still in role**; gigabytes = RAG/cabinet.

Package **`memnet-llm`** (CLI **`memnet`**). Python ≥ 3.11. Repo product **0.19.3**. Last published PyPI wheel is **`memnet-llm==0.19.0`** until `0.19.3` is uploaded (`pip install memnet-llm` still resolves 0.19.0). **1.0** stays unclaimed.

## Install + quick CLI

```bash
pip install memnet-llm
# or pin: pip install memnet-llm==0.19.3  (after PyPI upload; else ==0.19.0)
# optional extras (drivers only — not AgensGraph/Neo4j servers):
# pip install 'memnet-llm[mcp]'
# pip install 'memnet-llm[agensgraph]'
# pip install 'memnet-llm[neo4j]'
# contributors: pip install -e ".[dev,mcp]"
```

CLI needs a serve process. Prefer local IPC; TCP is the fallback.

```bash
# Terminal 1
export MEMNET_IPC_SOCKET=/tmp/memnet.sock
memnet serve --ipc

# Terminal 2 (same MEMNET_IPC_SOCKET)
memnet session open --map-file parts/common/memnet/memnet/examples/schema.example.txt
# demo-world map for tests; warehouse GQL below is illustrative (not that world's field list)
# stderr prints MEMNET_SESSION=mn_… — pass it as --session (serve proxies argv, not your shell env)

memnet mutate --session mn_… --stdin <<'EOF'
CREATE (t:TSK {goal:'Clear warehouse', status:'in_progress'})
CREATE (n:NPC {role:'helper', status:'active'})
MATCH (n:NPC {role:'helper'}), (t:TSK {goal:'Clear warehouse'})
CREATE (n)-[:helps {note:'labour'}]->(t)
EOF

memnet query find --session mn_… --kind TSK --limit 8
memnet query pin-map --session mn_… --kind TSK --locator 'goal=Clear warehouse' --depth 2
```

Shaped pin map (illustrative; nickname `id` only if set):

```cypher
(:TSK {goal: 'Clear warehouse', status: 'in_progress'})
(:NPC {role: 'helper', status: 'active'})
(:NPC {role: 'helper'})-[:helps {note: 'labour'}]->(:TSK {goal: 'Clear warehouse'})
```

Create by labels+properties (`CREATE ()` is legal). leftover `id:'NEW'` mint / `@ID:` AssignedIdMap is leftover, not product. Each turn `pin_map(q)` (or skip); **drop** prior maps from the prompt; leftover `--anchor` is a nickname cue. The agent dialect is **GQL only** (openCypher-shaped). Wire SSOT: [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md). Layer accept is dead.

MCP in-process (`memnet-mcp`) does not need serve — that's the usual single-agent path.

## Session pipe

Handoff between modules/agents is the **`sessionId`** (treat it as a secret capability). The peer **re-`pin_map`s** — don't dump the graph into chat. Keep working/mission memory distinct from other product handles (e.g. a company store id); mixing those is an app concern, not MemNet's job.

## Import absorb vs shared session

- **Path A** — same `sessionId`; peers just re-`pin_map`. No import.
- **Path B** — separate member session; lead absorbs a bounded slice via `memnet import-slice` (pattern match, not MERGE-by-id). leftover `keep`/`reject`/`remint` `id_policy` is leftover, not product. That's absorb into the lead SSOT, not append. Optional **ImportGuard** soft policy: host hook and/or env-gated **CheapLlmImportGuard** (`MEMNET_IMPORT_GUARD_API_KEY`; optional `MEMNET_IMPORT_GUARD_BASE_URL` / `MEMNET_IMPORT_GUARD_MODEL`). `--no-guard` skips even when the key is set.

## ACL + transport

**CapsPolicy ACL** (shipped; off by default until `session acl-enable`): who (`caller`) / `pin_map` vs mutate / `WorkerWriteScope` hard reject / optional `missionId`+`lease` bind.

**RSV** neighbourhood reserve exists (`memnet reserve` / `extend` / `release`; `llm_id` + TTL; pin map may show `## Reserves`).

**Transport:** in-process MCP default (one graph per process). Shared graph: `memnet serve --ipc` (`MEMNET_IPC_SOCKET`) or TCP `memnet serve` (`127.0.0.1:18765`). Multitask / parallel workers need a shared serve — not default in-process.

**Durable:** optional clients `memnet-llm[agensgraph]` and `memnet-llm[neo4j]`; cabinets are external and not vendored. **0.7** AgensGraph live hydrate/flush proven (`liveCabinetClaimed`); CI skips unless `MEMNET_AGENSGRAPH_URL` is set. Neo4j is the same hydrate/flush seam (`Neo4jAdapter`); extra **0.14** claims `liveNeo4jClaimed=true` (live round-trip yes; hid flush; leftover-nickname hydrate after hid miss). Extra **0.16**: optional library database (`MEMNET_NEO4J_LIBRARY_DATABASE`) on the same URL emits locators only. Skip unless `MEMNET_NEO4J_URL`.

## Deferred (honest)

- Hosted AgensGraph as a product service (operator runs the server; this repo does not vendor it)
- N-server session pipe ([#47](https://github.com/chouswei/MemNet/issues/47))
- SysML file reverse / pin-map re-ingest (MN-REQ-11.5 SHOULD / [#66](https://github.com/chouswei/MemNet/issues/66)) — 0.19 writes cue `pin_map` GQL out; identity merge on the way back is later
- Host search / RAG as a MemNet tool — application nest only ([`docs/extras/memnet-host-search-nest.md`](docs/extras/memnet-host-search-nest.md))

## Links

| Doc | Role |
|-----|------|
| [`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) | Agent playbook (GQL only) |
| [`docs/SHAPE.md`](docs/SHAPE.md) | Product shape from the problem |
| [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md) | GQL wire SSOT |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Version map SSOT |
| [`sysml-models/`](sysml-models/) | Requirements / verify |
| [`docs/operations/multi-agent-sessions.md`](docs/operations/multi-agent-sessions.md) | Multitask ops |
| [`docs/README.md`](docs/README.md) | Full docs index |

Layout: [`LAYOUT.md`](LAYOUT.md) · [`AGENTS.md`](AGENTS.md). Novel-writer is out: [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md).

## Licence

MIT
