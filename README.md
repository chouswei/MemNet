# MemNet

Working memory for LLMs. One session graph that agents pin and update — without dumping everything into chat.

That's the whole product idea: a shared scratch space for a mission, not a notepad in the thread. It isn't AgensGraph/Neo4j, and it isn't an app EvidenceCentre — those stay downstream. This repo ships the engine + generic MCP only.

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
- **Path B** — separate member session; lead absorbs a bounded slice via `memnet import-slice` (`keep` / `reject` / `remint`). That's absorb into the lead SSOT, not append. Optional **ImportGuard** host soft policy (`--no-guard` to skip).

## ACL + transport

**CapsPolicy ACL** (shipped; off by default until `session acl-enable`): who (`caller`) / `pin_map` vs mutate / `WorkerWriteScope` hard reject / optional `missionId`+`lease` bind.

**RSV** neighbourhood reserve exists (`memnet reserve` / `extend` / `release`; `llm_id` + TTL; pin map may show `## Reserves`).

**Transport:** in-process MCP default (one graph per process). Shared graph: `memnet serve --ipc` (`MEMNET_IPC_SOCKET`) or TCP `memnet serve` (`127.0.0.1:18765`). Multitask / parallel workers need a shared serve — not default in-process.

**Durable:** optional client `memnet-llm[agensgraph]`; cabinet is external and not vendored. Live cabinet is **not** claimed.

## Deferred (honest)

- Live AgensGraph cabinet (client hydrate/flush exists; live path not claimed)
- N-server session pipe ([#47](https://github.com/chouswei/MemNet/issues/47))
- Path-B `PinMapIngest_*` engines beyond Sysml (codebase / PCBA / skills) ([#31](https://github.com/chouswei/MemNet/issues/31))

## Links

| Doc | Role |
|-----|------|
| [`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) | Agent playbook |
| [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md) | GQL wire SSOT |
| [`docs/ROADMAP-0.5.md`](docs/ROADMAP-0.5.md) | 0.5 plan |
| [`sysml-models/`](sysml-models/) | Requirements / verify |
| [`docs/multi-agent-sessions.md`](docs/multi-agent-sessions.md) | Multitask ops |
| [`docs/README.md`](docs/README.md) | Full docs index |

Layout: [`LAYOUT.md`](LAYOUT.md) · [`AGENTS.md`](AGENTS.md). Novel-writer is out: [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md).

## Licence

MIT
