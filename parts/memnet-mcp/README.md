# parts/memnet-mcp

Generic MemNet MCP server (`memnet_mcp`) — goldfish-loop tools via **InProcessEngine** by default (`MEMNET_MCP_TRANSPORT=tcp` for serve fallback).

| Item | Value |
|------|-------|
| SysML | `MemNetMcpServer` / `McpFacade` |
| Role | host-local software surface |
| Package | `software/memnet_mcp/` |
| Entry | `python -m memnet_mcp` / console script `memnet-mcp` |

## Tools (thin)

Primary read: **`pin_map`** (`query_warm` = deprecated alias). Optional additive
`view=` — teach `shell` | `interior`; soft-accept `flowchart` | `parts` |
`statechart` (shell-like caps; grain filters deferred). Omit `view` for 0.3
Tier A `depth` / `max_rows` behaviour. See `docs/grammar/memnet-multi-layer.md` §5.

## Transports

| Transport | When | Command |
|-----------|------|---------|
| **stdio** (default) | Local Cursor `command` | `memnet-mcp` |
| **streamable-http** (opt-in) | Remote Cursor `"url"` | `memnet-mcp --transport streamable-http` |

HTTP is **not** the default. Doctrine remains **in-process first**; HTTP is for a dedicated remote MCP endpoint (e.g. Pi) without touching Inventree on `:80` / `:443`.

### streamable-http defaults

| Env | Default | Notes |
|-----|---------|-------|
| `MEMNET_MCP_HTTP_HOST` | `127.0.0.1` | Loopback only unless allow-remote |
| `MEMNET_MCP_HTTP_PORT` | `18766` | Distinct from TCP `memnet serve` `:18765` |
| `MEMNET_MCP_HTTP_PATH` | `/mcp` | Cursor URL path |
| `MEMNET_MCP_ALLOW_REMOTE` | unset | Required for non-loopback bind (mirrors `MEMNET_SERVE_ALLOW_REMOTE`) |
| `MEMNET_MCP_HTTP_TOKEN` | empty | When set, require `Authorization: Bearer <token>`; reject otherwise |

CLI overrides: `--host`, `--port`, `--path`.

**Unsafe:** empty `MEMNET_MCP_HTTP_TOKEN` plus LAN bind (`MEMNET_MCP_ALLOW_REMOTE=1`). Prefer a long shared secret before advertising the URL.

Same tool surface as stdio; the HTTP process owns the graph via InProcessEngine (do not dual-write to TCP unless you deliberately set `MEMNET_MCP_TRANSPORT=tcp`).

### Cursor `url` example

```json
{
  "mcpServers": {
    "memnet-pi": {
      "url": "http://10.0.0.10:18766/mcp",
      "headers": {
        "Authorization": "Bearer REPLACE_WITH_SHARED_TOKEN"
      }
    }
  }
}
```

Local stdio remains:

```json
{
  "mcpServers": {
    "memnet-local": {
      "command": "memnet-mcp",
      "env": {
        "MEMNET_WORKSPACE_ROOT": "c:\\Projects\\MemNet"
      }
    }
  }
}
```

### Pi install / restart (paste-friendly)

Do **not** bind `:80` / `:443` (Inventree). Use **18766** for MCP HTTP and **18765** for optional TCP serve.

```bash
# install / upgrade (example)
cd ~/MemNet   # or your clone path
pip install -e ".[mcp]"

# optional: TCP serve on loopback (CLI clients)
# MEMNET_SERVE_HOST=127.0.0.1 MEMNET_SERVE_PORT=18765
# memnet serve

# MCP HTTP for remote Cursor (LAN bind + bearer)
export MEMNET_MCP_HTTP_HOST=10.0.0.10
export MEMNET_MCP_HTTP_PORT=18766
export MEMNET_MCP_HTTP_PATH=/mcp
export MEMNET_MCP_ALLOW_REMOTE=1
export MEMNET_MCP_HTTP_TOKEN='generate-a-long-shared-secret'
memnet-mcp --transport streamable-http
```

systemd sketch (adjust paths/user):

```ini
[Unit]
Description=MemNet MCP streamable-http
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/pi/MemNet
Environment=MEMNET_MCP_HTTP_HOST=10.0.0.10
Environment=MEMNET_MCP_HTTP_PORT=18766
Environment=MEMNET_MCP_ALLOW_REMOTE=1
EnvironmentFile=-/home/pi/MemNet/.env.memnet-mcp
ExecStart=/home/pi/MemNet/.venv/bin/memnet-mcp --transport streamable-http
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Put `MEMNET_MCP_HTTP_TOKEN=…` in `.env.memnet-mcp` (gitignored). Restart: `sudo systemctl restart memnet-mcp-http`.
