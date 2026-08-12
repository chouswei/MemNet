# AGENTS.md — MemNet

LLM hub for this system repo. Prefer in-repo skills and docs over ad-hoc invention. Layout authority: `LAYOUT.md` + `C:\Projects\SYSTEM-REPO-LAYOUT.md`.

## Mission

**MemNet** (Net of Memory) is an **agent memory graph** (NODE | EDGE) between LLM call pipelines and data search. Agents read a bounded **live pin map** each turn and write with the same shapes — that **shared dialect** (**Write = display**). Design docs may still say “Tier A” for this dialect. Primary read: MCP `pin_map` / CLI `query pin-map`; `query_warm` / `query warm` are legacy aliases. Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy. Aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation**. Transport: **in-process first** (single-agent; TCP fallback). **Multitask** requires TCP serve or streamable-http MCP — see Multitask policy below. This repo is **engine + generic memnet-mcp** only — novel-writer dropped. See `README.md` and `docs/grammar/`.

## Where to look

| Need | Path | Class |
|------|------|-------|
| Docs index (developers vs applications) | `docs/README.md` | — |
| Doctrine / quick start | `README.md` | — |
| System identity / SemVer | `project.toml` | — |
| Python packaging | `pyproject.toml` | — |
| Layout adaptation notes | `LAYOUT.md` | — |
| SysML models | `sysml-models/` | — |
| Shared-dialect grammar design | `docs/grammar/` | developers |
| Layer ↔ GQL construct map (model; wire stays Layer) | `docs/grammar/layer-gql-map.md` | developers |
| Field formulas (generic EDGE relations) | `docs/grammar/memnet-field-formulas.md` (any domain; not circuit-only) | developers |
| Multi-layer (design) | `docs/grammar/memnet-multi-layer.md` (stratified pin maps; law on node; dual EDGE bind/relation; nesting = view budget) | developers |
| Neighbourhood reserve (design) | `docs/grammar/memnet-neighbourhood-reserve.md` | developers |
| Security / session ACL / multi-agent (design) | `docs/grammar/memnet-security-multi-agent.md` | developers |
| Multi-agent / Multitask (as-is 0.4.x) | `docs/multi-agent-sessions.md` | developers |
| Multitask for system repos (`modelbasedPrj-*`) | `docs/application-notes/llm-system-dev-multitask.md` | applications |
| MN-REQ-12 SysML + verify | `sysml-models/models/requirements.sysml`, `sysml-models/models/verify.sysml`, `sysml-models/outputs/multitask-case-study.md` | — |
| Agent playbook (0.4.x) | `docs/LLM-GUIDE.md` | developers |
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
| Doctrine / grammar / models | `README.md`, `docs/grammar/`, `sysml-models/` |
| Generic MCP implementation | `parts/memnet-mcp/` |

## Policy

1. **Part-based folders** — do not recreate top-level `src/` or `applications/`.
2. **Novel-writer is dropped** — do not restore `parts/novel-writer/` or novel MCP extras; see `DROP-NOVEL-WRITER.md`.
3. Keep `AGENT-CONTEXT.md` thin; durable state lives in MemNet sessions when used.
4. British English in new docs written for this repo.
5. **Multitask + MemNet** — when Multitask Mode is on or Task sub-agents run: **MUST** follow `docs/multi-agent-sessions.md`. One shared session id per mission; chat is never SSOT. **MUST** use TCP serve or streamable-http MCP (not default in-process). Parent owns `TSK_*` / `USR_*` settle and ends turn after delegate; workers `pin_map` first and mutate only under assigned scope. **MUST NOT** poll workers, redo worker investigation from chat, or assume ACL / reserve / ingest (design-only in 0.4.x).
