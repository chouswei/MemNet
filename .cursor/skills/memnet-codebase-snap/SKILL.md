---
name: memnet-codebase-snap
description: >-
  Atomise a source tree into MemNet :MOD / :SYM nodes and typed relations.
  Triggers: codebase snap, memnet index, symbol graph, ingest_codebase,
  MOD SYM snap.
metadata:
  pattern: pipeline
  version: "0.6"
  domain: memnet,codebase
  product: memnet-llm==0.19.0
token_guardrails: |
  - Verify on disk (Grep/Read) before mutate; never invent paths or call edges.
  - Prefer ingest_codebase for locator pins; mutate only confirmed facts.
  - Product write is mutate; leftover add/update / NEW named leftover.
---

# MemNet codebase snap

Pair with [memnet-format](../memnet-format/SKILL.md) and [mcp-memnet](../mcp-memnet/SKILL.md). Wire: `docs/grammar/gql-wire-profile.md`.

**Role:** durable index of files (`:MOD`) and symbols (`:SYM`) plus typed edges (`defines`, `calls`, `includes`, `owns`, …). Not a substitute for grep / LSP.

## Before acting

1. Hub: repo `AGENTS.md`.
2. Single agent: in-process MCP. Shared graph: TCP / HTTP ([memnet-multitask](../memnet-multitask/SKILL.md)).
3. `session_open` with a coding map (bundled `schema.example.txt` or project map).
4. First pass: **`ingest_codebase`** on the tree, then `pin_map` — still **verify on disk** before trusting call/use edges.
5. Copy ids from the map. leftover NEW is leftover.

## Labels

| Label | Props | Notes |
|-------|-------|-------|
| `:MOD` | `path`, `lang`, `recycle` | one per file |
| `:SYM` | `name`, `kind`, `path`, `line`, `sig` | `fn` / `gvar` / `struct` / … |
| `:TSK` | `goal`, `status` | owns the snap |
| Rel | type + short `note` | `defines`, `calls`, `includes`, `owns`, `uses` |

Stable nicknames if used: `MOD_` + path slug; `SYM_` + short slug. Locators (`path`, `line`) are properties, not a PK.

## Workflow

1. `pin_map` on the live `TSK_*` or a root `MOD` (cue `kind` / `path=`). Empty cue = outline.
2. Glob / Grep / Read the files in this batch.
3. **`mutate`** CREATE/SET only facts just verified. Batch 30–80 atoms.
4. Re-`pin_map` to confirm. Add `calls` / `uses` only from a Read of the call site.
5. Incremental: cue the `MOD` for the edited file; SET line/sig; do not duplicate.
6. `housekeep_stats`; settle scratch `TSK_*`.

## MUST NOT

- Invent call edges from memory.
- Teach leftover `--anchor` as the goldfish read.
- Flood one generate with the whole tree — cut batches (or a nested session if over \(M\)).
