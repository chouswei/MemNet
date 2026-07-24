# AGENTS.md — MemNet

LLM hub for this system repo. Prefer skills over ad-hoc invention. Layout authority: `LAYOUT.md` + `C:\Projects\SYSTEM-REPO-LAYOUT.md`.

## Mission

**MemNet** (Net of Memory) sits between pipelines of LLM calls and data searching: a **NODE | EDGE** working graph for agents. **Tier A** Write = display; live **pin map** (bounded ego digest; `query warm` / `query_warm` is a legacy alias). Aims (MN-REQ-00): save wall-clock time and tokens while keeping factual accuracy. Aids **system**, **programme**, **software**, **firmware**, **hardware**, and **documentation**. Transport: **in-process first** (TCP fallback). This repo is **engine + generic memnet-mcp** only — novel-writer dropped. See `README.md` and `docs/grammar/`.

## Where to look

| Need | Path |
|------|------|
| Doctrine / quick start | `README.md` |
| System identity / SemVer | `project.toml` |
| Python packaging | `pyproject.toml` |
| Layout adaptation notes | `LAYOUT.md` |
| SysML models | `sysml-models/` |
| Tier A grammar design | `docs/grammar/` |
| Agent playbook (as-is pipe) | `docs/LLM-GUIDE.md` |
| Domain worked examples | `docs/application-notes/` |
| Core library | `parts/common/memnet/` |
| Generic MCP | `parts/memnet-mcp/software/memnet_mcp/` |
| Session stub | `AGENT-CONTEXT.md` |
| Novel-writer drop record | `DROP-NOVEL-WRITER.md` |
| Vendor grammar pins | `refs/README.md` |

## Skill routing

| Intent | Skill / tool |
|--------|----------------|
| MemNet work in this repo (Tier A / pin map / MCP / parts) | **primary:** `.cursor/skills/memnet-reference`; then user pack `memnet-format`, `mcp-memnet`; SSOT `README.md` + `docs/grammar/` (playbook `docs/LLM-GUIDE.md`) |
| Ambiguous planning | user pack `reasoning-strategy-selector` |

## Policy

1. **Part-based folders** — do not recreate top-level `src/` or `applications/`.
2. **Novel-writer is dropped** — do not restore `parts/novel-writer/` or novel MCP extras; see `DROP-NOVEL-WRITER.md`.
3. Keep `AGENT-CONTEXT.md` thin; durable state lives in MemNet sessions when used.
4. British English in new docs written for this repo.
