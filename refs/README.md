# Grammar and parser references

Local, ASCII-path vendor material for MemNet wire / LLM grammar work and a future human/parser SSOT. **Not** product code under `parts/`. Do not reintroduce novel-writer here.

## Layout

| Path | Role |
|------|------|
| `refs/novel-cut-grammar/` | Extracted grammar + Gn digest notes from private `chouswei/novel-cut` |
| `third_party/antlr4/` | Sparse shallow checkout of ANTLR 4 (docs only) |

Both content trees are **gitignored** (local-only). This README is the tracked pin index.

## novel-cut (LLM-friendly grammar SSOT)

- **Upstream:** https://github.com/chouswei/novel-cut (private; needs `gh` auth)
- **Pinned commit:** `6a0ed88396f6a6e295c7f7adef8852b04a3cf515` (main @ 2026-07-21, v0.7.14 message)
- **Why:** MemNet wire dialect lineage — `md_triple` **Write = display**, G_n digest composition, author-prompt grammar load path. Reference only; no novel play loop under `parts/`.

### Refresh

```powershell
# Re-fetch selected blobs (example: grammar SSOT)
gh api repos/chouswei/novel-cut/contents/specs/md_triple_grammar.md -q .content
# Prefer copying via the same selective extract used when seeding this folder.
```

See `refs/novel-cut-grammar/MANIFEST.md` for the file list and Gn pointers.

### MemNet use

- Treat `specs/md_triple_grammar.md` as the **LLM-facing wire grammar** template (copy shapes; one dialect).
- Use `compose_g_n_digest` in `src/novel_engine/world_graph.py` and `docs/architecture.md` as the **working-memory digest** pattern when designing MemNet warm/query → prompt assembly.
- Ignore novel modules / prompt packs / applications — out of scope for MemNet core.

## antlr4 (human / parser SSOT tooling)

- **Upstream:** https://github.com/antlr/antlr4
- **Pin method:** **sparse shallow clone** (not submodule) — tag **`4.13.2`**, commit `cc82115a4e7f53d71d9d905caa2c2dfa4da58899`
- **Sparse paths:** cone checkout of `doc/` plus root metadata (`README.md`, `LICENSE.txt`, …)
- **Why not submodule:** full antlr4 tree is large (~70k GitHub size units); we only need docs/tooling reference before any `.g4` authoring. Submodule can be added later if CI must pin the whole tree.

### Refresh

```powershell
$dest = "C:\Projects\MemNet\third_party\antlr4"
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
git clone --depth 1 --filter=blob:none --sparse --branch 4.13.2 https://github.com/antlr/antlr4.git $dest
Set-Location $dest
git sparse-checkout set doc
# README.md and other root files arrive with the sparse tip; verify HEAD == 4.13.2
git describe --tags --always
```

### MemNet use

- Human/parser SSOT for future `.g4` grammars that mirror the LLM wire book.
- Prefer docs under `third_party/antlr4/doc/` (e.g. `grammars.md`, `getting-started.md`) before pulling runtimes.

## MemNet grammar design (in-repo)

Normative design for the LLM-facing dialect (Write = display, NODE|EDGE, pin-map warm):

- [`docs/grammar/memnet-grammar-design.md`](../docs/grammar/memnet-grammar-design.md)
- Starter ANTLR stub: [`docs/grammar/MemNet.g4`](../docs/grammar/MemNet.g4)
- Fixtures: [`docs/grammar/examples/`](../docs/grammar/examples/)

Vendor trees below remain lineage / tooling references only.

## Policy

- No SysML parts building from this folder.
- Prefer leaving fetch artefacts uncommitted; commit only when explicitly requested.
- Do not publish or rewrite remote history of vendor trees from this workspace.
