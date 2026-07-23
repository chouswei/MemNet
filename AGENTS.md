# AGENTS.md — MemNet

LLM hub for this system repo. Prefer skills over ad-hoc invention. Layout authority: `LAYOUT.md` + `C:\Projects\SYSTEM-REPO-LAYOUT.md`.

## Mission

MemNet is an in-memory working-memory graph for LLM agents (CLI + MCP). This repository hosts the graph engine and generic memnet-mcp only.

## Where to look

| Need | Path |
|------|------|
| System identity / SemVer | `project.toml` |
| Python packaging | `pyproject.toml` |
| Layout adaptation notes | `LAYOUT.md` |
| SysML models | `sysml-models/` |
| Agent playbook | `docs/LLM-GUIDE.md` |
| Domain worked examples | `docs/application-notes/` |
| Core library | `parts/common/memnet/` |
| Generic MCP | `parts/memnet-mcp/software/memnet_mcp/` |
| Session stub | `AGENT-CONTEXT.md` |
| Novel-writer drop record | `DROP-NOVEL-WRITER.md` |

## Skill routing

| Intent | Skill / tool |
|--------|----------------|
| MemNet wire format / goldfish loop | user pack `memnet-format`, `mcp-memnet`; read `docs/LLM-GUIDE.md` |
| Ambiguous planning | user pack `reasoning-strategy-selector` |

## Policy

1. **Part-based folders** — do not recreate top-level `src/` or `applications/`.
2. **Novel-writer is dropped** — do not restore `parts/novel-writer/` or novel MCP extras; see `DROP-NOVEL-WRITER.md`.
3. Keep `AGENT-CONTEXT.md` thin; durable state lives in MemNet sessions when used.
4. British English in new docs written for this repo.
