---
name: memnet-repo
description: Use when working in the MemNet repository: build and test commands, layout pointers, SysML source of truth and standing conventions. Read first, then add the task delta.
---

# MemNet repo context

Repo context lives in the repo (owner rule t275u). This file points; it does not copy. Authority: `AGENTS.md`.

## Build and test
- Install: `uv sync --all-extras` (or `pip install -e ".[dev,mcp]"`).
- Test: `uv run pytest -q`. `tests/conftest.py` runs everything in-process; no serve daemon needed.
- Lint: `ruff check` and `ruff format --check` over the paths in `.github/workflows/ci.yml` (that file is the authority).
- Delete any generated, untracked `uv.lock` before committing.

## Layout
- `LAYOUT.md`: layout authority.
- `parts/common/memnet/`: engine. `parts/memnet-mcp/`: MCP server.
- `tests/`: test suite. `docs/README.md`: docs catalogue. `ops/`: operations sidecars.
- `sysml-models/`: models (`sysml-models/models/requirements.sysml`, `sysml-models/models/verify.sysml`, `sysml-models/models/deploy.sysml`).

## SysML source of truth
`sysml-models/` is the model SSOT for this repo (repo-based): `AGENTS.md` policy 6. Implementation tracking: `.cursor/skills/sysml-ssot-to-code/`.

## Standing conventions
- Ids are opaque: never read meaning from an id's value, order or sequence; only uniqueness and never-reuse count. No range comparisons on ids (equality lookup is fine).
- Link and relation types are camelCase (e.g. `inFile`): `docs/operations/honesty-c-wire-audit.md`.
- Every change ends in a PR from a branch; only the owner merges. No push to master, no force-push.
- British English in new docs (`AGENTS.md` policy 4).
- Part-based folders; novel-writer stays dropped (`AGENTS.md` policies 1 and 2).

## Vendored skills
Routing: `.cursor/skills/SKILL-GRAPH.md`.
