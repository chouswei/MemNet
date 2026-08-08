# Fixture labels for shared-dialect golden harness (`docs/grammar/tools/tier_a.py`)

Harness / package names keep `tier_a` for continuity; fixtures teach **legal and illegal shapes** of the shared dialect (Write = display). **Do not delete** these fixtures when renaming prose — they are the precision benefit of `docs/grammar/`.

Product context: **MemNet 0.3.6+** — generic agent memory graph; examples favour SysML, PCBA, circuit nodal analysis, and domain-neutral formula EDGEs (not novel-writer / game-economy tags).

#
# Header marker (first lines):
#   # expect: parse-ok       — must parse; lint errors fail the test if present on *_good
#   # expect: parse-reject   — parse() must raise
#   # expect: lint-reject    — parse OK; lint() must yield at least one error
#
# Files without `# expect:`:
#   *_good.txt  → parse-ok (default)
#   *_bad.txt   → inferred: try parse; if OK then lint-reject else parse-reject
#   deprecated/10_compile_down_sketch.txt → skipped (legacy pipe illustration)
#
# Classification (R1):

| File | Class | Notes |
|------|-------|-------|
| 01_warm_slice_good | parse-ok | Pin-map (bare present); laws; edge ids |
| 02_mutate_create_good | parse-ok | `[NEW]` node mint; `NEW` edge-id mint |
| 03_mutate_settle_good | parse-ok | Known ids only |
| 04_pin_map_sysml_code_good | parse-ok | Pin map + edge ids (SysML / code / skills) |
| 05_bad_pipe_as_agent | parse-reject | `@TAG` pipe as agent I/O (illegal) |
| 06_bad_prose_blob | lint-reject | Soft prose/fat-field lint |
| 07_bad_embedded_relation | lint-reject | Comma id-list → use EDGE |
| 08_bad_corpus_dump | lint-reject | Corpus in field |
| 09_bad_mixed_dialect | parse-reject | Pipe line in batch |
| 10_compile_down_sketch | skip | Legacy pipe sketch — not shared-dialect input |
| 11_create_assigned_ids_good | parse-ok | Pin map/response with assigned ids |
| 12_bad_invent_create_ids | lint-reject | Invented ids; use `[NEW]` |
| 13_bad_new_on_update | parse-reject | `NEW` on `~` |
| 14_mutate_drop_edge_good | parse-ok | `- Eid` |
| 15_mutate_numeric_ops_good | parse-ok | `+=` / `-=` on `~` (update only) |
| 16_quoted_path_good | parse-ok | STRING escapes |
| 17_pin_map_pcba_ato_good | parse-ok | PCBA / `.ato` locators |
| 18_mutate_annotation_on_pcba_pin_good | parse-ok | Annotate ingest pins |
| 19_schema_map_good | parse-ok | `SCHEMA` session map (not NODE/EDGE) |
| 20_bad_numeric_op_on_create | lint-reject | `+=` / `-=` illegal on `+` create |
| 21_bad_numeric_op_delta_not_number | parse-reject | non-number after `+=` / `-=` |
| 22_inverting_amp_nodal_good | parse-ok | Circuit nodal slice + `derives` (Ohm, KCL, gain) |
| 23_formula_derives_good | parse-ok | Domain-neutral self-loop `derives` |
| 24_mutate_reid_good | parse-ok | Re-id node and edge on `~` |

**Worked example (prose + MCP seed):** [`docs/application-notes/examples/inverting-amplifier-memnet.md`](../application-notes/examples/inverting-amplifier-memnet.md).

`focus` / caps are **not** in body fixtures (MCP/CLI envelope only).

Run harness: `python -m pytest tests/grammar/test_tier_a_golden.py -v`

---

## MemNetLayer fixtures (`layer/`)

Proposed **1.x** multi-layer dialect ([`../memnet-multi-layer.md`](../memnet-multi-layer.md); ANTLR [`../antlr/MemNetLayer.g4`](../antlr/MemNetLayer.g4)). Same `# expect:` markers. Soft-validate: [`../tools/layer_soft_validate.py`](../tools/layer_soft_validate.py).

| File | Class | Notes |
|------|-------|-------|
| layer_01_bind_good | parse-ok | Port↔port bind (`--bind-->` / `--bind--`) |
| layer_02_relation_good | parse-ok | Bare-id relation; label = sense |
| layer_03_ports_law_alias_good | parse-ok | `ports=` + `@alias` in bag / `law=` |
| layer_04_named_fn_A_good | parse-ok | CST Sum + binds (A only; no B) |
| layer_05_bad_mixed_endpoints | lint-reject | Mixed port ↔ bare |
| layer_06_bad_law_on_edge | lint-reject | `law=` on EDGE |
| layer_07_bad_bag_on_law | lint-reject | Bag on denylist key `law=` |
| layer_08_bad_brace_depth3 | parse-reject | Brace nesting depth 3 (grammar cap 2) |
| layer_09_inv_amp_good | parse-ok | Inverting amp CST ports/law + binds (app-note twin) |

Run: `python -m pytest tests/grammar/test_memnet_layer_golden.py -v`
