# In-repo Cursor skills (MemNet checkout)

Two jobs. **Use MemNet** (agent reference). **Build MemNet** (this product’s engine). Doctrine SSOT is `docs/` — skills route; they do not invent claims.

**Upstream pack (optional):** [chouswei/cursor-user-skills](https://github.com/chouswei/cursor-user-skills). This folder is **not** the whole pack.

## Use MemNet (reference)

Hub: [`memnet-use/`](memnet-use/SKILL.md). Then one specialist:

| Skill | Role |
|-------|------|
| `mcp-memnet/` | MCP: `pin_map`, `mutate`, ingest, `snap_model`, export |
| `memnet-format/` | GQL / shaped `pin_map` wire |
| `memnet-nested-sessions/` | Nested sessions, look loop, already-built `session=` |
| `memnet-multitask/` | Multitask + shared TCP/HTTP |
| `memnet-codebase-snap/` | Code `MOD`/`SYM` snap |
| `sysml-*` | SysML modelling with MemNet |

## Build MemNet (this repo)

| Skill | Role |
|-------|------|
| `memnet-reference/` | Engine / MCP / grammar / CI / layout |

**MUST NOT** vendor hardware / PCBA / mermaid / generator / DigiKey skills here.

Routing: [`SKILL-GRAPH.md`](SKILL-GRAPH.md). Hub: repo `AGENTS.md`.
