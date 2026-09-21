---
name: memnet-reference
description: >-
  Load when developing the MemNet product repository: engine, generic MCP,
  shared-dialect grammar, SysML models, packaging, CI, and contributor layout.
  Triggers: MemNet development, memnet engine, MutateGate, PinMapComposer,
  memnet-mcp server, parts/common/memnet, grammar fixtures, MN-REQ, product
  SysML, memnet contributor, build memnet, SSOT to code (pair sysml-ssot-to-code).
metadata:
  pattern: pipeline
  version: "2.4"
  domain: memnet
  product: "0.19.11"
---

# MemNet product development reference

Repo skill for **building** MemNet in **this** repository. Doctrine SSOT is `docs/` — do not duplicate or invent features here.

This checkout **vendors** agent skills under `.cursor/skills/` (core: `memnet-use` + MCP/format/nested/multitask). Load those when **using** MemNet; load **this** skill only when changing the engine, generic MCP, grammar, product SysML, or packaging. Which file realises a SysML part: [sysml-ssot-to-code](../sysml-ssot-to-code/SKILL.md) (allocate ledger; do not keep a second code map here).

**Product:** Hatch **0.19.11** (CLI `memnet`). Last published PyPI wheel is **`memnet-llm==0.19.6`** until this cut is uploaded. Version map: `docs/ROADMAP.md`. Shape: `docs/SHAPE.md`. **1.0** = 0.5–0.8 claimed (do not tag from this skill).

**`a.b.c` (ROADMAP law).** `a` = claim / generation (`0` = 1.0 unclaimed; `1` = claim of 0.5–0.8). `a` moves only if the contract breaks (Recall=`pin_map` / Commit=`mutate`, GraphElement identity, GQL-only wire). `b` = usage-method revision (new required loop step, new product tool, cue/outline/identity law, new goldfish verb). Historical extras **0.10–0.19** were `b`. N-server (#47) is not a `b`. `c` = same-method cut (honesty, leftover naming, docs/skills, wheel/tag, caps, façade, faster same `cue → pin_map → mutate`). Efficiency on the current loop is **`0.19.c`**, not `0.20`. Do not invent a 0.20 extra. Do not claim 1.0.

## When loaded

1. Confirm the task is **product development** in this MemNet repo. If the task is **using** MemNet, stop and load [memnet-use](../memnet-use/SKILL.md).
2. Read `AGENTS.md` and `project.toml`.
3. Route via `docs/README.md` (identity / `grammar/` / `cabinet/` / `extras/` / `operations/` / `application-notes/`).
4. SysML agent I/O: in-repo `sysml-*` skills (table in [`.cursor/skills/README.md`](../README.md)).

## Mission (product)

**MemNet** is mission working memory — a session graph (GQL node, edge, property) between LLM call pipelines and data search, not a RAG corpus. This repo ships the **engine** (`parts/common/memnet/`) and **generic MCP** (`parts/memnet-mcp/`) only — novel-writer dropped.

## Implementation tracker (SSOT → code)

Do **not** keep a second code-map table in this skill. Logical parts → live modules:

| Need | Path |
|------|------|
| Ledger (every allocate row) | `sysml-models/outputs/ssot-to-code-allocate-map.md` |
| Allocate structure | `sysml-models/models/implementation.sysml` |
| Skill | [sysml-ssot-to-code](../sysml-ssot-to-code/SKILL.md) |

Console entries: `memnet.cli:main` (`parts/common/memnet/memnet/cli.py`) and `memnet_mcp.server:main`. Serve daemon: `memnet/serve.py`. TCP `:18765`; `--ipc`. When you add, move, or drop a shipped module: update the allocate row, sync the map, run `pytest tests/test_sysml_ssot_to_code.py`. MUST NOT invent a `sysmledge` path.

Wire: `docs/grammar/gql-wire-profile.md`. ADR: `docs/adr/ADR-001-gql-agent-wire.md`.

## Development checks

```bash
source .venv/bin/activate
pytest
ruff check parts/common/memnet parts/memnet-mcp/software tests
```

## MUSTNOT (contributors)

- Restore `parts/novel-writer/` or novel MCP extras.
- Invent a third peer agent wire — teach is **GQL only**.
- Claim MN-REQ-11.1–11.5 round-trip from ingest or from cue `export_pin_map` (SysML reverse still #66).
- Invent N-server federation (#47).
- Duplicate a drifting code-map table that bypasses `implementation.sysml`.
- Invent a SysMLEdge / `sysmledge` product face or upload/bind in this repo.
- Vendor the **whole** user pack, or hardware/PCBA/mermaid/generator skills, into `.cursor/skills/`.
- Revive Layer / Tier A as agent teach; do not restore dropped Layer docs into `docs/`.

## Related

Index: [`.cursor/skills/README.md`](../README.md) · routing: [`SKILL-GRAPH.md`](../SKILL-GRAPH.md) · hub: `AGENTS.md` · allocate: [sysml-ssot-to-code](../sysml-ssot-to-code/SKILL.md).
