# Changelog

All notable changes to MemNet will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.17] — 2026-06-23

### Fixed
- **memnet_mcp.client._run_inline** — captured `app(..., standalone_mode=False)` return value. Previously `typer.Exit(n)` was converted by click to a return value and silently discarded, so MCP tools (e.g. `add`, `update`) reported `exit_code=0` even when the underlying command failed (e.g. `unknown_relation`). Errors still appeared in `errors[]` but the exit code lied.
- **memnet_mcp.server.session_open** — exposes `allow_new_relation: bool = False` and pipes it into the seed-add subcall. Lets callers seed `@EDG` rows with novel relations in a single tool invocation; without it the seed batch silently rolls back on the first unknown relation, leaving `rows=0`.

### Tests
- `tests/test_mcp.py::test_session_open_seed_lines_unknown_relation_aborts` — locks in fail-closed behaviour.
- `tests/test_mcp.py::test_session_open_seed_lines_allow_new_relation` — verifies the new flag.

## [0.2.16] — 2026-06-23

### Fixed
- **application-notes/llm-tech-docs-decomposition.md** — Mermaid diagram parse error (`@` in node labels; reserved `graph` subgraph id).

## [0.2.15] — 2026-06-23

### Added
- **application-notes/llm-build-on-memnet.md** — seventh application note; builder guide for writing MCP servers + Cursor skill packs on top of MemNet (FastMCP + `run_memnet` bridge, JSON envelope, LAW supplementation, skill-pack anatomy, `mcp.json` registration); worked example = `mcp-memnet` skill pack with `novel-mcp` split as secondary illustration.

### Changed
- **README.md**, **LLM-GUIDE.md** — application-notes index extended from 6 to 7 rows; LLM-GUIDE adds `prune stale` vs `prune recyclable` clarification, session snapshot / MCP `session_save`/`session_load` guidance, CLI + MCP quick-reference subsections.

## [0.2.14] — 2026-06-23

### Added
- **application-notes/llm-software-development.md** — multi-turn coding in Cursor; retrospective v0.2.12 `session_load`/`session_save` MCP tools; `@TSK` anchor field; `@USR`/`@DEC` patterns.
- **src/memnet/examples/schema.coding.example.txt** and **workflow.coding.example.txt** — coding tag map and tutorial seed (~45 rows).
- **tests/test_tag_map.py** — `test_coding_schema_and_workflow_parse` validates coding example seed against schema.

### Changed
- **README.md**, **LLM-GUIDE.md** — application notes reordered by adoption path (coding → batch → manual → SysML → novel → MUD); compact index table replaces chronological "first…sixth" list.

### Fixed
- **application-notes/llm-software-development.md** — Mermaid diagram parse error (`@` in node labels; reserved `graph` subgraph id).

## [0.2.13] — 2026-06-22

### Added
- **application-notes/llm-tech-docs-decomposition.md** — instrument manual / SCPI remote-mode decomposition (R&S RTO User Manual rev 29 worked example); `@CMD` user-map tag; two 6-step turns (hello + capture/measure).
- **src/memnet/examples/schema.techdocs.example.txt** and **workflow.rto-remote.example.txt** — tech-docs tag map and RTO full command dictionary (4 584 `@CMD`, ~1 MB seed).
- **scripts/extract_rto_scpi.py** — regenerates seed from `data/rto/UserManual_en_29.pdf`.
- **data/rto/scpi_commands.txt** — tab-separated command index.
- **tests/test_tag_map.py** — `test_techdocs_schema_and_workflow_parse` validates example seed against schema.

## [0.2.12] — 2026-06-22

### Added
- **`novel_mcp`** package and **`novel-mcp`** MCP server — `prose_metrics`, `chapter_prose_gate`, `chapter_prose_append` (application layer, separate from graph MCP).
- MemNet MCP **`session_load`** and **`session_save`** tools for snapshot restore/persist without Shell.
- **`scripts/novel_beat.py`**, **`scripts/bench_novel_turn.py`** — novel beat CLI and turn benchmark helpers.

### Changed
- **Breaking:** prose/chapter MCP tools removed from **`memnet-mcp`**; use **`novel-mcp`** for step-2 chapter writes.
- Chapter file reader splits beat blocks on **blank lines** (fixes one-line-per-sentence paragraph inflation).
- **application-notes/llm-sysml-v2-modeling.md**, novel writer docs, and initial-state note updated.

