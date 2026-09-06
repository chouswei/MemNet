# Honesty `c` wire audit (0.19.5)

**Date:** 2026-09-06. **Package:** Hatch **0.19.5** (same-method cut on **0.19**). Last published PyPI wheel remains **`memnet-llm==0.19.4`** until upload. Numbered extras **0.10–0.19** unchanged. No usage-method `b`. No claim `a`. No 0.20. No 1.0. No `rag_query`.

This note records the hot-path audit after [#148](https://github.com/chouswei/MemNet/pull/148) (nickname off `pin_map`) and [#147](https://github.com/chouswei/MemNet/pull/147) (observable rank). Chat is not SSOT.

## Surfaces checked

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

## Cut in 0.19.5

`#148` documented `DROP_KEYS={id,hid}` but `wire.py` had no strip and `_emit_props` would print `hid` / `_memnet_hid` / `elementId` if those keys sat on `Record.fields` (cabinet leftover / poison). SSOT is now `memnet.models.SHAPE_DROP_KEYS`, applied on GQL emit and jsonl. Nickname `id` stays off **shaped read** only (`include_nickname=False`).

Regression: `tests/test_honesty_c_wire.py`.
