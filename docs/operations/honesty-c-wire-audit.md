# Honesty `c` wire audit (0.19.7)

**Date:** 2026-09-08. **Package:** Hatch **0.19.7** (same-method cut on **0.19**). Last published PyPI wheel remains **`memnet-llm==0.19.6`** until upload. Numbered extras **0.10–0.19** unchanged. No usage-method `b`. No claim `a`. No 0.20. No 1.0. No `rag_query`.

This note records catalog Snap leftover nicknames so snapshot save/load round-trips, plus Truncation honesty (0.19.6) and the 0.19.5 hid / nickname audit. Chat is not SSOT.

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

## Cut in 0.19.7

Catalog Snap wrote PKG without a leftover nickname (`CREATE (:PKG {qname, session, …})`). Snapshot emit is leftover `@TAG` with required id length 1–64, so empty id (`@PKG: ||qname|…`) failed `session_load` (`invalid_id`). Honesty: mint leftover nicknames on catalog emit; do not teach identity-by-id; do not change the goldfish loop.

## Cut in 0.19.6

Silent `context_pack[:max_rows]` was the same class of lie as silentPickOneRoot. Honesty: keep hard caps; highlight clip on the shaped emit (`emit_truncation`, CueConflict spelling). Agents cut a nested session rather than treating a clipped map as Shape.

## Cut in 0.19.5

`#148` documented `DROP_KEYS={id,hid}` but `wire.py` had no strip and `_emit_props` would print `hid` / `_memnet_hid` / `elementId` if those keys sat on `Record.fields` (cabinet leftover / poison). SSOT is now `memnet.models.SHAPE_DROP_KEYS`, applied on GQL emit and jsonl. Nickname `id` stays off **shaped read** only (`include_nickname=False`).