### Removed
- `memnet_mcp/chapter_io.py`, `memnet_mcp/zh_text.py` — moved to `novel_mcp/`.

## [0.2.11] — 2026-06-17

### Added
- MCP **`prose_metrics`** and **`chapter_prose_append`** — Traditional Chinese beat length gates (default 300–600 chars) for interactive novel workflows.
- **`src/memnet_mcp/zh_text.py`**, **`chapter_io.py`** — zh char counting and chapter file append with validation.
- Novel examples: **`schema.novel.example.txt`**, **`workflow.novel.example.txt`**, **`application-notes/novel-initial-state.md`**, **`.cursor/rules/novel-writer.mdc`**.

### Changed
- **`modified_at`** updates on any session interaction (reads and writes via `_load_session`, `session resume`, `session current`); `has_writes` still tracks graph mutations only.
- Novel prose minimum beat length **400 → 300** chars (MCP defaults, RULE09 seed, docs, tests).

## [0.2.10] — 2026-06-12

### Added
- MCP **`session_open(seed_lines=…)`** — optional seed rows (`@CFG`, domain `@LAW`, …) via chained `add --stdin` after open.
- MCP **`session_open`** auto-seeds **LAW01–LAW05** (engine invariants + goldfish read-first rule) when those ids are absent from `seed_lines` (`src/memnet_mcp/seed.py`).
- **`MemNetResponse.merge()`** — combine open + seed envelopes in the MCP client.

### Changed
- **README.md**, **LLM-GUIDE.md**, **application-notes/llm-daily-news.md** — MCP session seeding and default LAW behaviour.

## [0.2.9] — 2026-06-12

### Added
- `application-notes/llm-daily-news.md` — daily RSS digest pipeline (session-scoped `@KYWD` hubs, `@CLU`/`@SYN` layers, Python bridge, prompt formatters).

### Changed
- **README.md** and **LLM-GUIDE.md** — pointer to the daily-news application note.

## [0.2.8] — 2026-06-11

### Changed
- **README.md** and **LLM-GUIDE.md** — emphasise **atomisation** as required discipline (knowledge graph, one idea per row, `@EDG` wiring, token-efficient wire format).

## [0.2.7] — 2026-06-11

### Added
- Optional **`memnet-llm[mcp]`** extra: `memnet-mcp` stdio MCP server (`src/memnet_mcp/`) with tools for the goldfish loop (`query_warm`, `add`, `update`, `session_open`, `read_get`, `housekeep_stats`, `serve_status`).

### Changed
- `memnet serve` TCP protocol accepts optional **`stdin`** on JSON payloads so `add --stdin` / `update --stdin` work over TCP (backward-compatible).
- CLI `--stdin` ingest accepts text streams (e.g. from serve/MCP) when `sys.stdin` has no `.buffer`.
- `session current` accepts **`--session`** (same as other stateful commands) for MCP and remote TCP clients.

## [0.2.6] — 2026-06-11

### Added
- `scripts/estimate_novel_io_tokens.py` — recompute wire-format token estimates for novel-writer MemNet IO examples.

### Changed
- `application-notes/llm-novel-writer.md` — atomized graph rows (`@EVT`, `@COST`, `@BOND`, `@STEP`), per-IO token annotations, follow-on pipeline cycle, STEP anchoring, and pipeline pitfalls.

## [0.2.5] — 2026-06-11

### Added
- PyPI distribution as **`memnet-llm`** (`pip install memnet-llm`); CLI entry point remains `memnet`.
- `LICENSE` (MIT) and `[project.urls]` in package metadata.

### Changed
- Removed duplicate wheel `force-include` for bundled examples (included via package layout).

## [0.2.4] — 2026-06-10

### Changed
- `memStore` maintains `src`/`dist` edge indexes for O(1) adjacency lookup; `neighbors`, `find_path`, and `query warm` no longer scan all EDG rows.
- Sessions track `modified_at` (ISO UTC, set on add/update/delete/prune). Exposed in `session list`, `session current`, and `housekeep stats` (`@STAT: modified|…`); persisted in snapshots when present.

## [0.2.3] — 2026-06-10

