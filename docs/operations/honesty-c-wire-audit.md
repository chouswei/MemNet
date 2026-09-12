# Honesty `c` wire audit (0.19.9)

**Date:** 2026-09-12. **Package:** Hatch **0.19.9** (same-method cut on **0.19**). Last published PyPI wheel remains **`memnet-llm==0.19.6`** until upload. Numbered extras **0.10–0.19** unchanged. No usage-method `b`. No claim `a`. No 0.20. No 1.0. No `rag_query`.

This note records Path-B SysML `connection` → CON (0.19.9), leftover nicknames on **all** snapshot records (0.19.8), camelCase product relation types on leftover pipe load, Truncation honesty (0.19.6), and the 0.19.5 hid / nickname audit. Chat is not SSOT. Teach already mapped connection to `:CON`; ingest code was wrong — this cut is honesty `c`, not a new goldfish step.

## Surfaces checked (0.19.9 Path-B SysML CON)

| Surface | Result |
|---------|--------|
| `PinMapIngest_Sysml` `_KIND_FOR_KW` | `connection def` / `connection` / `link def` / `link` → CON. Not PRT. |
| `_DEF_HEAD` | Named bare `connection` / `link` usages project. Anonymous `#derivation connection {` still skipped (no name). |
| CON props | `kind` = `connectionDef` / `connectionUsage` / `linkUsage`. `sysml_kind` stays `connection_def` / `connection`. |
| Cheap rels | `typedBy` (usage → def), `hasPort` (def end → POR), `connects` (`::>` / `connect … to`). Nest `contains` / `satisfies` unchanged. |
| Map | `schema.sysml.example.txt` SCHEMA CON. Canonical kind was already CON. |
| `pin_map` | Cue `kind=CON` + `name` / `qname`. Loop still `cue → pin_map → mutate`. |

Regression: `tests/test_pin_map_ingest.py` (`test_project_sysml_connection_def_is_con`, `test_ingest_sysml_connection_rels`, `test_ingest_connections_sysml_con_count`).

