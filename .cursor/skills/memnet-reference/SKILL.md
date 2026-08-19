---
name: memnet-reference
description: >-
  Load when developing the MemNet product repository: engine, generic MCP,
  shared-dialect grammar, SysML models, packaging, CI, and contributor layout.
  Triggers: MemNet development, memnet engine, MutateGate, PinMapComposer,
  memnet-mcp server, parts/common/memnet, grammar fixtures, MN-REQ, product
  SysML, memnet contributor, build memnet. For SysML agent I/O in this checkout,
  load `.cursor/skills/sysml-*` (cloud VMs have no user pack). For MCP / Multitask
  application on a human machine, load user-pack mcp-memnet, memnet-format, or
  memnet-multitask.
metadata:
  pattern: pipeline
  version: "2.0"
  domain: memnet
  product: "0.9.0"
---

# MemNet product development reference

Repo skill for **building** MemNet in **this** repository. Doctrine SSOT lives in docs below -- do not duplicate or invent features here.

**Product version:** `project.toml` / Hatch **0.9.0** (CLI command remains `memnet`). **PyPI `memnet-llm` is 0.9.0.** Version map SSOT: `docs/ROADMAP.md`. Product shape: `docs/SHAPE.md`. **0.9** = Neo4j cabinet-client extra (`liveNeo4jClaimed=false`). **0.8** = GQL teach + shape for people. **1.0** = 0.5–0.8 claimed (do not tag from this skill).

## When loaded

1. Confirm the task is **product development** in this MemNet repo (not user-pack application).
2. Read `AGENTS.md` and `project.toml` for version, layout, and policy.
3. Route to the canonical path below (engine, MCP, grammar, SysML) — do not duplicate doctrine.
4. For SysML agent I/O in this repo, open the **in-repo** skills under `.cursor/skills/` first (table below). On a human machine the user pack (`~/.cursor/skills`) is the live home of those skills; cloud VMs have no user pack and **MUST** use the vendored copies.

## Mission (product)

**MemNet** (Net of Memory) is **mission working memory** — a session graph (GQL node/vertex, edge/relationship, property) between LLM call pipelines and data search, not a RAG corpus. This repo ships the **engine** (`parts/common/memnet/`) and **generic MCP** (`parts/memnet-mcp/`) only -- novel-writer dropped.

## Using MemNet (SysML / agent I/O -- pointer only)

**In-repo first** (cloud VMs only see this checkout):

| Intent | Path |
|--------|------|
| 6-step MemNet modeling turn | `.cursor/skills/sysml-modeling-workflow/` |
| Session checklist before `.sysml` edits | `.cursor/skills/sysml-modeling-session-checklist/` |
| Specialist read/write defer | `.cursor/skills/sysml-memnet-cache/` |
| Snap, read policy, pattern SSOT | `.cursor/skills/sysml-memnet-documentation/` |
| Thin SysML × GQL bridge | `.cursor/skills/sysml-gql/` |

On a human machine the same names live in **`~/.cursor/skills/`** (live home of the Apache user pack). Cloud VMs **MUST** use the vendored copies above. Do not teach those playbooks here.

MCP tools (`mcp-memnet`), wire shapes (`memnet-format`), and Multitask (`memnet-multitask`) remain user-pack only — not vendored in this repo.

## Canonical paths (this repo)

| Need | Path | Docs class |
|------|------|------------|
| Docs index | `docs/README.md` | -- |
| Doctrine / quick start | `README.md` | -- |
| Product shape | `docs/SHAPE.md` | developers |
| One-path / version map | `docs/ROADMAP.md` (SSOT; 0.9 this cut; 1.0 = 0.5–0.8 claimed) | developers |
| Agent playbook (product) | `docs/LLM-GUIDE.md` | developers |
| Multitask product ops | `docs/multi-agent-sessions.md` | developers |
| Multitask system-repo pattern | `docs/application-notes/llm-system-dev-multitask.md` | applications |
| Shared-dialect grammar | `docs/grammar/` | developers |
| Grammar golden fixtures | `docs/grammar/examples/` | developers |
| Grammar tools | `docs/grammar/tools/` | developers |
| Core library | `parts/common/memnet/` | -- |
| Generic MCP | `parts/memnet-mcp/software/memnet_mcp/` | -- |
| SysML product models | `sysml-models/` | -- |
| Tests | `tests/` | -- |
| Layout / hub | `LAYOUT.md`, `AGENTS.md` | -- |
| Novel-writer drop | `DROP-NOVEL-WRITER.md` | -- |

