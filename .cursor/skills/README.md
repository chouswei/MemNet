# In-repo Cursor skills (MemNet vendor)

This checkout **vendors** the MemNet agent skills. Doctrine SSOT remains `docs/`. Skills **route**; they do not invent claims.

Optional extra pack on a human machine: [chouswei/cursor-user-skills](https://github.com/chouswei/cursor-user-skills). **This folder wins** in this repo (cloud VMs have no user pack).

## Core (use MemNet)

Default one skill per turn. Hub first unless a specialist trigger matches.

| Skill | Job |
|-------|-----|
| [`memnet-use/`](memnet-use/SKILL.md) | Goldfish loop: cue → `pin_map` → sparse `mutate` |
| [`mcp-memnet/`](mcp-memnet/SKILL.md) | MCP tools, session, ingest, RSV, export |
| [`memnet-format/`](memnet-format/SKILL.md) | GQL / shaped `pin_map` wire |
| [`memnet-nested-sessions/`](memnet-nested-sessions/SKILL.md) | Catalog / look loop / `session=` |
| [`memnet-multitask/`](memnet-multitask/SKILL.md) | Shared TCP/HTTP; parent / worker |

Product write is **`mutate`**. leftover `add` / `update` / `id:'NEW'` / `anchor=` / `query_warm` are leftover-named.

## Specialists (open on need)

| Skill | Job |
|-------|-----|
| [`memnet-codebase-snap/`](memnet-codebase-snap/SKILL.md) | Code `:MOD` / `:SYM` |
| [`sysml-modeling-workflow/`](sysml-modeling-workflow/SKILL.md) | SysML 6-step turn in this repo |
| [`sysml-modeling-session-checklist/`](sysml-modeling-session-checklist/SKILL.md) | Preflight before `.sysml` edits |
| [`sysml-memnet-cache/`](sysml-memnet-cache/SKILL.md) | Relatives cache defer |
| [`sysml-memnet-documentation/`](sysml-memnet-documentation/SKILL.md) | Snap / read policy / patterns |
| [`sysml-gql/`](sysml-gql/SKILL.md) | Thin SysML × GQL bridge |

## Build this product

| Skill | Job |
|-------|-----|
| [`memnet-reference/`](memnet-reference/SKILL.md) | Engine / MCP / grammar / CI / layout |

**MUST NOT** vendor hardware / PCBA / mermaid / generator / DigiKey skills here.

Routing: [`SKILL-GRAPH.md`](SKILL-GRAPH.md). Hub: repo [`AGENTS.md`](../AGENTS.md). Docs index: [`docs/README.md`](../docs/README.md).
