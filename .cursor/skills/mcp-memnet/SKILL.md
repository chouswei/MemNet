---
name: mcp-memnet
description: >-
  MemNet MCP tools: cue then pin_map, GQL mutate, session, ingest, snap_model,
  export_pin_map. Triggers: memnet mcp, pin_map, mutate, session_open, find,
  ingest_sysml, snap_model, export_pin_map, reserve, RSV.
metadata:
  pattern: tool-wrapper
  version: "7.1"
  domain: memnet
  product: memnet-llm==0.19.0
token_guardrails: |
  - Product read is pin_map from a cue (kind / locators / keyword / session). leftover anchor= is leftover.
  - Product write is mutate (CREATE/MERGE/SET/DELETE). leftover add/update / id:'NEW' are leftover façades.
  - Parse envelope stdout. Wire SSOT: memnet-format + docs/grammar/gql-wire-profile.md.
---

# MemNet MCP

**Use** MemNet via MCP. Doctrine: `docs/SHAPE.md`, `docs/LLM-GUIDE.md`. Wire: [memnet-format](../memnet-format/SKILL.md). Nested interiors: [memnet-nested-sessions](../memnet-nested-sessions/SKILL.md). Tool SSOT: `parts/memnet-mcp/software/memnet_mcp/server.py`.

Product **0.19.0**. PyPI **`memnet-llm==0.19.0`**. Arg **`session`** (not `session_id`). Novel-writer is out of scope.

## Transport

| Role | How |
|------|-----|
| Single agent | In-process `memnet-mcp` (stdio); no serve |
| Shared / Multitask | TCP `:18765` or streamable-http; load [memnet-multitask](../memnet-multitask/SKILL.md) |

`serve_status` is a TCP probe. Skip it under default in-process.

## Agent loop

```text
cue / find → pin_map → reason → mutate → pin_map
```

1. **Cue** — `kind` / `locators` (`qname=`, `path=`, …) / `keyword` / nickname `cue`. Empty cue = **session outline** (0.11). If ego unknown: `find(limit=…)` then `pin_map` from labels+props. Prefer one live `TSK_*`. When \(|Q|>1\), CueConflict — do not pick one root.
2. **`pin_map`** — one \(S\) per generate. Drop the prior map next turn. leftover `anchor=` / `anchors=` are leftover nicknames, not TARGET law.
3. **`mutate`** — sparse GraphElement `CREATE` / `MATCH`…`SET`/`DELETE`. No leftover `id:'NEW'` mint.
4. Persist if needed: `session_save` (file) or live cabinet (0.7 Agens / 0.14 Neo4j). Agents MUST NOT talk Bolt.

**MCP missing:** skip MemNet; plain Markdown only.

## Product tools

| Tool | Role |
|------|------|
| `session_open` | Map required (`map_file` / `map_lines`). This repo SysML: `schema.sysml.example.txt` |
| `session_list` | Live session ids (catalog strata) |
| `session_save` / `session_load` / `session_current` | Snapshot / resume |
| `pin_map` | Primary read. Cue params above. Empty q = outline. `view=shell` is grain on a seed, not outline |
| `find` | Bounded seed (`limit` required). Not RAG |
| `mutate` | Product Commit |
| `snap_model` | One load tree → catalog + interiors (`session=` + `qname=`). Look loop: nested-sessions skill |
| `ingest_sysml` / `ingest_codebase` / `ingest_pcba` / `ingest_skills` | Path-B locators into **this** session (1→1). Not Snap. Not export |
| `export_pin_map` | Write out a cue `pin_map` as GQL. Not ingest. Not Absorb |
| `import_slice` | Absorb a **slice** (not a whole \(S\)) |
| `reserve` / `extend` / `release` | RSV; pass `llm_id` on mutate |
| `read_list` | Enumerate by kind / where |
| `housekeep_stats` | Caps |

## leftover (do not teach as product)

| Name | Status |
|------|--------|
| `add` / `update` | leftover façades; still registered. Prefer **`mutate`** |
| `query_warm` | leftover alias of `pin_map` |
| `query_walk` | leftover hop debug |
| `anchor=` / `--anchor` | leftover nickname |
| `read_get` | **not** on this MCP |
| `id:'NEW'` | leftover mint; not product Commit |

Args: [references/tool-parameters.md](references/tool-parameters.md). Policy: [references/mcp-policy.md](references/mcp-policy.md). Map: [references/tool-grammar.md](references/tool-grammar.md).

## MUST NOT

- `rag_query` / ANN of \(S\) / dump \(S\) / stack \(N\) nested maps in one generate.
- Invent ids already on the map. Pipe `@TAG` / Layer / TOON as agent I/O.
- Treat ingest as pin-map export. Restore novel-writer tools.
