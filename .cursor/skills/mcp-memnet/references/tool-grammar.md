# MCP tools ↔ MemNet GQL wire

SSOT: `parts/memnet-mcp/software/memnet_mcp/server.py`. Product **0.19.2**. Wire: [memnet-format](../../memnet-format/SKILL.md); `docs/grammar/gql-wire-profile.md`.

Envelope JSON is transport. **`stdout` / `wire_lines`** carry GQL. `serve_status` is the only non-envelope JSON.

| Tool | Purpose | Wire |
|------|---------|------|
| `session_open` | Map + optional seed | `SCHEMA …`; optional CREATE seed |
| `session_list` | Live ids | text |
| `pin_map` | Primary read | shaped subgraph (empty q = outline) |
| `find` | Seed | bounded MATCH |
| `mutate` | Product Commit | CREATE / MERGE / SET / DELETE |
| `snap_model` | Catalog + interiors | locators `session=` + `qname=` |
| `ingest_*` | Path-B into **this** \(S\) | locators; no leftover NEW |
| `export_pin_map` | Cue map write-out | shaped GQL; not Absorb |
| `import_slice` | Slice Absorb | pattern match |
| `reserve` / `extend` / `release` | RSV | `:RSV` present |
| `read_list` | Enumerate | rows |

leftover: `query_warm` (= `pin_map`), `add`/`update` (façades), `query_walk`. **No** `read_get`. leftover `anchor=` is leftover.

| Situation | Tool |
|-----------|------|
| This turn's Shape | `pin_map` from cue |
| Create / patch | `mutate` |
| Nested interior | `snap_model` then `pin_map(session=…)` — [memnet-nested-sessions](../../memnet-nested-sessions/SKILL.md) |
