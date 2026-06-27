# MemNet

**Pure in-memory working-memory graph for LLM "goldfish brains"** — structured state an agent writes once and re-reads each turn because the model forgets.

MemNet is **scratch memory for the current task**, not a durable knowledge base or vector store. Sessions live in RAM, expire by TTL, and disappear on `session close`. There is **no automatic disk state**; persistence is explicit and user-controlled via `session save` / `session load`.

## The problem it solves

LLMs lose track of entities, state, and rules between tool calls. MemNet gives the agent a small, typed, **atomised knowledge graph** it can:

- **atomise** state into many small `@TAG:` rows and `@EDG` links (one idea per row — the most important discipline),
- add facts, tasks, and relations once; update them when state changes,
- pull back only the live slice on the next turn (`query warm --anchor`),
- settle or expire missions so they stop polluting the prompt,
- keep hard limits and produce machine-readable warnings instead of silent bloat.

The pipe wire format is intentionally **token-efficient**: warm reads inject a connected subgraph, not JSON dumps or prose blobs.

## Installation

```powershell
pip install memnet-llm
```

From source (development):

```powershell
pip install -e ".[dev]"
```

The CLI command is still **`memnet`**. PyPI package name is **`memnet-llm`** (the name `memnet` on [PyPI](https://pypi.org/project/memnet/) is a different project — memristive neural networks).

Requires Python ≥ 3.11.

## Quick start

You need two terminals. One runs the in-memory server that holds the graph; the other runs the CLI client.

**Terminal 1 (server):**

```powershell
memnet serve
# prints: MEMNET_SERVE=127.0.0.1:18765
```

**Terminal 2 (client):**

```powershell
# See the cheat sheet
memnet guide --loose

# Start a session with the bundled schema
memnet session open --map-file src/memnet/examples/schema.example.txt
# stderr also prints: MEMNET_SESSION=mn_xxxxxxxx
$env:MEMNET_SESSION = "mn_xxxxxxxx"

# Ingest a small world (LAW rules + world state + missions)
memnet add --file src/memnet/examples/workflow.example.txt

# Preferred read for the next LLM turn: only live mission state
memnet query warm --anchor PLR01

# When done
memnet session close $env:MEMNET_SESSION
```

Without `memnet serve` running, any stateful command returns `@ERR: serve_required`.

For one-off scripting or tests you can set `MEMNET_TEST_INLINE=1` to run in-process (no server), but this is not the normal multi-turn agent mode.

**LLM agents:** read `LLM-GUIDE.md` (in this repo) for the full agent playbook, the goldfish loop, settlement pattern, and disciplines. It is written to be consumed by models.

## Atomisation (required)

MemNet is a **knowledge graph**, not a document store. **Atomisation** — breaking state into many small nodes and explicit `@EDG` edges — is the discipline that makes `query warm` token-efficient.

| Do | Don't |
|----|--------|
| One fact / entity / task per `@TAG:` row | Paragraphs or merged facts in one field |
| Wire relations with `@EDG` | "A helps B and also C" in a single row |
| Short fields: ids, codes, keys, paths | Prose, markdown, full file contents |
| Batch many lines in one `add --stdin` | One giant row instead of many atoms |

```powershell
# Good — three atoms + one edge
memnet add --stdin @"
@TSK: T01|Clear warehouse|1|in_progress|persistent
@NPC: N03|helper|labour|1|0|0|active|persistent
@EDG: E01|N03|helps|T01|labour|persistent
"@
```

See `LLM-GUIDE.md` for the full agent playbook. Application notes (novel, SysML, MUD) show domain-specific tag maps — all use the same atomisation rule.

## The goldfish loop (recommended pattern)

A typical agent turn:

1. `add` new rows or `update` existing ones — **atomised** `@TAG:` lines (batch via `--stdin` or `--file` is best).
2. `query warm --anchor <focus>` — returns only active (non-recyclable) rows, always includes LAW.
3. Paste the wire lines into the prompt, reason, decide on next adds/updates or a mission settle.
4. On mission complete: **update** the `TSK` (or equivalent) with both `status=settled` **and** `recycle=delete_on_settle`. Mission edges usually use `delete_on_expire` or `delete_on_settle`.
5. Optionally `housekeep prune stale --apply` to physically remove settled rows.
6. Next turn starts again at step 1 with a (usually new) anchor.

`query context` (cold) returns everything and emits `@WRN: stale_in_store|…` on stderr when recyclable rows exist. Prefer `warm`.

## Wire format

Token-efficient **pipe rows** — one graph atom per line (pair with atomisation above):

```
@TAG: field|field|...
```

- **One record = one idea** — split compound state into more rows + `@EDG`, not longer fields.
- Pipe inside a value must be escaped: `note\|extra` (or `\\|` in some shells).
- Always quote the whole line in PowerShell or bash when it contains special characters.
- Reserved output tags: `@SESSION`, `@ERR`, `@WRN`, `@STAT`, `@REL`, `@DEL`.
- Errors and advisories go to **stderr**; data rows to **stdout**.

Example multi-line ingest (PowerShell):

```powershell
memnet add --stdin @"
@NPC: N01|Shen Tiexin|female(12)|0|traditional|80|active|persistent
@EDG: E01|N01|seeks_help|PLR01|unlock|delete_on_expire
"@

memnet update --stdin @"
@NPC: N01|Shen Tiexin|female(12)|0|traditional|90|active|persistent
"@
```

See `memnet guide`, `memnet examples map`, and `memnet tagmap fields --tag <TAG>` for the current schema.

## Commands

Run any command with `--help` for full flags.

### Session lifecycle
| Command                  | Purpose |
|--------------------------|---------|
| `session open --map-file` | Create a new session (prints `@SESSION:` and `MEMNET_SESSION=...` on stderr) |
| `session resume <id>`    | Attach to an existing session |
| `session current`        | Show the id from `$env:MEMNET_SESSION` (or "none") |
| `session list`           | List live sessions (id, expires, minutes left, last modified) |
| `session save --file`    | **Optional** export of the current graph to a user-chosen snapshot file (wire format) |
| `session load --file`    | Restore a snapshot into RAM (new session id by default; `--keep-id` to reuse) |
| `session close <id>`     | Destroy the session (graph is gone) |

Default TTL is 60 minutes (`MEMNET_SESSION_TTL_MINUTES` or `--ttl`).

### Add, update & delete
- `add [line] [--file PATH] [--stdin] [--dry-run] [--allow-new-relation] [--agent NAME] [--session]`
  - Create **new** rows only. Fails with `id_exists` if the id is already in the graph.
- `update [line] [--file PATH] [--stdin] [--dry-run] [--allow-new-relation] [--agent NAME] [--session]`
  - Replace **existing** rows only. Fails with `not_found` if the id is missing (catches update typos).
- Batch via `--stdin` or `--file` is strongly preferred. `--dry-run` parses without mutating.
- `delete --id ID`

### Query (graph reads)
- `query warm --anchor ID [--depth N] [--max-rows M]` — **the normal read for agents**. `active_only` is forced; anchor is required. LAW rows are always included.
- `query context [--anchor] [--depth] [--max-rows] [--active-only]` — cold/full view (use for audit; warns on stale rows).
- `query neighbors <id> [--depth]`
- `query path <src> <dst>`

### Direct reads
- `read list [--tag T] [--active-only] [--where field=value ...]`
- `read get --id ID [--tag T]`

`--where` filters by field value (exact match). Repeat for AND. Use `*` or `?` wildcards for glob match (e.g. `--where name=*Tiexin*`).

### Housekeeping
- `housekeep stats` — `@STAT` rows + caps for rows/edges/relations/orphans/dangling/recyclable/**modified**.
- `housekeep stale|orphans|dangling|recyclable` — list the respective sets.
- `housekeep prune stale|... --apply` — actually delete (emits `@DEL` lines and a summary on stderr).

`stale` = recyclable + dangling + orphans.

### Schema & relations
- `tagmap fields [--tag T]` / `map fields` — reference field lists.
- `tagmap show` / `map show` — current session's effective tag map.
- `relations list` — allowed EDG relation names for this session.
- New relations are rejected unless `add` or `update` uses `--allow-new-relation` (subject to `max_relations`).

### Examples & server
- `examples map|workflow|add <tag>|path`
- `serve [--host] [--port]` — the in-memory graph host. Required for normal CLI use across processes.
- `version`, `guide`, `guide --loose`

## Session model & optional snapshots

- One `session open` per task. Agents should `resume` rather than open duplicates.
- The graph is **RAM only** while the session is live.
- `session save --file my.snap` writes a plain-text wire-format snapshot that *you* own. `session load --file my.snap` brings it back into a (usually new) RAM session.
- On `close` or TTL expiry the session is dropped from the server; no server-side files remain.
- Snapshots are a user convenience, not MemNet's durability layer.

## Housekeeping, warnings, and signals

On every stateful command the server emits advisory `@WRN` lines on stderr (capped per call):

- `near_cap*`, `ttl_expiring`
- `stale_in_store`, `stale_dangling`, `stale_orphans`, `stale_graph`
- `mission_settled`
- `fanout_clamped`, `dangling_endpoint`, etc.

`@STAT` lines report counts vs caps. `@DEL` lines are emitted after successful `prune --apply` or `delete`.

## Environment variables

| Variable                        | Effect |
|---------------------------------|--------|
| `MEMNET_SESSION`                | Default session id when `--session` is omitted |
| `MEMNET_SESSION_TTL_MINUTES`    | Default TTL for new sessions (1..1440) |
| `MEMNET_AGENT`                  | Default agent name stamped on written records |
| `MEMNET_SERVE_HOST`, `MEMNET_SERVE_PORT` | Bind address for `memnet serve` (client discovery is implicit via the same vars) |
| `MEMNET_MAX_ROWS` / `MAX_LAW` / `MAX_RELATIONS` / ... | Hard caps (see `Caps` in config) |
| `MEMNET_TEST_INLINE`            | When set, CLI runs in-process (tests, one-off scripts). Not for normal agent use. |

All caps have `MEMNET_MAX_*` names; see source for the full list and defaults.

## Architecture (one minute)

- `tagMap` — merged fixed + user schema loaded at `session open`. Drives parsing and field order on output.
- `memStore` — in-memory nodes + directed edges (EDG). Write-order index, simple BFS for neighbours / paths / warm packs.
- `LAW` rows — special, usually exempt from orphan/dangling accounting and always surface in warm reads.
- `recycle` field — `persistent` (default for active world) vs `delete_on_settle` / `delete_on_expire` (missions). `query warm` hides the latter.
- Server holds a registry of live `SessionEntry`s. CLI is a stateless client that talks over localhost TCP (or in-process in tests).

No JSON on the wire for LLM consumption — only the `@TAG:` lines plus a handful of control records on stderr.

## Application notes

Seven self-contained worked examples live under `application-notes/` — each shows a complete MemNet pattern (schema, seed, 6-step loop, domain LAW rows). Ordered by typical adoption path, not release date.

| # | Note | Pattern |
|---|------|---------|
| 1 | [llm-software-development.md](application-notes/llm-software-development.md) | **Multi-turn coding in Cursor** — `@MOD`/`@SYM`/`@TSK`/`@USR`/`@DEC`, verified locators, v0.2.12 `session_load`/`session_save` retrospective; complements grep/LSP/git and Cursor codebase indexing |
| 2 | [llm-daily-news.md](application-notes/llm-daily-news.md) | **Batch RSS digest** (~100 articles/day) — run-scoped working memory (120-min TTL), `@KYWD` hub salience, `@CLU`/`@SYN` layers, Python bridge via `send_command` |
| 3 | [llm-tech-docs-decomposition.md](application-notes/llm-tech-docs-decomposition.md) | **Instrument manual / SCPI remote mode** — R&S RTO rev 29, 4 584 `@CMD`, procedure layers with `precedes`/`requires`, two driver turns; `scripts/extract_rto_scpi.py` |
| 4 | [llm-sysml-v2-modeling.md](application-notes/llm-sysml-v2-modeling.md) | **SysML v2 textual modeling** — 6U CubeSat PDU, `@PKG` cross-file refs, allocations/ports/traceability from rows, runtime behaviour budgeting |
| 5 | [llm-novel-writer.md](application-notes/llm-novel-writer.md) | **Interactive novel / RPG** — 6-step read → context → user-input-as-data → analyse → update → loop; `@LORE`/`@SCN`/`@STEP`, chapter merge |
| 6 | [llm-mud.md](application-notes/llm-mud.md) | **Multiplayer text MUD** — server-side world agent + client prose agents, *Alice in Wonderland* sample; tiered atomisation, `scripts/load_test_mud.py` |
| 7 | [llm-build-on-memnet.md](application-notes/llm-build-on-memnet.md) | **Builder guide** — author your own MCP server (`FastMCP` + `run_memnet` bridge, JSON envelope, LAW supplementation) and Cursor skill pack (`SKILL.md` frontmatter, `references/` split, `mcp.json` registration); worked example = `mcp-memnet` skill + `novel-mcp` application split |

Supplement: [novel-shenjia-initial-state.md](application-notes/novel-shenjia-initial-state.md) — 《工匠傳奇》 bootstrap rows for the novel writer MCP pipeline.

## Development

```powershell
.\scripts\dev.ps1          # setup / test / lint / fmt / cli
pytest
```

Tests run with `MEMNET_TEST_INLINE=1` so they do not require a separate `serve` process.

## MCP (optional)

Install the MCP adapter:

```powershell
pip install memnet-llm[mcp]
```

**Prerequisites:** `memnet serve` running in another terminal (same as normal multi-command CLI use).

```powershell
# Terminal 1
memnet serve

# Terminal 2 — stdio MCP server for Cursor / other hosts
memnet-mcp
```

Set `MEMNET_SESSION` to your open session id. Example Cursor MCP config:

```json
{
  "mcpServers": {
    "memnet": {
      "command": "memnet-mcp",
      "env": {
        "MEMNET_SESSION": "mn_your_session_id"
      }
    }
  }
}
```

**Tools (v1):** `serve_status`, `session_open`, `session_current`, `query_warm`, `add`, `update`, `read_get`, `housekeep_stats`. Each returns a JSON envelope with `stdout` / `stderr` wire lines, `exit_code`, `session_id`, and `errors[]` (from `@ERR:` lines). **`session_open`** auto-seeds **LAW01–LAW05** on every new session (prepended on each `query_warm`); optional **`seed_lines`** adds `@CFG` anchors and domain `@LAW` rows in the same call. See [LLM-GUIDE.md](LLM-GUIDE.md).

## Licence

MIT
