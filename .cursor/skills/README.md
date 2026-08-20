# In-repo Cursor skills (MemNet checkout)

**Not** the whole user pack. Vendored here so cloud VMs and this repo can load MemNet **application** skills without `~/.cursor/skills`.

**Upstream pack:** [chouswei/cursor-user-skills](https://github.com/chouswei/cursor-user-skills) (optional on a human machine).  
**Doctrine SSOT:** this repo’s `docs/` (`SHAPE.md`, `grammar/gql-wire-profile.md`, `LLM-GUIDE.md`). Skills route; they do not invent product claims.

| Skill | Role |
|-------|------|
| `memnet-reference/` | **Build** this product (engine / MCP / grammar) |
| `mcp-memnet/` | Use generic `memnet-mcp` tools |
| `memnet-format/` | GQL / shaped `pin_map` wire |
| `memnet-multitask/` | Multitask + shared TCP/HTTP |
| `memnet-codebase-snap/` | Code `MOD`/`SYM` snap |
| `sysml-*` | SysML modelling with MemNet |

**MUST NOT** vendor hardware / PCBA / mermaid / generator / DigiKey skills into this folder.

Routing: [`SKILL-GRAPH.md`](SKILL-GRAPH.md). Hub: repo `AGENTS.md`.
