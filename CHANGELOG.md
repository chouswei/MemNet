# Changelog

All notable changes to MemNet will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.5] - 2026-08-13

### Added
- **PinMapIngest leftover domains (#64)** — `PinMapIngest_Codebase` / `_PcbaAto` / `_SkillsRules` with deterministic locator ids (no client `NEW`), MutateGate GQL commit, budgets. CLI: `memnet ingest codebase|pcba|skills`. MCP: `ingest_codebase` / `ingest_pcba` / `ingest_skills`. Schema examples beside Sysml. Model: `implemented=true` / `roadmapOnly=false`; MN-VER-12-S09 no longer treats leftover domains as must-not-assume.

## [0.4.4] - 2026-08-13

### Added
- **LocalIpcGateway (MN-REQ-06.2)** — real AF_UNIX share of the in-process session registry (same length-prefixed JSON protocol as TCP `memnet serve`). Env: `MEMNET_IPC_SOCKET`. CLI: `memnet serve --ipc` / `--ipc-path`. Client `dispatch` prefers IPC over TCP when the socket is listening. Closes #50.
- **NeighbourhoodReserve / RSV (MN-REQ-12.13, #30)** — ego leases with required `llm_id` + `ttl_s`; `reserve` / `extend` / `release` (CLI + MCP); MutateGate rejects foreign/missing holder on reserved ids; pin map may emit `## Reserves` / `RSV […]` present lines; expired leases auto-release. SysML nest under `SessionLifecycle`.
- **PinMapIngest_Sysml (MN-REQ-11.16 / #31)** — first Path-B pin-map ingest engine: selective SysML v2 `.sysml` → PKG/PRT/REQ/POR pins with deterministic ids from `qname=` / `requirementId=` / `path=` (no client `NEW`). CLI `memnet ingest sysml`; MCP `ingest_sysml`. Codebase / PCBA `.ato` / skills remain interface-only (`not_implemented`). SysML nest under `PinMapRoadmap` (four engines; Sysml first).
- **ImportAbsorb / `import_slice`** — Path-B session import into the lead SSOT with `keep` / `reject` / `remint`; optional host **ImportGuard** soft policy (`--no-guard` to skip). CLI `memnet import-slice`; closes #48 / #49.
- **CapsPolicy ACL** — shipped engine gates (off by default until `session acl-enable`): who (`caller`) / `pin_map` vs mutate / `WorkerWriteScope` hard reject / optional `missionId`+`lease` bind. Live AgensGraph / N-server not claimed.
- **Linux publisher** — `scripts/publish.sh` (Unix twin of `publish.ps1`): `hatch build` + `twine check`; upload only with `--upload` when `TWINE_PASSWORD` is already set (`TWINE_USERNAME` defaults to `__token__`).

### Changed
- **docs: one-path / 0.5.0 plan** — `docs/ROADMAP-0.5.md`; README “How to run (one path)” + known gaps; multi-layer Open § aligned; `memnet-pi` HTTP as default remote teach; Layer = 1.x teach / Tier A = legacy alias; Pi one graph owner (HTTP bridged to serve).
- **docs: application-notes Layer teach** — circuit notes + InvAmp example use CST `ports=` / `law=` / `--bind-->` as primary; Tier A `derives` / `connects_to` / paren arrows / `@TAG` pipe demoted to legacy pointers; `docs/README.md` + `LLM-GUIDE.md` Layer pointers; golden `docs/grammar/examples/layer/layer_09_inv_amp_good.txt`.
- **README rewrite** — short as-is engineer guide (install, session pipe, import absorb, ACL/transport, honest deferred); no live AgensGraph or N-server claim.

### Fixed
- **MutateGate `rename_id` batch rollback (#27)** — failed mutate batches undo node re-id / endpoint retargets so the graph is not left half-renamed.
- **README merge markers** — remove conflict markers left on master after Path-B ingest merge (#61); restore the short as-is page.

## [0.4.2] - 2026-08-08

### Added
- **MN-VER-12-G00** - group verification case for organisational parent MN-REQ-12 (`sysml-models/models/verify.sysml`).
- **`docs/application-notes/llm-system-dev-multitask.md`** - Multitask pattern for downstream `modelbasedPrj-*` system repos (MemNet mission SSOT + product SysML structural SSOT).
- **`docs/README.md`** - developers vs applications docs index.

### Changed
- **Multitask doc trail** - `docs/multi-agent-sessions.md`, `AGENTS.md`, `README.md`, and repo skill cross-link MN-REQ-12, verify package, and case study; product backlog table for deferred ACL / reserve / ingest / WorkerWriteScope (MN-REQ-12.7, MN-VER-12-S09).
- **Skill routing** - slim repo `memnet-reference` to product development; thin `memnet-multitask` rule; application notes point at user-pack `memnet-format` / `memnet-multitask`.

### Fixed
- **MCP streamable-http Host header** - FastMCP DNS-rebinding allowlist was left at localhost after LAN/`0.0.0.0` rebind, causing Cursor `Invalid Host header` (421) for `Host: 10.0.0.10:18766`. Refresh `transport_security` on HTTP start; add `MEMNET_MCP_HTTP_TRUSTED_HOSTS` (comma list; `*` disables). Binding `0.0.0.0` without an allowlist disables Host checks (with warning).

## [0.4.1] - 2026-08-07

### Added
- **MCP streamable-http** - opt-in remote Cursor `"url"` transport on dedicated port **18766** path `/mcp` (`memnet-mcp --transport streamable-http`). Env: `MEMNET_MCP_HTTP_HOST` / `PORT` / `PATH`; LAN bind requires `MEMNET_MCP_ALLOW_REMOTE=1` (mirrors serve allow-remote); optional `MEMNET_MCP_HTTP_TOKEN` bearer gate. Stdio and TCP `memnet serve` `:18765` unchanged. Docs: `parts/memnet-mcp/README.md`, `.cursor/mcp.json.example`.
## [0.4.0] — 2026-08-06

### Added
- **MCP/CLI `pin_map(view=)`** — optional grain on live pin map (additive to 0.3 `depth`/`max_rows`): teach `shell` (depth≤1 + soft ≤8 NODE / ≤12 EDGE) and `interior` (no soft shell cap); `flowchart`|`parts`|`statechart` accepted with shell-like budget (grain filters deferred). `query_warm` / `query warm` alias the same param. Unknown view → `@ERR: bad_view`.
- **Layer dialect engine slice (step 3)** — parallel `memnet.layer` / `LayerCodec` + MutateGate path: dual EDGE (`src_port`/`dist_port`/`wire` on EDG), structured `ports=` / `law=` on NODE (CST auto-registered), soft-validate before commit (mixed endpoints, law-on-EDGE, bag denylist, carries= bind-only); pin map emits Layer wire when ports marked. Coexists with 0.3 Tier A `--(rel)-->` path.
- **Numeric incremental update** — shared-dialect `~` patches accept `key+=N` / `key-=N` for int/float fields; create keeps plain `=`; pin map shows absolute values; `@ERR: bad_numeric` / `invalid_field` on misuse.
- **Field formulas design** — `docs/grammar/memnet-field-formulas.md` (relation-first: formula as EDGE/`derives`; same-node self-loop MVP; no expression engine).
- **llm-nodal-analysis-formulas.md** — nodal (node-method) mapping to MemNet NODE|EDGE and multi-field `derives`/`feeds` for KCL/Ohm; cross-links from circuit schematic + formula design docs.

### Changed
- **Efficiency test budgets** — soft local wall-clock guards raised for Windows host noise (exact 2000 ms, glob 3000 ms, AND 2000 ms, neighbours 3000 ms); correctness asserts unchanged.

## [0.3.6] — 2026-08-06

### Added
- **Serve hardening MVP** — TCP length-prefixed frames capped (default 4 MiB; `MEMNET_SERVE_MAX_FRAME_BYTES`); oversized requests return `@ERR: frame_too_large` without unbounded allocation.
- **Non-loopback bind gate** — `memnet serve` refuses `0.0.0.0` and other non-loopback hosts unless `MEMNET_SERVE_ALLOW_REMOTE=1` (warns when enabled). Escape hatch for existing LAN binds (e.g. `10.0.0.10`).
- **Serve protocol errors** — malformed JSON and handler failures return framed JSON envelopes instead of silent disconnects.

### Changed
- **docs/grammar/memnet-security-multi-agent.md** — notes partial MVP (bind + frame cap); session token/ACL still design-only.

## [0.3.5] — 2026-07-25

### Added
- **Shared-dialect `SCHEMA` for session maps** — `session open --map-file` prefers `SCHEMA KIND ; fields=id …` (`MemNet.g4` `schemaDecl` / `KW_SCHEMA`); legacy `@TAG: id|…` pipe still accepted on load; `tag_map_to_lines` emits SCHEMA; examples under `schema.*.example.txt` migrated.

## [0.3.4] — 2026-07-25

### Changed
- **llm-circuit-schematic.md** — §3 leads with shared-dialect kinds/fields; legacy pipe TagMap confined to `session open --map-file` only (not agent wire).

## [0.3.3] — 2026-07-25

### Added
- **application-notes/llm-circuit-schematic.md** — schematic grain (`CMP`/`PIN`/`NET`), undirected net convention, ideal op-amp golden rules in s-domain under negative feedback, nodal analysis atoms; s-domain as unifying linear frame (DC / \(j\omega\) / inverse Laplace as views); indexed from `docs/LLM-GUIDE.md`.

## [0.3.2] — 2026-07-24

### Added
- **MCP `pin_map` tool** — primary name for live pin map read; `query_warm` kept as deprecated alias (same params/behaviour).
- **CLI `query pin-map`** — preferred subcommand; `query warm` kept as deprecated alias.
- **Node re-id on update** — `~ [OldId] ; id=NewId` re-keys and retargets edge endpoints; occupied target rejects (`id_occupied`) unless `; merge=true` (nodes only).
- **Neighbourhood reserve design** — `docs/grammar/memnet-neighbourhood-reserve.md` (holder `llm_id` + TTL; MCP sketch; not implemented).

### Changed
- MCP/CLI help and docs teach `pin_map` / `pin-map` first; legacy `query_warm` / `query warm` noted as aliases.

### Notes
- Multi-agent same-session lost-update remains unmitigated in code (mutex only); primary fix is neighbourhood reservation (design), not optimistic `rev`.

## [0.3.1] — 2026-07-23

### Fixed
- **ASCII-only example header** — schema.coding.example.txt header uses ASCII only (hygiene after v0.3.0).

## [0.3.0] — 2026-07-23

### Added
- **Tier A agent surface** — Write=display dialect (`tier_a.py`), golden tests, grammar design and examples under `docs/grammar/`.
- **MutateGate / PinMapComposer / IdAllocator** — Tier A mutate batches, live pin map (bounded ego digest), engine id mint for `[NEW]`.
- **SysML baseline** — `sysml-models/` and doctrine aligned to Net of Memory / pin-map ingest.
- **In-process MCP default** — generic `memnet-mcp` without a required TCP serve hop.

### Changed
- **Live pin map emits bare present lines** — no leading `+`/`~`/`-` on MemNet→LLM output (ops remain mutate-only); grammar, composer, README, and golden examples updated.
- **MCP law seed defaults to Tier A** — LAW01–LAW05 injected as Tier A; legacy `@TAG` pipe only when `seed_lines` are already pipe.
- **Parts layout** — engine under `parts/common/memnet/`, MCP under `parts/memnet-mcp/`; CLI help and bundled examples clarified (schema/workflow vs agent grammar fixtures).
- Housekeeping: root agent docs aligned to Tier A / pin map; `.gitignore` tightened for validate/refs/antlr extracts.

### Removed
- **novel-writer** — dropped from this repo (`DROP-NOVEL-WRITER.md`); MemNet hosts the graph engine and generic MCP only.

### Fixed / closed
- Issues #10–#12, #15–#16, #21 (Net of Memory refactor, Tier A/pin map, parts layout, novel drop, MCP path).

## [0.2.32] — 2026-07-07

### Fixed
- **Critical: `memnet/serve_client.py` unterminated module docstring** — the 0.2.31 client-API doc update (#2) added a closing paragraph but omitted the closing `"""`, wrapping `from __future__ import annotations` inside the string literal. Every `memnet` invocation (including `--help`) raised `SyntaxError` at import time. 0.2.31 was completely unusable (#9).
- **Regression coverage** — added `tests/test_packaging_sanity.py`: `ast.parse`'s every file under `src/`, imports `memnet`/`memnet_mcp` top-level modules, and walks+imports every submodule of `memnet` via `pkgutil.walk_packages`. This class of bug (valid at edit time, broken at import time, never exercised by any existing test) can no longer ship silently.

### Note
- If you installed `memnet-llm==0.2.31`, upgrade immediately: `pip install -U memnet-llm==0.2.32`.

## [0.2.31] — 2026-07-07

### Fixed
- **registry.py** — bare `get`/`remove` renamed to `get_entry`/`remove_entry` to avoid shadowing builtins (#1).
- **serve / serve_client surface** — `dispatch` declared canonical public client API; low-level TCP helpers documented as internal (#2).
- **snapshot load on remote serve** — `FileNotFoundError` now emits `snapshot_not_found|<path>|serve_cwd=<...>` so cross-host path mismatches are diagnosable (#3).
- **ingest hot path** — full-store `to_jsonl_rows` backup replaced by O(batch) incremental journal (added ids + replaced Records); rollback cost now proportional to batch size (#4).
- **serve TCP path exit_code** — `_handle_request` now captures `app(...)` return value for `typer.Exit`, ensuring `exit_code` is non-zero when per-line errors (FIELD_COUNT, etc.) occur (#5).
- **read enumeration** — added `read_list` MCP tool (and documented `read list --tag`) as the supported path for "all rows of tag X"; `query_walk` docstrings redirect to it (#7).
- **TTL expiry** — `get_session` now implements sliding TTL (extends `expires_at` by original `ttl_minutes` on every access), eliminating silent expiry for long-lived sessions (#8).

### Changed
- **TagMap immutability** — confirmed by design: schema is fixed at session open. Runtime tag addition is unsupported and dangerous; closed #6 with rationale.

## [0.2.30] — 2026-06-30

### Added
- **Two-step script pipeline** — `script_draft` (OLN+SBD+SCR bundle) → `script_review` (SCR only) → `prose`; `beat_stage.py`, `stage_wire_validate.py` (mechanical bundle checks only).
- **Prose author context** — `build_prose_user` includes **SBD** storyboard; Cast lists graph ids (`N01`, `P01`, …).
- **novel-mobile** — phase labels for `script_draft` / `script_review`; orchestrator logs finish retry errors to stderr.
- **Tests** — `test_stage_wire_validate`, prose SBD attachment, legacy `no_bundle` presentation clarification.

### Changed
- **Seed / LAW-PIPE20** — `script_draft_bundle`; USR55–57 stage hints; FSM `script_draft → script_review → prose → script_draft`.
- **`beat_orchestrator` / `wire_parse`** — bundle extract at draft; LLM review at review (no programmatic wire-id / canonical-name blocking on finish).
- **`presentation`** — legacy graphs with `no_bundle` no longer tell the LLM one-wire-only at `script_draft`.
- **`prose_beat_prepare`** — surfaces `sbd_rows` alongside `scr_row` / `oln_row`.
- **`warm_supplement`** — stage keys aligned to v2 FSM.
- **Codebase snap** — regenerated `workflow.memnet-codebase.snap.txt` (novel_mcp pipeline modules indexed).

### Fixed
- **novel-mobile `server.py`** — `continue` gate uses v2 script stages (not legacy `oln`).
- **Stuck `script_draft`** — conflicting LAW/presentation hints on old worlds; rebootstrap recommended.

## [0.2.29] — 2026-06-29

### Added
- **`effective_plr_body`** — preview post-`finish_delta` body from `update_lines` for LAW-VIT01 and HUD.

### Changed
- **HUD** — built after successful `beat_turn_finish` (post-commit semantics).
- **Prose retries** — up to 5 attempts when finish or VIT01 validation fails.

### Fixed
- **`play_service.run_beat`** — skip script when `beat_stage=prose`; propagate real errors instead of `None`.
- **`beat_orchestrator`** — fresh `beat_turn_begin` each prose phase; VIT01 honours `update_lines`; auto `飽食` downgrade when prose costs hunger.
- **`beat_turn_finish` warm** — use `NOVEL_WARM_DEPTH` (not depth 1) so option validation sees `lib_opt_copy`.
- **`validators`** — slot 6 min length follows `lib_opt_copy` when shorter than global `opt_copy` min.
- **novel-mobile `play.js`** — opening beat sends `{ start: true }`; `continue` only when resuming prose stage.
- **Seed USR32** — library option template lengthened to meet `12-28字`.

## [0.2.28] — 2026-06-29

### Added
- **`body_state`** — seed-driven HUD from `USR45` `body_plot` + `USR02` `hud_pipe`; vitality vs satiety conflict check.
- **`graph_sync_output_paths`** — align USR14/USR15 with per-world chapter/snapshot dirs on rebootstrap and each beat.
- **Tests** — `test_body_state`, `test_play_service_paths`; beat anchor, prompt, and presentation coverage.

### Changed
- **Beat progression** — world-dir continuation anchor; choice text in script + prose; hard fail when prose does not write chapter file; default `chp_num=1`.
- **`beat_prompt`** — world lore (魂穿、圖書館、文風) from seed `presentation.contracts` only; no genre hardcoding in prompts.
- **`presentation`** — voice/option USR keys (`narration`, `prose_style`, `inner_voice`, `opt_layout`, etc.) compiled into contracts.
- **Seed** — `@CHP` in tag map + opening row (fixes bootstrap seed ingest).
- **Martial catalog** — full-art name validation; renamed borderline `ART` rows; catalog expand tests.
- **novel-mobile** — beat index in UI (`play.js`); slightly larger root font (`app.css`).

### Fixed
- Rebootstrap/bootstrap no longer silently loads empty graph when `@CHP` was missing from tag map.


### Added
- **`entity_knowledge`** — `@EDG` SSOT for holder acquaintance (`knows` / `knows_via` / `soul_knows`); depth-gated POV name masking (`name_visible`, `knowledge_depth`).
- **`party_sheet`** — roster panel with EDG-gated NPC display names.
- **`catalog_session`**, **`affinity_edges`**, **`character_gender`**, **`skill_catalog_keys`** — catalog merge, affinity edges, gender normalisation, martial key helpers.
- **novel-mobile multi-world** — `world_registry`, `world_slot`, optional `auth`; split sheet modules; `scripts/novel_mobile_e2e.py`.
- **Tests** — `test_entity_knowledge`, `test_party_sheet`, `test_catalog_session`, `test_world_slot`, `test_novel_mobile_auth`, `test_novel_mobile_ui`, and related coverage.

### Changed
- **`knowledge_graph`** — EDG-based view; legacy `@KNH` path deprecated (shim only).
- **`presentation` / `beat_prompt`** — acquaintance masking in scene snapshot; prose POV layering (旁白「你」、內心才「我」); `LAW-NAME01` for EDG name reveal.
- **`player_sheet` / `player_profile`** — `pc_name` display; catalog-session skill names.
- **`novel_mobile` server** — per-world sessions, beat jobs, `expand_catalog` on world create; mobile UX fixes.
- **`warm_supplement`** — stage-aware USR enrichment; opening loadout improvements.

## [0.2.26] — 2026-06-29

### Added
- **`novel-mobile`** — LAN FastAPI + static SPA (`applications/novel_mobile/`): setup FSM, beat job polling, items/martial/production tabs; CLI `novel-mobile --app <id>`.
- **`play_service.py`** — shared session preflight and `run_beat` for `cursor_beat` and HTTP server; `on_phase` hooks for job status.
- **`player_sheet.py`** — generic inventory, martial stats, and production nodes from graph + `catalog_specs`.
- **`setup_profile_rules.py`** — instance-driven profile validation rules.
- **`catalog_specs`** — `item_actions`, `martial_actions`, `production` blocks in `wuxia_jinyong.json`.
- **Tests** — `test_play_service`, `test_player_sheet`, `test_novel_mobile_api`, `test_setup_profile_rules`.

### Changed
- **`cursor_beat.py`** — thin wrapper over `play_service`; removed duplicate orchestration.
- **`llm_client.py`** — DeepSeek-only chat completions (dropped multi-provider routing).
- **`opening_loadout` / `player_setup` / `player_profile`** — generic catalog-driven setup; improved guidance and pick flow.
- **`pyproject.toml`** — `[novel-mobile]` extra (`fastapi`, `uvicorn`); `novel-mobile` entry point.

### Removed
- **`agent_session.py`** — superseded by orchestrated `cursor_beat` pipeline.

## [0.2.25] — 2026-06-28

### Added
- **`novel_mcp.constants.NOVEL_WARM_MAX_ROWS`** (150) — shared warm row cap so `USR21` prose advisory and mid-sequence `@USR` rows are not truncated at 55.

### Changed
- **novel-writer warm reads** — `beat_turn_begin`, `_warm_pipeline`, `beat_turn_finish`, and `_supplement_prose_target` use `NOVEL_WARM_MAX_ROWS`; MCP server and `scripts/beat_turn.py` defaults updated.
- **Operator docs** — `.cursor/rules/novel-writer.mdc`, `llm-novel-cursor-sdk.md`, `novel_cursor/README.md`: production play via `cursor_beat.py` only; MCP beat commit tools reserved for SDK agents and system tests.
- **novel-shenjia-initial-state.md** — integrator table notes warm `max_rows=150`.

### Tests
- **`test_beat_turn_begin_uses_novel_warm_max_rows`** — asserts warm CLI passes `150`.

## [0.2.24] — 2026-06-27

### Added
- **novel-seed-spec.md** — normative SEED planning principles (§2 layering, three EDG planes, opening scene contract, god-realm vs play).
- **Player setup pipeline** — `player_profile.py`, `player_setup.py`, `setup_graph.py`, `setup_constants.py`, `opening_loadout.py`; MCP `read_player_setup`, `commit_player_profile`, `commit_opening_pick`.
- **Generic catalog schema** — `catalog_schema.py`, `martial_catalog_expand.py`, `applications/novel_cursor/catalog_specs/`; instance-driven genre validation (no Jin Yong hardcoding in `novel_mcp` core).
- **Warm enrich** — `warm_supplement.py` stage-aware merge; `presentation` opening_scene / `biz` / `scn_code`; `warm_index` BIZ/SCN rows.
- **cursor_beat** — `--setup`, `--name`, `--gender`, `--arts`; `beat_orchestrator.py`, `catalog_expand.py`, `chat_thread.py`, `llm_client.py`, `wire_parse.py`.
- **Shenjia martial catalog** — `application-notes/novel-shenjia-martial-catalog.md`; seed `USR69`/`USR70` opening contract.
- **Tests** — opening loadout, player profile, setup guidance, warm supplement, seed LAW budget, martial catalog expand, wire parse, chat thread, edg_time.

### Changed
- **scripts/novel_bootstrap.py** — generic `--app` bootstrap; optional catalog expand; removed `bootstrap_shenjia.py` / `shenjia_bootstrap.py`.
- **novel-shenjia-initial-state.md** — Engine/World split maintenance; opening scene domain wiring (`USR70`, `LAW-OLN01` opening_scn); setup USRs 60–67; LAW budget ≤40.
- **Tag map** — `@ART`, `@WUX`, `@MWU` for martial loadout.
- **beat_pipeline** — setup gate integration; prose-stage SCR enrich from `read list`.

### Fixed
- **Setup wire** — USR/PLR 4-field shape; PLR without extra recycle field; EDG add vs update on bootstrap.
- **catalog_expand** — `complete_messages` API for LLM expand.
- **test_beat_pipeline** — patch `play_context.run_memnet` for enrich isolation.

## [0.2.23] — 2026-06-27

### Added
- **Dual-loop Cursor SDK beat agents** — separate persistent script (編劇) and prose (作者) agents per story slug; agent ids under `novel-output/<slug>/agents/`.
- **applications/novel_cursor/agent_session.py** — create+primer or `Agent.resume`, stale-id recovery, `run_script_turn` / `run_prose_turn`.
- **src/novel_mcp/play_context.py** — `script_beat_prepare`, `prose_beat_prepare` (handoff gate at `USR23=prose`); `player_beat_prepare` deprecated alias.
- **novel-writer MCP** — `script_beat_prepare`, `prose_beat_prepare` tools.
- **src/novel_mcp/chapter_io.py** — `last_committed_paragraph` for `continuation_anchor`.
- **tests/** — `test_play_context.py`, `test_agent_session_paths.py`, `test_beat_prompts.py`.

### Changed
- **applications/novel_cursor/cursor_beat.py** — dual-phase orchestrator (script → handoff verify → prose); flags `--script-only`, `--prose-only`, `--reset-agents`, `--continue`; exit codes 0–4.
- **applications/novel_cursor/beat_prompt.py** — split `build_script_primer/turn`, `build_prose_primer/turn`; removed monolithic `build_beat_prompt`.
- **applications/novel_cursor/app_config.py** — `script_agent_id_file`, `prose_agent_id_file`.
- **.cursor/rules/novel-writer.mdc** — thin chat shells `cursor_beat.py` only; dual-agent contract.
- **application-notes/llm-novel-cursor-sdk.md** — dual-loop operator SSOT.
- **application-notes/llm-novel-writer.md** — § Cursor SDK dual-loop cross-ref.

### Tests
- Handoff gates, agent id paths, prompt smoke tests; `test_novel_cursor_config` agents_dir.

## [0.2.22] — 2026-06-27

### Added
- **applications/novel_cursor/** — generic Cursor SDK beat runner (`cursor_beat.py`, `app_config.py`, instance JSON); `NOVEL_BEAT_RESULT` wire contract; paths from seed `USR14`/`USR15`.
- **applications/novel_cursor/instances/shenjia_caifa.json** — 《工匠傳奇》 instance config.
- **application-notes/llm-novel-cursor-sdk.md** — operator guide for thin-chat + SDK beat architecture.
- **tests/test_novel_cursor_config.py** — instance/seed path resolution.

### Fixed
- **novel_mcp.beat_pipeline** — `_ensure_beat_stage_update` now matches `@USR: UID|beat_stage|STAGE|…` via `_usr_beat_stage_row` (was splitting on wrong pipe field; USR23 prose→oln persist could fail).

### Changed
- **.cursor/rules/novel-writer.mdc** — generic novel-writer chat contract (`--app` / `novel-output/<slug>/` paths).
- **applications/shenjia_caifa/** — thin shim forwarding to `novel_cursor --app shenjia_caifa`.
- **application-notes/novel-shenjia-initial-state.md** — bootstrap doc points at `scripts/novel_bootstrap.py`.

### Tests
- `tests/test_beat_pipeline.py` — USR23 beat_stage update regressions.

## [0.2.21] — 2026-06-27

### Fixed
- **tests/test_mem_store.py** — drop `@LAW` from user tag-map fixtures; `LAW` is a fixed tag (`fixed_tags.py`). Restores `test_linked_law_scope_reduces_warm_laws`, `test_context_walk_hops_from_anchor`, and `test_all_law_scope_without_law06` (full suite green).

## [0.2.20] — 2026-06-27

### Fixed
- **novel_mcp.beat_pipeline** — `beat_stage` desync: `read_get USR23` is now authoritative (instead of relying on potentially stale/truncated `query warm --anchor STEP01`). `_apply_authoritative_beat_stage` and `_read_get_body` added; called from `beat_turn_begin`, `beat_turn_finish`, `_warm_pipeline`.
- `pipeline_next_action` now respects `pipeline_no_bundle` + current `beat_stage` (no longer overridden by `step_n==4` "finish prose" hint).
- `parse_warm_stdout` prefers USR23 when multiple `beat_stage` rows present.

### Changed
- **.cursor/rules/novel-writer.mdc** — made fully generic (title, SSOT, examples, player name handling, contract topics). No longer hard-coded to any specific novel or `CHR01`.
- Improved stage transition reliability for strict `LAW-PIPE20 no_bundle` 4-micro-cycle pipeline (OLN → SBD → SCR → prose).

### Tests
- `test_beat_stage_authoritative_over_stale_warm`
- `test_pipeline_oln_then_sbd_without_bypass`
- Extended `test_pipeline_next_action` for no_bundle case.

## [0.2.19] — 2026-06-26

### Added
- **novel_mcp.beat_pipeline** — LAW-PIPE20 four-stage pipeline: `@OLN` → `@SBD` → `@SCR` → prose; `sbd_lines` / `scr_lines` on `beat_turn_finish`; stage gate + auto `USR23|beat_stage` advance.
- **novel_mcp** — ISO game-time parsing (`game_time.py`), Chongzhen shichen display (`time_display.py`, `calendars/`), workspace path helper (`paths.py`).
- **application-notes/novel-shenjia-initial-state.md** — 《工匠傳奇》seed: VIT02/VIT03 (氣血/內力 pools, 昏厥 auto_beat), USR21 prose advisory, integrator notes.
- **scripts** — `beat_turn.py` SBD/SCR wire files; `shenjia_bootstrap.py`, `reorganize_seed.py`.

### Changed
- **novel-mcp** — beat tools live only on `novel-writer` MCP (removed duplicate from `memnet-mcp`).
- **beat_turn_begin** — per-stage `draft_note`; supplemental `USR21` warm; `auto_beat` / `no_options` when 氣血=0.
- **beat_turn_finish** — `prose_advisory_hint` for short beats; `pipeline_bypass` for legacy paths.

### Tests
- `tests/test_beat_pipeline.py` — pipeline gate, bundle, stage advance, auto_beat, time regress.
- `tests/test_game_time.py`, `tests/test_time_display.py` — calendar / ISO time.

## [0.2.18] — 2026-06-24

### Changed
- **memnet.housekeep** — single-pass `_categorise` walker now shared by `stats`, `stale_rows`, `prune_stale`, `dangling_rows`, and `orphan_rows`. Previously `stats` walked the store five times (one each for `row_count_non_law`, edges scan, recyclable, dangling, orphans); now once. Public API unchanged.
- **memnet.mem_store** — added `_by_tag: dict[str, set[str]]` secondary index maintained by `upsert`/`delete`/`load_records`. `list_records(tag=...)` now starts from the tag bucket (O(k)) instead of scanning every row in the store (O(N)). `row_count_non_law` and `law_count` also use the index. Measured ~4× speed-up on mixed-tag 10k-row stores; no API change.
- **memnet.wire.split_payload** — fast path via `payload.split("|")` when no backslash is present (the >95 % case). Falls back to the escape-aware loop only when needed.

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

[Unreleased]: https://github.com/chouswei/MemNet/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/chouswei/MemNet/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/chouswei/MemNet/compare/v0.3.6...v0.4.0
[0.3.6]: https://github.com/chouswei/MemNet/compare/v0.3.5...v0.3.6
[0.2.30]: https://github.com/chouswei/MemNet/compare/v0.2.29...v0.2.30
[0.2.29]: https://github.com/chouswei/MemNet/compare/v0.2.28...v0.2.29
[0.2.28]: https://github.com/chouswei/MemNet/compare/v0.2.27...v0.2.28
[0.2.27]: https://github.com/chouswei/MemNet/compare/v0.2.26...v0.2.27
[0.2.26]: https://github.com/chouswei/MemNet/compare/v0.2.25...v0.2.26
[0.2.25]: https://github.com/chouswei/MemNet/compare/v0.2.24...v0.2.25
[0.2.24]: https://github.com/chouswei/MemNet/compare/v0.2.23...v0.2.24
[0.2.23]: https://github.com/chouswei/MemNet/compare/v0.2.22...v0.2.23
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
