# MemNet MCP — tool parameters

MCP server key: typically **`memnet`** in Cursor MCP config (user pack primary id **`memnet-pi`**). Tools return **JSON text** (parse as object) unless noted. Product: **`memnet-llm` 0.9.0**. PyPI wheel is still **0.4.6** — engine version = remote serve / repo install. User-pack store: TCP **`10.0.0.10:18765`**; Cursor entry: HTTP **`http://10.0.0.10:18766/mcp`**.

## Invoke order (typical session)

1. **`serve_status`** — optional under default in-process; required when using TCP/`memnet serve`
2. **`session_open`** — `map_lines` (or `map_file`); store `session_id`
3. **`find`** — when the ego id is unknown (`limit` required); skip if the anchor is already known
4. **`pin_map`** — every turn; `anchor` and/or `anchors` (live **pin map**; `query_warm` is legacy alias)
5. **`add`** / **`update`** — GQL mutate via `wire_lines` (pass `llm_id` under RSV)
6. **`session_current`** — optional; pass `session` or set `MEMNET_SESSION`
7. **`read_get`** / **`read_list`** — single-row or enumerate-by-tag
8. **`housekeep_stats`** — caps / row counts when the graph grows

Path-B: **`ingest_*`** for artefact pins; **`import_slice`** for session-to-session absorb. Envelope and errors: [mcp-policy.md](mcp-policy.md). Atomisation: [atomisation.md](atomisation.md). Tool <-> grammar: [tool-grammar.md](tool-grammar.md).

## Tools

| Tool | Required args | Optional args | Notes |
|------|---------------|---------------|-------|
| `serve_status` | — | — | `{ running, host, port }` — TCP probe |
| `session_open` | `map_lines` **or** `map_file` | `ttl`, `seed_lines`, `allow_new_relation` | Auto-seeds LAW01–LAW05 |
| `session_save` | `file` | `session` | Snapshot to disk |
| `session_load` | `file` | `keep_id`, `ttl` | Resume; no prior session required |
| `session_current` | — | `session` | Needs `session` or `MEMNET_SESSION` |
| `pin_map` | `anchor` **or** `anchors` | `depth` (2), `max_rows` (50), `view`, `session`, `caller` | **Primary read**; `view=shell\|interior`; multi-ego via `anchors` (one budget, one LAW) |
| `query_warm` | same as `pin_map` | same | Deprecated alias for `pin_map` |
| `find` | `limit` | `kind`, `locators`, `keyword`, `session` | Seed nodes only; then pin_map a copied id. Not RAG. |
| `query_walk` | `anchor` | `depth`, `max_rows`, `session` | Hop lines for debug — not the agent pin-map loop |
| `add` | `wire_lines` | `allow_new_relation`, `agent`, `session`, `llm_id`, `caller`, `mission_id`, `lease`, `write_scope` | Create; GQL `CREATE` / `id:'NEW'` |
| `update` | `wire_lines` | same as `add` | Patch/drop; known ids only |
| `ingest_sysml` | `path` | `max_nodes`, `max_files`, `root`, `dry_run`, `session` | Path-B SysML pins |
| `ingest_codebase` | `path` | same | MOD/SYM locators |
| `ingest_pcba` | `path` | same | `.ato` CMP/NET/PIN |
| `ingest_skills` | `path` | same | SKL/RUL locators |
| `import_slice` | `from_session`, `anchors` | `id_policy`, `depth`, `max_rows`, `view`, `enable_guard`, `session` | Path-B absorb; optional CheapLlmImportGuard |
| `reserve` | `anchor`, `llm_id` | `depth`, `ttl_s`, `session` | RSV lease |
| `extend` | `llm_id` | `rid` or `anchor`, `ttl_s`, `session` | Extend RSV |
| `release` | `llm_id` | `rid` or `anchor`, `session` | Drop RSV |
| `session_acl_grant` | `caller` | `pin_map`, `mutate`, `write_scope`, `session` | CapsPolicy who |
| `session_acl_bind` | `mission_id`, `lease` | `session` | Optional bind |
| `session_acl_enable` | — | `session` | Turns ACL gates on |
| `read_get` | `id` | `session` | One row by id |
| `read_list` | — | `tag`, `active_only`, `where`, `session` | Enumerate without prior ids |
| `housekeep_stats` | — | `session` | Counts / caps |

## Response envelope (all tools except `serve_status`)

```json
{
  "exit_code": 0,
  "stdout": "…pin map…",
  "stderr": "…",
  "session_id": "mn_…",
  "errors": []
}
```

- Branch on **`exit_code`** and **`errors[]`**
- Parse **`stdout`** for the live pin map (shaped subgraph)
- **`wire_lines`** are joined with `\n` before send

## Environment

| Variable | Purpose |
|----------|---------|
| `MEMNET_MCP_TRANSPORT` | User pack HTTP MCP on Pi should be **`tcp`** so Cursor shares the serve graph. Local single-agent may stay in-process. |
| `MEMNET_SERVE_HOST` / `MEMNET_SERVE_PORT` | User pack: **`10.0.0.10`** / **`18765`**. (Library default: `127.0.0.1:18765`.) |
| `MEMNET_SESSION` | Default session id after open/load |
| `MEMNET_AGENSGRAPH_URL` | Live cabinet (0.7 claimed) — optional |
| `MEMNET_NEO4J_URL` | Neo4j client extra (0.9); live **unclaimed**. If both cabinet URLs set, `MEMNET_DURABLE_BACKEND` must pick one. |
| `MEMNET_IMPORT_GUARD_API_KEY` | Optional CheapLlmImportGuard on `import_slice` |

Set TCP vars on the **Pi HTTP MCP process**, not as a second Cursor `command` server. Restart `memnet-pi` after mcp.json changes.

## wire_lines

openCypher-shaped mutate (GQL teach — not pipe):

```cypher
CREATE (c:CLM {id: 'NEW', type: 'decision', code: 'bitrate cap 2000 bps', recycle: 'persistent'})
MATCH (t {id: $tid}) SET t.status = 'in_progress', t.recycle = 'persistent'
CREATE (a)-[:HELPS {id: 'NEW', note: 'labour', recycle: 'persistent'}]->(b)
```

Batch many statements in one `add`/`update` call. Copy minted ids from the next `pin_map`.
