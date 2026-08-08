# MemNet

**MemNet** (Net of Memory) is an in-memory **NODE | EDGE** graph that sits between pipelines of LLM calls and data search. It is working memory for agents — not a chat notepad and not the search corpus.

Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy when presenting facts. It aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation** development.

Version: see `project.toml` / package `memnet-llm` (CLI command remains `memnet`). Python ≥ 3.11.

---

## Doctrine (target)

| Idea | Meaning |
|------|---------|
| NODE \| EDGE only | Conceptual kinds are nodes and edges; tags realise node kinds |
| One agent dialect | **Shared dialect** (Write = display) — same shapes for live read and mutate; design docs may still say “Tier A” |
| Live **pin map** | Bounded ego/anchor digest for the turn (not a session dump) |
| `NEW` vs locators | LLM creates use mint token `NEW`; pin-map ingest uses **stable locators** (no client `NEW` for source pins). PCBA schematics use Atopile **`.ato`** |
| Transport | **In-process first** (MCP stdio default); CLI + TCP `memnet serve` as shared-process fallback; opt-in streamable-http for remote |
| Persistence | Optional snapshots (`session save` / `session load`); sessions are RAM + TTL |

**Primary term:** pin map. MCP tool `pin_map` / CLI `query pin-map`. Legacy aliases: `query_warm` / `query warm`.

---

## Agent I/O (shared dialect)

Target surface (not `@TAG` pipe). Shared NODE | EDGE field shapes (**Write = display**). **Mutate** uses ops (`+` create, `~` update, `-` drop). **Live pin map** emits bare present lines — no leading ops (ops are mutate-only; a pin-map `+` would look like “please add”).

**Mutate input** (LLM → MemNet) — may use `[NEW]`; engine mints ids:

```text
## Nodes
+ CLM [NEW] ; type=decision ; code=bitrate cap 2000 bps ; recycle=persistent
+ TSK [T42] ; goal=Clear warehouse ; status=in_progress ; recycle=persistent

## Edges
+ E77 [N03] --(helps)--> [T42] ; note=labour ; recycle=persistent
```

**Live pin map output** (MemNet → LLM) — assigned ids, no `NEW`; copyable for the next mutate:

```text
## Nodes
CLM [C12] ; type=decision ; code=bitrate cap 2000 bps ; recycle=persistent
TSK [T42] ; goal=Clear warehouse ; phase=2 ; status=in_progress ; recycle=persistent
NPC [N03] ; role=helper ; status=active ; recycle=persistent

## Edges
E77 [N03] --(helps)--> [T42] ; note=labour ; recycle=persistent
```

- **Create:** `[NEW]` / leading `NEW` — engine allocates ids; copy them afterwards.
- **Update / settle:** known ids only; `NEW` illegal on patch.
- **Pin-map ingest** (SysML, codebase, PCBA `.ato`, skills): deterministic ids from locators (`refdes=`, `path=`, `qname=`, …); reject client `NEW` for those pins.

Design and examples: [`docs/grammar/memnet-grammar-design.md`](docs/grammar/memnet-grammar-design.md), [`docs/grammar/examples/`](docs/grammar/examples/). SysML notes: [`sysml-models/outputs/system-design-notes.md`](sysml-models/outputs/system-design-notes.md).

---

## Current vs target (honest)

| Area | Today (as-is) | Target |
|------|---------------|--------|
| Agent wire | Mutate + live pin map prefer **shared dialect**; legacy `@TAG` pipe still accepted on add/update and used in snapshots / `read` | Shared shapes; pin map bare present; mutate keeps ops |
| Shared-dialect codec | Pure-Python codec in `memnet/tier_a.py` + golden tests | SSOT parse/emit; ANTLR optional later |
| Id mint | `IdAllocator` wired through `MutateGate` on shared-dialect batches | Same |
| MutateGate | `mutate_gate.py` — shared-dialect parse → mint → commit; pipe import-once | Same dialect only |
| Live pin map | `PinMapComposer` via `pin_map` / `query pin-map` (shared-dialect emit) | Done |
| Transport | MCP **in-process** by default; `MEMNET_MCP_TRANSPORT=tcp` for serve; opt-in HTTP `:18766` | In-process primary; TCP fallback; remote streamable-http |
| MCP | Generic tools; in-process engine | Same |
| Novel-writer | **Removed** — see [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md) | Stay out of this repo |

