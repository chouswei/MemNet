# MemNet

**MemNet** (Net of Memory) is **shared working memory for LLMs**: a session-scoped **NODE | EDGE** buffer between LLM call pipelines and data search. It is not a chat notepad, not the search corpus, and **not** a Cypher proxy to AgensGraph / Neo4j.

Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy when presenting facts. It aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation** development.

This repo ships the **engine** + **generic memnet-mcp** only. Application patterns such as EvidenceCentre, MissionDock, and CompanyMemory live in downstream products (e.g. ai-investor) — they are not MemNet parts.

Version: see `project.toml` / package `memnet-llm` (CLI command remains `memnet`). Python ≥ 3.11.

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
| **CLI + `memnet serve`** | `memnet` CLI → TCP `:18765` | Shared serve process | Scripts, multi-client |
| **MCP streamable-http** | `memnet-mcp --transport streamable-http` → `:18766/mcp` | Own process today (bridge to serve = **0.5.0**) | Remote Cursor `url` (`memnet-pi`) |

Set `MEMNET_MCP_TRANSPORT=tcp` when MCP tools must call a running serve instead of a separate in-process graph. Multitask / parallel workers sharing one graph need TCP or HTTP — default in-process isolates per process. See [`docs/multi-agent-sessions.md`](docs/multi-agent-sessions.md).

## Known gaps → 0.5.0

Plan: [`docs/ROADMAP-0.5.md`](docs/ROADMAP-0.5.md).

1. **One remote entry** — teach `memnet-pi` HTTP; demote project `memnet-local`.
2. **One dialect teach** — GQL only (**done**: M1 profile + M2 engine + M3 playbooks).
3. **One graph owner on Pi** — HTTP MCP bridged to `memnet serve`; never two writers.
4. **Footguns** — Host / token / `view=` defaults so Cursor just works.
5. **M2.5 durable** — client hydrate/flush landed; live external AgensGraph cabinet deferred (not claimed).

Deferred elsewhere: neighbourhood reserve, full ACL `session_token` modes, Path-B ingest, first-class `PORT` NODE — grammar Open + MN-REQ-12 backlog. **CapsPolicy ACL who/scope/bind is as-is** (PR #44), not target-only.

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
pip install memnet-llm
# or from source:
pip install -e ".[dev]"
# optional MCP:
pip install memnet-llm[mcp]
# optional durable client (psycopg only — not an AgensGraph server):
pip install memnet-llm[agensgraph]
```

PyPI name is **`memnet-llm`** (`memnet` on PyPI is a different project). The AgensGraph cabinet is external and not vendored; live path is not claimed.

---

## Quick start (remote `memnet-pi` — default teach)

On the Pi: run streamable-http MCP bridged to one `memnet serve` (0.5.0 target; today set `MEMNET_MCP_TRANSPORT=tcp` when serve is up). Cursor: copy [`.cursor/mcp.json.example`](.cursor/mcp.json.example) (`memnet-pi` `"url"` + bearer). Then `session_open` → `pin_map` → `add` / `update`. Full env paste: [`parts/memnet-mcp/README.md`](parts/memnet-mcp/README.md). Plan: [`docs/ROADMAP-0.5.md`](docs/ROADMAP-0.5.md).

## Quick start (MCP in-process — local / optional)

```powershell
pip install memnet-llm[mcp]
```

Register stdio `memnet-mcp` only for **dev-only** local graphs (not default remote; omit `memnet-local` when using Pi). See `parts/memnet-mcp/README.md`. Open a session via MCP `session_open`, then `pin_map(anchor=…)` / `add` / `update` — **GQL** wire.

## Quick start (CLI + serve)

For shell scripts or a shared TCP graph:

**Terminal 1:**

```powershell
memnet serve
# MEMNET_SERVE=127.0.0.1:18765
```

**Terminal 2:**

```powershell
memnet session open --map-file parts/common/memnet/memnet/examples/schema.example.txt
$env:MEMNET_SESSION = "mn_xxxxxxxx"   # from stderr

memnet add --file parts/common/memnet/memnet/examples/workflow.example.txt
memnet query pin-map --anchor PLR01   # live pin map (bare present; query warm is legacy)

memnet session close $env:MEMNET_SESSION
```

Without `memnet serve`, the **CLI** fails with `@ERR: serve_required` (unless `MEMNET_TEST_INLINE=1` for tests/scripts). **MCP in-process** does not need serve.

**Serve safety:** default bind is **localhost only** (`127.0.0.1:18765`). Non-loopback bind requires `MEMNET_SERVE_ALLOW_REMOTE=1`. CapsPolicy ACL (who / pin_map vs mutate / scope / bind) is available when enabled on the session; full `session_token` modes remain deferred — remote bind is still largely LAN-trust exposure. Frame cap default 4 MiB (`MEMNET_SERVE_MAX_FRAME_BYTES`). See `docs/grammar/memnet-security-multi-agent.md` and `sysml-models/outputs/system-design-notes.md`.

**MCP:** local Cursor uses stdio `memnet-mcp` (in-process graph by default). Opt-in remote: `memnet-mcp --transport streamable-http` on **`:18766/mcp`**. LAN bind needs `MEMNET_MCP_ALLOW_REMOTE=1`; set `MEMNET_MCP_HTTP_TOKEN` for bearer auth; for `0.0.0.0` set `MEMNET_MCP_HTTP_TRUSTED_HOSTS`. TCP `memnet serve` remains **`:18765`**. Tools: `serve_status`, `session_open`, `session_current`, `session_load`, `session_save`, `pin_map` (`query_warm` alias), `query_walk`, `add`, `update`, `read_get`, `housekeep_stats`. See `parts/memnet-mcp/README.md`.

Forward reading order for agents (full index: [`docs/README.md`](docs/README.md)):

1. [`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) — goldfish loop, GQL wire, MCP primary **(developers)**  
2. [`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md) — GQL wire SSOT, shaped `pin_map`, `NEW` vs locators **(developers)**  
3. [`docs/multi-agent-sessions.md`](docs/multi-agent-sessions.md) — Multitask operating doctrine; session-id handoff; **MN-REQ-12** verify trail **(developers)**  
4. [`docs/application-notes/llm-system-dev-multitask.md`](docs/application-notes/llm-system-dev-multitask.md) — Multitask pattern for downstream `modelbasedPrj-*` repos **(applications)**  
5. [`docs/application-notes/examples/inverting-amplifier-gql-case-study.md`](docs/application-notes/examples/inverting-amplifier-gql-case-study.md) — worked GQL case study **(applications)**  
6. [`sysml-models/outputs/system-design-notes.md`](sysml-models/outputs/system-design-notes.md) — target part tree and gaps  
7. [`sysml-models/outputs/multitask-case-study.md`](sysml-models/outputs/multitask-case-study.md) — MN-REQ-12 worked scenario (MN-VER-12-G00, S01…S09)

---

## What was removed

Novel-writer (`parts/novel-writer/`, novel MCP extras, novel application notes) is **out of scope**. This repository hosts the graph engine and generic memnet-mcp only. Record: [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md).

---

## Licence

MIT
