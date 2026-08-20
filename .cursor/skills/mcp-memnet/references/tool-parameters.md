# MemNet MCP — tool parameters

Product **`memnet-llm` 0.19.1**. Hatch **0.19.1**; last published PyPI wheel is **0.19.0** until upload. Tools return JSON text. Arg **`session`** (not `session_id`). SSOT: `parts/memnet-mcp/software/memnet_mcp/server.py`.

User-pack Pi (`10.0.0.10`) is optional on a human machine — not this cloud VM.

## Invoke order

1. `serve_status` — TCP only; skip under in-process
2. `session_open` — `map_file` or `map_lines`
3. `find` if ego unknown (`limit` required)
4. `pin_map` every turn from a **cue**
5. `mutate` (`wire_lines`; `llm_id` under RSV)
6. Optional: `session_save` / `export_pin_map` / `housekeep_stats`

Path-B: `ingest_*` into the current session. Catalog Snap: `snap_model`. Join a slice: `import_slice`. Envelope: [mcp-policy.md](mcp-policy.md). Map: [tool-grammar.md](tool-grammar.md).

## Tools

| Tool | Required | Optional | Notes |
|------|----------|----------|-------|
| `serve_status` | — | — | `{running, host, port}` |
| `session_open` | `map_lines` **or** `map_file` | `ttl`, `seed_lines`, `allow_new_relation` | SysML map: `schema.sysml.example.txt` |
| `session_list` | — | — | Live ids |
| `session_save` | `file` | `session` | Snapshot |
| `session_load` | `file` | `keep_id`, `ttl` | Resume |
| `session_current` | — | `session` | |
| `pin_map` | cue: `kind` / `locators` / `keyword` / `cue` / empty outline | `depth`, `max_rows`, `view`, `session`, leftover `anchor`/`anchors` | Primary read |
| `find` | `limit` | `kind`, `locators`, `keyword`, `session` | Seeds only |
| `mutate` | `wire_lines` | `allow_new_relation`, `session`, `llm_id`, `caller`, `mission_id`, `lease`, `write_scope` | Product Commit |
| `snap_model` | `root` | `map_file`, `max_nodes`, `max_files`, `ttl` | Catalog + interiors |
| `ingest_sysml` | `path` | `max_nodes`, `max_files`, `root`, `dry_run`, `session` | 1 path → this session |
| `ingest_codebase` / `ingest_pcba` / `ingest_skills` | `path` | same family | Locator pins |
| `export_pin_map` | same cue family as `pin_map` | `out`, `view`, `session` | Cue GQL write-out |
| `import_slice` | `from_session`, `anchors` | `depth`, `max_rows`, `view`, `session` | Slice Absorb |
| `reserve` | leftover nick `anchor`, `llm_id` | `depth`, `ttl_s`, `session` | RSV |
| `extend` / `release` | `llm_id` | `rid` or leftover nick, `session` | |
| `read_list` | — | `tag`, `active_only`, `where`, `session` | Enumerate |
| `housekeep_stats` | — | `session` | |

leftover façades (registered, not TARGET): `add`, `update`, `query_warm`, `query_walk`. **No** `read_get`. leftover `id_policy` on import is leftover.

## Envelope (all except `serve_status`)

```json
{ "exit_code": 0, "stdout": "…", "stderr": "…", "session_id": "mn_…", "errors": [] }
```

Parse **`stdout`**. Join `wire_lines` with `\n`.

## Environment

| Variable | Purpose |
|----------|---------|
| `MEMNET_MCP_TRANSPORT` | `tcp` when sharing a serve graph |
| `MEMNET_SERVE_HOST` / `MEMNET_SERVE_PORT` | Serve bind (library default `127.0.0.1:18765`) |
| `MEMNET_SESSION` | Default session after open/load |
| `MEMNET_AGENSGRAPH_URL` | Live Agens (0.7) |
| `MEMNET_NEO4J_URL` | Neo4j extra; live claimed **0.14**. Both URLs need `MEMNET_DURABLE_BACKEND` |

## wire_lines (product)

```cypher
CREATE (t:TSK {goal:'Clear warehouse', status:'in_progress'})
MATCH (t:TSK {goal:'Clear warehouse'}) SET t.status = 'settled', t.recycle = 'delete_on_settle'
```
