# MemNet MCP policy

```text
Cursor (stdio) → memnet-mcp
                 ├─ in-process engine (default, single agent)
                 └─ TCP → memnet serve (MEMNET_MCP_TRANSPORT=tcp)
```

- Product **0.19.3**. Cue then `pin_map`. Write **`mutate`**. leftover `add`/`update` / `query_warm` / `anchor=` named leftover.
- Multitask **MUST NOT** use in-process MCP for a shared session.
- Live Agens claimed (0.7); Neo4j live claimed (0.14); RSV + Path-B ingest + `snap_model` + `export_pin_map` shipped.
- Novel-writer MCP is dropped.

## mcp.json (this repo / local)

```json
"memnet": {
  "command": "memnet-mcp",
  "args": [],
  "env": { "MEMNET_WORKSPACE_ROOT": "<checkout>" }
}
```

Do **not** set serve host/port unless `MEMNET_MCP_TRANSPORT=tcp`. This repo vendors the skill; optional extra HTTP `memnet-pi` is a human-machine path — not this cloud VM.

## Tools (product)

`serve_status`, `session_open` / `list` / `close` / `save` / `load` / `current`, `pin_map`, `find`, `mutate`, `snap_model`, `ingest_*`, `export_pin_map`, `import_slice`, `reserve` / `extend` / `release`, `read_list`, `housekeep_stats`, CapsPolicy `session_acl_*` opt-in.

leftover: `add`, `update`, `query_warm`, `query_walk`. No `read_get`.

Args: [tool-parameters.md](tool-parameters.md). Wire: [wire-format.md](wire-format.md).

## Errors

| Symptom | Action |
|---------|--------|
| Tools absent from catalog | Skip MemNet; plain Markdown |
| `serve_required` | Start `memnet serve` or stay in-process |
| `session_not_found` | `session_open` / `session_load` |
| `no_map` | Pass `map_file` / `map_lines` |
| `limit_exceeded` | `session_list` for `sessions|n/max`; `session_close` unused strata |

## MUST NOT

- Teach leftover NEW / leftover `--anchor` as TARGET.
- `rag_query`, Layer, pipe `@TAG`, TOON as agent I/O.
- Call tools that are not in the session catalog.