[`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) is the agent playbook (**0.4.x shared dialect first**; legacy `@TAG` pipe in appendix).

---

## Transport

| Mode | Entry | Graph store | Typical use |
|------|-------|-------------|-------------|
| **MCP in-process** (primary) | `memnet-mcp` stdio in Cursor | In-process engine in the MCP host | Local agents; no `memnet serve` required |
| **CLI + `memnet serve`** | `memnet` CLI → TCP `:18765` | Shared serve process | Scripts, multi-client, migration from pre-0.4 |
| **MCP streamable-http** (opt-in) | `memnet-mcp --transport streamable-http` → `:18766/mcp` | Shared remote process | Remote Cursor `url` clients; bearer token optional |

Set `MEMNET_MCP_TRANSPORT=tcp` when MCP tools must call a running serve instead of the in-process graph. Multitask / parallel workers sharing one graph need TCP or HTTP — default in-process isolates per process. See [`docs/multi-agent-sessions.md`](docs/multi-agent-sessions.md).

---

## Layout

Part-based tree ([`LAYOUT.md`](LAYOUT.md), [`AGENTS.md`](AGENTS.md)):

| Path | Role |
|------|------|
| `parts/common/memnet/` | Core library + CLI (`memnet`) |
| `parts/memnet-mcp/` | Generic MCP server (`memnet-mcp`) |
| `docs/` | LLM-GUIDE, grammar, application notes |
| `sysml-models/` | Requirements and deploy/behaviour models |
| `tests/` | Engine, MCP, shared-dialect golden tests |

Do not recreate top-level `src/` or `applications/`. Do not restore `parts/novel-writer/`.

---

## Installation

```powershell
pip install memnet-llm
# or from source:
pip install -e ".[dev]"
# optional MCP:
pip install memnet-llm[mcp]
```

PyPI name is **`memnet-llm`** (`memnet` on PyPI is a different project).

---

## Quick start (MCP in-process — primary)

```powershell
pip install memnet-llm[mcp]
```

Register `memnet-mcp` in `.cursor/mcp.json` (see `parts/memnet-mcp/README.md`). Open a session via MCP `session_open`, then `pin_map(anchor=…)` / `add` / `update` — shared dialect, no separate serve terminal.

## Quick start (CLI + serve — fallback)

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

**Serve safety:** default bind is **localhost only** (`127.0.0.1:18765`). Non-loopback bind requires `MEMNET_SERVE_ALLOW_REMOTE=1`. No session token or ACL on TCP yet — remote bind is LAN-trust exposure. Frame cap default 4 MiB (`MEMNET_SERVE_MAX_FRAME_BYTES`). See `docs/grammar/memnet-security-multi-agent.md`.

**MCP:** local Cursor uses stdio `memnet-mcp` (in-process graph by default). Opt-in remote: `memnet-mcp --transport streamable-http` on **`:18766/mcp`**. LAN bind needs `MEMNET_MCP_ALLOW_REMOTE=1`; set `MEMNET_MCP_HTTP_TOKEN` for bearer auth; for `0.0.0.0` set `MEMNET_MCP_HTTP_TRUSTED_HOSTS`. TCP `memnet serve` remains **`:18765`**. Tools: `serve_status`, `session_open`, `session_current`, `session_load`, `session_save`, `pin_map` (`query_warm` alias), `query_walk`, `add`, `update`, `read_get`, `housekeep_stats`. See `parts/memnet-mcp/README.md`.

Forward reading order for agents:

1. [`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) — goldfish loop, shared dialect, MCP primary  
2. [`docs/grammar/memnet-grammar-design.md`](docs/grammar/memnet-grammar-design.md) — Write = display, pin map, `NEW` vs locators  
3. [`docs/multi-agent-sessions.md`](docs/multi-agent-sessions.md) — single-writer / Multitask guidance (as-is); links **MN-REQ-12** verify trail  
4. [`docs/application-notes/llm-system-dev-multitask.md`](docs/application-notes/llm-system-dev-multitask.md) — Multitask pattern for downstream `modelbasedPrj-*` repos  
5. [`docs/grammar/memnet-multi-layer.md`](docs/grammar/memnet-multi-layer.md) — stratified pin maps (design)  
6. [`sysml-models/outputs/system-design-notes.md`](sysml-models/outputs/system-design-notes.md) — target part tree and gaps  
7. [`sysml-models/outputs/multitask-case-study.md`](sysml-models/outputs/multitask-case-study.md) — MN-REQ-12 worked scenario (MN-VER-12-G00, S01…S09)

---

## What was removed

Novel-writer (`parts/novel-writer/`, novel MCP extras, novel application notes) is **out of scope**. This repository hosts the graph engine and generic memnet-mcp only. Record: [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md).

---

## Licence

MIT
