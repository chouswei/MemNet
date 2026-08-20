# MCP tools <-> MemNet GQL wire

**Audience:** model. Package SSOT: MemNet `parts/memnet-mcp/software/memnet_mcp/server.py` (0.9 tool set). Wire shapes: [memnet-format](../../memnet-format/SKILL.md); product wire: `docs/grammar/gql-wire-profile.md`. Product **`memnet-llm` 0.19.0**.

MCP does **not** replace the grammar. Tools open a session and move **GQL / openCypher-shaped text** (or engine-rendered shaped subgraph) through a JSON envelope.

## Envelope vs wire

| Plane | Role |
|-------|------|
| MCP JSON `{exit_code, stdout, stderr, session_id, errors}` | Transport / CLI adapter result |
| `stdout` or `wire_lines` text | **GQL wire** (shaped pin_map or openCypher-shaped mutate) |
| MemNet grammar / engine | What those statements must look like |

`serve_status` is the only tool that returns a non-envelope JSON object (`{running, host, port}`).

## Full map (all tools)

| Tool | Purpose | Wire role | Dialect payload |
|------|---------|-----------|-----------------|
| `serve_status` | Probe TCP serve | Transport only | None |
| `session_open` | New session + tag map | Lifecycle + schema | `map_lines`: `SCHEMA Kind ; fields=id …`; `seed_lines` = optional openCypher-shaped seed (LAW01–05 auto) |
| `session_current` | Session id / TTL | Lifecycle | None |
| `session_save` | Write snapshot file | Snapshot | None (file holds graph) |
| `session_load` | Restore snapshot | Snapshot | None |
| `pin_map` | **Live shaped subgraph** | Primary **read** | `stdout`: neighbourhood; optional `view`, `anchors` |
| `query_warm` | Deprecated alias for `pin_map` | Same as `pin_map` | Same (incl. `view` / `anchors`) |
| `find` | Bounded seed lookup | Cue when ego unknown | Required `limit`; then pin_map. Not RAG. |
| `query_walk` | Hop listing | Debug read | Walk lines — not the pin-map agent loop |
| `add` | Create atoms | Mutate **create** | `wire_lines`: CREATE / NEW mint; `llm_id` under RSV |
| `update` | Replace / drop | Mutate **patch/drop** | `wire_lines`: MATCH/SET/DELETE on known ids |
| `ingest_sysml` / `ingest_codebase` / `ingest_pcba` / `ingest_skills` | Path-B artefact ingest | **Shipped** | Locator ids; no client NEW |
| `import_slice` | Session-slice absorb | Path-B import | Optional CheapLlmImportGuard |
| `reserve` / `extend` / `release` | Neighbourhood RSV | **Shipped** | `llm_id` + TTL; pin_map may show `:RSV` |
| `session_acl_grant` / `session_acl_bind` / `session_acl_enable` | CapsPolicy ACL | Opt-in | Full ACL modes still design |
| `read_get` | One row by id | Lookup | One rendered row |
| `read_list` | Enumerate by label / where | Lookup | Many rows |
| `housekeep_stats` | Counts vs caps | Housekeeping | Stats text / envelope |

**Still design:** full session ACL modes / roles / `session_token`. RSV + Path-B ingest are **shipped**. See MemNet `docs/grammar/memnet-neighbourhood-reserve.md`.

## Shapes agents must recognise

| Situation | Tool | Shape |
|-----------|------|-------|
| Read this turn | `pin_map` | Shaped subgraph present — **no** exploratory unbounded walk |
| Nodes of a relationship | `read_get` or pin_map rel | Parse endpoints — those values **are** the node ids; no extra tool |
| Create | `add` | `CREATE (n:Kind {id: 'NEW', …})` / `CREATE (a)-[:TYPE {id: 'NEW'}]->(b)` |
| Patch | `update` | `MATCH (n {id: $id}) SET n.…` |
| Re-id | `update` | `MATCH (n {id: $old}) SET n.id = $new` (optional merge; nodes only) |
| Patch / drop rel | `update` | MATCH by `{id}` or endpoints+type; SET or DELETE |
| Validate shapes | (offline) | MemNet `docs/grammar/` fixtures — not an MCP tool |

## Why names look "weird"

| MCP name | Wire vocabulary | Keep API? |
|----------|-----------------|-----------|
| `pin_map` | live **shaped subgraph** | **Primary** read tool |
| `query_warm` | same as `pin_map` | Yes — deprecated alias |
| `add` / `update` | CREATE / MATCH-SET-DELETE | Yes — ops live in `wire_lines` |
| `serve_status` | in-process needs no serve | Yes — optional under default transport |
| Missing novel tools | product dropped novel-writer | Expected |

## Config note (user pack)

This pack's **Cursor** entry is HTTP **`memnet-pi`** -> `http://10.0.0.10:18766/mcp`. Do not also enable a stdio `memnet` server in the same mcp.json (doubles the tool list). Engine version = Pi serve / HTTP MCP process, not a local wrapper.

Cross-ref: [tool-parameters.md](tool-parameters.md) · [mcp-policy.md](mcp-policy.md) · MemNet `docs/grammar/`