### Added
- `read list --where field=value` — filter rows by field value (exact match; repeat for AND). `*` and `?` wildcards supported (e.g. `--where name=*Tiexin*`).
- Efficiency benchmarks and regression tests for `--where` filtering (`scripts/benchmark_efficiency.py`, `tests/test_efficiency.py`).
- New application note: `application-notes/llm-sysml-v2-modeling.md` — LLM-assisted SysML v2 textual modeling (6U CubeSat PDU controller) following the 6-step pipeline; README and LLM-GUIDE updated with pointers.

## [0.2.0] — 2026-06-10

### Added
- Single source of truth for the package version: `pyproject.toml` reads it from `src/memnet/__init__.py` via `hatch.version`.
- `memnet version --json` for automation; default output is now a wire line `@VER: memnet|<version>`.
- `memnet add` — create new rows only (`id_exists` if the id is already in the graph).
- `memnet update` — replace existing rows only (`not_found` if the id is missing).
- `CHANGELOG.md`.

### Changed
- CLI `memnet version` now emits the wire-format `@VER: memnet|<version>` line instead of the plain `memnet <version>` string.
- **Breaking:** `memnet write` removed. Use `add` for new rows and `update` for changes. `LLM-GUIDE.md` and `README.md` updated.
- `memnet examples write` renamed to `memnet examples add`.
- LAW02 in the bundled workflow example now documents add-then-update id discipline.

## [0.1.0] — 2026-06-10

Initial public release.

### Added
- In-memory working-memory graph for LLM agents (no automatic disk state).
- `memnet serve` — local TCP server holding sessions in RAM; CLI is a stateless client.
- Wire-format I/O (`@TAG: field|field|...`) on stdout; `@ERR`, `@WRN`, `@STAT`, `@DEL` signals on stderr.
- Session lifecycle: `session open / resume / current / list / close`, TTL (default 60 min, env `MEMNET_SESSION_TTL_MINUTES`).
- Optional snapshot save/load (`session save --file`, `session load --file [--ttl] [--keep-id]`) — wire-format files the user owns.
- Tag schema (fixed `EDG` / `LAW` + user tags at open), strict field validation, relation allow-list with `--allow-new-relation`.
- Graph reads:
  - `query warm --anchor <id>` — active-only, LAW-prepended (the recommended agent read).
  - `query context` — cold/full view, warns on stale rows.
  - `query neighbors`, `query path`.
- Direct reads: `read list`, `read get`.
- Mission lifecycle via `recycle` labels (`persistent`, `delete_on_settle`, `delete_on_expire`); settled missions hidden from `warm` reads.
- Housekeeping: `housekeep stats|stale|recyclable|dangling|orphans`, `housekeep prune ... --apply`.
- Advisory warnings: `near_cap*`, `ttl_expiring`, `stale_in_store`, `stale_dangling`, `stale_orphans`, `stale_graph`, `mission_settled`, `fanout_clamped`, `dangling_endpoint`, `corrupt_row`, etc.
- Bundled examples (`memnet examples map|workflow|write|path|agent-guide`) and inline guides (`memnet guide`, `memnet guide --loose`).
- `LLM-GUIDE.md` — full agent playbook (goldfish loop, settlement pattern, ID discipline, common failure modes).
- 26 tests passing on Python 3.11 / 3.12.

### Notes
- v1 is **local only** — TCP loopback, no remote / MCP / authentication.
- Caps are configurable via `MEMNET_MAX_*` env vars.
- Sessions live in process memory only. On `serve` restart, all sessions are gone unless saved via `session save`.

[Unreleased]: https://github.com/chouswei/MemNet/compare/v0.2.16...HEAD
[0.2.16]: https://github.com/chouswei/MemNet/compare/v0.2.15...v0.2.16
[0.2.15]: https://github.com/chouswei/MemNet/compare/v0.2.14...v0.2.15
[0.2.14]: https://github.com/chouswei/MemNet/compare/v0.2.13...v0.2.14
[0.2.13]: https://github.com/chouswei/MemNet/compare/v0.2.12...v0.2.13
[0.2.7]: https://github.com/chouswei/MemNet/compare/v0.2.6...v0.2.7
[0.2.6]: https://github.com/chouswei/MemNet/compare/v0.2.5...v0.2.6
[0.2.5]: https://github.com/chouswei/MemNet/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/chouswei/MemNet/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/chouswei/MemNet/compare/v0.2.2...v0.2.3
[0.2.0]: https://github.com/chouswei/MemNet/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/chouswei/MemNet/releases/tag/v0.1.0