**Precedent (CON as node).** Schummer & Hyba (2022) map each SysML connector to a labelled-property-graph **`:HYPERNODE`** — a connector *node*, not a bare binary edge — because an LPG edge joins exactly two vertices (Florian Schummer & Maximillian Hyba, *An Approach for System Analysis with MBSE and Graph Data Engineering*, [arXiv:2201.06363](https://arxiv.org/abs/2201.06363); HTML [v1](https://arxiv.org/html/2201.06363v1); *Data-Centric Engineering*). MemNet Path-B is the same schema class: `connection def` / `connection` / `link` project as node kind **CON** (`connectionDef` / `connectionUsage` / `linkUsage`); ends are edges (`connects`, `hasPort`, `typedBy`). CON is not a mission `TSK`.

## Surfaces checked (0.19.8 snapshot leftover nick + `:inFile`)

| Surface | Result |
|---------|--------|
| `snapshot_text` / `session_save` | Every `# memnet-snapshot-v1` record has leftover nickname length 1–64. Empty GraphElement `id` mints `sn_<kind>_<digest>` from hid. EDG `src`/`dist` hid rewritten to that nick. SHALL NOT mint `TSK_model_*`. |
| `parse_line` / `session_load` | Empty first field mints the same leftover nick class. Old foam empty-id lines no longer `invalid_id`. |
| Relation pattern | `RELATION_PATTERN` allows camelCase (`inFile`, `declaredIn`, `typedBy`, `memberOf`). Seed includes product verbs. |
| `pin_map` | Still kind + locators. Nickname off shaped read (0.19.4). Hid off emit (0.19.5). |

Regression: `tests/test_snapshot.py` (`test_mission_empty_nick_infile_save_load`). Catalog PKG mint (0.19.7) remains `tests/test_catalog_snap.py`.

## Surfaces checked (0.19.7 catalog leftover nick)

| Surface | Result |
|---------|--------|
| `snap_model` `_commit_catalog` | Catalog PKG CREATE carries leftover `id: 'pkg_…'` (slug from `qname` / `kind_band`, hash if over 64). Not GraphElement identity. |
| Snapshot `# memnet-snapshot-v1` | `@PKG:` first field length 1–64. `session_save` → `session_load` parses. |
| `pin_map` on catalog | Still kind + `qname` / locators. Nickname off shaped read (0.19.4). |
| Catalog vs mission | SHALL NOT mint `TSK_model_*`. Interiors unchanged (Path-B CREATE still locator-only). |

Regression: `tests/test_catalog_snap.py` (`test_catalog_session_save_load_roundtrip`).

## Surfaces checked (0.19.6 Truncation)

| Surface | Result |
|---------|--------|
| `PinMapComposer` / CLI `query pin-map` / leftover `query warm` | When ShapeWalk clips (`max_rows` \(M\), hop \(k\) vs `max_depth`, fan-out, `view=shell`), emit `## Truncation truncated=true M=… omitted=… reason=…`. When the offer fits, the mark is absent. Caps stay hard. |
| Outline (empty \(q\)) | Same mark when \(M\) clips the census (per-kind `LIMIT=` stays on `## outline`). |
| `export_pin_map` | Body is composer text; header MAY add `truncated=1`. |
| MCP `pin_map` JSON envelope | `stdout` is CLI pin-map (Truncation in `stdout`, CueConflict family). Not a second JSON dialect. |
| `SHAPE_DROP_KEYS` / hid | Unchanged from 0.19.5. Truncation lines carry no hid. |

Regression: `tests/test_pin_map_truncation.py`. Hid regression remains `tests/test_honesty_c_wire.py`.

## Surfaces checked (0.19.5 hid)

| Surface | Result |
|---------|--------|
| `PinMapComposer` / CLI `query pin-map` / leftover `query warm` | Nickname `id` already off (0.19.4). Store-identity keys now dropped by `SHAPE_DROP_KEYS` even if present in `Record.fields`. |
| Outline, CueConflict, `query find` / MCP `find` | Same composer / `emit_gql` / `record_to_gql_line` path. PASS after drop. |
| `export_pin_map` / CLI `export pin-map` / MCP `export_pin_map` | Body is composer text. PASS. |
| MCP `pin_map` JSON envelope | `stdout` is CLI pin-map. PASS (regression in `tests/test_honesty_c_wire.py`). |
| Mutate / GQL ack | `emit_item(..., as_mutate=True)` may echo nickname `id` the agent wrote. Hid / `_elN` / `_memnet_hid` / `elementId` stripped via `_emit_props`. |
| jsonl (`MemStore.to_jsonl_rows`) | `Record.hid` already `exclude=True`. Field copies of `SHAPE_DROP_KEYS` now popped. |
| Rank / offer order | `RANK_EXCLUDE_KEYS` = `{id, src, dist}` ∪ `SHAPE_DROP_KEYS`. Seed-first in `view=shell` still prefers the cued element, not peer hid. |
| RSV product errors | Were leaking hid (`id {_elN} already held…`). Now `anchor=` + `llm_id` only. Pin-map `## Reserves` already omitted held ids. |
| Cabinet `_memnet_hid` MERGE | Internal only. Tests in `tests/test_durable_store.py` still require it on adapter Cypher. |

## Allowed leftovers (not this cut)

- Cue / find / `match_nickname` **lookup** by nickname the agent already holds.
- leftover CLI `query walk` `@WALK:` hops still use endpoint **hids** (leftover hop debug, not goldfish). leftover `read list` / `query context` pipe `@TAG` may show nickname `id` as the first field.
- leftover `add`/`update` façades; leftover `--anchor`.
- Snapshot files (`# memnet-snapshot-v1`) are operator save/load, not `pin_map`.
- leftover `query context` pipe emit still silent-clips (not goldfish).

## Cut in 0.19.9

Teach (`sysml-gql`, `sysml-memnet-patterns`) already said SysML connection is `:CON`. Path-B ingest mapped `connection def` to PRT and skipped named `connection` usages, so Foam connection defs and deploy usages were CON=0. Honesty: project CON with the closed `kind` enum; emit cheap end rels when names exist; do not change the goldfish loop.

## Cut in 0.19.8

Mission `CREATE (:TSK {goal})` (and PRT/SYM/MOD/…) still had empty leftover `id` on snapshot emit after 0.19.7 catalog PKG mint. Load failed `invalid_id`. Hand-mint then failed `invalid_relation` on `:inFile` (camelCase vs lowercase-only pattern). Honesty: mint leftover nicks on **all** snapshot records (and on empty-id parse); allow product camelCase relation types on leftover pipe; do not teach identity-by-id; do not change the goldfish loop.

## Cut in 0.19.7

Catalog Snap wrote PKG without a leftover nickname (`CREATE (:PKG {qname, session, …})`). Snapshot emit is leftover `@TAG` with required id length 1–64, so empty id (`@PKG: ||qname|…`) failed `session_load` (`invalid_id`). Honesty: mint leftover nicknames on catalog emit; do not teach identity-by-id; do not change the goldfish loop.

## Cut in 0.19.6

Silent `context_pack[:max_rows]` was the same class of lie as silentPickOneRoot. Honesty: keep hard caps; highlight clip on the shaped emit (`emit_truncation`, CueConflict spelling). Agents cut a nested session rather than treating a clipped map as Shape.

## Cut in 0.19.5

`#148` documented `DROP_KEYS={id,hid}` but `wire.py` had no strip and `_emit_props` would print `hid` / `_memnet_hid` / `elementId` if those keys sat on `Record.fields` (cabinet leftover / poison). SSOT is now `memnet.models.SHAPE_DROP_KEYS`, applied on GQL emit and jsonl. Nickname `id` stays off **shaped read** only (`include_nickname=False`).
