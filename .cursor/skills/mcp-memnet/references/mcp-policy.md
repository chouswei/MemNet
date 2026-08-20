# MemNet MCP policy

## Architecture

```text
Cursor (stdio) → memnet-mcp
                 ├─ in-process engine (default)
                 └─ TCP → memnet serve (MEMNET_MCP_TRANSPORT=tcp)
```

- MCP is a thin adapter. Product default transport is **in-process** (no separate `memnet serve` required) for a **single** agent.
- User pack **shared / remote** path: Cursor HTTP `url` -> **`http://10.0.0.10:18766/mcp`**; Pi HTTP MCP MUST set `MEMNET_MCP_TRANSPORT=tcp` so it shares `memnet serve` **`:18765`**.
- Multitask / Task workers **MUST NOT** use in-process MCP for a shared session.
- Agent wire is **GQL / openCypher-shaped** (shaped pin_map read). Cue then pin_map (`find` if no ego).
- Primary read is the live **pin map** (`pin_map` tool; `query_warm` is legacy alias).
- Product **0.9.0**: live AgensGraph cabinet claimed (0.7); Neo4j client extra not live-claimed; RSV + Path-B ingest shipped.

## mcp.json (user pack)

Default (in-process — preferred):

```json
"memnet": {
  "command": "memnet-mcp",
  "args": [],
  "env": {
    "MEMNET_WORKSPACE_ROOT": "c:\\Projects\\MemNet"
  }
}
```

Do **not** set `MEMNET_SERVE_HOST` / `MEMNET_SERVE_PORT` unless you also set `MEMNET_MCP_TRANSPORT=tcp` (those host/port env vars alone do not select TCP; the package defaults to in-process).

Optional TCP (requires a running `memnet serve`):

```json
"env": {
  "MEMNET_MCP_TRANSPORT": "tcp",
  "MEMNET_SERVE_HOST": "127.0.0.1",
  "MEMNET_SERVE_PORT": "18765",
  "MEMNET_SESSION": "mn_…"
}
```

Use full path to `memnet-mcp` (or `python -m memnet_mcp.server`) on Windows if not on PATH. Restart Cursor after edits. Avoid remote LAN hosts for the default MemNet session unless deliberately bridging TCP.

**Out of scope:** novel-writer MCP (`novel-mcp`) is dropped from the MemNet product — do not configure it for MemNet work.

## Tools

See [tool-parameters.md](tool-parameters.md).

| Tool | Purpose |
|------|---------|
| `serve_status` | Probe (mainly TCP) |
| `session_open` / `save` / `load` / `current` | Session lifecycle |
| `pin_map` | Live pin map (`anchors` / `view` optional) |
| `find` | Bounded seed lookup then pin_map |
| `query_warm` | Deprecated alias for `pin_map` |
| `query_walk` | Hop debug |
| `add` / `update` | Mutate (openCypher-shaped) |
| `ingest_*` | Path-B artefact pins (shipped) |
| `import_slice` | Path-B absorb |
| `reserve` / `extend` / `release` | RSV (shipped) |
| `read_get` / `read_list` | Lookup / enumerate |
| `housekeep_stats` | Counts vs caps |

## Response envelope

Every tool (except `serve_status`) returns JSON text:

```json
{
  "exit_code": 0,
  "stdout": "…",
  "stderr": "…",
  "session_id": "mn_…",
  "errors": []
}
```

Branch on **`errors[]`** and **`exit_code`**. Parse **`stdout`** for pin-map content.

## Domain references

| Topic | Doc |
|-------|-----|
| GQL wire | MemNet `README.md`, `docs/grammar/`, [memnet-format](../../memnet-format/SKILL.md) |
| Wire / pin map notes | [wire-format.md](wire-format.md) |
| Atomisation | [atomisation.md](atomisation.md) |
| Coding memory | [coding-memory.md](coding-memory.md) |
| User input | [user-input-memory.md](user-input-memory.md) |

## Errors

| Symptom | Action |
|---------|--------|
| MemNet MCP tools absent from session catalog | Skip MemNet entirely: plain Markdown only (no TOON/TRON); do not call `pin_map` / `add` / `update` |
| `serve_required` | Under TCP: start `memnet serve` or switch to in-process |
| `session_not_found` | `session_open` / `session_load` or set `MEMNET_SESSION` |
| `id_exists` on add | Use `update` or mint with `NEW` |
| `not_found` on update | Use `add` or fix id from pin map |

## MUSTNOT

- Depend on novel-writer MCP extras (dropped from MemNet product).
- Recommend TOON/TRON for agent handoffs — use GQL wire or plain Markdown.
- Teach pipe `@TAG:…` as agent I/O.
- Call MemNet tools when they are not listed in the session MCP catalog.
