# AGENTS.md — MemNet

LLM hub for this system repo. Prefer in-repo skills and docs over ad-hoc invention. Layout authority: `LAYOUT.md` + `C:\Projects\SYSTEM-REPO-LAYOUT.md`.

## Mission

**MemNet** (Net of Memory) is an **agent memory graph** (NODE | EDGE) between LLM call pipelines and data search. Agents read a bounded **live pin map** each turn and write with the same shapes — that **shared dialect** (**Write = display**). Design docs may still say “Tier A” for this dialect. Primary read: MCP `pin_map` / CLI `query pin-map`; `query_warm` / `query warm` are legacy aliases. Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy. Aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation**. Transport: **in-process first** (TCP fallback). This repo is **engine + generic memnet-mcp** only — novel-writer dropped. See `README.md` and `docs/grammar/`.

## Where to look

| Need | Path |
|------|------|
| Doctrine / quick start | `README.md` |
| System identity / SemVer | `project.toml` |
| Python packaging | `pyproject.toml` |
| Layout adaptation notes | `LAYOUT.md` |
| SysML models | `sysml-models/` |
| Shared-dialect grammar design | `docs/grammar/` |
| Field formulas (generic EDGE relations) | `docs/grammar/memnet-field-formulas.md` (any domain; not circuit-only) |
| Multi-layer (design) | `docs/grammar/memnet-multi-layer.md` (stratified pin maps; law on node; EDGE = connection; nesting = view budget) |
| Neighbourhood reserve (design) | `docs/grammar/memnet-neighbourhood-reserve.md` |
| Security / session ACL / multi-agent (design) | `docs/grammar/memnet-security-multi-agent.md` |
| Agent playbook (as-is pipe) | `docs/LLM-GUIDE.md` |
| Domain worked examples | `docs/application-notes/` (schematic; nodal note *applies* formula grammar to circuits) |
| Core library | `parts/common/memnet/` |
| Generic MCP | `parts/memnet-mcp/software/memnet_mcp/` |
| Session stub | `AGENT-CONTEXT.md` |
| Novel-writer drop record | `DROP-NOVEL-WRITER.md` |
| Vendor grammar pins | `refs/README.md` |

## Skill routing

| Intent | Path |
|--------|------|
| MemNet work (pin map / MCP session / mutate / parts) | `.cursor/skills/memnet-reference/` |
| Doctrine / grammar / models | `README.md`, `docs/grammar/`, `sysml-models/` |
| Generic MCP implementation | `parts/memnet-mcp/` |

Personal Cursor skills (user pack) are out of scope for this repo.

## Policy

1. **Part-based folders** — do not recreate top-level `src/` or `applications/`.
2. **Novel-writer is dropped** — do not restore `parts/novel-writer/` or novel MCP extras; see `DROP-NOVEL-WRITER.md`.
3. Keep `AGENT-CONTEXT.md` thin; durable state lives in MemNet sessions when used.
4. British English in new docs written for this repo.
