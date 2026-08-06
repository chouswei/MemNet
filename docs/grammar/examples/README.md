# Fixture labels for shared-dialect golden harness (`docs/grammar/tools/tier_a.py`)

Harness / package names keep `tier_a` for continuity; fixtures teach **legal and illegal shapes** of the shared dialect (Write = display). **Do not delete** these fixtures when renaming prose — they are the precision benefit of `docs/grammar/`.

#
# Header marker (first lines):
#   # expect: parse-ok       — must parse; lint errors fail the test if present on *_good
#   # expect: parse-reject   — parse() must raise
#   # expect: lint-reject    — parse OK; lint() must yield at least one error
#
# Files without `# expect:`:
#   *_good.txt  → parse-ok (default)
#   *_bad.txt   → inferred: try parse; if OK then lint-reject else parse-reject
#   10_compile_down_sketch.txt → skipped (legacy pipe illustration, not shared-dialect input)
#
# Classification (R1):

| File | Class | Notes |
|------|-------|-------|
| 01_warm_slice_good | parse-ok | Pin-map (bare present); laws without leading `;`; edge ids |
| 02_mutate_create_good | parse-ok | `[NEW]` node mint; `NEW` edge-id mint |
| 03_mutate_settle_good | parse-ok | Known ids only |
| 04_pin_map_sysml_code_good | parse-ok | Pin map + edge ids |
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

focus / caps are **not** in body fixtures (MCP/CLI envelope only).
