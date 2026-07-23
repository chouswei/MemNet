# MemNet

**MemNet** (Net of Memory) is an in-memory **NODE | EDGE** graph that sits between pipelines of LLM calls and data search. It is working memory for agents — not a chat notepad and not the search corpus.

Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy when presenting facts. It aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation** development.

Version: see `project.toml` / package `memnet-llm` (CLI command remains `memnet`). Python ≥ 3.11.

---

## Doctrine (target)

| Idea | Meaning |
|------|---------|
| NODE \| EDGE only | Conceptual kinds are nodes and edges; tags realise node kinds |
| One agent dialect | **Tier A** Write = display — same shapes for live read and mutate |
| Live **pin map** | Bounded ego/anchor digest for the turn (not a session dump) |
| `NEW` vs locators | LLM creates use mint token `NEW`; pin-map ingest uses **stable locators** (no client `NEW` for source pins). PCBA schematics use Atopile **`.ato`** |
| Transport | **In-process first**; local IPC next; TCP localhost as migration fallback |
| Persistence | Optional snapshots (`session save` / `session load`); sessions are RAM + TTL |

**Primary term:** pin map. CLI/MCP `query warm` / `query_warm` is a **legacy alias** until call sites rename.

---

## Agent I/O (Tier A)

Target surface (not `@TAG` pipe). **Write = display** — same Tier A grammar both ways.

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
+ CLM [C12] ; type=decision ; code=bitrate cap 2000 bps ; recycle=persistent
+ TSK [T42] ; goal=Clear warehouse ; phase=2 ; status=in_progress ; recycle=persistent
+ NPC [N03] ; role=helper ; status=active ; recycle=persistent

## Edges
+ E77 [N03] --(helps)--> [T42] ; note=labour ; recycle=persistent
```

- **Create:** `[NEW]` / leading `NEW` — engine allocates ids; copy them afterwards.
- **Update / settle:** known ids only; `NEW` illegal on patch.
- **Pin-map ingest** (SysML, codebase, PCBA `.ato`, skills): deterministic ids from locators (`refdes=`, `path=`, `qname=`, …); reject client `NEW` for those pins.

Design and examples: [`docs/grammar/memnet-grammar-design.md`](docs/grammar/memnet-grammar-design.md), [`docs/grammar/examples/`](docs/grammar/examples/). SysML notes: [`sysml-models/outputs/system-design-notes.md`](sysml-models/outputs/system-design-notes.md).

---

## Current vs target (honest)

| Area | Today (as-is) | Target |
|------|---------------|--------|
| Agent wire | Mutate + live pin map prefer **Tier A**; legacy `@TAG` pipe still accepted on add/update and used in snapshots / `read` | Tier A Write=display both ways everywhere agent-facing |
| Tier A | Pure-Python codec in `memnet/tier_a.py` + golden tests | SSOT parse/emit; ANTLR optional later |
| Id mint | `IdAllocator` wired through `MutateGate` on Tier A batches | Same |
| MutateGate | `mutate_gate.py` — Tier A parse → mint → commit; pipe import-once | Same dialect only |
| Live pin map | `PinMapComposer` via `query warm` / `query_warm` (Tier A emit) | Rename alias when call sites ready |
| Transport | MCP **in-process** by default; `MEMNET_MCP_TRANSPORT=tcp` for serve | In-process primary; local IPC; TCP fallback |
| MCP | Generic tools; in-process engine | Same |
| Novel-writer | **Removed** — see [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md) | Stay out of this repo |

[`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) is still largely **pipe-centric** (goldfish loop, `query warm`). Prefer the grammar design + SysML notes for the forward dialect; treat the GUIDE as operational until it is migrated.

---

## Layout

Part-based tree ([`LAYOUT.md`](LAYOUT.md), [`AGENTS.md`](AGENTS.md)):

| Path | Role |
|------|------|
| `parts/common/memnet/` | Core library + CLI (`memnet`) |
| `parts/memnet-mcp/` | Generic MCP server (`memnet-mcp`) |
| `docs/` | LLM-GUIDE, grammar, application notes |
| `sysml-models/` | Requirements and deploy/behaviour models |
| `tests/` | Engine, MCP, Tier A golden tests |

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

## Quick start (as-is CLI)

Until Tier A is the store boundary, the running path is still pipe + serve.

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
memnet query warm --anchor PLR01      # live pin map (legacy name)

memnet session close $env:MEMNET_SESSION
```

Without `memnet serve`, stateful commands fail with `@ERR: serve_required` (unless `MEMNET_TEST_INLINE=1` for tests/scripts).

**MCP (as-is):** run `memnet serve`, then `memnet-mcp`. Tools include `serve_status`, `session_open`, `session_current`, `session_load`, `session_save`, `query_warm`, `query_walk`, `add`, `update`, `read_get`, `housekeep_stats`. Envelope is JSON; memory payload is still pipe lines today.

Forward reading order for agents:

1. [`docs/grammar/memnet-grammar-design.md`](docs/grammar/memnet-grammar-design.md) — Tier A, pin map, `NEW` vs locators  
2. [`sysml-models/outputs/system-design-notes.md`](sysml-models/outputs/system-design-notes.md) — target part tree and gaps  
3. [`docs/LLM-GUIDE.md`](docs/LLM-GUIDE.md) — current goldfish loop (pipe; migration pending)

---

## What was removed

Novel-writer (`parts/novel-writer/`, novel MCP extras, novel application notes) is **out of scope**. This repository hosts the graph engine and generic memnet-mcp only. Record: [`DROP-NOVEL-WRITER.md`](DROP-NOVEL-WRITER.md).

---

## Licence

MIT
