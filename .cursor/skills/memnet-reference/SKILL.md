---
name: memnet-reference
description: >-
  Load when working in this MemNet (Net of Memory) repository on the agent
  memory graph, MCP sessions, live pin-map reads, or graph mutates (including
  minting ids with NEW) — triggers: MemNet, pin map, MCP session, mutate NEW,
  query_warm, memnet-mcp, Net of Memory, MutateGate, Tier A. Explains the shared
  agent read/write dialect (Tier A: Write=display — same NODE|EDGE shapes for
  display and mutate), parts layout, and doctrine SSOT pointers. Use before
  inventing a wire dialect or restoring novel-writer.
metadata:
  pattern: pipeline
  version: "1.1"
  domain: memnet
---

# MemNet project reference

Repo skill for agents using MemNet in **this** repository. Doctrine SSOT lives in docs below — do not duplicate or invent features here.

## Mission

**MemNet** (Net of Memory) is an **agent memory graph** (NODE | EDGE) between LLM call pipelines and data search. Agents read a bounded **live pin map** each turn and write with the **same shapes** — that shared dialect is **Tier A** (**Write = display**). Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy. Aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation**. Transport: **in-process first**. This repo is **engine + generic memnet-mcp** only — novel-writer dropped.

## Agent I/O (Tier A)

- **Tier A only** for agent dialect: **Write = display** means shared NODE | EDGE field shapes for live read and mutate (copy what you see).
- **Mutate** uses ops: `+` create, `~` update, `-` drop. May use `[NEW]` / leading `NEW` so the engine mints ids.
- **Live pin map** output is **bare present** (assigned ids, **no** leading `+`/`~`/`-`). Ops are mutate-only.
- LLM creates: mint with `NEW`. Pin-map ingest (SysML, codebase, PCBA, skills): **stable locators** (`refdes=`, `path=`, `qname=`, …); reject client `NEW` for those pins. PCBA schematics use Atopile **`.ato`**.

Forward dialect: `README.md` + `docs/grammar/`. `docs/LLM-GUIDE.md` remains operational (still largely pipe-centric) until migrated.

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
| Tier A grammar design | `docs/grammar/` |
| Agent playbook (as-is pipe) | `docs/LLM-GUIDE.md` |
| Core library | `parts/common/memnet/` |
| Generic MCP | `parts/memnet-mcp/` |
| SysML models | `sysml-models/` |
| Layout / hub | `LAYOUT.md`, `AGENTS.md` |
| Novel-writer drop | `DROP-NOVEL-WRITER.md` |

Part-based folders only — do not recreate top-level `src/` or `applications/`.

## MCP (generic memnet)

Implementation: `parts/memnet-mcp/`. Typical tools: `session_*` (open/save/load/…), `query_warm` (pin-map alias), `add` / `update` via **MutateGate** (Tier A preferred; legacy `@TAG` pipe still accepted on mutate). Always pass the same `session` id.

Wire shapes and grammar: `README.md` + `docs/grammar/` (not personal Cursor skills).

## MUSTNOT

- Invent ids when a pin map already shows them — copy assigned ids.
- Feed `@TAG` pipe as the agent-facing dialect (store/legacy only; Tier A for LLM I/O).
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
| `README.md`, `docs/grammar/` | SSOT doctrine / Tier A |
| `parts/memnet-mcp/` | Generic MCP |
| `sysml-models/` | SysML models |
| `AGENTS.md` | Hub / policy |
