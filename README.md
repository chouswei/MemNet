# MemNet

Mission working memory for LLMs. A named session graph (GQL **node**/vertex, **edge**/relationship, **property**) that agents **pin** and **mutate** — not a notepad in chat, and not the search library.

MemNet sits **between** LLM call pipelines and data search (MN-REQ-00). Corpus lookup stays on the host (grep, ingest, optional RAG); it may propose **locators**. In the session, kinds/tags are overlapping **cues**; recall is **serial** — cue, then a bounded `pin_map` neighbourhood. It is not GraphRAG, not a vector store, and not AgensGraph/Neo4j.

This repo ships the engine + generic MCP only. **Pinned role:** working set of **a few technical documents** (atoms and locators, not PDF bytes) plus live `TSK`/`USR`/`MOD`, re-read fast. Tens of MiB typical; **hundreds of MiB still in role**; gigabytes = RAG/cabinet.

Package **`memnet-llm`** (CLI **`memnet`**). Python ≥ 3.11.

## Install + quick CLI

```bash
pip install memnet-llm
# optional: pip install 'memnet-llm[mcp]'
# optional durable client (psycopg only — not an AgensGraph server):
# pip install 'memnet-llm[agensgraph]'
```

CLI needs a serve process. Prefer local IPC; TCP is the fallback.

```bash
# Terminal 1
export MEMNET_IPC_SOCKET=/tmp/memnet.sock
memnet serve --ipc

# Terminal 2 (same MEMNET_IPC_SOCKET)
memnet session open --map-file parts/common/memnet/memnet/examples/schema.example.txt
# stderr prints MEMNET_SESSION=mn_… — pass it as --session (serve proxies argv, not your shell env)

memnet add --session mn_… --stdin <<'EOF'
CREATE (t:TSK {id:'NEW', goal:'Clear warehouse', status:'in_progress'})
CREATE (n:NPC {id:'NEW', role:'helper', status:'active'})
EOF
# stderr @ID lines mint real ids (e.g. TSK1, NPC1) — copy them

memnet add --session mn_… --stdin <<'EOF'
MATCH (n:NPC {id:'NPC1'}), (t:TSK {id:'TSK1'})
CREATE (n)-[:helps {id:'NEW', note:'labour'}]->(t)
EOF

memnet query pin-map --session mn_… --anchor TSK1 --depth 2
```

Shaped pin map (illustrative):

```cypher
(:TSK {id: 'TSK1', goal: 'Clear warehouse', status: 'in_progress'})
(:NPC {id: 'NPC1', role: 'helper', status: 'active'})
(:NPC {id: 'NPC1'})-[:helps {id: 'E1', note: 'labour'}]->(:TSK {id: 'TSK1'})
```

Create with `id:'NEW'`; patch/settle with known ids only. The agent dialect is **GQL only** (openCypher-shaped): shaped `pin_map` read + gated mutate. Wire SSOT: [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md). Layer accept is dead.

MCP in-process (`memnet-mcp`) does not need serve — that's the usual single-agent path.

## Session pipe

Handoff between modules/agents is the **`sessionId`** (treat it as a secret capability). The peer **re-`pin_map`s** — don't dump the graph into chat. Keep working/mission memory distinct from other product handles (e.g. a company store id); mixing those is an app concern, not MemNet's job.

## Import absorb vs shared session

- **Path A** — same `sessionId`; peers just re-`pin_map`. No import.
- **Path B** — separate member session; lead absorbs a bounded slice via `memnet import-slice` (`keep` / `reject` / `remint`). That's absorb into the lead SSOT, not append. Optional **ImportGuard** soft policy: host hook and/or env-gated **CheapLlmImportGuard** (`MEMNET_IMPORT_GUARD_API_KEY`; optional `MEMNET_IMPORT_GUARD_BASE_URL` / `MEMNET_IMPORT_GUARD_MODEL`). `--no-guard` skips even when the key is set.

## ACL + transport

**CapsPolicy ACL** (shipped; off by default until `session acl-enable`): who (`caller`) / `pin_map` vs mutate / `WorkerWriteScope` hard reject / optional `missionId`+`lease` bind.

**RSV** neighbourhood reserve exists (`memnet reserve` / `extend` / `release`; `llm_id` + TTL; pin map may show `## Reserves`).

**Transport:** in-process MCP default (one graph per process). Shared graph: `memnet serve --ipc` (`MEMNET_IPC_SOCKET`) or TCP `memnet serve` (`127.0.0.1:18765`). Multitask / parallel workers need a shared serve — not default in-process.

**Durable:** optional client `memnet-llm[agensgraph]`; cabinet is external and not vendored. **0.7** live hydrate/flush proven (`liveCabinetClaimed`); CI skips unless `MEMNET_AGENSGRAPH_URL` is set.

## Deferred (honest)

- Hosted AgensGraph as a product service (operator runs the server; this repo does not vendor it)
- N-server session pipe ([#47](https://github.com/chouswei/MemNet/issues/47))
- Pin-map export / round-trip (MN-REQ-11.1–11.5 / [#66](https://github.com/chouswei/MemNet/issues/66)) — Path-B ingest domains are shipped (#64); export is separate
- Host search / RAG as a MemNet tool — application nest only ([`docs/grammar/memnet-host-search-nest.md`](docs/grammar/memnet-host-search-nest.md))

## Links

| Doc | Role |
|-----|------|
| [`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) | Agent playbook |
| [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md) | GQL wire SSOT |
| [`docs/ROADMAP-0.5.md`](docs/ROADMAP-0.5.md) | Version map SSOT (0.8 next; 1.0 after 0.8) |
| [`sysml-models/`](sysml-models/) | Requirements / verify |
| [`docs/multi-agent-sessions.md`](docs/multi-agent-sessions.md) | Multitask ops |
| [`docs/README.md`](docs/README.md) | Full docs index |

Layout: [`LAYOUT.md`](LAYOUT.md) · [`AGENTS.md`](AGENTS.md). Novel-writer is out: [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md).

## Licence

MIT
