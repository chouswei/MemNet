# AGENTS.md — MemNet

LLM hub for this system repo. Prefer in-repo skills and docs over ad-hoc invention. Layout authority: `LAYOUT.md` + `C:\Projects\SYSTEM-REPO-LAYOUT.md`.

## Mission

**MemNet** (Net of Memory) is **mission working memory** — a session graph (GQL **node**/vertex, **edge**/relationship, **property**) **between** LLM call pipelines and data search, not the corpus and not GraphRAG. Agents read a bounded **live pin map** each turn and write in the same **GQL (openCypher-shaped)** family — redefined **Write = display** via shaped subgraph emit ([`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md)). In-session recall is **serial**: kind/keyword cue, then `pin_map` neighbourhood. Primary read: MCP `pin_map` / CLI `query pin-map`; leftover `query_warm` / `query warm` are leftover aliases. Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy. Aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation**. Transport: **in-process first** (single-agent; TCP fallback). **Multitask** requires TCP serve or streamable-http MCP — see Multitask policy below. This repo is **engine + generic memnet-mcp** only — novel-writer dropped. Repo product **0.19.5** (Hatch SSOT; last PyPI **`memnet-llm==0.19.4`** until upload; [#148](https://github.com/chouswei/MemNet/pull/148) nickname-off-`pin_map` published; 0.19.5 `SHAPE_DROP_KEYS`). **1.0** = 0.5–0.8 claimed (unclaimed). See `README.md`, [`docs/SHAPE.md`](docs/SHAPE.md), and `docs/grammar/`.

## Where to look

Catalog and load order: [`docs/README.md`](docs/README.md) (identity / `grammar/` / `cabinet/` / `extras/` / `operations/` / `application-notes/`).

| Need | Path |
|------|------|
| Doctrine / quick start | `README.md` |
| Product shape / version map | `docs/SHAPE.md`, `docs/ROADMAP.md` |
| GQL wire / 0.5 math | `docs/grammar/` |
| Durable cabinet | `docs/cabinet/` |
| Numbered extras / ACL design | `docs/extras/` |
| Multitask ops | `docs/operations/multi-agent-sessions.md` |
| Applications | `docs/application-notes/` (`system/`, `domains/`, `examples/`) |
| SysML models + MN-REQ-12 | `sysml-models/` |
| Engine / MCP | `parts/common/memnet/`, `parts/memnet-mcp/` |
| Identity / packaging / layout | `project.toml`, `pyproject.toml`, `LAYOUT.md` |
| Session stub / novel drop / vendor pins | `AGENT-CONTEXT.md`, `DROP-NOVEL-WRITER.md`, `refs/README.md` |

## Skill routing

**Repo skills** (`.cursor/skills/`): this checkout **vendors** the MemNet stack. **Core:** `memnet-use` + `mcp-memnet` + `memnet-format` + `memnet-nested-sessions` + `memnet-multitask`. **Build:** `memnet-reference`. SysML / codebase are specialists. Routing: [`.cursor/skills/SKILL-GRAPH.md`](.cursor/skills/SKILL-GRAPH.md). Optional human-machine pack: [cursor-user-skills](https://github.com/chouswei/cursor-user-skills) — this folder wins here.

| Intent | Path |
|--------|------|
| **Use MemNet** (goldfish) | `.cursor/skills/memnet-use/` |
| MCP tools, session, ingest | `.cursor/skills/mcp-memnet/` |
| GQL / shaped pin_map wire | `.cursor/skills/memnet-format/` |
| Nested sessions / look loop | `.cursor/skills/memnet-nested-sessions/` |
| Multitask Mode + MemNet | `.cursor/skills/memnet-multitask/`, `docs/operations/multi-agent-sessions.md`, `.cursor/rules/memnet-multitask.mdc` |
| Code MOD/SYM | `.cursor/skills/memnet-codebase-snap/` |
| SysML design memory | `.cursor/skills/sysml-modeling-workflow/` (checklist / cache / documentation / gql) |
| Develop MemNet engine / MCP / grammar | `.cursor/skills/memnet-reference/` |
| MN-REQ-12 SysML + verify | `sysml-models/models/requirements.sysml`, `sysml-models/models/verify.sysml`, `sysml-models/outputs/multitask-case-study.md` |

## Policy

1. **Part-based folders** — do not recreate top-level `src/` or `applications/`.
2. **Novel-writer is dropped** — do not restore `parts/novel-writer/` or novel MCP extras; see `DROP-NOVEL-WRITER.md`.
3. Keep `AGENT-CONTEXT.md` thin; durable state lives in MemNet sessions when used.
4. British English in new docs written for this repo.
5. **Multitask + MemNet** — when Multitask Mode is on or Task sub-agents run: **MUST** follow `docs/operations/multi-agent-sessions.md`. One shared session id per mission; chat is never SSOT. **MUST** use TCP serve or streamable-http MCP (not default in-process). Parent owns `TSK_*` / `USR_*` settle and ends turn after delegate; workers cue then `pin_map` first and mutate only under assigned scope. **MUST NOT** poll workers, redo worker investigation from chat, Snap-on-session, or assume full ACL modes / `session_token` (CapsPolicy when ACL enabled; RSV and Path-B ingest **are** shipped).

## Cursor Cloud specific instructions

Pure Python package (`memnet-llm`, Python >= 3.11). No external services, database, or Docker — the graph is in-memory. Standard lint/test/build commands are the authoritative recipe in `.github/workflows/ci.yml`; run/quick-start flow is in `README.md`.

- **Virtualenv**: the startup update script installs everything (editable, with `dev,mcp` extras) into `.venv` at the repo root. **Activate it first** each session: `source .venv/bin/activate`. The `memnet` and `memnet-mcp` console scripts and `pytest`/`ruff` only exist inside `.venv`. System Python is externally managed, so do not `pip install` into it.
- **Tests / lint**: `pytest` (runs fully in-process; `tests/conftest.py` sets `MEMNET_TEST_INLINE=1`, no serve daemon needed). `ruff check` + `ruff format --check` over `parts/common/memnet parts/memnet-mcp/software tests`. One test (`agensgraph_live`) is skipped unless `MEMNET_AGENSGRAPH_URL` points at an external AgensGraph server.
- **CLI path**: every `memnet` subcommand except `serve` needs a running serve process. Start it with `export MEMNET_IPC_SOCKET=/tmp/memnet.sock && memnet serve --ipc` (TCP fallback: `memnet serve`). Non-obvious: serve proxies argv, not your shell env — pass the minted `--session mn_...` explicitly (do not rely on `MEMNET_SESSION`).
- **MCP path**: single-agent `memnet-mcp` (stdio) is in-process and needs no serve. `session_open` requires a map. Product write is **`mutate`**. leftover `add`/`update` remain leftover façades. MCP args are `wire_lines`/`map_lines` and `session` (the id), not `session_id`.
- **SysML:** map `schema.sysml.example.txt` (not the game map) or ingest fails `unknown_tag`. Path-B `ingest_sysml` is **1 path → current session**. **Model Snap** (`memnet snap model` / `snap_model`) is one load tree → catalog + interiors. Goldfish: relatives of **one** interior; look loop re-anchors `session=` (one \(S\) per generate). Raise `max_nodes` (default 200) for large Path-B ingest — `requirements.sysml` needs ~200 (193 nodes / 192 edges). Cue a returned `qname=` / `requirementId=` (e.g. `REQ_MN_REQ_00`). leftover `anchor=` is leftover.
