# Changelog

All notable changes to MemNet will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- `memStore` maintains `src`/`dist` edge indexes for O(1) adjacency lookup; `neighbors`, `find_path`, and `query warm` no longer scan all EDG rows.

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

[Unreleased]: https://github.com/chouswei/MemNet/compare/v0.2.3...HEAD
[0.2.3]: https://github.com/chouswei/MemNet/compare/v0.2.2...v0.2.3
[0.2.0]: https://github.com/chouswei/MemNet/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/chouswei/MemNet/releases/tag/v0.1.0
