# parts/memnet-mcp

Generic MemNet MCP server (`memnet_mcp`) — goldfish-loop tools via **InProcessEngine** by default (`MEMNET_MCP_TRANSPORT=tcp` for serve fallback).

| Item | Value |
|------|-------|
| SysML | `MemNetMcpServer` / `McpFacade` |
| Role | host-local software surface |
| Package | `software/memnet_mcp/` |
| Entry | `python -m memnet_mcp.server` / console script `memnet-mcp` |

## Tools (thin)

Primary read: **`pin_map`** (`query_warm` = deprecated alias). Optional additive
`view=` — teach `shell` | `interior`; soft-accept `flowchart` | `parts` |
`statechart` (shell-like caps; grain filters deferred). Omit `view` for 0.3
Tier A `depth` / `max_rows` behaviour. See `docs/grammar/memnet-multi-layer.md` §5.
