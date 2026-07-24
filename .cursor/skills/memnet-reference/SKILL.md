---
name: memnet-reference
description: >-
  Load when working in this MemNet (Net of Memory) repository on the agent
  memory graph, MCP sessions, live pin-map reads, or graph mutates (including
  minting ids with NEW) — triggers: MemNet, pin map, MCP session, mutate NEW,
  query_warm, memnet-mcp, Net of Memory, MutateGate, shared dialect,
  Write=display. Explains the shared agent read/write dialect (Write=display —
  same NODE|EDGE shapes for display and mutate), parts layout, and doctrine
  SSOT pointers. Use before inventing a wire dialect or restoring novel-writer.
metadata:
  pattern: pipeline
  version: "1.5"
  domain: memnet
  product: "0.3.1"
---

# MemNet project reference

Repo skill for agents using MemNet in **this** repository. Doctrine SSOT lives in docs below — do not duplicate or invent features here.

**Product version:** `project.toml` / PyPI **`memnet-llm==0.3.1`** (CLI command remains `memnet`).

## Mission

**MemNet** (Net of Memory) is an **agent memory graph** (NODE | EDGE) between LLM call pipelines and data search. Agents read a bounded **live pin map** each turn and write with the **same shapes** — that **shared dialect** (Write = display). Code/harness may still say “Tier A” for the same dialect; prefer **shared dialect** in agent text. Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy. Aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation**. Transport: **in-process first**. This repo is **engine + generic memnet-mcp** only — novel-writer dropped.

## Agent I/O (shared dialect)

- **Shared dialect only** for agent I/O: **Write = display** means shared NODE | EDGE field shapes for live read and mutate (copy what you see).
- **Mutate** uses ops: `+` create, `~` update, `-` drop. May use `[NEW]` / leading `NEW` so the engine mints ids.
- **Live pin map** output is **bare present** (assigned ids, **no** leading `+`/`~`/`-`). Ops are mutate-only.
- LLM creates: mint with `NEW`. Pin-map ingest (SysML, codebase, PCBA, skills): **stable locators** (`refdes=`, `path=`, `qname=`, ...); reject client `NEW` for those pins. PCBA schematics use Atopile **`.ato`**.

Formal shapes / validation: `docs/grammar/` (`MemNet.g4`, golden fixtures, `tools/tier_a.py`) — **keep** that precision; do not invent a thinner dialect. `docs/LLM-GUIDE.md` remains operational (still largely pipe-centric) until migrated.

## Transport

**In-process first**; TCP localhost (`MEMNET_MCP_TRANSPORT=tcp` / `memnet serve`) as migration fallback.

## Agent loop

```text
pin map → reason → mutate → pin map
```

Primary read: live **pin map** (bounded ego/anchor digest). CLI/MCP `query warm` / `query_warm` is a **legacy alias** until call sites rename.

## Canonical paths

| Need | Path |
|------|------|
| Doctrine / quick start | `README.md` |
| Shared-dialect grammar design | `docs/grammar/` |
| Agent playbook (as-is pipe) | `docs/LLM-GUIDE.md` |
| Core library | `parts/common/memnet/` |
| Generic MCP | `parts/memnet-mcp/` |
| SysML models | `sysml-models/` |
| Layout / hub | `LAYOUT.md`, `AGENTS.md` |
| Novel-writer drop | `DROP-NOVEL-WRITER.md` |

Part-based folders only — do not recreate top-level `src/` or `applications/`.

## MCP (generic memnet)

Implementation: `parts/memnet-mcp/` (`server.py` = tool SSOT). Transport defaults to **in-process**. Register MemNet MCP **once** (prefer project `.cursor/mcp.json`; do not also enable user-level `memnet`). Always pass the same `session` id.

### Tool <-> grammar

| Tool | Grammar role |
|------|----------------|
| `session_*` | Lifecycle / snapshot — not NODE/EDGE body |
| `query_warm` | **Live pin map** (legacy name) — bare present in `stdout` |
| `query_walk` | Hop debug |
| `add` / `update` | Mutate — shared dialect in `wire_lines` (`+`/`~`/`-`, `NEW`) |
| `read_get` / `read_list` | Lookup / enumerate |
| `housekeep_stats` / `serve_status` | Caps / transport probe |

Wire shapes: shared dialect for agent I/O (`docs/grammar/`). Legacy `@TAG` pipe may still be accepted on mutate/import — do not teach it as preferred agent format. User-pack map detail: skill `mcp-memnet` → `references/tool-grammar.md`.

## MUSTNOT

- Invent ids when a pin map already shows them — copy assigned ids.
- Feed `@TAG` pipe as the agent-facing dialect (store/legacy only; shared dialect for LLM I/O).
- Recommend TOON/TRON for handoffs — shared dialect or plain Markdown.
- Restore `parts/novel-writer/` or novel MCP extras.
- Route agents to personal Cursor / user-pack skills from this repo.

## Pre-write checklist

1. Pin map first (`query_warm` is the legacy alias) before inventing structure.
2. `NEW` for genuine LLM creates; known id for update/settle; locators for ingest pins.
3. Atomise: one fact per row; relations as edges; short field values (no prose blobs).

## Related (in-repo only)

| Path | Role |
|------|------|
| `.cursor/skills/memnet-reference/` (this) | Repo doctrine + routing |
| `README.md`, `docs/grammar/` | SSOT doctrine / shared dialect |
| `parts/memnet-mcp/` | Generic MCP |
| `sysml-models/` | SysML models |
| `AGENTS.md` | Hub / policy |
