# AGENTS.md — MemNet

LLM hub for this system repo. Prefer in-repo skills and docs over ad-hoc invention. Layout authority: `LAYOUT.md` + `C:\Projects\SYSTEM-REPO-LAYOUT.md`.

## Mission

**MemNet** (Net of Memory) is **mission working memory** — a session graph (GQL **node**/vertex, **edge**/relationship, **property**) **between** LLM call pipelines and data search, not the corpus and not GraphRAG. Agents read a bounded **live pin map** each turn and write in the same **GQL (openCypher-shaped)** family — redefined **Write = display** via shaped subgraph emit ([`docs/grammar/gql-wire-profile.md`](docs/grammar/gql-wire-profile.md)). In-session recall is **serial**: kind/keyword cue, then `pin_map` neighbourhood. Primary read: MCP `pin_map` / CLI `query pin-map`; `query_warm` / `query warm` are legacy tool aliases. Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy. Aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation**. Transport: **in-process first** (single-agent; TCP fallback). **Multitask** requires TCP serve or streamable-http MCP — see Multitask policy below. This repo is **engine + generic memnet-mcp** only — novel-writer dropped. See `README.md`, [`docs/SHAPE.md`](docs/SHAPE.md), and `docs/grammar/`.

## Where to look

| Need | Path | Class |
|------|------|-------|
| Docs index (developers vs applications) | `docs/README.md` | — |
| Doctrine / quick start | `README.md` | — |
| Product shape (from the problem) | `docs/SHAPE.md` | developers |
| Version map (SemVer SSOT) | `docs/ROADMAP-0.5.md` | developers |
| System identity / SemVer | `project.toml` | — |
| Python packaging | `pyproject.toml` | — |
| Layout adaptation notes | `LAYOUT.md` | — |
| SysML models | `sysml-models/` | — |
| Shared-dialect grammar / GQL wire | `docs/grammar/` (`gql-wire-profile.md` = M1 SSOT; `math-skeleton.md` = 0.5 Recall/Commit math) | developers |
| Field formulas (design; formula-as-EDGE) | `docs/grammar/memnet-field-formulas.md` (any domain; not circuit-only) | developers |
| Stratified pin-map views | Covered in `docs/grammar/gql-wire-profile.md` (archive: former multi-layer Layer doc) | developers |
| Neighbourhood reserve (RSV shipped; grammar still the design note) | `docs/grammar/memnet-neighbourhood-reserve.md` | developers |
| Security / session ACL / multi-agent (design) | `docs/grammar/memnet-security-multi-agent.md` | developers |
| Multi-agent / Multitask (as-is 0.8) | `docs/multi-agent-sessions.md` | developers |
| Multitask for system repos (`modelbasedPrj-*`) | `docs/application-notes/llm-system-dev-multitask.md` | applications |
| MN-REQ-12 SysML + verify | `sysml-models/models/requirements.sysml`, `sysml-models/models/verify.sysml`, `sysml-models/outputs/multitask-case-study.md` | — |
| Agent playbook (0.8) | `docs/LLM-GUIDE.md` | developers |
| Domain worked examples | `docs/application-notes/` (schematic; nodal note *applies* formula grammar to circuits) | applications |
| Core library | `parts/common/memnet/` | — |
| Generic MCP | `parts/memnet-mcp/software/memnet_mcp/` | — |
| Session stub | `AGENT-CONTEXT.md` | — |
| Novel-writer drop record | `DROP-NOVEL-WRITER.md` | — |
| Vendor grammar pins | `refs/README.md` | — |

## Skill routing

**Repo skills** (`.cursor/skills/`) = **MemNet product development** only.  
**User pack** (`~/.cursor/skills/`) = **applying** MemNet in agents, Multitask, and system repos. Routing graph: `~/.cursor/skills/SKILL-GRAPH.md`.

