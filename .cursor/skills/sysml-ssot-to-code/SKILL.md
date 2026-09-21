---
name: sysml-ssot-to-code
description: >-
  Track MemNet implementation from SysML SSOT to live Python modules.
  Triggers: track implementation, SSOT to code, SoftwareAllocate,
  MN-REQ-06.7, allocate map, which file realises, implementation.sysml.
metadata:
  pattern: pipeline
  domain: sysml,memnet
  version: "1.0"
  product: "0.19.11"
  pairs_with: [sysml-modeling-workflow, memnet-reference, sysml-gql, mcp-memnet]
token_guardrails: |
  - Ledger: implementation.sysml + outputs/ssot-to-code-allocate-map.md.
  - MUST NOT invent sysmledge path, N-server, or a second drifting code map.
---

# SSOT → code (implementation tracker)

This MemNet checkout. Logical parts live in `sysml-models/models/deploy.sysml`. **Which file realises them** is `SoftwareAllocate` in `sysml-models/models/implementation.sysml` plus the derived ledger `sysml-models/outputs/ssot-to-code-allocate-map.md` (`ImplementationTracker`; MN-REQ-06.7 / MN-VER-06-S04).

**Not** codebase `:MOD` / `:SYM` snap. **Not** cousin sysmledge. **Not** N-server (#47). One Hatch wheel (`memnet-llm`) for many hosts. MemNet MCP stays tip/ops (`tipIsFace=false`). Hatch **0.19.11** honesty `c`.

## When loaded

Ask which file is a SSOT part (`MutateGate`, `MemNetMcpServer`, `Peak_L`, …); ship or move a module; track implementation.

If the task is only **using** MemNet, stop and load [memnet-use](../memnet-use/SKILL.md). Engine behaviour edits still follow [memnet-reference](../memnet-reference/SKILL.md) **after** the allocate row names the path.

## MUST

1. Open the allocate map (or cue `kind=TSK` `locators=['goal=TSK_model_alloc']` then `pin_map`).
2. Match the logical SSOT path to `path` / `pyName`.
3. When a module ships or moves: edit `implementation.sysml` first, sync the map, run `pytest tests/test_sysml_ssot_to_code.py`.
4. Align engine/MCP behaviour code only when the model says so.
5. Keep `sysmlEdgeTracked=false` / `mustNotInventUploadBind`.

## MUST NOT

- Invent a `sysmledge` / SysMLEdge product-face path in this repo.
- Duplicate a second code-map table in skills that drifts from the ledger.
- Treat `ingest_codebase` / `:MOD` snap as SoftwareAllocate SSOT.
- Load pack-only `sysml-allocate-generator` — that folder is not vendored here.
- Invent N-server federation (#47).
- Bump Hatch or SemVer `b` for allocate honesty.

## Proof

`pytest tests/test_sysml_ssot_to_code.py` — every in-repo `path=` exists; every `SoftwareAllocate` name is on the map.

## Related

[sysml-modeling-workflow](../sysml-modeling-workflow/SKILL.md) · [memnet-reference](../memnet-reference/SKILL.md) · [sysml-gql](../sysml-gql/SKILL.md) · case study `sysml-models/outputs/ssot-to-code-allocate-case-study.md`