**Remote teach (one path):** Cursor **`memnet-pi`** HTTP `"url"` — not dual-equal with project `memnet-local` (stdio = optional/dev-only). **Dialect teach:** **GQL only** — [`docs/grammar/gql-wire-profile.md`](../../../docs/grammar/gql-wire-profile.md); ADR [`docs/adr/ADR-001-gql-agent-wire.md`](../../../docs/adr/ADR-001-gql-agent-wire.md). Detail: `docs/ROADMAP.md`.

Part-based folders only -- do not recreate top-level `src/` or `applications/`.

## Code map

| Component | Path | Notes |
|-----------|------|-------|
| As-is line codec | `parts/common/memnet/memnet/tier_a.py` | Retired from product accept (M2); archive/tests only |
| GqlCodec | `parts/common/memnet/memnet/gql_codec.py` | Primary agent wire (M2) |
| MutateGate | `parts/common/memnet/memnet/mutate_gate.py` | Mutate parse → mint → commit (GQL path) |
| PinMapComposer | `parts/common/memnet/memnet/pin_map_composer.py` | Live pin map emit → shaped GQL |
| IdAllocator | `parts/common/memnet/memnet/id_allocator.py` | `NEW` minting |
| CLI + serve | `parts/common/memnet/memnet/cli/` | `memnet serve` TCP `:18765`; `--ipc` / `MEMNET_IPC_SOCKET` (MN-REQ-06.2) |
| MCP server | `parts/memnet-mcp/software/memnet_mcp/server.py` | Tool SSOT |
| Path-B ingest (all domains) | `parts/common/memnet/memnet/pin_map_ingest.py` | `PinMapIngest_Sysml` / `_Codebase` / `_PcbaAto` / `_SkillsRules` |
| Path-B session import | `parts/common/memnet/memnet/import_absorb.py` | `import_slice` + optional ImportGuard host hook |

Formal wire: `docs/grammar/gql-wire-profile.md`. As-is harness notes: `docs/grammar/memnet-grammar-design.md`.

## Development checks

```powershell
pip install -e ".[dev]"
pytest tests/
```

Grammar fixtures: `docs/grammar/tools/tier_a.py`, `docs/grammar/examples/`. SysML verify trail for Multitask: MN-REQ-12 in `sysml-models/models/requirements.sysml`, MN-VER-12 in `sysml-models/models/verify.sysml`.

## MUSTNOT (contributors)

- Restore `parts/novel-writer/` or novel MCP extras.
- Invent a third peer agent wire dialect — teach is **GQL only** (ADR-001 + `gql-wire-profile.md`).
- Claim **pin-map export / round-trip** (MN-REQ-11.1–11.5 / #66) from ingest alone —
  Path-B `PinMapIngest_*` domains (Sysml/Codebase/PcbaAto/SkillsRules) are as-is;
  export remains separate.
- Invent N-server federation for Path-B ingest.
- Vendor the whole user pack, or hardware/PCBA/mermaid/generator skills, into `.cursor/skills/`. The five SysML modeling trees above are the allowed copies so cloud VMs can load them.
- Revive Layer / Tier A as agent teach or accept path; archived sources stay under `docs/grammar/archive/`.

## Related

| Path | Role |
|------|------|
| `.cursor/skills/memnet-reference/` (this) | Product development routing |
| `.cursor/skills/sysml-modeling-workflow/` | In-repo SysML 6-step turn (cloud VM copy) |
| `.cursor/skills/sysml-modeling-session-checklist/` | In-repo modeling checklist (cloud VM copy) |
| `.cursor/skills/sysml-memnet-cache/` | In-repo SysML cache defer (cloud VM copy) |
| `.cursor/skills/sysml-memnet-documentation/` | In-repo snap / read policy (cloud VM copy) |
| `.cursor/skills/sysml-gql/` | In-repo SysML GQL bridge (cloud VM copy) |
| `~/.cursor/skills/mcp-memnet/` | Using MemNet via MCP (user pack; not in this checkout) |
| `~/.cursor/skills/memnet-multitask/` | Multitask application doctrine (user pack; not in this checkout) |
| `docs/README.md` | Developers vs applications doc index |
| `AGENTS.md` | Hub / policy |
