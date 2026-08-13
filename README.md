# MemNet

Working memory for LLMs. One session graph that agents pin and update — without dumping everything into chat.

That's the whole product idea: a shared scratch space for a mission, not a notepad in the thread. It isn't AgensGraph/Neo4j, and it isn't an app EvidenceCentre — those stay downstream. This repo ships the engine + generic MCP only.

Package **`memnet-llm`** (CLI **`memnet`**). Python ≥ 3.11.

## Install + quick CLI

<<<<<<< HEAD
```bash
=======
---

## Doctrine (today)

| Idea | Meaning |
|------|---------|
| Shared LLM memory | Session-scoped NODE \| EDGE working set; goldfish re-read each turn |
| One agent dialect | **GQL (openCypher-shaped)** only — shaped `pin_map` + gated mutate (`id:'NEW'`) ([`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md)). Layer / Tier A retired |
| Live **pin map** | Bounded ego/anchor shaped subgraph for the turn (not a session dump; not raw `RETURN` tables) |
| **Session id** = SSOT handle | Inter-module pipe: module A → B passes `sessionId`; B `pin_map`s. Chat / HTTP / MissionDock never carry the graph. Treat session id as a **secret capability** |
| Distinct sessions | Keep mission/working memory separate from other stores (e.g. company Role D `companySessionId`) — do not mash ids |
| CapsPolicy **ACL** (shipped) | Who (`caller`) / TRAVERSE≈`pin_map` vs WRITE≈mutate / `WorkerWriteScope` hard reject / optional `missionId`+`lease` bind. Analogy to Neo4j privileges only — no Bolt teach |
| `NEW` vs locators | LLM creates use mint token `NEW`; pin-map ingest uses **stable locators** (no client `NEW` for source pins) |
| Transport | Local single-agent: in-process stdio OK. **Remote / Multitask:** TCP serve or streamable-http (`memnet-pi`) — not default in-process |
| Durable (optional) | Client hydrate/flush behind MemNet (`memnet-llm[agensgraph]`); cabinet is **external** (not vendored). Live AgensGraph **not** claimed |
| Snapshots | Optional `session save` / `session load`; live sessions are RAM + TTL |

**Primary term:** pin map. MCP tool `pin_map` / CLI `query pin-map`. Legacy aliases: `query_warm` / `query warm`.

**Sequence:** M1 / M2 / M3-docs **done**; M2.5 client hydrate/flush **landed**; live cabinet **deferred**. Detail: [`docs/ROADMAP-0.5.md`](docs/ROADMAP-0.5.md).

---

## Agent I/O (GQL wire)

**Teach:** openCypher-shaped **GQL** only — SSOT [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md). Primary read = shaped subgraph via **`pin_map`** (anchor / depth / view). Mutate = gated `CREATE` / `MERGE` / `SET` / `DELETE` patterns; mint with `id: 'NEW'`.

Illustrative shaped read / mutate family:

```cypher
(:TSK {id:'TSK_42', goal:'Clear warehouse', status:'in_progress'})
(:NPC {id:'NPC_03', role:'helper'})-[:helps {id:'E_77'}]->(:TSK {id:'TSK_42'})
```

```cypher
CREATE (t:TSK {id:'NEW', goal:'Clear warehouse', status:'in_progress'})
```

- **Create:** `id: 'NEW'` — engine allocates; copy from next `pin_map` / response.
- **Update / settle:** known ids only; `NEW` illegal on patch.
- **Pin-map ingest** (SysML, codebase, PCBA `.ato`, skills): deterministic ids from locators; reject client `NEW` for those pins.
- **Handoff:** pass `sessionId` (+ `caller` / optional bind / write scope); peer re-`pin_map` — never dump the graph into chat.

**M2 shipped:** engine/MCP accept openCypher-shaped GQL and emit shaped `pin_map`. Layer / Tier A are retired from product accept. SysML: [`sysml-models/outputs/system-design-notes.md`](sysml-models/outputs/system-design-notes.md).

---

## Current vs target (honest)