| Intent | Path |
|--------|------|
| Develop MemNet engine / MCP / grammar / product SysML | `.cursor/skills/memnet-reference/` |
| Use MemNet via MCP (pin map, sessions, mutate) | `~/.cursor/skills/mcp-memnet/` |
| Shared dialect wire shapes | `~/.cursor/skills/memnet-format/` |
| Multitask Mode + MemNet (application) | `~/.cursor/skills/memnet-multitask/`, `docs/multi-agent-sessions.md`, `.cursor/rules/memnet-multitask.mdc` |
| Multitask system-dev (`modelbasedPrj-*`) | `~/.cursor/skills/memnet-multitask/`, `docs/application-notes/llm-system-dev-multitask.md` |
| SysML design memory with MemNet | `~/.cursor/skills/sysml-memnet-documentation/`, `~/.cursor/skills/sysml-memnet-cache/` |
| MN-REQ-12 SysML + verify (Multitask) | `sysml-models/models/requirements.sysml`, `sysml-models/models/verify.sysml`, `sysml-models/outputs/multitask-case-study.md` |
| Doctrine / grammar / models | `README.md`, `docs/SHAPE.md`, `docs/ROADMAP-0.5.md`, `docs/grammar/`, `sysml-models/` |
| Generic MCP implementation | `parts/memnet-mcp/` |

## Policy

1. **Part-based folders** — do not recreate top-level `src/` or `applications/`.
2. **Novel-writer is dropped** — do not restore `parts/novel-writer/` or novel MCP extras; see `DROP-NOVEL-WRITER.md`.
3. Keep `AGENT-CONTEXT.md` thin; durable state lives in MemNet sessions when used.
4. British English in new docs written for this repo.
5. **Multitask + MemNet** — when Multitask Mode is on or Task sub-agents run: **MUST** follow `docs/multi-agent-sessions.md`. One shared session id per mission; chat is never SSOT. **MUST** use TCP serve or streamable-http MCP (not default in-process). Parent owns `TSK_*` / `USR_*` settle and ends turn after delegate; workers cue then `pin_map` first and mutate only under assigned scope. **MUST NOT** poll workers, redo worker investigation from chat, Snap-on-session, or assume full ACL modes / `session_token` (CapsPolicy when ACL enabled; RSV and Path-B ingest **are** shipped).

## Cursor Cloud specific instructions

Pure Python package (`memnet-llm`, Python >= 3.11). No external services, database, or Docker — the graph is in-memory. Standard lint/test/build commands are the authoritative recipe in `.github/workflows/ci.yml`; run/quick-start flow is in `README.md`.

- **Virtualenv**: the startup update script installs everything (editable, with `dev,mcp` extras) into `.venv` at the repo root. **Activate it first** each session: `source .venv/bin/activate`. The `memnet` and `memnet-mcp` console scripts and `pytest`/`ruff` only exist inside `.venv`. System Python is externally managed, so do not `pip install` into it.
- **Tests / lint**: `pytest` (runs fully in-process; `tests/conftest.py` sets `MEMNET_TEST_INLINE=1`, no serve daemon needed). `ruff check` + `ruff format --check` over `parts/common/memnet parts/memnet-mcp/software tests`. One test (`agensgraph_live`) is skipped unless `MEMNET_AGENSGRAPH_URL` points at an external AgensGraph server.
- **CLI path**: every `memnet` subcommand except `serve` needs a running serve process. Start it with `export MEMNET_IPC_SOCKET=/tmp/memnet.sock && memnet serve --ipc` (TCP fallback: `memnet serve`). Non-obvious: serve proxies argv, not your shell env — pass the minted `--session mn_...` explicitly (do not rely on `MEMNET_SESSION`).
- **MCP path**: single-agent `memnet-mcp` (stdio) is in-process and needs no serve. `session_open` requires a map — pass `map_file=parts/common/memnet/memnet/examples/schema.example.txt` (or `map_lines`) or it errors `no_map`. MCP tool args are `wire_lines`/`map_lines` (lists) and `session` (the id), not `session_id`.
- **SysML modeling (`ingest_sysml`)**: open the session with the SysML schema map `parts/common/memnet/memnet/examples/schema.sysml.example.txt`, not the game `schema.example.txt`, or ingest fails `unknown_tag|PKG not in schema`. Raise `max_nodes` (default 200) for large files — `sysml-models/models/requirements.sysml` needs ~200 (ingests 193 nodes / 192 edges). Then `pin_map` on a returned `@ANCHORS` id (e.g. `REQ_MN_REQ_00`).