| Area | Today (as-is) | Target / deferred |
|------|---------------|-------------------|
| Agent wire | **GQL** accept (M2) + docs teach GQL | profile [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md) |
| Codec | `GqlCodec` / `PinMapShapedRead` on product path | Tier A / Layer retired from accept |
| Id mint | `IdAllocator` via `MutateGate` on GQL batches | Same |
| MutateGate | gated GQL parse → mint → commit | GQL only |
| Live pin map | `PinMapComposer` shaped emit via `pin_map` | Done |
| CapsPolicy ACL | **Shipped** (`acl.py`): who / `pin_map` vs mutate / `WorkerWriteScope` hard reject / optional bind; off by default; session id = capability | Full private/shared/open `session_token` modes remain deferred |
| Session pipe | Handoff = `sessionId`; Multitask docs teach A→B pipe | Same |
| Durable store | M2.5 **client** hydrate/flush landed (`memnet-llm[agensgraph]`); Fake always-on; live AgensGraph not claimed | Prove external cabinet; one sync owner |
| Transport | MCP **in-process** by default; `MEMNET_MCP_TRANSPORT=tcp` for serve; opt-in HTTP `:18766` | One remote entry (`memnet-pi`); HTTP bridged to serve |
| MCP | Generic tools; in-process engine | Same |
| Novel-writer | **Removed** — [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md) | Stay out of this repo |
| App patterns | EvidenceCentre / MissionDock / CompanyMemory = **application** (not this repo) | Stay downstream |

[`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) is the agent playbook (**dialect teach = GQL** + shaped `pin_map` + gated mutate). ACL grain: [`sysml-models/outputs/system-design-notes.md`](sysml-models/outputs/system-design-notes.md).

---

## How to run (one path)

**Remote / shared graph (default teach):** Cursor MCP **`memnet-pi`** via `"url"` → Pi streamable-http `:18766/mcp` (token + trusted Host). On the Pi, HTTP MCP **MUST** bridge to one `memnet serve` (TCP `:18765`) — **one graph owner**, never two writers. See [`.cursor/mcp.json.example`](.cursor/mcp.json.example) and [`parts/memnet-mcp/README.md`](parts/memnet-mcp/README.md).

**Local stdio (`memnet-local`):** optional / **dev-only** — omit or disable by default; not the Multitask path.

**Dialect teach:** **GQL only** — [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md). Detail: [`docs/ROADMAP-0.5.md`](docs/ROADMAP-0.5.md).

## Transport (as-is 0.4.x)

| Mode | Entry | Graph store | Typical use |
|------|-------|-------------|-------------|
| **MCP in-process** | `memnet-mcp` stdio | In-process engine in the MCP host | Local single-agent; no serve |
| **CLI + `memnet serve`** | `memnet` CLI → TCP `:18765` or AF_UNIX (`MEMNET_IPC_SOCKET`, `--ipc`) | Shared serve process | Scripts, multi-client |
| **MCP streamable-http** | `memnet-mcp --transport streamable-http` → `:18766/mcp` | Own process today (bridge to serve = **0.5.0**) | Remote Cursor `url` (`memnet-pi`) |

Set `MEMNET_MCP_TRANSPORT=tcp` when MCP tools must call a running serve instead of a separate in-process graph. Multitask / parallel workers sharing one graph need TCP or HTTP — default in-process isolates per process. See [`docs/multi-agent-sessions.md`](docs/multi-agent-sessions.md).

## Known gaps → 0.5.0

Plan: [`docs/ROADMAP-0.5.md`](docs/ROADMAP-0.5.md).

1. **One remote entry** — teach `memnet-pi` HTTP; demote project `memnet-local`.
2. **One dialect teach** — GQL only (**done**: M1 profile + M2 engine + M3 playbooks).
3. **One graph owner on Pi** — HTTP MCP bridged to `memnet serve`; never two writers.
4. **Footguns** — Host / token / `view=` defaults so Cursor just works.
5. **M2.5 durable** — client hydrate/flush landed; live external AgensGraph cabinet deferred (not claimed).

Deferred elsewhere: full ACL `session_token` modes, Path-B ingest domains beyond Sysml (codebase / PCBA / skills), first-class `PORT` NODE — grammar Open + MN-REQ-12 backlog. **CapsPolicy ACL who/scope/bind is as-is** (PR #44). **NeighbourhoodReserve** and **PinMapIngest_Sysml** are as-is.

---

## Layout

Part-based tree ([`LAYOUT.md`](LAYOUT.md), [`AGENTS.md`](AGENTS.md)):

| Path | Role |
|------|------|
| `parts/common/memnet/` | Core library + CLI (`memnet`) |
| `parts/memnet-mcp/` | Generic MCP server (`memnet-mcp`) |
| `docs/` | Docs index [`docs/README.md`](docs/README.md): developers + applications |
| `sysml-models/` | Requirements and deploy/behaviour models |
| `tests/` | Engine, MCP, GQL / archive golden tests |

Do not recreate top-level `src/` or `applications/`. Do not restore `parts/novel-writer/`.

---

## Installation

```powershell
>>>>>>> 0eba810 (Ship Path-B PinMapIngest_Sysml (#31))
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
- Path-B `PinMapIngest_*` engines ([#31](https://github.com/chouswei/MemNet/issues/31))

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
